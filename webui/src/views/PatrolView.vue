<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RefreshCw, AlertTriangle, Clock, Ban, CheckCircle2, Loader2 } from 'lucide-vue-next'
import api from '@/api/client'

// ── Types ──────────────────────────────────────────────

interface TimeoutSubTask {
  id: string
  task_id: string
  name: string
  status: string
  assigned_agent: string | null
  timeout_minutes: number
  last_heartbeat: string | null
  created_at: string | null
  updated_at: string | null
}

interface PatrolCheckResponse {
  blocked: TimeoutSubTask[]
  available_timeout: TimeoutSubTask[]
  in_progress_timeout: TimeoutSubTask[]
  alert: boolean
}

// ── State ───────────────────────────────────────────────

const loading = ref(false)
const error = ref('')
const patrolData = ref<PatrolCheckResponse | null>(null)

// ── Helpers ─────────────────────────────────────────────

function formatDate(value: string | null) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return '—'
  return new Intl.DateTimeFormat('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
}

function formatAgent(name: string | null) {
  return name || '未分配'
}

function subTaskBadgeClass(status: string) {
  return {
    pending: 'border-slate-300 bg-slate-100 text-slate-700',
    assigned: 'border-indigo-200 bg-indigo-50 text-indigo-700',
    in_progress: 'border-sky-200 bg-sky-50 text-sky-700',
    review: 'border-amber-200 bg-amber-50 text-amber-700',
    rework: 'border-orange-200 bg-orange-50 text-orange-700',
    blocked: 'border-rose-200 bg-rose-50 text-rose-700',
    done: 'border-emerald-200 bg-emerald-50 text-emerald-700',
    cancelled: 'border-stone-200 bg-stone-100 text-stone-700',
  }[status] ?? 'border-border bg-muted text-muted-foreground'
}

function subTaskStatusLabel(status: string) {
  return {
    pending: '待分配',
    assigned: '已分配',
    in_progress: '执行中',
    review: '待审查',
    rework: '返工中',
    blocked: '阻塞',
    done: '已完成',
    cancelled: '已取消',
  }[status] ?? status
}

function dotClass(status: string) {
  return {
    pending: 'bg-slate-400',
    assigned: 'bg-indigo-500',
    in_progress: 'bg-sky-500 animate-pulse',
    review: 'bg-amber-500 animate-pulse',
    rework: 'bg-orange-500 animate-pulse',
    blocked: 'bg-rose-500',
    done: 'bg-emerald-500',
    cancelled: 'bg-stone-400',
  }[status] ?? 'bg-muted-foreground'
}

// ── Computed ────────────────────────────────────────────

const total = computed(() => {
  if (!patrolData.value) return 0
  return (
    patrolData.value.blocked.length +
    patrolData.value.available_timeout.length +
    patrolData.value.in_progress_timeout.length
  )
})

const alertLevel = computed(() => {
  if (!patrolData.value?.alert) return 'ok'
  if (patrolData.value.blocked.length > 0) return 'critical'
  if (total.value > 5) return 'warning'
  return 'normal'
})

// ── Load ────────────────────────────────────────────────

async function loadPatrol() {
  loading.value = true
  error.value = ''
  try {
    const response = await api.get<PatrolCheckResponse>('/patrol/check')
    patrolData.value = response.data
  } catch (e) {
    console.error('[patrol/check] Failed', e)
    error.value = '巡查接口请求失败，请检查后端服务。'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void loadPatrol()
})
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-3.5rem)]">
    <!-- ─── 顶栏 ─── -->
    <header class="shrink-0 border-b border-border/40 bg-background px-4 py-3">
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <AlertTriangle
            class="h-5 w-5"
            :class="{
              'text-emerald-500': alertLevel === 'ok',
              'text-amber-500': alertLevel === 'normal' || alertLevel === 'warning',
              'text-rose-500': alertLevel === 'critical',
            }"
          />
          <h1 class="text-base font-semibold">系统巡查</h1>
        </div>
        <div class="flex-1" />
        <span
          v-if="patrolData"
          class="text-xs text-muted-foreground tabular-nums"
        >
          共 {{ total }} 项异常
        </span>
        <button
          class="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          :class="loading ? 'opacity-50 pointer-events-none' : ''"
          @click="loadPatrol"
        >
          <RefreshCw class="h-3.5 w-3.5" :class="loading ? 'animate-spin' : ''" />
          刷新
        </button>
      </div>

      <!-- Alert banner -->
      <div
        v-if="patrolData?.alert"
        class="mt-2.5 rounded-lg border px-3 py-2 text-xs flex items-center gap-2"
        :class="{
          'border-rose-300 bg-rose-50 text-rose-700': alertLevel === 'critical',
          'border-amber-300 bg-amber-50 text-amber-700': alertLevel === 'warning',
          'border-sky-300 bg-sky-50 text-sky-700': alertLevel === 'normal',
        }"
      >
        <AlertTriangle class="h-3.5 w-3.5 shrink-0" />
        <span v-if="alertLevel === 'critical'">检测到 {{ patrolData.blocked.length }} 个阻塞任务，请立即处理。</span>
        <span v-else-if="alertLevel === 'warning'">存在 {{ total }} 项超时任务，请关注。</span>
        <span v-else>存在少量超时任务，建议关注。</span>
      </div>

      <div
        v-else-if="patrolData && !patrolData.alert"
        class="mt-2.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs flex items-center gap-2 text-emerald-700"
      >
        <CheckCircle2 class="h-3.5 w-3.5 shrink-0" />
        当前无超时或阻塞任务，系统运行正常。
      </div>
    </header>

    <!-- ─── 内容 ─── -->
    <div class="flex-1 overflow-y-auto p-4 space-y-6">
      <!-- 加载 -->
      <div v-if="loading && !patrolData" class="flex items-center justify-center py-20">
        <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
      </div>

      <!-- 错误 -->
      <div v-else-if="error" class="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
        <p class="text-sm text-muted-foreground">{{ error }}</p>
        <button class="mt-3 text-xs text-primary hover:underline" @click="loadPatrol">重试</button>
      </div>

      <template v-else-if="patrolData">
        <!-- 阻塞任务 -->
        <section>
          <div class="flex items-center gap-2 mb-3">
            <Ban class="h-4 w-4 text-rose-500" />
            <h2 class="text-sm font-semibold">阻塞任务</h2>
            <span class="ml-1 text-xs text-muted-foreground tabular-nums">({{ patrolData.blocked.length }})</span>
          </div>

          <div v-if="patrolData.blocked.length === 0" class="rounded-xl border border-dashed border-emerald-200 bg-emerald-50/50 p-5 text-center">
            <p class="text-xs text-emerald-600">无阻塞任务</p>
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="(item, idx) in patrolData.blocked"
              :key="item.id"
              class="rounded-xl border border-rose-200 bg-rose-50/30 p-4 border-l-[3px] border-l-rose-500 animate-slide-up"
              :style="{ animationDelay: `${idx * 40}ms` }"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-1.5">
                  <span class="inline-block w-2 h-2 rounded-full bg-rose-500 shrink-0" />
                  <span class="text-sm font-medium leading-5">{{ item.name }}</span>
                </div>
                <span class="text-[10px] border border-rose-200 bg-rose-100 text-rose-700 px-1.5 py-0.5 rounded-full shrink-0">
                  阻塞
                </span>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                <span>执行者：{{ formatAgent(item.assigned_agent) }}</span>
                <span>超时：{{ item.timeout_minutes }} 分钟</span>
                <span>更新于 {{ formatDate(item.updated_at) }}</span>
                <span>心跳 {{ formatDate(item.last_heartbeat) }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 超时未认领 -->
        <section>
          <div class="flex items-center gap-2 mb-3">
            <Clock class="h-4 w-4 text-amber-500" />
            <h2 class="text-sm font-semibold">超时未认领</h2>
            <span class="ml-1 text-xs text-muted-foreground tabular-nums">({{ patrolData.available_timeout.length }})</span>
          </div>

          <div v-if="patrolData.available_timeout.length === 0" class="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-center">
            <p class="text-xs text-muted-foreground">无超时未认领任务</p>
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="(item, idx) in patrolData.available_timeout"
              :key="item.id"
              class="rounded-xl border border-amber-100 bg-amber-50/20 p-4 border-l-[3px] border-l-amber-400 animate-slide-up"
              :style="{ animationDelay: `${idx * 40}ms` }"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-1.5">
                  <span class="inline-block w-2 h-2 rounded-full bg-amber-400 shrink-0" />
                  <span class="text-sm font-medium leading-5">{{ item.name }}</span>
                </div>
                <span class="border text-[10px] border-amber-200 bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full shrink-0">
                  超时未认领
                </span>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                <span>超时：{{ item.timeout_minutes }} 分钟</span>
                <span>创建于 {{ formatDate(item.created_at) }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 超时执行中 -->
        <section>
          <div class="flex items-center gap-2 mb-3">
            <Clock class="h-4 w-4 text-sky-500" />
            <h2 class="text-sm font-semibold">执行中超时</h2>
            <span class="ml-1 text-xs text-muted-foreground tabular-nums">({{ patrolData.in_progress_timeout.length }})</span>
          </div>

          <div v-if="patrolData.in_progress_timeout.length === 0" class="rounded-xl border border-dashed border-slate-200 bg-slate-50/50 p-5 text-center">
            <p class="text-xs text-muted-foreground">无执行中超时任务</p>
          </div>
          <div v-else class="space-y-2">
            <div
              v-for="(item, idx) in patrolData.in_progress_timeout"
              :key="item.id"
              class="rounded-xl border border-sky-100 bg-sky-50/20 p-4 border-l-[3px] border-l-sky-400 animate-slide-up"
              :style="{ animationDelay: `${idx * 40}ms` }"
            >
              <div class="flex items-start justify-between gap-2">
                <div class="flex items-center gap-1.5">
                  <span class="inline-block w-2 h-2 rounded-full bg-sky-500 shrink-0" />
                  <span class="text-sm font-medium leading-5">{{ item.name }}</span>
                </div>
                <span class="border text-[10px] border-sky-200 bg-sky-100 text-sky-700 px-1.5 py-0.5 rounded-full shrink-0">
                  执行超时
                </span>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-muted-foreground">
                <span>执行者：{{ formatAgent(item.assigned_agent) }}</span>
                <span>超时：{{ item.timeout_minutes }} 分钟</span>
                <span>心跳 {{ formatDate(item.last_heartbeat) }}</span>
              </div>
            </div>
          </div>
        </section>
      </template>
    </div>
  </div>
</template>
