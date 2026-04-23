"""
管理端任务查询响应模型
"""
from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field


class AdminTaskStatsMixin(BaseModel):
    module_count: int = 0
    sub_task_count: int = 0
    pending_count: int = 0
    assigned_count: int = 0
    in_progress_count: int = 0
    review_count: int = 0
    rework_count: int = 0
    blocked_count: int = 0
    done_count: int = 0
    cancelled_count: int = 0


class AdminTaskListItem(AdminTaskStatsMixin):
    id: str
    name: str
    description: str
    type: str
    status: str
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None


class AdminTaskDetail(AdminTaskListItem):
    pass


class AdminTaskPageResponse(BaseModel):
    items: List[AdminTaskListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminModuleStatsMixin(BaseModel):
    sub_task_count: int = 0
    pending_count: int = 0
    assigned_count: int = 0
    in_progress_count: int = 0
    review_count: int = 0
    rework_count: int = 0
    blocked_count: int = 0
    done_count: int = 0
    cancelled_count: int = 0


class AdminModuleListItem(AdminModuleStatsMixin):
    id: str
    task_id: str
    name: str
    description: str
    created_at: Optional[dt] = None


class AdminModuleDetail(AdminModuleListItem):
    task_name: str


class AdminModulePageResponse(BaseModel):
    items: List[AdminModuleListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminSubTaskListItem(BaseModel):
    id: str
    task_id: str
    task_name: str
    module_id: Optional[str] = None
    module_name: Optional[str] = None
    name: str
    description: str
    type: str
    status: str
    priority: str
    assigned_agent: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    current_session_id: Optional[str] = None
    rework_count: int = 0
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None
    completed_at: Optional[dt] = None


class AdminSubTaskDetail(AdminSubTaskListItem):
    deliverable: str
    acceptance: str


class AdminSubTaskPageResponse(BaseModel):
    items: List[AdminSubTaskListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False
