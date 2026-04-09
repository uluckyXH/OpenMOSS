import api from '../../core/http';
import type {
  ManagedAgentPromptAsset,
  ManagedAgentPromptAssetInput,
  ManagedAgentPromptRenderPreview,
} from './types';

export const managedAgentPromptAssetApi = {
  get: (agentId: string) => api.get<ManagedAgentPromptAsset>(`/admin/managed-agents/${agentId}/prompt-asset`),
  update: (agentId: string, data: ManagedAgentPromptAssetInput) =>
    api.put<ManagedAgentPromptAsset>(`/admin/managed-agents/${agentId}/prompt-asset`, data),
  resetFromTemplate: (agentId: string) =>
    api.post<ManagedAgentPromptAsset>(`/admin/managed-agents/${agentId}/prompt-asset/reset-from-template`),
  renderPreview: (agentId: string) =>
    api.post<ManagedAgentPromptRenderPreview>(`/admin/managed-agents/${agentId}/prompt-asset/render-preview`),
};
