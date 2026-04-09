import api from '../core/http';
import type { AdminPageResponse } from '../core/types';

export interface AdminAgentItem {
  id: string
  name: string
  role: string
  description: string
  status: string
  total_score: number
  rank: number
  open_sub_task_count: number
  assigned_count: number
  in_progress_count: number
  review_count: number
  rework_count: number
  blocked_count: number
  last_request_at: string | null
  last_activity_at: string | null
  created_at: string | null
}

export interface AdminAgentDetail extends AdminAgentItem {
  total_agents: number
  reward_count: number
  penalty_count: number
  total_reward_records: number
  done_count: number
  cancelled_count: number
}

export interface AdminAgentListParams {
  page?: number
  page_size?: number
  role?: string
  status?: string
  keyword?: string
  last_request_within_days?: number
  last_activity_within_days?: number
  sort_by?: string
  sort_order?: string
}

export const adminAgentApi = {
  list: (params?: AdminAgentListParams) =>
    api.get<AdminPageResponse<AdminAgentItem>>('/admin/agents', { params }),
  get: (agentId: string) => api.get<AdminAgentDetail>(`/admin/agents/${agentId}`),
  updateProfile: (
    agentId: string,
    data: { name?: string; role?: string; description?: string },
  ) => api.put(`/admin/agents/${agentId}`, data),
  updateStatus: (agentId: string, status: string) =>
    api.put(`/admin/agents/${agentId}/status`, { status }),
  scoreLogs: (
    agentId: string,
    params?: { page?: number; page_size?: number; sub_task_id?: string; sort_order?: string },
  ) => api.get(`/admin/agents/${agentId}/score-logs`, { params }),
  activityLogs: (
    agentId: string,
    params?: { page?: number; page_size?: number; action?: string; days?: number; sub_task_id?: string },
  ) => api.get(`/admin/agents/${agentId}/activity-logs`, { params }),
  requestLogs: (
    agentId: string,
    params?: { page?: number; page_size?: number; days?: number; method?: string; path_keyword?: string },
  ) => api.get(`/admin/agents/${agentId}/request-logs`, { params }),
  relatedCounts: (agentId: string) => api.get(`/admin/agents/${agentId}/related-counts`),
  deleteAgent: (agentId: string, confirmName: string) =>
    api.delete(`/admin/agents/${agentId}`, { data: { confirm_name: confirmName } }),
};
