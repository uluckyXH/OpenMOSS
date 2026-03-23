# Agent 通信协作 - 团队介绍模板设计方案

## 概述

在团队介绍模板中添加 Agent 间通信协作配置，使各角色能够通过 OpenClaw 的 agent-send 机制主动通知相关成员认领或处理任务，替代原有的纯定时任务轮询模式。

## 背景

### 当前问题

- 各 Agent 依赖 cron 定时唤醒，唤醒时间不一致
- 任务完成后需要被动等待其他 Agent 轮询发现
- 整体任务完成时间不可预测

### 解决思路

- 在团队介绍模板中定义各角色的协作关系
- Agent 完成任务后通过 agent-send 主动通知下游角色
- 各角色被唤醒后直接获取针对性任务，而非扫描全部 pending 任务

## 架构设计

### 角色与通知关系

| 角色 | 角色名称 | 完成任务后通知 | 通知目的 |
|------|----------|---------------|---------|
| planner | 规划师 | executor | 创建任务后通知执行者认领 |
| executor | 执行者 | reviewer | 提交审核时通知审核者审查 |
| reviewer | 审核者 | executor (驳回时) | 返工时通知执行者修复 |
| reviewer | 审核者 | patrol (通过时) | 任务完成时通知巡查者确认 |
| patrol | 巡查者 | 相关角色 | 发现异常时通知相关人员处理 |

### 通知消息模板

每个角色在完成任务后，发送通知消息格式如下：

```
【{角色名称}】{任务状态变化}

任务：{task_name}
任务ID：{task_id}
状态：{from_status} → {to_status}

{具体说明}

请前往系统处理：{api_endpoint}

遇到问题时可通过消息渠道联系我。
```

### 数据占位符

Agent 在发送通知时需要自行替换的占位符：

| 占位符 | 说明 | 示例 |
|--------|------|------|
| `{{task_name}}` | 任务名称 | "小红书今日内容发布" |
| `{{task_id}}` | 任务ID | "abc-123-def" |
| `{{from_status}}` | 原状态 | "pending" |
| `{{to_status}}` | 新状态 | "in_progress" |
| `{{sub_task_name}}` | 子任务名称 | "美食笔记撰写" |
| `{{sub_task_id}}` | 子任务ID | "sub-456-789" |

## 团队介绍模板结构

在 `TeamProfileTemplate` 的默认模板中添加以下章节：

```markdown
## 角色协作配置

### 规划师 (planner)
- **职责**：分析数据、制定计划、拆分任务
- **需要通知的执行者**：xhs_executor_wheat（小麦）
- **通知模板**：
  ```
  【新任务通知】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  任务ID：{{task_id}}
  子任务ID：{{sub_task_id}}

  详情：{{description}}
  验收标准：{{acceptance}}

  请前往系统认领并执行：GET /api/sub-tasks/{{sub_task_id}}
  ```

### 执行者 (executor)
- **职责**：根据计划创作内容并发布
- **需要通知的审核者**：xhs_reviewer_cherry（樱桃）
- **通知模板**：
  ```
  【任务提交审核】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  任务ID：{{task_id}}
  子任务ID：{{sub_task_id}}

  交付物：{{deliverable}}
  状态：{{from_status}} → {{to_status}}

  请前往系统审核：GET /api/sub-tasks/{{sub_task_id}}
  ```

### 审核者 (reviewer)
- **职责**：审核内容质量，通过或驳回
- **审核通过时**：任务完成（无需通知）
- **审核驳回时通知**：原执行者
- **通知模板**：
  ```
  【任务需要返工】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  任务ID：{{task_id}}
  子任务ID：{{sub_task_id}}

  原因：{{rejection_reason}}

  请前往系统查看详情并修复：GET /api/sub-tasks/{{sub_task_id}}
  ```

### 巡查者 (patrol)
- **职责**：监控系统状态、处理异常
- **发现异常时通知**：相关角色（根据异常类型）
- **通知模板**：
  ```
  【异常告警】

  任务：{{task_name}}
  子任务：{{sub_task_name}}
  问题：{{issue_description}}

  请及时处理：GET /api/sub-tasks/{{sub_task_id}}
  ```
```

## 实施步骤

### 步骤1：更新默认模板

修改 `app/models/team.py` 中的 `TeamProfileTemplate.get_default_template()` 方法，添加角色协作配置章节。

### 步骤2：验证现有团队

对于已存在的团队，调用 `generate_team_profile` 重新生成团队介绍。

### 步骤3：（可选）Agent 模板更新

根据需要更新各角色的 prompt 模板，添加 agent-send 的使用说明。

## 预期效果

- Agent 完成任务后主动通知相关角色
- 减少任务等待时间
- 协作关系清晰可追溯
- 无需修改后端 API
