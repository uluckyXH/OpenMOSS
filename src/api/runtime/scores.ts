import api from '../core/http';

export const scoreApi = {
  leaderboard: () => api.get('/scores/leaderboard'),
  agentScore: (agentId: string) => api.get(`/scores/${agentId}`),
  agentLogs: (agentId: string, params?: { page?: number; page_size?: number }) =>
    api.get(`/scores/${agentId}/logs`, { params }),
  adjust: (data: { agent_id: string; score_delta: number; reason: string; sub_task_id?: string }) =>
    api.post('/scores/adjust', data),
};
