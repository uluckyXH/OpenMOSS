import api from '../core/http';

export const subTaskApi = {
  list: (params?: { task_id?: string; status?: string; page?: number; page_size?: number }) =>
    api.get('/sub-tasks', { params }),
  get: (id: string) => api.get(`/sub-tasks/${id}`),
};
