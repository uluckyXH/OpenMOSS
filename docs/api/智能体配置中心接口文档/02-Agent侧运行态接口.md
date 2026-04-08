# Agent 侧运行态接口

> 最后同步：2026-04-08
> 接口前缀：`/api/agents`
> 对应代码：`app/routers/agents.py`

## 1. 模块概览

本模块包含三类接口：

- 旧运行态 Agent 的注册与基础管理接口
- Agent 自身调用的运行时接口，如心跳与获取 `SKILL.md`
- 运行态 Agent 下载自己的 `skill-bundle`，用于 `task-cli update` 或旧版本平滑迁移

## 2. 请求头

### 2.1 Agent Bearer 鉴权

```http
Authorization: Bearer <api_key>
```

### 2.2 Agent 注册令牌

```http
X-Registration-Token: <registration_token>
```

### 2.3 管理员鉴权

```http
X-Admin-Token: <admin_token>
```

## 3. 通用错误码

| 状态码 | 含义 | 说明 |
|---|---|---|
| `400` | 业务错误 | 例如角色非法、名称重复、状态非法 |
| `401` | Agent 鉴权失败 | `Authorization` 格式错误或 API Key 无效 |
| `403` | 权限不足 | 例如 Agent 已禁用、管理员鉴权失败、自注册关闭 |
| `404` | 资源不存在 | 例如角色技能文件不存在 |
| `422` | 请求体验证失败 | 缺少必填 Header 或 Body 字段 |

## 4. 响应结构

### 4.1 Agent 注册响应 `AgentRegisterResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Agent ID |
| `name` | string | Agent 名称 |
| `role` | string | Agent 角色 |
| `api_key` | string | 运行态 API Key |
| `message` | string | 提示信息 |

### 4.2 Agent 列表项 / 状态响应 `AgentResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Agent ID |
| `name` | string | Agent 名称 |
| `role` | string | Agent 角色 |
| `description` | string | 描述 |
| `status` | string | 当前状态：`active / disabled` |
| `total_score` | int | 当前累计积分 |

### 4.3 心跳响应 `AgentHeartbeatResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `agent_id` | string | 当前 Agent ID |
| `heartbeat_at` | datetime | 心跳记录时间 |
| `heartbeat_ip` | string/null | 解析出来的来源 IP |
| `message` | string | 提示信息，当前固定为 `心跳已记录` |

---

## 5. 接口清单

### 5.1 Agent 自注册

#### `POST /api/agents/register`

作用：Agent 使用注册令牌完成自注册，获取运行态 `api_key`。

#### 请求头

| 头 | 必填 | 说明 |
|---|---|---|
| `X-Registration-Token` | 是 | 注册令牌 |

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | Agent 名称，最大长度 `100` |
| `role` | string | 是 | 角色：`planner / executor / reviewer / patrol` |
| `description` | string | 否 | 描述，默认空字符串 |

#### 成功返回

- 状态码：`200`
- 返回体：`AgentRegisterResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 名称重复、角色非法等业务错误 |
| `403` | 自注册关闭，或注册令牌无效 |
| `422` | 缺少注册令牌 Header 或请求体不合法 |

#### 请求示例

```json
{
  "name": "ai-xiaohui",
  "role": "executor",
  "description": "测试执行 Agent"
}
```

#### 响应示例

```json
{
  "id": "a6f6f4fd-203d-4b66-a8fe-c9d3d3ee8f1d",
  "name": "ai-xiaohui",
  "role": "executor",
  "api_key": "ak_1234567890abcdef1234567890abcdef",
  "message": "注册成功，请保存 API Key"
}
```

### 5.2 管理员创建运行态 Agent

#### `POST /api/agents`

作用：管理员直接创建运行态 Agent。

#### 鉴权

- `X-Admin-Token`

#### 请求体

与“Agent 自注册”相同。

#### 成功返回

- 状态码：`200`
- 返回体：`AgentRegisterResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 名称重复、角色非法等业务错误 |
| `403` | 管理员鉴权失败 |
| `422` | 请求体不合法 |

### 5.3 查看 Agent 列表

#### `GET /api/agents`

作用：查看已注册运行态 Agent 列表。

#### 鉴权

- `Authorization: Bearer <api_key>`

#### Query 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `role` | string | 否 | - | 按角色过滤 |
| `status` | string | 否 | - | 按状态过滤 |

#### 成功返回

- 状态码：`200`
- 返回体：`AgentResponse[]`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `401` | API Key 格式错误或无效 |
| `403` | Agent 已禁用 |

### 5.4 更新 Agent 状态

#### `PUT /api/agents/{agent_id}/status`

作用：管理员更新某个运行态 Agent 的状态。

#### 鉴权

- `X-Admin-Token`

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 运行态 Agent ID |

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `status` | string | 是 | 状态：`active / disabled` |

#### 成功返回

- 状态码：`200`
- 返回体：`AgentResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | Agent 不存在，或状态非法 |
| `403` | 管理员鉴权失败 |
| `422` | 请求体不合法 |

### 5.5 Agent 上报心跳

#### `POST /api/agents/me/heartbeat`

作用：当前 Agent 使用自己的 API Key 上报在线心跳。

#### 鉴权

- `Authorization: Bearer <api_key>`

#### 请求体

- 无请求体

#### 来源 IP 解析规则

当前后端按以下优先级解析 IP：

1. `X-Forwarded-For`
2. `X-Real-IP`
3. `request.client.host`

#### 成功返回

- 状态码：`200`
- 返回体：`AgentHeartbeatResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `401` | `Authorization` 格式错误或 API Key 无效 |
| `403` | Agent 已禁用 |
| `422` | 缺少 `Authorization` Header |

### 5.6 获取当前 Agent 的 SKILL.md

#### `GET /api/agents/me/skill`

作用：根据当前 Agent 角色返回对应的 `SKILL.md` 说明文档。

#### 鉴权

- `Authorization: Bearer <api_key>`

#### 成功返回

- 状态码：`200`
- 返回体：纯文本 `SKILL.md`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `401` | `Authorization` 格式错误或 API Key 无效 |
| `403` | Agent 已禁用 |
| `404` | 当前角色对应的 `SKILL.md` 不存在 |
| `422` | 缺少 `Authorization` Header |

### 5.7 下载当前 Agent 的 Skill Bundle

#### `GET /api/agents/me/skill-bundle`

作用：按当前运行态 Agent 下载自己的 `skill-bundle`。

当前行为：

- 如果该运行态 Agent 已绑定 `managed_agent.runtime_agent_id`，则返回当前配置态 Agent 对应的专属 bundle
- 如果该运行态 Agent 仍是旧版本实例、尚未进入配置中心，则按当前 `role` 模板构建 bundle，便于从旧单文件目录平滑迁移

#### 鉴权

- `Authorization: Bearer <api_key>`

#### 成功返回

- 状态码：`200`
- 返回体：`application/zip`
- 响应头：`Content-Disposition: attachment; filename="task-<role>-skill.zip"`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `401` | `Authorization` 格式错误或 API Key 无效 |
| `403` | Agent 已禁用 |
| `404` | 当前角色模板目录不存在 |
| `422` | 缺少 `Authorization` Header |

#### 响应示例

```json
{
  "agent_id": "a6f6f4fd-203d-4b66-a8fe-c9d3d3ee8f1d",
  "heartbeat_at": "2026-04-03T20:00:00.123456",
  "heartbeat_ip": "203.0.113.10",
  "message": "心跳已记录"
}
```

### 5.6 获取当前 Agent 的 SKILL.md

#### `GET /api/agents/me/skill`

作用：获取当前 Agent 角色对应的 `SKILL.md`，并把 `<注册后填入>` 占位符替换成真实 API Key。

#### 鉴权

- `Authorization: Bearer <api_key>`

#### 成功返回

- 状态码：`200`
- 返回体：纯文本 `text/plain`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `401` | API Key 无效或格式错误 |
| `403` | Agent 已禁用 |
| `404` | 当前角色对应的 `SKILL.md` 不存在 |
