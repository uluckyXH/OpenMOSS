import api from '../core/http';

export const logApi = {
  list: (params?: { sub_task_id?: string; action?: string; days?: number; limit?: number }) =>
    api.get('/logs', { params }),
};
