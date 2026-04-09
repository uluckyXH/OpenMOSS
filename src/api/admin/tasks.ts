import api from '../core/http';
import type { AdminPageResponse } from '../core/types';

export interface AdminTaskItem {
  id: string
  name: string
  description: string
  type: string
  status: string
  module_count: number
  sub_task_count: number
  pending_count: number
  assigned_count: number
  in_progress_count: number
  review_count: number
  rework_count: number
  blocked_count: number
  done_count: number
  cancelled_count: number
  created_at: string | null
  updated_at: string | null
}

export type AdminTaskDetail = AdminTaskItem

export interface AdminModuleItem {
  id: string
  task_id: string
  name: string
  description: string
  sub_task_count: number
  pending_count: number
  assigned_count: number
  in_progress_count: number
  review_count: number
  rework_count: number
  blocked_count: number
  done_count: number
  cancelled_count: number
  created_at: string | null
}

export interface AdminSubTaskItem {
  id: string
  task_id: string
  task_name: string
  module_id: string | null
  module_name: string | null
  name: string
  description: string
  type: string
  status: string
  priority: string
  assigned_agent: string | null
  assigned_agent_name: string | null
  current_session_id: string | null
  rework_count: number
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
}

export interface AdminSubTaskDetail extends AdminSubTaskItem {
  deliverable: string
  acceptance: string
}

export interface AdminTaskListParams {
  page?: number
  page_size?: number
  status?: string
  type?: string
  keyword?: string
  sort_by?: string
  sort_order?: string
}

export interface AdminModuleListParams {
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface AdminSubTaskListParams {
  page?: number
  page_size?: number
  module_id?: string
  status?: string
  assigned_agent?: string
  priority?: string
  type?: string
  keyword?: string
  sort_by?: string
  sort_order?: string
}

export const adminTaskApi = {
  list: (params?: AdminTaskListParams) =>
    api.get<AdminPageResponse<AdminTaskItem>>('/admin/tasks', { params }),
  get: (id: string) => api.get<AdminTaskDetail>(`/admin/tasks/${id}`),
  listModules: (taskId: string, params?: AdminModuleListParams) =>
    api.get<AdminPageResponse<AdminModuleItem>>(`/admin/tasks/${taskId}/modules`, { params }),
  listSubTasks: (taskId: string, params?: AdminSubTaskListParams) =>
    api.get<AdminPageResponse<AdminSubTaskItem>>(`/admin/tasks/${taskId}/sub-tasks`, { params }),
  getSubTask: (subTaskId: string) => api.get<AdminSubTaskDetail>(`/admin/sub-tasks/${subTaskId}`),
};
