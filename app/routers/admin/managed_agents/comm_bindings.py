"""配置态 Agent 通讯绑定路由。"""

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    ManagedAgentCommBindingCreateRequest,
    ManagedAgentCommBindingResponse,
    ManagedAgentCommBindingUpdateRequest,
)
from app.services import managed_agent as svc
from app.services.managed_agent.platforms.registry import get_comm_provider_adapter


router = APIRouter(prefix="/admin/managed-agents")


@router.get("/{agent_id}/comm-bindings", response_model=list[ManagedAgentCommBindingResponse])
def list_comm_bindings(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取宿主通讯渠道配置。"""
    try:
        bindings = svc.list_comm_bindings(db, agent_id)
        return [
            ManagedAgentCommBindingResponse.model_validate(svc.serialize_comm_binding(item))
            for item in bindings
        ]
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/comm-bindings", response_model=ManagedAgentCommBindingResponse, status_code=201)
def create_comm_binding(
    agent_id: str,
    req: ManagedAgentCommBindingCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建宿主通讯渠道配置。"""
    try:
        binding = svc.create_comm_binding(
            db,
            agent_id,
            **req.model_dump(),
        )
        return ManagedAgentCommBindingResponse.model_validate(svc.serialize_comm_binding(binding))
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.put("/{agent_id}/comm-bindings/{binding_id}", response_model=ManagedAgentCommBindingResponse)
def update_comm_binding(
    agent_id: str,
    binding_id: str,
    req: ManagedAgentCommBindingUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新宿主通讯渠道配置。"""
    try:
        binding = svc.update_comm_binding_for_agent(
            db,
            agent_id,
            binding_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return ManagedAgentCommBindingResponse.model_validate(svc.serialize_comm_binding(binding))
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{agent_id}/comm-bindings/{binding_id}", status_code=204)
def delete_comm_binding(
    agent_id: str,
    binding_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除宿主通讯渠道配置。"""
    try:
        svc.delete_comm_binding_for_agent(db, agent_id, binding_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/meta/host-platforms/{platform}/comm-providers/{provider}/schema")
def get_comm_provider_schema(
    platform: str,
    provider: str,
    _: bool = Depends(verify_admin),
):
    """返回指定平台 + 通讯渠道的字段 schema（能力发现）。"""
    try:
        adapter = get_comm_provider_adapter(platform, provider)
        return adapter.get_binding_schema()
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/meta/host-platforms/{platform}/comm-providers/{provider}/validate")
def validate_comm_binding_structured(
    platform: str,
    provider: str,
    body: dict = Body(...),
    _: bool = Depends(verify_admin),
):
    """预校验指定平台 + 通讯渠道的绑定数据。"""
    try:
        adapter = get_comm_provider_adapter(platform, provider)
        return adapter.validate_binding(body)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/comm-bindings-structured/{provider}")
def list_comm_bindings_structured(
    agent_id: str,
    provider: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """列出该 Agent 下指定通讯渠道的绑定。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        adapter = get_comm_provider_adapter(agent.host_platform, provider)
        return adapter.list_bindings(db, agent_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/comm-bindings-structured/{provider}/suggest")
def suggest_comm_binding_defaults(
    agent_id: str,
    provider: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """返回创建通讯绑定时的建议默认值（如自动生成的 account_id）。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        adapter = get_comm_provider_adapter(agent.host_platform, provider)
        return adapter.suggest_binding_defaults(db, agent_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/comm-bindings-structured/{provider}", status_code=201)
def create_comm_binding_structured(
    agent_id: str,
    provider: str,
    body: dict = Body(...),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建指定通讯渠道的绑定。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        adapter = get_comm_provider_adapter(agent.host_platform, provider)
        return adapter.create_binding(db, agent_id, body)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.put("/{agent_id}/comm-bindings-structured/{provider}/{binding_id}")
def update_comm_binding_structured(
    agent_id: str,
    provider: str,
    binding_id: str,
    body: dict = Body(...),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新指定通讯渠道的绑定。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        adapter = get_comm_provider_adapter(agent.host_platform, provider)
        return adapter.update_binding(db, agent_id, binding_id, body)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{agent_id}/comm-bindings-structured/{provider}/{binding_id}", status_code=204)
def delete_comm_binding_structured(
    agent_id: str,
    provider: str,
    binding_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除指定通讯渠道的绑定。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        adapter = get_comm_provider_adapter(agent.host_platform, provider)
        adapter.delete_binding(db, agent_id, binding_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

