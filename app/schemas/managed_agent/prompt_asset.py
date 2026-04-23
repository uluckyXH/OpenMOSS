"""配置态 Agent Prompt 资产 Schema。"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base import ManagedAgentHostRenderStrategy


class ManagedAgentPromptAssetRequest(BaseModel):
    """更新 Prompt 资产。"""

    system_prompt_content: Optional[str] = None
    persona_prompt_content: Optional[str] = None
    identity_content: Optional[str] = None
    host_render_strategy: Optional[ManagedAgentHostRenderStrategy] = Field(
        default=None,
        description="host_default/openclaw_workspace_files/openclaw_inline_schedule",
    )
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_nullable_fields(self):
        if "host_render_strategy" in self.model_fields_set and self.host_render_strategy is None:
            raise ValueError("host_render_strategy 不能为 null")
        return self


class ManagedAgentPromptAssetResponse(BaseModel):
    """Prompt 资产响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    template_role: Optional[str] = None
    system_prompt_content: str
    persona_prompt_content: str
    identity_content: str
    host_render_strategy: ManagedAgentHostRenderStrategy
    authority_source: str
    notes: Optional[str] = None
    updated_at: datetime


class ManagedAgentRenderedArtifact(BaseModel):
    """宿主平台渲染结果。"""

    name: str
    content: str


class ManagedAgentPromptRenderPreviewResponse(BaseModel):
    """Prompt 渲染预览。"""

    host_platform: str
    host_render_strategy: ManagedAgentHostRenderStrategy
    artifacts: List[ManagedAgentRenderedArtifact]

