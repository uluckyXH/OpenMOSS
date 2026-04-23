"""配置态 Agent Prompt 资产路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    ManagedAgentPromptAssetRequest,
    ManagedAgentPromptAssetResponse,
    ManagedAgentPromptRenderPreviewResponse,
)
from app.services import managed_agent as svc


router = APIRouter(prefix="/admin/managed-agents")


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

