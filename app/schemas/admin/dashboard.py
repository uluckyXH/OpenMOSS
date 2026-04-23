"""
管理端仪表盘响应模型
"""
from datetime import datetime as dt
from typing import List, Optional

from pydantic import BaseModel, Field


class AdminDashboardCoreCards(BaseModel):
    open_task_count: int = 0
    active_sub_task_count: int = 0
    review_queue_count: int = 0
    blocked_sub_task_count: int = 0
    active_agent_count: int = 0
    today_completed_sub_task_count: int = 0


class AdminDashboardSecondaryCards(BaseModel):
    disabled_agent_count: int = 0
    today_review_count: int = 0
    today_rejected_review_count: int = 0
    today_reject_rate: float = 0.0
    today_net_score_delta: int = 0


class AdminDashboardTaskStatusDistribution(BaseModel):
    planning: int = 0
    active: int = 0
    in_progress: int = 0
    completed: int = 0
    archived: int = 0
    cancelled: int = 0


class AdminDashboardSubTaskStatusDistribution(BaseModel):
    pending: int = 0
    assigned: int = 0
    in_progress: int = 0
    review: int = 0
    rework: int = 0
    blocked: int = 0
    done: int = 0
    cancelled: int = 0


class AdminDashboardAgentStatusDistribution(BaseModel):
    active: int = 0
    disabled: int = 0


class AdminDashboardAgentRoleDistribution(BaseModel):
    planner: int = 0
    executor: int = 0
    reviewer: int = 0
    patrol: int = 0


class AdminDashboardReviewResultDistribution(BaseModel):
    approved: int = 0
    rejected: int = 0


class AdminDashboardDistributions(BaseModel):
    task_status_distribution: AdminDashboardTaskStatusDistribution = Field(
        default_factory=AdminDashboardTaskStatusDistribution
    )
    sub_task_status_distribution: AdminDashboardSubTaskStatusDistribution = Field(
        default_factory=AdminDashboardSubTaskStatusDistribution
    )
    agent_status_distribution: AdminDashboardAgentStatusDistribution = Field(
        default_factory=AdminDashboardAgentStatusDistribution
    )
    agent_role_distribution: AdminDashboardAgentRoleDistribution = Field(
        default_factory=AdminDashboardAgentRoleDistribution
    )
    review_result_distribution_7d: AdminDashboardReviewResultDistribution = Field(
        default_factory=AdminDashboardReviewResultDistribution
    )


class AdminDashboardOverviewResponse(BaseModel):
    generated_at: dt
    review_window_days: int = 7
    core_cards: AdminDashboardCoreCards = Field(default_factory=AdminDashboardCoreCards)
    secondary_cards: AdminDashboardSecondaryCards = Field(default_factory=AdminDashboardSecondaryCards)
    distributions: AdminDashboardDistributions = Field(default_factory=AdminDashboardDistributions)


class AdminDashboardSubTaskHighlightItem(BaseModel):
    id: str
    task_id: str
    task_name: str
    name: str
    status: str
    assigned_agent: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    updated_at: Optional[dt] = None
    rework_count: int = 0


class AdminDashboardAgentHighlightItem(BaseModel):
    id: str
    name: str
    role: str
    status: str
    total_score: int = 0
    open_sub_task_count: int = 0
    last_request_at: Optional[dt] = None
    last_activity_at: Optional[dt] = None


class AdminDashboardRecentReviewItem(BaseModel):
    id: str
    task_id: str
    task_name: str
    sub_task_id: str
    sub_task_name: str
    reviewer_agent: str
    reviewer_agent_name: Optional[str] = None
    result: str
    score: int
    created_at: Optional[dt] = None


class AdminDashboardHighlightsResponse(BaseModel):
    generated_at: dt
    limit: int = 5
    inactive_hours: int = 24
    blocked_sub_tasks: List[AdminDashboardSubTaskHighlightItem] = Field(default_factory=list)
    pending_review_sub_tasks: List[AdminDashboardSubTaskHighlightItem] = Field(default_factory=list)
    busy_agents: List[AdminDashboardAgentHighlightItem] = Field(default_factory=list)
    low_activity_agents: List[AdminDashboardAgentHighlightItem] = Field(default_factory=list)
    recent_reviews: List[AdminDashboardRecentReviewItem] = Field(default_factory=list)


class AdminDashboardCountTrendPoint(BaseModel):
    date: str
    count: int = 0


class AdminDashboardReviewTrendPoint(BaseModel):
    date: str
    total: int = 0
    approved: int = 0
    rejected: int = 0


class AdminDashboardScoreTrendPoint(BaseModel):
    date: str
    positive_score_delta: int = 0
    negative_score_delta: int = 0
    net_score_delta: int = 0


class AdminDashboardTrendsResponse(BaseModel):
    generated_at: dt
    days: int = 7
    start_date: str
    end_date: str
    sub_task_created_trend: List[AdminDashboardCountTrendPoint] = Field(default_factory=list)
    sub_task_completed_trend: List[AdminDashboardCountTrendPoint] = Field(default_factory=list)
    review_trend: List[AdminDashboardReviewTrendPoint] = Field(default_factory=list)
    score_delta_trend: List[AdminDashboardScoreTrendPoint] = Field(default_factory=list)
    request_trend: List[AdminDashboardCountTrendPoint] = Field(default_factory=list)
    activity_trend: List[AdminDashboardCountTrendPoint] = Field(default_factory=list)
