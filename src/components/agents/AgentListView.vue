<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue';
import { useDebounceFn } from '@vueuse/core';
import {
  managedAgentApi,
  type ManagedAgentPageResponse,
  type ManagedAgentRole,
  type ManagedAgentStatus,
} from '@/api/client';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu, DropdownMenuContent,
  DropdownMenuRadioGroup, DropdownMenuRadioItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Search, RefreshCw, Loader2, AlertCircle, Users, ArrowLeft, ArrowRight, Plus, ChevronDown,
} from 'lucide-vue-next';
import AgentCard from '@/components/agents/AgentCard.vue';
import AgentCreateDialog from '@/components/agents/dialogs/AgentCreateDialog.vue';

const emit = defineEmits<{ select: [agentId: string] }>();

const PAGE_SIZE = 20;
const keyword = ref('');
const roleFilter = ref<ManagedAgentRole | 'all'>('all');
const statusFilter = ref<ManagedAgentStatus | 'all'>('all');
const page = ref(1);
const loading = ref(false);
const listError = ref('');
const pageData = ref<ManagedAgentPageResponse>({ items: [], total: 0, page: 1, page_size: PAGE_SIZE });
const showCreateDialog = ref(false);

const roleOptions: { value: ManagedAgentRole | 'all'; label: string }[] = [
  { value: 'all', label: '全部角色' },
  { value: 'planner', label: '规划者' },
  { value: 'executor', label: '执行者' },
  { value: 'reviewer', label: '审查者' },
  { value: 'patrol', label: '巡查者' },
];

const statusOptions: { value: ManagedAgentStatus | 'all'; label: string }[] = [
  { value: 'all', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'configured', label: '已配置' },
  { value: 'deployed', label: '已部署' },
  { value: 'disabled', label: '已禁用' },
  { value: 'archived', label: '已归档' },
];

const totalPages = computed(() => Math.max(1, Math.ceil(pageData.value.total / PAGE_SIZE)));

let listRequestId = 0;
const reloadDebounced = useDebounceFn(() => { page.value = 1; void loadAgents(); }, 280);
watch([keyword, roleFilter, statusFilter], () => { loading.value = true; reloadDebounced(); });
onMounted(() => { void loadAgents(); });

async function loadAgents() {
  const requestId = ++listRequestId;
  loading.value = true;
  listError.value = '';
  try {
    const response = await managedAgentApi.list({
      page: page.value, page_size: PAGE_SIZE,
      role: roleFilter.value === 'all' ? undefined : roleFilter.value,
      status: statusFilter.value === 'all' ? undefined : statusFilter.value,
    });
    if (requestId !== listRequestId) return;
    pageData.value = response.data;
  } catch {
    if (requestId !== listRequestId) return;
    listError.value = 'Agent 列表加载失败，请稍后再试。';
    pageData.value = { items: [], total: 0, page: 1, page_size: PAGE_SIZE };
  } finally {
    if (requestId === listRequestId) loading.value = false;
  }
}

function goToPage(p: number) {
  if (p < 1 || p > totalPages.value || p === page.value) return;
  page.value = p;
  void loadAgents();
}

function refreshList() { void loadAgents(); }
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-3.5rem)]">
    <!-- 顶栏 -->
    <header class="shrink-0 border-b border-border/40 bg-background">
      <div class="max-w-6xl mx-auto px-6 py-3">
        <div class="flex items-center justify-between gap-4">
          <div class="flex items-center gap-2.5">
            <Users class="h-5 w-5 text-primary" />
            <h1 class="text-base font-semibold">Agent 管理</h1>
            <Badge variant="outline" class="text-xs tabular-nums">
              {{ pageData.total }}
            </Badge>
          </div>
          <div class="flex items-center gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" class="h-8 gap-1 text-xs font-normal">
                  {{roleOptions.find(o => o.value === roleFilter)?.label ?? '全部角色'}}
                  <ChevronDown class="h-3 w-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="min-w-[120px]">
                <DropdownMenuRadioGroup :model-value="roleFilter"
                  @update:model-value="(v) => roleFilter = String(v) as ManagedAgentRole | 'all'">
                  <DropdownMenuRadioItem v-for="option in roleOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button variant="outline" size="sm" class="h-8 gap-1 text-xs font-normal">
                  {{statusOptions.find(o => o.value === statusFilter)?.label ?? '全部状态'}}
                  <ChevronDown class="h-3 w-3 opacity-50" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" class="min-w-[120px]">
                <DropdownMenuRadioGroup :model-value="statusFilter"
                  @update:model-value="(v) => statusFilter = String(v) as ManagedAgentStatus | 'all'">
                  <DropdownMenuRadioItem v-for="option in statusOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </DropdownMenuRadioItem>
                </DropdownMenuRadioGroup>
              </DropdownMenuContent>
            </DropdownMenu>
            <div class="relative">
              <Search
                class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input v-model="keyword" class="h-8 w-44 bg-muted/30 pl-8 text-xs" placeholder="搜索名称…" />
            </div>
            <Button variant="outline" size="sm" class="h-8 gap-1.5 text-xs" @click="showCreateDialog = true">
              <Plus class="h-3.5 w-3.5" />
              新建
            </Button>
            <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="loading" @click="refreshList">
              <RefreshCw class="h-3.5 w-3.5" :class="loading ? 'animate-spin' : ''" />
            </Button>
          </div>
        </div>
      </div>
    </header>

    <!-- 内容区 -->
    <main class="flex-1 overflow-y-auto">
      <div class="max-w-6xl mx-auto px-6 py-5">
        <!-- 加载中 -->
        <div v-if="loading" class="flex items-center justify-center py-20">
          <Loader2 class="h-7 w-7 animate-spin text-muted-foreground" />
        </div>
        <!-- 错误 -->
        <div v-else-if="listError" class="flex flex-col items-center py-20 text-muted-foreground">
          <AlertCircle class="h-7 w-7 mb-2 text-rose-400" />
          <p class="text-sm">{{ listError }}</p>
          <Button variant="link" size="sm" class="mt-2" @click="refreshList">重试</Button>
        </div>
        <!-- 空 -->
        <div v-else-if="pageData.items.length === 0" class="flex flex-col items-center py-20 text-muted-foreground/50">
          <Users class="h-8 w-8 mb-3" />
          <p class="text-sm">暂无 Agent</p>
        </div>
        <!-- 卡片网格 -->
        <div v-else class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div v-for="(agent, idx) in pageData.items" :key="agent.id" class="animate-slide-up"
            :style="{ animationDelay: `${idx * 40}ms` }">
            <AgentCard :agent="agent" @select="emit('select', $event)" />
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="!loading && pageData.items.length > 0"
          class="flex items-center justify-center gap-3 py-5 text-sm text-muted-foreground">
          <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="page <= 1" @click="goToPage(page - 1)">
            <ArrowLeft class="h-4 w-4" />
          </Button>
          <span class="tabular-nums">{{ page }} / {{ totalPages }}</span>
          <Button variant="ghost" size="icon" class="h-8 w-8" :disabled="page >= totalPages"
            @click="goToPage(page + 1)">
            <ArrowRight class="h-4 w-4" />
          </Button>
        </div>
      </div>
    </main>

    <!-- 创建弹窗 -->
    <AgentCreateDialog v-model:open="showCreateDialog" @created="refreshList" />
  </div>
</template>
