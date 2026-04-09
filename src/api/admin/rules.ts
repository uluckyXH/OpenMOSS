import api from '../core/http';

export const adminRuleApi = {
  list: (scope?: string) => api.get('/rules/list', { params: scope ? { scope } : undefined }),
  create: (data: { scope: string; content: string; task_id?: string; sub_task_id?: string }) =>
    api.post('/rules', data),
  update: (id: string, content: string) => api.put(`/rules/${id}`, { content }),
  delete: (id: string) => api.delete(`/rules/${id}`),
};
