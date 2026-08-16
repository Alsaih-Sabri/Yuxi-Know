"""用户 repository 的凭据撤销测试。"""

from __future__ import annotations

from datetime import timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from yuxi.repositories.user_repository import UserRepository
from yuxi.storage.postgres.models_business import APIKey, Base, User
from yuxi.utils.auth_utils import AuthUtils
from yuxi.utils.datetime_utils import utc_now_naive

pytestmark = [pytest.mark.asyncio, pytest.mark.unit]


@pytest_asyncio.fixture()
async def user_session():
    """创建带活动 Key 与历史 tombstone 的 SQLite 会话。"""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            username="Delete User",
            uid="delete_user",
            password_hash="$argon2id$placeholder",
            role="user",
        )
        session.add(user)
        await session.flush()
        keys = []
        for name in ("active", "already revoked"):
            _secret, key_hash, key_prefix = AuthUtils.generate_api_key()
            keys.append(
                APIKey(
                    key_hash=key_hash,
                    key_prefix=key_prefix,
                    name=name,
                    user_id=user.id,
                    created_by=str(user.id),
                )
            )
        previous_revocation = utc_now_naive() - timedelta(days=1)
        keys[1].is_enabled = False
        keys[1].revoked_at = previous_revocation
        session.add_all(keys)
        await session.commit()
        yield session, user, keys, previous_revocation
    await engine.dispose()


async def test_soft_delete_tombstones_all_api_keys_without_rewriting_history(user_session) -> None:
    """通用软删除入口也必须阻止旧请求复活凭据。"""

    session, user, keys, previous_revocation = user_session

    deleted = await UserRepository(session).soft_delete(user.id, username=user.username)

    assert deleted is True
    assert user.is_deleted == 1
    assert keys[0].is_enabled is False
    assert keys[0].revoked_at is not None
    assert keys[1].is_enabled is False
    assert keys[1].revoked_at == previous_revocation
