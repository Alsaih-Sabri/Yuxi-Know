"""Dashboard 统计与监控 HTTP 路由。"""

import traceback

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.utils.auth_middleware import get_db, get_superadmin_user
from yuxi.repositories.conversation_repository import ConversationRepository
from yuxi.repositories.dashboard_repository import DashboardRepository
from yuxi.storage.minio.client import normalize_public_minio_url
from yuxi.storage.postgres.models_business import User
from yuxi.utils.logging_config import logger


dashboard = APIRouter(prefix="/dashboard", tags=["Dashboard"])


class UserActivityStats(BaseModel):
    """用户活跃度统计"""

    total_users: int
    active_users_24h: int
    active_users_30d: int
    daily_active_users: list[dict]


class ToolCallStats(BaseModel):
    """工具调用统计"""

    total_calls: int
    successful_calls: int
    failed_calls: int
    success_rate: float
    most_used_tools: list[dict]
    tool_error_distribution: dict
    daily_tool_calls: list[dict]


class AgentAnalytics(BaseModel):
    """AI 智能体分析"""

    total_agents: int
    agent_conversation_counts: list[dict]
    agent_satisfaction_rates: list[dict]
    agent_tool_usage: list[dict]
    top_performing_agents: list[dict]
    agent_names: dict[str, str] = {}


class ConversationListItem(BaseModel):
    """Dashboard 对话列表项。"""

    thread_id: str
    uid: str
    agent_id: str
    title: str | None
    status: str
    message_count: int
    created_at: str
    updated_at: str


class ConversationDetailResponse(BaseModel):
    """Dashboard 对话详情。"""

    thread_id: str
    uid: str
    agent_id: str
    title: str | None
    status: str
    message_count: int
    created_at: str
    updated_at: str
    total_tokens: int
    messages: list[dict]


@dashboard.get("/conversations", response_model=list[ConversationListItem])
async def get_all_conversations(
    uid: str | None = None,
    agent_id: str | None = None,
    status: str = "active",
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取所有对话（超级管理员权限）。"""
    try:
        return await DashboardRepository(db).list_conversations(
            uid=uid,
            agent_id=agent_id,
            status=status,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        logger.error(f"Error getting conversations: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get conversations: {str(exc)}") from exc


@dashboard.get("/conversations/{thread_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    thread_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取指定对话详情（超级管理员权限）。"""
    try:
        repository = ConversationRepository(db)
        conversation = await repository.get_conversation_by_thread_id(thread_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages = await repository.get_messages(conversation.id)
        stats = await repository.get_stats(conversation.id)
        message_list = []
        for message in messages:
            message_data = {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "message_type": message.message_type,
                "created_at": message.created_at.isoformat(),
            }
            if message.tool_calls:
                message_data["tool_calls"] = [
                    {
                        "id": tool_call.id,
                        "tool_name": tool_call.tool_name,
                        "tool_input": tool_call.tool_input,
                        "tool_output": tool_call.tool_output,
                        "status": tool_call.status,
                    }
                    for tool_call in message.tool_calls
                ]
            message_list.append(message_data)

        return {
            "thread_id": conversation.thread_id,
            "uid": conversation.uid,
            "agent_id": conversation.agent_id,
            "title": conversation.title,
            "status": conversation.status,
            "message_count": stats.message_count if stats else len(message_list),
            "created_at": conversation.created_at.isoformat(),
            "updated_at": conversation.updated_at.isoformat(),
            "total_tokens": stats.total_tokens if stats else 0,
            "messages": message_list,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error getting conversation detail: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get conversation detail: {str(exc)}") from exc


@dashboard.get("/stats/users", response_model=UserActivityStats)
async def get_user_activity_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取用户活动统计（超级管理员权限）。"""
    try:
        return UserActivityStats(**await DashboardRepository(db).get_user_activity_stats())
    except Exception as exc:
        logger.error(f"Error getting user activity stats: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get user activity stats: {str(exc)}") from exc


@dashboard.get("/stats/tools", response_model=ToolCallStats)
async def get_tool_call_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取工具调用统计（超级管理员权限）。"""
    try:
        return ToolCallStats(**await DashboardRepository(db).get_tool_call_stats())
    except Exception as exc:
        logger.error(f"Error getting tool call stats: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get tool call stats: {str(exc)}") from exc


@dashboard.get("/stats/agents", response_model=AgentAnalytics)
async def get_agent_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取智能体分析（超级管理员权限）。"""
    try:
        return AgentAnalytics(**await DashboardRepository(db).get_agent_analytics())
    except Exception as exc:
        logger.error(f"Error getting agent analytics: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get agent analytics: {str(exc)}") from exc


@dashboard.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取基础统计（超级管理员权限）。"""
    try:
        return await DashboardRepository(db).get_basic_stats()
    except Exception as exc:
        logger.error(f"Error getting dashboard stats: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard stats: {str(exc)}") from exc


class FeedbackListItem(BaseModel):
    """反馈列表项。"""

    id: int
    uid: str
    username: str | None
    avatar: str | None
    rating: str
    reason: str | None
    created_at: str
    message_content: str
    conversation_title: str | None
    agent_id: str


@dashboard.get("/feedbacks", response_model=list[FeedbackListItem])
async def get_all_feedbacks(
    rating: str | None = None,
    agent_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取所有反馈记录（超级管理员权限）。"""
    try:
        rows = await DashboardRepository(db).list_feedbacks(rating=rating, agent_id=agent_id)
        logger.info(f"Found {len(rows)} feedback records")
        return [
            {
                "id": feedback.id,
                "message_id": feedback.message_id,
                "uid": feedback.uid,
                "username": user.username if user else None,
                "avatar": normalize_public_minio_url(user.avatar) if user else None,
                "rating": feedback.rating,
                "reason": feedback.reason,
                "created_at": feedback.created_at.isoformat(),
                "message_content": message.content,
                "conversation_title": conversation.title,
                "agent_id": conversation.agent_id,
            }
            for feedback, message, conversation, user in rows
        ]
    except Exception as exc:
        logger.error(f"Error getting feedbacks: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get feedbacks: {str(exc)}") from exc


class TimeSeriesStats(BaseModel):
    """时间序列统计数据。"""

    data: list[dict]
    categories: list[str]
    total_count: int
    average_count: float
    peak_count: int
    peak_date: str
    agent_names: dict[str, str] | None = None


@dashboard.get("/stats/calls/timeseries", response_model=TimeSeriesStats)
async def get_call_timeseries_stats(
    type: str = "models",
    time_range: str = "14days",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_superadmin_user),
):
    """获取调用分析时间序列统计（超级管理员权限）。"""
    if type not in {"models", "agents", "tokens", "tools"}:
        raise HTTPException(status_code=422, detail=f"Invalid type: {type}")
    try:
        data = await DashboardRepository(db).get_call_timeseries(
            metric_type=type,
            time_range=time_range,
        )
        return TimeSeriesStats(**data)
    except Exception as exc:
        logger.error(f"Error getting call timeseries stats: {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to get call timeseries stats: {str(exc)}") from exc
