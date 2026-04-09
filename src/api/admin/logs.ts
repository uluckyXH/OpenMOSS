import api from '../core/http';
import type { AdminPageResponse } from '../core/types';

export interface AdminActivityLogItem {
  id: string
  agent_id: string
  agent_name: string
  agent_role: string
  sub_task_id: string | null
  action: string
  summary: string
  session_id: string | null
  created_at: string | null
}

export interface AdminLogParams {
  page?: number
  page_size?: number
  agent_id?: string
  action?: string
  sub_task_id?: string
  keyword?: string
  days?: number
  sort_order?: string
}

export const adminLogApi = {
  list: (params?: AdminLogParams) =>
    api.get<AdminPageResponse<AdminActivityLogItem>>('/admin/logs', { params }),
};
