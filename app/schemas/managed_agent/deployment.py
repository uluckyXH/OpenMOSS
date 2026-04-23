"""配置态 Agent 部署变更集与快照 Schema。"""

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


DeployScriptIntent = Literal["bootstrap", "sync"]
DeployChangeType = Literal["add", "update", "remove"]


class DeployScriptRequest(BaseModel):
    """部署脚本生成请求。"""

    script_intent: DeployScriptIntent
    prompt_artifact_keys: List[str] = Field(default_factory=list, description="语义资产 key 列表")
    schedule_ids: List[str] = Field(default_factory=list, description="定时任务 ID 列表")
    comm_binding_ids: List[str] = Field(default_factory=list, description="通讯绑定 ID 列表")
    register_ttl_seconds: int = Field(default=3600, ge=60, description="注册 token 有效期（秒），仅 bootstrap")
    download_ttl_seconds: int = Field(default=86400, ge=60, description="下载 token 有效期（秒），仅 bootstrap")


class DeployPreviewRequest(BaseModel):
    """部署变更预检请求（与 DeployScriptRequest 相同结构）。"""

    script_intent: DeployScriptIntent
    prompt_artifact_keys: List[str] = Field(default_factory=list)
    schedule_ids: List[str] = Field(default_factory=list)
    comm_binding_ids: List[str] = Field(default_factory=list)


class DeployChangesetItem(BaseModel):
    """变更集中的单个变更项。"""

    resource_type: Literal["prompt", "schedule", "comm_binding"]
    change_type: DeployChangeType
    resource_id: Optional[str] = None
    resource_key: Optional[str] = None
    label: str = Field(description="前端展示文本")
    enabled: Optional[bool] = None


class DeployChangeset(BaseModel):
    """完整变更集。"""

    items: List[DeployChangesetItem] = Field(default_factory=list)
    validation_errors: List[str] = Field(default_factory=list)
    is_valid: bool = True


class DeployPreviewResponse(BaseModel):
    """部署变更预检响应。"""

    script_intent: DeployScriptIntent
    changeset: DeployChangeset
    has_removals: bool = Field(default=False, description="是否包含待删除项")


class DeployReportRequest(BaseModel):
    """脚本执行结果回传请求。"""

    snapshot_id: str
    status: Literal["confirmed", "failed"]
    exit_code: Optional[int] = None
    last_stage: Optional[str] = None
    message: Optional[str] = None


class DeploySnapshotDismissRequest(BaseModel):
    """忽略已删除资源的清理提醒。"""

    schedule_ids: List[str] = Field(default_factory=list)
    comm_binding_ids: List[str] = Field(default_factory=list)
    prompt_artifact_keys: List[str] = Field(default_factory=list)


DeploymentSnapshotStatus = Literal["pending", "confirmed", "failed"]


class DeploymentSnapshotListItem(BaseModel):
    """部署快照列表项。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    managed_agent_id: str
    script_intent: DeployScriptIntent
    config_version: int
    snapshot_json: str
    status: str
    failure_detail_json: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime] = None
