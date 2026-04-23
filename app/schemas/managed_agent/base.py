"""配置态 Agent 基础 Schema。"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


ManagedAgentRole = Literal["planner", "executor", "reviewer", "patrol"]
ManagedAgentHostPlatform = Literal["openclaw", "codex_cli", "claude_code", "generic_api_agent"]
ManagedAgentDeploymentMode = Literal["create_sub_agent", "bind_existing_agent", "bind_main_agent"]
ManagedAgentHostAccessMode = Literal["local", "remote"]
ManagedAgentStatus = Literal["draft", "configured", "deployed", "disabled", "archived"]
ManagedAgentHostRenderStrategy = Literal[
    "host_default",
    "openclaw_workspace_files",
    "openclaw_inline_schedule",
]
ManagedAgentScheduleType = Literal["interval", "cron"]
ManagedAgentCommProvider = Literal["feishu", "slack", "telegram", "wechat", "email", "webhook"]


class ManagedAgentCreateRequest(BaseModel):
    """创建配置态 Agent。"""

    name: str = Field(..., min_length=1, max_length=100, description="名称")
    slug: str = Field(..., min_length=1, max_length=100, description="稳定标识")
    role: ManagedAgentRole = Field(..., description="角色: planner/executor/reviewer/patrol")
    description: str = Field(default="", description="描述")
    host_platform: ManagedAgentHostPlatform = Field(default="openclaw", description="宿主平台")
    deployment_mode: ManagedAgentDeploymentMode = Field(
        ...,
        description="create_sub_agent/bind_existing_agent/bind_main_agent",
    )
    host_access_mode: ManagedAgentHostAccessMode = Field(default="local", description="local/remote")
    host_agent_identifier: Optional[str] = Field(default=None, description="宿主平台中的 Agent 标识")
    workdir_path: Optional[str] = Field(default=None, description="宿主平台中的工作目录")


class ManagedAgentUpdateRequest(BaseModel):
    """更新配置态 Agent。"""

    name: Optional[str] = Field(default=None, max_length=100)
    description: Optional[str] = None
    host_platform: Optional[ManagedAgentHostPlatform] = None
    deployment_mode: Optional[ManagedAgentDeploymentMode] = None
    host_access_mode: Optional[ManagedAgentHostAccessMode] = None
    status: Optional[ManagedAgentStatus] = None

    @model_validator(mode="after")
    def validate_nullable_fields(self):
        non_nullable_fields = {
            "name",
            "host_platform",
            "deployment_mode",
            "host_access_mode",
            "status",
        }
        for field_name in non_nullable_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class ManagedAgentReadiness(BaseModel):
    """配置就绪度。"""

    host_config: bool = False
    prompt_asset: bool = False
    schedules_count: int = 0
    comm_bindings_count: int = 0
    deploy_ready: bool = False


class ManagedAgentRuntimeIdentity(BaseModel):
    """运行态身份摘要。"""

    registered: bool = False
    runtime_agent_id: Optional[str] = None
    api_key_masked: Optional[str] = None


class ManagedAgentListItem(BaseModel):
    """配置态 Agent 列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    role: ManagedAgentRole
    description: str
    host_platform: ManagedAgentHostPlatform
    deployment_mode: ManagedAgentDeploymentMode
    host_access_mode: ManagedAgentHostAccessMode
    status: ManagedAgentStatus
    runtime_agent_id: Optional[str] = None
    config_version: int
    deployed_config_version: Optional[int] = None
    needs_redeploy: bool = False
    online_status: Optional[str] = None
    data_source: str = "managed"
    readiness: ManagedAgentReadiness = Field(default_factory=ManagedAgentReadiness)
    runtime_identity: ManagedAgentRuntimeIdentity = Field(default_factory=ManagedAgentRuntimeIdentity)
    created_at: datetime
    updated_at: datetime


class ManagedAgentDetail(ManagedAgentListItem):
    """配置态 Agent 详情。"""


class ManagedAgentPageResponse(BaseModel):
    """分页响应。"""

    items: List[ManagedAgentListItem]
    total: int
    page: int
    page_size: int


class ManagedAgentHostPlatformCapabilities(BaseModel):
    """宿主平台能力。"""

    renderer: bool
    bootstrap_script: bool
    skill_bundle: bool
    prompt_preview: bool
    schedule: bool
    comm_binding: bool


class ManagedAgentHostPlatformMetaItem(BaseModel):
    """宿主平台元数据项。"""

    key: ManagedAgentHostPlatform
    label: str
    description: str = ""
    access_modes: List[ManagedAgentHostAccessMode]
    deployment_modes: List[ManagedAgentDeploymentMode]
    capabilities: ManagedAgentHostPlatformCapabilities
    supported_comm_providers: List[ManagedAgentCommProvider]
    ui_hints: Dict[str, Any] = Field(default_factory=dict)


class ManagedAgentHostPlatformMetaResponse(BaseModel):
    """宿主平台元数据响应。"""

    items: List[ManagedAgentHostPlatformMetaItem]


class ManagedAgentPromptTemplateItem(BaseModel):
    """角色 Prompt 模板示例。"""

    role: ManagedAgentRole
    label: str
    filename: str
    content: str


class ManagedAgentPromptTemplateListResponse(BaseModel):
    """角色 Prompt 模板示例列表响应。"""

    items: List[ManagedAgentPromptTemplateItem]


class ManagedAgentRuntimeApiKeyResetResponse(BaseModel):
    """重置运行态 API Key 响应，仅本次返回明文。"""

    runtime_agent_id: str
    api_key: str
    api_key_masked: str
    message: str

