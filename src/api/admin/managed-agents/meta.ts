import api from '../../core/http';
import type { HostPlatformMetaResponse, PromptTemplateResponse } from './types';

export const managedAgentMetaApi = {
  getHostPlatforms: () =>
    api.get<HostPlatformMetaResponse>('/admin/managed-agents/meta/host-platforms'),
  getPromptTemplates: (role?: string) =>
    api.get<PromptTemplateResponse>('/admin/managed-agents/meta/prompt-templates', { params: role ? { role } : {} }),
};
