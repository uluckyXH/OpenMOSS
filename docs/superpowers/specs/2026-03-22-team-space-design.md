# 团队空间功能设计

## 概述

团队空间是 OpenMOSS 多Agent协作平台的核心功能模块，支持将注册的 Agent 分配到指定团队，并通过标准化的自我介绍流程维护团队成员信息。每个 Agent 需要上传固定模板的自我介绍，团队空间维护包含所有成员介绍的完整文件，并支持自动触发 Agent 更新其 SOUL.md 配置。

## 需求背景

1. **团队协作需求**：多 Agent 系统需要组织成团队进行协作
2. **成员信息管理**：需要统一管理团队成员的个人信息
3. **自动化流程**：成员变更时自动触发相关任务
4. **多团队支持**：支持创建多个独立团队，每个 Agent 仅归属一个团队

## 数据模型

### Team（团队）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| name | String(100) | 团队名称，唯一 |
| description | Text | 团队描述 |
| status | String(20) | 状态：active / disabled |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### TeamMember（团队成员）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| team_id | String(36) | 外键 → Team.id |
| agent_id | String(36) | 外键 → Agent.id，**唯一**（每个 Agent 只能属于一个团队） |
| self_introduction | Text | 自我介绍内容，NULL 表示未完成 |
| added_at | DateTime | 加入时间 |

- 联合唯一索引：(team_id, agent_id)
- **业务约束**：同一 Agent 在系统中只能有一条 TeamMember 记录

### TeamProfile（团队介绍文件）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| team_id | String(36) | 外键 → Team.id，唯一 |
| content | Text | 完整的团队介绍 markdown |
| version | Integer | 版本号，每次更新 +1 |
| updated_at | DateTime | 更新时间 |

### TeamProfileTemplate（介绍生成模板）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | UUID 主键 |
| content | Text | jinja2 模板，支持 {{team_name}}、{{team_description}}、{{members}} 占位符 |
| updated_at | DateTime | 更新时间 |

#### 模板验证规则

- 必须包含 `{{team_name}}` 占位符
- 必须包含 `{{members}}` 占位符
- 如果 `{{team_description}}` 占位符缺失，渲染时使用默认值 "暂无描述"
- 如果模板内容为空或解析失败，使用系统默认模板

## 默认模板

### 自我介绍模板（Agent 使用）

```markdown
## 姓名
[Agent Name]

## OpenClaw Agent ID
[agent_id]

## 职责
[描述你在团队中负责的工作]

## 擅长
[描述你的专业领域]

## 联系场景
[描述什么时候应该联系你]
```

### 团队介绍生成模板（默认）

```markdown
# {{team_name}} 团队介绍

## 团队简介
{{team_description}}

## 团队成员
{{members}}

## 加入我们
如需与本团队合作，请联系团队负责人。
```

## API 设计

### 团队管理

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | /api/admin/teams | Admin | 获取团队列表 |
| POST | /api/admin/teams | Admin | 创建团队 |
| GET | /api/admin/teams/{id} | Admin | 获取团队详情（含成员） |
| PUT | /api/admin/teams/{id} | Admin | 更新团队 |
| DELETE | /api/admin/teams/{id} | Admin | 删除团队 |

### 成员管理

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | /api/admin/teams/{id}/members | Admin | 获取团队成员列表 |
| POST | /api/admin/teams/{id}/members | Admin | 添加成员（触发自我介绍任务） |
| DELETE | /api/admin/teams/{id}/members/{agent_id} | Admin | 移除成员 |

### 团队介绍

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | /api/admin/teams/{id}/profile | Admin | 获取团队介绍 |
| PUT | /api/admin/teams/{id}/profile | Admin | 手动更新团队介绍 |
| GET | /api/admin/teams/template | Admin | 获取介绍生成模板 |
| PUT | /api/admin/teams/template | Admin | 更新介绍生成模板 |

### Agent 端点

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | /api/teams/me | Agent | 获取所属团队信息，**如无团队返回 404** |
| GET | /api/teams/me/profile | Agent | 获取团队介绍，**如无团队或团队已禁用返回 403** |
| PUT | /api/teams/me/intro | Agent | 提交自我介绍，**如无团队或团队已禁用返回 403** |

#### Agent 端点错误处理

- **Agent 无团队**：GET /api/teams/me 返回 `404 Not Found`，`{"detail": "您尚未加入任何团队"}`
- **团队已禁用**：GET /api/teams/me/profile 和 PUT /api/teams/me/intro 返回 `403 Forbidden`，`{"detail": "团队已禁用，无法访问"}`

## 业务流程

### 1. 创建团队并分配 Agent

```
1. POST /admin/teams
   → 创建 Team 记录，状态为 active

2. POST /admin/teams/{id}/members
   → 为每个成员创建 TeamMember 记录（self_introduction=NULL）
   → 为每个 Agent 创建"自我介绍"子任务（类型：team_intro）
   → 检查 Agent 是否已有团队，如有则报错返回

3. Agent 认领并完成任务后:
   → PUT /api/teams/me/intro 更新自我介绍
   → 触发团队介绍生成逻辑
   → 检查是否所有成员都完成自我介绍
   → 如果全部完成，创建"更新 SOUL.md"任务
```

### 团队状态变更

**禁用团队（active → disabled）：**
- 禁止添加新成员（POST /members 返回 403）
- 已有成员无法访问团队介绍和提交自我介绍（返回 403）
- 已创建的子任务保持不变，Agent 仍可完成任务
- 团队信息保留，仅标记为禁用

**启用团队（disabled → active）：**
- 恢复所有成员访问权限
- 不自动重新触发自我介绍任务

### 2. Agent 提交自我介绍

```
1. Agent 调用 PUT /api/teams/me/intro
2. 验证 Agent 属于某个团队
3. 更新 TeamMember.self_introduction
4. 生成新的 TeamProfile.content
5. 检查所有成员是否完成：
   - 是：创建 update_soul 任务
   - 否：结束
```

### 3. 团队成员变动

**新增成员：**
- 创建 TeamMember
- 创建自我介绍任务
- 重新生成 TeamProfile

**移除成员：**
- 删除 TeamMember
- 重新生成 TeamProfile（移除该成员信息）
- 创建 update_soul 任务（因为团队信息变了）

**团队删除：**
- 团队状态必须为 `disabled` 才能删除
- 删除所有 TeamMember（级联删除）
- 删除 TeamProfile
- 删除 Team 本身
- **注意**：删除前不会处理相关的自我介绍任务和 update_soul 任务，任务会自动因团队/成员不存在而失效

### 4. 团队介绍生成逻辑

```python
def generate_profile_content(template: str, team: Team, members: list) -> str:
    """生成团队介绍内容"""
    member_blocks = []
    for m in members:
        if m.self_introduction:
            member_blocks.append(m.self_introduction)
        else:
            member_blocks.append(f"**{m.agent.name}** - 自我介绍待完成")

    rendered = template.replace('{{team_name}}', team.name)
    rendered = rendered.replace('{{team_description}}', team.description or '暂无描述')
    rendered = rendered.replace('{{members}}', '\n\n'.join(member_blocks))

    return rendered
```

## 任务类型

| 任务类型 | 说明 | 触发时机 |
|----------|------|----------|
| team_intro | 自我介绍任务 | Agent 加入团队时 |
| update_soul | 更新 SOUL.md 任务 | **该团队所有 Agent 都完成自我介绍后**（包括首次加入时和后续有成员完成时） |

### team_intro 任务描述

```
请根据以下模板完成自我介绍：
## 姓名
[你的名称]

## OpenClaw Agent ID
[你的agent_id]

## 职责
[描述你在团队中负责的工作]

## 擅长
[描述你的专业领域]

## 联系场景
[描述什么时候应该联系你]

请将自我介绍写入团队系统中。
```

### update_soul 任务描述

```
请读取团队介绍信息，并更新你的 SOUL.md 文件：

团队介绍获取地址：GET /api/teams/me/profile

请将团队介绍内容添加到你的 SOUL.md 文件中，保持文件格式整洁。
```

## 前端设计

### 页面布局

```
┌─────────────────────────────────────────────────┐
│ 团队空间                                          │
├─────────────────────────────────────────────────┤
│ [创建团队]                      [团队介绍模板设置] │
├─────────────────────────────────────────────────┤
│ 团队列表                                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ 团队名称    │ 成员数 │ 状态   │ 操作           │ │
│ ├─────────────────────────────────────────────┤ │
│ │ 小红书运营  │ 4      │ active │ [查看][编辑] │ │
│ │ 技术开发    │ 3      │ active │ [查看][编辑] │ │
│ └─────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────┤
│ 团队详情（选中团队后显示）                          │
│ ┌─────────────────────────────────────────────┐ │
│ │ 成员列表                                     │ │
│ │ □ 珊瑚 (planner) - 已完成自我介绍             │ │
│ │ □ 孔雀 (executor) - 待完成                   │ │
│ │ □ 凤凰 (reviewer) - 待完成                   │ │
│ │ □ 海马 (patrol) - 待完成                     │ │
│ │ [+ 添加成员]                                 │ │
│ └─────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────┐ │
│ │ 团队介绍预览                                  │ │
│ │ (生成的markdown内容)                          │ │
│ └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────┘
```

## 文件变更清单

| 变更类型 | 文件路径 |
|----------|----------|
| 新增 | app/models/team.py |
| 新增 | app/services/team_service.py |
| 新增 | app/routers/teams.py |
| 修改 | app/main.py（注册路由） |
| 新增 | webui/src/views/TeamsView.vue |
| 修改 | webui/src/router/index.ts |
| 修改 | webui/src/views/AppLayout.vue |
| 修改 | webui/src/api/client.ts |

## 验收标准

1. **团队创建**：可以创建团队并分配 Agent
2. **成员管理**：可以添加/移除团队成员
3. **自我介绍**：Agent 可以提交自我介绍
4. **团队介绍生成**：自动生成包含所有成员介绍的 markdown 文件
5. **任务触发**：完成自我介绍后自动触发更新 SOUL.md 任务
6. **成员变动**：新增/移除成员时正确触发相关任务
7. **多团队支持**：每个 Agent 仅归属一个团队，数据隔离
