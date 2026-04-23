"""
管理端活动日志响应模型
"""
from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field


class AdminActivityLogItem(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    agent_role: str
    sub_task_id: Optional[str] = None
    action: str
    summary: str
    session_id: Optional[str] = None
    created_at: Optional[dt] = None


class AdminActivityLogPageResponse(BaseModel):
    items: List[AdminActivityLogItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False
