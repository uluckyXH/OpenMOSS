"""配置态 Agent 元数据路由。"""

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import verify_admin
from app.schemas.managed_agent import (
    ManagedAgentHostPlatformMetaResponse,
    ManagedAgentPromptTemplateListResponse,
    ManagedAgentRole,
)
from app.services import managed_agent as svc


router = APIRouter(prefix="/admin/managed-agents")


@router.get("/meta/host-platforms", response_model=ManagedAgentHostPlatformMetaResponse)
def list_host_platforms(
    _: bool = Depends(verify_admin),
):
    """返回当前后端真实支持的宿主平台能力。"""
    return ManagedAgentHostPlatformMetaResponse(items=svc.list_supported_host_platforms())


@router.get("/meta/prompt-templates", response_model=ManagedAgentPromptTemplateListResponse)
def list_prompt_templates(
    role: ManagedAgentRole | None = Query(None),
    _: bool = Depends(verify_admin),
):
    """返回 Agent 管理域使用的角色 Prompt 模板示例。"""
    return ManagedAgentPromptTemplateListResponse(items=svc.list_prompt_templates(role=role))

