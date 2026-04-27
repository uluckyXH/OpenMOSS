<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { managedAgentBootstrapApi, type ManagedAgentDeployScriptIntent, type ManagedAgentDeploymentSnapshot } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Loader2, AlertCircle, History, RefreshCw } from 'lucide-vue-next';

const props = defineProps<{ agentId: string }>();

const snapshots = ref<ManagedAgentDeploymentSnapshot[]>([]);
const loading = ref(false);
const error = ref('');

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const res = await managedAgentBootstrapApi.listDeploymentSnapshots(props.agentId);
    snapshots.value = res.data;
  } catch {
    error.value = '加载部署历史失败';
  } finally {
    loading.value = false;
  }
}

onMounted(() => load());
watch(() => props.agentId, () => load());

function intentLabel(intent: ManagedAgentDeployScriptIntent) {
  return intent === 'bootstrap' ? '首次接入' : '同步变更';
}

function statusLabel(status: string) {
  if (status === 'pending') return '待回传';
  if (status === 'confirmed') return '已确认';
  if (status === 'failed') return '失败';
  if (status === 'timeout') return '超时未回传';
  if (status === 'cancelled') return '已取消';
  return status;
}

function statusClass(status: string) {
  if (status === 'confirmed') return 'text-emerald-400 border-emerald-500/20';
  if (status === 'failed' || status === 'timeout') return 'text-rose-400 border-rose-500/20';
  if (status === 'cancelled') return 'text-muted-foreground/50 border-muted-foreground/20';
  return 'text-amber-400 border-amber-500/20';
}

function fmt(val: string | null) {
  if (!val) return '—';
  try {
    return new Date(val).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return val;
  }
}
</script>

<template>
  <div class="space-y-4 animate-slide-up">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <History class="h-4 w-4 text-muted-foreground/60" />
        <span class="text-sm font-semibold">部署快照历史</span>
        <Badge variant="outline" class="text-[10px] tabular-nums">{{ snapshots.length }}</Badge>
      </div>
      <Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" :disabled="loading" @click="load">
        <RefreshCw :class="['h-3 w-3', loading ? 'animate-spin' : '']" />
        刷新
      </Button>
    </div>

    <Separator />

    <div v-if="loading" class="flex items-center justify-center py-12">
      <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
    </div>

    <div v-else-if="error" class="flex flex-col items-center gap-2 py-12 text-center">
      <AlertCircle class="h-5 w-5 text-rose-400" />
      <p class="text-xs text-muted-foreground">{{ error }}</p>
      <Button variant="link" size="sm" @click="load">重试</Button>
    </div>

    <div v-else-if="snapshots.length === 0"
      class="rounded-xl border border-dashed bg-muted/5 p-10 text-center text-muted-foreground/40">
      <History class="h-8 w-8 mx-auto mb-2 opacity-50" />
      <p class="text-sm">暂无部署快照</p>
      <p class="text-xs mt-1">完成首次接入后，历史记录将显示在这里。</p>
    </div>

    <div v-else class="space-y-2">
      <div v-for="snap in snapshots" :key="snap.id"
        class="rounded-xl border bg-card px-4 py-3 space-y-2">
        <!-- 头部：意图、状态、版本 -->
        <div class="flex items-center gap-2 flex-wrap">
          <span class="text-xs font-mono text-muted-foreground/60 truncate max-w-[180px]">{{ snap.id }}</span>
          <Badge variant="outline" class="text-[10px]">{{ intentLabel(snap.script_intent) }}</Badge>
          <Badge variant="outline" class="text-[10px]" :class="statusClass(snap.status)">
            {{ statusLabel(snap.status) }}
          </Badge>
          <Badge v-if="snap.status === 'pending' && snap.is_likely_timeout"
            variant="outline" class="text-[10px] text-amber-400 border-amber-500/20">
            疑似超时
          </Badge>
          <Badge variant="outline" class="text-[10px]">v{{ snap.config_version }}</Badge>
        </div>

        <!-- 时间轴 -->
        <div class="flex flex-wrap gap-x-4 gap-y-0.5 text-[11px] text-muted-foreground/40">
          <span>创建 {{ fmt(snap.created_at) }}</span>
          <span v-if="snap.expires_at">超时截止 {{ fmt(snap.expires_at) }}</span>
          <span v-if="snap.confirmed_at" class="text-emerald-400/60">确认 {{ fmt(snap.confirmed_at) }}</span>
        </div>

        <!-- 错误详情 -->
        <p v-if="snap.failure_detail_json"
          class="text-[11px] text-rose-300 break-all bg-rose-500/5 rounded-md px-2 py-1.5">
          {{ snap.failure_detail_json }}
        </p>
      </div>
    </div>
  </div>
</template>
