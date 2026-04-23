"""
管理端审查记录响应模型
"""
from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field


class AdminReviewListItem(BaseModel):
    id: str
    task_id: str
    task_name: str
    module_id: Optional[str] = None
    module_name: Optional[str] = None
    sub_task_id: str
    sub_task_name: str
    reviewer_agent: str
    reviewer_agent_name: Optional[str] = None
    round: int
    result: str
    score: int
    issues: str = ""
    comment: str = ""
    rework_agent: Optional[str] = None
    rework_agent_name: Optional[str] = None
    created_at: Optional[dt] = None


class AdminReviewDetail(AdminReviewListItem):
    sub_task_description: str = ""
    sub_task_deliverable: str = ""
    sub_task_acceptance: str = ""


class AdminReviewPageResponse(BaseModel):
    items: List[AdminReviewListItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False
