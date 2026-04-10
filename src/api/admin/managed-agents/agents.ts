import api from '../../core/http';
import type {
  ManagedAgentCreateInput,
  ManagedAgentDetail,
  ManagedAgentListParams,
  ManagedAgentPageResponse,
  ManagedAgentRuntimeApiKeyResetResponse,
  ManagedAgentUpdateInput,
} from './types';

export const managedAgentApi = {
  list: (params?: ManagedAgentListParams) =>
    api.get<ManagedAgentPageResponse>('/admin/managed-agents', { params }),
  create: (data: ManagedAgentCreateInput) => api.post<ManagedAgentDetail>('/admin/managed-agents', data),
  get: (agentId: string) => api.get<ManagedAgentDetail>(`/admin/managed-agents/${agentId}`),
  update: (agentId: string, data: ManagedAgentUpdateInput) =>
    api.put<ManagedAgentDetail>(`/admin/managed-agents/${agentId}`, data),
  resetRuntimeApiKey: (agentId: string) =>
    api.post<ManagedAgentRuntimeApiKeyResetResponse>(`/admin/managed-agents/${agentId}/runtime-api-key/reset`),
  remove: (agentId: string) => api.delete(`/admin/managed-agents/${agentId}`),
};
