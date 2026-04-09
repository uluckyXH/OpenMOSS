<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentScheduleApi,
  type ManagedAgentSchedule,
  type ManagedAgentScheduleCreateInput,
  type ManagedAgentScheduleUpdateInput,
  type ManagedAgentScheduleType,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

import {
  Loader2, AlertCircle, Clock, Plus, Pencil, Trash2, Power, PowerOff,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; disabled?: boolean }>();

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
const form = ref<ManagedAgentScheduleCreateInput>({
  name: '', enabled: true, schedule_type: 'interval',
  schedule_expr: '15m', timeout_seconds: 1800,
  model_override: '', execution_options_json: '', schedule_message_content: '',
});

// ─── 删除状态 ───

const deletingId = ref<string | null>(null);

// ─── 类型选项 ───

const typeOptions: { value: ManagedAgentScheduleType; label: string }[] = [
  { value: 'interval', label: '间隔' },
  { value: 'cron', label: 'Cron' },
];

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
  showForm.value = true;
}

async function handleSave() {
  if (!form.value.name.trim()) { saveError.value = '名称不能为空'; return; }
  saving.value = true;
  saveError.value = '';
  try {
    const payload = {
      ...form.value,
      name: form.value.name.trim(),
      model_override: form.value.model_override?.trim() || undefined,
      execution_options_json: form.value.execution_options_json?.trim() || undefined,
      schedule_message_content: form.value.schedule_message_content?.trim() || undefined,
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

async function handleDelete(id: string) {
  deletingId.value = id;
  try {
    await managedAgentScheduleApi.remove(props.agentId, id);
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
        <span class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">定时任务</span>
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
      class="rounded-xl border bg-card p-4 animate-slide-up transition-all"
      :style="{ animationDelay: `${idx * 30}ms` }">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-1">
            <span class="text-sm font-medium">{{ item.name }}</span>
            <Badge variant="outline" class="text-[10px]"
              :class="item.enabled ? 'text-emerald-400 border-emerald-500/20' : 'text-zinc-400 border-zinc-500/20'">
              {{ item.enabled ? '启用' : '禁用' }}
            </Badge>
            <Badge variant="outline" class="text-[10px] text-muted-foreground">
              {{ item.schedule_type === 'interval' ? '间隔' : 'Cron' }}
            </Badge>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span class="font-mono">{{ item.schedule_expr }}</span>
            <span>超时 {{ item.timeout_seconds }}s</span>
            <span v-if="item.model_override">模型 {{ item.model_override }}</span>
            <span class="text-muted-foreground/40">{{ formatDate(item.updated_at) }}</span>
          </div>
          <p v-if="item.schedule_message_content"
            class="mt-1.5 text-xs text-muted-foreground/60 line-clamp-2 leading-relaxed">
            {{ item.schedule_message_content }}
          </p>
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
            :disabled="deletingId === item.id" @click="handleDelete(item.id)">
            <Loader2 v-if="deletingId === item.id" class="h-3 w-3 animate-spin" />
            <Trash2 v-else class="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>

    <!-- ─── 创建/编辑弹窗 ─── -->
    <Teleport to="body">
      <div v-if="showForm"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showForm = false" />
        <div
          class="relative z-10 w-full max-w-md max-h-[85vh] overflow-y-auto rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
          <h3 class="text-base font-semibold mb-4">{{ formMode === 'create' ? '新增定时任务' : '编辑定时任务' }}</h3>

          <div class="space-y-3">
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">名称 <span class="text-rose-500">*</span></label>
              <Input v-model="form.name" placeholder="任务名称" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-xs text-muted-foreground mb-1 block">类型</label>
                <div class="flex gap-1.5">
                  <Button v-for="opt in typeOptions" :key="opt.value" size="sm"
                    :variant="form.schedule_type === opt.value ? 'default' : 'outline'" class="flex-1 h-8 text-xs"
                    @click="form.schedule_type = opt.value">
                    {{ opt.label }}
                  </Button>
                </div>
              </div>
              <div>
                <label class="text-xs text-muted-foreground mb-1 block">表达式</label>
                <Input v-model="form.schedule_expr"
                  :placeholder="form.schedule_type === 'interval' ? '15m' : '*/15 * * * *'" class="font-mono text-sm" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-xs text-muted-foreground mb-1 block">超时 (秒)</label>
                <Input v-model.number="form.timeout_seconds" type="number" min="60" />
              </div>
              <div>
                <label class="text-xs text-muted-foreground mb-1 block">模型覆盖</label>
                <Input v-model="form.model_override" placeholder="可选" class="text-sm" />
              </div>
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">唤醒消息</label>
              <textarea v-model="form.schedule_message_content" rows="3"
                class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                placeholder="定时触发时发给 Agent 的消息（可选）" />
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">执行选项 (JSON)</label>
              <textarea v-model="form.execution_options_json" rows="2"
                class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                placeholder='{"key": "value"}' />
            </div>
          </div>

          <p v-if="saveError" class="text-xs text-rose-500 mt-3">{{ saveError }}</p>

          <div class="flex gap-3 mt-4">
            <Button variant="outline" class="flex-1" :disabled="saving" @click="showForm = false">取消</Button>
            <Button class="flex-1" :disabled="saving" @click="handleSave">
              <Loader2 v-if="saving" class="h-4 w-4 animate-spin mr-1" />
              {{ formMode === 'create' ? '创建' : '保存' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
