<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentBootstrapApi,
  managedAgentFeishuCommBindingApi,
  managedAgentScheduleApi,
  type FeishuCommBinding,
  type ManagedAgentDeployChangeset,
  type ManagedAgentDeployScriptConflictDetail,
  type ManagedAgentDeploymentSnapshot,
  type ManagedAgentDeploymentState,
  type ManagedAgentListItem,
  type ManagedAgentOnboardingMessageResponse,
  type ManagedAgentSchedule,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  AlertCircle, ArrowLeft, Check, ChevronRight, Clock, Copy, FileText,
  HelpCircle, Loader2, MessageSquare, RefreshCw, Rocket, Shield, Terminal,
} from 'lucide-vue-next';

const props = defineProps<{
  agentId: string;
  agent?: ManagedAgentListItem | null;
  deploymentState: ManagedAgentDeploymentState;
  disabled?: boolean;
}>();

const emit = defineEmits<{ completed: [] }>();

// ─── 向导步骤 ───
// 1 = 配置参数  2 = 执行接入  3 = 等待回传

const step = ref(1);

// ─── 资源加载 ───

const schedules = ref<ManagedAgentSchedule[]>([]);
const commBindings = ref<FeishuCommBinding[]>([]);
const loadingResources = ref(false);
const resourceError = ref('');

const promptArtifactOptions = [
  { key: 'system_prompt', artifact: 'AGENTS.md', label: '工作规则', description: '写入 OpenClaw 工作目录的 AGENTS.md。' },
  { key: 'persona_prompt', artifact: 'SOUL.md', label: '人格设定', description: '写入 OpenClaw 工作目录的 SOUL.md。' },
  { key: 'identity', artifact: 'IDENTITY.md', label: '身份信息', description: '写入 OpenClaw 工作目录的 IDENTITY.md。' },
] as const;

const selectedPromptKeys = ref<string[]>(promptArtifactOptions.map(o => o.key));
const selectedScheduleIds = ref<string[]>([]);
const selectedCommBindingIds = ref<string[]>([]);

async function loadResources() {
  loadingResources.value = true;
  resourceError.value = '';
  try {
    const [schedRes, bindRes] = await Promise.allSettled([
      managedAgentScheduleApi.list(props.agentId),
      managedAgentFeishuCommBindingApi.list(props.agentId),
    ]);
    schedules.value = schedRes.status === 'fulfilled' ? schedRes.value.data : [];
    commBindings.value = bindRes.status === 'fulfilled' ? bindRes.value.data : [];
    selectedScheduleIds.value = schedules.value.map(s => s.id);
    selectedCommBindingIds.value = commBindings.value.map(b => b.id);
    if (schedRes.status === 'rejected' || bindRes.status === 'rejected') {
      resourceError.value = '部分资源加载失败，请刷新后重试。';
    }
  } finally {
    loadingResources.value = false;
  }
}

// ─── TTL / 超时配置 ───

const registerTtl = ref(3600);
const downloadTtl = ref(86400);
const snapshotTimeoutSecs = ref(1800);

// ─── 预检 ───

const previewing = ref(false);
const previewChangeset = ref<ManagedAgentDeployChangeset | null>(null);

async function handlePreview() {
  previewing.value = true;
  try {
    const res = await managedAgentBootstrapApi.previewDeploy(props.agentId, {
      script_intent: 'bootstrap',
      prompt_artifact_keys: [...selectedPromptKeys.value],
      schedule_ids: [...selectedScheduleIds.value],
      comm_binding_ids: [...selectedCommBindingIds.value],
    });
    previewChangeset.value = res.data.changeset;
  } catch {
    toast.error('预检变更失败');
  } finally {
    previewing.value = false;
  }
}

// ─── 生成快照 ───

const creatingSnapshot = ref(false);
const snapshotId = ref<string | null>(null);
const changeset = ref<ManagedAgentDeployChangeset | null>(null);
const generatingInstructions = ref(false);
const instructions = ref<ManagedAgentOnboardingMessageResponse | null>(null);
const conflictInfo = ref<ManagedAgentDeployScriptConflictDetail | null>(null);

function selectedArtifacts() {
  return promptArtifactOptions.filter(o => selectedPromptKeys.value.includes(o.key)).map(o => o.artifact);
}

const hasPartialSelection = computed(() => {
  const partialSched = schedules.value.length > 0 &&
    selectedScheduleIds.value.length > 0 &&
    selectedScheduleIds.value.length !== schedules.value.length;
  const partialComm = commBindings.value.length > 0 &&
    selectedCommBindingIds.value.length > 0 &&
    selectedCommBindingIds.value.length !== commBindings.value.length;
  return partialSched || partialComm;
});

async function handleCreate(replacePending = false) {
  if (selectedPromptKeys.value.length === 0) {
    toast.error('至少需要选择一个 Prompt 文件。');
    return;
  }
  creatingSnapshot.value = true;
  conflictInfo.value = null;
  try {
    const res = await managedAgentBootstrapApi.createDeployScript(props.agentId, {
      script_intent: 'bootstrap',
      prompt_artifact_keys: [...selectedPromptKeys.value],
      schedule_ids: [...selectedScheduleIds.value],
      comm_binding_ids: [...selectedCommBindingIds.value],
      register_ttl_seconds: registerTtl.value,
      download_ttl_seconds: downloadTtl.value,
      snapshot_timeout_seconds: snapshotTimeoutSecs.value,
      replace_pending_snapshot: replacePending,
    });
    snapshotId.value = res.data.snapshot_id;
    changeset.value = res.data.changeset;

    // 同步获取接入指令
    generatingInstructions.value = true;
    try {
      const onbRes = await managedAgentBootstrapApi.getOnboardingMessage(props.agentId, {
        selected_artifacts: selectedArtifacts(),
        include_schedule: selectedScheduleIds.value.length > 0,
        include_comm_bindings: selectedCommBindingIds.value.length > 0,
        download_ttl_seconds: downloadTtl.value,
      });
      instructions.value = onbRes.data;
    } catch {
      toast.warning('快照已创建，但生成接入指令失败，请稍后重试。');
    } finally {
      generatingInstructions.value = false;
    }

    if (hasPartialSelection.value) {
      toast.warning('定时任务或通讯渠道存在部分选择，接入脚本将包含全部已启用的资源；精确 diff 以下方变更清单为准。');
    }

    step.value = 2;
  } catch (err: unknown) {
    const resp = (err as { response?: { status?: number; data?: { detail?: unknown } } })?.response;
    if (resp?.status === 409) {
      const detail = resp.data?.detail as ManagedAgentDeployScriptConflictDetail | undefined;
      if (detail?.error_code === 'DEPLOYMENT_SNAPSHOT_CONFLICT') {
        conflictInfo.value = detail;
        return;
      }
    }
    const msg = (resp?.data?.detail as string | undefined) ?? '创建部署快照失败';
    toast.error(msg);
  } finally {
    creatingSnapshot.value = false;
  }
}

async function retryInstructions() {
  if (!snapshotId.value) return;
  generatingInstructions.value = true;
  try {
    const res = await managedAgentBootstrapApi.getOnboardingMessage(props.agentId, {
      selected_artifacts: selectedArtifacts(),
      include_schedule: selectedScheduleIds.value.length > 0,
      include_comm_bindings: selectedCommBindingIds.value.length > 0,
      download_ttl_seconds: downloadTtl.value,
    });
    instructions.value = res.data;
  } catch {
    toast.error('重试获取接入指令失败');
  } finally {
    generatingInstructions.value = false;
  }
}

function resetToStep1() {
  step.value = 1;
  snapshotId.value = null;
  changeset.value = null;
  instructions.value = null;
  previewChangeset.value = null;
  conflictInfo.value = null;
  showFullScript.value = false;
  fullScript.value = null;
  fullScriptError.value = '';
  stopPolling();
}

// ─── 复制 ───

const copiedKey = ref<string | null>(null);
async function copyText(text: string, key: string) {
  await navigator.clipboard.writeText(text);
  copiedKey.value = key;
  setTimeout(() => { copiedKey.value = null; }, 2000);
}

// ─── 查看完整 Shell 脚本 ───

const showFullScript = ref(false);
const fullScript = ref<string | null>(null);
const loadingFullScript = ref(false);
const fullScriptError = ref('');

async function loadFullScript() {
  if (fullScript.value) { showFullScript.value = !showFullScript.value; return; }
  showFullScript.value = true;
  loadingFullScript.value = true;
  fullScriptError.value = '';
  try {
    const res = await managedAgentBootstrapApi.getBootstrapScript(props.agentId, {
      selected_artifacts: selectedArtifacts(),
      include_schedule: selectedScheduleIds.value.length > 0,
      include_comm_bindings: selectedCommBindingIds.value.length > 0,
      register_ttl_seconds: registerTtl.value,
    });
    fullScript.value = res.data.script;
  } catch {
    fullScriptError.value = '加载完整脚本失败';
    showFullScript.value = false;
  } finally {
    loadingFullScript.value = false;
  }
}

// ─── 轮询快照状态 ───

const pollingSnapshot = ref<ManagedAgentDeploymentSnapshot | null>(null);
const pollingError = ref('');
let pollTimer: ReturnType<typeof setInterval> | null = null;
let polling = false;

function stopPolling() {
  if (pollTimer !== null) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
  polling = false;
}

async function pollOnce() {
  if (polling || !snapshotId.value) return;
  const currentAgentId = props.agentId;
  const currentSnapshotId = snapshotId.value;
  polling = true;
  try {
    const res = await managedAgentBootstrapApi.listDeploymentSnapshots(currentAgentId);
    if (props.agentId !== currentAgentId || snapshotId.value !== currentSnapshotId) return;
    const found = res.data.find(s => s.id === currentSnapshotId);
    if (!found) return;
    pollingSnapshot.value = found;
    if (found.status === 'confirmed' || found.status === 'failed' || found.status === 'timeout') {
      stopPolling();
    }
  } catch {
    pollingError.value = '轮询状态失败，将继续重试…';
  } finally {
    polling = false;
  }
}

function startPolling() {
  stopPolling();
  pollingSnapshot.value = null;
  pollingError.value = '';
  void pollOnce();
  pollTimer = setInterval(() => { void pollOnce(); }, 5000);
}

function goToWait() {
  step.value = 3;
  startPolling();
}

// ─── 断点恢复：挂载时检查是否有 pending bootstrap 快照 ───

async function checkResume() {
  try {
    const res = await managedAgentBootstrapApi.listDeploymentSnapshots(props.agentId);
    const pending = res.data.find(s => s.script_intent === 'bootstrap' && s.status === 'pending');
    if (pending) {
      snapshotId.value = pending.id;
      pollingSnapshot.value = pending;
      step.value = 3;
      startPolling();
    }
  } catch {
    // 非关键，静默忽略
  }
}

onMounted(async () => {
  await loadResources();
  await checkResume();
});

watch(() => props.agentId, () => {
  stopPolling();
  step.value = 1;
  snapshotId.value = null;
  changeset.value = null;
  instructions.value = null;
  previewChangeset.value = null;
  pollingSnapshot.value = null;
  showFullScript.value = false;
  fullScript.value = null;
  fullScriptError.value = '';
  void loadResources();
  void checkResume();
});

onUnmounted(() => stopPolling());

// ─── 格式化工具 ───

function fmt(val: string | null) {
  if (!val) return '—';
  try {
    return new Date(val).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return val; }
}

function getChangeBadgeClass(type: string) {
  if (type === 'add') return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
  if (type === 'update') return 'text-sky-400 border-sky-500/20 bg-sky-500/5';
  if (type === 'remove') return 'text-rose-400 border-rose-500/20 bg-rose-500/5';
  return '';
}
function getChangeTypeLabel(type: string) {
  if (type === 'add') return '新增'; if (type === 'update') return '更新'; if (type === 'remove') return '删除'; return type;
}
function getResourceTypeLabel(type: string) {
  if (type === 'prompt') return 'Prompt'; if (type === 'schedule') return '定时任务'; if (type === 'comm_binding') return '通讯渠道'; return type;
}
</script>

<template>
  <div class="space-y-5 animate-slide-up">

    <!-- deploy_ready=false 阻塞提示 -->
    <div v-if="!deploymentState.deploy_ready"
      class="rounded-xl border border-amber-500/20 bg-amber-500/5 p-5 text-center space-y-3">
      <AlertCircle class="h-8 w-8 mx-auto text-amber-400" />
      <div>
        <p class="text-sm font-medium">请先完善平台配置</p>
        <p class="text-xs text-muted-foreground/60 mt-1 leading-relaxed">
          首次接入需要先完成平台配置（宿主机信息等前置条件），再回来生成部署脚本。
        </p>
      </div>
      <p class="text-[11px] text-muted-foreground/40">{{ deploymentState.message }}</p>
    </div>

    <!-- 正常向导流程 -->
    <template v-else>

      <!-- 步骤指示器 -->
      <div class="flex items-center gap-2">
        <div v-for="(label, idx) in ['配置参数', '执行接入', '等待回传']" :key="idx"
          class="flex items-center gap-1.5">
          <div :class="[
            'h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0',
            step === idx + 1 ? 'bg-primary text-primary-foreground' :
            step > idx + 1 ? 'bg-emerald-500 text-white' : 'bg-muted/40 text-muted-foreground/40'
          ]">
            <Check v-if="step > idx + 1" class="h-3 w-3" />
            <span v-else>{{ idx + 1 }}</span>
          </div>
          <span :class="['text-xs', step === idx + 1 ? 'text-foreground font-medium' : 'text-muted-foreground/40']">
            {{ label }}
          </span>
          <ChevronRight v-if="idx < 2" class="h-3.5 w-3.5 text-muted-foreground/30 shrink-0" />
        </div>
      </div>

      <!-- ══════════ STEP 1：配置参数 ══════════ -->
      <div v-if="step === 1" class="space-y-4">

        <!-- 资源选择 -->
        <div class="rounded-xl border bg-card p-5 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="flex items-center gap-2">
                <Shield class="h-4 w-4 text-emerald-400" />
                <span class="text-sm font-semibold">部署资源</span>
              </div>
              <p class="text-xs text-muted-foreground/60 mt-1 leading-relaxed">
                选择本次要写入 OpenClaw 的资源文件和配置。
              </p>
            </div>
            <Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs shrink-0"
              :disabled="loadingResources" @click="loadResources">
              <RefreshCw :class="['h-3 w-3', loadingResources ? 'animate-spin' : '']" />
              刷新
            </Button>
          </div>

          <div v-if="resourceError" class="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
            <div class="flex items-center gap-2 text-xs text-amber-300">
              <AlertCircle class="h-3.5 w-3.5" /> {{ resourceError }}
            </div>
          </div>

          <div class="grid gap-3 lg:grid-cols-3">
            <!-- Prompt 文件 -->
            <div class="rounded-lg border bg-background/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                <FileText class="h-3.5 w-3.5 text-muted-foreground/60" />
                <span class="text-xs font-medium">Prompt 文件</span>
                <Badge variant="outline" class="text-[10px]">{{ selectedPromptKeys.length }}/{{ promptArtifactOptions.length }}</Badge>
              </div>
              <div class="space-y-2">
                <label v-for="opt in promptArtifactOptions" :key="opt.key"
                  class="flex items-start gap-2 rounded-md border border-transparent p-2 hover:bg-muted/30 cursor-pointer">
                  <input v-model="selectedPromptKeys" type="checkbox" :value="opt.key"
                    class="mt-0.5 accent-primary" :disabled="disabled" @change="previewChangeset = null" />
                  <span class="min-w-0">
                    <span class="block text-xs">{{ opt.label }} <span class="text-muted-foreground/40">{{ opt.artifact }}</span></span>
                    <span class="block text-[11px] text-muted-foreground/45 leading-relaxed">{{ opt.description }}</span>
                  </span>
                </label>
              </div>
            </div>

            <!-- 定时任务 -->
            <div class="rounded-lg border bg-background/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                <Clock class="h-3.5 w-3.5 text-muted-foreground/60" />
                <span class="text-xs font-medium">定时任务</span>
                <Badge variant="outline" class="text-[10px]">{{ selectedScheduleIds.length }}/{{ schedules.length }}</Badge>
              </div>
              <div v-if="loadingResources" class="py-5 text-center">
                <Loader2 class="h-4 w-4 animate-spin text-muted-foreground mx-auto" />
              </div>
              <div v-else-if="schedules.length === 0"
                class="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground/40">
                暂无定时任务
              </div>
              <div v-else class="space-y-2 max-h-40 overflow-y-auto">
                <label v-for="sched in schedules" :key="sched.id"
                  class="flex items-start gap-2 rounded-md border border-transparent p-2 hover:bg-muted/30 cursor-pointer">
                  <input v-model="selectedScheduleIds" type="checkbox" :value="sched.id"
                    class="mt-0.5 accent-primary" :disabled="disabled" @change="previewChangeset = null" />
                  <span class="min-w-0">
                    <span class="block text-xs truncate">{{ sched.name }}</span>
                    <span class="block text-[11px] text-muted-foreground/45">
                      {{ sched.schedule_type }} · {{ sched.schedule_expr }}
                      <span :class="sched.enabled ? 'text-emerald-400' : 'text-muted-foreground/40'">
                        · {{ sched.enabled ? '启用' : '停用' }}
                      </span>
                    </span>
                  </span>
                </label>
              </div>
            </div>

            <!-- 通讯渠道 -->
            <div class="rounded-lg border bg-background/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                <MessageSquare class="h-3.5 w-3.5 text-muted-foreground/60" />
                <span class="text-xs font-medium">通讯渠道</span>
                <Badge variant="outline" class="text-[10px]">{{ selectedCommBindingIds.length }}/{{ commBindings.length }}</Badge>
              </div>
              <div v-if="loadingResources" class="py-5 text-center">
                <Loader2 class="h-4 w-4 animate-spin text-muted-foreground mx-auto" />
              </div>
              <div v-else-if="commBindings.length === 0"
                class="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground/40">
                暂无飞书绑定
              </div>
              <div v-else class="space-y-2 max-h-40 overflow-y-auto">
                <label v-for="binding in commBindings" :key="binding.id"
                  class="flex items-start gap-2 rounded-md border border-transparent p-2 hover:bg-muted/30 cursor-pointer">
                  <input v-model="selectedCommBindingIds" type="checkbox" :value="binding.id"
                    class="mt-0.5 accent-primary" :disabled="disabled" @change="previewChangeset = null" />
                  <span class="min-w-0">
                    <span class="block text-xs truncate">{{ binding.account_name || binding.account_id }}</span>
                    <span class="block text-[11px] text-muted-foreground/45">
                      feishu · {{ binding.account_id }}
                      <span :class="binding.enabled ? 'text-emerald-400' : 'text-muted-foreground/40'">
                        · {{ binding.enabled ? '启用' : '停用' }}
                      </span>
                    </span>
                  </span>
                </label>
              </div>
            </div>
          </div>
        </div>

        <!-- TTL 配置 -->
        <div class="rounded-xl border bg-card p-5">
          <div class="flex items-center gap-2 mb-3">
            <Clock class="h-4 w-4 text-muted-foreground/60" />
            <span class="text-sm font-semibold">有效期配置</span>
          </div>
          <div class="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label class="space-y-1.5">
              <span class="flex items-center gap-1 text-xs text-muted-foreground/60">
                注册 Token（秒）
                <TooltipProvider :delay-duration="200"><Tooltip>
                  <TooltipTrigger as-child>
                    <button type="button" class="inline-flex items-center justify-center h-4 w-4 rounded-full text-muted-foreground/30 hover:text-muted-foreground/60 hover:bg-muted/30 transition-colors">
                      <HelpCircle class="h-3 w-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" :side-offset="4" class="max-w-xs text-xs leading-relaxed">
                    脚本执行期间向后端注册运行态 Agent 身份的 Token 有效期。默认 3600 秒（1 小时），最小 60 秒。
                  </TooltipContent>
                </Tooltip></TooltipProvider>
              </span>
              <Input v-model.number="registerTtl" type="number" min="60" class="h-9 text-sm" :disabled="disabled" />
            </label>
            <label class="space-y-1.5">
              <span class="flex items-center gap-1 text-xs text-muted-foreground/60">
                下载 Token（秒）
                <TooltipProvider :delay-duration="200"><Tooltip>
                  <TooltipTrigger as-child>
                    <button type="button" class="inline-flex items-center justify-center h-4 w-4 rounded-full text-muted-foreground/30 hover:text-muted-foreground/60 hover:bg-muted/30 transition-colors">
                      <HelpCircle class="h-3 w-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" :side-offset="4" class="max-w-xs text-xs leading-relaxed">
                    接入说明 curl 命令用于下载脚本的临时 Token 有效期。默认 86400 秒（24 小时），最小 60 秒。
                  </TooltipContent>
                </Tooltip></TooltipProvider>
              </span>
              <Input v-model.number="downloadTtl" type="number" min="60" class="h-9 text-sm" :disabled="disabled" />
            </label>
            <label class="space-y-1.5">
              <span class="flex items-center gap-1 text-xs text-muted-foreground/60">
                快照超时（秒）
                <TooltipProvider :delay-duration="200"><Tooltip>
                  <TooltipTrigger as-child>
                    <button type="button" class="inline-flex items-center justify-center h-4 w-4 rounded-full text-muted-foreground/30 hover:text-muted-foreground/60 hover:bg-muted/30 transition-colors">
                      <HelpCircle class="h-3 w-3" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top" :side-offset="4" class="max-w-xs text-xs leading-relaxed">
                    快照等待回传的时间上限，超时后后端标记为 timeout。默认 1800 秒（30 分钟），范围 60 ~ 86400 秒。
                  </TooltipContent>
                </Tooltip></TooltipProvider>
              </span>
              <Input v-model.number="snapshotTimeoutSecs" type="number" min="60" max="86400" class="h-9 text-sm" :disabled="disabled" />
            </label>
          </div>
        </div>

        <!-- 变更预检（可选） -->
        <div class="rounded-xl border bg-card p-5">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <Terminal class="h-4 w-4 text-muted-foreground/60" />
              <span class="text-sm font-semibold">变更预检</span>
              <span class="text-xs text-muted-foreground/40">（可选）</span>
            </div>
            <Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs"
              :disabled="previewing || disabled" @click="handlePreview">
              <Loader2 v-if="previewing" class="h-3 w-3 animate-spin" />
              <Shield v-else class="h-3 w-3" />
              预检变更
            </Button>
          </div>
          <p class="text-xs text-muted-foreground/50 leading-relaxed">
            生成快照前可先预检资源级变更清单，了解本次部署的具体内容。不预检也可直接生成。
          </p>
          <div v-if="previewChangeset" class="mt-3 space-y-1.5 animate-slide-up">
            <div class="flex items-center gap-2 flex-wrap mb-2">
              <Badge v-if="previewChangeset.is_valid" variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">校验通过</Badge>
              <Badge v-else variant="outline" class="text-[10px] text-rose-400 border-rose-500/20">校验失败</Badge>
              <span class="text-[11px] text-muted-foreground/40">{{ previewChangeset.items.length }} 项变更</span>
            </div>
            <div v-if="previewChangeset.validation_errors.length" class="rounded-md border border-rose-500/20 bg-rose-500/5 p-2 mb-2">
              <div v-for="e in previewChangeset.validation_errors" :key="e" class="text-xs text-rose-300">{{ e }}</div>
            </div>
            <div v-if="previewChangeset.items.length === 0"
              class="text-center text-xs text-muted-foreground/40 py-3">暂无变更</div>
            <div v-for="(item, idx) in previewChangeset.items"
              :key="`${item.resource_type}-${item.resource_id ?? item.resource_key}-${idx}`"
              class="flex items-center gap-3 rounded-md border bg-background/70 px-3 py-2">
              <Badge variant="outline" class="text-[10px]" :class="getChangeBadgeClass(item.change_type)">
                {{ getChangeTypeLabel(item.change_type) }}
              </Badge>
              <div class="min-w-0 flex-1">
                <div class="text-xs truncate">{{ item.label }}</div>
                <div class="text-[11px] text-muted-foreground/40">{{ getResourceTypeLabel(item.resource_type) }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- 409 冲突确认 -->
        <div v-if="conflictInfo"
          class="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-3 animate-slide-up">
          <div class="flex items-start gap-3">
            <AlertCircle class="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium text-amber-300">存在未完成的部署快照</p>
              <p class="text-xs text-muted-foreground/60 mt-1 leading-relaxed">
                {{ conflictInfo.message }}
              </p>
              <div class="mt-2 flex flex-wrap gap-3 text-[11px] text-muted-foreground/50">
                <span>快照 {{ conflictInfo.conflict_snapshot.id.slice(0, 8) }}…</span>
                <span>创建于 {{ fmt(conflictInfo.conflict_snapshot.created_at) }}</span>
                <span v-if="conflictInfo.conflict_snapshot.expires_at">超时截止 {{ fmt(conflictInfo.conflict_snapshot.expires_at) }}</span>
                <Badge v-if="conflictInfo.conflict_snapshot.is_likely_timeout"
                  variant="outline" class="text-[10px] text-amber-400 border-amber-500/20">疑似已超时</Badge>
              </div>
            </div>
          </div>
          <div class="flex items-center justify-end gap-2">
            <Button variant="ghost" size="sm" class="h-7 text-xs"
              @click="conflictInfo = null">
              取消
            </Button>
            <Button size="sm" class="h-7 text-xs gap-1.5 bg-amber-600 hover:bg-amber-500 text-white"
              :disabled="creatingSnapshot" @click="handleCreate(true)">
              <Loader2 v-if="creatingSnapshot" class="h-3 w-3 animate-spin" />
              确认替换，重新生成
            </Button>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="flex justify-end">
          <Button size="lg" class="gap-2 bg-primary" :disabled="creatingSnapshot || disabled" @click="handleCreate()">
            <Loader2 v-if="creatingSnapshot" class="h-4 w-4 animate-spin" />
            <Rocket v-else class="h-4 w-4" />
            {{ creatingSnapshot ? '生成中…' : '生成 Bootstrap 快照' }}
          </Button>
        </div>
      </div>

      <!-- ══════════ STEP 2：执行接入 ══════════ -->
      <div v-else-if="step === 2" class="space-y-4">
        <div class="rounded-xl border bg-card p-5 space-y-4">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Terminal class="h-4 w-4 text-emerald-400" />
              <span class="text-sm font-semibold">接入指令</span>
              <Badge variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">快照已创建</Badge>
            </div>
            <button type="button" class="flex items-center gap-1 text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors"
              @click="resetToStep1">
              <ArrowLeft class="h-3.5 w-3.5" /> 重新生成
            </button>
          </div>
          <p class="text-xs text-muted-foreground/60 leading-relaxed">
            将下方 curl 命令发送给要接入的机器执行者，等待脚本在目标机器上执行并回传结果。
          </p>

          <!-- 变更清单（来自 changeset） -->
          <div v-if="changeset" class="space-y-1.5">
            <div class="text-[11px] text-muted-foreground/50 font-medium">变更清单</div>
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <Badge v-if="changeset.is_valid" variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">校验通过</Badge>
              <Badge v-else variant="outline" class="text-[10px] text-rose-400 border-rose-500/20">校验失败</Badge>
              <span class="text-[11px] text-muted-foreground/40">快照 {{ snapshotId }}</span>
            </div>
            <div v-if="changeset.validation_errors.length" class="rounded-md border border-rose-500/20 bg-rose-500/5 p-2 mb-1">
              <div v-for="e in changeset.validation_errors" :key="e" class="text-xs text-rose-300">{{ e }}</div>
            </div>
            <div v-for="(item, idx) in changeset.items"
              :key="`${item.resource_type}-${item.resource_id ?? item.resource_key}-${idx}`"
              class="flex items-center gap-3 rounded-md border bg-background/70 px-3 py-2">
              <Badge variant="outline" class="text-[10px]" :class="getChangeBadgeClass(item.change_type)">
                {{ getChangeTypeLabel(item.change_type) }}
              </Badge>
              <div class="min-w-0 flex-1">
                <div class="text-xs truncate">{{ item.label }}</div>
                <div class="text-[11px] text-muted-foreground/40">{{ getResourceTypeLabel(item.resource_type) }}</div>
              </div>
            </div>
          </div>

          <Separator />

          <!-- curl 命令 / 加载中 / 失败 -->
          <div v-if="generatingInstructions" class="flex items-center gap-2 py-4">
            <Loader2 class="h-4 w-4 animate-spin text-muted-foreground" />
            <span class="text-xs text-muted-foreground/60">正在生成接入指令…</span>
          </div>
          <div v-else-if="instructions" class="space-y-3">
            <div class="space-y-1">
              <div class="text-[11px] text-muted-foreground/50 font-medium">接入说明</div>
              <pre class="rounded-lg bg-muted/30 border p-3 text-xs whitespace-pre-wrap break-all max-h-28 overflow-y-auto leading-relaxed">{{ instructions.message }}</pre>
            </div>
            <div class="space-y-1">
              <div class="text-[11px] text-muted-foreground/50 font-medium">curl 下载命令</div>
              <div class="relative">
                <pre class="rounded-lg bg-muted/30 border p-3 text-xs font-mono whitespace-pre-wrap break-all max-h-20 overflow-y-auto leading-relaxed pr-10">{{ instructions.curl_command }}</pre>
                <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                  @click="copyText(instructions.curl_command, 'curl')">
                  <Check v-if="copiedKey === 'curl'" class="h-3 w-3 text-emerald-400" />
                  <Copy v-else class="h-3 w-3" />
                </Button>
              </div>
            </div>
            <p class="text-[11px] text-muted-foreground/40">
              下载 Token 过期：{{ fmt(instructions.download_token_expires_at) }}
            </p>
            <!-- 查看完整 Shell 脚本 -->
            <div>
              <button type="button"
                class="flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                @click="loadFullScript">
                <Loader2 v-if="loadingFullScript" class="h-3 w-3 animate-spin" />
                <FileText v-else class="h-3 w-3" />
                {{ showFullScript && fullScript ? '收起完整脚本' : '查看完整 Shell 脚本' }}
              </button>
              <div v-if="showFullScript && fullScript" class="mt-2 relative animate-slide-up">
                <pre class="rounded-lg bg-muted/30 border p-3 text-[11px] font-mono whitespace-pre break-all max-h-72 overflow-auto leading-relaxed pr-10">{{ fullScript }}</pre>
                <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                  @click="copyText(fullScript!, 'full-script')">
                  <Check v-if="copiedKey === 'full-script'" class="h-3 w-3 text-emerald-400" />
                  <Copy v-else class="h-3 w-3" />
                </Button>
              </div>
              <p v-if="fullScriptError" class="text-xs text-rose-400 mt-1">{{ fullScriptError }}</p>
            </div>
          </div>
          <div v-else class="rounded-lg border border-rose-500/20 bg-rose-500/5 p-3 flex items-center justify-between">
            <div class="flex items-center gap-2 text-xs text-rose-300">
              <AlertCircle class="h-3.5 w-3.5 shrink-0" />
              快照已创建，但获取接入指令失败。
            </div>
            <Button variant="outline" size="sm" class="h-7 text-xs ml-3 shrink-0"
              :disabled="generatingInstructions" @click="retryInstructions">
              重试
            </Button>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="flex justify-end">
          <Button size="lg" class="gap-2" :disabled="!snapshotId" @click="goToWait">
            <Check class="h-4 w-4" />
            我已执行脚本，等待回传
          </Button>
        </div>
      </div>

      <!-- ══════════ STEP 3：等待回传 ══════════ -->
      <div v-else-if="step === 3" class="space-y-4">

      <!-- 正在等待 -->
      <template v-if="!pollingSnapshot || pollingSnapshot.status === 'pending'">

        <!-- 状态卡片（紧凑） -->
        <div class="rounded-xl border border-sky-500/20 bg-sky-500/5 p-5 space-y-2">
          <div class="flex items-center gap-3">
            <Loader2 class="h-5 w-5 animate-spin text-sky-400 shrink-0" />
            <div>
              <p class="text-sm font-medium">等待目标机器回传…</p>
              <p class="text-xs text-muted-foreground/60 mt-0.5">
                脚本在目标机器执行后会自动回传结果，每 5 秒自动刷新一次状态。
              </p>
            </div>
          </div>
          <div v-if="pollingSnapshot" class="flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground/40 pl-8">
            <span>快照 {{ pollingSnapshot.id }}</span>
            <span v-if="pollingSnapshot.expires_at">· 超时截止：{{ fmt(pollingSnapshot.expires_at) }}</span>
            <Badge v-if="pollingSnapshot.is_likely_timeout"
              variant="outline" class="text-[10px] text-amber-400 border-amber-500/20">
              疑似已超时，可重新生成
            </Badge>
          </div>
          <p v-if="pollingError" class="text-[11px] text-amber-400 pl-8">{{ pollingError }}</p>
          <button type="button" class="text-xs text-muted-foreground/40 hover:text-muted-foreground transition-colors pl-8"
            @click="resetToStep1">
            重新生成快照
          </button>
        </div>

        <!-- 接入指令（等待期间可随时参考） -->
        <div class="rounded-xl border bg-card p-5 space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <Terminal class="h-4 w-4 text-muted-foreground/60" />
              <span class="text-sm font-semibold">接入指令</span>
              <span class="text-xs text-muted-foreground/40">（等待期间可随时参考）</span>
            </div>
            <Button v-if="!instructions && !generatingInstructions" variant="ghost" size="sm"
              class="h-7 text-xs gap-1" @click="retryInstructions">
              <RefreshCw class="h-3 w-3" />
              重新获取
            </Button>
          </div>

          <div v-if="generatingInstructions" class="flex items-center gap-2 py-2">
            <Loader2 class="h-3.5 w-3.5 animate-spin text-muted-foreground" />
            <span class="text-xs text-muted-foreground/60">正在获取接入指令…</span>
          </div>
          <div v-else-if="instructions" class="space-y-3">
            <div class="space-y-1">
              <div class="text-[11px] text-muted-foreground/50 font-medium">接入说明</div>
              <pre class="rounded-lg bg-muted/30 border p-3 text-xs whitespace-pre-wrap break-all max-h-28 overflow-y-auto leading-relaxed">{{ instructions.message }}</pre>
            </div>
            <div class="space-y-1">
              <div class="text-[11px] text-muted-foreground/50 font-medium">curl 下载命令</div>
              <div class="relative">
                <pre class="rounded-lg bg-muted/30 border p-3 text-xs font-mono whitespace-pre-wrap break-all max-h-20 overflow-y-auto leading-relaxed pr-10">{{ instructions.curl_command }}</pre>
                <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                  @click="copyText(instructions.curl_command, 'curl')">
                  <Check v-if="copiedKey === 'curl'" class="h-3 w-3 text-emerald-400" />
                  <Copy v-else class="h-3 w-3" />
                </Button>
              </div>
            </div>
            <p class="text-[11px] text-muted-foreground/40">
              下载 Token 过期：{{ fmt(instructions.download_token_expires_at) }}
            </p>
          </div>
          <div v-else class="text-xs text-muted-foreground/40 py-1">
            接入指令暂不可用，请点击"重新获取"。
          </div>

          <Separator />

          <!-- 查看完整 Shell 脚本 -->
          <div>
            <button type="button"
              class="flex items-center gap-1.5 text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors"
              @click="loadFullScript">
              <Loader2 v-if="loadingFullScript" class="h-3 w-3 animate-spin" />
              <FileText v-else class="h-3 w-3" />
              {{ showFullScript && fullScript ? '收起完整脚本' : '查看完整 Shell 脚本' }}
            </button>
            <div v-if="showFullScript && fullScript" class="mt-2 relative animate-slide-up">
              <pre class="rounded-lg bg-muted/30 border p-3 text-[11px] font-mono whitespace-pre break-all max-h-72 overflow-auto leading-relaxed pr-10">{{ fullScript }}</pre>
              <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                @click="copyText(fullScript!, 'full-script')">
                <Check v-if="copiedKey === 'full-script'" class="h-3 w-3 text-emerald-400" />
                <Copy v-else class="h-3 w-3" />
              </Button>
            </div>
            <p v-if="fullScriptError" class="text-xs text-rose-400 mt-1">{{ fullScriptError }}</p>
          </div>
        </div>

      </template>

      <!-- 已确认：接入成功 -->
      <div v-else-if="pollingSnapshot?.status === 'confirmed'"
        class="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 text-center space-y-3">
        <div class="h-12 w-12 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto">
          <Check class="h-6 w-6 text-emerald-400" />
        </div>
        <div>
          <p class="text-base font-semibold text-emerald-400">首次接入成功！</p>
          <p class="text-xs text-muted-foreground/60 mt-1 leading-relaxed">
            Agent 运行态已成功注册，后续可在"同步变更"面板管理配置更新。
          </p>
        </div>
        <p class="text-[11px] text-muted-foreground/40">
          确认时间：{{ fmt(pollingSnapshot!.confirmed_at) }}
        </p>
        <Button @click="emit('completed')" class="mt-2">
          进入同步变更管理
        </Button>
      </div>

      <!-- 失败 -->
      <div v-else-if="pollingSnapshot?.status === 'failed'"
        class="rounded-xl border border-rose-500/20 bg-rose-500/5 p-6 text-center space-y-3">
        <AlertCircle class="h-8 w-8 mx-auto text-rose-400" />
        <div>
          <p class="text-sm font-medium text-rose-400">部署失败</p>
          <p class="text-xs text-muted-foreground/60 mt-1">请检查错误信息后重新生成快照。</p>
        </div>
        <p v-if="pollingSnapshot!.failure_detail_json" class="text-xs text-rose-300 break-all text-left bg-rose-500/10 rounded-lg p-3">
          {{ pollingSnapshot!.failure_detail_json }}
        </p>
        <Button variant="outline" @click="resetToStep1">重新生成快照</Button>
      </div>

      <!-- 超时 -->
      <div v-else-if="pollingSnapshot?.status === 'timeout'"
        class="rounded-xl border border-amber-500/20 bg-amber-500/5 p-6 text-center space-y-3">
        <Clock class="h-8 w-8 mx-auto text-amber-400" />
        <div>
          <p class="text-sm font-medium text-amber-400">等待超时</p>
          <p class="text-xs text-muted-foreground/60 mt-1 leading-relaxed">
            目标机器在有效期内未回传结果。请确认脚本已在目标机器正确执行，或重新生成快照。
          </p>
        </div>
        <Button variant="outline" @click="resetToStep1">重新生成快照</Button>
      </div>

      </div>

    </template>
  </div>
</template>
