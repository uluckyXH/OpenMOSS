<script setup lang="ts">
import { onMounted, ref, watch, computed } from 'vue';
import { managedAgentApi, type ManagedAgentListItem } from '@/api/client';
import { usePlatformMeta } from '@/composables/agents/usePlatformMeta';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  ChevronLeft, Loader2, AlertCircle, Pencil, Trash2,
  Settings, FileText, Clock, MessageSquare, Rocket, Info, History,
  CheckCircle2, Circle, Lock, AlertTriangle,
} from 'lucide-vue-next';
import {
  formatRole, getRoleBadgeClass,
  formatStatus, getStatusBadgeClass,
} from '@/composables/agents/useAgentFormatters';
import { useAgentReadiness, type TabReadiness } from '@/composables/agents/useAgentReadiness';

import BasicInfoTab from '@/components/agents/tabs/BasicInfoTab.vue';
import PlatformConfigTab from '@/components/agents/tabs/PlatformConfigTab.vue';
import PromptTab from '@/components/agents/tabs/PromptTab.vue';
import ScheduleTab from '@/components/agents/tabs/ScheduleTab.vue';
import CommBindingTab from '@/components/agents/tabs/CommBindingTab.vue';
import BootstrapTab from '@/components/agents/tabs/BootstrapTab.vue';
import DeployHistoryTab from '@/components/agents/tabs/DeployHistoryTab.vue';
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

// ─── Tab 子组件 ref（用于未保存提醒） ───
const platformConfigTabRef = ref<InstanceType<typeof PlatformConfigTab> | null>(null);
const promptTabRef = ref<InstanceType<typeof PromptTab> | null>(null);

// ─── 未保存切换确认 ───
const pendingTab = ref<string | null>(null);
const showUnsavedDialog = ref(false);

function isCurrentTabEditing(): boolean {
  if (activeTab.value === 'host') return platformConfigTabRef.value?.editing ?? false;
  if (activeTab.value === 'prompt') return promptTabRef.value?.editing ?? false;
  return false;
}

function tryChangeTab(tabKey: string) {
  if (tabKey === activeTab.value) return;
  if (isCurrentTabEditing()) {
    pendingTab.value = tabKey;
    showUnsavedDialog.value = true;
    return;
  }
  activeTab.value = tabKey;
}

function confirmDiscard() {
  // 让子组件取消编辑态
  if (activeTab.value === 'host') platformConfigTabRef.value?.cancelEdit();
  if (activeTab.value === 'prompt') promptTabRef.value?.cancelEdit();
  // 切到目标 Tab
  if (pendingTab.value) activeTab.value = pendingTab.value;
  pendingTab.value = null;
  showUnsavedDialog.value = false;
}

function cancelDiscard() {
  pendingTab.value = null;
  showUnsavedDialog.value = false;
}

let detailRequestId = 0;

// ─── 就绪检测（从 agent.readiness 直接读取，无额外请求） ───
const { readiness, progress, raw: rawReadiness } = useAgentReadiness(selectedAgent);

// ─── 平台 Meta（用于 capabilities 过滤和传递 hostPlatform） ───
const { platforms, loadPlatforms } = usePlatformMeta();
const currentPlatform = computed(() => selectedAgent.value?.host_platform ?? 'openclaw');
const currentCapabilities = computed(() =>
  platforms.value.find(p => p.key === currentPlatform.value)?.capabilities ?? null
);



// ─── Tab 配置 ───
interface TabMeta {
  key: string;
  label: string;
  icon: typeof Info;
  readinessKey: keyof TabReadiness;
  required: boolean;
  /** 此 Tab 的编辑功能是否可用（前置条件是否满足） */
  isEditable: (r: TabReadiness) => boolean;
  prerequisiteLabel?: string; // 前置条件不满足时显示的提示
}

const tabsMeta: TabMeta[] = [
  {
    key: 'basic', label: '基础信息', icon: Info, readinessKey: 'basic', required: true,
    isEditable: () => true
  },
  {
    key: 'host', label: '平台配置', icon: Settings, readinessKey: 'host', required: true,
    isEditable: () => true
  }, // 前置 = basic，始终满足
  {
    key: 'prompt', label: 'Prompt', icon: FileText, readinessKey: 'prompt', required: false,
    isEditable: (r) => r.host, prerequisiteLabel: '平台配置'
  },
  {
    key: 'schedule', label: '定时任务', icon: Clock, readinessKey: 'schedule', required: false,
    isEditable: (r) => r.host, prerequisiteLabel: '平台配置'
  },
  {
    key: 'comm', label: '通讯渠道', icon: MessageSquare, readinessKey: 'comm', required: false,
    isEditable: (r) => r.host, prerequisiteLabel: '平台配置'
  },
  {
    key: 'bootstrap', label: '部署接入', icon: Rocket, readinessKey: 'bootstrap', required: false,
    isEditable: (r) => r.host, prerequisiteLabel: '平台配置'
  },
  {
    key: 'deploy-history', label: '部署历史', icon: History, readinessKey: 'bootstrap', required: false,
    isEditable: () => true
  },
];

const requiredTabs = tabsMeta.filter(t => t.required);
const optionalTabs = tabsMeta.filter(t => !t.required);

// 根据 capabilities 过滤可见 Tab
const visibleRequiredTabs = computed(() =>
  requiredTabs.filter(t => isTabVisible(t.key))
);
const visibleOptionalTabs = computed(() =>
  optionalTabs.filter(t => isTabVisible(t.key))
);

function isTabVisible(tabKey: string) {
  const caps = currentCapabilities.value;
  if (!caps) return true; // 无 meta 时全部显示
  switch (tabKey) {
    case 'schedule': return caps.schedule !== false;
    case 'comm': return caps.comm_binding !== false;
    case 'bootstrap': return caps.bootstrap_script !== false;
    case 'deploy-history': return caps.bootstrap_script !== false;
    default: return true;
  }
}

// 当前 Tab 是否可编辑（前置条件是否满足）
const activeTabEditable = computed(() => {
  const meta = tabsMeta.find(t => t.key === activeTab.value);
  return meta ? meta.isEditable(readiness.value) : true;
});

function isTabEditable(tabKey: string) {
  const meta = tabsMeta.find(t => t.key === tabKey);
  return meta ? meta.isEditable(readiness.value) : true;
}

// "下一步"提示：第一个未完成的必填项
const nextStep = computed(() => {
  return requiredTabs.find(t => !readiness.value[t.readinessKey]);
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

onMounted(() => { void loadPlatforms(); void loadDetail(props.agentId); });
watch(() => props.agentId, (id) => { if (id) void loadDetail(id); });

function handleSaved() {
  void loadDetail(props.agentId);
}

function handleDeleted() {
  emit('deleted');
}

// Tab 内容保存后刷新 agent 数据（readiness 会自动更新）
function onTabSaved() {
  void loadDetail(props.agentId);
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
          <!-- ═══════ 头卡 ═══════ -->
          <div class="rounded-xl border bg-card overflow-hidden mb-5">
            <div class="p-5">
              <!-- 第一行：角色标识 + slug + 描述 + 版本 -->
              <div class="flex items-start justify-between gap-4">
                <div class="flex items-start gap-3 min-w-0">
                  <!-- 角色图标 -->
                  <div class="shrink-0 h-9 w-9 rounded-lg flex items-center justify-center text-xs font-bold"
                    :class="getRoleBadgeClass(selectedAgent.role)">
                    {{ formatRole(selectedAgent.role).charAt(0) }}
                  </div>
                  <div class="min-w-0">
                    <p class="text-xs text-muted-foreground font-mono mb-1">{{ selectedAgent.slug }}</p>
                    <p v-if="selectedAgent.description" class="text-sm text-muted-foreground leading-relaxed max-w-lg">
                      {{ selectedAgent.description }}
                    </p>
                    <p v-else class="text-sm text-muted-foreground/40 italic">暂无描述</p>
                  </div>
                </div>
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

              <!-- ─── 配置清单 ─── -->
              <div class="mt-4 pt-4 border-t border-border/30">
                <!-- 必填项 -->
                <div class="flex items-center gap-3 mb-2">
                  <span class="text-[11px] text-muted-foreground/50 font-medium">必填配置</span>
                  <span class="text-[11px] tabular-nums"
                    :class="progress.done === progress.total ? 'text-emerald-400' : 'text-muted-foreground/50'">
                    {{ progress.done }} / {{ progress.total }}
                  </span>
                </div>
                <div class="flex gap-2 mb-3">
                  <button v-for="tab in visibleRequiredTabs" :key="tab.key"
                    class="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-md transition-colors" :class="[
                      readiness[tab.readinessKey]
                        ? 'text-emerald-400 bg-emerald-500/5 hover:bg-emerald-500/10'
                        : nextStep?.key === tab.key
                          ? 'text-primary bg-primary/5 ring-1 ring-primary/20 hover:bg-primary/10'
                          : 'text-muted-foreground/40 bg-muted/20 hover:bg-muted/30',
                    ]" @click="tryChangeTab(tab.key)">
                    <CheckCircle2 v-if="readiness[tab.readinessKey]" class="h-3 w-3" />
                    <Circle v-else class="h-3 w-3" />
                    {{ tab.label }}
                    <span v-if="nextStep?.key === tab.key" class="text-[9px] ml-0.5 text-primary/70">← 下一步</span>
                  </button>
                </div>

                <!-- 可选项 -->
                <div class="flex items-center gap-2">
                  <span class="text-[11px] text-muted-foreground/30 font-medium">可选</span>
                  <button v-for="tab in visibleOptionalTabs" :key="tab.key"
                    class="flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-md text-muted-foreground/30 hover:text-muted-foreground/50 hover:bg-muted/20 transition-colors"
                    @click="tryChangeTab(tab.key)">
                    {{ tab.label }}
                    <template v-if="tab.key === 'schedule' && rawReadiness">
                      <Badge v-if="rawReadiness.schedules_count > 0" variant="outline"
                        class="text-[9px] px-1 py-0 h-3.5 text-muted-foreground/40">
                        {{ rawReadiness.schedules_count }}
                      </Badge>
                    </template>
                    <template v-if="tab.key === 'comm' && rawReadiness">
                      <Badge v-if="rawReadiness.comm_bindings_count > 0" variant="outline"
                        class="text-[9px] px-1 py-0 h-3.5 text-muted-foreground/40">
                        {{ rawReadiness.comm_bindings_count }}
                      </Badge>
                    </template>
                  </button>
                </div>

              </div>
            </div>
          </div>

          <!-- ═══════ Tab 面板 ═══════ -->
          <Tabs :model-value="activeTab" @update:model-value="(v) => tryChangeTab(String(v))" class="w-full">
            <TabsList class="bg-transparent border-b rounded-none w-full justify-start h-auto p-0 gap-0">
              <TabsTrigger v-for="tab in tabsMeta.filter(t => isTabVisible(t.key))" :key="tab.key" :value="tab.key"
                class="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:shadow-none gap-1.5 text-xs px-4 py-2.5 relative">
                <component :is="tab.icon" class="h-3.5 w-3.5" />
                {{ tab.label }}
                <!-- Tab 就绪指示：已完成 = 绿点，前置未满足 = Lock -->
                <span v-if="tab.required && readiness[tab.readinessKey]"
                  class="absolute top-1.5 right-1.5 h-1.5 w-1.5 rounded-full bg-emerald-400" />
                <Lock v-else-if="!tab.isEditable(readiness)" class="h-2.5 w-2.5 text-muted-foreground/30 ml-0.5" />
              </TabsTrigger>
            </TabsList>

            <!-- 前置条件未满足时的提示横幅 -->
            <div v-if="!activeTabEditable"
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
              <BasicInfoTab :agent="selectedAgent" @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="host" class="mt-5">
              <PlatformConfigTab ref="platformConfigTabRef" :agent-id="agentId" :host-platform="currentPlatform"
                @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="prompt" class="mt-5">
              <PromptTab ref="promptTabRef" :agent-id="agentId" :host-platform="currentPlatform"
                :disabled="!isTabEditable('prompt')" @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="schedule" class="mt-5">
              <ScheduleTab :agent-id="agentId" :agent-role="selectedAgent?.role"
                :disabled="!isTabEditable('schedule')" />
            </TabsContent>
            <TabsContent value="comm" class="mt-5">
              <CommBindingTab :agent-id="agentId" :host-platform="currentPlatform" :disabled="!isTabEditable('comm')"
                @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="bootstrap" class="mt-5">
              <BootstrapTab :agent-id="agentId" :agent="selectedAgent" :disabled="!isTabEditable('bootstrap')"
                @saved="onTabSaved" />
            </TabsContent>
            <TabsContent value="deploy-history" class="mt-5">
              <DeployHistoryTab :agent-id="agentId" />
            </TabsContent>
          </Tabs>
        </div>
      </template>
    </main>

    <!-- 弹窗 -->
    <AgentEditDialog v-model:open="showEditDialog" :agent="selectedAgent" @saved="handleSaved" />
    <AgentDeleteDialog v-model:open="showDeleteDialog" :agent="selectedAgent" @deleted="handleDeleted" />

    <!-- ─── 未保存切换确认弹窗 ─── -->
    <Teleport to="body">
      <div v-if="showUnsavedDialog"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="cancelDiscard" />
        <div
          class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 text-center space-y-3">
          <AlertTriangle class="h-8 w-8 mx-auto text-amber-500" />
          <h3 class="text-base font-semibold">未保存的修改</h3>
          <p class="text-sm text-muted-foreground">
            当前有未保存的修改，切换后将丢失。
          </p>
          <div class="flex gap-3 pt-2">
            <Button variant="outline" class="flex-1" @click="cancelDiscard">继续编辑</Button>
            <Button variant="destructive" class="flex-1" @click="confirmDiscard">放弃修改</Button>
          </div>
        </div>
      </div>
    </Teleport>


  </div>
</template>
