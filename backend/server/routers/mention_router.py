from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from server.utils.auth_middleware import get_required_user
from yuxi.services.mention_search_service import search_mention_files_in_index
from yuxi.storage.postgres.models_business import User

mention_router = APIRouter(prefix="/mention", tags=["mention"])


@mention_router.get("/search", response_model=list[dict])
async def search_mention_files(
    thread_id: str = Query(..., description="当前聊天会话 ID"),
    query: str = Query("", description="模糊搜索关键字"),
    current_user: User = Depends(get_required_user),
):
    """
    提及文件模糊搜索接口：使用 Redis 二进制缓存进行极速过滤，防止大文件递归卡死。
    """
    user_id = str(current_user.id)
    return await search_mention_files_in_index(
        thread_id=thread_id,
        user_id=user_id,
        query=query,
    )
