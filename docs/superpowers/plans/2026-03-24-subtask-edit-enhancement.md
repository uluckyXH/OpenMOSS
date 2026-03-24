# 子任务编辑界面增强实现计划

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强子任务编辑界面：状态选项从 2 个扩展到 9 个，Agent 下拉框只显示当前任务所属团队的 agent

**Architecture:** 后端扩展 SubTaskResponse 添加 team_id，前端修改编辑框逻辑加载团队成员

**Tech Stack:** FastAPI (Python), Vue 3, TypeScript

---

## Chunk 1: 后端改动 - 添加 team_id 到子任务查询

### Task 1: 修改 _build_sub_task_query 添加 team_id

**Files:**
- Modify: `app/services/admin_task_query_service.py:463-498`

- [ ] **Step 1: 修改查询添加 team_id 列**

在 `_build_sub_task_query` 函数的 columns 列表中添加 `Task.team_id`：

```python
def _build_sub_task_query(db: Session, include_detail_fields: bool) -> Query:
    """构建子任务基础查询"""
    columns = [
        SubTask.id.label("id"),
        SubTask.task_id.label("task_id"),
        Task.name.label("task_name"),
        Task.team_id.label("team_id"),  # 新增
        SubTask.module_id.label("module_id"),
        # ... existing columns ...
    ]
```

- [ ] **Step 2: 修改 _serialize_sub_task_row 添加 team_id**

修改 `app/services/admin_task_query_service.py:562-586` 中的序列化函数：

```python
def _serialize_sub_task_row(row, include_detail_fields: bool = False) -> dict:
    mapping = row._mapping
    data = {
        # ... existing fields ...
        "team_id": mapping.get("team_id"),  # 新增
    }
    return data
```

- [ ] **Step 3: 验证语法正确**

```bash
cd /Users/leon_zheng/PycharmProjects/wenge/OpenMOSS
python -m py_compile app/services/admin_task_query_service.py
```

---

## Chunk 2: 前端改动 - 扩展状态选项

### Task 2: 修改状态 dropdown 扩展为 9 个选项

**Files:**
- Modify: `webui/src/views/TasksView.vue:1238-1244`

- [ ] **Step 1: 修改状态 dropdown HTML**

将编辑对话框中的状态 dropdown 从 2 个选项扩展为 9 个：

```html
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
```

- [ ] **Step 2: 构建前端验证**

```bash
cd /Users/leon_zheng/PycharmProjects/wenge/OpenMOSS/webui
npm run build 2>&1 | head -30
```

---

## Chunk 3: 前端改动 - Agent 下拉框按团队过滤

### Task 3: 添加团队 Agent 加载逻辑

**Files:**
- Modify: `webui/src/views/TasksView.vue:82-100`, `591-606`, `1247-1254`

- [ ] **Step 1: 添加 editTeamAgents ref**

在 `webui/src/views/TasksView.vue` 的 ref 定义区域（约第 82-100 行）添加：

```javascript
const editTeamAgents = ref([])
```

- [ ] **Step 2: 添加 loadTeamAgents 函数**

在 `webui/src/views/TasksView.vue` 中添加新函数（约在 `loadAvailableAgents` 函数附近）：

```javascript
async function loadTeamAgents(teamId: string) {
    if (!teamId) {
        editTeamAgents.value = availableAgents.value
        return
    }
    try {
        const res = await teamApi.get(teamId)
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
```

- [ ] **Step 3: 修改 openEditSubTaskDialog 函数**

修改 `openEditSubTaskDialog` 函数（约第 591-606 行），在打开编辑框时加载团队 agent：

```javascript
async function openEditSubTaskDialog(subTask: any) {
    // ... existing code ...
    editSubTaskStatus.value = subTask.status || ''
    editSubTaskAssignedAgent.value = subTask.assigned_agent || ''

    // 新增：根据 team_id 加载团队 agent
    if (subTask.team_id) {
        await loadTeamAgents(subTask.team_id)
    } else {
        editTeamAgents.value = availableAgents.value
    }
}
```

- [ ] **Step 4: 修改 agent dropdown 使用新数据源**

修改 agent dropdown 模板（约第 1247-1254 行），将 `availableAgents` 改为 `editTeamAgents`：

```html
<select id="edit-subtask-agent" v-model="editSubTaskAssignedAgent"
    class="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">
    <option value="">不指派</option>
    <option v-for="agent in editTeamAgents" :key="agent.id" :value="agent.id">
        {{ agent.name }} ({{ agent.role }})
    </option>
</select>
```

- [ ] **Step 5: 构建前端验证**

```bash
cd /Users/leon_zheng/PycharmProjects/wenge/OpenMOSS/webui
npm run build 2>&1 | head -30
```

---

## Chunk 4: 验证和提交

### Task 4: 验证完整功能

- [ ] **Step 1: 启动后端服务**

```bash
cd /Users/leon_zheng/PycharmProjects/wenge/OpenMOSS
python -m uvicorn app.main:app --host 0.0.0.0 --port 6565 &
sleep 3
```

- [ ] **Step 2: 启动前端服务**

```bash
cd /Users/leon_zheng/PycharmProjects/wenge/OpenMOSS/webui
npm run dev &
sleep 5
```

- [ ] **Step 3: 测试 API 返回 team_id**

```bash
curl -s http://localhost:6565/api/admin/sub-tasks -H "Authorization: Bearer <token>" | jq '.items[0].team_id'
```

- [ ] **Step 4: 提交代码**

```bash
cd /Users/leon_zheng/PycharmProjects/wenge/OpenMOSS
git add app/services/admin_task_query_service.py webui/src/views/TasksView.vue
git commit -m "feat: enhance sub-task edit with full status options and team-based agent filtering"
git push
```

---

## 执行顺序

1. **Chunk 1**: 后端改动 - 添加 team_id
2. **Chunk 2**: 前端改动 - 状态选项扩展
3. **Chunk 3**: 前端改动 - Agent 团队过滤
4. **Chunk 4**: 验证和提交
