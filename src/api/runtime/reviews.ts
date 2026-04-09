import api from '../core/http';

export const reviewApi = {
  list: (params?: { sub_task_id?: string; page?: number; page_size?: number }) => api.get('/review-records', { params }),
  get: (id: string) => api.get(`/review-records/${id}`),
};
