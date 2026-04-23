"""配置态 Agent 基础 CRUD 路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    ManagedAgentCreateRequest,
    ManagedAgentDetail,
    ManagedAgentListItem,
    ManagedAgentPageResponse,
    ManagedAgentUpdateRequest,
)
from app.services import managed_agent as svc

from .readiness import agent_detail_response, apply_agent_projection


router = APIRouter(prefix="/admin/managed-agents")


@router.get("", response_model=ManagedAgentPageResponse)
def list_agents(
    _: bool = Depends(verify_admin),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: str = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    """分页查询配置态 Agent。"""
    items, total = svc.list_managed_agents(db, page, page_size, role, status)
    readiness_map = svc.compute_readiness_for_agents(db, items)
    runtime_identity_map = svc.compute_runtime_identity_for_agents(db, items)

    result_items = []
    for item in items:
        result_items.append(
            apply_agent_projection(
                ManagedAgentListItem.model_validate(item),
                item,
                readiness_map.get(item.id, {}),
                runtime_identity_map.get(item.id, {}),
            )
        )

    return ManagedAgentPageResponse(
        items=result_items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ManagedAgentDetail, status_code=201)
def create_agent(
    req: ManagedAgentCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建配置态 Agent（草稿）。"""
    try:
        agent = svc.create_managed_agent(
            db,
            name=req.name,
            slug=req.slug,
            role=req.role,
            description=req.description,
            host_platform=req.host_platform,
            deployment_mode=req.deployment_mode,
            host_access_mode=req.host_access_mode,
            host_agent_identifier=req.host_agent_identifier,
            workdir_path=req.workdir_path,
        )
        return agent_detail_response(db, agent)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}", response_model=ManagedAgentDetail)
def get_agent(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取配置态 Agent 详情。"""
    agent = svc.get_managed_agent(db, agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return agent_detail_response(db, agent)


@router.put("/{agent_id}", response_model=ManagedAgentDetail)
def update_agent(
    agent_id: str,
    req: ManagedAgentUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新配置态 Agent 基础信息。"""
    try:
        agent = svc.update_managed_agent(
            db,
            agent_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return agent_detail_response(db, agent)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{agent_id}", status_code=204)
def delete_agent(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除配置态 Agent（硬删除）。"""
    try:
        svc.delete_managed_agent(db, agent_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

