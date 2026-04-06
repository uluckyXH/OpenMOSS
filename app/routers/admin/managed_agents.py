"""
管理端路由 — 配置态 Agent 管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    ManagedAgentCommBindingCreateRequest,
    ManagedAgentCommBindingResponse,
    ManagedAgentCommBindingUpdateRequest,
    ManagedAgentCreateRequest,
    ManagedAgentDetail,
    ManagedAgentHostConfigRequest,
    ManagedAgentHostConfigResponse,
    ManagedAgentListItem,
    ManagedAgentPageResponse,
    ManagedAgentPromptAssetRequest,
    ManagedAgentPromptAssetResponse,
    ManagedAgentPromptRenderPreviewResponse,
    ManagedAgentScheduleCreateRequest,
    ManagedAgentScheduleResponse,
    ManagedAgentScheduleUpdateRequest,
    ManagedAgentUpdateRequest,
)
from app.services import managed_agent as svc

router = APIRouter(
    prefix="/admin/managed-agents",
    tags=["Admin - 配置态 Agent"],
)


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

    result_items = []
    for item in items:
        list_item = ManagedAgentListItem.model_validate(item)
        if item.config_version and item.deployed_config_version:
            list_item.needs_redeploy = item.config_version != item.deployed_config_version
        result_items.append(list_item)

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
        return ManagedAgentDetail.model_validate(agent)
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
    detail = ManagedAgentDetail.model_validate(agent)
    if agent.config_version and agent.deployed_config_version:
        detail.needs_redeploy = agent.config_version != agent.deployed_config_version
    return detail


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
        return ManagedAgentDetail.model_validate(agent)
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


@router.get("/{agent_id}/host-config", response_model=ManagedAgentHostConfigResponse)
def get_host_config(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取宿主平台配置。"""
    svc.get_managed_agent_or_404(db, agent_id)
    host_config = svc.get_host_config(db, agent_id)
    if not host_config:
        raise HTTPException(status_code=404, detail="宿主平台配置未配置")
    return ManagedAgentHostConfigResponse.model_validate(svc.serialize_host_config(host_config))


@router.put("/{agent_id}/host-config", response_model=ManagedAgentHostConfigResponse)
def update_host_config(
    agent_id: str,
    req: ManagedAgentHostConfigRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新宿主平台配置。"""
    try:
        host_config = svc.update_host_config(
            db,
            agent_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return ManagedAgentHostConfigResponse.model_validate(svc.serialize_host_config(host_config))
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/prompt-asset", response_model=ManagedAgentPromptAssetResponse)
def get_prompt_asset(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取 Prompt 资产。"""
    svc.get_managed_agent_or_404(db, agent_id)
    prompt_asset = svc.get_prompt_asset(db, agent_id)
    if not prompt_asset:
        raise HTTPException(status_code=404, detail="Prompt 资产未配置")
    return ManagedAgentPromptAssetResponse.model_validate(prompt_asset)


@router.put("/{agent_id}/prompt-asset", response_model=ManagedAgentPromptAssetResponse)
def update_prompt_asset(
    agent_id: str,
    req: ManagedAgentPromptAssetRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新 Prompt 资产。"""
    try:
        prompt_asset = svc.update_prompt_asset(
            db,
            agent_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return ManagedAgentPromptAssetResponse.model_validate(prompt_asset)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/prompt-asset/reset-from-template", response_model=ManagedAgentPromptAssetResponse)
def reset_prompt_asset(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """从角色模板重新初始化 Prompt 资产。"""
    try:
        prompt_asset = svc.reset_prompt_from_template(db, agent_id)
        return ManagedAgentPromptAssetResponse.model_validate(prompt_asset)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/prompt-asset/render-preview", response_model=ManagedAgentPromptRenderPreviewResponse)
def render_prompt_preview(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """预览宿主平台渲染结果。"""
    try:
        preview = svc.render_prompt_preview(db, agent_id)
        return ManagedAgentPromptRenderPreviewResponse.model_validate(preview)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/schedules", response_model=list[ManagedAgentScheduleResponse])
def list_schedules(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取 Agent 的所有定时任务。"""
    try:
        schedules = svc.list_schedules(db, agent_id)
        return [ManagedAgentScheduleResponse.model_validate(item) for item in schedules]
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/schedules", response_model=ManagedAgentScheduleResponse, status_code=201)
def create_schedule(
    agent_id: str,
    req: ManagedAgentScheduleCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建定时任务。"""
    try:
        schedule = svc.create_schedule(
            db,
            agent_id,
            **req.model_dump(),
        )
        return ManagedAgentScheduleResponse.model_validate(schedule)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.put("/{agent_id}/schedules/{schedule_id}", response_model=ManagedAgentScheduleResponse)
def update_schedule(
    agent_id: str,
    schedule_id: str,
    req: ManagedAgentScheduleUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新定时任务。"""
    try:
        schedule = svc.update_schedule_for_agent(
            db,
            agent_id,
            schedule_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return ManagedAgentScheduleResponse.model_validate(schedule)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{agent_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    agent_id: str,
    schedule_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除定时任务。"""
    try:
        svc.delete_schedule_for_agent(db, agent_id, schedule_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


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
