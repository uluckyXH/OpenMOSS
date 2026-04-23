"""
管理端 Agent 管理响应模型
"""
from datetime import datetime as dt
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


AgentRole = Literal["planner", "executor", "reviewer", "patrol"]
AgentStatus = Literal["active", "disabled"]


class AdminAgentWorkloadMixin(BaseModel):
    open_sub_task_count: int = 0
    assigned_count: int = 0
    in_progress_count: int = 0
    review_count: int = 0
    rework_count: int = 0
    blocked_count: int = 0


class AdminAgentListItem(AdminAgentWorkloadMixin):
    id: str
    name: str
    role: str
    description: str
    status: str
    total_score: int = 0
    rank: int = 1
    last_request_at: Optional[dt] = None
    last_activity_at: Optional[dt] = None
    created_at: Optional[dt] = None


class AdminAgentDetail(AdminAgentListItem):
    total_agents: int = 0
    reward_count: int = 0
    penalty_count: int = 0
    total_reward_records: int = 0
    done_count: int = 0
    cancelled_count: int = 0


class AdminAgentPageResponse(BaseModel):
    items: List[AdminAgentListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminAgentScoreLogItem(BaseModel):
    id: str
    agent_id: str
    sub_task_id: Optional[str] = None
    reason: str
    score_delta: int
    created_at: Optional[dt] = None


class AdminAgentScoreLogPageResponse(BaseModel):
    items: List[AdminAgentScoreLogItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminAgentActivityLogItem(BaseModel):
    id: str
    agent_id: str
    sub_task_id: Optional[str] = None
    action: str
    summary: str
    session_id: Optional[str] = None
    created_at: Optional[dt] = None


class AdminAgentActivityLogPageResponse(BaseModel):
    items: List[AdminAgentActivityLogItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminAgentRequestLogItem(BaseModel):
    id: str
    timestamp: Optional[dt] = None
    method: str
    path: str
    response_status: Optional[int] = None
    request_body: Optional[str] = None


class AdminAgentRequestLogPageResponse(BaseModel):
    items: List[AdminAgentRequestLogItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminAgentCreateRequest(BaseModel):
    name: str = Field(..., description="Agent 名称", max_length=100)
    role: AgentRole = Field(..., description="角色")
    description: str = Field("", description="职责简要")


class AdminAgentCreateResponse(BaseModel):
    id: str
    name: str
    role: str
    api_key: str
    message: str = "注册成功，请保存 API Key"


class AdminAgentStatusUpdateRequest(BaseModel):
    status: AgentStatus = Field(..., description="状态")


class AdminAgentUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="Agent 名称", max_length=100)
    role: Optional[AgentRole] = Field(None, description="角色类型")
    description: Optional[str] = Field(None, description="职责简要")


class AdminAgentWriteResponse(BaseModel):
    id: str
    name: str
    role: str
    description: str
    status: str
    total_score: int = 0


class AdminAgentResetKeyResponse(BaseModel):
    agent_id: str
    new_api_key: str
    message: str = "API Key 已重置"


class AdminAgentDeleteRequest(BaseModel):
    confirm_name: str = Field(..., description="输入 Agent 名称以确认删除")


class AdminAgentDeleteResponse(BaseModel):
    message: str = "Agent 已删除"
    agent_name: str
    sub_task_count: int = 0
    review_count: int = 0
    reward_count: int = 0
    activity_count: int = 0
    patrol_count: int = 0
    request_count: int = 0


class AdminAgentRelatedCountsResponse(BaseModel):
    agent_id: str
    agent_name: str
    sub_task_count: int = 0
    review_count: int = 0
    reward_count: int = 0
    activity_count: int = 0
    patrol_count: int = 0
    request_count: int = 0
