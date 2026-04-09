import api from '../core/http';

export const ruleApi = {
  list: (params?: { task_id?: string; sub_task_id?: string }) => api.get('/rules', { params }),
};
