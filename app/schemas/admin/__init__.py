"""
管理端 Schema 子包 — 汇总 re-export
"""
from app.schemas.admin.agent import (
    AgentRole,
    AgentStatus,
    AdminAgentWorkloadMixin,
    AdminAgentListItem,
    AdminAgentDetail,
    AdminAgentPageResponse,
    AdminAgentScoreLogItem,
    AdminAgentScoreLogPageResponse,
    AdminAgentActivityLogItem,
    AdminAgentActivityLogPageResponse,
    AdminAgentRequestLogItem,
    AdminAgentRequestLogPageResponse,
    AdminAgentCreateRequest,
    AdminAgentCreateResponse,
    AdminAgentStatusUpdateRequest,
    AdminAgentUpdateRequest,
    AdminAgentWriteResponse,
    AdminAgentResetKeyResponse,
    AdminAgentDeleteRequest,
    AdminAgentDeleteResponse,
    AdminAgentRelatedCountsResponse,
)
from app.schemas.admin.dashboard import (
    AdminDashboardCoreCards,
    AdminDashboardSecondaryCards,
    AdminDashboardTaskStatusDistribution,
    AdminDashboardSubTaskStatusDistribution,
    AdminDashboardAgentStatusDistribution,
    AdminDashboardAgentRoleDistribution,
    AdminDashboardReviewResultDistribution,
    AdminDashboardDistributions,
    AdminDashboardOverviewResponse,
    AdminDashboardSubTaskHighlightItem,
    AdminDashboardAgentHighlightItem,
    AdminDashboardRecentReviewItem,
    AdminDashboardHighlightsResponse,
    AdminDashboardCountTrendPoint,
    AdminDashboardReviewTrendPoint,
    AdminDashboardScoreTrendPoint,
    AdminDashboardTrendsResponse,
)
from app.schemas.admin.log import (
    AdminActivityLogItem,
    AdminActivityLogPageResponse,
)
from app.schemas.admin.review import (
    AdminReviewListItem,
    AdminReviewDetail,
    AdminReviewPageResponse,
)
from app.schemas.admin.score import (
    AdminScoreSummaryResponse,
    AdminScoreLeaderboardItem,
    AdminScoreLeaderboardPageResponse,
    AdminScoreAdjustRequest,
    AdminScoreAdjustResponse,
    AdminScoreLogItem,
    AdminScoreLogPageResponse,
)
from app.schemas.admin.task import (
    AdminTaskStatsMixin,
    AdminTaskListItem,
    AdminTaskDetail,
    AdminTaskPageResponse,
    AdminModuleStatsMixin,
    AdminModuleListItem,
    AdminModuleDetail,
    AdminModulePageResponse,
    AdminSubTaskListItem,
    AdminSubTaskDetail,
    AdminSubTaskPageResponse,
)

__all__ = [
    # agent
    "AgentRole", "AgentStatus",
    "AdminAgentWorkloadMixin", "AdminAgentListItem", "AdminAgentDetail",
    "AdminAgentPageResponse", "AdminAgentScoreLogItem", "AdminAgentScoreLogPageResponse",
    "AdminAgentActivityLogItem", "AdminAgentActivityLogPageResponse",
    "AdminAgentRequestLogItem", "AdminAgentRequestLogPageResponse",
    "AdminAgentCreateRequest", "AdminAgentCreateResponse",
    "AdminAgentStatusUpdateRequest", "AdminAgentUpdateRequest", "AdminAgentWriteResponse",
    "AdminAgentResetKeyResponse", "AdminAgentDeleteRequest", "AdminAgentDeleteResponse",
    "AdminAgentRelatedCountsResponse",
    # dashboard
    "AdminDashboardCoreCards", "AdminDashboardSecondaryCards",
    "AdminDashboardTaskStatusDistribution", "AdminDashboardSubTaskStatusDistribution",
    "AdminDashboardAgentStatusDistribution", "AdminDashboardAgentRoleDistribution",
    "AdminDashboardReviewResultDistribution", "AdminDashboardDistributions",
    "AdminDashboardOverviewResponse", "AdminDashboardSubTaskHighlightItem",
    "AdminDashboardAgentHighlightItem", "AdminDashboardRecentReviewItem",
    "AdminDashboardHighlightsResponse", "AdminDashboardCountTrendPoint",
    "AdminDashboardReviewTrendPoint", "AdminDashboardScoreTrendPoint",
    "AdminDashboardTrendsResponse",
    # log
    "AdminActivityLogItem", "AdminActivityLogPageResponse",
    # review
    "AdminReviewListItem", "AdminReviewDetail", "AdminReviewPageResponse",
    # score
    "AdminScoreSummaryResponse", "AdminScoreLeaderboardItem", "AdminScoreLeaderboardPageResponse",
    "AdminScoreAdjustRequest", "AdminScoreAdjustResponse",
    "AdminScoreLogItem", "AdminScoreLogPageResponse",
    # task
    "AdminTaskStatsMixin", "AdminTaskListItem", "AdminTaskDetail", "AdminTaskPageResponse",
    "AdminModuleStatsMixin", "AdminModuleListItem", "AdminModuleDetail", "AdminModulePageResponse",
    "AdminSubTaskListItem", "AdminSubTaskDetail", "AdminSubTaskPageResponse",
]
