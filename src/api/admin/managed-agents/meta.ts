import api from '../../core/http';
import type {
  CommProviderSchema,
  CommProviderValidateResponse,
  HostPlatformMetaResponse,
  ManagedAgentCommProvider,
  PromptTemplateResponse,
} from './types';

export const managedAgentMetaApi = {
  getHostPlatforms: () =>
    api.get<HostPlatformMetaResponse>('/admin/managed-agents/meta/host-platforms'),
  getPromptTemplates: (role?: string) =>
    api.get<PromptTemplateResponse>('/admin/managed-agents/meta/prompt-templates', { params: role ? { role } : {} }),
  getCommProviderSchema: (hostPlatform: string, provider: ManagedAgentCommProvider) =>
    api.get<CommProviderSchema>(
      `/admin/managed-agents/meta/host-platforms/${hostPlatform}/comm-providers/${provider}/schema`
    ),
  validateCommProviderBinding: (hostPlatform: string, provider: ManagedAgentCommProvider, data: object) =>
    api.post<CommProviderValidateResponse>(
      `/admin/managed-agents/meta/host-platforms/${hostPlatform}/comm-providers/${provider}/validate`,
      data
    ),
};
