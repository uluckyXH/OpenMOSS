import api from '../core/http';
import type { AdminPageResponse } from '../core/types';

export interface AdminScoreSummary {
  total_agents: number
  positive_score_agents: number
  zero_score_agents: number
  negative_score_agents: number
  top_score: number
  average_score: number
  last_score_at: string | null
}

export interface AdminScoreLeaderboardItem {
  rank: number
  agent_id: string
  agent_name: string
  role: string
  status: string
  total_score: number
  reward_count: number
  penalty_count: number
  total_records: number
  last_score_at: string | null
  created_at: string | null
}

export interface AdminScoreLeaderboardParams {
  page?: number
  page_size?: number
  role?: string
  status?: string
  keyword?: string
  score_min?: number
  score_max?: number
  sort_by?: string
  sort_order?: string
}

export interface AdminScoreLogItem {
  id: string
  agent_id: string
  agent_name: string
  sub_task_id: string | null
  reason: string
  score_delta: number
  created_at: string | null
}

export interface AdminScoreLogParams {
  page?: number
  page_size?: number
  agent_id?: string
  sub_task_id?: string
  score_sign?: string
  keyword?: string
  sort_order?: string
}

export const adminScoreApi = {
  summary: () => api.get<AdminScoreSummary>('/admin/scores/summary'),
  leaderboard: (params?: AdminScoreLeaderboardParams) =>
    api.get<AdminPageResponse<AdminScoreLeaderboardItem>>('/admin/scores/leaderboard', { params }),
  logs: (params?: AdminScoreLogParams) =>
    api.get<AdminPageResponse<AdminScoreLogItem>>('/admin/scores/logs', { params }),
  adjust: (data: { agent_id: string; score_delta: number; reason: string; sub_task_id?: string }) =>
    api.post('/admin/scores/adjust', data),
};
