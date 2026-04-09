import api from '../../core/http';
import type {
  ManagedAgentCommBinding,
  ManagedAgentCommBindingCreateInput,
  ManagedAgentCommBindingUpdateInput,
} from './types';

export const managedAgentCommBindingApi = {
  list: (agentId: string) => api.get<ManagedAgentCommBinding[]>(`/admin/managed-agents/${agentId}/comm-bindings`),
  create: (agentId: string, data: ManagedAgentCommBindingCreateInput) =>
    api.post<ManagedAgentCommBinding>(`/admin/managed-agents/${agentId}/comm-bindings`, data),
  update: (agentId: string, bindingId: string, data: ManagedAgentCommBindingUpdateInput) =>
    api.put<ManagedAgentCommBinding>(`/admin/managed-agents/${agentId}/comm-bindings/${bindingId}`, data),
  remove: (agentId: string, bindingId: string) =>
    api.delete(`/admin/managed-agents/${agentId}/comm-bindings/${bindingId}`),
};
