"""
管理端活动日志路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin_log import AdminActivityLogPageResponse
from app.services import admin_log_query_service


router = APIRouter(prefix="/admin", tags=["Admin Log"])


@router.get(
    "/logs",
    response_model=AdminActivityLogPageResponse,
    summary="管理端查看活动日志",
)
async def list_admin_activity_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    agent_id: Optional[str] = Query(None, description="按 Agent 过滤"),
    action: Optional[str] = Query(None, description="按动作类型过滤"),
    sub_task_id: Optional[str] = Query(None, description="按关联子任务过滤"),
    keyword: Optional[str] = Query(None, description="按摘要内容搜索"),
    days: Optional[int] = Query(None, ge=1, description="最近 N 天"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看管理端全局活动日志"""
    return admin_log_query_service.list_activity_logs(
        db,
        page=page,
        page_size=page_size,
        agent_id=agent_id,
        action=action,
        sub_task_id=sub_task_id,
        keyword=keyword,
        days=days,
        sort_order=sort_order,
    )
