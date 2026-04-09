<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue';
import { managedAgentApi, type ManagedAgentListItem } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ChevronLeft, Loader2, AlertCircle, Pencil, Trash2,
  Settings, FileText, Clock, MessageSquare, Rocket, Info,
  CheckCircle2, Circle, Lock,
} from 'lucide-vue-next';
import {
  formatRole, getRoleBadgeClass, getRoleBarClass,
  formatStatus, getStatusBadgeClass,
} from '@/composables/agents/useAgentFormatters';
import { useAgentReadiness, type TabReadiness } from '@/composables/agents/useAgentReadiness';

import BasicInfoTab from '@/components/agents/tabs/BasicInfoTab.vue';
import PlatformConfigTab from '@/components/agents/tabs/PlatformConfigTab.vue';
import PromptTab from '@/components/agents/tabs/PromptTab.vue';
import ScheduleTab from '@/components/agents/tabs/ScheduleTab.vue';
import CommBindingTab from '@/components/agents/tabs/CommBindingTab.vue';
import BootstrapTab from '@/components/agents/tabs/BootstrapTab.vue';
import AgentEditDialog from '@/components/agents/dialogs/AgentEditDialog.vue';
import AgentDeleteDialog from '@/components/agents/dialogs/AgentDeleteDialog.vue';

const props = defineProps<{ agentId: string }>();
const emit = defineEmits<{ back: []; deleted: [] }>();

const selectedAgent = ref<ManagedAgentListItem | null>(null);
const loadingDetail = ref(false);
const detailError = ref('');
const activeTab = ref('basic');

const showEditDialog = ref(false);
const showDeleteDialog = ref(false);

let detailRequestId = 0;

// ─── 就绪检测 ───
const { readiness, progress, loading: readinessLoading, refresh: refreshReadiness } =
  useAgentReadiness(() => props.agentId);

// ─── Tab 配置 ───
interface TabMeta {
  key: string;
  label: string;
  icon: typeof Info;
  readinessKey: keyof TabReadiness;
  prerequisiteLabel?: string; // 前置条件不满足时显示的提示
}

const tabsMeta: TabMeta[] = [
  { key: 'basic', label: '基础信息', icon: Info, readinessKey: 'basic' },
  { key: 'host', label: '平台配置', icon: Settings, readinessKey: 'host', prerequisiteLabel: '基础信息' },
  { key: 'prompt', label: 'Prompt', icon: FileText, readinessKey: 'prompt', prerequisiteLabel: '平台配置' },
  { key: 'schedule', label: '定时任务', icon: Clock, readinessKey: 'schedule', prerequisiteLabel: 'Prompt' },
  { key: 'comm', label: '通讯渠道', icon: MessageSquare, readinessKey: 'comm', prerequisiteLabel: 'Prompt' },
  { key: 'bootstrap', label: '部署接入', icon: Rocket, readinessKey: 'bootstrap', prerequisiteLabel: '平台配置 + Prompt' },
];

// 当前 Tab 是否就绪
const activeTabReady = computed(() => {
  const meta = tabsMeta.find(t => t.key === activeTab.value);
  return meta ? readiness.value[meta.readinessKey] : true;
});

// ─── 数据加载 ───
async function loadDetail(agentId: string) {
  const requestId = ++detailRequestId;
  loadingDetail.value = true;
  detailError.value = '';
  try {
    const res = await managedAgentApi.get(agentId);
    if (requestId !== detailRequestId) return;
    selectedAgent.value = res.data;
  } catch {
    if (requestId !== detailRequestId) return;
    detailError.value = '加载详情失败';
  } finally {
    if (requestId === detailRequestId) loadingDetail.value = false;
  }
}

onMounted(() => { void loadDetail(props.agentId); });
watch(() => props.agentId, (id) => { if (id) void loadDetail(id); });

function handleSaved() {
  void loadDetail(props.agentId);
  void refreshReadiness();
}

function handleDeleted() {
  emit('deleted');
}

// Tab 内容保存后刷新就绪状态
function onTabSaved() {
  void refreshReadiness();
}
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-3.5rem)]">
    <!-- 顶栏 -->
    <header class="shrink-0 border-b border-border/40 bg-background">
      <div class="max-w-5xl mx-auto px-6 py-2.5 flex items-center justify-between">
        <div class="flex items-center gap-3 min-w-0">
          <Button variant="ghost" size="sm" class="gap-1 text-muted-foreground shrink-0" @click="emit('back')">
            <ChevronLeft class="h-4 w-4" /> 返回
          </Button>
          <template v-if="selectedAgent">
            <div class="h-4 w-px bg-border/50" />
            <h1 class="text-sm font-semibold truncate">{{ selectedAgent.name }}</h1>
            <Badge variant="outline" class="text-[10px] shrink-0" :class="getRoleBadgeClass(selectedAgent.role)">
              {{ formatRole(selectedAgent.role) }}
            </Badge>
            <Badge variant="outline" class="text-[10px] shrink-0" :class="getStatusBadgeClass(selectedAgent.status)">
              {{ formatStatus(selectedAgent.status) }}
            </Badge>
          </template>
        </div>
        <div v-if="selectedAgent" class="flex gap-1.5 shrink-0">
          <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" @click="showEditDialog = true">
            <Pencil class="h-3 w-3" /> 编辑
          </Button>
          <Button variant="outline" size="sm"
            class="h-7 gap-1 text-xs text-rose-500 hover:text-rose-600 hover:bg-rose-50"
            @click="showDeleteDialog = true">
            <Trash2 class="h-3 w-3" /> 删除
          </Button>
        </div>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="flex-1 overflow-y-auto">
      <!-- 加载中 -->
      <div v-if="loadingDetail" class="flex items-center justify-center py-20">
        <Loader2 class="h-7 w-7 animate-spin text-muted-foreground" />
      </div>
      <!-- 错误 -->
      <div v-else-if="detailError" class="flex flex-col items-center py-20 text-muted-foreground">
        <AlertCircle class="h-7 w-7 mb-2 text-rose-400" />
        <p class="text-sm">{{ detailError }}</p>
      </div>
      <!-- 详情 -->
      <template v-else-if="selectedAgent">
        <div class="max-w-5xl mx-auto px-6 py-5 animate-slide-up">
          <!-- 简洁头卡 + 配置进度 -->
          <div class="rounded-xl border bg-card overflow-hidden mb-5">
            <div class="h-1" :class="getRoleBarClass(selectedAgent.role)" />
            <div class="p-5">
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0">
                  <p class="text-xs text-muted-foreground font-mono mb-1">{{ selectedAgent.slug }}</p>
                  <p v-if="selectedAgent.description" class="text-sm text-muted-foreground leading-relaxed max-w-lg">
                    {{ selectedAgent.description }}
                  </p>
                  <p v-else class="text-sm text-muted-foreground/40 italic">暂无描述</p>
                </div>
                <!-- 版本 + 进度 -->
                <div class="shrink-0 text-right space-y-2">
                  <div>
                    <div class="text-[11px] text-muted-foreground/50">配置版本</div>
                    <div class="text-sm font-medium tabular-nums mt-0.5">
                      v{{ selectedAgent.config_version }}
                      <template v-if="selectedAgent.deployed_config_version !== null">
                        <span class="text-muted-foreground/40 mx-0.5">→</span>
                        v{{ selectedAgent.deployed_config_version }}
                      </template>
                    </div>
                  </div>
                  <Badge v-if="selectedAgent.deployed_config_version !== null" variant="outline" class="text-[10px]"
                    :class="selectedAgent.needs_redeploy
                      ? 'text-amber-400 border-amber-500/20 bg-amber-500/5'
                      : 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5'">
                    {{ selectedAgent.needs_redeploy ? '需重新部署' : '已同步' }}
                  </Badge>
                </div>
              </div>

              <!-- 配置进度条 -->
              <div v-if="!readinessLoading" class="mt-4 pt-4 border-t border-border/30">
                <div class="flex items-center gap-3 mb-2">
                  <span class="text-[11px] text-muted-foreground/50 font-medium">配置进度</span>
                  <span class="text-[11px] tabular-nums"
                    :class="progress.done === progress.total ? 'text-emerald-400' : 'text-muted-foreground/50'">
                    {{ progress.done }} / {{ progress.total }}
                  </span>
                </div>
                <div class="flex gap-2">
                  <button v-for="tab in tabsMeta.slice(0, 3)" :key="tab.key"
                    class="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md transition-colors" :class="readiness[tab.readinessKey]
                      ? 'text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/10'
                      : 'text-muted-foreground/40 bg-muted/20 hover:bg-muted/30'" @click="activeTab = tab.key">
                    <CheckCircle2 v-if="readiness[tab.readinessKey]" class="h-3 w-3" />
                    <Circle v-else class="h-3 w-3" />
                    {{ tab.label }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Tab 面板 -->
          <Tabs v-model="activeTab" class="w-full">
            <TabsList class="bg-transparent border-b rounded-none w-full justify-start h-auto p-0 gap-0">
              <TabsTrigger v-for="tab in tabsMeta" :key="tab.key" :value="tab.key"
                class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none gap-1.5 text-xs px-4 py-2.5 relative">
                <component :is="tab.icon" class="h-3.5 w-3.5" />
                {{ tab.label }}
                <!-- Tab 就绪指示 -->
                <span v-if="readiness[tab.readinessKey]"
                  class="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <Lock v-else-if="tab.key !== 'basic' && !readiness[tab.readinessKey]"
                  class="h-2.5 w-2.5 text-muted-foreground/30 ml-0.5" />
              </TabsTrigger>
            </TabsList>

            <!-- 未就绪 Tab 的提示横幅 -->
            <div v-if="!activeTabReady && activeTab !== 'basic'"
              class="mt-4 rounded-lg border border-amber-500/20 bg-amber-500/5 px-4 py-3 flex items-center gap-2">
              <Lock class="h-4 w-4 text-amber-400 shrink-0" />
              <p class="text-xs text-amber-300/80">
                请先完成
                <strong class="text-amber-400">
                  {{tabsMeta.find(t => t.key === activeTab)?.prerequisiteLabel}}
                </strong>
                的配置，以启用此模块的编辑功能。
              </p>
            </div>

            <TabsContent value="basic" class="mt-5">
              <BasicInfoTab :agent="selectedAgent" />
            </TabsContent>
            <TabsContent value="host" class="mt-5">
              <PlatformConfigTab :agent-id="agentId" @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="prompt" class="mt-5">
              <PromptTab :agent-id="agentId" :disabled="!readiness.host" @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="schedule" class="mt-5">
              <ScheduleTab :agent-id="agentId" :disabled="!readiness.prompt" />
            </TabsContent>
            <TabsContent value="comm" class="mt-5">
              <CommBindingTab :agent-id="agentId" :disabled="!readiness.prompt" />
            </TabsContent>
            <TabsContent value="bootstrap" class="mt-5">
              <BootstrapTab :agent-id="agentId" :disabled="!readiness.bootstrap" />
            </TabsContent>
          </Tabs>
        </div>
      </template>
    </main>

    <!-- 弹窗 -->
    <AgentEditDialog v-model:open="showEditDialog" :agent="selectedAgent" @saved="handleSaved" />
    <AgentDeleteDialog v-model:open="showDeleteDialog" :agent="selectedAgent" @deleted="handleDeleted" />
  </div>
</template>
