# 子任务人工干预功能实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 OpenMOSS 管理员端增加子任务编辑和强制取消功能

**Architecture:**
- 后端：在 admin_tasks.py 添加两个新端点，在 sub_task_service.py 添加强制取消逻辑
- 前端：在 TasksView.vue 子任务详情面板中添加编辑表单和强制取消按钮

**Tech Stack:** FastAPI (Python), Vue 3 + TypeScript

---

## Chunk 1: 后端 - Schema 和 Service

### Task 1: 添加请求 Schema

**Files:**
- Modify: `app/schemas/admin_task.py` - 添加请求模型

- [ ] **Step 1: 添加 AdminSubTaskUpdateRequest**

在 `admin_task.py` 文件末尾添加:

```python
class AdminSubTaskUpdateRequest(BaseModel):
    """子任务更新请求"""
    name: Optional[str] = Field(None, description="子任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    deliverable: Optional[str] = Field(None, description="交付物")
    acceptance: Optional[str] = Field(None, description="验收标准")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")
    assigned_agent: Optional[str] = Field(None, description="指派 Agent ID")


class ForceCancelRequest(BaseModel):
    """强制取消请求"""
    reason: str = Field(..., description="取消原因")
```

- [ ] **Step 2: 提交变更**

```bash
git add app/schemas/admin_task.py
git commit -m "feat: add admin subtask update and force-cancel request schemas"
```

---

### Task 2: 添加强制取消 Service 方法

**Files:**
- Modify: `app/services/sub_task_service.py` - 添加 force_cancel_sub_task 方法

- [ ] **Step 1: 添加 force_cancel_sub_task 函数**

在 `sub_task_service.py` 文件末尾（约第 290 行后）添加:

```python
def force_cancel_sub_task(db: Session, sub_task_id: str) -> SubTask:
    """
    强制取消子任务（跳过状态机，直接改为 cancelled）
    """
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")
    if sub_task.status in ("done", "cancelled"):
        raise ValueError(f"子任务状态为 {sub_task.status}，无法取消")

    sub_task.status = "cancelled"
    sub_task.current_session_id = None
    db.commit()
    db.refresh(sub_task)
    return sub_task


def admin_update_sub_task(
    db: Session,
    sub_task_id: str,
    name: str = None,
    description: str = None,
    deliverable: str = None,
    acceptance: str = None,
    priority: str = None,
    assigned_agent: str = None,
) -> SubTask:
    """
    管理员更新子任务（支持更多状态）
    """
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")
    if sub_task.status not in ("pending", "assigned", "blocked"):
        raise ValueError(f"子任务状态为 {sub_task.status}，只有 pending/assigned/blocked 状态可编辑")

    # 验证 assigned_agent（如果提供了）
    if assigned_agent is not None:
        if assigned_agent:
            agent = db.query(Agent).filter(Agent.id == assigned_agent).first()
            if not agent:
                raise ValueError(f"Agent {assigned_agent} 不存在")
        sub_task.assigned_agent = assigned_agent

    if name is not None:
        sub_task.name = name
    if description is not None:
        sub_task.description = description
    if deliverable is not None:
        sub_task.deliverable = deliverable
    if acceptance is not None:
        sub_task.acceptance = acceptance
    if priority is not None:
        sub_task.priority = priority

    db.commit()
    db.refresh(sub_task)
    return sub_task
```

- [ ] **Step 2: 提交变更**

```bash
git add app/services/sub_task_service.py
git commit -m "feat: add admin force-cancel and update subtask methods"
```

---

## Chunk 2: 后端 - Admin API 端点

### Task 3: 添加 Admin API 端点

**Files:**
- Modify: `app/routers/admin_tasks.py` - 添加 PUT 和 POST 端点

- [ ] **Step 1: 添加 import**

在 `admin_tasks.py` 顶部添加:

```python
from app.schemas.admin_task import (
    AdminSubTaskUpdateRequest,
    ForceCancelRequest,
)
from app.services import sub_task_service
```

- [ ] **Step 2: 添加 PUT /admin/sub-tasks/{id} 端点**

在 `admin_tasks.py` 文件末尾（约第 237 行后）添加:

```python
@router.put("/sub-tasks/{sub_task_id}", response_model=AdminSubTaskDetail, summary="管理员修改子任务")
async def admin_update_sub_task(
    sub_task_id: str,
    req: AdminSubTaskUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员修改子任务（支持 pending/assigned/blocked 状态）"""
    try:
        return sub_task_service.admin_update_sub_task(
            db,
            sub_task_id,
            name=req.name,
            description=req.description,
            deliverable=req.deliverable,
            acceptance=req.acceptance,
            priority=req.priority,
            assigned_agent=req.assigned_agent,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        _raise_admin_query_error(exc)
```

- [ ] **Step 3: 添加 POST /admin/sub-tasks/{id}/force-cancel 端点**

在同一位置添加:

```python
@router.post("/sub-tasks/{sub_task_id}/force-cancel", response_model=AdminSubTaskDetail, summary="强制取消子任务")
async def force_cancel_sub_task(
    sub_task_id: str,
    req: ForceCancelRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """强制取消子任务（跳过状态机）"""
    try:
        return sub_task_service.force_cancel_sub_task(db, sub_task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        _raise_admin_query_error(exc)
```

- [ ] **Step 4: 测试 API 端点**

启动后端并测试:
```bash
curl -X PUT http://localhost:6565/api/admin/sub-tasks/{id} \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: <token>" \
  -d '{"name": "new name", "assigned_agent": "agent-id"}'
```

- [ ] **Step 5: 提交变更**

```bash
git add app/routers/admin_tasks.py
git commit -m "feat: add admin subtask update and force-cancel endpoints"
```

---

## Chunk 3: 前端 - API Client

### Task 4: 添加前端 API 方法

**Files:**
- Modify: `webui/src/api/client.ts` - 添加 API 方法

- [ ] **Step 1: 添加 SubTaskUpdateRequest 类型**

在 `client.ts` 文件中找到 `AdminSubTaskListParams` 定义位置（约第 460 行），在其后添加:

```typescript
export interface SubTaskUpdateRequest {
  name?: string
  description?: string
  deliverable?: string
  acceptance?: string
  priority?: string
  assigned_agent?: string
}
```

- [ ] **Step 2: 在 adminTaskApi 中添加方法**

在 `adminTaskApi` 对象中 `getSubTask` 方法后添加:

```typescript
  updateSubTask: (id: string, data: SubTaskUpdateRequest) =>
    api.put<AdminSubTaskDetail>(`/admin/sub-tasks/${id}`, data),

  forceCancelSubTask: (id: string, reason: string) =>
    api.post<AdminSubTaskDetail>(`/admin/sub-tasks/${id}/force-cancel`, { reason }),
```

- [ ] **Step 3: 提交变更**

```bash
git add webui/src/api/client.ts
git commit -m "feat: add admin subtask update and force-cancel API methods"
```

---

## Chunk 4: 前端 - 任务编辑界面

### Task 5: 添加前端编辑界面

**Files:**
- Modify: `webui/src/views/TasksView.vue` - 添加编辑表单和强制取消按钮

- [ ] **Step 1: 添加状态变量**

在 `<script setup>` 中添加:

```typescript
// 编辑模式状态
const isEditingSubTask = ref(false)
const editingSubTask = ref<SubTaskUpdateRequest>({})
const cancelReason = ref('')
const showCancelDialog = ref(false)
const isSaving = ref(false)
const isCancelling = ref(false)

// Agent 列表
const agentList = ref<{id: string, name: string, role: string}[]>([])
const loadAgentList = async () => {
  const response = await agentApi.list()
  agentList.value = response.data.agents || []
}
```

- [ ] **Step 2: 添加编辑相关函数**

添加编辑相关的函数:

```typescript
function startEditSubTask() {
  if (!selectedSubTask.value) return
  editingSubTask.value = {
    name: selectedSubTask.value.name,
    description: selectedSubTask.value.description,
    deliverable: selectedSubTask.value.deliverable,
    acceptance: selectedSubTask.value.acceptance,
    priority: selectedSubTask.value.priority,
    assigned_agent: selectedSubTask.value.assigned_agent || '',
  }
  isEditingSubTask.value = true
}

function cancelEditSubTask() {
  isEditingSubTask.value = false
  editingSubTask.value = {}
}

async function saveSubTask() {
  if (!selectedSubTask.value) return
  isSaving.value = true
  try {
    const response = await adminTaskApi.updateSubTask(
      selectedSubTask.value.id,
      editingSubTask.value
    )
    selectedSubTask.value = response.data
    isEditingSubTask.value = false
  } catch (error) {
    console.error('Failed to save sub task', error)
    subTaskDetailError.value = '保存失败，请稍后重试。'
  } finally {
    isSaving.value = false
  }
}

async function confirmForceCancel() {
  if (!selectedSubTask.value || !cancelReason.value.trim()) return
  isCancelling.value = true
  try {
    const response = await adminTaskApi.forceCancelSubTask(
      selectedSubTask.value.id,
      cancelReason.value
    )
    selectedSubTask.value = response.data
    showCancelDialog.value = false
    cancelReason.value = ''
  } catch (error) {
    console.error('Failed to cancel sub task', error)
    subTaskDetailError.value = '取消失败，请稍后重试。'
  } finally {
    isCancelling.value = false
  }
}
```

- [ ] **Step 3: 在子任务详情模板中添加编辑表单**

找到子任务详情显示区域（约 L905 行），将显示模式改为可编辑表单:

```vue
<!-- 编辑模式 -->
<template v-if="isEditingSubTask">
  <div class="space-y-4">
    <div class="grid gap-2">
      <Label>名称</Label>
      <Input v-model="editingSubTask.name" />
    </div>
    <div class="grid gap-2">
      <Label>描述</Label>
      <Textarea v-model="editingSubTask.description" />
    </div>
    <div class="grid gap-2">
      <Label>交付物</Label>
      <Input v-model="editingSubTask.deliverable" />
    </div>
    <div class="grid gap-2">
      <Label>验收标准</Label>
      <Input v-model="editingSubTask.acceptance" />
    </div>
    <div class="grid gap-2">
      <Label>优先级</Label>
      <Select v-model="editingSubTask.priority">
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="high">高</SelectItem>
          <SelectItem value="medium">中</SelectItem>
          <SelectItem value="low">低</SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div class="grid gap-2">
      <Label>指派 Agent</Label>
      <Select v-model="editingSubTask.assigned_agent">
        <SelectTrigger>
          <SelectValue placeholder="选择 Agent" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">取消指派</SelectItem>
          <SelectItem v-for="agent in agentList" :key="agent.id" :value="agent.id">
            {{ agent.name }} ({{ agent.role }})
          </SelectItem>
        </SelectContent>
      </Select>
    </div>
    <div class="flex gap-2">
      <Button @click="saveSubTask" :disabled="isSaving">
        {{ isSaving ? '保存中...' : '保存' }}
      </Button>
      <Button variant="outline" @click="cancelEditSubTask">
        取消
      </Button>
    </div>
  </div>
</template>
```

- [ ] **Step 4: 添加编辑按钮**

在子任务详情面板中找到"状态显示区域"（约 L905 行的位置），在状态 badge 后面添加编辑按钮:

```vue
<div class="flex items-center gap-2" v-if="!isEditingSubTask && canEditSubTask(selectedSubTask?.status)">
  <Button variant="outline" size="sm" @click="startEditSubTask">
    编辑
  </Button>
</div>

<script>
function canEditSubTask(status: string) {
  return ['pending', 'assigned', 'blocked'].includes(status)
}
</script>
```

- [ ] **Step 5: 添加强制取消按钮和对话框**

在详情面板底部添加:

```vue
<!-- 强制取消按钮 -->
<Button
  v-if="selectedSubTask && selectedSubTask.status !== 'cancelled'"
  variant="destructive"
  class="mt-4"
  @click="showCancelDialog = true"
>
  强制取消
</Button>

<!-- 取消确认对话框 -->
<Dialog v-model:open="showCancelDialog">
  <DialogContent>
    <DialogHeader>
      <DialogTitle>强制取消子任务</DialogTitle>
      <DialogDescription>
        确定要强制取消 "{{ selectedSubTask?.name }}" 吗？此操作不可撤销。
      </DialogDescription>
    </DialogHeader>
    <div class="grid gap-2">
      <Label>取消原因</Label>
      <Textarea v-model="cancelReason" placeholder="请输入取消原因" />
    </div>
    <DialogFooter>
      <Button variant="outline" @click="showCancelDialog = false">取消</Button>
      <Button variant="destructive" @click="confirmForceCancel" :disabled="!cancelReason.trim() || isCancelling">
        {{ isCancelling ? '处理中...' : '确认取消' }}
      </Button>
    </DialogFooter>
  </DialogContent>
</Dialog>
```

- [ ] **Step 6: 导入必要的 UI 组件**

确保引入所需的 UI 组件:

```typescript
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter
} from '@/components/ui/dialog'
```

- [ ] **Step 7: 提交变更**

```bash
git add webui/src/views/TasksView.vue
git commit -m "feat: add subtask edit and force-cancel UI"
```

---

## 验证清单

完成实现后执行以下验证:

- [ ] 创建子任务时指定 Agent，创建后修改为其他 Agent
- [ ] 取消指派（设置 assigned_agent 为空）
- [ ] 强制取消各状态的任务（pending, assigned, in_progress, review, blocked）
- [ ] 验证强制取消后状态正确且无法再操作
- [ ] 前端界面正确显示和隐藏编辑按钮
- [ ] 前端强制取消对话框正常工作