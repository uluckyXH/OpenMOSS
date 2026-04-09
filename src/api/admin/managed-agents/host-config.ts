import api from '../../core/http';
import type { ManagedAgentHostConfig, ManagedAgentHostConfigInput } from './types';

export const managedAgentHostConfigApi = {
  get: (agentId: string) => api.get<ManagedAgentHostConfig>(`/admin/managed-agents/${agentId}/host-config`),
  update: (agentId: string, data: ManagedAgentHostConfigInput) =>
    api.put<ManagedAgentHostConfig>(`/admin/managed-agents/${agentId}/host-config`, data),
};
