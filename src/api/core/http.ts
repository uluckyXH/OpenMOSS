import axios from 'axios';
import { useAuthStore } from '@/stores/auth';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 10000,
});

api.interceptors.request.use((config) => {
  const auth = useAuthStore();
  if (auth.token) {
    config.headers = config.headers ?? {};
    config.headers['X-Admin-Token'] = auth.token;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 403 && !error.config?.url?.includes('/admin/login')) {
      const auth = useAuthStore();
      auth.logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export default api;
