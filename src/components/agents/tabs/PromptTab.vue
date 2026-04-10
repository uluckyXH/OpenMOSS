<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentPromptAssetApi,
  type ManagedAgentPromptAsset,
  type ManagedAgentPromptAssetInput,
  type ManagedAgentPromptRenderPreview,
  type ManagedAgentHostRenderStrategy,
} from '@/api/client';
import { usePlatformMeta } from '@/composables/agents/usePlatformMeta';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Loader2, AlertCircle, Pencil, X, Save, FileText, RotateCcw, Eye, Copy, ChevronDown, Check, Info,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; hostPlatform?: string; disabled?: boolean }>();
const emit = defineEmits<{ saved: [] }>();

// ─── 数据状态 ───

const asset = ref<ManagedAgentPromptAsset | null>(null);
const loading = ref(false);
const loadError = ref('');
const notConfigured = ref(false);

// ─── 编辑状态 ───

const editing = ref(false);
const saving = ref(false);
const saveError = ref('');
const editForm = ref<ManagedAgentPromptAssetInput>({
  system_prompt_content: '',
  persona_prompt_content: '',
  identity_content: '',
  host_render_strategy: 'host_default',
  notes: '',
});

// ─── 重置状态 ───

const resetting = ref(false);
const showResetConfirm = ref(false);

// ─── 预览状态 ───

const previewing = ref(false);
const preview = ref<ManagedAgentPromptRenderPreview | null>(null);
const showPreview = ref(false);

// ─── 平台 Meta 驱动 ───

const { platforms, loadPlatforms } = usePlatformMeta();

const promptUIHints = computed(() => {
  const key = props.hostPlatform ?? 'openclaw';
  return platforms.value.find(p => p.key === key)?.ui_hints?.prompt ?? null;
});

// 渲染策略（meta 驱动，fallback 硬编码）
const strategyOptions = computed(() => {
  if (promptUIHints.value?.render_strategies?.length) {
    return promptUIHints.value.render_strategies.map(s => ({
      value: s.value as ManagedAgentHostRenderStrategy,
      label: s.label,
      desc: s.description,
    }));
  }
  return [
    { value: 'host_default' as ManagedAgentHostRenderStrategy, label: '平台默认', desc: '由平台自行决定渲染方式' },
    { value: 'openclaw_workspace_files' as ManagedAgentHostRenderStrategy, label: 'Workspace 文件', desc: '渲染为 OpenClaw 工作目录文件' },
    { value: 'openclaw_inline_schedule' as ManagedAgentHostRenderStrategy, label: '内联 Schedule', desc: '内联到定时任务的唤醒消息中' },
  ];
});

// ─── 加载 ───

async function loadAsset() {
  loading.value = true;
  loadError.value = '';
  notConfigured.value = false;
  try {
    const res = await managedAgentPromptAssetApi.get(props.agentId);
    asset.value = res.data;
  } catch (err: unknown) {
    const status = (err as { response?: { status?: number } })?.response?.status;
    if (status === 404) {
      notConfigured.value = true;
      asset.value = null;
    } else {
      loadError.value = '加载 Prompt 资产失败';
    }
  } finally {
    loading.value = false;
  }
}

onMounted(() => { void loadPlatforms(); void loadAsset(); });
watch(() => props.agentId, () => { editing.value = false; showPreview.value = false; void loadAsset(); });

// ─── 编辑 ───

function startEdit() {
  editForm.value = {
    system_prompt_content: asset.value?.system_prompt_content ?? '',
    persona_prompt_content: asset.value?.persona_prompt_content ?? '',
    identity_content: asset.value?.identity_content ?? '',
    host_render_strategy: asset.value?.host_render_strategy ?? 'host_default',
    notes: asset.value?.notes ?? '',
  };
  saveError.value = '';
  editing.value = true;
}

function cancelEdit() {
  editing.value = false;
  saveError.value = '';
}

async function handleSave() {
  saving.value = true;
  saveError.value = '';
  try {
    const res = await managedAgentPromptAssetApi.update(props.agentId, editForm.value);
    asset.value = res.data;
    editing.value = false;
    toast.success('Prompt 已保存');
    emit('saved');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    saveError.value = msg ?? '保存失败';
  } finally {
    saving.value = false;
  }
}

// ─── 从模板重置 ───

async function handleReset() {
  resetting.value = true;
  try {
    const res = await managedAgentPromptAssetApi.resetFromTemplate(props.agentId);
    asset.value = res.data;
    notConfigured.value = false;
    showResetConfirm.value = false;
    editing.value = false;
    toast.success('已从模板重置');
    emit('saved');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    toast.error(msg ?? '重置失败');
  } finally {
    resetting.value = false;
  }
}

// ─── 渲染预览 ───

async function handlePreview() {
  previewing.value = true;
  try {
    const res = await managedAgentPromptAssetApi.renderPreview(props.agentId);
    preview.value = res.data;
    showPreview.value = true;
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    toast.error(msg ?? '预览失败');
  } finally {
    previewing.value = false;
  }
}

// ─── 复制 ───

const copiedIdx = ref<number | null>(null);
async function copyContent(text: string, idx: number) {
  await navigator.clipboard.writeText(text);
  copiedIdx.value = idx;
  setTimeout(() => { copiedIdx.value = null; }, 2000);
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

// Prompt 段落（meta 驱动，fallback 硬编码）
const promptSections = computed(() => {
  if (promptUIHints.value?.sections?.length) {
    return promptUIHints.value.sections.map(s => ({
      key: s.key,
      label: s.label,
      placeholder: s.placeholder ?? '',
      required: s.required,
    }));
  }
  return [
    { key: 'system_prompt_content', label: '系统提示词', placeholder: '定义 Agent 的行为规则和约束…', required: true },
    { key: 'persona_prompt_content', label: '人格提示词', placeholder: '定义 Agent 的性格和沟通风格…', required: false },
    { key: 'identity_content', label: '身份内容', placeholder: '定义 Agent 的身份信息和背景…', required: false },
  ];
});
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
    <Button variant="link" size="sm" class="mt-2" @click="loadAsset">重试</Button>
  </div>

  <!-- 未配置 -->
  <div v-else-if="notConfigured && !editing"
    class="rounded-xl border border-dashed border-border bg-muted/10 p-8 text-center">
    <FileText class="h-8 w-8 mx-auto mb-3 text-muted-foreground/30" />
    <p class="text-sm text-muted-foreground mb-4">该 Agent 尚未配置 Prompt 资产</p>
    <div class="flex justify-center gap-2">
      <Button variant="outline" size="sm" class="gap-1.5" :disabled="resetting" @click="handleReset">
        <Loader2 v-if="resetting" class="h-3.5 w-3.5 animate-spin" />
        <RotateCcw v-else class="h-3.5 w-3.5" />
        从模板初始化
      </Button>
    </div>
  </div>

  <!-- 正常展示 / 编辑 -->
  <div v-else class="space-y-5 animate-slide-up">
    <!-- 平台说明 -->
    <div v-if="promptUIHints?.description"
      class="rounded-lg border border-border/30 bg-muted/5 px-4 py-3 flex items-start gap-2">
      <Info class="h-4 w-4 text-primary/60 shrink-0 mt-0.5" />
      <p class="text-xs text-muted-foreground leading-relaxed">{{ promptUIHints.description }}</p>
    </div>

    <!-- 顶部操作栏 -->
    <div class="flex items-center justify-between flex-wrap gap-2">
      <div class="flex items-center gap-3">
        <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">Prompt 管理</div>
        <template v-if="asset">
          <Badge variant="outline" class="text-[10px]">
            {{strategyOptions.find((s: { value: string }) => s.value === asset!.host_render_strategy)?.label ?? asset!.host_render_strategy
            }}
          </Badge>
          <span class="text-[11px] text-muted-foreground/40">{{ formatDate(asset.updated_at) }}</span>
        </template>
      </div>
      <div class="flex gap-1.5">
        <template v-if="!editing">
          <Button variant="ghost" size="sm" class="h-7 gap-1 text-xs" :disabled="previewing" @click="handlePreview">
            <Loader2 v-if="previewing" class="h-3 w-3 animate-spin" />
            <Eye v-else class="h-3 w-3" />
            预览
          </Button>
          <Button variant="ghost" size="sm" class="h-7 gap-1 text-xs" @click="showResetConfirm = true">
            <RotateCcw class="h-3 w-3" /> 重置
          </Button>
          <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="disabled" @click="startEdit">
            <Pencil class="h-3 w-3" /> 编辑
          </Button>
        </template>
        <template v-else>
          <Button variant="ghost" size="sm" class="h-7 gap-1 text-xs" :disabled="saving" @click="cancelEdit">
            <X class="h-3 w-3" /> 取消
          </Button>
          <Button size="sm" class="h-7 gap-1 text-xs" :disabled="saving" @click="handleSave">
            <Loader2 v-if="saving" class="h-3 w-3 animate-spin" />
            <Save v-else class="h-3 w-3" />
            保存
          </Button>
        </template>
      </div>
    </div>

    <!-- ─── 只读模式 ─── -->
    <template v-if="!editing && asset">
      <!-- 元信息 -->
      <div v-if="asset.template_role || asset.authority_source || asset.notes"
        class="rounded-xl border bg-muted/10 p-4 text-xs text-muted-foreground space-y-1">
        <div v-if="asset.template_role"><span class="text-muted-foreground/50">模板角色：</span>{{ asset.template_role
          }}</div>
        <div v-if="asset.authority_source"><span class="text-muted-foreground/50">权威来源：</span>{{
          asset.authority_source }}</div>
        <div v-if="asset.notes"><span class="text-muted-foreground/50">备注：</span>{{ asset.notes }}</div>
      </div>

      <!-- 三段 Prompt -->
      <div class="space-y-4">
        <div v-for="sec in promptSections" :key="sec.key" class="rounded-xl border bg-card p-4">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-medium text-muted-foreground/60">{{ sec.label }}</span>
            <Button v-if="(asset as Record<string, unknown>)[sec.key]" variant="ghost" size="sm"
              class="h-6 w-6 p-0 text-muted-foreground/40 hover:text-muted-foreground"
              @click="copyContent(String((asset as Record<string, unknown>)[sec.key] ?? ''), promptSections.indexOf(sec))">
              <Check v-if="copiedIdx === promptSections.indexOf(sec)" class="h-3 w-3 text-emerald-400" />
              <Copy v-else class="h-3 w-3" />
            </Button>
          </div>
          <div v-if="(asset as Record<string, unknown>)[sec.key]"
            class="text-sm leading-relaxed whitespace-pre-wrap break-words text-foreground/90 max-h-64 overflow-y-auto">
            {{ (asset as Record<string, unknown>)[sec.key] }}
          </div>
          <p v-else class="text-xs text-muted-foreground/40 italic">未设置</p>
        </div>
      </div>
    </template>

    <!-- ─── 编辑模式 ─── -->
    <template v-if="editing">
      <!-- 渲染策略 -->
      <div class="rounded-xl border bg-card p-4">
        <label class="text-xs text-muted-foreground mb-1.5 block">渲染策略</label>
        <DropdownMenu>
          <DropdownMenuTrigger as-child>
            <Button variant="outline" size="sm" class="h-8 w-full max-w-xs justify-between text-xs font-normal">
              {{strategyOptions.find((s: { value: string }) => s.value === editForm.host_render_strategy)?.label ??
                editForm.host_render_strategy}}
              <ChevronDown class="h-3 w-3 opacity-50" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" class="min-w-[240px]">
            <DropdownMenuRadioGroup :model-value="editForm.host_render_strategy"
              @update:model-value="(v) => editForm.host_render_strategy = String(v) as ManagedAgentHostRenderStrategy">
              <DropdownMenuRadioItem v-for="opt in strategyOptions" :key="opt.value" :value="opt.value as string">
                <div>
                  <div class="text-sm">{{ opt.label }}</div>
                  <div class="text-[11px] text-muted-foreground">{{ opt.desc }}</div>
                </div>
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <!-- 三段编辑器 -->
      <div v-for="sec in promptSections" :key="sec.key" class="rounded-xl border bg-card p-4">
        <label class="text-xs font-medium text-muted-foreground/60 mb-1.5 block">{{ sec.label }}</label>
        <textarea v-model="(editForm as Record<string, string>)[sec.key]" rows="8"
          class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-y leading-relaxed"
          :placeholder="sec.placeholder" />
      </div>

      <!-- 备注 -->
      <div class="rounded-xl border bg-card p-4">
        <label class="text-xs text-muted-foreground mb-1.5 block">备注</label>
        <textarea v-model="editForm.notes" rows="2"
          class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
          placeholder="内部备注（可选）" />
      </div>

      <p v-if="saveError" class="text-xs text-rose-500">{{ saveError }}</p>
    </template>
  </div>

  <!-- ─── 重置确认弹窗 ─── -->
  <Teleport to="body">
    <div v-if="showResetConfirm"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showResetConfirm = false" />
      <div
        class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 text-center space-y-3">
        <RotateCcw class="h-8 w-8 mx-auto text-amber-500" />
        <h3 class="text-base font-semibold">从模板重置 Prompt</h3>
        <p class="text-sm text-muted-foreground">此操作将用角色模板覆盖当前所有 Prompt 内容，无法撤销。</p>
        <div class="flex gap-3 pt-2">
          <Button variant="outline" class="flex-1" :disabled="resetting" @click="showResetConfirm = false">取消
          </Button>
          <Button variant="destructive" class="flex-1" :disabled="resetting" @click="handleReset">
            <Loader2 v-if="resetting" class="h-4 w-4 animate-spin mr-1" />
            确认重置
          </Button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ─── 渲染预览弹窗 ─── -->
  <Teleport to="body">
    <div v-if="showPreview && preview"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showPreview = false" />
      <div
        class="relative z-10 w-full max-w-2xl max-h-[80vh] overflow-y-auto rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-base font-semibold">渲染预览</h3>
          <Button variant="ghost" size="icon" class="h-7 w-7" @click="showPreview = false">
            <X class="h-4 w-4" />
          </Button>
        </div>
        <div class="flex items-center gap-3 mb-4 text-xs text-muted-foreground">
          <Badge variant="outline">{{ preview.host_platform }}</Badge>
          <Badge variant="outline">{{
            strategyOptions.find((s: { value: string }) => s.value === preview!.host_render_strategy)?.label ??
            preview.host_render_strategy}}</Badge>
        </div>
        <div class="space-y-4">
          <div v-for="(artifact, idx) in preview.artifacts" :key="idx" class="rounded-lg border bg-muted/20 p-4">
            <div class="flex items-center justify-between mb-2">
              <span class="text-xs font-medium">{{ artifact.name }}</span>
              <Button variant="ghost" size="sm" class="h-6 gap-1 text-[11px] text-muted-foreground/50"
                @click="copyContent(artifact.content, 100 + idx)">
                <Check v-if="copiedIdx === 100 + idx" class="h-3 w-3 text-emerald-400" />
                <Copy v-else class="h-3 w-3" />
                复制
              </Button>
            </div>
            <pre
              class="text-xs font-mono leading-relaxed whitespace-pre-wrap break-words max-h-80 overflow-y-auto text-foreground/80">
            {{ artifact.content }}</pre>
          </div>
          <p v-if="!preview.artifacts.length" class="text-sm text-muted-foreground/40 text-center py-6">
            无渲染产物
          </p>
        </div>
      </div>
    </div>
  </Teleport>
</template>
