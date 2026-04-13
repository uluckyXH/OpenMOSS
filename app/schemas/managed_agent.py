"""
配置态 Agent 请求/响应 Schema
"""
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
ManagedAgentBootstrapPurpose = Literal["download_script", "register_runtime"]


# ============================================================
# ManagedAgent
# ============================================================


class ManagedAgentCreateRequest(BaseModel):
    """创建配置态 Agent"""
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

    # 新结构推荐字段
    host_agent_identifier: Optional[str] = Field(default=None, description="宿主平台中的 Agent 标识")
    workdir_path: Optional[str] = Field(default=None, description="宿主平台中的工作目录")


class ManagedAgentUpdateRequest(BaseModel):
    """更新配置态 Agent"""
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
    """列表项"""
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
    """详情"""


class ManagedAgentPageResponse(BaseModel):
    """分页响应"""
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


# ============================================================
# Host Config
# ============================================================


class ManagedAgentHostConfigRequest(BaseModel):
    """创建/更新宿主平台配置"""
    host_agent_identifier: Optional[str] = None
    workdir_path: Optional[str] = None
    host_config_payload: Optional[str] = Field(default=None, description="明文配置文本，当前先原样存储")
    host_metadata_json: Optional[str] = None


class ManagedAgentHostConfigResponse(BaseModel):
    """宿主平台配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    host_platform: str
    host_agent_identifier: Optional[str] = None
    workdir_path: Optional[str] = None
    host_config_payload_masked: Optional[str] = None
    host_metadata_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# Prompt Asset
# ============================================================


class ManagedAgentPromptAssetRequest(BaseModel):
    """更新 Prompt 资产"""
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
    """Prompt 资产响应"""
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
    """宿主平台渲染结果"""
    name: str
    content: str


class ManagedAgentPromptRenderPreviewResponse(BaseModel):
    """Prompt 渲染预览"""
    host_platform: str
    host_render_strategy: ManagedAgentHostRenderStrategy
    artifacts: List[ManagedAgentRenderedArtifact]


# ============================================================
# Schedule
# ============================================================


class ManagedAgentScheduleCreateRequest(BaseModel):
    """创建定时任务"""
    name: str = Field(..., min_length=1, max_length=200)
    enabled: bool = True
    schedule_type: ManagedAgentScheduleType = Field(..., description="interval/cron")
    schedule_expr: str = Field(..., min_length=1, description="间隔值或 5 段 cron 表达式")
    timeout_seconds: int = Field(..., ge=60)
    model_override: Optional[str] = None
    execution_options_json: Optional[str] = None
    schedule_message_content: str = Field(..., min_length=1, description="定时唤醒提示词")


class ManagedAgentScheduleUpdateRequest(BaseModel):
    """更新定时任务"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    enabled: Optional[bool] = None
    schedule_type: Optional[ManagedAgentScheduleType] = Field(default=None, description="interval/cron")
    schedule_expr: Optional[str] = Field(default=None, min_length=1, description="间隔值或 5 段 cron 表达式")
    timeout_seconds: Optional[int] = Field(default=None, ge=60)
    model_override: Optional[str] = None
    execution_options_json: Optional[str] = None
    schedule_message_content: Optional[str] = Field(default=None, min_length=1, description="定时唤醒提示词")

    @model_validator(mode="after")
    def validate_nullable_fields(self):
        non_nullable_fields = {
            "name",
            "enabled",
            "schedule_type",
            "schedule_expr",
            "timeout_seconds",
            "schedule_message_content",
        }
        for field_name in non_nullable_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class ManagedAgentScheduleResponse(BaseModel):
    """定时任务响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    name: str
    enabled: bool
    schedule_type: ManagedAgentScheduleType
    schedule_expr: str
    timeout_seconds: int
    model_override: Optional[str] = None
    execution_options_json: Optional[str] = None
    schedule_message_content: str
    created_at: datetime
    updated_at: datetime


# ============================================================
# Comm Binding
# ============================================================


class ManagedAgentCommBindingCreateRequest(BaseModel):
    """创建宿主通讯渠道配置"""
    provider: ManagedAgentCommProvider = Field(description="feishu/slack/telegram/wechat/email/webhook")
    binding_key: str = Field(description="平台账号或连接标识")
    display_name: Optional[str] = None
    enabled: bool = True
    routing_policy_json: Optional[str] = None
    metadata_json: Optional[str] = None
    config_payload: Optional[str] = Field(default=None, description="平台配置文本，当前先原样存储")


class ManagedAgentCommBindingUpdateRequest(BaseModel):
    """更新宿主通讯渠道配置"""
    provider: Optional[ManagedAgentCommProvider] = Field(
        default=None,
        description="feishu/slack/telegram/wechat/email/webhook",
    )
    binding_key: Optional[str] = Field(default=None, description="平台账号或连接标识")
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    routing_policy_json: Optional[str] = None
    metadata_json: Optional[str] = None
    config_payload: Optional[str] = Field(default=None, description="平台配置文本，当前先原样存储")

    @model_validator(mode="after")
    def validate_nullable_fields(self):
        non_nullable_fields = {"provider", "binding_key", "enabled"}
        for field_name in non_nullable_fields:
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise ValueError(f"{field_name} 不能为 null")
        return self


class ManagedAgentCommBindingResponse(BaseModel):
    """宿主通讯渠道配置响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    provider: ManagedAgentCommProvider
    binding_key: str
    display_name: Optional[str] = None
    enabled: bool
    routing_policy_json: Optional[str] = None
    metadata_json: Optional[str] = None
    config_payload_masked: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ============================================================
# Bootstrap Token
# ============================================================


class ManagedAgentBootstrapTokenResponse(BaseModel):
    """引导 Token 响应"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    token: str
    purpose: ManagedAgentBootstrapPurpose
    expires_at: datetime
    created_at: datetime


class ManagedAgentBootstrapTokenCreateRequest(BaseModel):
    """创建引导 Token 请求"""
    purpose: ManagedAgentBootstrapPurpose = Field(description="download_script/register_runtime")
    ttl_seconds: int = Field(..., gt=0, description="Token 存活秒数")
    scope_json: Optional[str] = Field(default=None, description="附加范围信息 JSON")


class ManagedAgentBootstrapTokenCreateResponse(BaseModel):
    """创建引导 Token 响应，仅此处返回明文 token"""
    id: str
    managed_agent_id: str
    token: str
    purpose: ManagedAgentBootstrapPurpose
    scope_json: Optional[str] = None
    expires_at: datetime
    created_at: datetime


class ManagedAgentBootstrapTokenListItem(BaseModel):
    """引导 Token 列表项，不返回明文 token"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    token_masked: str = "仅创建时可见"
    purpose: ManagedAgentBootstrapPurpose
    scope_json: Optional[str] = None
    expires_at: datetime
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    is_valid: bool


class ManagedAgentBootstrapScriptResponse(BaseModel):
    """管理端脚本预览响应"""
    script: str
    register_token_id: str
    register_token_expires_at: datetime


class ManagedAgentOnboardingMessageResponse(BaseModel):
    """管理端接入说明响应"""
    message: str
    curl_command: str
    download_token_id: str
    download_token_expires_at: datetime
