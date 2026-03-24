# 子任务编辑界面增强设计

**日期**: 2026-03-24
**主题**: 子任务编辑界面状态和 Agent 下拉框增强

## 1. 需求概述

增强子任务编辑界面的两项功能：
1. 状态选项：从 2 个扩展到 9 个
2. Agent 下拉框：只显示当前任务所属团队的 agent

## 2. 技术方案

### 2.1 后端改动

**文件**: `app/routers/sub_tasks.py`

**改动点 1**: 扩展 `SubTaskResponse` 添加 `team_id` 字段

```python
class SubTaskResponse(BaseModel):
    # ... existing fields ...
    team_id: Optional[str] = None  # 新增：通过 task_id 关联获取团队 ID
```

**改动点 2**: 修改 `list_sub_tasks` 函数，在返回时填充 `team_id`

通过 `task_id` 关联查询 Task 表获取 `team_id`。

**改动点 3**: 修改 `get_sub_task` 函数，同步填充 `team_id`

### 2.2 前端改动

**文件**: `webui/src/views/TasksView.vue`

**改动点 1**: 扩展状态选项（行 1238-1244）

将编辑对话框的状态 dropdown 从 2 个选项扩展为 9 个：

```html
<select id="edit-subtask-status" v-model="editSubTaskStatus">
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

**改动点 2**: 新增团队 Agent 加载逻辑

添加新变量和函数：

```javascript
// 新增 ref
const editTeamAgents = ref([])

// 新增函数
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

**改动点 3**: 修改 `openEditSubTaskDialog` 函数

在打开编辑框时调用 `loadTeamAgents`：

```javascript
async function openEditSubTaskDialog(subTask: any) {
    // ... existing code ...
    editSubTaskStatus.value = subTask.status || ''
    editSubTaskAssignedAgent.value = subTask.assigned_agent || ''
    // 新增：加载团队 agent
    if (subTask.team_id) {
        await loadTeamAgents(subTask.team_id)
    } else {
        editTeamAgents.value = availableAgents.value
    }
}
```

**改动点 4**: 修改 Agent 下拉框模板

将 agent dropdown 的数据源从 `availableAgents` 改为 `editTeamAgents`：

```html
<select id="edit-subtask-agent" v-model="editSubTaskAssignedAgent">
    <option value="">不指派</option>
    <option v-for="agent in editTeamAgents" :key="agent.id" :value="agent.id">
        {{ agent.name }} ({{ agent.role }})
    </option>
</select>
```

## 3. 实现步骤

1. 修改后端 `SubTaskResponse` 添加 `team_id`
2. 修改后端 `list_sub_tasks` 和 `get_sub_task` 填充 `team_id`
3. 前端扩展状态选项为 9 个
4. 前端添加 `editTeamAgents` ref 和 `loadTeamAgents` 函数
5. 前端修改编辑框打开逻辑，调用团队 agent 加载
6. 前端修改 agent dropdown 使用新数据源

## 4. 回归测试

- 编辑非团队任务的子任务时，应显示所有 agent（fallback）
- 编辑团队任务的子任务时，应只显示团队成员
- 状态选项应为 9 个，且可正常保存
