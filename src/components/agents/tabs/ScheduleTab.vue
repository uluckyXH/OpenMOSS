<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { marked } from 'marked';
import {
  managedAgentScheduleApi,
  managedAgentMetaApi,
  type ManagedAgentSchedule,
  type ManagedAgentScheduleCreateInput,
  type ManagedAgentScheduleUpdateInput,
  type ManagedAgentScheduleType,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

import {
  Loader2, AlertCircle, Clock, Plus, Pencil, Trash2, Power, PowerOff, ChevronDown, ArrowRight, ArrowLeft, Eye, Code, MessageSquare, FileText, Info,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; agentRole?: string; disabled?: boolean }>();

// ─── 列表状态 ───

const items = ref<ManagedAgentSchedule[]>([]);
const loading = ref(false);
const loadError = ref('');

// ─── 弹窗状态 ───

const showForm = ref(false);
const formMode = ref<'create' | 'edit'>('create');
const editingId = ref<string | null>(null);
const saving = ref(false);
const saveError = ref('');
const formStep = ref(1);
const totalSteps = 3;

// 本地草稿（创建时一次性提交）
const form = ref<ManagedAgentScheduleCreateInput>({
  name: '', enabled: true, schedule_type: 'interval',
  schedule_expr: '15m', timeout_seconds: 1800,
  model_override: '', execution_options_json: '', schedule_message_content: '',
});

// ─── 删除状态 ───

const deletingId = ref<string | null>(null);
const pendingDeleteItem = ref<ManagedAgentSchedule | null>(null);

// ─── 列表预览展开 ───
const expandedPreviews = ref<Set<string>>(new Set());
// function togglePreview(id: string) {
//   if (expandedPreviews.value.has(id)) expandedPreviews.value.delete(id);
//   else expandedPreviews.value.add(id);
// }

// ─── 类型选项 ───

const typeOptions: { value: ManagedAgentScheduleType; label: string; desc: string }[] = [
  { value: 'interval', label: '固定间隔', desc: '按固定时间间隔触发，如每 15 分钟' },
  { value: 'cron', label: 'Cron 表达式', desc: '按 Cron 规则触发，支持复杂周期' },
];

const intervalPresets = [
  { value: '5m', label: '每 5 分钟' },
  { value: '15m', label: '每 15 分钟' },
  { value: '30m', label: '每 30 分钟' },
  { value: '1h', label: '每小时' },
  { value: '2h', label: '每 2 小时' },
  { value: '6h', label: '每 6 小时' },
  { value: '1d', label: '每天' },
];

const cronPresets = [
  { value: '*/5 * * * *', label: '每 5 分钟' },
  { value: '*/15 * * * *', label: '每 15 分钟' },
  { value: '0 * * * *', label: '每小时整点' },
  { value: '0 9 * * *', label: '每天 9:00' },
  { value: '0 9 * * 1-5', label: '工作日 9:00' },
  { value: '0 0 * * 0', label: '每周日 0:00' },
];

const timeoutPresets = [
  { value: 300, label: '5 分钟' },
  { value: 900, label: '15 分钟' },
  { value: 1800, label: '30 分钟' },
  { value: 3600, label: '1 小时' },
  { value: 7200, label: '2 小时' },
];

function handleTypeChange(type: ManagedAgentScheduleType) {
  form.value.schedule_type = type;
  form.value.schedule_expr = type === 'interval' ? '15m' : '*/15 * * * *';
  showCronBuilder.value = type === 'cron';
}

// ─── Cron 可视化组装器 ───

const showCronBuilder = ref(false);
type CronParts = [string, string, string, string, string];
const DEFAULT_CRON_PARTS: CronParts = ['*', '*', '*', '*', '*'];

const cronFields = [
  {
    key: 'minute', label: '分钟', options: [
      { value: '*', label: '每分钟' },
      { value: '*/5', label: '每 5 分钟' },
      { value: '*/10', label: '每 10 分钟' },
      { value: '*/15', label: '每 15 分钟' },
      { value: '*/30', label: '每 30 分钟' },
      { value: '0', label: '整点 (0)' },
      { value: '15', label: '15 分' },
      { value: '30', label: '30 分' },
      { value: '45', label: '45 分' },
    ]
  },
  {
    key: 'hour', label: '小时', options: [
      { value: '*', label: '每小时' },
      { value: '*/2', label: '每 2 小时' },
      { value: '*/6', label: '每 6 小时' },
      { value: '0', label: '0:00' },
      { value: '6', label: '6:00' },
      { value: '9', label: '9:00' },
      { value: '12', label: '12:00' },
      { value: '18', label: '18:00' },
      { value: '21', label: '21:00' },
    ]
  },
  {
    key: 'day', label: '日', options: [
      { value: '*', label: '每天' },
      { value: '1', label: '1 号' },
      { value: '15', label: '15 号' },
      { value: '1,15', label: '1 和 15 号' },
    ]
  },
  {
    key: 'month', label: '月', options: [
      { value: '*', label: '每月' },
      { value: '1', label: '1 月' },
      { value: '*/3', label: '每季度' },
      { value: '*/6', label: '每半年' },
    ]
  },
  {
    key: 'weekday', label: '星期', options: [
      { value: '*', label: '不限' },
      { value: '1-5', label: '工作日' },
      { value: '0,6', label: '周末' },
      { value: '1', label: '周一' },
      { value: '5', label: '周五' },
      { value: '0', label: '周日' },
    ]
  },
];

const cronParts = computed<CronParts>(() => {
  const scheduleExpr = form.value.schedule_expr ?? '';
  const parts = scheduleExpr.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 5) {
    const [minute = '*', hour = '*', day = '*', month = '*', weekday = '*'] = parts;
    return [minute, hour, day, month, weekday];
  }
  return [...DEFAULT_CRON_PARTS];
});

function setCronPart(index: number, value: string) {
  const parts = [...cronParts.value];
  parts[index] = value;
  form.value.schedule_expr = parts.join(' ');
}

function getCronPartLabel(fieldIdx: number): string {
  const val = cronParts.value[fieldIdx] ?? DEFAULT_CRON_PARTS[fieldIdx] ?? '*';
  const field = cronFields[fieldIdx];
  return field?.options.find(o => o.value === val)?.label ?? val;
}

const cronDescription = computed(() => {
  const [min, hour, day, month, weekday] = cronParts.value;
  const parts: string[] = [];

  if (weekday === '1-5') parts.push('工作日');
  else if (weekday === '0,6') parts.push('周末');
  else if (weekday !== '*') parts.push(`星期${weekday}`);

  if (month !== '*') parts.push(`${month}月`);
  if (day !== '*') parts.push(`${day}号`);

  if (hour !== '*' && min !== '*') parts.push(`${hour}:${min.padStart(2, '0')}`);
  else if (hour !== '*') parts.push(`${hour}点`);
  else if (min.startsWith('*/')) parts.push(`每 ${min.slice(2)} 分钟`);
  else if (min !== '*') parts.push(`第 ${min} 分钟`);

  return parts.length ? parts.join('，') + ' 执行' : '每分钟执行';
});

// ─── 超时可读转换 ───

const timeoutReadable = computed(() => {
  const s = form.value.timeout_seconds;
  if (!s || s < 60) return '';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (h > 0 && m > 0) return `${h} 小时 ${m} 分钟`;
  if (h > 0) return `${h} 小时`;
  return `${m} 分钟`;
});

// ─── 步骤校验 ───

const stepErrors = computed(() => {
  const errs: Record<number, string> = {};
  if (!form.value.name.trim()) errs[1] = '请填写任务名称';
  else if (!form.value.schedule_expr.trim()) errs[1] = '请设置调度表达式';
  if (!form.value.schedule_message_content?.trim()) errs[2] = '唤醒消息不能为空';
  return errs;
});

function canProceed(step: number): boolean {
  return !stepErrors.value[step];
}

function nextStep() {
  if (canProceed(formStep.value) && formStep.value < totalSteps) {
    formStep.value++;
  }
}

function prevStep() {
  if (formStep.value > 1) formStep.value--;
}

// ─── Markdown 渲染 ───

function renderMarkdown(content: string): string {
  if (!content) return '';
  return marked(content) as string;
}

// 编辑弹窗的预览 Tab
const messageEditorTab = ref<'edit' | 'preview'>('edit');

// ─── 从 Prompt 填充 ───

const fillingPrompt = ref(false);
const showFillNotice = ref(false);
const showOverwriteConfirm = ref(false);

function fillFromPrompt() {
  // 如果已有内容，先弹自定义确认框
  if (form.value.schedule_message_content?.trim()) {
    showOverwriteConfirm.value = true;
    return;
  }
  doFillFromPrompt();
}

async function doFillFromPrompt() {
  showOverwriteConfirm.value = false;
  fillingPrompt.value = true;
  try {
    const res = await managedAgentMetaApi.getPromptTemplates(props.agentRole);
    const templates = res.data.items;
    if (!templates?.length) {
      toast.warning('当前角色暂无可用的示例提示词模板。');
      return;
    }
    // 优先使用匹配角色的，否则用第一个
    const tpl = (props.agentRole && templates.find(t => t.role === props.agentRole)) || templates[0];
    if (!tpl) {
      toast.warning('当前角色暂无可用的示例提示词模板。');
      return;
    }
    form.value.schedule_message_content = tpl.content;
    showFillNotice.value = true;
    messageEditorTab.value = 'edit';
    toast.success(`已填入「${tpl.label}」角色的示例提示词。`);
  } catch {
    toast.error('获取示例提示词失败');
  } finally {
    fillingPrompt.value = false;
  }
}

// ─── 加载 ───

async function loadItems() {
  loading.value = true;
  loadError.value = '';
  try {
    const res = await managedAgentScheduleApi.list(props.agentId);
    items.value = res.data;
  } catch {
    loadError.value = '加载定时任务失败';
  } finally {
    loading.value = false;
  }
}

onMounted(() => { void loadItems(); });
watch(() => props.agentId, () => { showForm.value = false; void loadItems(); });

// ─── 表单操作 ───

function openCreate() {
  form.value = {
    name: '', enabled: true, schedule_type: 'interval',
    schedule_expr: '15m', timeout_seconds: 1800,
    model_override: '', execution_options_json: '', schedule_message_content: '',
  };
  formMode.value = 'create';
  editingId.value = null;
  saveError.value = '';
  formStep.value = 1;
  showCronBuilder.value = false;
  messageEditorTab.value = 'edit';
  showFillNotice.value = false;
  showForm.value = true;
}

function openEdit(item: ManagedAgentSchedule) {
  form.value = {
    name: item.name, enabled: item.enabled, schedule_type: item.schedule_type,
    schedule_expr: item.schedule_expr, timeout_seconds: item.timeout_seconds,
    model_override: item.model_override ?? '', execution_options_json: item.execution_options_json ?? '',
    schedule_message_content: item.schedule_message_content ?? '',
  };
  formMode.value = 'edit';
  editingId.value = item.id;
  saveError.value = '';
  formStep.value = 1;
  showCronBuilder.value = item.schedule_type === 'cron';
  messageEditorTab.value = 'edit';
  showFillNotice.value = false;
  showForm.value = true;
}

async function handleSave() {
  // 校验所有步骤
  if (stepErrors.value[1]) { formStep.value = 1; saveError.value = stepErrors.value[1]; return; }
  if (stepErrors.value[2]) { formStep.value = 2; saveError.value = stepErrors.value[2]; return; }

  saving.value = true;
  saveError.value = '';
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      schedule_message_content: form.value.schedule_message_content.trim(),
      model_override: form.value.model_override?.trim() || undefined,
      execution_options_json: form.value.execution_options_json?.trim() || undefined,
    };
    if (formMode.value === 'create') {
      await managedAgentScheduleApi.create(props.agentId, payload);
      toast.success('定时任务已创建');
    } else if (editingId.value) {
      await managedAgentScheduleApi.update(props.agentId, editingId.value, payload as ManagedAgentScheduleUpdateInput);
      toast.success('定时任务已更新');
    }
    showForm.value = false;
    void loadItems();
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    saveError.value = msg ?? '保存失败';
  } finally {
    saving.value = false;
  }
}

// ─── 删除 ───

function confirmDelete(item: ManagedAgentSchedule) {
  pendingDeleteItem.value = item;
}

async function executeDelete() {
  const item = pendingDeleteItem.value;
  if (!item) return;
  deletingId.value = item.id;
  pendingDeleteItem.value = null;
  try {
    await managedAgentScheduleApi.remove(props.agentId, item.id);
    toast.success('已删除');
    void loadItems();
  } catch {
    toast.error('删除失败');
  } finally {
    deletingId.value = null;
  }
}

// ─── 快捷启用/禁用 ───

async function toggleEnabled(item: ManagedAgentSchedule) {
  try {
    await managedAgentScheduleApi.update(props.agentId, item.id, { enabled: !item.enabled });
    item.enabled = !item.enabled;
    toast.success(item.enabled ? '已启用' : '已禁用');
  } catch {
    toast.error('操作失败');
  }
}

// ─── 辅助 ───

function formatDate(value: string | null) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit',
    });
  } catch { return value; }
}

// 步骤信息
const steps = [
  { num: 1, label: '调度配置' },
  { num: 2, label: '唤醒消息' },
  { num: 3, label: '高级选项' },
];
</script>

<template>
  <!-- 加载态 -->
  <div v-if="loading" class="flex items-center justify-center py-16">
    <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
  </div>

  <!-- 错误态 -->
  <div v-else-if="loadError" class="flex flex-col items-center py-16 text-muted-foreground">
    <AlertCircle class="h-6 w-6 mb-2 text-rose-400" />
    <p class="text-sm">{{ loadError }}</p>
    <Button variant="link" size="sm" class="mt-2" @click="loadItems">重试</Button>
  </div>

  <!-- 正常 -->
  <div v-else class="space-y-4 animate-slide-up">
    <!-- 顶栏 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xs font-medium text-muted-foreground uppercase tracking-wider">定时任务</span>
        <Badge variant="outline" class="text-[10px] tabular-nums">{{ items.length }}</Badge>
      </div>
      <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="disabled" @click="openCreate">
        <Plus class="h-3 w-3" /> 新增
      </Button>
    </div>

    <!-- 空态 -->
    <div v-if="items.length === 0 && !showForm"
      class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
      <Clock class="h-8 w-8 mx-auto mb-3 text-muted-foreground/30" />
      <p class="text-sm text-muted-foreground">暂无定时任务</p>
    </div>

    <!-- 列表 -->
    <div v-for="(item, idx) in items" :key="item.id"
      class="group rounded-xl border bg-card overflow-hidden animate-slide-up transition-all hover:border-border/60 hover:shadow-sm"
      :style="{ animationDelay: `${idx * 30}ms` }">
      <div class="p-4">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 mb-1.5">
              <span class="text-sm font-semibold">{{ item.name }}</span>
              <Badge variant="outline" class="text-[10px] gap-1" :class="item.enabled
                ? 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5'
                : 'text-zinc-400 border-zinc-500/20 bg-zinc-500/5'">
                <span class="h-1.5 w-1.5 rounded-full" :class="item.enabled ? 'bg-emerald-400' : 'bg-zinc-400'" />
                {{ item.enabled ? '启用' : '禁用' }}
              </Badge>
              <Badge variant="outline" class="text-[10px] text-muted-foreground/70 bg-muted/20">
                {{ item.schedule_type === 'interval' ? '固定间隔' : 'Cron' }}
              </Badge>
            </div>
            <!-- 元信息行 -->
            <div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground/60">
              <span class="inline-flex items-center gap-1 font-mono bg-muted/20 px-1.5 py-0.5 rounded text-[11px]">
                <Clock class="h-3 w-3 text-muted-foreground/40" />{{ item.schedule_expr }}
              </span>
              <span class="inline-flex items-center gap-1"><span class="text-muted-foreground/30">超时</span> {{
                item.timeout_seconds }}s</span>
              <span v-if="item.model_override" class="inline-flex items-center gap-1"><span
                  class="text-muted-foreground/30">模型</span> {{ item.model_override }}</span>
              <span class="text-muted-foreground/30 ml-auto text-[11px]">{{ formatDate(item.updated_at) }}</span>
            </div>
            <!-- 唤醒消息预览 -->
            <div v-if="item.schedule_message_content" class="mt-3 rounded-lg border border-border/20 overflow-hidden">
              <div class="flex items-center justify-between px-3 py-1.5 border-b border-border/10 bg-muted/10">
                <div class="flex items-center gap-1.5">
                  <MessageSquare class="h-3 w-3 text-primary/40" />
                  <span class="text-[10px] text-muted-foreground/50 font-medium">唤醒消息</span>
                </div>
                <button v-if="item.schedule_message_content.split('\n').length > 4"
                  class="text-[10px] text-muted-foreground/40 hover:text-muted-foreground transition-colors"
                  @click="expandedPreviews.has(item.id) ? expandedPreviews.delete(item.id) : expandedPreviews.add(item.id)">
                  {{ expandedPreviews.has(item.id) ? '收起' : '展开' }}
                </button>
              </div>
              <div class="px-3 py-2 bg-muted/5">
                <div class="relative">
                  <div class="prose prose-sm dark:prose-invert max-w-none text-foreground/80 text-xs"
                    :class="{ 'max-h-36 overflow-hidden': !expandedPreviews.has(item.id) }"
                    v-html="renderMarkdown(item.schedule_message_content)" />
                  <div v-if="!expandedPreviews.has(item.id) && item.schedule_message_content.split('\n').length > 4"
                    class="absolute bottom-0 left-0 right-0 h-12 bg-gradient-to-t from-muted/30 to-transparent flex items-end justify-center pb-0.5">
                    <button
                      class="text-[11px] text-primary/70 hover:text-primary font-medium transition-colors bg-background/80 backdrop-blur-sm px-2.5 py-0.5 rounded-full border border-border/30 shadow-sm"
                      @click="expandedPreviews.add(item.id)">
                      查看全部
                    </button>
                  </div>
                </div>
                <button v-if="expandedPreviews.has(item.id)"
                  class="text-[11px] text-muted-foreground/40 hover:text-muted-foreground mt-1.5 transition-colors"
                  @click="expandedPreviews.delete(item.id)">
                  收起
                </button>
              </div>
            </div>
          </div>
          <div class="flex gap-1 shrink-0">
            <Button variant="ghost" size="icon" class="h-7 w-7" @click="toggleEnabled(item)">
              <Power v-if="item.enabled" class="h-3.5 w-3.5 text-emerald-400" />
              <PowerOff v-else class="h-3.5 w-3.5 text-zinc-400" />
            </Button>
            <Button variant="ghost" size="icon" class="h-7 w-7" @click="openEdit(item)">
              <Pencil class="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="icon" class="h-7 w-7 text-rose-400 hover:text-rose-500"
              :disabled="deletingId === item.id" @click="confirmDelete(item)">
              <Loader2 v-if="deletingId === item.id" class="h-3 w-3 animate-spin" />
              <Trash2 v-else class="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- ─── 分步创建/编辑弹窗 ─── -->
    <Teleport to="body">
      <div v-if="showForm"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showForm = false" />
        <div
          class="relative z-10 w-full max-h-[85vh] overflow-y-auto rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 transition-[max-width] duration-300 ease-in-out"
          :class="formStep === 2 ? 'max-w-7xl' : 'max-w-2xl'">
          <h3 class="text-base font-semibold mb-1">{{ formMode === 'create' ? '新增定时任务' : '编辑定时任务' }}</h3>
          <p class="text-xs text-muted-foreground/60 mb-4">配置 Agent 的自动唤醒计划，定时触发执行任务。</p>

          <!-- 步骤指示器 -->
          <div class="flex items-center gap-1 mb-6">
            <template v-for="(step, i) in steps" :key="step.num">
              <button class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors"
                :class="formStep === step.num
                  ? 'bg-primary text-primary-foreground'
                  : formStep > step.num
                    ? 'bg-primary/10 text-primary cursor-pointer'
                    : 'bg-muted/30 text-muted-foreground/50'" @click="formStep > step.num && (formStep = step.num)">
                <span class="inline-flex items-center justify-center h-4 w-4 rounded-full text-[10px]"
                  :class="formStep > step.num ? 'bg-primary/20' : ''">
                  {{ formStep > step.num ? '✓' : step.num }}
                </span>
                {{ step.label }}
              </button>
              <ArrowRight v-if="i < steps.length - 1" class="h-3 w-3 text-muted-foreground/30 shrink-0" />
            </template>
          </div>

          <!-- ═══ Step 1: 调度配置 ═══ -->
          <div v-show="formStep === 1" class="space-y-4">
            <!-- 名称 -->
            <div>
              <label class="text-xs text-muted-foreground font-medium mb-1 block">任务名称 <span
                  class="text-rose-500">*</span></label>
              <Input v-model="form.name" placeholder="例如：每日巡检、定时同步…" />
            </div>

            <!-- 调度类型 -->
            <div>
              <label class="text-xs text-muted-foreground font-medium mb-1.5 block">调度类型 <span
                  class="text-rose-500">*</span></label>
              <div class="grid grid-cols-2 gap-2">
                <button v-for="opt in typeOptions" :key="opt.value"
                  class="rounded-lg border p-3 text-left transition-all" :class="form.schedule_type === opt.value
                    ? 'border-primary bg-primary/5 ring-1 ring-primary/20'
                    : 'border-border hover:border-border/80'" @click="handleTypeChange(opt.value)">
                  <div class="text-sm font-medium">{{ opt.label }}</div>
                  <div class="text-[11px] text-muted-foreground/60 mt-0.5">{{ opt.desc }}</div>
                </button>
              </div>
            </div>

            <!-- 调度表达式 -->
            <div>
              <label class="text-xs text-muted-foreground font-medium mb-1 block">
                {{ form.schedule_type === 'interval' ? '执行间隔' : 'Cron 表达式' }} <span class="text-rose-500">*</span>
              </label>
              <Input v-model="form.schedule_expr"
                :placeholder="form.schedule_type === 'interval' ? '15m' : '*/15 * * * *'" class="font-mono text-sm" />
              <!-- 快捷选择 -->
              <div class="flex flex-wrap gap-1.5 mt-2">
                <template v-if="form.schedule_type === 'interval'">
                  <button v-for="p in intervalPresets" :key="p.value"
                    class="px-2 py-0.5 text-[11px] rounded-md border transition-colors"
                    :class="form.schedule_expr === p.value ? 'bg-primary/10 border-primary/30 text-primary' : 'border-border/40 text-muted-foreground/60 hover:border-border hover:text-muted-foreground'"
                    @click="form.schedule_expr = p.value">
                    {{ p.label }}
                  </button>
                </template>
                <template v-else>
                  <button v-for="p in cronPresets" :key="p.value"
                    class="px-2 py-0.5 text-[11px] rounded-md border transition-colors"
                    :class="form.schedule_expr === p.value ? 'bg-primary/10 border-primary/30 text-primary' : 'border-border/40 text-muted-foreground/60 hover:border-border hover:text-muted-foreground'"
                    @click="form.schedule_expr = p.value">
                    {{ p.label }}
                  </button>
                </template>
              </div>
              <p class="text-[11px] text-muted-foreground/50 mt-1.5">
                <template v-if="form.schedule_type === 'interval'">
                  支持格式：<code class="text-[10px] bg-muted/30 px-1 rounded">15m</code>（分钟）、<code
                    class="text-[10px] bg-muted/30 px-1 rounded">2h</code>（小时）、<code
                    class="text-[10px] bg-muted/30 px-1 rounded">1d</code>（天）
                </template>
                <template v-else>
                  标准 5 位 Cron：<code class="text-[10px] bg-muted/30 px-1 rounded">分 时 日 月 周</code>
                  <button class="ml-2 text-primary/60 hover:text-primary transition-colors"
                    @click="showCronBuilder = !showCronBuilder">
                    {{ showCronBuilder ? '收起组装器' : '可视化组装 →' }}
                  </button>
                </template>
              </p>
              <!-- Cron 可视化组装器 -->
              <div v-if="form.schedule_type === 'cron' && showCronBuilder"
                class="mt-3 rounded-lg border border-border/40 bg-muted/5 p-3 space-y-3">
                <div class="grid grid-cols-5 gap-2">
                  <div v-for="(field, idx) in cronFields" :key="field.key">
                    <label class="text-[10px] text-muted-foreground/60 mb-1 block text-center">{{ field.label }}</label>
                    <DropdownMenu>
                      <DropdownMenuTrigger as-child>
                        <button
                          class="w-full h-7 text-[11px] rounded-md border border-input bg-background hover:bg-muted/20 px-1.5 flex items-center justify-between gap-0.5 transition-colors focus:outline-none focus:ring-1 focus:ring-ring">
                          <span class="truncate">{{ getCronPartLabel(idx) }}</span>
                          <ChevronDown class="h-3 w-3 text-muted-foreground/40 shrink-0" />
                        </button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="center" class="min-w-[100px]">
                        <DropdownMenuRadioGroup :model-value="cronParts[idx]"
                          @update:model-value="setCronPart(idx, $event as string)">
                          <DropdownMenuRadioItem v-for="opt in field.options" :key="opt.value" :value="opt.value"
                            class="text-xs">
                            {{ opt.label }}
                          </DropdownMenuRadioItem>
                        </DropdownMenuRadioGroup>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
                <div class="flex items-center justify-between">
                  <span class="text-[11px] text-muted-foreground/60">结果：<code
                      class="font-mono bg-muted/30 px-1.5 py-0.5 rounded text-[10px]">{{ form.schedule_expr }}</code></span>
                  <span class="text-[11px] text-muted-foreground/50">≈ {{ cronDescription }}</span>
                </div>
              </div>
            </div>

            <!-- 超时 -->
            <div>
              <label class="text-xs text-muted-foreground font-medium mb-1 block">
                超时时间 <span class="text-rose-500">*</span>
                <span v-if="timeoutReadable" class="text-muted-foreground/40 font-normal ml-1">≈ {{ timeoutReadable
                  }}</span>
              </label>
              <Input v-model.number="form.timeout_seconds" type="number" min="60" />
              <div class="flex flex-wrap gap-1.5 mt-2">
                <button v-for="p in timeoutPresets" :key="p.value"
                  class="px-2 py-0.5 text-[11px] rounded-md border transition-colors"
                  :class="form.timeout_seconds === p.value ? 'bg-primary/10 border-primary/30 text-primary' : 'border-border/40 text-muted-foreground/60 hover:border-border hover:text-muted-foreground'"
                  @click="form.timeout_seconds = p.value">
                  {{ p.label }}
                </button>
              </div>
              <p class="text-[11px] text-muted-foreground/50 mt-1.5">
                任务执行超过此时间将被视为失败并终止。建议设置为预期耗时的 2–3 倍。
              </p>
            </div>
          </div>

          <!-- ═══ Step 2: 唤醒消息 ═══ -->
          <div v-show="formStep === 2" class="space-y-3">
            <div class="flex items-start justify-between gap-3">
              <div>
                <label class="text-xs text-muted-foreground font-medium mb-1 block">
                  唤醒消息 <span class="text-rose-500">*</span>
                </label>
                <p class="text-[11px] text-muted-foreground/50">
                  定时触发时发送给 Agent 的指令内容。相当于定时任务的“提示词”，告诉 Agent 被唤醒后该做什么。
                </p>
              </div>
              <Button variant="outline" size="sm" class="h-7 gap-1 text-xs shrink-0" :disabled="fillingPrompt"
                @click="fillFromPrompt">
                <Loader2 v-if="fillingPrompt" class="h-3 w-3 animate-spin" />
                <FileText v-else class="h-3 w-3" />
                从示例填充
              </Button>
            </div>

            <!-- 左右分栏：编辑 + 实时预览 -->
            <div class="grid grid-cols-2 gap-4">
              <!-- 左：编辑器 -->
              <div class="space-y-1.5">
                <div class="flex items-center gap-1.5 text-[11px] text-muted-foreground/60">
                  <Code class="h-3 w-3" />
                  <span class="font-medium">编辑</span>
                  <span class="text-muted-foreground/30">· Markdown</span>
                </div>
                <textarea v-model="form.schedule_message_content"
                  class="flex w-full rounded-lg border border-input bg-muted/5 px-3.5 py-2.5 text-sm font-mono placeholder:text-muted-foreground/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:bg-background resize-none leading-relaxed h-[520px] transition-colors"
                  placeholder="请检查今日待办事项并汇总，有紧急事项请立即通知…" />
              </div>
              <!-- 右：实时预览 -->
              <div class="space-y-1.5">
                <div class="flex items-center gap-1.5 text-[11px] text-muted-foreground/60">
                  <Eye class="h-3 w-3" />
                  <span class="font-medium">实时预览</span>
                </div>
                <div class="rounded-lg border border-border/50 bg-background px-4 py-3 h-[520px] overflow-y-auto">
                  <div v-if="form.schedule_message_content?.trim()"
                    class="prose prose-sm dark:prose-invert max-w-none text-foreground/90"
                    v-html="renderMarkdown(form.schedule_message_content)" />
                  <div v-else class="flex flex-col items-center justify-center h-full text-muted-foreground/30">
                    <Eye class="h-6 w-6 mb-2" />
                    <p class="text-xs">在左侧输入内容后这里会实时渲染预览</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ═══ Step 3: 高级选项 ═══ -->
          <div v-show="formStep === 3" class="space-y-4">
            <p class="text-xs text-muted-foreground/50">以下为可选配置，可留空使用默认值。</p>

            <!-- 模型覆盖 -->
            <div>
              <label class="text-xs text-muted-foreground font-medium mb-1 block">模型覆盖 <span
                  class="text-muted-foreground/40 font-normal">（可选）</span></label>
              <Input v-model="form.model_override" placeholder="留空使用平台默认模型" class="text-sm" />
              <p class="text-[11px] text-muted-foreground/50 mt-1">
                指定执行此任务的模型。留空则使用平台默认模型。
              </p>
              <div v-if="form.model_override?.trim()"
                class="flex items-start gap-2 mt-2 rounded-md border border-amber-500/20 bg-amber-500/5 px-2.5 py-2">
                <AlertCircle class="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
                <p class="text-[11px] text-amber-400/80 leading-relaxed">
                  请确保该模型在平台中正常可用，否则任务会执行失败。
                </p>
              </div>
            </div>

            <!-- 配置摘要 -->
            <div class="rounded-lg border border-border/30 bg-muted/5 p-4 space-y-2">
              <div class="text-xs font-medium text-muted-foreground mb-2">配置摘要</div>
              <div class="grid grid-cols-2 gap-y-1.5 text-xs">
                <span class="text-muted-foreground/60">任务名称</span>
                <span class="text-foreground">{{ form.name || '—' }}</span>
                <span class="text-muted-foreground/60">调度类型</span>
                <span class="text-foreground">{{ form.schedule_type === 'interval' ? '固定间隔' : 'Cron' }}</span>
                <span class="text-muted-foreground/60">调度表达式</span>
                <span class="text-foreground font-mono">{{ form.schedule_expr }}</span>
                <span class="text-muted-foreground/60">超时时间</span>
                <span class="text-foreground">{{ timeoutReadable || `${form.timeout_seconds}s` }}</span>
                <span class="text-muted-foreground/60">唤醒消息</span>
                <span class="text-foreground truncate">{{ form.schedule_message_content?.slice(0, 40) || '—' }}{{
                  (form.schedule_message_content?.length ?? 0) > 40 ? '…' : '' }}</span>
                <template v-if="form.model_override?.trim()">
                  <span class="text-muted-foreground/60">模型覆盖</span>
                  <span class="text-foreground">{{ form.model_override }}</span>
                </template>
              </div>
            </div>
          </div>

          <!-- 错误提示 -->
          <p v-if="saveError" class="text-xs text-rose-500 mt-3">{{ saveError }}</p>

          <!-- 底部按钮 -->
          <div class="flex gap-3 mt-5">
            <Button v-if="formStep > 1" variant="outline" class="gap-1" :disabled="saving" @click="prevStep">
              <ArrowLeft class="h-3.5 w-3.5" /> 上一步
            </Button>
            <div class="flex-1" />
            <Button variant="outline" :disabled="saving" @click="showForm = false">取消</Button>
            <Button v-if="formStep < totalSteps" class="gap-1" :disabled="!canProceed(formStep)" @click="nextStep">
              下一步
              <ArrowRight class="h-3.5 w-3.5" />
            </Button>
            <Button v-else class="gap-1" :disabled="saving" @click="handleSave">
              <Loader2 v-if="saving" class="h-4 w-4 animate-spin" />
              {{ formMode === 'create' ? '创建' : '保存' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ─── 删除确认弹窗 ─── -->
    <Teleport to="body">
      <div v-if="pendingDeleteItem"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="pendingDeleteItem = null" />
        <div
          class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 text-center space-y-3">
          <Trash2 class="h-8 w-8 mx-auto text-rose-400" />
          <h3 class="text-base font-semibold">删除定时任务</h3>
          <p class="text-sm text-muted-foreground">
            确定要删除「<span class="font-medium text-foreground">{{ pendingDeleteItem.name }}</span>」吗？此操作不可撤销。
          </p>
          <div class="flex gap-3 pt-2">
            <Button variant="outline" class="flex-1" @click="pendingDeleteItem = null">取消</Button>
            <Button variant="destructive" class="flex-1" @click="executeDelete">确认删除</Button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- ─── 覆盖确认弹窗 ─── -->
    <Teleport to="body">
      <div v-if="showOverwriteConfirm"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showOverwriteConfirm = false" />
        <div
          class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 text-center space-y-3">
          <FileText class="h-8 w-8 mx-auto text-amber-400" />
          <h3 class="text-base font-semibold">覆盖现有内容？</h3>
          <p class="text-sm text-muted-foreground">
            唤醒消息已有内容，从 Prompt 填充将<span class="font-medium text-foreground">替换当前全部内容</span>。
          </p>
          <div class="flex gap-3 pt-2">
            <Button variant="outline" class="flex-1" @click="showOverwriteConfirm = false">取消</Button>
            <Button class="flex-1" @click="doFillFromPrompt">确认覆盖</Button>
          </div>
        </div>
      </div>
    </Teleport>
    <!-- ─── 填充提示弹窗 ─── -->
    <Teleport to="body">
      <div v-if="showFillNotice"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" />
        <div
          class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 text-center space-y-3">
          <Info class="h-8 w-8 mx-auto text-amber-400" />
          <h3 class="text-base font-semibold">示例提示词已填入</h3>
          <p class="text-sm text-muted-foreground leading-relaxed">
            已将该角色的示例提示词填入作为基础内容。不同的模型可能需要调整对应的提示词，请根据实际任务需求<span
              class="font-medium text-foreground">修改和补充</span>具体的任务指令。
          </p>
          <Button class="w-full mt-2" @click="showFillNotice = false">OK 我了解了</Button>
        </div>
      </div>
    </Teleport>
  </div>
</template>
