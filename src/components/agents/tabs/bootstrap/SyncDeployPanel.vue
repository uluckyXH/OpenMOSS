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
  type ManagedAgentSchedule,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  AlertCircle, Check, CheckCircle2, Clock, Copy, FileText, HelpCircle,
  Loader2, MessageSquare, RefreshCw, Terminal,
} from 'lucide-vue-next';

const props = defineProps<{
  agentId: string;
  agent?: ManagedAgentListItem | null;
  deploymentState: ManagedAgentDeploymentState;
  disabled?: boolean;
}>();

const emit = defineEmits<{ stateChanged: [] }>();

// ─── 视图状态 ───
// 'idle' | 'generating' | 'ready' | 'waiting' | 'confirmed' | 'failed' | 'timeout'

type ViewState = 'idle' | 'generating' | 'ready' | 'waiting' | 'confirmed' | 'failed' | 'timeout';
const viewState = ref<ViewState>('idle');

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

// ─── 快照超时 ───

const snapshotTimeoutSecs = ref(1800);

// ─── 生成脚本 ───

const snapshotId = ref<string | null>(null);
const changeset = ref<ManagedAgentDeployChangeset | null>(null);
const curlCommand = ref<string | null>(null);
const curlExpiry = ref<string | null>(null);
const conflictInfo = ref<ManagedAgentDeployScriptConflictDetail | null>(null);

const canGenerate = computed(() => selectedPromptKeys.value.length > 0);

async function handleGenerate(replacePending = false) {
  if (!canGenerate.value) {
    toast.error('同步变更至少需要选择一个 Prompt 文件。');
    return;
  }
  viewState.value = 'generating';
  snapshotId.value = null;
  changeset.value = null;
  curlCommand.value = null;
  curlExpiry.value = null;
  conflictInfo.value = null;
  stopPolling();

  try {
    const res = await managedAgentBootstrapApi.createDeployScript(props.agentId, {
      script_intent: 'sync',
      prompt_artifact_keys: [...selectedPromptKeys.value],
      schedule_ids: [...selectedScheduleIds.value],
      comm_binding_ids: [...selectedCommBindingIds.value],
      snapshot_timeout_seconds: snapshotTimeoutSecs.value,
      replace_pending_snapshot: replacePending,
    });
    snapshotId.value = res.data.snapshot_id;
    changeset.value = res.data.changeset;

    try {
      const onbRes = await managedAgentBootstrapApi.getOnboardingMessage(props.agentId, {
        selected_artifacts: promptArtifactOptions.filter(o => selectedPromptKeys.value.includes(o.key)).map(o => o.artifact),
        include_schedule: selectedScheduleIds.value.length > 0,
        include_comm_bindings: selectedCommBindingIds.value.length > 0,
      });
      curlCommand.value = onbRes.data.curl_command;
      curlExpiry.value = onbRes.data.download_token_expires_at;
    } catch {
      toast.warning('快照已创建，但获取下载命令失败，请手动刷新后重试。');
    }

    viewState.value = 'ready';
    toast.success('已创建待部署快照');
    emit('stateChanged');
  } catch (err: unknown) {
    const resp = (err as { response?: { status?: number; data?: { detail?: unknown } } })?.response;
    if (resp?.status === 409) {
      const detail = resp.data?.detail as ManagedAgentDeployScriptConflictDetail | undefined;
      if (detail?.error_code === 'DEPLOYMENT_SNAPSHOT_CONFLICT') {
        conflictInfo.value = detail;
        viewState.value = 'idle';
        return;
      }
    }
    const msg = (resp?.data?.detail as string | undefined) ?? '生成同步脚本失败';
    toast.error(msg);
    viewState.value = 'idle';
  }
}

// ─── 开始等待 ───

const pollingSnapshot = ref<ManagedAgentDeploymentSnapshot | null>(null);
const pollingError = ref('');
let pollTimer: ReturnType<typeof setInterval> | null = null;
let polling = false;

function stopPolling() {
  if (pollTimer !== null) { clearInterval(pollTimer); pollTimer = null; }
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
    if (found.status === 'confirmed') { stopPolling(); viewState.value = 'confirmed'; emit('stateChanged'); }
    else if (found.status === 'failed') { stopPolling(); viewState.value = 'failed'; }
    else if (found.status === 'timeout') { stopPolling(); viewState.value = 'timeout'; }
  } catch {
    pollingError.value = '轮询状态失败，将继续重试…';
  } finally {
    polling = false;
  }
}

function startWaiting() {
  viewState.value = 'waiting';
  pollingSnapshot.value = null;
  pollingError.value = '';
  void pollOnce();
  pollTimer = setInterval(() => { void pollOnce(); }, 5000);
}

function reset() {
  stopPolling();
  viewState.value = 'idle';
  snapshotId.value = null;
  changeset.value = null;
  curlCommand.value = null;
  curlExpiry.value = null;
  pollingSnapshot.value = null;
}

// ─── 复制 ───

const copiedKey = ref<string | null>(null);
async function copyText(text: string, key: string) {
  await navigator.clipboard.writeText(text);
  copiedKey.value = key;
  setTimeout(() => { copiedKey.value = null; }, 2000);
}

// ─── 生命周期 ───

onMounted(() => loadResources());
watch(() => props.agentId, () => { reset(); void loadResources(); });
onUnmounted(() => stopPolling());

// ─── 辅助 ───

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

    <!-- 版本信息卡 -->
    <div class="rounded-xl border bg-card p-5">
      <div class="flex items-center gap-3">
        <div :class="[
          'h-9 w-9 rounded-full flex items-center justify-center shrink-0',
          deploymentState.deployment_phase === 'up_to_date'
            ? 'bg-emerald-500/15' : 'bg-amber-500/15'
        ]">
          <CheckCircle2 v-if="deploymentState.deployment_phase === 'up_to_date'" class="h-5 w-5 text-emerald-400" />
          <RefreshCw v-else class="h-5 w-5 text-amber-400" />
        </div>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-semibold">
            {{ deploymentState.deployment_phase === 'up_to_date' ? '配置已同步' : '有待同步变更' }}
          </p>
          <p class="text-xs text-muted-foreground/60 mt-0.5 leading-relaxed">{{ deploymentState.message }}</p>
        </div>
        <div class="text-right shrink-0">
          <div class="text-xs text-muted-foreground/50">当前配置</div>
          <div class="text-sm font-bold">v{{ deploymentState.config_version }}</div>
          <div v-if="deploymentState.deployed_config_version !== null"
            :class="['text-xs', deploymentState.deployment_phase === 'up_to_date' ? 'text-emerald-400/60' : 'text-amber-400/60']">
            已部署 v{{ deploymentState.deployed_config_version }}
          </div>
        </div>
      </div>
    </div>

    <!-- up_to_date：已同步态 -->
    <div v-if="deploymentState.deployment_phase === 'up_to_date'"
      class="rounded-xl border border-dashed border-emerald-500/20 bg-emerald-500/5 p-6 text-center space-y-2">
      <Check class="h-6 w-6 mx-auto text-emerald-400" />
      <p class="text-sm font-medium text-emerald-400">所有配置已同步到运行态</p>
      <p class="text-xs text-muted-foreground/50 leading-relaxed">
        下次配置变更后，"有待同步变更"提示会自动出现，届时可在此生成同步脚本。
      </p>
    </div>

    <!-- sync_required：同步变更流程 -->
    <template v-else>

      <!-- ── idle / ready：生成配置 ── -->
      <div v-if="viewState === 'idle' || viewState === 'generating' || viewState === 'ready'"
        class="space-y-4">

        <!-- 资源选择 -->
        <div class="rounded-xl border bg-card p-5 space-y-4">
          <div class="flex items-center justify-between">
            <div>
              <div class="flex items-center gap-2">
                <Terminal class="h-4 w-4 text-muted-foreground/60" />
                <span class="text-sm font-semibold">同步资源</span>
              </div>
              <p class="text-xs text-muted-foreground/60 mt-1">选择本次要同步的资源，建议全选以确保一致性。</p>
            </div>
            <Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs shrink-0"
              :disabled="loadingResources" @click="loadResources">
              <RefreshCw :class="['h-3 w-3', loadingResources ? 'animate-spin' : '']" /> 刷新
            </Button>
          </div>

          <div v-if="resourceError" class="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3">
            <div class="flex items-center gap-2 text-xs text-amber-300"><AlertCircle class="h-3.5 w-3.5" /> {{ resourceError }}</div>
          </div>

          <div class="grid gap-3 lg:grid-cols-3">
            <div class="rounded-lg border bg-background/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                <FileText class="h-3.5 w-3.5 text-muted-foreground/60" />
                <span class="text-xs font-medium">Prompt 文件</span>
                <Badge variant="outline" class="text-[10px]">{{ selectedPromptKeys.length }}/{{ promptArtifactOptions.length }}</Badge>
              </div>
              <div class="space-y-2">
                <label v-for="opt in promptArtifactOptions" :key="opt.key"
                  class="flex items-start gap-2 rounded-md border border-transparent p-2 hover:bg-muted/30 cursor-pointer">
                  <input v-model="selectedPromptKeys" type="checkbox" :value="opt.key" class="mt-0.5 accent-primary" :disabled="disabled" />
                  <span class="min-w-0">
                    <span class="block text-xs">{{ opt.label }} <span class="text-muted-foreground/40">{{ opt.artifact }}</span></span>
                    <span class="block text-[11px] text-muted-foreground/45 leading-relaxed">{{ opt.description }}</span>
                  </span>
                </label>
              </div>
            </div>

            <div class="rounded-lg border bg-background/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                <Clock class="h-3.5 w-3.5 text-muted-foreground/60" />
                <span class="text-xs font-medium">定时任务</span>
                <Badge variant="outline" class="text-[10px]">{{ selectedScheduleIds.length }}/{{ schedules.length }}</Badge>
              </div>
              <div v-if="loadingResources" class="py-5 text-center"><Loader2 class="h-4 w-4 animate-spin text-muted-foreground mx-auto" /></div>
              <div v-else-if="schedules.length === 0" class="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground/40">暂无定时任务</div>
              <div v-else class="space-y-2 max-h-40 overflow-y-auto">
                <label v-for="sched in schedules" :key="sched.id"
                  class="flex items-start gap-2 rounded-md border border-transparent p-2 hover:bg-muted/30 cursor-pointer">
                  <input v-model="selectedScheduleIds" type="checkbox" :value="sched.id" class="mt-0.5 accent-primary" :disabled="disabled" />
                  <span class="min-w-0">
                    <span class="block text-xs truncate">{{ sched.name }}</span>
                    <span class="block text-[11px] text-muted-foreground/45">{{ sched.schedule_type }} · {{ sched.schedule_expr }}</span>
                  </span>
                </label>
              </div>
            </div>

            <div class="rounded-lg border bg-background/50 p-3">
              <div class="flex items-center gap-2 mb-2">
                <MessageSquare class="h-3.5 w-3.5 text-muted-foreground/60" />
                <span class="text-xs font-medium">通讯渠道</span>
                <Badge variant="outline" class="text-[10px]">{{ selectedCommBindingIds.length }}/{{ commBindings.length }}</Badge>
              </div>
              <div v-if="loadingResources" class="py-5 text-center"><Loader2 class="h-4 w-4 animate-spin text-muted-foreground mx-auto" /></div>
              <div v-else-if="commBindings.length === 0" class="rounded-md border border-dashed p-4 text-center text-xs text-muted-foreground/40">暂无飞书绑定</div>
              <div v-else class="space-y-2 max-h-40 overflow-y-auto">
                <label v-for="binding in commBindings" :key="binding.id"
                  class="flex items-start gap-2 rounded-md border border-transparent p-2 hover:bg-muted/30 cursor-pointer">
                  <input v-model="selectedCommBindingIds" type="checkbox" :value="binding.id" class="mt-0.5 accent-primary" :disabled="disabled" />
                  <span class="min-w-0">
                    <span class="block text-xs truncate">{{ binding.account_name || binding.account_id }}</span>
                    <span class="block text-[11px] text-muted-foreground/45">feishu · {{ binding.account_id }}</span>
                  </span>
                </label>
              </div>
            </div>
          </div>

          <!-- 快照超时 -->
          <div class="grid sm:grid-cols-3 gap-3 pt-1">
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
                :disabled="viewState === 'generating'" @click="handleGenerate(true)">
                <Loader2 v-if="viewState === 'generating'" class="h-3 w-3 animate-spin" />
                确认替换，重新生成
              </Button>
            </div>
          </div>

          <!-- 生成按钮 -->
          <div class="flex justify-end pt-1">
            <Button size="lg" class="gap-2" :disabled="viewState === 'generating' || disabled || !canGenerate" @click="handleGenerate()">
              <Loader2 v-if="viewState === 'generating'" class="h-4 w-4 animate-spin" />
              <RefreshCw v-else class="h-4 w-4" />
              {{ viewState === 'generating' ? '生成中…' : '生成同步脚本' }}
            </Button>
          </div>
        </div>

        <!-- 生成结果：changeset + curl 命令 -->
        <div v-if="viewState === 'ready'" class="rounded-xl border bg-card p-5 space-y-4 animate-slide-up">
          <div class="flex items-center gap-2">
            <Terminal class="h-4 w-4 text-emerald-400" />
            <span class="text-sm font-semibold">接入指令</span>
            <Badge variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">快照已创建</Badge>
          </div>

          <div v-if="changeset" class="space-y-1.5">
            <div class="flex items-center gap-2 flex-wrap mb-1">
              <Badge v-if="changeset.is_valid" variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">校验通过</Badge>
              <Badge v-else variant="outline" class="text-[10px] text-rose-400 border-rose-500/20">校验失败</Badge>
              <span class="text-[11px] text-muted-foreground/40">快照 {{ snapshotId }} · {{ changeset.items.length }} 项变更</span>
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

          <Separator v-if="curlCommand" />

          <div v-if="curlCommand" class="space-y-1">
            <div class="text-[11px] text-muted-foreground/50 font-medium">curl 下载命令</div>
            <div class="relative">
              <pre class="rounded-lg bg-muted/30 border p-3 text-xs font-mono whitespace-pre-wrap break-all max-h-20 overflow-y-auto leading-relaxed pr-10">{{ curlCommand }}</pre>
              <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                @click="copyText(curlCommand, 'curl')">
                <Check v-if="copiedKey === 'curl'" class="h-3 w-3 text-emerald-400" />
                <Copy v-else class="h-3 w-3" />
              </Button>
            </div>
            <p class="text-[11px] text-muted-foreground/40">下载 Token 过期：{{ fmt(curlExpiry) }}</p>
          </div>
          <div v-else class="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-300 flex items-center gap-2">
            <AlertCircle class="h-3.5 w-3.5 shrink-0" /> 快照已创建，但获取下载命令失败。
          </div>

          <div class="flex justify-end pt-1">
            <Button class="gap-2" @click="startWaiting">
              <Check class="h-4 w-4" /> 我已执行，等待回传
            </Button>
          </div>
        </div>
      </div>

      <!-- ── waiting：等待轮询 ── -->
      <div v-else-if="viewState === 'waiting' || viewState === 'confirmed' || viewState === 'failed' || viewState === 'timeout'"
        class="space-y-4">

        <!-- 等待中 -->
        <div v-if="viewState === 'waiting'"
          class="rounded-xl border border-sky-500/20 bg-sky-500/5 p-6 text-center space-y-3">
          <Loader2 class="h-8 w-8 animate-spin mx-auto text-sky-400" />
          <div>
            <p class="text-sm font-medium">等待目标机器回传…</p>
            <p class="text-xs text-muted-foreground/60 mt-1">脚本执行完毕后会自动回传，每 5 秒刷新一次。</p>
          </div>
          <div v-if="pollingSnapshot">
            <p class="text-[11px] text-muted-foreground/40">快照 {{ pollingSnapshot.id }}</p>
            <p v-if="pollingSnapshot.expires_at" class="text-[11px] text-muted-foreground/40">超时截止：{{ fmt(pollingSnapshot.expires_at) }}</p>
            <Badge v-if="pollingSnapshot.is_likely_timeout" variant="outline" class="text-[10px] text-amber-400 border-amber-500/20 mt-2">疑似已超时</Badge>
          </div>
          <p v-if="pollingError" class="text-[11px] text-amber-400">{{ pollingError }}</p>
          <button type="button" class="text-xs text-muted-foreground/40 hover:text-muted-foreground transition-colors" @click="reset">
            取消，重新生成
          </button>
        </div>

        <!-- 已确认 -->
        <div v-else-if="viewState === 'confirmed'"
          class="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-6 text-center space-y-3">
          <div class="h-10 w-10 rounded-full bg-emerald-500/20 flex items-center justify-center mx-auto">
            <Check class="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <p class="text-sm font-semibold text-emerald-400">同步成功！</p>
            <p class="text-xs text-muted-foreground/60 mt-1">配置已同步到运行态 Agent。</p>
          </div>
          <p v-if="pollingSnapshot" class="text-[11px] text-muted-foreground/40">确认时间：{{ fmt(pollingSnapshot.confirmed_at) }}</p>
          <Button variant="outline" size="sm" @click="reset">继续管理</Button>
        </div>

        <!-- 失败 -->
        <div v-else-if="viewState === 'failed'"
          class="rounded-xl border border-rose-500/20 bg-rose-500/5 p-6 text-center space-y-3">
          <AlertCircle class="h-7 w-7 mx-auto text-rose-400" />
          <div>
            <p class="text-sm font-medium text-rose-400">同步失败</p>
            <p class="text-xs text-muted-foreground/60 mt-1">请检查错误信息后重新生成脚本。</p>
          </div>
          <p v-if="pollingSnapshot?.failure_detail_json" class="text-xs text-rose-300 break-all text-left bg-rose-500/10 rounded-lg p-3">
            {{ pollingSnapshot.failure_detail_json }}
          </p>
          <Button variant="outline" @click="reset">重新生成</Button>
        </div>

        <!-- 超时 -->
        <div v-else-if="viewState === 'timeout'"
          class="rounded-xl border border-amber-500/20 bg-amber-500/5 p-6 text-center space-y-3">
          <Clock class="h-7 w-7 mx-auto text-amber-400" />
          <div>
            <p class="text-sm font-medium text-amber-400">等待超时</p>
            <p class="text-xs text-muted-foreground/60 mt-1 leading-relaxed">目标机器在有效期内未回传结果，请重新生成脚本后再次尝试。</p>
          </div>
          <Button variant="outline" @click="reset">重新生成</Button>
        </div>
      </div>
    </template>
  </div>
</template>
