<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { toast } from 'vue-sonner';
import {
  managedAgentBootstrapApi,
  type ManagedAgentBootstrapTokenListItem,
  type ManagedAgentBootstrapTokenCreateResponse,
  type ManagedAgentBootstrapPurpose,
  type ManagedAgentBootstrapScriptResponse,
  type ManagedAgentOnboardingMessageResponse,
} from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Loader2, AlertCircle, Plus, Trash2, Copy, Check, Terminal, MessageCircle, Key, Shield, Clock,
} from 'lucide-vue-next';

const props = defineProps<{ agentId: string; disabled?: boolean }>();

// ─── Token 列表 ───

const tokens = ref<ManagedAgentBootstrapTokenListItem[]>([]);
const loadingTokens = ref(false);
const tokenError = ref('');

// ─── 创建 Token ───

const showCreateToken = ref(false);
const creatingToken = ref(false);
const newTokenPurpose = ref<ManagedAgentBootstrapPurpose>('download_script');
const newTokenTtl = ref(3600);
const newTokenScope = ref('');
const createdToken = ref<ManagedAgentBootstrapTokenCreateResponse | null>(null);

// ─── 撤销 ───

const revokingId = ref<string | null>(null);

// ─── 脚本 / Onboarding ───

const loadingScript = ref(false);
const scriptResult = ref<ManagedAgentBootstrapScriptResponse | null>(null);
const loadingOnboarding = ref(false);
const onboardingResult = ref<ManagedAgentOnboardingMessageResponse | null>(null);

// ─── 复制 ───

const copiedKey = ref<string | null>(null);
async function copyText(text: string, key: string) {
  await navigator.clipboard.writeText(text);
  copiedKey.value = key;
  setTimeout(() => { copiedKey.value = null; }, 2000);
}

// ─── Purpose 选项 ───

const purposeOptions: { value: ManagedAgentBootstrapPurpose; label: string }[] = [
  { value: 'download_script', label: '下载脚本' },
  { value: 'register_runtime', label: '注册运行态' },
];

function getPurposeLabel(p: string) {
  return purposeOptions.find(o => o.value === p)?.label ?? p;
}

// ─── 加载 Token ───

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

onMounted(() => { void loadTokens(); });
watch(() => props.agentId, () => {
  createdToken.value = null;
  scriptResult.value = null;
  onboardingResult.value = null;
  void loadTokens();
});

// ─── 创建 Token ───

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
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    toast.error(msg ?? '创建失败');
  } finally {
    creatingToken.value = false;
  }
}

// ─── 撤销 Token ───

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

// ─── 生成部署脚本 ───

async function handleGetScript() {
  loadingScript.value = true;
  try {
    const res = await managedAgentBootstrapApi.getBootstrapScript(props.agentId);
    scriptResult.value = res.data;
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    toast.error(msg ?? '生成脚本失败');
  } finally {
    loadingScript.value = false;
  }
}

// ─── 生成 Onboarding 消息 ───

async function handleGetOnboarding() {
  loadingOnboarding.value = true;
  try {
    const res = await managedAgentBootstrapApi.getOnboardingMessage(props.agentId);
    onboardingResult.value = res.data;
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    toast.error(msg ?? '生成消息失败');
  } finally {
    loadingOnboarding.value = false;
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

function isExpired(expiresAt: string) {
  return new Date(expiresAt) < new Date();
}
</script>

<template>
  <div class="space-y-6 animate-slide-up">
    <!-- ════════════════════ 快速操作 ════════════════════ -->
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <!-- 部署脚本 -->
      <div class="rounded-xl border bg-card p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <Terminal class="h-4 w-4 text-primary" />
            <span class="text-sm font-medium">部署脚本</span>
          </div>
          <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="loadingScript || disabled"
            @click="handleGetScript">
            <Loader2 v-if="loadingScript" class="h-3 w-3 animate-spin" />
            生成
          </Button>
        </div>
        <p class="text-xs text-muted-foreground/60 mb-3">生成一键部署脚本，包含 Token，可在目标机器上直接执行。</p>
        <template v-if="scriptResult">
          <div class="relative">
            <pre
              class="rounded-lg bg-muted/30 border p-3 text-xs font-mono whitespace-pre-wrap break-all max-h-48 overflow-y-auto leading-relaxed">{{ scriptResult.script }}</pre>
            <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
              @click="copyText(scriptResult.script, 'script')">
              <Check v-if="copiedKey === 'script'" class="h-3 w-3 text-emerald-400" />
              <Copy v-else class="h-3 w-3" />
            </Button>
          </div>
          <p class="text-[11px] text-muted-foreground/40 mt-2">
            注册 Token 过期：{{ formatDate(scriptResult.register_token_expires_at) }}
          </p>
        </template>
      </div>

      <!-- Onboarding 消息 -->
      <div class="rounded-xl border bg-card p-4">
        <div class="flex items-center justify-between mb-3">
          <div class="flex items-center gap-2">
            <MessageCircle class="h-4 w-4 text-primary" />
            <span class="text-sm font-medium">Onboarding 消息</span>
          </div>
          <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="loadingOnboarding || disabled"
            @click="handleGetOnboarding">
            <Loader2 v-if="loadingOnboarding" class="h-3 w-3 animate-spin" />
            生成
          </Button>
        </div>
        <p class="text-xs text-muted-foreground/60 mb-3">生成可发送给 Agent 的引导消息和 curl 下载命令。</p>
        <template v-if="onboardingResult">
          <div class="space-y-2">
            <div class="relative">
              <div class="text-[11px] text-muted-foreground/50 mb-1">消息</div>
              <pre
                class="rounded-lg bg-muted/30 border p-3 text-xs whitespace-pre-wrap break-all max-h-32 overflow-y-auto leading-relaxed">{{ onboardingResult.message }}</pre>
              <Button variant="ghost" size="icon"
                class="absolute top-6 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                @click="copyText(onboardingResult.message, 'msg')">
                <Check v-if="copiedKey === 'msg'" class="h-3 w-3 text-emerald-400" />
                <Copy v-else class="h-3 w-3" />
              </Button>
            </div>
            <div class="relative">
              <div class="text-[11px] text-muted-foreground/50 mb-1">curl 命令</div>
              <pre
                class="rounded-lg bg-muted/30 border p-3 text-xs font-mono whitespace-pre-wrap break-all max-h-24 overflow-y-auto leading-relaxed">{{ onboardingResult.curl_command }}</pre>
              <Button variant="ghost" size="icon"
                class="absolute top-6 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
                @click="copyText(onboardingResult.curl_command, 'curl')">
                <Check v-if="copiedKey === 'curl'" class="h-3 w-3 text-emerald-400" />
                <Copy v-else class="h-3 w-3" />
              </Button>
            </div>
          </div>
          <p class="text-[11px] text-muted-foreground/40 mt-2">
            下载 Token 过期：{{ formatDate(onboardingResult.download_token_expires_at) }}
          </p>
        </template>
      </div>
    </div>

    <Separator />

    <!-- ════════════════════ Token 管理 ════════════════════ -->
    <div>
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <Key class="h-4 w-4 text-muted-foreground" />
          <span class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">Bootstrap Tokens</span>
          <Badge variant="outline" class="text-[10px] tabular-nums">{{ tokens.length }}</Badge>
        </div>
        <Button variant="outline" size="sm" class="h-7 gap-1 text-xs" :disabled="disabled"
          @click="showCreateToken = true">
          <Plus class="h-3 w-3" /> 新建 Token
        </Button>
      </div>

      <!-- 刚创建的 Token 高亮 -->
      <div v-if="createdToken"
        class="rounded-xl border-2 border-emerald-500/30 bg-emerald-500/5 p-4 mb-3 animate-slide-up">
        <div class="flex items-center gap-2 mb-2">
          <Shield class="h-4 w-4 text-emerald-400" />
          <span class="text-sm font-medium text-emerald-400">Token 已创建 — 请立即复制</span>
        </div>
        <div class="relative">
          <pre class="rounded-lg bg-background border p-3 text-xs font-mono break-all leading-relaxed select-all">{{
            createdToken.token }}</pre>
          <Button variant="ghost" size="icon" class="absolute top-2 right-2 h-6 w-6 bg-background/80 backdrop-blur-sm"
            @click="copyText(createdToken.token, 'new-token')">
            <Check v-if="copiedKey === 'new-token'" class="h-3 w-3 text-emerald-400" />
            <Copy v-else class="h-3 w-3" />
          </Button>
        </div>
        <p class="text-[11px] text-amber-400 mt-2">⚠ 此 Token 仅展示一次，关闭后将无法再次查看完整值。</p>
        <div class="flex items-center gap-3 mt-2 text-[11px] text-muted-foreground/50">
          <span>用途：{{ getPurposeLabel(createdToken.purpose) }}</span>
          <span>过期：{{ formatDate(createdToken.expires_at) }}</span>
        </div>
        <Button variant="ghost" size="sm" class="h-6 text-[11px] mt-2 text-muted-foreground/50"
          @click="createdToken = null">关闭</Button>
      </div>

      <!-- 加载 -->
      <div v-if="loadingTokens" class="flex items-center justify-center py-8">
        <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
      </div>

      <!-- 错误 -->
      <div v-else-if="tokenError" class="text-center py-8">
        <AlertCircle class="h-5 w-5 mx-auto mb-2 text-rose-400" />
        <p class="text-xs text-muted-foreground">{{ tokenError }}</p>
        <Button variant="link" size="sm" class="mt-1" @click="loadTokens">重试</Button>
      </div>

      <!-- 空 -->
      <div v-else-if="tokens.length === 0"
        class="rounded-xl border border-dashed bg-muted/10 p-6 text-center text-muted-foreground/40">
        <Key class="h-6 w-6 mx-auto mb-2" />
        <p class="text-xs">暂无 Bootstrap Token</p>
      </div>

      <!-- Token 列表 -->
      <div v-else class="space-y-2">
        <div v-for="(token, idx) in tokens" :key="token.id"
          class="rounded-xl border bg-card p-3 flex items-center gap-3 animate-slide-up"
          :class="{ 'opacity-50': !token.is_valid }" :style="{ animationDelay: `${idx * 25}ms` }">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap mb-0.5">
              <span class="text-xs font-mono text-muted-foreground">{{ token.token_masked }}</span>
              <Badge variant="outline" class="text-[10px]">{{ getPurposeLabel(token.purpose) }}</Badge>
              <Badge v-if="!token.is_valid" variant="outline" class="text-[10px] text-rose-400 border-rose-500/20">
                {{ token.revoked_at ? '已撤销' : isExpired(token.expires_at) ? '已过期' : '已使用' }}
              </Badge>
              <Badge v-else variant="outline" class="text-[10px] text-emerald-400 border-emerald-500/20">
                有效
              </Badge>
            </div>
            <div class="flex flex-wrap gap-x-3 gap-y-0.5 text-[11px] text-muted-foreground/40">
              <span class="flex items-center gap-1">
                <Clock class="h-3 w-3" /> 过期 {{ formatDate(token.expires_at) }}
              </span>
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

    <!-- ─── 创建 Token 弹窗 ─── -->
    <Teleport to="body">
      <div v-if="showCreateToken"
        class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
        <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showCreateToken = false" />
        <div
          class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200">
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
            <Button variant="outline" class="flex-1" :disabled="creatingToken"
              @click="showCreateToken = false">取消</Button>
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
