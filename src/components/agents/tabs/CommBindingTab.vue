<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentFeishuCommBindingApi,
  managedAgentMetaApi,
  type CommProviderSchema,
  type CommProviderSchemaField,
  type FeishuCommBinding,
  type FeishuCommBindingCreateInput,
  type FeishuCommBindingUpdateInput,
} from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Switch } from '@/components/ui/switch';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import {
  AlertCircle,
  ChevronRight,
  Info,
  Loader2,
  MessageSquare,
  Pencil,
  Plus,
  Power,
  PowerOff,
  ShieldAlert,
  Trash2,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; hostPlatform?: string; disabled?: boolean }>();
const emit = defineEmits<{ saved: [] }>();

interface FeishuBindingFormState {
  account_id: string
  app_id: string
  app_secret: string
  account_name: string
  enabled: boolean
}

const FALLBACK_SCHEMA: CommProviderSchema = {
  provider: 'feishu',
  label: '飞书（Feishu）',
  description: [
    '为 Agent 配置飞书通讯渠道。',
    '绑定后即可在飞书中与该 Agent 对话，Agent 通过飞书机器人自动收发消息。',
    '支持绑定多个飞书账号，对应不同的飞书应用。',
  ].join(''),
  supports_multiple_bindings: true,
  fields: [
    {
      key: 'account_id',
      label: 'OpenClaw 内部账号标识',
      type: 'text',
      required: false,
      advanced: true,
      placeholder: '留空自动生成（推荐）',
      description: [
        'OpenClaw 中用于标识这条飞书机器人账号配置的内部 key。',
        '对应的账号配置会在 OpenClaw 中保存该机器人的 app_id、app_secret 等信息。',
        '它不是飞书官方账号 ID，也不是在飞书侧看到的名称，而是 OpenClaw 内部用来区分、存储和引用这条飞书机器人配置的键。',
        '留空时系统会根据当前 Agent 的 OpenClaw Agent ID 自动生成。',
      ].join(''),
    },
    {
      key: 'app_id',
      label: '飞书 App ID',
      type: 'text',
      required: true,
      placeholder: 'cli_xxx',
      description: '飞书开放平台的应用凭证，可在「凭证与基础信息」页面获取。',
    },
    {
      key: 'app_secret',
      label: '飞书 App Secret',
      type: 'password',
      required: true,
      sensitive: true,
      placeholder: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
      description: '飞书应用密钥，与 App ID 配对使用，可在「凭证与基础信息」页面获取。提交后加密存储。',
    },
    {
      key: 'account_name',
      label: '账号备注名',
      type: 'text',
      required: false,
      placeholder: '我的飞书助手',
      description: [
        '给 OpenClaw 配置中这条飞书账号写的备注名。',
        '主要用于自己识别和管理，不是功能性参数；可能会在部分界面展示，但不保证处处显示，不填也不影响飞书绑定本身。',
      ].join(''),
    },
    {
      key: 'enabled',
      label: '是否启用',
      type: 'switch',
      required: false,
      default: true,
      description: '关闭后 Agent 将暂停通过此账号收发飞书消息。',
    },
  ],
};

const schema = ref<CommProviderSchema | null>(null);
const items = ref<FeishuCommBinding[]>([]);
const loadError = ref('');
const schemaLoading = ref(false);
const listLoading = ref(false);

const showForm = ref(false);
const formMode = ref<'create' | 'edit'>('create');
const editingId = ref<string | null>(null);
const saving = ref(false);
const validating = ref(false);
const deletingId = ref<string | null>(null);
const saveErrors = ref<string[]>([]);

const form = reactive<FeishuBindingFormState>({
  account_id: '',
  app_id: '',
  app_secret: '',
  account_name: '',
  enabled: true,
});

const effectiveHostPlatform = computed(() => props.hostPlatform ?? 'openclaw');
const isOpenClaw = computed(() => effectiveHostPlatform.value === 'openclaw');
const activeSchema = computed(() => schema.value ?? FALLBACK_SCHEMA);
const providerDisplayLabel = computed(() =>
  activeSchema.value.provider === 'feishu' ? '飞书' : activeSchema.value.label
);
const schemaFields = computed(() => activeSchema.value.fields);
const basicFields = computed(() => schemaFields.value.filter(field => !field.advanced));
const advancedFields = computed(() => schemaFields.value.filter(field => !!field.advanced));
const loading = computed(() => schemaLoading.value || listLoading.value);
const canCreateMore = computed(() =>
  activeSchema.value.supports_multiple_bindings || items.value.length === 0
);
const showAdvanced = ref(false);

function getEnabledDefault() {
  const defaultValue = activeSchema.value.fields.find(field => field.key === 'enabled')?.default;
  return typeof defaultValue === 'boolean' ? defaultValue : true;
}

function resetForm() {
  form.account_id = '';
  form.app_id = '';
  form.app_secret = '';
  form.account_name = '';
  form.enabled = getEnabledDefault();
  saveErrors.value = [];
  showAdvanced.value = false;
}

function closeForm() {
  showForm.value = false;
  editingId.value = null;
  saveErrors.value = [];
}

async function openCreate() {
  resetForm();
  formMode.value = 'create';
  showForm.value = true;

  // 调用 suggest 接口预填 account_id（高级字段）
  try {
    const { data } = await managedAgentFeishuCommBindingApi.suggest(props.agentId);
    if (data.account_id) {
      form.account_id = data.account_id;
    }
  } catch {
    // suggest 失败不阻塞表单，后端创建时会兜底自动生成
  }
}

function openEdit(item: FeishuCommBinding) {
  resetForm();
  formMode.value = 'edit';
  editingId.value = item.id;
  form.account_id = item.account_id;
  form.app_id = item.app_id_masked;
  form.app_secret = '';
  form.account_name = item.account_name ?? '';
  form.enabled = item.enabled;
  showAdvanced.value = advancedFields.value.some(field => getTextFieldValue(field.key).trim());
  showForm.value = true;
}

function getTextFieldValue(key: string) {
  switch (key) {
    case 'account_id':
      return form.account_id;
    case 'app_id':
      return form.app_id;
    case 'app_secret':
      return form.app_secret;
    case 'account_name':
      return form.account_name;
    default:
      return '';
  }
}

function setTextFieldValue(key: string, value: string | number) {
  const nextValue = String(value);
  switch (key) {
    case 'account_id':
      form.account_id = nextValue;
      break;
    case 'app_id':
      form.app_id = nextValue;
      break;
    case 'app_secret':
      form.app_secret = nextValue;
      break;
    case 'account_name':
      form.account_name = nextValue;
      break;
  }
}

function getBooleanFieldValue(key: string) {
  return key === 'enabled' ? form.enabled : false;
}

function setBooleanFieldValue(key: string, value: boolean) {
  if (key === 'enabled') form.enabled = value;
}

function isFieldRequired(field: CommProviderSchemaField) {
  if (formMode.value === 'edit' && field.key === 'app_secret') return false;
  return field.required;
}

function isFieldDisabled(field: CommProviderSchemaField) {
  if (props.disabled) return true;
  return formMode.value === 'edit' && field.key === 'account_id';
}

function fieldBehaviorHint(field: CommProviderSchemaField) {
  if (formMode.value === 'edit' && field.key === 'account_id') {
    return '创建后不可修改。';
  }
  if (formMode.value === 'edit' && field.key === 'app_secret') {
    return '留空表示不修改当前密钥。';
  }
  return null;
}



function formatDate(value: string | null) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return value;
  }
}

function getErrorMessage(error: unknown, fallback: string) {
  return (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? fallback;
}

async function loadSchema() {
  schemaLoading.value = true;
  try {
    const res = await managedAgentMetaApi.getCommProviderSchema('openclaw', 'feishu');
    schema.value = res.data;
  } catch {
    schema.value = FALLBACK_SCHEMA;
  } finally {
    schemaLoading.value = false;
  }
}

async function loadItems() {
  listLoading.value = true;
  try {
    const res = await managedAgentFeishuCommBindingApi.list(props.agentId);
    items.value = res.data;
    loadError.value = '';
  } catch (error: unknown) {
    items.value = [];
    loadError.value = getErrorMessage(error, '加载飞书绑定失败');
  } finally {
    listLoading.value = false;
  }
}

async function loadData() {
  loadError.value = '';
  if (!isOpenClaw.value) return;
  await Promise.all([loadSchema(), loadItems()]);
}

function validateForm() {
  const errors: string[] = [];
  for (const field of schemaFields.value) {
    if (!isFieldRequired(field) || field.type === 'switch') continue;
    const value = getTextFieldValue(field.key).trim();
    if (!value) errors.push(`${field.label}不能为空`);
  }
  return errors;
}

function buildCreatePayload(): FeishuCommBindingCreateInput {
  return {
    account_id: form.account_id.trim(),
    app_id: form.app_id.trim(),
    app_secret: form.app_secret.trim(),
    account_name: form.account_name.trim() || null,
    enabled: form.enabled,
  };
}

function buildUpdatePayload(): FeishuCommBindingUpdateInput {
  return {
    app_id: form.app_id.trim(),
    app_secret: form.app_secret.trim() || undefined,
    account_name: form.account_name.trim() || null,
    enabled: form.enabled,
  };
}

async function handleSave() {
  const localErrors = validateForm();
  if (localErrors.length > 0) {
    saveErrors.value = localErrors;
    return;
  }

  saveErrors.value = [];
  saving.value = true;
  try {
    if (formMode.value === 'create') {
      const payload = buildCreatePayload();
      validating.value = true;
      const validation = await managedAgentMetaApi.validateCommProviderBinding('openclaw', 'feishu', payload);
      validating.value = false;
      if (!validation.data.valid) {
        saveErrors.value = validation.data.errors.length > 0 ? validation.data.errors : ['预校验未通过'];
        return;
      }
      await managedAgentFeishuCommBindingApi.create(props.agentId, payload);
      toast.success('飞书绑定已创建');
    } else if (editingId.value) {
      await managedAgentFeishuCommBindingApi.update(props.agentId, editingId.value, buildUpdatePayload());
      toast.success('飞书绑定已更新');
    }

    closeForm();
    await loadItems();
    emit('saved');
  } catch (error: unknown) {
    saveErrors.value = [getErrorMessage(error, '保存失败')];
  } finally {
    validating.value = false;
    saving.value = false;
  }
}

async function toggleEnabled(item: FeishuCommBinding) {
  try {
    await managedAgentFeishuCommBindingApi.update(props.agentId, item.id, { enabled: !item.enabled });
    item.enabled = !item.enabled;
    toast.success(item.enabled ? '已启用' : '已禁用');
  } catch {
    toast.error('操作失败');
  }
}

async function handleDelete(bindingId: string) {
  deletingId.value = bindingId;
  try {
    await managedAgentFeishuCommBindingApi.remove(props.agentId, bindingId);
    toast.success('已删除');
    await loadItems();
    emit('saved');
  } catch {
    toast.error('删除失败');
  } finally {
    deletingId.value = null;
  }
}

onMounted(() => {
  void loadData();
});

watch([() => props.agentId, () => props.hostPlatform], () => {
  closeForm();
  void loadData();
});
</script>

<template>
  <div v-if="!isOpenClaw" class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
    <MessageSquare class="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
    <p class="text-sm font-medium text-foreground/80">当前通讯渠道页仅适配 OpenClaw + Feishu</p>
    <p class="mt-1 text-sm text-muted-foreground">
      当前 Agent 宿主平台为 {{ effectiveHostPlatform }}，暂未接入专用通讯绑定交互。
    </p>
  </div>

  <div v-else-if="loading" class="flex items-center justify-center py-16">
    <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
  </div>

  <div v-else-if="loadError" class="flex flex-col items-center py-16 text-muted-foreground">
    <AlertCircle class="mb-2 h-6 w-6 text-rose-400" />
    <p class="text-sm">{{ loadError }}</p>
    <Button variant="link" size="sm" class="mt-2" @click="loadData">重试</Button>
  </div>

  <div v-else class="space-y-4 animate-slide-up">
    <div class="rounded-xl border bg-muted/10 p-4">
      <div class="flex flex-wrap items-center gap-2">
        <Badge variant="outline">OpenClaw</Badge>
        <Badge variant="outline" class="border-blue-500/20 bg-blue-500/10 text-blue-400">
          {{ providerDisplayLabel }}
        </Badge>
        <Badge variant="outline" class="tabular-nums">{{ items.length }}</Badge>
      </div>
      <p class="mt-2 text-sm leading-relaxed text-muted-foreground">
        {{ activeSchema.description }}
      </p>
    </div>

    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <span class="text-xs font-medium uppercase tracking-wider text-muted-foreground/60">飞书绑定</span>
        <Badge variant="outline" class="text-[10px] tabular-nums">{{ items.length }}</Badge>
      </div>
      <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="disabled || !canCreateMore"
        @click="openCreate">
        <Plus class="h-3 w-3" />
        新增
      </Button>
    </div>

    <div v-if="items.length === 0 && !showForm"
      class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
      <MessageSquare class="mx-auto mb-3 h-8 w-8 text-muted-foreground/30" />
      <p class="text-sm text-muted-foreground">暂无飞书绑定</p>
      <p class="mt-1 text-xs text-muted-foreground/60">
        创建后将通过结构化接口写入 OpenClaw + 飞书通讯配置。
      </p>
    </div>

    <div v-for="(item, idx) in items" :key="item.id"
      class="rounded-xl border bg-card p-4 animate-slide-up transition-all"
      :style="{ animationDelay: `${idx * 30}ms` }">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0 flex-1">
          <div class="mb-1 flex flex-wrap items-center gap-2">
            <Badge variant="outline" class="border-blue-500/20 bg-blue-500/10 text-[10px] text-blue-400">
              飞书
            </Badge>
            <span class="text-sm font-medium font-mono">{{ item.account_id }}</span>
            <span v-if="item.account_name" class="text-xs text-muted-foreground">{{ item.account_name }}</span>
            <Badge variant="outline" class="text-[10px]"
              :class="item.enabled ? 'border-emerald-500/20 text-emerald-400' : 'border-zinc-500/20 text-zinc-400'">
              {{ item.enabled ? '启用' : '禁用' }}
            </Badge>
          </div>
          <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground/60">
            <span class="font-mono">App ID {{ item.app_id_masked }}</span>
            <span v-if="item.app_secret_masked" class="flex items-center gap-1">
              <ShieldAlert class="h-3 w-3" />
              App Secret {{ item.app_secret_masked }}
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

    <!-- ═══════ 新增 / 编辑弹窗 ═══════ -->
    <Teleport to="body">
      <div v-if="showForm"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeForm" />
        <div
          class="relative z-10 w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
          <!-- 弹窗头部 -->
          <div class="flex items-start justify-between gap-3">
            <div>
              <h3 class="text-base font-semibold">
                {{ formMode === 'create' ? '新增飞书绑定' : '编辑飞书绑定' }}
              </h3>
              <p class="mt-1 text-xs text-muted-foreground/70">
                {{ activeSchema.description }}
              </p>
            </div>
            <Badge variant="outline" class="shrink-0 border-blue-500/20 bg-blue-500/10 text-blue-400">OpenClaw / 飞书
            </Badge>
          </div>

          <Separator class="my-4" />

          <TooltipProvider :delay-duration="200">
            <div class="space-y-5">
              <!-- ─── 飞书应用凭证分组 ─── -->
              <div class="rounded-lg border border-border/50 bg-muted/5 p-4 space-y-4">
                <div>
                  <p class="text-xs font-medium text-foreground/80">飞书应用凭证</p>
                  <p class="mt-0.5 text-[11px] text-muted-foreground/50">
                    可在飞书开放平台「凭证与基础信息」页面获取
                  </p>
                </div>

                <template v-for="field in basicFields.filter(f => f.key === 'app_id' || f.key === 'app_secret')"
                  :key="field.key">
                  <div class="space-y-1.5">
                    <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
                      {{ field.label }}
                      <span v-if="isFieldRequired(field)" class="text-rose-500">*</span>
                      <span v-if="field.sensitive"
                        class="inline-flex items-center gap-0.5 rounded border border-amber-500/20 bg-amber-500/10 px-1 py-0.5 text-[9px] text-amber-500">
                        <ShieldAlert class="h-2.5 w-2.5" />
                        加密存储
                      </span>
                      <Tooltip v-if="field.description">
                        <TooltipTrigger as-child>
                          <Info
                            class="h-3 w-3 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" class="max-w-xs text-xs leading-relaxed">
                          {{ field.description }}
                        </TooltipContent>
                      </Tooltip>
                    </label>
                    <Input :model-value="getTextFieldValue(field.key)"
                      :type="field.type === 'password' ? 'password' : 'text'"
                      :placeholder="field.placeholder ?? undefined" :disabled="isFieldDisabled(field)"
                      class="font-mono text-sm" @update:model-value="(value) => setTextFieldValue(field.key, value)" />
                    <p v-if="fieldBehaviorHint(field)" class="text-[11px] text-muted-foreground/40">
                      {{ fieldBehaviorHint(field) }}
                    </p>
                  </div>
                </template>
              </div>

              <!-- ─── 其他基础字段（排除凭证和 switch） ─── -->
              <template
                v-for="field in basicFields.filter(f => f.key !== 'app_id' && f.key !== 'app_secret' && f.type !== 'switch')"
                :key="field.key">
                <div class="space-y-1.5">
                  <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
                    {{ field.label }}
                    <span v-if="isFieldRequired(field)" class="text-rose-500">*</span>
                    <Tooltip v-if="field.description">
                      <TooltipTrigger as-child>
                        <Info
                          class="h-3 w-3 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent side="top" class="max-w-xs text-xs leading-relaxed">
                        {{ field.description }}
                      </TooltipContent>
                    </Tooltip>
                  </label>
                  <Input :model-value="getTextFieldValue(field.key)"
                    :type="field.type === 'password' ? 'password' : 'text'"
                    :placeholder="field.placeholder ?? undefined" :disabled="isFieldDisabled(field)"
                    class="font-mono text-sm" @update:model-value="(value) => setTextFieldValue(field.key, value)" />
                  <p v-if="fieldBehaviorHint(field)" class="text-[11px] text-muted-foreground/40">
                    {{ fieldBehaviorHint(field) }}
                  </p>
                </div>
              </template>

              <!-- ─── Switch 字段 ─── -->
              <template v-for="field in basicFields.filter(f => f.type === 'switch')" :key="field.key">
                <div class="flex items-center justify-between rounded-lg border bg-muted/10 px-3 py-2.5">
                  <div class="flex items-center gap-1.5">
                    <p class="text-sm font-medium">{{ field.label }}</p>
                    <Tooltip v-if="field.description">
                      <TooltipTrigger as-child>
                        <Info
                          class="h-3 w-3 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors cursor-help" />
                      </TooltipTrigger>
                      <TooltipContent side="top" class="max-w-xs text-xs leading-relaxed">
                        {{ field.description }}
                      </TooltipContent>
                    </Tooltip>
                  </div>
                  <Switch :model-value="getBooleanFieldValue(field.key)" :disabled="isFieldDisabled(field)"
                    @update:model-value="(value) => setBooleanFieldValue(field.key, value)" />
                </div>
              </template>

              <!-- ─── 高级选项 ─── -->
              <div v-if="advancedFields.length > 0"
                class="space-y-3 rounded-lg border border-dashed border-border/70 bg-muted/5 p-4">
                <button type="button" class="flex w-full items-center justify-between text-left"
                  @click="showAdvanced = !showAdvanced">
                  <div>
                    <p class="text-xs font-medium uppercase tracking-wider text-muted-foreground/70">高级选项</p>
                    <p class="mt-1 text-[11px] text-muted-foreground/50">
                      用于宿主平台内部标识等进阶配置；通常保持默认即可。
                    </p>
                  </div>
                  <span class="inline-flex h-7 items-center rounded-md px-2 text-xs text-muted-foreground/70">
                    {{ showAdvanced ? '收起' : '展开' }}
                  </span>
                </button>

                <div v-if="showAdvanced" class="space-y-4">
                  <Separator />

                  <div v-for="field in advancedFields" :key="field.key" class="space-y-1.5">
                    <label class="flex items-center gap-1.5 text-xs text-muted-foreground">
                      {{ field.label }}
                      <span v-if="isFieldRequired(field)" class="text-rose-500">*</span>
                      <Badge variant="outline" class="text-[9px] text-muted-foreground/60">高级</Badge>
                      <Tooltip v-if="field.description">
                        <TooltipTrigger as-child>
                          <Info
                            class="h-3 w-3 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors cursor-help" />
                        </TooltipTrigger>
                        <TooltipContent side="top" class="max-w-xs text-xs leading-relaxed">
                          {{ field.description }}
                        </TooltipContent>
                      </Tooltip>
                    </label>

                    <Input v-if="field.type === 'text' || field.type === 'password'"
                      :model-value="getTextFieldValue(field.key)"
                      :type="field.type === 'password' ? 'password' : 'text'"
                      :placeholder="field.placeholder ?? undefined" :disabled="isFieldDisabled(field)"
                      class="font-mono text-sm" @update:model-value="(value) => setTextFieldValue(field.key, value)" />

                    <div v-else-if="field.type === 'switch'"
                      class="flex items-center justify-between rounded-lg border bg-muted/10 px-3 py-2.5">
                      <div class="flex items-center gap-1.5">
                        <p class="text-sm font-medium">{{ field.label }}</p>
                        <Tooltip v-if="field.description">
                          <TooltipTrigger as-child>
                            <Info
                              class="h-3 w-3 text-muted-foreground/30 hover:text-muted-foreground/60 transition-colors cursor-help" />
                          </TooltipTrigger>
                          <TooltipContent side="top" class="max-w-xs text-xs leading-relaxed">
                            {{ field.description }}
                          </TooltipContent>
                        </Tooltip>
                      </div>
                      <Switch :model-value="getBooleanFieldValue(field.key)" :disabled="isFieldDisabled(field)"
                        @update:model-value="(value) => setBooleanFieldValue(field.key, value)" />
                    </div>

                    <p v-if="fieldBehaviorHint(field)" class="text-[11px] text-muted-foreground/40">
                      {{ fieldBehaviorHint(field) }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </TooltipProvider>

          <!-- 错误提示 -->
          <div v-if="saveErrors.length > 0" class="mt-4 rounded-lg border border-rose-500/20 bg-rose-500/10 p-3">
            <div class="flex items-center gap-2 text-sm font-medium text-rose-500">
              <AlertCircle class="h-4 w-4" />
              保存前需要处理以下问题
            </div>
            <ul class="mt-2 space-y-1 text-xs text-rose-500/90">
              <li v-for="error in saveErrors" :key="error" class="flex items-start gap-1.5">
                <ChevronRight class="mt-0.5 h-3 w-3 shrink-0" />
                <span>{{ error }}</span>
              </li>
            </ul>
          </div>

          <!-- 操作按钮 -->
          <div class="mt-5 flex gap-3">
            <Button variant="outline" class="flex-1" :disabled="saving || validating" @click="closeForm">
              取消
            </Button>
            <Button class="flex-1" :disabled="saving || validating" @click="handleSave">
              <Loader2 v-if="saving || validating" class="mr-1 h-4 w-4 animate-spin" />
              {{ formMode === 'create' ? '创建绑定' : '保存修改' }}
            </Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
/* reserved for future field animations */
</style>
