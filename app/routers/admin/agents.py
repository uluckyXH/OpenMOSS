"""
管理端 Agent 路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin_agent import (
    AdminAgentCreateRequest,
    AdminAgentCreateResponse,
    AdminAgentActivityLogPageResponse,
    AdminAgentDeleteRequest,
    AdminAgentDeleteResponse,
    AdminAgentDetail,
    AdminAgentPageResponse,
    AdminAgentRelatedCountsResponse,
    AdminAgentRequestLogPageResponse,
    AdminAgentResetKeyResponse,
    AdminAgentScoreLogPageResponse,
    AdminAgentStatusUpdateRequest,
    AdminAgentUpdateRequest,
    AdminAgentWriteResponse,
)
from app.services import admin_agent_query_service, agent_service


router = APIRouter(prefix="/admin", tags=["Admin Agent"])


@router.get("/agents", response_model=AdminAgentPageResponse, summary="管理端查看 Agent 列表")
async def list_admin_agents(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    role: Optional[str] = Query(None, description="按角色过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    keyword: Optional[str] = Query(None, description="按名称或描述搜索"),
    last_request_within_days: Optional[int] = Query(None, ge=1, description="最近请求 N 天内"),
    last_activity_within_days: Optional[int] = Query(None, ge=1, description="最近活动 N 天内"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查询管理端 Agent 列表"""
    return admin_agent_query_service.list_agents(
        db,
        page=page,
        page_size=page_size,
        role=role,
        status=status,
        keyword=keyword,
        last_request_within_days=last_request_within_days,
        last_activity_within_days=last_activity_within_days,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post("/agents", response_model=AdminAgentCreateResponse, summary="管理端创建 Agent")
async def create_admin_agent(
    req: AdminAgentCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员通过管理端命名空间创建 Agent"""
    agent = agent_service.register_agent(db, req.name, req.role, req.description)
    return AdminAgentCreateResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        api_key=agent.api_key,
    )


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


@router.put(
    "/agents/{agent_id}",
    response_model=AdminAgentWriteResponse,
    summary="管理端更新 Agent 信息",
)
async def update_admin_agent_profile(
    agent_id: str,
    req: AdminAgentUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员更新 Agent 的名称、角色或描述"""
    agent = agent_service.update_agent_profile(
        db,
        agent_id,
        name=req.name,
        role=req.role,
        description=req.description,
    )
    return AdminAgentWriteResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        description=agent.description,
        status=agent.status,
        total_score=agent.total_score,
    )


@router.put(
    "/agents/{agent_id}/status",
    response_model=AdminAgentWriteResponse,
    summary="管理端更新 Agent 状态",
)
async def update_admin_agent_status(
    agent_id: str,
    req: AdminAgentStatusUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员通过管理端命名空间更新 Agent 状态"""
    agent = agent_service.update_agent_status(db, agent_id, req.status)
    return AdminAgentWriteResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        description=agent.description,
        status=agent.status,
        total_score=agent.total_score,
    )


@router.post(
    "/agents/{agent_id}/reset-key",
    response_model=AdminAgentResetKeyResponse,
    summary="管理端重置 Agent API Key",
)
async def reset_admin_agent_key(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员通过管理端命名空间重置 Agent API Key"""
    agent = agent_service.reset_agent_api_key(db, agent_id)
    return AdminAgentResetKeyResponse(
        agent_id=agent.id,
        new_api_key=agent.api_key,
    )


@router.get("/agents/{agent_id}", response_model=AdminAgentDetail, summary="管理端查看 Agent 详情")
async def get_admin_agent_detail(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端单个 Agent 详情"""
    return admin_agent_query_service.get_agent_detail(db, agent_id)


@router.get(
    "/agents/{agent_id}/related-counts",
    response_model=AdminAgentRelatedCountsResponse,
    summary="查询 Agent 关联数据数量",
)
async def get_admin_agent_related_counts(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除前查询关联数据数量，用于风险提示"""
    return agent_service.get_agent_related_counts(db, agent_id)


@router.delete(
    "/agents/{agent_id}",
    response_model=AdminAgentDeleteResponse,
    summary="管理端删除 Agent",
)
async def delete_admin_agent(
    agent_id: str,
    req: AdminAgentDeleteRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除 Agent 并级联清理所有关联数据，需输入 Agent 名称确认"""
    counts = agent_service.delete_agent(db, agent_id, req.confirm_name)
    return AdminAgentDeleteResponse(
        agent_name=counts["agent_name"],
        sub_task_count=counts["sub_task_count"],
        review_count=counts["review_count"],
        reward_count=counts["reward_count"],
        activity_count=counts["activity_count"],
        patrol_count=counts["patrol_count"],
        request_count=counts["request_count"],
    )
