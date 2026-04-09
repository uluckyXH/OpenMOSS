import api from '../core/http';

export const adminApi = {
  login: (password: string) => api.post('/admin/login', { password }),
  resetKey: (agentId: string) => api.post(`/admin/agents/${agentId}/reset-key`),
};
