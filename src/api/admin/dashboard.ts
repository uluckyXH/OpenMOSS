import api from '../core/http';

export interface DashboardCoreCards {
  open_task_count: number
  active_sub_task_count: number
  review_queue_count: number
  blocked_sub_task_count: number
  active_agent_count: number
  today_completed_sub_task_count: number
}

export interface DashboardSecondaryCards {
  disabled_agent_count: number
  today_review_count: number
  today_rejected_review_count: number
  today_reject_rate: number
  today_net_score_delta: number
}

export interface DashboardDistributions {
  task_status_distribution: Record<string, number>
  sub_task_status_distribution: Record<string, number>
  agent_status_distribution: Record<string, number>
  agent_role_distribution: Record<string, number>
  review_result_distribution_7d: Record<string, number>
}

export interface DashboardOverview {
  generated_at: string
  review_window_days: number
  core_cards: DashboardCoreCards
  secondary_cards: DashboardSecondaryCards
  distributions: DashboardDistributions
}

export interface HighlightSubTask {
  id: string
  task_id: string
  task_name: string
  name: string
  status: string
  assigned_agent: string | null
  assigned_agent_name: string | null
  updated_at: string | null
  rework_count: number
}

export interface HighlightAgent {
  id: string
  name: string
  role: string
  status: string
  total_score: number
  open_sub_task_count: number
  last_request_at: string | null
  last_activity_at: string | null
}

export interface HighlightReview {
  id: string
  task_id: string
  task_name: string
  sub_task_id: string
  sub_task_name: string
  reviewer_agent: string
  reviewer_agent_name: string | null
  result: string
  score: number
  created_at: string | null
}

export interface DashboardHighlights {
  generated_at: string
  limit: number
  inactive_hours: number
  blocked_sub_tasks: HighlightSubTask[]
  pending_review_sub_tasks: HighlightSubTask[]
  busy_agents: HighlightAgent[]
  low_activity_agents: HighlightAgent[]
  recent_reviews: HighlightReview[]
}

export interface TrendPoint {
  date: string
  count: number
}

export interface ReviewTrendPoint {
  date: string
  total: number
  approved: number
  rejected: number
}

export interface ScoreTrendPoint {
  date: string
  positive_score_delta: number
  negative_score_delta: number
  net_score_delta: number
}

export interface DashboardTrends {
  generated_at: string
  days: number
  start_date: string
  end_date: string
  sub_task_created_trend: TrendPoint[]
  sub_task_completed_trend: TrendPoint[]
  review_trend: ReviewTrendPoint[]
  score_delta_trend: ScoreTrendPoint[]
  request_trend: TrendPoint[]
  activity_trend: TrendPoint[]
}

export const adminDashboardApi = {
  overview: () => api.get<DashboardOverview>('/admin/dashboard/overview'),
  highlights: (params?: { limit?: number; inactive_hours?: number }) =>
    api.get<DashboardHighlights>('/admin/dashboard/highlights', { params }),
  trends: (params?: { days?: number }) => api.get<DashboardTrends>('/admin/dashboard/trends', { params }),
};
