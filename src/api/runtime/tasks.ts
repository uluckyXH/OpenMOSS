import api from '../core/http';

export const taskApi = {
  list: (params?: { page?: number; page_size?: number; status?: string }) => api.get('/tasks', { params }),
  get: (id: string) => api.get(`/tasks/${id}`),
  create: (data: { name: string; description?: string; type?: string }) => api.post('/tasks', data),
  update: (id: string, data: { name?: string; description?: string }) => api.put(`/tasks/${id}`, data),
  updateStatus: (id: string, status: string) => api.put(`/tasks/${id}/status`, { status }),
  cancel: (id: string) => api.delete(`/tasks/${id}`),
};
