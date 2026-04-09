import { computed, ref } from 'vue';
import {
  managedAgentMetaApi,
  type HostPlatformMeta,
  type ManagedAgentDeploymentMode,
  type ManagedAgentHostAccessMode,
} from '@/api/client';
import { accessModeLabels, deployModeLabels } from './useAgentFormatters';

export function usePlatformMeta() {
  const platforms = ref<HostPlatformMeta[]>([]);

  async function loadPlatforms() {
    try {
      const res = await managedAgentMetaApi.getHostPlatforms();
      platforms.value = res.data.items;
    } catch {
      console.warn('Failed to load host platforms meta');
    }
  }

  function selectedPlatformFor(hostPlatformKey: string) {
    return platforms.value.find(p => p.key === hostPlatformKey) ?? null;
  }

  function deployModeOptionsFor(hostPlatformKey: string) {
    const platform = selectedPlatformFor(hostPlatformKey);
    const modes = platform?.deployment_modes ?? ['create_sub_agent', 'bind_existing_agent', 'bind_main_agent'];
    return modes.map(m => ({ value: m as ManagedAgentDeploymentMode, label: deployModeLabels[m] ?? m }));
  }

  function accessModeOptionsFor(hostPlatformKey: string) {
    const platform = selectedPlatformFor(hostPlatformKey);
    const modes = platform?.access_modes ?? ['local', 'remote'];
    return modes.map(m => ({ value: m as ManagedAgentHostAccessMode, label: accessModeLabels[m] ?? m }));
  }

  const platformOptions = computed(() =>
    platforms.value.map(p => ({ value: p.key, label: p.label }))
  );

  return { platforms, platformOptions, loadPlatforms, selectedPlatformFor, deployModeOptionsFor, accessModeOptionsFor };
}
