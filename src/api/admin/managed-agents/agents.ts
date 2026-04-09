import api from '../../core/http';
import type {
  ManagedAgentCreateInput,
  ManagedAgentDetail,
  ManagedAgentListParams,
  ManagedAgentPageResponse,
  ManagedAgentUpdateInput,
} from './types';

export const managedAgentApi = {
  list: (params?: ManagedAgentListParams) =>
    api.get<ManagedAgentPageResponse>('/admin/managed-agents', { params }),
  create: (data: ManagedAgentCreateInput) => api.post<ManagedAgentDetail>('/admin/managed-agents', data),
  get: (agentId: string) => api.get<ManagedAgentDetail>(`/admin/managed-agents/${agentId}`),
  update: (agentId: string, data: ManagedAgentUpdateInput) =>
    api.put<ManagedAgentDetail>(`/admin/managed-agents/${agentId}`, data),
  remove: (agentId: string) => api.delete(`/admin/managed-agents/${agentId}`),
};
