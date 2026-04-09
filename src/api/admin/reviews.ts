import api from '../core/http';
import type { AdminPageResponse } from '../core/types';

export interface AdminReviewListItem {
  id: string
  task_id: string
  task_name: string
  module_id: string | null
  module_name: string | null
  sub_task_id: string
  sub_task_name: string
  reviewer_agent: string
  reviewer_agent_name: string | null
  round: number
  result: string
  score: number
  issues: string
  comment: string
  rework_agent: string | null
  rework_agent_name: string | null
  created_at: string | null
}

export interface AdminReviewDetail extends AdminReviewListItem {
  sub_task_description: string
  sub_task_deliverable: string
  sub_task_acceptance: string
}

export interface AdminReviewParams {
  page?: number
  page_size?: number
  task_id?: string
  sub_task_id?: string
  reviewer_agent?: string
  result?: string
  keyword?: string
  days?: number
  sort_order?: string
}

export const adminReviewApi = {
  list: (params?: AdminReviewParams) =>
    api.get<AdminPageResponse<AdminReviewListItem>>('/admin/review-records', { params }),
  get: (id: string) => api.get<AdminReviewDetail>(`/admin/review-records/${id}`),
};
