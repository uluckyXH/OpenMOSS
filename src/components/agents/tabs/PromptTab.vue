<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import { marked } from 'marked';
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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Loader2, AlertCircle, Pencil, X, Save, FileText, RotateCcw, Eye, Copy, ChevronDown, Check, Info, Code, HelpCircle,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; hostPlatform?: string; disabled?: boolean }>();
const emit = defineEmits<{ saved: [] }>();

// ─── 数据状态 ───

const asset = ref<ManagedAgentPromptAsset | null>(null);
const loading = ref(false);
const loadError = ref('');
const notConfigured = ref(false);

// ─── 分段编辑弹窗状态 ───

const showSectionEditor = ref(false);
const editingSectionKey = ref('');
const editingSectionLabel = ref('');
const editingSectionContent = ref('');
const sectionSaving = ref(false);
const sectionSaveError = ref('');
const sectionPreviewMode = ref<'edit' | 'preview'>('edit');

// ─── 渲染策略编辑弹窗 ───

const showStrategyEditor = ref(false);
const editingStrategy = ref<ManagedAgentHostRenderStrategy>('host_default');
const editingNotes = ref('');
const strategySaving = ref(false);
const strategySaveError = ref('');

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
watch(() => props.agentId, () => { showSectionEditor.value = false; showPreview.value = false; void loadAsset(); });

// ─── 分段编辑 ───

function openSectionEditor(sectionKey: string, sectionLabel: string) {
  editingSectionKey.value = sectionKey;
  editingSectionLabel.value = sectionLabel;
  editingSectionContent.value = (asset.value as unknown as Record<string, string>)?.[sectionKey] ?? '';
  sectionSaveError.value = '';
  sectionPreviewMode.value = 'edit';
  showSectionEditor.value = true;
}

function closeSectionEditor() {
  showSectionEditor.value = false;
  editingSectionKey.value = '';
  editingSectionContent.value = '';
  sectionSaveError.value = '';
}

async function handleSectionSave() {
  sectionSaving.value = true;
  sectionSaveError.value = '';
  try {
    const payload: ManagedAgentPromptAssetInput = {
      [editingSectionKey.value]: editingSectionContent.value,
    };
    const res = await managedAgentPromptAssetApi.update(props.agentId, payload);
    asset.value = res.data;
    closeSectionEditor();
    toast.success(`${editingSectionLabel.value}已保存`);
    emit('saved');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    sectionSaveError.value = msg ?? '保存失败';
  } finally {
    sectionSaving.value = false;
  }
}

// 编辑器预览 Markdown
const renderedSectionPreview = computed(() => {
  if (!editingSectionContent.value) return '';
  return marked(editingSectionContent.value) as string;
});

// ─── 渲染策略编辑 ───

function openStrategyEditor() {
  editingStrategy.value = asset.value?.host_render_strategy ?? 'host_default';
  editingNotes.value = asset.value?.notes ?? '';
  strategySaveError.value = '';
  showStrategyEditor.value = true;
}

async function handleStrategySave() {
  strategySaving.value = true;
  strategySaveError.value = '';
  try {
    const payload: ManagedAgentPromptAssetInput = {
      host_render_strategy: editingStrategy.value,
      notes: editingNotes.value.trim() || undefined,
    };
    const res = await managedAgentPromptAssetApi.update(props.agentId, payload);
    asset.value = res.data;
    showStrategyEditor.value = false;
    toast.success('渲染策略已更新');
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    strategySaveError.value = msg ?? '保存失败';
  } finally {
    strategySaving.value = false;
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

const copiedKey = ref<string | null>(null);
async function copyContent(text: string, key: string) {
  await navigator.clipboard.writeText(text);
  copiedKey.value = key;
  setTimeout(() => { copiedKey.value = null; }, 2000);
}

// ─── Markdown 渲染 ───

function renderMarkdown(content: string): string {
  if (!content) return '';
  return marked(content) as string;
}

// ─── 内容截断控制 ───

const expandedSections = reactive(new Set<string>());

function isContentLong(content: string): boolean {
  if (!content) return false;
  const lines = content.split('\n').length;
  return lines > 5 || content.length > 300;
}

// ─── 辅助 ───

// 当前是否有编辑弹窗打开（用于父组件的 unsaved guard）
const editing = computed(() => showSectionEditor.value || showStrategyEditor.value);
function cancelEdit() {
  closeSectionEditor();
  showStrategyEditor.value = false;
}
defineExpose({ editing, cancelEdit });

function formatDate(value: string | null) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return value; }
}

// 段落描述 fallback（后端没返回时自动补上）
const descFallback: Record<string, { description: string; detail: string }> = {
  system_prompt_content: {
    description: '定义 Agent 的行为规则和工作流程',
    detail: '相当于 Agent 的「操作手册」：包括会话流程、安全边界、记忆策略、协作规则等。在 OpenClaw 中对应 AGENTS.md，是最核心的配置文件，子 Agent 也主要依赖此内容。',
  },
  persona_prompt_content: {
    description: '定义 Agent 的性格和说话风格',
    detail: 'Agent 的「灵魂设定」：语气、态度、个性和与用户的关系边界。决定 Agent 是偏工具化还是有独立个性。在 OpenClaw 中对应 SOUL.md。',
  },
  identity_content: {
    description: '定义 Agent 的名称和外显身份',
    detail: 'Agent 的「名片」：名字、emoji、头像等对外展示信息。比人格设定更轻量，用于标识而非行为。在 OpenClaw 中对应 IDENTITY.md。',
  },
};

// Prompt 段落（meta 驱动 + fallback 补描述）
const promptSections = computed(() => {
  const raw = promptUIHints.value?.sections?.length
    ? promptUIHints.value.sections
    : [
        { key: 'system_prompt_content', label: '系统提示词', placeholder: '定义 Agent 的行为规则和约束…', required: true },
        { key: 'persona_prompt_content', label: '人格提示词', placeholder: '定义 Agent 的性格和沟通风格…', required: false },
        { key: 'identity_content', label: '身份内容', placeholder: '定义 Agent 的名称和外显身份…', required: false },
      ];
  return raw.map(s => {
    const fb = descFallback[s.key];
    return {
      key: s.key,
      label: s.label,
      placeholder: s.placeholder ?? '',
      required: s.required,
      description: s.description || fb?.description || '',
      detail: s.detail || fb?.detail || '',
    };
  });
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
  <div v-else-if="notConfigured"
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

  <!-- 正常展示 -->
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
        <div class="text-xs font-medium text-muted-foreground uppercase tracking-wider">Prompt 管理</div>
        <template v-if="asset">
          <Badge variant="outline" class="text-[10px]">
            {{strategyOptions.find((s: { value: string }) => s.value === asset!.host_render_strategy)?.label ?? asset!.host_render_strategy
            }}
          </Badge>
          <span class="text-[11px] text-muted-foreground/40">{{ formatDate(asset.updated_at) }}</span>
        </template>
      </div>
      <div class="flex gap-1.5">
        <Button variant="ghost" size="sm" class="h-7 gap-1 text-xs" :disabled="previewing" @click="handlePreview">
          <Loader2 v-if="previewing" class="h-3 w-3 animate-spin" />
          <Eye v-else class="h-3 w-3" />
          预览
        </Button>
        <Button variant="ghost" size="sm" class="h-7 gap-1 text-xs" @click="showResetConfirm = true">
          <RotateCcw class="h-3 w-3" /> 重置
        </Button>
      </div>
    </div>

    <!-- 元信息 + 渲染策略 -->
    <div v-if="asset" class="rounded-xl border bg-card/50 p-4">
      <div class="flex items-center justify-between">
        <div class="space-y-1">
          <div class="flex items-center gap-2">
            <span class="text-xs text-muted-foreground font-medium">渲染策略</span>
            <Badge variant="outline" class="text-[10px]">
              {{ strategyOptions.find((s: { value: string }) => s.value === asset!.host_render_strategy)?.label ?? asset!.host_render_strategy }}
            </Badge>
          </div>
          <div v-if="asset.template_role" class="text-xs text-muted-foreground/40">
            模板角色：{{ asset.template_role }}
          </div>
          <div v-if="asset.notes" class="text-xs text-muted-foreground/40">
            备注：{{ asset.notes }}
          </div>
        </div>
        <!-- 多策略时展示设置按钮；单策略自动选定，不展示 -->
        <Button v-if="strategyOptions.length > 1" variant="ghost" size="sm" class="h-7 gap-1 text-xs shrink-0" :disabled="disabled"
          @click="openStrategyEditor">
          <Pencil class="h-3 w-3" /> 设置
        </Button>
      </div>
    </div>

    <!-- ─── Prompt 段落卡片（Markdown 渲染 + 点击编辑） ─── -->
    <div class="space-y-4">
      <div v-for="sec in promptSections" :key="sec.key"
        class="rounded-xl border bg-card transition-all hover:border-border/60">
        <!-- 标题行 -->
        <div class="flex items-center justify-between px-4 pt-4 pb-1">
          <div class="flex items-center gap-2">
            <span class="text-sm font-medium text-muted-foreground">{{ sec.label }}</span>
            <Badge v-if="sec.required" variant="outline" class="text-[9px] text-primary/60 border-primary/20">必填</Badge>
            <!-- ? 悬浮气泡 -->
            <TooltipProvider v-if="sec.detail" :delay-duration="200">
              <Tooltip>
                <TooltipTrigger as-child>
                  <button class="inline-flex items-center justify-center h-4 w-4 rounded-full text-muted-foreground/30 hover:text-muted-foreground/60 hover:bg-muted/30 transition-colors">
                    <HelpCircle class="h-3 w-3" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" :side-offset="6" class="max-w-xs text-xs leading-relaxed">
                  {{ sec.detail }}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div class="flex gap-1 items-center">
            <button v-if="(asset as unknown as Record<string, string>)?.[sec.key] && isContentLong(String((asset as unknown as Record<string, string>)?.[sec.key] ?? ''))"
              class="text-[10px] text-muted-foreground/40 hover:text-muted-foreground transition-colors mr-1 px-1.5 py-0.5 rounded hover:bg-muted/20"
              @click="expandedSections.has(sec.key) ? expandedSections.delete(sec.key) : expandedSections.add(sec.key)">
              {{ expandedSections.has(sec.key) ? '收起' : '展开' }}
            </button>
            <Button v-if="(asset as unknown as Record<string, string>)?.[sec.key]"
              variant="ghost" size="icon" class="h-6 w-6 text-muted-foreground/30 hover:text-muted-foreground"
              @click="copyContent(String((asset as unknown as Record<string, string>)?.[sec.key] ?? ''), sec.key)">
              <Check v-if="copiedKey === sec.key" class="h-3 w-3 text-emerald-400" />
              <Copy v-else class="h-3 w-3" />
            </Button>
            <Button variant="ghost" size="sm" class="h-6 gap-1 text-xs text-muted-foreground/40 hover:text-muted-foreground"
              :disabled="disabled"
              @click="openSectionEditor(sec.key, sec.label)">
              <Pencil class="h-3 w-3" />
              编辑
            </Button>
          </div>
        </div>
        <!-- 简介 -->
        <div v-if="sec.description" class="px-4 pb-2">
          <p class="text-xs text-muted-foreground/60">{{ sec.description }}</p>
        </div>
        <!-- 内容（Markdown 渲染 + 长内容截断） -->
        <div class="px-4 pb-4">
          <template v-if="(asset as unknown as Record<string, string>)?.[sec.key]">
            <div class="relative">
              <div
                class="prose prose-sm dark:prose-invert max-w-none text-foreground/90"
                :class="{ 'max-h-40 overflow-hidden': !expandedSections.has(sec.key) }"
                v-html="renderMarkdown(String((asset as unknown as Record<string, string>)?.[sec.key] ?? ''))" />
              <!-- 渐变遮罩 + 查看全部（仅当内容被截断时） -->
              <div v-if="!expandedSections.has(sec.key) && isContentLong(String((asset as unknown as Record<string, string>)?.[sec.key] ?? ''))"
                class="absolute bottom-0 left-0 right-0 h-16 bg-gradient-to-t from-card to-transparent flex items-end justify-center pb-1">
                <button
                  class="text-[11px] text-primary/70 hover:text-primary font-medium transition-colors bg-background/80 backdrop-blur-sm px-2.5 py-0.5 rounded-full border border-border/30 shadow-sm"
                  @click="expandedSections.add(sec.key)">
                  查看全部
                </button>
              </div>
            </div>
            <button v-if="expandedSections.has(sec.key)"
              class="text-xs text-muted-foreground/40 hover:text-muted-foreground mt-2 transition-colors"
              @click="expandedSections.delete(sec.key)">
              收起
            </button>
          </template>
          <div v-else
            class="rounded-lg border border-dashed border-border/40 bg-muted/5 p-4 text-center cursor-pointer hover:bg-muted/10 transition-colors"
            @click="!disabled && openSectionEditor(sec.key, sec.label)">
            <Pencil class="h-4 w-4 mx-auto mb-1.5 text-muted-foreground/30" />
            <p class="text-xs text-muted-foreground/40">点击添加{{ sec.label }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- ─── 分段编辑弹窗 ─── -->
  <Teleport to="body">
    <div v-if="showSectionEditor"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="closeSectionEditor" />
      <div
        class="relative z-10 w-full max-w-7xl max-h-[85vh] flex flex-col rounded-xl border bg-background shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <!-- 弹窗头 -->
        <div class="flex items-center justify-between px-6 py-3 border-b shrink-0">
          <div class="flex items-center gap-3">
            <FileText class="h-4 w-4 text-primary" />
            <h3 class="text-base font-semibold">{{ editingSectionLabel }}</h3>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[11px] text-muted-foreground/30">支持 Markdown 格式</span>
            <Button variant="ghost" size="icon" class="h-7 w-7" @click="closeSectionEditor">
              <X class="h-4 w-4" />
            </Button>
          </div>
        </div>

        <!-- 弹窗体：左右分栏 -->
        <div class="flex-1 flex min-h-0">
          <!-- 左：编辑器面板 -->
          <div class="flex-1 flex flex-col border-r border-border/30">
            <div class="flex items-center gap-1.5 px-4 py-2 border-b border-border/20 bg-muted/10 shrink-0">
              <Code class="h-3 w-3 text-primary/50" />
              <span class="text-[11px] font-medium text-muted-foreground/70">编辑</span>
              <Badge variant="outline" class="text-[9px] px-1.5 py-0 h-4 text-muted-foreground/40 border-border/30 ml-auto">Markdown</Badge>
            </div>
            <textarea
              v-model="editingSectionContent"
              class="flex-1 w-full bg-transparent px-4 py-3 text-sm font-mono placeholder:text-muted-foreground/30 focus-visible:outline-none resize-none leading-relaxed"
              :placeholder="promptSections.find(s => s.key === editingSectionKey)?.placeholder ?? ''" />
          </div>
          <!-- 右：实时预览面板 -->
          <div class="flex-1 flex flex-col">
            <div class="flex items-center gap-1.5 px-4 py-2 border-b border-border/20 bg-muted/10 shrink-0">
              <Eye class="h-3 w-3 text-emerald-500/50" />
              <span class="text-[11px] font-medium text-muted-foreground/70">实时预览</span>
              <div v-if="editingSectionContent?.trim()" class="ml-auto flex items-center gap-1">
                <span class="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span class="text-[10px] text-emerald-500/50">同步中</span>
              </div>
            </div>
            <div class="flex-1 overflow-y-auto px-4 py-3">
              <div v-if="editingSectionContent"
                class="prose prose-sm dark:prose-invert max-w-none text-foreground/90"
                v-html="renderedSectionPreview" />
              <div v-else class="flex flex-col items-center justify-center h-full text-muted-foreground/20">
                <div class="h-12 w-12 rounded-xl bg-muted/20 flex items-center justify-center mb-3">
                  <Eye class="h-5 w-5" />
                </div>
                <p class="text-xs text-muted-foreground/30">在左侧输入内容后</p>
                <p class="text-xs text-muted-foreground/30">这里会实时渲染 Markdown 预览</p>
              </div>
            </div>
          </div>
        </div>

        <!-- 弹窗尾 -->
        <div class="flex items-center justify-end px-6 py-3 border-t shrink-0">
          <p v-if="sectionSaveError" class="text-xs text-rose-500 mr-auto">{{ sectionSaveError }}</p>
          <div class="flex gap-2">
            <Button variant="outline" size="sm" :disabled="sectionSaving" @click="closeSectionEditor">取消</Button>
            <Button size="sm" class="gap-1" :disabled="sectionSaving" @click="handleSectionSave">
              <Loader2 v-if="sectionSaving" class="h-3.5 w-3.5 animate-spin" />
              <Save v-else class="h-3.5 w-3.5" />
              保存
            </Button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ─── 渲染策略编辑弹窗 ─── -->
  <Teleport to="body">
    <div v-if="showStrategyEditor"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showStrategyEditor = false" />
      <div
        class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        <h3 class="text-base font-semibold mb-4">Prompt 设置</h3>
        <div class="space-y-4">
          <div>
            <label class="text-xs text-muted-foreground mb-1.5 block">渲染策略</label>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" class="h-8 w-full max-w-xs justify-between text-xs font-normal">
                  {{strategyOptions.find((s: { value: string }) => s.value === editingStrategy)?.label ?? editingStrategy}}
                  <ChevronDown class="h-3 w-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="min-w-[240px]">
                <DropdownMenuRadioGroup :model-value="editingStrategy"
                  @update:model-value="(v) => editingStrategy = String(v) as ManagedAgentHostRenderStrategy">
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
          <div>
            <label class="text-xs text-muted-foreground mb-1 block">备注</label>
            <textarea v-model="editingNotes" rows="2"
              class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="内部备注（可选）" />
          </div>
        </div>
        <p v-if="strategySaveError" class="text-xs text-rose-500 mt-3">{{ strategySaveError }}</p>
        <div class="flex gap-3 mt-4">
          <Button variant="outline" class="flex-1" :disabled="strategySaving" @click="showStrategyEditor = false">取消</Button>
          <Button class="flex-1" :disabled="strategySaving" @click="handleStrategySave">
            <Loader2 v-if="strategySaving" class="h-4 w-4 animate-spin mr-1" />
            保存
          </Button>
        </div>
      </div>
    </div>
  </Teleport>

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
                @click="copyContent(artifact.content, `artifact-${idx}`)">
                <Check v-if="copiedKey === `artifact-${idx}`" class="h-3 w-3 text-emerald-400" />
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
