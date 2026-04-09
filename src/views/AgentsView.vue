<script setup lang="ts">
import { ref } from 'vue';
import AgentListView from '@/components/agents/AgentListView.vue';
import AgentDetailView from '@/components/agents/AgentDetailView.vue';

// ─── 模式切换：列表 ↔ 详情 ───

const mode = ref<'list' | 'detail'>('list');
const selectedAgentId = ref<string | null>(null);

function openDetail(agentId: string) {
  selectedAgentId.value = agentId;
  mode.value = 'detail';
}

function goBackToList() {
  mode.value = 'list';
  selectedAgentId.value = null;
}
</script>

<template>
  <Transition name="view" mode="out-in" appear>
    <AgentListView v-if="mode === 'list'" key="list" @select="openDetail" />
    <AgentDetailView v-else-if="selectedAgentId" :key="selectedAgentId" :agent-id="selectedAgentId" @back="goBackToList"
      @deleted="goBackToList" />
  </Transition>
</template>

<style scoped>
.view-enter-active {
  transition: all 0.25s ease-out;
}

.view-leave-active {
  transition: all 0.15s ease-in;
}

.view-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.view-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
