<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useDebounceFn, useMediaQuery } from '@vueuse/core'
import {
    adminTaskApi,
    subTaskApi,
    taskApi,
    agentApi,
    adminTeamApi,
    type AdminModuleItem,
    type AdminPageResponse,
    type AdminSubTaskDetail,
    type AdminSubTaskItem,
    type AdminTaskDetail,
    type AdminTaskItem,
} from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import TextOverflowTooltip from '@/components/common/TextOverflowTooltip.vue'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import {
    Sheet,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetTitle,
} from '@/components/ui/sheet'

import { TooltipProvider } from '@/components/ui/tooltip'
import {
    AlertCircle,
    ArrowLeft,
    ArrowRight,
    FolderKanban,
    ListTodo,
    Loader2,
    Pencil,
    RefreshCw,
    Search,
} from 'lucide-vue-next'

const TASK_PAGE_SIZE = 8
const SUB_TASK_PAGE_SIZE = 8
const MIN_SKELETON_MS = 300

const isCompactLayout = useMediaQuery('(max-width: 1023px)')
const detailAnchor = ref<HTMLElement | null>(null)

const taskKeyword = ref('')
const taskStatus = ref('all')
const taskType = ref('all')
const taskPage = ref(1)

const subTaskStatus = ref('all')
const subTaskPage = ref(1)

const loadingTasks = ref(false)
const loadingDetail = ref(false)
const loadingSubTasks = ref(false)
const subTaskDetailLoading = ref(false)

const taskListError = ref('')
const detailError = ref('')
const subTaskListError = ref('')
const subTaskDetailError = ref('')

const selectedTaskId = ref<string | null>(null)
const selectedModuleId = ref<string | null>(null)
const selectedTask = ref<AdminTaskDetail | null>(null)
const selectedSubTask = ref<AdminSubTaskDetail | null>(null)
const subTaskSheetOpen = ref(false)

// 编辑任务弹窗状态
const showEditTaskDialog = ref(false)
const editTaskName = ref('')
const editTaskDescription = ref('')
const savingEditTask = ref(false)
const editTaskError = ref('')

// 编辑子任务弹窗状态
const showEditSubTaskDialog = ref(false)
const editSubTaskName = ref('')
const editSubTaskDescription = ref('')
const editSubTaskDeliverable = ref('')
const editSubTaskAcceptance = ref('')
const editSubTaskPriority = ref('')
const editSubTaskType = ref('')
const editSubTaskRemarks = ref('')
const editSubTaskStatus = ref('')
const editSubTaskAssignedAgent = ref('')
const editSubTaskRecurringConfig = ref('')
const savingEditSubTask = ref(false)
const editSubTaskError = ref('')

// 可用 Agent 列表
const availableAgents = ref<{ id: string; name: string; role: string }[]>([])
// 编辑子任务时的团队 Agent 列表
const editTeamAgents = ref<{ id: string; name: string; role: string }[]>([])

const taskPageData = ref<AdminPageResponse<AdminTaskItem>>(createEmptyPage<AdminTaskItem>())
const modulePageData = ref<AdminPageResponse<AdminModuleItem>>(createEmptyPage<AdminModuleItem>())
const subTaskPageData =
    ref<AdminPageResponse<AdminSubTaskItem>>(createEmptyPage<AdminSubTaskItem>())

let taskListRequestId = 0
let taskContextRequestId = 0
let subTaskListRequestId = 0
let subTaskDetailRequestId = 0
const detailKey = ref(0)

function minDelay(): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, MIN_SKELETON_MS))
}

const taskStatusOptions = [
    { value: 'all', label: '全部状态' },
    { value: 'planning', label: '规划中' },
    { value: 'active', label: '进行中' },
    { value: 'in_progress', label: '推进中' },
    { value: 'completed', label: '已完成' },
    { value: 'archived', label: '已归档' },
    { value: 'cancelled', label: '已取消' },
] as const

const taskTypeOptions = [
    { value: 'all', label: '全部类型' },
    { value: 'once', label: '一次性任务' },
    { value: 'recurring', label: '周期任务' },
] as const

const subTaskStatusOptions = [
    { value: 'all', label: '全部' },
    { value: 'pending', label: '待分配' },
    { value: 'assigned', label: '已分配' },
    { value: 'in_progress', label: '执行中' },
    { value: 'review', label: '待审查' },
    { value: 'rework', label: '返工中' },
    { value: 'blocked', label: '阻塞' },
    { value: 'done', label: '已完成' },
    { value: 'cancelled', label: '已取消' },
] as const

const selectedTaskProgress = computed(() => {
    if (!selectedTask.value) {
        return 0
    }
    return getCompletionRatio(selectedTask.value.done_count, selectedTask.value.sub_task_count)
})



const reloadTasksDebounced = useDebounceFn(() => {
    taskPage.value = 1
    void loadTasks()
}, 280)

watch([taskKeyword, taskStatus, taskType], () => {
    loadingTasks.value = true
    reloadTasksDebounced()
})

watch(subTaskStatus, () => {
    subTaskPage.value = 1
    if (selectedTaskId.value) {
        void loadSelectedTaskSubTasks(selectedTaskId.value)
    }
})

// 加载可用 Agent 列表
async function loadAvailableAgents() {
    try {
        const res = await agentApi.list({})
        availableAgents.value = (res.data.items || []).map((a: any) => ({
            id: a.id,
            name: a.name,
            role: a.role,
        }))
    } catch (e) {
        console.error('Failed to load agents:', e)
    }
}

// 加载团队 Agent 列表
async function loadTeamAgents(teamId: string) {
    if (!teamId) {
        editTeamAgents.value = availableAgents.value
        return
    }
    try {
        const res = await adminTeamApi.get(teamId)
        const members = res.data.members || []
        editTeamAgents.value = members.map((m: any) => ({
            id: m.agent_id,
            name: m.agent_name,
            role: m.role,
        }))
    } catch (e) {
        console.error('Failed to load team agents:', e)
        editTeamAgents.value = availableAgents.value
    }
}

onMounted(() => {
    void loadTasks()
    void loadAvailableAgents()
})

function createEmptyPage<T>(): AdminPageResponse<T> {
    return {
        items: [],
        total: 0,
        page: 1,
        page_size: 0,
        total_pages: 1,
        has_more: false,
    }
}

function clearSelectedTaskState() {
    selectedTaskId.value = null
    selectedModuleId.value = null
    selectedTask.value = null
    modulePageData.value = createEmptyPage<AdminModuleItem>()
    subTaskPageData.value = createEmptyPage<AdminSubTaskItem>()
    detailError.value = ''
    subTaskListError.value = ''
}

function toggleModule(moduleId: string) {
    selectedModuleId.value = selectedModuleId.value === moduleId ? null : moduleId
}

function formatDate(value: string | null) {
    if (!value) {
        return '未记录'
    }

    const date = new Date(value)
    if (Number.isNaN(date.getTime())) {
        return '未记录'
    }

    return new Intl.DateTimeFormat('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    }).format(date)
}

function formatTaskType(value: string) {
    if (value === 'once') {
        return '一次性'
    }
    if (value === 'recurring') {
        return '周期性'
    }
    return value
}

function formatTaskStatus(value: string) {
    return (
        {
            planning: '规划中',
            active: '进行中',
            in_progress: '推进中',
            completed: '已完成',
            archived: '已归档',
            cancelled: '已取消',
        }[value] ?? value
    )
}

function formatSubTaskStatus(value: string) {
    return (
        {
            pending: '待分配',
            assigned: '已分配',
            in_progress: '执行中',
            review: '待审查',
            rework: '返工中',
            blocked: '阻塞',
            done: '已完成',
            cancelled: '已取消',
        }[value] ?? value
    )
}

function formatPriority(value: string) {
    return (
        {
            high: '高优先',
            medium: '中优先',
            low: '低优先',
        }[value] ?? value
    )
}

function getCompletionRatio(doneCount: number, totalCount: number) {
    if (!totalCount) {
        return 0
    }
    return Math.round((doneCount / totalCount) * 100)
}



function getTaskBadgeClass(status: string) {
    return (
        {
            planning: 'border-slate-300 bg-slate-100 text-slate-700',
            active: 'border-amber-200 bg-amber-50 text-amber-700',
            in_progress: 'border-sky-200 bg-sky-50 text-sky-700',
            completed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
            archived: 'border-stone-200 bg-stone-100 text-stone-700',
            cancelled: 'border-rose-200 bg-rose-50 text-rose-700',
        }[status] ?? 'border-border bg-muted text-muted-foreground'
    )
}

function getSubTaskBadgeClass(status: string) {
    return (
        {
            pending: 'border-slate-300 bg-slate-100 text-slate-700',
            assigned: 'border-indigo-200 bg-indigo-50 text-indigo-700',
            in_progress: 'border-sky-200 bg-sky-50 text-sky-700',
            review: 'border-amber-200 bg-amber-50 text-amber-700',
            rework: 'border-orange-200 bg-orange-50 text-orange-700',
            blocked: 'border-rose-200 bg-rose-50 text-rose-700',
            done: 'border-emerald-200 bg-emerald-50 text-emerald-700',
            cancelled: 'border-stone-200 bg-stone-100 text-stone-700',
        }[status] ?? 'border-border bg-muted text-muted-foreground'
    )
}

function getSubTaskLeftBorderClass(status: string) {
    return (
        {
            pending: 'border-l-slate-300',
            assigned: 'border-l-indigo-400',
            in_progress: 'border-l-sky-500',
            review: 'border-l-amber-500',
            rework: 'border-l-orange-500',
            blocked: 'border-l-rose-500',
            done: 'border-l-emerald-500',
            cancelled: 'border-l-stone-400',
        }[status] ?? 'border-l-border'
    )
}

function getSubTaskDotClass(status: string) {
    return (
        {
            pending: 'bg-slate-400',
            assigned: 'bg-indigo-500',
            in_progress: 'bg-sky-500 animate-pulse',
            review: 'bg-amber-500 animate-pulse',
            rework: 'bg-orange-500 animate-pulse',
            blocked: 'bg-rose-500',
            done: 'bg-emerald-500',
            cancelled: 'bg-stone-400',
        }[status] ?? 'bg-muted-foreground'
    )
}

function getPriorityBadgeClass(priority: string) {
    return (
        {
            high: 'border-rose-200 bg-rose-50 text-rose-700',
            medium: 'border-amber-200 bg-amber-50 text-amber-700',
            low: 'border-slate-300 bg-slate-100 text-slate-700',
        }[priority] ?? 'border-border bg-muted text-muted-foreground'
    )
}



async function loadTasks() {
    const requestId = ++taskListRequestId
    loadingTasks.value = true
    taskListError.value = ''

    try {
        const response = await adminTaskApi.list({
            page: taskPage.value,
            page_size: TASK_PAGE_SIZE,
            keyword: taskKeyword.value.trim() || undefined,
            status: taskStatus.value === 'all' ? undefined : taskStatus.value,
            type: taskType.value === 'all' ? undefined : taskType.value,
            sort_by: 'updated_at',
            sort_order: 'desc',
        })

        if (requestId !== taskListRequestId) {
            return
        }

        taskPageData.value = response.data

        if (!response.data.items.length) {
            clearSelectedTaskState()
            return
        }

        const firstTask = response.data.items[0]
        if (!firstTask) {
            clearSelectedTaskState()
            return
        }

        const currentIds = new Set(response.data.items.map((item) => item.id))
        const nextTaskId =
            selectedTaskId.value && currentIds.has(selectedTaskId.value)
                ? selectedTaskId.value
                : firstTask.id

        const prevTaskId = selectedTaskId.value
        selectedTaskId.value = nextTaskId
        if (nextTaskId !== prevTaskId || !selectedTask.value) {
            void loadSelectedTaskContext(nextTaskId)
        }
    } catch (error) {
        if (requestId !== taskListRequestId) {
            return
        }

        console.error('Failed to load admin tasks', error)
        taskListError.value = '任务列表加载失败，请稍后再试。'
        taskPageData.value = createEmptyPage<AdminTaskItem>()
        clearSelectedTaskState()
    } finally {
        if (requestId === taskListRequestId) {
            loadingTasks.value = false
        }
    }
}

async function loadSelectedTaskContext(taskId: string) {
    const requestId = ++taskContextRequestId
    loadingDetail.value = true
    detailError.value = ''
    subTaskListError.value = ''

    try {
        const [taskResponse, moduleResponse, subTaskResponse] = await Promise.all([
            adminTaskApi.get(taskId),
            adminTaskApi.listModules(taskId, {
                page: 1,
                page_size: 24,
                sort_by: 'created_at',
                sort_order: 'asc',
            }),
            adminTaskApi.listSubTasks(taskId, {
                page: 1,
                page_size: SUB_TASK_PAGE_SIZE,
                status: subTaskStatus.value === 'all' ? undefined : subTaskStatus.value,
                sort_by: 'updated_at',
                sort_order: 'desc',
            }),
        ])

        if (requestId !== taskContextRequestId || selectedTaskId.value !== taskId) {
            return
        }

        selectedTask.value = taskResponse.data
        modulePageData.value = moduleResponse.data
        subTaskPageData.value = subTaskResponse.data
        subTaskPage.value = 1
        detailKey.value++
    } catch (error) {
        if (requestId !== taskContextRequestId) {
            return
        }

        console.error('Failed to load selected task context', error)
        detailError.value = '任务详情加载失败，请重新刷新。'
        selectedTask.value = null
        modulePageData.value = createEmptyPage<AdminModuleItem>()
        subTaskPageData.value = createEmptyPage<AdminSubTaskItem>()
    } finally {
        if (requestId === taskContextRequestId) {
            loadingDetail.value = false
        }
    }
}

async function loadSelectedTaskSubTasks(taskId: string) {
    const requestId = ++subTaskListRequestId
    loadingSubTasks.value = true
    subTaskListError.value = ''

    try {
        const [response] = await Promise.all([
            adminTaskApi.listSubTasks(taskId, {
                page: subTaskPage.value,
                page_size: SUB_TASK_PAGE_SIZE,
                status: subTaskStatus.value === 'all' ? undefined : subTaskStatus.value,
                sort_by: 'updated_at',
                sort_order: 'desc',
            }),
            minDelay(),
        ])

        if (requestId !== subTaskListRequestId || selectedTaskId.value !== taskId) {
            return
        }

        subTaskPageData.value = response.data
    } catch (error) {
        if (requestId !== subTaskListRequestId) {
            return
        }

        console.error('Failed to load task sub tasks', error)
        subTaskListError.value = '子任务列表加载失败，请稍后重试。'
        subTaskPageData.value = createEmptyPage<AdminSubTaskItem>()
    } finally {
        if (requestId === subTaskListRequestId) {
            loadingSubTasks.value = false
        }
    }
}

async function selectTask(taskId: string) {
    if (selectedTaskId.value === taskId) {
        if (isCompactLayout.value) {
            await scrollDetailIntoView()
        }
        return
    }

    selectedModuleId.value = null
    selectedTaskId.value = taskId
    subTaskPage.value = 1
    void loadSelectedTaskContext(taskId)

    if (isCompactLayout.value) {
        await scrollDetailIntoView()
    }
}

async function scrollDetailIntoView() {
    await nextTick()
    detailAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function goToTaskPage(page: number) {
    if (page < 1 || page > taskPageData.value.total_pages || page === taskPage.value) {
        return
    }
    taskPage.value = page
    void loadTasks()
}

function goToSubTaskPage(page: number) {
    if (page < 1 || page > subTaskPageData.value.total_pages || page === subTaskPage.value) {
        return
    }
    subTaskPage.value = page
    if (selectedTaskId.value) {
        void loadSelectedTaskSubTasks(selectedTaskId.value)
    }
}

function refreshCurrentView() {
    void loadTasks()
}

// 编辑任务相关函数
function openEditTaskDialog() {
    if (!selectedTask.value) return
    editTaskName.value = selectedTask.value.name
    editTaskDescription.value = selectedTask.value.description ?? ''
    editTaskError.value = ''
    showEditTaskDialog.value = true
}

async function handleSaveEditTask() {
    if (!selectedTaskId.value) return
    const name = editTaskName.value.trim()
    if (!name) {
        editTaskError.value = '任务名称不能为空'
        return
    }
    // 检查任务状态
    if (selectedTask.value && selectedTask.value.status !== 'planning' && selectedTask.value.status !== 'active') {
        editTaskError.value = '仅 planning/active 状态的任务可编辑'
        return
    }
    savingEditTask.value = true
    editTaskError.value = ''
    try {
        await taskApi.update(selectedTaskId.value, {
            name,
            description: editTaskDescription.value.trim(),
        })
        showEditTaskDialog.value = false
        // 刷新任务详情
        await loadSelectedTaskContext(selectedTaskId.value)
        // 刷新任务列表
        void loadTasks()
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        editTaskError.value = msg ?? '保存失败，请重试'
    } finally {
        savingEditTask.value = false
    }
}

// 编辑子任务相关函数
async function openEditSubTaskDialog() {
    if (!selectedSubTask.value) return
    editSubTaskName.value = selectedSubTask.value.name
    editSubTaskDescription.value = selectedSubTask.value.description ?? ''
    editSubTaskDeliverable.value = selectedSubTask.value.deliverable ?? ''
    editSubTaskAcceptance.value = selectedSubTask.value.acceptance ?? ''
    editSubTaskPriority.value = selectedSubTask.value.priority ?? ''
    editSubTaskType.value = selectedSubTask.value.type ?? ''
    editSubTaskRemarks.value = selectedSubTask.value.remarks ?? ''
    editSubTaskStatus.value = selectedSubTask.value.status ?? ''
    editSubTaskAssignedAgent.value = selectedSubTask.value.assigned_agent ?? ''
    // recurring_config 是 JSON，转换为字符串方便编辑
    const rc = selectedSubTask.value.recurring_config
    editSubTaskRecurringConfig.value = rc ? JSON.stringify(rc, null, 2) : ''
    editSubTaskError.value = ''
    // 根据 team_id 加载团队 agent
    if (selectedSubTask.value.team_id) {
        await loadTeamAgents(selectedSubTask.value.team_id)
    } else {
        editTeamAgents.value = availableAgents.value
    }
    showEditSubTaskDialog.value = true
}

async function handleSaveEditSubTask() {
    if (!selectedSubTask.value) return
    const name = editSubTaskName.value.trim()
    if (!name) {
        editSubTaskError.value = '子任务名称不能为空'
        return
    }
    // 检查子任务状态
    const status = selectedSubTask.value.status
    if (status !== 'pending' && status !== 'assigned') {
        editSubTaskError.value = '仅 pending/assigned 状态的子任务可编辑'
        return
    }
    savingEditSubTask.value = true
    editSubTaskError.value = ''
    try {
        // 处理 recurring_config - 解析 JSON 字符串
        let recurringConfig: object | undefined = undefined
        const rcStr = editSubTaskRecurringConfig.value.trim()
        if (rcStr) {
            try {
                recurringConfig = JSON.parse(rcStr)
            } catch {
                editSubTaskError.value = '循环配置格式无效，请输入有效的 JSON'
                savingEditSubTask.value = false
                return
            }
        }

        await subTaskApi.update(selectedSubTask.value.id, {
            name,
            description: editSubTaskDescription.value.trim(),
            deliverable: editSubTaskDeliverable.value.trim(),
            acceptance: editSubTaskAcceptance.value.trim(),
            priority: editSubTaskPriority.value || undefined,
            type: editSubTaskType.value || undefined,
            remarks: editSubTaskRemarks.value || undefined,
            status: editSubTaskStatus.value || undefined,
            assigned_agent: editSubTaskAssignedAgent.value || undefined,
            recurring_config: recurringConfig,
        })
        showEditSubTaskDialog.value = false
        // 刷新子任务详情
        await openSubTaskDetail(selectedSubTask.value.id)
    } catch (err: unknown) {
        const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        editSubTaskError.value = msg ?? '保存失败，请重试'
    } finally {
        savingEditSubTask.value = false
    }
}

async function openSubTaskDetail(subTaskId: string) {
    const requestId = ++subTaskDetailRequestId
    subTaskSheetOpen.value = true
    subTaskDetailLoading.value = true
    subTaskDetailError.value = ''
    selectedSubTask.value = null

    try {
        const response = await adminTaskApi.getSubTask(subTaskId)

        if (requestId !== subTaskDetailRequestId) {
            return
        }

        selectedSubTask.value = response.data
    } catch (error) {
        if (requestId !== subTaskDetailRequestId) {
            return
        }

        console.error('Failed to load sub task detail', error)
        subTaskDetailError.value = '子任务详情加载失败，请稍后重试。'
    } finally {
        if (requestId === subTaskDetailRequestId) {
            subTaskDetailLoading.value = false
        }
    }
}
</script>

<template>
    <TooltipProvider>
        <div class="flex flex-col h-[calc(100vh-3.5rem)]">
            <!-- ─── 顶栏：搜索 + 筛选 + 刷新 ─── -->
            <header class="shrink-0 border-b border-border/40 bg-background px-4 py-3 space-y-2.5">
                <div class="flex items-center gap-3">
                    <div class="relative flex-1 max-w-md">
                        <Search
                            class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                        <Input v-model="taskKeyword" class="h-9 bg-muted/30 pl-10 text-sm" placeholder="搜索任务名或说明…" />
                    </div>
                    <Badge variant="secondary" class="h-7 px-2.5 text-xs tabular-nums shrink-0">
                        {{ taskPageData.total }} 个任务
                    </Badge>
                    <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0"
                        :disabled="loadingTasks || loadingDetail" @click="refreshCurrentView">
                        <RefreshCw class="h-3.5 w-3.5" :class="loadingTasks || loadingDetail ? 'animate-spin' : ''" />
                    </Button>
                </div>

                <div class="flex items-center gap-4">
                    <div class="flex flex-wrap gap-1.5">
                        <Button v-for="option in taskStatusOptions" :key="option.value" size="sm"
                            :variant="taskStatus === option.value ? 'default' : 'ghost'"
                            class="h-7 rounded-full px-3 text-xs" @click="taskStatus = option.value">
                            {{ option.label }}
                        </Button>
                    </div>
                    <Separator orientation="vertical" class="h-4 opacity-30" />
                    <div class="flex gap-1.5">
                        <Button v-for="option in taskTypeOptions" :key="option.value" size="sm"
                            :variant="taskType === option.value ? 'secondary' : 'ghost'"
                            class="h-7 rounded-full px-3 text-xs" @click="taskType = option.value">
                            {{ option.label }}
                        </Button>
                    </div>
                </div>
            </header>

            <!-- ─── 主体：左列表 + 右详情 ─── -->
            <div class="flex flex-1 min-h-0">
                <!-- 任务列表 -->
                <div class="w-full lg:w-[380px] xl:w-[420px] shrink-0 border-r border-border/40 overflow-y-auto">
                    <!-- 错误 -->
                    <div v-if="taskListError" class="p-6 text-center">
                        <AlertCircle class="mx-auto h-5 w-5 text-muted-foreground" />
                        <p class="mt-2 text-sm">{{ taskListError }}</p>
                        <Button class="mt-3" size="sm" @click="refreshCurrentView"> 重新加载 </Button>
                    </div>

                    <!-- 加载中 -->
                    <div v-else-if="loadingTasks" class="flex items-center justify-center py-16">
                        <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>

                    <!-- 任务卡片列表 -->
                    <template v-else-if="taskPageData.items.length">
                        <div :key="`tasks-${taskPage}-${taskStatus}-${taskType}-${taskKeyword}`"
                            class="divide-y divide-border/30">
                            <button v-for="(task, idx) in taskPageData.items" :key="task.id" type="button"
                                class="w-full px-4 py-3 text-left transition-all duration-150 hover:bg-muted/30 animate-slide-up"
                                :class="selectedTaskId === task.id ? 'bg-accent/60 border-l-[3px] border-l-primary' : 'border-l-[3px] border-l-transparent'"
                                :style="{ animationDelay: `${idx * 40}ms` }" @click="selectTask(task.id)">
                                <div class="flex items-start justify-between gap-2">
                                    <div class="min-w-0 flex-1">
                                        <TextOverflowTooltip :text="task.name" as="div"
                                            class="text-sm font-semibold leading-5" />
                                        <TextOverflowTooltip :text="task.description || '暂无说明'" as="p" :lines="1"
                                            class="mt-0.5 text-xs text-muted-foreground leading-4" />
                                    </div>
                                    <Badge variant="outline" :class="getTaskBadgeClass(task.status)"
                                        class="shrink-0 text-[10px] px-1.5">
                                        {{ formatTaskStatus(task.status) }}
                                    </Badge>
                                </div>

                                <div class="mt-2 flex items-center gap-3 text-[11px] text-muted-foreground">
                                    <span class="tabular-nums">{{ task.module_count }} 模块 · {{ task.sub_task_count }}
                                        子任务</span>
                                    <div class="flex-1 flex items-center gap-1.5">
                                        <div class="flex-1 h-1.5 rounded-full bg-muted max-w-[80px]">
                                            <div class="h-1.5 rounded-full bg-emerald-500 transition-all" :style="{
                                                width: `${getCompletionRatio(task.done_count, task.sub_task_count)}%`,
                                            }" />
                                        </div>
                                        <span class="tabular-nums">{{ getCompletionRatio(task.done_count,
                                            task.sub_task_count) }}%</span>
                                    </div>
                                    <span class="tabular-nums">{{ formatDate(task.updated_at) }}</span>
                                </div>
                            </button>
                        </div>

                        <!-- 分页 -->
                        <div v-if="taskPageData.total_pages > 1"
                            class="flex items-center justify-center gap-2 py-3 border-t border-border/30 text-xs text-muted-foreground">
                            <Button variant="ghost" size="icon" class="h-7 w-7"
                                :disabled="taskPageData.page <= 1 || loadingTasks"
                                @click="goToTaskPage(taskPageData.page - 1)">
                                <ArrowLeft class="h-3 w-3" />
                            </Button>
                            <span class="tabular-nums">{{ taskPageData.page }} / {{ taskPageData.total_pages }}</span>
                            <Button variant="ghost" size="icon" class="h-7 w-7"
                                :disabled="taskPageData.page >= taskPageData.total_pages || loadingTasks"
                                @click="goToTaskPage(taskPageData.page + 1)">
                                <ArrowRight class="h-3 w-3" />
                            </Button>
                        </div>
                    </template>

                    <!-- 空状态 -->
                    <div v-else class="flex flex-col items-center justify-center py-16 text-muted-foreground/50">
                        <ListTodo class="h-6 w-6 mb-2" />
                        <p class="text-sm">没有找到匹配任务</p>
                    </div>
                </div>

                <!-- ─── 右侧详情 ─── -->
                <div ref="detailAnchor" class="hidden lg:flex flex-col flex-1 min-h-0 overflow-y-auto">
                    <!-- 加载中 -->
                    <div v-if="loadingDetail" class="flex items-center justify-center flex-1">
                        <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>

                    <!-- 错误 -->
                    <div v-else-if="detailError"
                        class="flex flex-col items-center justify-center flex-1 text-muted-foreground/50">
                        <AlertCircle class="h-5 w-5 mb-2" />
                        <p class="text-sm">{{ detailError }}</p>
                        <Button v-if="selectedTaskId" class="mt-3" size="sm"
                            @click="loadSelectedTaskContext(selectedTaskId)">重试</Button>
                    </div>

                    <!-- 任务详情 -->
                    <div v-else-if="selectedTask" :key="detailKey" class="p-6 space-y-6 animate-slide-up">
                        <!-- 任务头 -->
                        <div>
                            <div class="flex items-start justify-between gap-3">
                                <div class="min-w-0 space-y-1">
                                    <TextOverflowTooltip :text="selectedTask.name" as="h2"
                                        class="text-lg font-semibold leading-7" />
                                    <TextOverflowTooltip :text="selectedTask.description || '暂无任务说明。'" as="p" :lines="2"
                                        class="text-sm text-muted-foreground leading-5" />
                                </div>
                                <div class="flex gap-1.5 shrink-0">
                                    <Button variant="ghost" size="icon" class="h-7 w-7"
                                        @click.stop="openEditTaskDialog">
                                        <Pencil class="h-3.5 w-3.5" />
                                    </Button>
                                    <Badge variant="outline" :class="getTaskBadgeClass(selectedTask.status)">
                                        {{ formatTaskStatus(selectedTask.status) }}
                                    </Badge>
                                    <Badge variant="secondary">
                                        {{ formatTaskType(selectedTask.type) }}
                                    </Badge>
                                </div>
                            </div>

                            <!-- 进度条 + 统计数字 -->
                            <div class="mt-4 rounded-xl border border-border/50 bg-muted/20 p-3.5 space-y-3">
                                <div class="flex items-center justify-between text-xs">
                                    <span class="text-muted-foreground">完成进度</span>
                                    <span class="font-semibold tabular-nums">{{ selectedTaskProgress }}%</span>
                                </div>
                                <div class="h-2 rounded-full bg-muted">
                                    <div class="h-2 rounded-full bg-emerald-500 transition-all"
                                        :style="{ width: `${selectedTaskProgress}%` }" />
                                </div>
                                <div class="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground tabular-nums">
                                    <span>子任务
                                        <span class="font-medium text-foreground">{{
                                            selectedTask.sub_task_count
                                        }}</span></span>
                                    <span>已完成
                                        <span class="font-medium text-foreground">{{
                                            selectedTask.done_count
                                        }}</span></span>
                                    <span>执行中
                                        <span class="font-medium text-foreground">{{
                                            selectedTask.in_progress_count
                                        }}</span></span>
                                    <span>待审查
                                        <span class="font-medium text-foreground">{{
                                            selectedTask.review_count
                                        }}</span></span>
                                    <span>待分配
                                        <span class="font-medium text-foreground">{{
                                            selectedTask.pending_count
                                        }}</span></span>
                                    <span v-if="selectedTask.blocked_count">阻塞
                                        <span class="font-medium text-rose-500">{{
                                            selectedTask.blocked_count
                                        }}</span></span>
                                    <span v-if="selectedTask.rework_count">返工
                                        <span class="font-medium text-amber-500">{{
                                            selectedTask.rework_count
                                        }}</span></span>
                                </div>
                                <div class="flex gap-4 text-[11px] text-muted-foreground/60">
                                    <span>创建于 {{ formatDate(selectedTask.created_at) }}</span>
                                    <span>更新于 {{ formatDate(selectedTask.updated_at) }}</span>
                                </div>
                            </div>
                        </div>

                        <!-- 模块拆分 -->
                        <div v-if="modulePageData.items.length">
                            <div class="flex items-center justify-between mb-2">
                                <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
                                    模块拆分 · {{ modulePageData.items.length }}
                                </div>
                                <button v-if="selectedModuleId" class="text-[10px] text-primary hover:underline"
                                    @click="selectedModuleId = null">
                                    清除筛选
                                </button>
                            </div>
                            <div class="space-y-2">
                                <button v-for="(module, idx) in modulePageData.items" :key="module.id" type="button"
                                    class="w-full rounded-lg border p-3 text-left transition-all animate-slide-up"
                                    :class="selectedModuleId === module.id
                                        ? 'border-primary/50 ring-1 ring-primary/20 bg-accent/30'
                                        : 'border-border/50 hover:border-border hover:bg-muted/20'"
                                    :style="{ animationDelay: `${idx * 40}ms` }" @click="toggleModule(module.id)">
                                    <div class="flex items-center justify-between gap-2">
                                        <TextOverflowTooltip :text="module.name" as="div" class="text-sm font-medium" />
                                        <div
                                            class="flex items-center gap-1.5 text-xs text-muted-foreground tabular-nums shrink-0">
                                            <span>{{ module.done_count }}/{{ module.sub_task_count }}</span>
                                            <div class="w-12 h-1.5 rounded-full bg-muted">
                                                <div class="h-1.5 rounded-full bg-sky-500" :style="{
                                                    width: `${getCompletionRatio(module.done_count, module.sub_task_count)}%`,
                                                }" />
                                            </div>
                                        </div>
                                    </div>
                                    <TextOverflowTooltip v-if="module.description" :text="module.description" as="p"
                                        :lines="1" class="mt-1 text-xs text-muted-foreground leading-4" />
                                </button>
                            </div>
                        </div>

                        <!-- 子任务列表 -->
                        <div>
                            <div class="flex items-center justify-between mb-2">
                                <div class="text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">
                                    子任务 · {{ subTaskPageData.total }}
                                </div>
                                <div class="flex items-center gap-2 text-xs text-muted-foreground">
                                    <span class="tabular-nums">{{ subTaskPageData.page }} / {{
                                        subTaskPageData.total_pages }}</span>
                                    <Button variant="ghost" size="icon" class="h-6 w-6"
                                        :disabled="subTaskPageData.page <= 1 || loadingSubTasks"
                                        @click="goToSubTaskPage(subTaskPageData.page - 1)">
                                        <ArrowLeft class="h-3 w-3" />
                                    </Button>
                                    <Button variant="ghost" size="icon" class="h-6 w-6" :disabled="subTaskPageData.page >= subTaskPageData.total_pages || loadingSubTasks
                                        " @click="goToSubTaskPage(subTaskPageData.page + 1)">
                                        <ArrowRight class="h-3 w-3" />
                                    </Button>
                                </div>
                            </div>

                            <!-- 子任务状态筛选 -->
                            <div class="flex flex-wrap gap-1.5 mb-3">
                                <Button v-for="option in subTaskStatusOptions" :key="option.value" size="sm"
                                    :variant="subTaskStatus === option.value ? 'default' : 'ghost'"
                                    class="h-6 rounded-full px-2.5 text-[11px]" @click="subTaskStatus = option.value">
                                    {{ option.label }}
                                </Button>
                            </div>

                            <!-- 子任务加载中 -->
                            <div v-if="loadingSubTasks" class="flex items-center justify-center py-10">
                                <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
                            </div>

                            <!-- 子任务错误 -->
                            <div v-else-if="subTaskListError" class="text-center py-6">
                                <p class="text-sm text-muted-foreground">{{ subTaskListError }}</p>
                                <Button v-if="selectedTaskId" class="mt-2" size="sm"
                                    @click="loadSelectedTaskSubTasks(selectedTaskId)">重试</Button>
                            </div>

                            <!-- 子任务列表 -->
                            <div v-else-if="subTaskPageData.items.length" :key="`st-${subTaskPage}-${subTaskStatus}`"
                                class="space-y-1.5">
                                <template v-for="(item, idx) in subTaskPageData.items" :key="item.id">
                                    <button
                                        v-if="!selectedModuleId || item.module_name === modulePageData.items.find(m => m.id === selectedModuleId)?.name"
                                        type="button"
                                        class="w-full rounded-lg border border-border/40 p-3 text-left transition-colors hover:bg-muted/30 animate-slide-up border-l-[3px]"
                                        :class="getSubTaskLeftBorderClass(item.status)"
                                        :style="{ animationDelay: `${idx * 40}ms` }"
                                        @click="openSubTaskDetail(item.id)">
                                        <div class="flex items-start justify-between gap-2">
                                            <div class="min-w-0 flex-1">
                                                <div class="flex items-center gap-1.5">
                                                    <span class="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                                                        :class="getSubTaskDotClass(item.status)" />
                                                    <TextOverflowTooltip :text="item.name" as="div"
                                                        class="text-sm font-medium leading-5" />
                                                </div>
                                                <TextOverflowTooltip :text="item.description || '暂无说明'" as="p"
                                                    :lines="1"
                                                    class="mt-0.5 text-xs text-muted-foreground leading-4 pl-3" />
                                            </div>
                                            <Badge variant="outline" :class="getSubTaskBadgeClass(item.status)"
                                                class="shrink-0 text-[10px] px-1.5">
                                                {{ formatSubTaskStatus(item.status) }}
                                            </Badge>
                                        </div>
                                        <div
                                            class="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground pl-3">
                                            <Badge variant="outline" :class="getPriorityBadgeClass(item.priority)"
                                                class="text-[10px] px-1.5 h-5">
                                                {{ formatPriority(item.priority) }}
                                            </Badge>
                                            <Badge variant="secondary" class="text-[10px] px-1.5 h-5">
                                                {{ formatTaskType(item.type) }}
                                            </Badge>
                                            <span>{{ item.module_name || '未绑定模块' }}</span>
                                            <span v-if="item.assigned_agent_name">· {{ item.assigned_agent_name
                                            }}</span>
                                            <span v-if="item.current_session_id" class="text-primary/60">Session: {{
                                                item.current_session_id.slice(0, 8) }}…</span>
                                            <span v-if="item.rework_count > 0" class="text-amber-500">返工 {{
                                                item.rework_count }}</span>
                                            <span class="ml-auto tabular-nums">{{ formatDate(item.updated_at)
                                            }}</span>
                                        </div>
                                    </button>
                                </template>
                            </div>

                            <!-- 子任务空状态 -->
                            <div v-else class="flex flex-col items-center justify-center py-8 text-muted-foreground/40">
                                <p class="text-xs">当前条件下没有子任务</p>
                            </div>
                        </div>
                    </div>

                    <!-- 未选择任务 -->
                    <div v-if="!loadingDetail && !detailError && !selectedTask"
                        class="flex flex-col items-center justify-center flex-1 text-muted-foreground/40">
                        <FolderKanban class="h-8 w-8 mb-3" />
                        <p class="text-sm font-medium text-muted-foreground/60">点击左侧任务查看详情</p>
                        <p class="text-xs mt-1">模块拆分和子任务会在这里展示</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- ─── 子任务详情抽屉 ─── -->
        <Sheet v-model:open="subTaskSheetOpen">
            <SheetContent side="right" class="w-full sm:max-w-xl p-0">
                <SheetHeader class="shrink-0 px-6 pt-6 pb-4 border-b border-border/30">
                    <SheetTitle class="pr-8">子任务详情</SheetTitle>
                    <SheetDescription>查看交付要求、验收标准和执行上下文。</SheetDescription>
                </SheetHeader>

                <div class="flex-1 overflow-y-auto px-6 py-5 space-y-5">
                    <div v-if="subTaskDetailLoading" class="flex items-center justify-center py-12">
                        <Loader2 class="h-5 w-5 animate-spin text-muted-foreground" />
                    </div>

                    <div v-else-if="subTaskDetailError"
                        class="rounded-xl border border-dashed border-border bg-muted/20 p-5 text-center">
                        <p class="text-sm font-medium">加载失败</p>
                        <p class="mt-1 text-xs text-muted-foreground">{{ subTaskDetailError }}</p>
                    </div>

                    <template v-else-if="selectedSubTask">
                        <div class="space-y-4">
                            <!-- 标签 -->
                            <div class="flex flex-wrap gap-1.5">
                                <Button variant="ghost" size="icon" class="h-7 w-7"
                                    @click.stop="openEditSubTaskDialog">
                                    <Pencil class="h-3.5 w-3.5" />
                                </Button>
                                <Badge variant="outline" :class="getSubTaskBadgeClass(selectedSubTask.status)">
                                    {{ formatSubTaskStatus(selectedSubTask.status) }}
                                </Badge>
                                <Badge variant="outline" :class="getPriorityBadgeClass(selectedSubTask.priority)">
                                    {{ formatPriority(selectedSubTask.priority) }}
                                </Badge>
                                <Badge variant="secondary">
                                    {{ formatTaskType(selectedSubTask.type) }}
                                </Badge>
                            </div>

                            <!-- 名称+描述 -->
                            <div>
                                <h3 class="text-lg font-semibold leading-7">{{ selectedSubTask.name }}</h3>
                                <p class="mt-1.5 text-sm leading-6 text-muted-foreground whitespace-pre-wrap">
                                    {{ selectedSubTask.description || '暂无子任务说明。' }}
                                </p>
                            </div>

                            <!-- 上下文 -->
                            <div class="grid gap-3 sm:grid-cols-2">
                                <div class="rounded-xl border border-border/50 bg-muted/20 p-3.5">
                                    <div class="text-[11px] text-muted-foreground/60 uppercase tracking-wider">
                                        所属
                                    </div>
                                    <div class="mt-1.5 text-sm font-medium leading-5">
                                        {{ selectedSubTask.task_name }}
                                    </div>
                                    <div class="mt-0.5 text-xs text-muted-foreground">
                                        {{ selectedSubTask.module_name || '未绑定模块' }}
                                    </div>
                                </div>
                                <div class="rounded-xl border border-border/50 bg-muted/20 p-3.5">
                                    <div class="text-[11px] text-muted-foreground/60 uppercase tracking-wider">
                                        执行者
                                    </div>
                                    <div class="mt-1.5 text-sm font-medium">
                                        {{ selectedSubTask.assigned_agent_name || '未分配' }}
                                    </div>
                                    <div class="mt-0.5 text-xs text-muted-foreground truncate">
                                        Session: {{ selectedSubTask.current_session_id || '未建立' }}
                                    </div>
                                </div>
                            </div>

                            <!-- 交付物 -->
                            <div class="rounded-xl border border-border/50 p-3.5">
                                <div class="text-[11px] text-muted-foreground/60 uppercase tracking-wider">
                                    交付物要求
                                </div>
                                <p class="mt-2 whitespace-pre-wrap text-sm leading-6">
                                    {{ selectedSubTask.deliverable || '暂无交付物要求。' }}
                                </p>
                            </div>

                            <!-- 验收标准 -->
                            <div class="rounded-xl border border-border/50 p-3.5">
                                <div class="text-[11px] text-muted-foreground/60 uppercase tracking-wider">
                                    验收标准
                                </div>
                                <p class="mt-2 whitespace-pre-wrap text-sm leading-6">
                                    {{ selectedSubTask.acceptance || '暂无验收标准。' }}
                                </p>
                            </div>

                            <Separator />

                            <!-- 元数据 -->
                            <div class="flex gap-4 text-xs text-muted-foreground">
                                <span>返工 <span class="font-medium text-foreground">{{ selectedSubTask.rework_count
                                        }}</span></span>
                                <span>更新于 {{ formatDate(selectedSubTask.updated_at) }}</span>
                            </div>
                        </div>
                    </template>
                </div>
            </SheetContent>
        </Sheet>

        <!-- 编辑任务弹窗 -->
        <div v-if="showEditTaskDialog" class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditTaskDialog = false" />
            <div
                class="relative z-10 w-full max-w-md rounded-xl border bg-background p-6 shadow-lg animate-in fade-in zoom-in-95 duration-200">
                <div class="flex flex-col gap-1.5">
                    <h3 class="text-lg font-semibold">编辑任务</h3>
                    <p class="text-sm text-muted-foreground">仅 planning/active 状态的任务可编辑</p>
                </div>

                <div class="mt-5 space-y-4">
                    <div class="space-y-2">
                        <Label for="edit-task-name">任务名称</Label>
                        <Input id="edit-task-name" v-model="editTaskName" placeholder="请输入任务名称"
                            :disabled="savingEditTask" />
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-task-desc">任务描述</Label>
                        <textarea id="edit-task-desc" v-model="editTaskDescription"
                            class="flex min-h-[100px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder="请输入任务描述（可选）" :disabled="savingEditTask" />
                    </div>
                    <div v-if="editTaskError" class="text-sm text-red-500">
                        {{ editTaskError }}
                    </div>
                </div>

                <div class="mt-6 flex justify-end gap-2.5">
                    <Button variant="outline" @click="showEditTaskDialog = false" :disabled="savingEditTask">
                        取消
                    </Button>
                    <Button @click="handleSaveEditTask" :disabled="savingEditTask">
                        <Loader2 v-if="savingEditTask" class="mr-2 h-4 w-4 animate-spin" />
                        {{ savingEditTask ? '保存中...' : '保存' }}
                    </Button>
                </div>
            </div>
        </div>

        <!-- 编辑子任务弹窗 -->
        <div v-if="showEditSubTaskDialog" class="fixed inset-0 z-50 flex items-center justify-center">
            <div class="absolute inset-0 bg-black/50 backdrop-blur-sm" @click="showEditSubTaskDialog = false" />
            <div
                class="relative z-10 w-full max-w-lg rounded-xl border bg-background p-6 shadow-lg animate-in fade-in zoom-in-95 duration-200 max-h-[90vh] overflow-y-auto">
                <div class="flex flex-col gap-1.5">
                    <h3 class="text-lg font-semibold">编辑子任务</h3>
                    <p class="text-sm text-muted-foreground">仅 pending/assigned 状态的子任务可编辑</p>
                </div>

                <div class="mt-5 space-y-4">
                    <div class="space-y-2">
                        <Label for="edit-subtask-name">子任务名称</Label>
                        <Input id="edit-subtask-name" v-model="editSubTaskName" placeholder="请输入子任务名称"
                            :disabled="savingEditSubTask" />
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-desc">任务描述</Label>
                        <textarea id="edit-subtask-desc" v-model="editSubTaskDescription"
                            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder="请输入任务描述（可选）" :disabled="savingEditSubTask" />
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-deliverable">交付物要求</Label>
                        <textarea id="edit-subtask-deliverable" v-model="editSubTaskDeliverable"
                            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder="请输入交付物要求（可选）" :disabled="savingEditSubTask" />
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-acceptance">验收标准</Label>
                        <textarea id="edit-subtask-acceptance" v-model="editSubTaskAcceptance"
                            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder="请输入验收标准（可选）" :disabled="savingEditSubTask" />
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-type">类型</Label>
                        <select id="edit-subtask-type" v-model="editSubTaskType"
                            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                            <option value="">请选择类型</option>
                            <option value="once">一次性 (once)</option>
                            <option value="recurring">循环 (recurring)</option>
                        </select>
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-remarks">备注</Label>
                        <textarea id="edit-subtask-remarks" v-model="editSubTaskRemarks"
                            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder="请输入备注（可选）" :disabled="savingEditSubTask" />
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-status">状态</Label>
                        <select id="edit-subtask-status" v-model="editSubTaskStatus"
                            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                            <option value="">请选择状态</option>
                            <option value="pending">待处理 (pending)</option>
                            <option value="assigned">已指派 (assigned)</option>
                            <option value="in_progress">执行中 (in_progress)</option>
                            <option value="review">待审查 (review)</option>
                            <option value="rework">返工中 (rework)</option>
                            <option value="blocked">阻塞 (blocked)</option>
                            <option value="done">已完成 (done)</option>
                            <option value="cancelled">已取消 (cancelled)</option>
                        </select>
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-agent">指派 Agent</Label>
                        <select id="edit-subtask-agent" v-model="editSubTaskAssignedAgent"
                            class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
                            <option value="">不指派</option>
                            <option v-for="agent in editTeamAgents" :key="agent.id" :value="agent.id">
                                {{ agent.name }} ({{ agent.role }})
                            </option>
                        </select>
                    </div>
                    <div class="space-y-2">
                        <Label for="edit-subtask-recurring">循环配置 (JSON)</Label>
                        <textarea id="edit-subtask-recurring" v-model="editSubTaskRecurringConfig"
                            class="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                            placeholder='{"cron": "0 9 * * *", "enabled": true}' :disabled="savingEditSubTask" />
                    </div>
                    <div v-if="editSubTaskError" class="text-sm text-red-500">
                        {{ editSubTaskError }}
                    </div>
                </div>

                <div class="mt-6 flex justify-end gap-2.5">
                    <Button variant="outline" @click="showEditSubTaskDialog = false" :disabled="savingEditSubTask">
                        取消
                    </Button>
                    <Button @click="handleSaveEditSubTask" :disabled="savingEditSubTask">
                        <Loader2 v-if="savingEditSubTask" class="mr-2 h-4 w-4 animate-spin" />
                        {{ savingEditSubTask ? '保存中...' : '保存' }}
                    </Button>
                </div>
            </div>
        </div>
    </TooltipProvider>
</template>

