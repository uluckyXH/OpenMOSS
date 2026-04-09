import api from '../core/http';

export const agentApi = {
  list: (params?: { role?: string }) => api.get('/agents', { params }),
  get: (id: string) => api.get(`/agents/${id}`),
};
