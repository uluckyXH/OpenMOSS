<script setup lang="ts">
import type { ManagedAgentListItem } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import {
  formatRole, getRoleBadgeClass, getRoleBarClass,
  formatStatus, getStatusDotClass,
  formatDeployMode, formatDate,
} from '@/composables/agents/useAgentFormatters';

defineProps<{
  agent: ManagedAgentListItem;
}>();

const emit = defineEmits<{
  select: [agentId: string];
}>();
</script>

<template>
  <div
    class="group relative rounded-xl border bg-card transition-all duration-200 hover:shadow-lg hover:shadow-primary/5 hover:border-primary/30 cursor-pointer overflow-hidden"
    @click="emit('select', agent.id)">
    <!-- 角色色条 -->
    <div class="h-1" :class="getRoleBarClass(agent.role)" />

    <div class="p-4 space-y-3">
      <!-- 名称 + 角色 -->
      <div class="flex items-start justify-between gap-2">
        <div class="min-w-0">
          <h3 class="font-medium text-sm truncate">{{ agent.name }}</h3>
          <p class="text-xs text-muted-foreground font-mono mt-0.5">{{ agent.slug }}</p>
        </div>
        <Badge variant="outline" class="shrink-0 text-[10px]" :class="getRoleBadgeClass(agent.role)">
          {{ formatRole(agent.role) }}
        </Badge>
      </div>

      <!-- 状态 + 部署模式 -->
      <div class="flex items-center gap-2 flex-wrap">
        <div class="flex items-center gap-1.5">
          <span class="h-1.5 w-1.5 rounded-full" :class="getStatusDotClass(agent.status)" />
          <span class="text-xs text-muted-foreground">{{ formatStatus(agent.status) }}</span>
        </div>
        <Badge variant="outline" class="text-[10px] text-muted-foreground">
          {{ formatDeployMode(agent.deployment_mode) }}
        </Badge>
      </div>

      <!-- 平台 + 版本 -->
      <div class="flex items-center justify-between text-xs text-muted-foreground/60">
        <span>{{ agent.host_platform }}</span>
        <span>v{{ agent.config_version }}
          <template v-if="agent.deployed_config_version !== null">
            → v{{ agent.deployed_config_version }}
            <span :class="agent.needs_redeploy ? 'text-amber-400' : 'text-emerald-400'">
              {{ agent.needs_redeploy ? '⚠' : '✓' }}
            </span>
          </template>
        </span>
      </div>

      <!-- 时间 -->
      <div class="text-[11px] text-muted-foreground/40">
        {{ formatDate(agent.updated_at) }}
      </div>
    </div>
  </div>
</template>
