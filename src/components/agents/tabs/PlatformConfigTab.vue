<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentHostConfigApi,
  type ManagedAgentHostConfig,
  type ManagedAgentHostConfigInput,
  type HostConfigFieldMeta,
  type HostConfigUIHints,
} from '@/api/client';
import { usePlatformMeta } from '@/composables/agents/usePlatformMeta';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import DynamicField from '@/components/agents/fields/DynamicField.vue';
import { Loader2, AlertCircle, Pencil, X, Save, Settings, Info, ChevronRight } from 'lucide-vue-next';

// “高级”组默认折叠
const expandedGroups = ref(new Set<string>());
function toggleGroup(group: string) {
  if (expandedGroups.value.has(group)) expandedGroups.value.delete(group);
  else expandedGroups.value.add(group);
}
function isGroupExpanded(group: string) {
  return group === '基本' || expandedGroups.value.has(group);
}

const props = defineProps<{
  agentId: string;
  /** 当前 agent 的宿主平台 key */
  hostPlatform?: string;
  disabled?: boolean;
}>();
const emit = defineEmits<{ saved: [] }>();

// ─── 平台 Meta ───
const { platforms, loadPlatforms } = usePlatformMeta();

const uiHints = computed<HostConfigUIHints | null>(() => {
  const key = props.hostPlatform ?? 'openclaw';
  const meta = platforms.value.find(p => p.key === key);
  return meta?.ui_hints?.host_config ?? null;
});

const fields = computed<HostConfigFieldMeta[]>(() => uiHints.value?.fields ?? fallbackFields);

// 按 group 分组
const groupedFields = computed(() => {
  const groups = new Map<string, HostConfigFieldMeta[]>();
  for (const f of fields.value) {
    const g = f.group ?? '基本';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g)!.push(f);
  }
  return groups;
});

// ─── Fallback 硬编码字段（当 meta 不可用时） ───
const fallbackFields: HostConfigFieldMeta[] = [
  { key: 'host_agent_identifier', label: 'Agent ID', type: 'text', placeholder: 'my-agent', description: 'OpenClaw 中的唯一标识。仅限英文小写字母、数字、下划线和连字符（a-z 0-9 _ -），首字符为字母或数字，最长 64 位。', group: '基本' },
  { key: 'workdir_path', label: '工作目录', type: 'text', placeholder: '~/.openclaw/workspace-my-agent', description: '通常为 ~/.openclaw/workspace-{Agent ID}，留空时将根据 Agent ID 自动生成。', group: '基本' },
  { key: 'host_config_payload', label: '配置数据', type: 'textarea', sensitive: true, description: '留空表示不修改现有值。', group: '高级' },
  { key: 'host_metadata_json', label: '扩展元数据', type: 'json', placeholder: '{ }', group: '高级' },
];

// 标准字段 key（直接存到 host_config 表字段）
const STANDARD_KEYS = new Set(['host_agent_identifier', 'workdir_path', 'host_config_payload', 'host_metadata_json']);

// ─── 数据状态 ───
const config = ref<ManagedAgentHostConfig | null>(null);
const loading = ref(false);
const loadError = ref('');
const notConfigured = ref(false);

// ─── 编辑状态 ───
const editing = ref(false);
const saving = ref(false);
const saveError = ref('');
const editForm = ref<Record<string, string>>({});

// ─── 加载配置 ───
async function loadConfig() {
  loading.value = true;
  loadError.value = '';
  notConfigured.value = false;
  try {
    const res = await managedAgentHostConfigApi.get(props.agentId);
    config.value = res.data;
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 404) {
      notConfigured.value = true;
      config.value = null;
    } else {
      loadError.value = '加载平台配置失败';
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadPlatforms();
  void loadConfig();
});
watch(() => props.agentId, () => { editing.value = false; void loadConfig(); });

// ─── 进入编辑 ───
function startEdit() {
  const form: Record<string, string> = {};
  for (const field of fields.value) {
    if (field.sensitive) {
      form[field.key] = ''; // 敏感字段不回填
    } else {
      form[field.key] = getReadonlyValue(field.key) ?? '';
    }
  }
  editForm.value = form;
  saveError.value = '';
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
  saveError.value = '';
}

// ─── 从 config 中读取只读值 ───
function getReadonlyValue(key: string): string | null {
  if (!config.value) return null;
  const c = config.value as Record<string, unknown>;
  // 标准字段直接读
  if (key === 'host_agent_identifier') return (c.host_agent_identifier as string) ?? null;
  if (key === 'workdir_path') return (c.workdir_path as string) ?? null;
  if (key === 'host_config_payload') return (c.host_config_payload_masked as string) ?? null;
  if (key === 'host_metadata_json') return (c.host_metadata_json as string) ?? null;
  return null;
}

// ─── 保存 ───
async function handleSave() {
  saving.value = true;
  saveError.value = '';
  try {
    const payload: ManagedAgentHostConfigInput = {};
    for (const field of fields.value) {
      const val = editForm.value[field.key]?.trim();
      if (!val) continue;
      if (STANDARD_KEYS.has(field.key)) {
        (payload as Record<string, string>)[field.key] = val;
      }
      // 非标准字段：未来可以打包到 host_config_payload JSON
    }
    const res = await managedAgentHostConfigApi.update(props.agentId, payload);
    config.value = res.data;
    notConfigured.value = false;
    editing.value = false;
    toast.success('平台配置已保存');
    emit('saved');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    saveError.value = msg ?? '保存失败，请稍后再试';
  } finally {
    saving.value = false;
  }
}

// ─── 辅助 ───
function formatDate(value: string | null) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
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
    <Button variant="link" size="sm" class="mt-2" @click="loadConfig">重试</Button>
  </div>

  <!-- 未配置 -->
  <div v-else-if="notConfigured && !editing"
    class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
    <Settings class="h-8 w-8 mx-auto mb-3 text-muted-foreground/30" />
    <p class="text-sm text-muted-foreground mb-4">该 Agent 尚未配置平台信息</p>
    <Button variant="outline" size="sm" class="gap-1.5" :disabled="disabled" @click="startEdit">
      <Pencil class="h-3.5 w-3.5" /> 配置平台信息
    </Button>
  </div>

  <!-- 正常 -->
  <div v-else class="space-y-5 animate-slide-up">
    <!-- 平台说明 -->
    <div v-if="uiHints?.description"
      class="rounded-lg border border-border/30 bg-muted/5 px-4 py-3 flex items-start gap-2">
      <Info class="h-4 w-4 text-primary/60 shrink-0 mt-0.5" />
      <p class="text-xs text-muted-foreground leading-relaxed">{{ uiHints.description }}</p>
    </div>

    <!-- 顶部操作栏 -->
    <div class="flex items-center justify-between">
      <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
        平台配置
      </div>
      <div v-if="!editing">
        <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="disabled" @click="startEdit">
          <Pencil class="h-3 w-3" /> 编辑
        </Button>
      </div>
      <div v-else class="flex gap-1.5">
        <Button variant="ghost" size="sm" class="h-7 gap-1 text-xs" :disabled="saving" @click="cancelEdit">
          <X class="h-3 w-3" /> 取消
        </Button>
        <Button size="sm" class="h-7 gap-1 text-xs" :disabled="saving" @click="handleSave">
          <Loader2 v-if="saving" class="h-3 w-3 animate-spin" />
          <Save v-else class="h-3 w-3" />
          保存
        </Button>
      </div>
    </div>

    <!-- ─── 只读模式 ─── -->
    <template v-if="!editing && config">
      <div class="rounded-xl border bg-card p-5 space-y-4">
        <template v-for="[group, gFields] in groupedFields" :key="group">
          <!-- 组标题（非“基本”组可折叠） -->
          <button v-if="groupedFields.size > 1"
            class="flex items-center gap-1 text-[11px] text-muted-foreground/40 font-medium uppercase tracking-wider hover:text-muted-foreground/60 transition-colors"
            @click="toggleGroup(group)">
            <ChevronRight class="h-3 w-3 transition-transform" :class="isGroupExpanded(group) ? 'rotate-90' : ''" />
            {{ group }}
          </button>
          <template v-if="isGroupExpanded(group)">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
              <div v-for="field in gFields" :key="field.key">
                <div class="text-[11px] text-muted-foreground/60 mb-0.5">{{ field.label }}</div>
                <div v-if="field.sensitive && getReadonlyValue(field.key)"
                  class="rounded-lg bg-muted/30 border border-border/40 p-2 font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap break-all">
                  {{ getReadonlyValue(field.key) }}
                </div>
                <div v-else-if="getReadonlyValue(field.key)"
                  class="text-sm font-mono">{{ getReadonlyValue(field.key) }}</div>
                <p v-else class="text-xs text-muted-foreground/40 italic">未设置</p>
              </div>
            </div>
          </template>
          <Separator v-if="groupedFields.size > 1" />
        </template>

        <!-- 更新时间 -->
        <div>
          <div class="text-[11px] text-muted-foreground/60 mb-0.5">最后更新</div>
          <div class="text-sm">{{ formatDate(config.updated_at) }}</div>
        </div>
      </div>
    </template>

    <!-- ─── 编辑模式 ─── -->
    <template v-if="editing">
      <div class="rounded-xl border bg-card p-5 space-y-4">
        <template v-for="[group, gFields] in groupedFields" :key="group">
          <button v-if="groupedFields.size > 1"
            class="flex items-center gap-1 text-[11px] text-muted-foreground/40 font-medium uppercase tracking-wider pt-1 hover:text-muted-foreground/60 transition-colors"
            @click="toggleGroup(group)">
            <ChevronRight class="h-3 w-3 transition-transform" :class="isGroupExpanded(group) ? 'rotate-90' : ''" />
            {{ group }}
          </button>
          <template v-if="isGroupExpanded(group)">
            <div class="space-y-4">
              <DynamicField v-for="field in gFields" :key="field.key"
                :field="field"
                :model-value="editForm[field.key] ?? ''"
                @update:model-value="(v: string) => editForm[field.key] = v"
                :disabled="disabled" />
            </div>
          </template>
          <Separator v-if="groupedFields.size > 1" />
        </template>

        <p v-if="saveError" class="text-xs text-rose-500">{{ saveError }}</p>
      </div>
    </template>
  </div>
</template>
