<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentCommBindingApi,
  type ManagedAgentCommBinding,
  type ManagedAgentCommBindingCreateInput,
  type ManagedAgentCommBindingUpdateInput,
  type ManagedAgentCommProvider,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Loader2, AlertCircle, MessageSquare, Plus, Pencil, Trash2, Power, PowerOff, ChevronDown, ShieldAlert,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; disabled?: boolean }>();

// ─── 列表状态 ───

const items = ref<ManagedAgentCommBinding[]>([]);
const loading = ref(false);
const loadError = ref('');

// ─── 弹窗状态 ───

const showForm = ref(false);
const formMode = ref<'create' | 'edit'>('create');
const editingId = ref<string | null>(null);
const saving = ref(false);
const saveError = ref('');
const form = ref<ManagedAgentCommBindingCreateInput>({
  provider: 'feishu', binding_key: '', display_name: '',
  enabled: true, routing_policy_json: '', metadata_json: '', config_payload: '',
});

// ─── 删除状态 ───

const deletingId = ref<string | null>(null);

// ─── Provider 选项 ───

const providerOptions: { value: ManagedAgentCommProvider; label: string; color: string }[] = [
  { value: 'feishu', label: '飞书', color: 'text-blue-400 border-blue-500/20 bg-blue-500/10' },
  { value: 'slack', label: 'Slack', color: 'text-purple-400 border-purple-500/20 bg-purple-500/10' },
  { value: 'telegram', label: 'Telegram', color: 'text-sky-400 border-sky-500/20 bg-sky-500/10' },
  { value: 'wechat', label: '微信', color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10' },
  { value: 'email', label: '邮件', color: 'text-amber-400 border-amber-500/20 bg-amber-500/10' },
  { value: 'webhook', label: 'Webhook', color: 'text-zinc-400 border-zinc-500/20 bg-zinc-500/10' },
];

function getProviderOption(provider: string) {
  return providerOptions.find(p => p.value === provider) ?? { label: provider, color: 'text-muted-foreground' };
}

// ─── 加载 ───

async function loadItems() {
  loading.value = true;
  loadError.value = '';
  try {
    const res = await managedAgentCommBindingApi.list(props.agentId);
    items.value = res.data;
  } catch {
    loadError.value = '加载通讯渠道失败';
  } finally {
    loading.value = false;
  }
}

onMounted(() => { void loadItems(); });
watch(() => props.agentId, () => { showForm.value = false; void loadItems(); });

// ─── 表单操作 ───

function openCreate() {
  form.value = {
    provider: 'feishu', binding_key: '', display_name: '',
    enabled: true, routing_policy_json: '', metadata_json: '', config_payload: '',
  };
  formMode.value = 'create';
  editingId.value = null;
  saveError.value = '';
  showForm.value = true;
}

function openEdit(item: ManagedAgentCommBinding) {
  form.value = {
    provider: item.provider, binding_key: item.binding_key,
    display_name: item.display_name ?? '', enabled: item.enabled,
    routing_policy_json: item.routing_policy_json ?? '',
    metadata_json: item.metadata_json ?? '', config_payload: '',
  };
  formMode.value = 'edit';
  editingId.value = item.id;
  saveError.value = '';
  showForm.value = true;
}

async function handleSave() {
  if (!form.value.binding_key.trim()) { saveError.value = 'binding_key 不能为空'; return; }
  saving.value = true;
  saveError.value = '';
  try {
    const payload = {
      ...form.value,
      binding_key: form.value.binding_key.trim(),
      display_name: form.value.display_name?.trim() || undefined,
      routing_policy_json: form.value.routing_policy_json?.trim() || undefined,
      metadata_json: form.value.metadata_json?.trim() || undefined,
      config_payload: form.value.config_payload?.trim() || undefined,
    };
    if (formMode.value === 'create') {
      await managedAgentCommBindingApi.create(props.agentId, payload);
      toast.success('渠道已创建');
    } else if (editingId.value) {
      await managedAgentCommBindingApi.update(props.agentId, editingId.value, payload as ManagedAgentCommBindingUpdateInput);
      toast.success('渠道已更新');
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
    await managedAgentCommBindingApi.remove(props.agentId, id);
    toast.success('已删除');
    void loadItems();
  } catch {
    toast.error('删除失败');
  } finally {
    deletingId.value = null;
  }
}

// ─── 快捷启用/禁用 ───

async function toggleEnabled(item: ManagedAgentCommBinding) {
  try {
    await managedAgentCommBindingApi.update(props.agentId, item.id, { enabled: !item.enabled });
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
        <span class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">通讯渠道</span>
        <Badge variant="outline" class="text-[10px] tabular-nums">{{ items.length }}</Badge>
      </div>
      <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="disabled" @click="openCreate">
        <Plus class="h-3 w-3" /> 新增
      </Button>
    </div>

    <!-- 空态 -->
    <div v-if="items.length === 0 && !showForm"
      class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
      <MessageSquare class="h-8 w-8 mx-auto mb-3 text-muted-foreground/30" />
      <p class="text-sm text-muted-foreground">暂无通讯渠道</p>
    </div>

    <!-- 列表 -->
    <div v-for="(item, idx) in items" :key="item.id"
      class="rounded-xl border bg-card p-4 animate-slide-up transition-all"
      :style="{ animationDelay: `${idx * 30}ms` }">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 mb-1 flex-wrap">
            <Badge variant="outline" class="text-[10px]" :class="getProviderOption(item.provider).color">
              {{ getProviderOption(item.provider).label }}
            </Badge>
            <span class="text-sm font-medium font-mono">{{ item.binding_key }}</span>
            <span v-if="item.display_name" class="text-xs text-muted-foreground">{{ item.display_name }}</span>
            <Badge variant="outline" class="text-[10px]"
              :class="item.enabled ? 'text-emerald-400 border-emerald-500/20' : 'text-zinc-400 border-zinc-500/20'">
              {{ item.enabled ? '启用' : '禁用' }}
            </Badge>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground/50">
            <span v-if="item.config_payload_masked" class="flex items-center gap-1">
              <ShieldAlert class="h-3 w-3" /> 已配置密钥
            </span>
            <span>{{ formatDate(item.updated_at) }}</span>
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
          <h3 class="text-base font-semibold mb-4">{{ formMode === 'create' ? '新增通讯渠道' : '编辑通讯渠道' }}</h3>

          <div class="space-y-3">
            <div>
              <label class="text-xs text-muted-foreground mb-1.5 block">渠道类型 <span
                  class="text-rose-500">*</span></label>
              <DropdownMenu>
                <DropdownMenuTrigger as-child>
                  <Button variant="outline" size="sm" class="h-8 w-full justify-between text-xs font-normal">
                    {{ getProviderOption(form.provider).label }}
                    <ChevronDown class="h-3 w-3 opacity-50" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" class="min-w-[160px]">
                  <DropdownMenuRadioGroup :model-value="form.provider"
                    @update:model-value="(v) => form.provider = String(v) as ManagedAgentCommProvider">
                    <DropdownMenuRadioItem v-for="opt in providerOptions" :key="opt.value" :value="opt.value">
                      {{ opt.label }}
                    </DropdownMenuRadioItem>
                  </DropdownMenuRadioGroup>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">Binding Key <span
                  class="text-rose-500">*</span></label>
              <Input v-model="form.binding_key" placeholder="唯一绑定标识" class="font-mono text-sm" />
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">显示名称</label>
              <Input v-model="form.display_name" placeholder="可选，用于展示" />
            </div>

            <Separator />

            <div>
              <label class="text-xs text-muted-foreground mb-1 block">
                渠道配置
                <Badge variant="outline" class="text-[9px] ml-1.5 text-amber-600 border-amber-300">敏感</Badge>
              </label>
              <p class="text-[11px] text-muted-foreground/50 mb-1.5">留空表示不修改现有值。</p>
              <textarea v-model="form.config_payload" rows="3"
                class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                placeholder="配置内容（明文输入，保存后脱敏展示）" />
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">路由策略 (JSON)</label>
              <textarea v-model="form.routing_policy_json" rows="2"
                class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                placeholder='{"key": "value"}' />
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">元数据 (JSON)</label>
              <textarea v-model="form.metadata_json" rows="2"
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
