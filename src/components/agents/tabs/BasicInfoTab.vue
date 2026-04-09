<script setup lang="ts">
import type { ManagedAgentDetail } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import {
  accessModeLabels,
  formatDate,
  formatDeployMode,
} from '@/composables/agents/useAgentFormatters';

defineProps<{
  agent: ManagedAgentDetail;
}>();

const accessModeDescriptions: Record<string, string> = {
  local: '共享当前主力平台的公共工作目录和平台配置',
  remote: '独立外部平台，需要单独接入',
};
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">Slug</div>
        <div class="text-sm font-mono break-all">{{ agent.slug }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">Agent 平台</div>
        <div class="text-sm">{{ agent.host_platform }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">部署模式</div>
        <div class="text-sm">{{ formatDeployMode(agent.deployment_mode) }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">平台归属</div>
        <div class="text-sm">{{ accessModeLabels[agent.host_access_mode] || agent.host_access_mode }}</div>
        <p class="mt-1 text-xs text-muted-foreground/60">
          {{ accessModeDescriptions[agent.host_access_mode] || '—' }}
        </p>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">关联运行态 Agent</div>
        <div class="text-sm font-mono break-all">{{ agent.runtime_agent_id ?? '未关联' }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">创建时间</div>
        <div class="text-sm">{{ formatDate(agent.created_at) }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-[11px] text-muted-foreground/60 mb-1">更新时间</div>
        <div class="text-sm">{{ formatDate(agent.updated_at) }}</div>
      </div>
    </div>

    <div class="rounded-xl border bg-card/50 p-4">
      <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div class="text-[11px] text-muted-foreground/60 mb-1">配置版本</div>
          <div class="text-sm font-medium tabular-nums">
            配置 v{{ agent.config_version }}
            <template v-if="agent.deployed_config_version !== null">
              <span class="mx-1 text-muted-foreground/50">→</span>
              已部署 v{{ agent.deployed_config_version }}
            </template>
            <span v-else class="text-muted-foreground/60"> · 尚未部署</span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground/60">
            {{ agent.needs_redeploy ? '当前配置有变更，发布前需要重新部署。' : '当前已部署版本与配置版本一致。' }}
          </p>
        </div>

        <Badge
          variant="outline"
          class="w-fit text-xs"
          :class="agent.needs_redeploy
            ? 'border-amber-500/20 bg-amber-500/10 text-amber-400'
            : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'"
        >
          {{ agent.needs_redeploy ? '需重新部署' : '已同步' }}
        </Badge>
      </div>
    </div>
  </div>
</template>
