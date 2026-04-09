<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentHostConfigApi,
  type ManagedAgentHostConfig,
  type ManagedAgentHostConfigInput,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Loader2, AlertCircle, Pencil, X, Save, Settings, ShieldAlert } from 'lucide-vue-next';

const props = defineProps<{ agentId: string; disabled?: boolean }>();
const emit = defineEmits<{ saved: [] }>();

// ─── 数据状态 ───

const config = ref<ManagedAgentHostConfig | null>(null);
const loading = ref(false);
const loadError = ref('');
const notConfigured = ref(false);

// ─── 编辑状态 ───

const editing = ref(false);
const saving = ref(false);
const saveError = ref('');
const editForm = ref<ManagedAgentHostConfigInput>({
  host_agent_identifier: '',
  workdir_path: '',
  host_config_payload: '',
  host_metadata_json: '',
});

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

onMounted(() => { void loadConfig(); });
watch(() => props.agentId, () => { editing.value = false; void loadConfig(); });

// ─── 进入编辑模式 ───

function startEdit() {
  editForm.value = {
    host_agent_identifier: config.value?.host_agent_identifier ?? '',
    workdir_path: config.value?.workdir_path ?? '',
    host_config_payload: '', // 不回填敏感值，留空表示不修改
    host_metadata_json: config.value?.host_metadata_json ?? '',
  };
  saveError.value = '';
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
  saveError.value = '';
}

// ─── 保存 ───

async function handleSave() {
  saving.value = true;
  saveError.value = '';
  try {
    const payload: ManagedAgentHostConfigInput = {};
    const f = editForm.value;
    // 仅发送有值的字段
    if (f.host_agent_identifier?.trim()) payload.host_agent_identifier = f.host_agent_identifier.trim();
    if (f.workdir_path?.trim()) payload.workdir_path = f.workdir_path.trim();
    if (f.host_config_payload?.trim()) payload.host_config_payload = f.host_config_payload.trim();
    if (f.host_metadata_json?.trim()) payload.host_metadata_json = f.host_metadata_json.trim();

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

  <!-- 未配置 + 编辑模式 -->
  <div v-else-if="notConfigured && !editing"
    class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
    <Settings class="h-8 w-8 mx-auto mb-3 text-muted-foreground/30" />
    <p class="text-sm text-muted-foreground mb-4">该 Agent 尚未配置平台信息</p>
    <Button variant="outline" size="sm" class="gap-1.5" :disabled="disabled" @click="startEdit">
      <Pencil class="h-3.5 w-3.5" /> 配置平台信息
    </Button>
  </div>

  <!-- 正常展示 / 编辑 -->
  <div v-else class="space-y-5 animate-slide-up">
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
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-8 gap-y-4">
          <!-- 平台 -->
          <div>
            <div class="text-[11px] text-muted-foreground/60 mb-0.5">Agent 平台</div>
            <div class="text-sm font-medium">{{ config.host_platform }}</div>
          </div>
          <!-- 标识 -->
          <div>
            <div class="text-[11px] text-muted-foreground/60 mb-0.5">Agent 平台标识</div>
            <div class="text-sm font-mono">{{ config.host_agent_identifier ?? '—' }}</div>
          </div>
          <!-- 工作目录 -->
          <div>
            <div class="text-[11px] text-muted-foreground/60 mb-0.5">工作目录</div>
            <div class="text-sm font-mono">{{ config.workdir_path ?? '—' }}</div>
          </div>
          <!-- 更新时间 -->
          <div>
            <div class="text-[11px] text-muted-foreground/60 mb-0.5">最后更新</div>
            <div class="text-sm">{{ formatDate(config.updated_at) }}</div>
          </div>
        </div>

        <Separator />

        <!-- 配置数据（脱敏） -->
        <div>
          <div class="flex items-center gap-1.5 mb-1.5">
            <ShieldAlert class="h-3.5 w-3.5 text-muted-foreground/50" />
            <span class="text-[11px] text-muted-foreground/60">配置数据（脱敏）</span>
          </div>
          <div v-if="config.host_config_payload_masked"
            class="rounded-lg bg-muted/30 border border-border/40 p-3 font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap break-all">
            {{ config.host_config_payload_masked }}
          </div>
          <p v-else class="text-xs text-muted-foreground/40 italic">未设置</p>
        </div>

        <!-- 元数据 -->
        <div>
          <div class="text-[11px] text-muted-foreground/60 mb-1.5">扩展元数据 (JSON)</div>
          <div v-if="config.host_metadata_json"
            class="rounded-lg bg-muted/30 border border-border/40 p-3 font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap break-all">
            {{ config.host_metadata_json }}
          </div>
          <p v-else class="text-xs text-muted-foreground/40 italic">未设置</p>
        </div>
      </div>
    </template>

    <!-- ─── 编辑模式 ─── -->
    <template v-if="editing">
      <div class="rounded-xl border bg-card p-5 space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4">
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">Agent 平台标识</label>
            <Input v-model="editForm.host_agent_identifier" placeholder="平台中的 Agent 唯一标识（可选）"
              class="font-mono text-sm" />
          </div>
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">工作目录</label>
            <Input v-model="editForm.workdir_path" placeholder="如 ~/.openclaw/workspace-xxx（可选）"
              class="font-mono text-sm" />
          </div>
        </div>

        <Separator />

        <div>
          <label class="text-xs text-muted-foreground mb-1 block">
            配置数据
            <Badge variant="outline" class="text-[9px] ml-1.5 text-amber-600 border-amber-300">敏感</Badge>
          </label>
          <p class="text-[11px] text-muted-foreground/50 mb-1.5">
            留空表示不修改现有值。输入新内容将替换旧值，保存后仅展示脱敏结果。
          </p>
          <textarea v-model="editForm.host_config_payload" rows="4"
            class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
            placeholder="配置内容（明文输入，保存后脱敏展示）" />
        </div>

        <div>
          <label class="text-xs text-muted-foreground mb-1 block">扩展元数据 (JSON)</label>
          <textarea v-model="editForm.host_metadata_json" rows="4"
            class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
            placeholder='{"key": "value"}' />
        </div>

        <!-- 保存错误 -->
        <p v-if="saveError" class="text-xs text-rose-500">{{ saveError }}</p>
      </div>
    </template>
  </div>
</template>
