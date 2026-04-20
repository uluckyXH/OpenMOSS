import api from '../../core/http';
import type {
  FeishuCommBinding,
  FeishuCommBindingCreateInput,
  FeishuCommBindingUpdateInput,
  FeishuCommSuggestResponse,
} from './types';

export const managedAgentFeishuCommBindingApi = {
  list: (agentId: string) =>
    api.get<FeishuCommBinding[]>(`/admin/managed-agents/${agentId}/comm-bindings-structured/feishu`),
  suggest: (agentId: string) =>
    api.get<FeishuCommSuggestResponse>(`/admin/managed-agents/${agentId}/comm-bindings-structured/feishu/suggest`),
  create: (agentId: string, data: FeishuCommBindingCreateInput) =>
    api.post<FeishuCommBinding>(`/admin/managed-agents/${agentId}/comm-bindings-structured/feishu`, data),
  update: (agentId: string, bindingId: string, data: FeishuCommBindingUpdateInput) =>
    api.put<FeishuCommBinding>(`/admin/managed-agents/${agentId}/comm-bindings-structured/feishu/${bindingId}`, data),
  remove: (agentId: string, bindingId: string) =>
    api.delete(`/admin/managed-agents/${agentId}/comm-bindings-structured/feishu/${bindingId}`),
};
