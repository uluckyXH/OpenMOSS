import api from '../core/http';

export const adminConfigApi = {
  get: () => api.get('/admin/config'),
  update: (data: Record<string, unknown>) => api.put('/admin/config', data),
  updatePassword: (oldPassword: string, newPassword: string) =>
    api.put('/admin/config/password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};
