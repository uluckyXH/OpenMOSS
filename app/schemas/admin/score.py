"""
管理端积分排行榜响应模型
"""
from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field


class AdminScoreSummaryResponse(BaseModel):
    total_agents: int = 0
    positive_score_agents: int = 0
    zero_score_agents: int = 0
    negative_score_agents: int = 0
    top_score: int = 0
    average_score: float = 0.0
    last_score_at: Optional[dt] = None


class AdminScoreLeaderboardItem(BaseModel):
    rank: int = 1
    agent_id: str
    agent_name: str
    role: str
    status: str
    total_score: int = 0
    reward_count: int = 0
    penalty_count: int = 0
    total_records: int = 0
    last_score_at: Optional[dt] = None
    created_at: Optional[dt] = None


class AdminScoreLeaderboardPageResponse(BaseModel):
    items: List[AdminScoreLeaderboardItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False


class AdminScoreAdjustRequest(BaseModel):
    agent_id: str
    score_delta: int
    reason: str
    sub_task_id: Optional[str] = None


class AdminScoreAdjustResponse(BaseModel):
    id: str
    agent_id: str
    sub_task_id: Optional[str] = None
    reason: str
    score_delta: int
    created_at: Optional[dt] = None
    current_total_score: int = 0


class AdminScoreLogItem(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    sub_task_id: Optional[str] = None
    reason: str
    score_delta: int
    created_at: Optional[dt] = None


class AdminScoreLogPageResponse(BaseModel):
    items: List[AdminScoreLogItem] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    has_more: bool = False
