# 子任务人工干预功能设计

## 概述

为 OpenMOSS 系统增加管理员对子任务的人工干预能力，包括：
1. 修改子任务信息（名称、描述、Agent 指派）
2. 强制取消任务（带取消原因）

## 背景

当前系统存在以下限制：
- 任务创建时指定 `assigned_agent` 后，只有 `executor` 角色可以认领
- 任务进行中无法人工干预，只能等待 Agent 完成任务
- 前端没有任务编辑功能

## 设计目标

1. 支持在创建后修改子任务的 Agent 指派
2. 支持管理员强制取消任务（无需通过状态机）
3. 前端在子任务详情中提供编辑界面

## 详细设计

### 1. 后端 API

#### 1.1 修改子任务

```
PUT /api/admin/sub-tasks/{sub_task_id}
```

**请求体**:
```typescript
interface SubTaskUpdateRequest {
  name?: string;           // 名称
  description?: string;     // 描述
  deliverable?: string;    // 交付物
  acceptance?: string;     // 验收标准
  priority?: string;       // 优先级
  assigned_agent?: string; // 指派 Agent ID（可为空表示取消指派）
}
```

**响应**: 返回更新后的 `AdminSubTaskDetail`

**限制**:
- 仅 `pending` / `assigned` / `blocked` 状态可编辑
- 修改 `assigned_agent` 时，如果是合法 Agent ID 则更新，否则报错

#### 1.2 强制取消

```
POST /api/admin/sub-tasks/{sub_task_id}/force-cancel
```

**请求体**:
```typescript
interface ForceCancelRequest {
  reason: string;  // 取消原因（必填）
}
```

**响应**: 返回更新后的 `AdminSubTaskDetail`

**实现逻辑**:
- 直接修改状态为 `cancelled`，跳过状态机校验
- 清空 `current_session_id`
- 记录取消原因到日志（可选）

### 2. 前端界面

#### 2.1 任务管理页面结构

位置: `webui/src/views/TasksView.vue`

#### 2.2 子任务详情面板

在现有 `selectedSubTask` 详情面板基础上增加：

**编辑表单区域**（仅 pending/assigned/blocked 状态显示）:
- 名称输入框
- 描述文本域
- 交付物输入框
- 验收标准输入框
- Agent 下拉选择器（显示 Agent 名称 + 角色）

**强制取消按钮**:
- 位置：详情面板底部
- 任何状态可见
- 点击弹出确认对话框，输入取消原因
- 确认后调用 `/force-cancel` API

#### 2.3 Agent 列表获取

使用现有 API:
```typescript
agentApi.list()  // 获取所有 Agent 列表
```

### 3. API Client 更新

在 `webui/src/api/client.ts` 中添加:

```typescript
updateSubTask: (id: string, data: SubTaskUpdateRequest) =>
  api.put(`/admin/sub-tasks/${id}`, data),

forceCancelSubTask: (id: string, reason: string) =>
  api.post(`/admin/sub-tasks/${id}/force-cancel`, { reason }),
```

### 4. 状态机调整

现有状态机不变，强制取消作为特殊操作绕过状态机:

```python
VALID_TRANSITIONS = {
    "pending":      ["assigned"],
    "assigned":     ["in_progress", "pending"],
    "in_progress":  ["review"],
    "review":       ["done", "rework"],
    "rework":       ["in_progress"],
    "blocked":      ["pending"],
    "done":         [],
    "cancelled":    [],  # 终态
}
```

## 文件变更清单

### 后端
- `app/routers/admin_tasks.py` - 添加修改和强制取消端点
- `app/services/sub_task_service.py` - 添加强制取消逻辑
- `app/schemas/admin_task.py` - 添加请求/响应模型

### 前端
- `webui/src/api/client.ts` - 添加 API 方法
- `webui/src/views/TasksView.vue` - 添加编辑界面

## 测试要点

1. 创建子任务时指定 Agent，创建后修改为其他 Agent
2. 取消指派（设置 assigned_agent 为空）
3. 强制取消各状态的任务（pending, assigned, in_progress, review, blocked）
4. 验证强制取消后状态正确且无法再操作
