<script setup lang="ts">
import { ref } from 'vue';
import { toast } from 'vue-sonner';
import { managedAgentApi, type ManagedAgentDetail } from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  accessModeLabels,
  formatDate,
  formatDeployMode,
} from '@/composables/agents/useAgentFormatters';
import { Key, Copy, Check, RotateCcw, Loader2, ShieldAlert } from 'lucide-vue-next';

const props = defineProps<{
  agent: ManagedAgentDetail;
}>();
const emit = defineEmits<{ saved: [] }>();

const accessModeDescriptions: Record<string, string> = {
  local: '共享当前主力平台的公共工作目录和平台配置',
  remote: '独立外部平台，需要单独接入',
};

// ─── API Key 重置 ───
const resettingKey = ref(false);
const showResetConfirm = ref(false);
const newApiKey = ref<string | null>(null);
const copiedKey = ref(false);

const showKeyDialog = ref(false);

async function handleResetApiKey() {
  resettingKey.value = true;
  try {
    const res = await managedAgentApi.resetRuntimeApiKey(props.agent.id);
    newApiKey.value = res.data.api_key;
    showResetConfirm.value = false;
    showKeyDialog.value = true; // 弹出 Key 展示窗口
  } catch (err: unknown) {
    const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
    toast.error(msg ?? 'API Key 重置失败');
  } finally {
    resettingKey.value = false;
  }
}

function dismissKeyDialog() {
  showKeyDialog.value = false;
  newApiKey.value = null;
  emit('saved'); // 关闭后才刷新
}

async function copyApiKey(text: string) {
  await navigator.clipboard.writeText(text);
  copiedKey.value = true;
  setTimeout(() => { copiedKey.value = false; }, 2000);
}
</script>

<template>
  <div class="space-y-4 animate-slide-up">
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">Slug</div>
        <div class="text-sm font-mono break-all">{{ agent.slug }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">Agent 平台</div>
        <div class="text-sm">{{ agent.host_platform }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">部署模式</div>
        <div class="text-sm">{{ formatDeployMode(agent.deployment_mode) }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">平台归属</div>
        <div class="text-sm">{{ accessModeLabels[agent.host_access_mode] || agent.host_access_mode }}</div>
        <p class="mt-1 text-xs text-muted-foreground/60">
          {{ accessModeDescriptions[agent.host_access_mode] || '—' }}
        </p>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">关联运行态 Agent</div>
        <div class="text-sm font-mono break-all">{{ agent.runtime_agent_id ?? '未关联' }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">创建时间</div>
        <div class="text-sm">{{ formatDate(agent.created_at) }}</div>
      </div>

      <div class="rounded-xl border bg-card/50 p-4">
        <div class="text-xs text-muted-foreground font-medium mb-1">更新时间</div>
        <div class="text-sm">{{ formatDate(agent.updated_at) }}</div>
      </div>
    </div>

    <!-- ─── 运行态身份 ─── -->
    <div class="rounded-xl border bg-card/50 p-4">
      <div class="flex items-center gap-2 mb-3">
        <Key class="h-3.5 w-3.5 text-muted-foreground/50" />
        <span class="text-xs text-muted-foreground font-medium uppercase tracking-wider">运行态身份</span>
        <Badge v-if="agent.runtime_identity?.registered" variant="outline"
          class="text-[9px] border-emerald-500/20 bg-emerald-500/10 text-emerald-400">
          已注册
        </Badge>
        <Badge v-else variant="outline"
          class="text-[9px] border-zinc-500/20 bg-zinc-500/10 text-zinc-400">
          未注册
        </Badge>
      </div>

      <!-- API Key 脱敏值 -->
      <div class="flex items-center justify-between gap-3">
        <div class="min-w-0">
          <div class="text-xs text-muted-foreground font-medium mb-0.5">API Key</div>
          <div v-if="agent.runtime_identity?.api_key_masked"
            class="text-sm font-mono text-muted-foreground break-all">
            {{ agent.runtime_identity.api_key_masked }}
          </div>
          <div v-else class="text-sm text-muted-foreground/40 italic">
            {{ agent.runtime_identity?.registered ? '—' : '部署后自动生成' }}
          </div>
        </div>
        <Button v-if="agent.runtime_identity?.registered"
          variant="outline" size="sm" class="h-7 gap-1 text-xs shrink-0"
          @click="showResetConfirm = true">
          <RotateCcw class="h-3 w-3" /> 重置
        </Button>
      </div>
    </div>

    <!-- ─── 配置版本 ─── -->
    <div class="rounded-xl border bg-card/50 p-4">
      <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <div class="text-xs text-muted-foreground font-medium mb-1">配置版本</div>
          <div class="text-sm font-medium tabular-nums">
            配置 v{{ agent.config_version }}
            <template v-if="agent.deployed_config_version !== null">
              <span class="mx-1 text-muted-foreground/50">→</span>
              已部署 v{{ agent.deployed_config_version }}
            </template>
            <span v-else class="text-muted-foreground/60"> · 尚未部署</span>
          </div>
          <p class="mt-1 text-xs text-muted-foreground/60">
            {{ agent.needs_redeploy ? '当前配置有变更，发布前需要重新部署。' : '当前已部署版本与配置版本一致。' }}
          </p>
        </div>

        <Badge
          variant="outline"
          class="w-fit text-xs"
          :class="agent.needs_redeploy
            ? 'border-amber-500/20 bg-amber-500/10 text-amber-400'
            : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-400'"
        >
          {{ agent.needs_redeploy ? '需重新部署' : '已同步' }}
        </Badge>
      </div>
    </div>
  </div>

  <!-- ─── 重置确认弹窗 ─── -->
  <Teleport to="body">
    <div v-if="showResetConfirm"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showResetConfirm = false" />
      <div
        class="relative z-10 w-full max-w-sm rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 text-center space-y-3">
        <ShieldAlert class="h-8 w-8 mx-auto text-amber-500" />
        <h3 class="text-base font-semibold">重置 API Key</h3>
        <p class="text-sm text-muted-foreground">
          此操作将使当前 API Key 立即失效，生成一个全新 Key。正在运行的 Agent 会断开连接，需要重新部署。
        </p>
        <div class="flex gap-3 pt-2">
          <Button variant="outline" class="flex-1" :disabled="resettingKey" @click="showResetConfirm = false">取消</Button>
          <Button variant="destructive" class="flex-1" :disabled="resettingKey" @click="handleResetApiKey">
            <Loader2 v-if="resettingKey" class="h-4 w-4 animate-spin mr-1" />
            确认重置
          </Button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- ─── 新 API Key 展示弹窗 ─── -->
  <Teleport to="body">
    <div v-if="showKeyDialog && newApiKey"
      class="fixed inset-0 z-50 flex items-center justify-center p-4 animate-in fade-in duration-150">
      <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-2xl animate-in fade-in zoom-in-95 duration-200 space-y-4">
        <div class="text-center">
          <div class="mx-auto h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center mb-3">
            <Key class="h-6 w-6 text-emerald-400" />
          </div>
          <h3 class="text-base font-semibold">API Key 已重置</h3>
          <p class="text-sm text-muted-foreground mt-1">请立即复制保存，关闭后将无法再次查看完整 Key。</p>
        </div>

        <div class="rounded-lg border bg-muted/20 p-3">
          <code class="block text-sm font-mono break-all select-all leading-relaxed">{{ newApiKey }}</code>
        </div>

        <Button variant="outline" class="w-full gap-2" @click="copyApiKey(newApiKey!)">
          <Check v-if="copiedKey" class="h-4 w-4 text-emerald-400" />
          <Copy v-else class="h-4 w-4" />
          {{ copiedKey ? '已复制' : '复制 API Key' }}
        </Button>

        <div class="flex items-start gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 p-2.5">
          <ShieldAlert class="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <p class="text-xs text-muted-foreground leading-relaxed">
            旧 Key 已永久失效。如有正在运行的 Agent，需要使用新 Key 重新部署。
          </p>
        </div>

        <Button class="w-full" @click="dismissKeyDialog">我已保存，关闭</Button>
      </div>
    </div>
  </Teleport>
</template>
