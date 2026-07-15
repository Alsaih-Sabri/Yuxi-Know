"""PostgreSQL concurrency coverage for Agent request intake."""

from __future__ import annotations

import asyncio
import os
import uuid
from unittest.mock import MagicMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yuxi.repositories.agent_run_request_repository import AgentRunRequestRepository
from yuxi.services import agent_request_queue_service
from yuxi.services.input_message_service import build_chat_input_message
from yuxi.storage.postgres.models_business import AgentRun, AgentRunRequest, Conversation, Message

pytestmark = [pytest.mark.asyncio, pytest.mark.integration]


async def test_concurrent_reject_requests_never_enter_queue(monkeypatch: pytest.MonkeyPatch):
    thread_id = f"pytest-reject-{uuid.uuid4()}"
    uid = f"pytest-user-{uuid.uuid4()}"
    request_ids = [f"reject-{uuid.uuid4()}" for _ in range(2)]
    engine = create_async_engine(os.environ["POSTGRES_URL"], pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    monkeypatch.setattr(agent_request_queue_service, "resolve_agent_run_config", lambda *args: ("model", "default"))

    original_create = AgentRunRequestRepository.create
    both_requests_created = asyncio.Event()
    created_count = 0
    count_lock = asyncio.Lock()

    async def synchronized_create(self, **kwargs):
        nonlocal created_count
        request = await original_create(self, **kwargs)
        async with count_lock:
            created_count += 1
            if created_count == 2:
                both_requests_created.set()
        await asyncio.wait_for(both_requests_created.wait(), timeout=5)
        return request

    monkeypatch.setattr(AgentRunRequestRepository, "create", synchronized_create)

    async with session_factory() as db:
        conversation = Conversation(thread_id=thread_id, uid=uid, agent_id="main", status="active")
        db.add(conversation)
        await db.commit()

    async def submit(request_id: str):
        async with session_factory() as db:
            result = await agent_request_queue_service.intake_request(
                db=db,
                request_id=request_id,
                uid=uid,
                agent_slug="main",
                thread_id=thread_id,
                queue_policy="reject",
                input_message=build_chat_input_message(request_id),
                agent_item=MagicMock(),
                agent_backend=MagicMock(),
            )
            await db.commit()
            return result

    try:
        results = await asyncio.wait_for(
            asyncio.gather(*(submit(request_id) for request_id in request_ids)),
            timeout=10,
        )

        assert sorted(result.status for result in results) == ["dispatched", "rejected"]

        async with session_factory() as db:
            requests = (
                (await db.execute(select(AgentRunRequest).where(AgentRunRequest.request_id.in_(request_ids))))
                .scalars()
                .all()
            )
            messages = (await db.execute(select(Message).where(Message.request_id.in_(request_ids)))).scalars().all()

        assert sorted(request.status for request in requests) == ["dispatched", "rejected"]
        assert sorted(message.delivery_status for message in messages) == ["dispatched", "rejected"]
    finally:
        async with session_factory() as db:
            conversation_id = await db.scalar(select(Conversation.id).where(Conversation.thread_id == thread_id))
            await db.execute(delete(AgentRunRequest).where(AgentRunRequest.conversation_thread_id == thread_id))
            if conversation_id is not None:
                await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
            await db.execute(delete(AgentRun).where(AgentRun.conversation_thread_id == thread_id))
            await db.execute(delete(Conversation).where(Conversation.thread_id == thread_id))
            await db.commit()
        await engine.dispose()
