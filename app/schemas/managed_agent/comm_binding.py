"""配置态 Agent 通讯绑定 Schema。"""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .base import ManagedAgentCommProvider


class ManagedAgentCommBindingCreateRequest(BaseModel):
    """创建宿主通讯渠道配置。"""

    provider: ManagedAgentCommProvider = Field(description="feishu/slack/telegram/wechat/email/webhook")
    binding_key: str = Field(description="平台账号或连接标识")
    display_name: Optional[str] = None
    enabled: bool = True
    routing_policy_json: Optional[str] = None
    metadata_json: Optional[str] = None
    config_payload: Optional[str] = Field(default=None, description="平台配置文本，当前先原样存储")


class ManagedAgentCommBindingUpdateRequest(BaseModel):
    """更新宿主通讯渠道配置。"""

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
    """宿主通讯渠道配置响应。"""

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


class FeishuCommBindingCreateRequest(BaseModel):
    """创建 Feishu 结构化通讯绑定。"""

    account_id: Optional[str] = Field(default=None, description="OpenClaw 内部账号标识，留空时自动生成")
    app_id: str = Field(..., min_length=1, description="飞书 App ID")
    app_secret: str = Field(..., min_length=1, description="飞书 App Secret")
    account_name: Optional[str] = Field(default=None, description="账号备注名")
    enabled: bool = Field(default=True, description="是否启用")


class FeishuCommBindingUpdateRequest(BaseModel):
    """更新 Feishu 结构化通讯绑定（部分更新）。"""

    account_id: Optional[str] = Field(default=None, min_length=1, description="OpenClaw 内部账号标识（高级）")
    app_id: Optional[str] = Field(default=None, min_length=1)
    app_secret: Optional[str] = Field(default=None, min_length=1)
    account_name: Optional[str] = None
    enabled: Optional[bool] = None

    @model_validator(mode="after")
    def validate_nullable_fields(self):
        if "enabled" in self.model_fields_set and self.enabled is None:
            raise ValueError("enabled 不能为 null")
        return self


class FeishuCommBindingResponse(BaseModel):
    """Feishu 结构化通讯绑定响应。"""

    id: str
    provider: str = "feishu"
    account_id: str
    account_name: Optional[str] = None
    enabled: bool
    app_id_masked: str
    app_secret_masked: str
    created_at: datetime
    updated_at: datetime


class FeishuCommSchemaField(BaseModel):
    """飞书表单字段定义。"""

    key: str
    label: str
    type: str
    required: bool
    placeholder: Optional[str] = None
    description: Optional[str] = None
    sensitive: Optional[bool] = None
    default: Optional[Any] = None
    advanced: Optional[bool] = None


class FeishuCommSchemaResponse(BaseModel):
    """Feishu 通讯绑定 schema 发现响应。"""

    provider: str
    label: str
    description: str
    supports_multiple_bindings: bool
    fields: List[FeishuCommSchemaField]


class FeishuCommValidateRequest(BaseModel):
    """Feishu 通讯绑定预校验请求。"""

    account_id: Optional[str] = None
    app_id: Optional[str] = None
    app_secret: Optional[str] = None
    account_name: Optional[str] = None
    enabled: Optional[bool] = None


class FeishuCommValidateResponse(BaseModel):
    """飞书通讯绑定预校验响应。"""

    valid: bool
    errors: List[str] = Field(default_factory=list)


class FeishuCommSuggestResponse(BaseModel):
    """飞书通讯绑定建议默认值响应。"""

    account_id: Optional[str] = None
    host_agent_identifier: Optional[str] = None
    message: Optional[str] = None

