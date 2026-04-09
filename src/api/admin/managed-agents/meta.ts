import api from '../../core/http';
import type { HostPlatformMetaResponse } from './types';

export const managedAgentMetaApi = {
  getHostPlatforms: () =>
    api.get<HostPlatformMetaResponse>('/admin/managed-agents/meta/host-platforms'),
};
