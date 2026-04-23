"""配置态 Agent Bootstrap Schema。"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


ManagedAgentBootstrapPurpose = Literal["download_script", "register_runtime"]


class ManagedAgentBootstrapTokenResponse(BaseModel):
    """引导 Token 响应。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    token: str
    purpose: ManagedAgentBootstrapPurpose
    expires_at: datetime
    created_at: datetime


class ManagedAgentBootstrapTokenCreateRequest(BaseModel):
    """创建引导 Token 请求。"""

    purpose: ManagedAgentBootstrapPurpose = Field(description="download_script/register_runtime")
    ttl_seconds: int = Field(..., gt=0, description="Token 存活秒数")
    scope_json: Optional[str] = Field(default=None, description="附加范围信息 JSON")


class ManagedAgentBootstrapTokenCreateResponse(BaseModel):
    """创建引导 Token 响应，仅此处返回明文 token。"""

    id: str
    managed_agent_id: str
    token: str
    purpose: ManagedAgentBootstrapPurpose
    scope_json: Optional[str] = None
    expires_at: datetime
    created_at: datetime


class ManagedAgentBootstrapTokenListItem(BaseModel):
    """引导 Token 列表项，不返回明文 token。"""

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
    """管理端脚本预览响应。"""

    script: str
    register_token_id: str
    register_token_expires_at: datetime


class ManagedAgentOnboardingMessageResponse(BaseModel):
    """管理端接入说明响应。"""

    message: str
    curl_command: str
    download_token_id: str
    download_token_expires_at: datetime

