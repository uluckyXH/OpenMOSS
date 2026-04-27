<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentBootstrapApi,
  type ManagedAgentBootstrapPurpose,
  type ManagedAgentBootstrapTokenCreateResponse,
  type ManagedAgentBootstrapTokenListItem,
  type ManagedAgentDeploymentState,
  type ManagedAgentListItem,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Loader2, AlertCircle, Plus, Trash2, Copy, Check, Key, Clock, ChevronDown, ChevronRight, Shield,
} from 'lucide-vue-next';
import OnboardingWizard from './bootstrap/OnboardingWizard.vue';
import SyncDeployPanel from './bootstrap/SyncDeployPanel.vue';

const props = defineProps<{ agentId: string; agent?: ManagedAgentListItem | null; disabled?: boolean }>();
const emit = defineEmits<{ saved: [] }>();

// ─── 部署阶段状态 ───

const deploymentState = ref<ManagedAgentDeploymentState | null>(null);
const loadingDeployState = ref(true);

async function loadDeploymentState() {
  loadingDeployState.value = true;
  try {
    const res = await managedAgentBootstrapApi.getDeploymentState(props.agentId);
    deploymentState.value = res.data;
  } catch {
    // non-critical, keep null
  } finally {
    loadingDeployState.value = false;
  }
}

function handleChildCompleted() {
  emit('saved');
  void loadDeploymentState();
}

// ─── Token 管理（高级，折叠） ───

const showAdvanced = ref(false);
const tokens = ref<ManagedAgentBootstrapTokenListItem[]>([]);
const loadingTokens = ref(false);
const tokenError = ref('');
const showCreateToken = ref(false);
const creatingToken = ref(false);
const newTokenPurpose = ref<ManagedAgentBootstrapPurpose>('download_script');
const newTokenTtl = ref(3600);
const newTokenScope = ref('');
const createdToken = ref<ManagedAgentBootstrapTokenCreateResponse | null>(null);
const revokingId = ref<string | null>(null);
const copiedKey = ref<string | null>(null);

const purposeOptions: { value: ManagedAgentBootstrapPurpose; label: string }[] = [
  { value: 'download_script', label: '下载脚本' },
  { value: 'register_runtime', label: '注册运行态' },
];

async function loadTokens() {
  loadingTokens.value = true;
  tokenError.value = '';
  try {
    const res = await managedAgentBootstrapApi.listTokens(props.agentId);
    tokens.value = res.data;
  } catch {
    tokenError.value = '加载 Token 列表失败';
  } finally {
    loadingTokens.value = false;
  }
}

async function handleCreateToken() {
  creatingToken.value = true;
  try {
    const res = await managedAgentBootstrapApi.createToken(props.agentId, {
      purpose: newTokenPurpose.value,
      ttl_seconds: newTokenTtl.value,
      scope_json: newTokenScope.value.trim() || undefined,
    });
    createdToken.value = res.data;
    showCreateToken.value = false;
    toast.success('Token 已创建');
    void loadTokens();
  } catch (err: unknown) {
    const data = (err as { response?: { data?: { detail?: string } } })?.response?.data;
    toast.error(data?.detail ?? '创建失败');
  } finally {
    creatingToken.value = false;
  }
}

async function handleRevoke(tokenId: string) {
  revokingId.value = tokenId;
  try {
    await managedAgentBootstrapApi.revokeToken(props.agentId, tokenId);
    toast.success('已撤销');
    void loadTokens();
  } catch {
    toast.error('撤销失败');
  } finally {
    revokingId.value = null;
  }
}

async function copyText(text: string, key: string) {
  await navigator.clipboard.writeText(text);
  copiedKey.value = key;
  setTimeout(() => { copiedKey.value = null; }, 2000);
}

function getPurposeLabel(p: string) {
  return purposeOptions.find(o => o.value === p)?.label ?? p;
}

function isExpired(expiresAt: string) {
  return new Date(expiresAt) < new Date();
}

function formatDate(value: string | null) {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch { return value; }
}

// ─── 生命周期 ───

onMounted(() => {
  void loadDeploymentState();
  void loadTokens();
});

watch(() => props.agentId, () => {
  deploymentState.value = null;
  createdToken.value = null;
  showAdvanced.value = false;
  void loadDeploymentState();
  void loadTokens();
});
</script>

<template>
  <div class="space-y-5 animate-slide-up">

    <!-- 加载中骨架 -->
    <div v-if="loadingDeployState" class="rounded-xl border bg-card p-8 flex items-center justify-center gap-2">
      <Loader2 class="h-5 w-5 animate-spin text-muted-foreground/40" />
      <span class="text-sm text-muted-foreground/40">加载部署状态…</span>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="!deploymentState" class="rounded-xl border border-rose-500/20 bg-rose-500/5 p-8 text-center space-y-2">
      <AlertCircle class="h-6 w-6 mx-auto text-rose-400" />
      <p class="text-sm font-medium">无法加载部署状态</p>
      <p class="text-xs text-muted-foreground/60">请检查网络连接后重试。</p>
      <Button variant="outline" size="sm" class="mt-2" @click="loadDeploymentState">重试</Button>
    </div>

    <!-- 主内容：按阶段切换 -->
    <template v-else>
      <!-- 首次接入 -->
      <OnboardingWizard
        v-if="deploymentState.deployment_phase === 'first_onboarding'"
        :agent-id="agentId"
        :agent="agent"
        :deployment-state="deploymentState"
        :disabled="disabled"
        @completed="handleChildCompleted"
      />

      <!-- 同步变更 / 已同步 -->
      <SyncDeployPanel
        v-else
        :agent-id="agentId"
        :agent="agent"
        :deployment-state="deploymentState"
        :disabled="disabled"
        @state-changed="handleChildCompleted"
      />
    </template>

    <!-- ════════════════════ Bootstrap Token 管理（高级，折叠） ════════════════════ -->
    <div class="rounded-xl border border-dashed border-border/70 bg-muted/5">
      <button type="button" class="flex w-full items-center justify-between px-4 py-3 text-left"
        @click="showAdvanced = !showAdvanced">
        <div class="flex items-center gap-2">
          <Key class="h-3.5 w-3.5 text-muted-foreground/40" />
          <span class="text-xs font-medium text-muted-foreground/60">Bootstrap Token 管理</span>
          <Badge variant="outline" class="text-[10px] tabular-nums">{{ tokens.length }}</Badge>
        </div>
        <div class="flex items-center gap-1 text-xs text-muted-foreground/40">
          {{ showAdvanced ? '收起' : '展开' }}
          <ChevronDown v-if="showAdvanced" class="h-3 w-3" />
          <ChevronRight v-else class="h-3 w-3" />
        </div>
      </button>

      <div v-if="showAdvanced" class="px-4 pb-4 space-y-3">
        <Separator />
        <div class="flex items-center justify-between">
          <p class="text-[11px] text-muted-foreground/40">
            手动创建 / 管理 Bootstrap Token。通常优先使用部署向导自动生成。
          </p>
          <Button variant="outline" size="sm" class="h-7 gap-1 text-xs shrink-0" :disabled="disabled"
            @click="showCreateToken = true">
            <Plus class="h-3 w-3" /> 新建
          </Button>
        </div>

        <div v-if="createdToken" class="rounded-lg border-2 border-emerald-500/30 bg-emerald-500/5 p-3 animate-slide-up">
          <div class="flex items-center gap-2 mb-2">
            <Shield class="h-3.5 w-3.5 text-emerald-400" />
            <span class="text-xs font-medium text-emerald-400">Token 已创建，请立即复制</span>
          </div>
          <div class="relative">
            <pre class="rounded-md bg-background border p-2.5 text-xs font-mono break-all leading-relaxed select-all">{{ createdToken.token }}</pre>
            <Button variant="ghost" size="icon" class="absolute top-1.5 right-1.5 h-6 w-6 bg-background/80 backdrop-blur-sm"
              @click="copyText(createdToken.token, 'new-token')">
              <Check v-if="copiedKey === 'new-token'" class="h-3 w-3 text-emerald-400" />
              <Copy v-else class="h-3 w-3" />
            </Button>
          </div>
          <p class="text-[11px] text-amber-400 mt-1.5">此 Token 仅展示一次，关闭后将无法再次查看完整值。</p>
          <div class="flex items-center gap-3 mt-1.5 text-[11px] text-muted-foreground/50">
            <span>用途：{{ getPurposeLabel(createdToken.purpose) }}</span>
            <span>过期：{{ formatDate(createdToken.expires_at) }}</span>
          </div>
          <Button variant="ghost" size="sm" class="h-5 text-[11px] mt-1.5 text-muted-foreground/50 px-1" @click="createdToken = null">关闭</Button>
        </div>

        <div v-if="loadingTokens" class="flex items-center justify-center py-6">
          <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
        <div v-else-if="tokenError" class="text-center py-6">
          <AlertCircle class="h-5 w-5 mx-auto mb-2 text-rose-400" />
          <p class="text-xs text-muted-foreground">{{ tokenError }}</p>
          <Button variant="link" size="sm" class="mt-1" @click="loadTokens">重试</Button>
        </div>
        <div v-else-if="tokens.length === 0"
          class="rounded-lg border border-dashed bg-muted/10 p-5 text-center text-muted-foreground/40">
          <Key class="h-5 w-5 mx-auto mb-1.5" />
          <p class="text-xs">暂无 Bootstrap Token</p>
        </div>
        <div v-else class="space-y-1.5">
          <div v-for="(token, idx) in tokens" :key="token.id"
            class="rounded-lg border bg-card px-3 py-2 flex items-center gap-3 animate-slide-up"
            :class="{ 'opacity-50': !token.is_valid }" :style="{ animationDelay: `${idx * 25}ms` }">
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2 flex-wrap mb-0.5">
                <span class="text-xs font-mono text-muted-foreground">{{ token.token_masked }}</span>
                <Badge variant="outline" class="text-[10px]">{{ getPurposeLabel(token.purpose) }}</Badge>
                <Badge v-if="!token.is_valid" variant="outline" class="text-[10px] text-rose-400 border-rose-500/20">
                  {{ token.revoked_at ? '已撤销' : isExpired(token.expires_at) ? '已过期' : '已使用' }}
                </Badge>
                <Badge v-else variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">有效</Badge>
              </div>
              <div class="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground/40">
                <span class="flex items-center gap-1"><Clock class="h-3 w-3" /> 过期 {{ formatDate(token.expires_at) }}</span>
                <span v-if="token.used_at">已使用 {{ formatDate(token.used_at) }}</span>
                <span>创建 {{ formatDate(token.created_at) }}</span>
              </div>
            </div>
            <Button v-if="token.is_valid" variant="ghost" size="icon"
              class="h-7 w-7 text-rose-400 hover:text-rose-500 shrink-0" :disabled="revokingId === token.id"
              @click="handleRevoke(token.id)">
              <Loader2 v-if="revokingId === token.id" class="h-3 w-3 animate-spin" />
              <Trash2 v-else class="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建 Token 弹窗 -->
    <Teleport to="body">
      <div v-if="showCreateToken"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showCreateToken = false" />
        <div class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
          <h3 class="text-base font-semibold mb-4">新建 Bootstrap Token</h3>
          <div class="space-y-3">
            <div>
              <label class="text-xs text-muted-foreground mb-1.5 block">用途</label>
              <div class="flex gap-1.5">
                <Button v-for="opt in purposeOptions" :key="opt.value" size="sm"
                  :variant="newTokenPurpose === opt.value ? 'default' : 'outline'" class="flex-1 h-8 text-xs"
                  @click="newTokenPurpose = opt.value">
                  {{ opt.label }}
                </Button>
              </div>
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">有效期（秒）</label>
              <Input v-model.number="newTokenTtl" type="number" min="300" />
              <p class="text-[11px] text-muted-foreground/40 mt-1">默认 3600 秒（1 小时）</p>
            </div>
            <div>
              <label class="text-xs text-muted-foreground mb-1 block">Scope (JSON，可选)</label>
              <textarea v-model="newTokenScope" rows="2"
                class="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                placeholder='{"key": "value"}' />
            </div>
          </div>
          <div class="flex gap-3 mt-4">
            <Button variant="outline" class="flex-1" :disabled="creatingToken" @click="showCreateToken = false">取消</Button>
            <Button class="flex-1" :disabled="creatingToken" @click="handleCreateToken">
              <Loader2 v-if="creatingToken" class="h-4 w-4 animate-spin mr-1" />
              创建
            </Button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>
