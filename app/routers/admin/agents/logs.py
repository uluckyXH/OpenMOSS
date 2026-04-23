"""
管理端 Agent 日志查询路由 — 积分明细、活动日志、请求日志
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin.agent import (
    AdminAgentActivityLogPageResponse,
    AdminAgentRequestLogPageResponse,
    AdminAgentScoreLogPageResponse,
)
from app.services.admin_query import agent as admin_agent_query_service


router = APIRouter(prefix="/admin", tags=["Admin Agent"])


@router.get(
    "/agents/{agent_id}/score-logs",
    response_model=AdminAgentScoreLogPageResponse,
    summary="管理端查看 Agent 积分明细",
)
async def list_admin_agent_score_logs(
    agent_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    sub_task_id: Optional[str] = Query(None, description="按关联子任务过滤"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看指定 Agent 的积分明细"""
    return admin_agent_query_service.list_agent_score_logs(
        db,
        agent_id=agent_id,
        page=page,
        page_size=page_size,
        sub_task_id=sub_task_id,
        sort_order=sort_order,
    )


@router.get(
    "/agents/{agent_id}/activity-logs",
    response_model=AdminAgentActivityLogPageResponse,
    summary="管理端查看 Agent 活动日志",
)
async def list_admin_agent_activity_logs(
    agent_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    action: Optional[str] = Query(None, description="按日志动作过滤"),
    days: Optional[int] = Query(None, ge=1, description="最近 N 天"),
    sub_task_id: Optional[str] = Query(None, description="按关联子任务过滤"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看指定 Agent 的活动日志"""
    return admin_agent_query_service.list_agent_activity_logs(
        db,
        agent_id=agent_id,
        page=page,
        page_size=page_size,
        action=action,
        days=days,
        sub_task_id=sub_task_id,
    )


@router.get(
    "/agents/{agent_id}/request-logs",
    response_model=AdminAgentRequestLogPageResponse,
    summary="管理端查看 Agent 请求日志",
)
async def list_admin_agent_request_logs(
    agent_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    days: Optional[int] = Query(None, ge=1, description="最近 N 天"),
    method: Optional[str] = Query(None, description="按 HTTP 方法过滤"),
    path_keyword: Optional[str] = Query(None, description="按请求路径关键字搜索"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看指定 Agent 的请求日志"""
    return admin_agent_query_service.list_agent_request_logs(
        db,
        agent_id=agent_id,
        page=page,
        page_size=page_size,
        days=days,
        method=method,
        path_keyword=path_keyword,
    )
