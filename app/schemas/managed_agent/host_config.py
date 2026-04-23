"""配置态 Agent 宿主配置 Schema。"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ManagedAgentHostConfigRequest(BaseModel):
    """创建/更新宿主平台配置。"""

    host_agent_identifier: Optional[str] = None
    workdir_path: Optional[str] = None
    host_config_payload: Optional[str] = Field(default=None, description="明文配置文本，当前先原样存储")
    host_metadata_json: Optional[str] = None


class ManagedAgentHostConfigResponse(BaseModel):
    """宿主平台配置响应。"""

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

