import api from '../../core/http';
import type {
  ManagedAgentBootstrapScriptParams,
  ManagedAgentBootstrapScriptResponse,
  ManagedAgentBootstrapTokenCreateInput,
  ManagedAgentBootstrapTokenCreateResponse,
  ManagedAgentBootstrapTokenListItem,
  ManagedAgentOnboardingMessageParams,
  ManagedAgentOnboardingMessageResponse,
} from './types';

function buildBootstrapParams(
  params?: ManagedAgentBootstrapScriptParams | ManagedAgentOnboardingMessageParams,
): URLSearchParams | undefined {
  if (!params) {
    return undefined;
  }
  const searchParams = new URLSearchParams();
  if (params.selected_artifacts) {
    for (const value of params.selected_artifacts) {
      searchParams.append('selected_artifacts', value);
    }
  }
  if (params.include_schedule !== undefined) {
    searchParams.append('include_schedule', String(params.include_schedule));
  }
  if (params.include_comm_bindings !== undefined) {
    searchParams.append('include_comm_bindings', String(params.include_comm_bindings));
  }
  if ('register_ttl_seconds' in params && params.register_ttl_seconds !== undefined) {
    searchParams.append('register_ttl_seconds', String(params.register_ttl_seconds));
  }
  if ('bundle_ttl_seconds' in params && params.bundle_ttl_seconds !== undefined) {
    searchParams.append('bundle_ttl_seconds', String(params.bundle_ttl_seconds));
  }
  if ('download_ttl_seconds' in params && params.download_ttl_seconds !== undefined) {
    searchParams.append('download_ttl_seconds', String(params.download_ttl_seconds));
  }
  return searchParams;
}

export const managedAgentBootstrapApi = {
  createToken: (agentId: string, data: ManagedAgentBootstrapTokenCreateInput) =>
    api.post<ManagedAgentBootstrapTokenCreateResponse>(`/admin/managed-agents/${agentId}/bootstrap-tokens`, data),
  listTokens: (agentId: string) =>
    api.get<ManagedAgentBootstrapTokenListItem[]>(`/admin/managed-agents/${agentId}/bootstrap-tokens`),
  revokeToken: (agentId: string, tokenId: string) =>
    api.delete(`/admin/managed-agents/${agentId}/bootstrap-tokens/${tokenId}`),
  getBootstrapScript: (agentId: string, params?: ManagedAgentBootstrapScriptParams) =>
    api.get<ManagedAgentBootstrapScriptResponse>(`/admin/managed-agents/${agentId}/bootstrap-script`, {
      params: buildBootstrapParams(params),
      paramsSerializer: (value) => value?.toString() ?? '',
    }),
  getOnboardingMessage: (agentId: string, params?: ManagedAgentOnboardingMessageParams) =>
    api.get<ManagedAgentOnboardingMessageResponse>(`/admin/managed-agents/${agentId}/onboarding-message`, {
      params: buildBootstrapParams(params),
      paramsSerializer: (value) => value?.toString() ?? '',
    }),
};
