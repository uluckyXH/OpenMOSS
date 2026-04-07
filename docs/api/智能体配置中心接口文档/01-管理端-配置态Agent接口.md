# 管理端配置态 Agent 接口

> 最后同步：2026-04-07
> 接口前缀：`/api/admin/managed-agents`
> 鉴权方式：`X-Admin-Token`
> 对应代码：`app/routers/admin/managed_agents.py`

## 1. 模块概览

本模块用于管理端维护配置态 Agent，当前已覆盖：

- 配置态 Agent 基础 CRUD
- 宿主平台配置管理
- Prompt 资产管理
- Prompt 渲染预览
- 定时任务管理
- 宿主通讯渠道配置管理
- Bootstrap Token 管理

## 2. 请求头

```http
X-Admin-Token: <admin_token>
Content-Type: application/json
```

## 3. 通用错误码

| 状态码 | 含义 | 说明 |
|---|---|---|
| `400` | 参数错误 / 业务错误 | 例如 slug 冲突、配置态 Agent 不存在、模板不存在 |
| `403` | 管理员鉴权失败 | `X-Admin-Token` 缺失或无效 |
| `404` | 资源不存在 | 例如 `GET /{agent_id}` 未命中、某些子资源不属于该 Agent |
| `422` | 请求体验证失败 | 必填字段缺失、字段类型不合法、长度不合法 |

## 4. 通用响应结构

### 4.1 分页响应 `ManagedAgentPageResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | array | 列表项数组 |
| `total` | int | 总条数 |
| `page` | int | 当前页码 |
| `page_size` | int | 每页条数 |

### 4.2 列表项 / 详情 `ManagedAgentListItem` / `ManagedAgentDetail`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 配置态 Agent ID |
| `name` | string | 显示名称 |
| `slug` | string | 稳定标识 |
| `role` | string | 角色：`planner / executor / reviewer / patrol` |
| `description` | string | 描述 |
| `host_platform` | string | 宿主平台，当前主要为 `openclaw` |
| `deployment_mode` | string | 部署模式：`create_sub_agent / bind_existing_agent / bind_main_agent` |
| `host_access_mode` | string | 宿主访问方式：`local / remote` |
| `status` | string | 状态：`draft / configured / deployed / disabled / archived` |
| `runtime_agent_id` | string/null | 关联的运行态 Agent ID |
| `config_version` | int | 当前配置版本 |
| `deployed_config_version` | int/null | 已部署版本 |
| `needs_redeploy` | bool | 是否需要重新部署 |
| `online_status` | string/null | 在线状态，当前未实际写入 |
| `data_source` | string | 当前固定为 `managed` |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 4.3 宿主配置响应 `ManagedAgentHostConfigResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 宿主配置 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `host_platform` | string | 宿主平台 |
| `host_agent_identifier` | string/null | 宿主平台中的 Agent 标识 |
| `workdir_path` | string/null | 宿主平台中的工作目录 |
| `host_config_payload_masked` | string/null | 脱敏后的宿主配置文本 |
| `host_metadata_json` | string/null | 宿主侧非敏感扩展信息 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 4.4 Prompt 资产响应 `ManagedAgentPromptAssetResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Prompt 资产 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `template_role` | string/null | 初始化时使用的角色模板 |
| `system_prompt_content` | string | 系统提示词 |
| `persona_prompt_content` | string | 人格提示词 |
| `identity_content` | string | 身份内容 |
| `host_render_strategy` | string | 渲染策略 |
| `authority_source` | string | 当前固定为 `database` |
| `notes` | string/null | 备注 |
| `updated_at` | datetime | 更新时间 |

### 4.5 Prompt 渲染预览响应 `ManagedAgentPromptRenderPreviewResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `host_platform` | string | 宿主平台 |
| `host_render_strategy` | string | 渲染策略 |
| `artifacts` | array | 渲染结果数组 |

`artifacts[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 文件名 |
| `content` | string | 文件内容 |

### 4.6 定时任务响应 `ManagedAgentScheduleResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 定时任务 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `name` | string | 定时任务名称 |
| `enabled` | bool | 是否启用 |
| `schedule_type` | string | `interval / cron` |
| `schedule_expr` | string | 间隔值或 cron 表达式 |
| `timeout_seconds` | int | 超时秒数 |
| `model_override` | string/null | 模型覆盖，当前仍保留字段但不建议作为主配置使用 |
| `execution_options_json` | string/null | 宿主侧执行选项 JSON |
| `schedule_message_content` | string | 唤醒消息内容 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 4.7 宿主通讯渠道响应 `ManagedAgentCommBindingResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 绑定 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `provider` | string | 渠道类型：`feishu / slack / telegram / wechat / email / webhook` |
| `binding_key` | string | 平台账号或连接标识 |
| `display_name` | string/null | 展示名 |
| `enabled` | bool | 是否启用 |
| `routing_policy_json` | string/null | 路由策略 JSON |
| `metadata_json` | string/null | 非敏感补充信息 JSON |
| `config_payload_masked` | string/null | 脱敏后的配置文本 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 4.8 Bootstrap Token 响应

#### 创建响应 `ManagedAgentBootstrapTokenCreateResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Bootstrap Token ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `token` | string | 一次性返回的明文 token，仅创建成功当次可见 |
| `purpose` | string | `download_script / register_runtime` |
| `scope_json` | string/null | 附加范围信息 JSON |
| `expires_at` | datetime | 过期时间 |
| `created_at` | datetime | 创建时间 |

#### 列表项 `ManagedAgentBootstrapTokenListItem`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Bootstrap Token ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `token_masked` | string | 固定返回 `仅创建时可见`，不会回显明文 token |
| `purpose` | string | `download_script / register_runtime` |
| `scope_json` | string/null | 附加范围信息 JSON |
| `expires_at` | datetime | 过期时间 |
| `used_at` | datetime/null | 使用时间 |
| `revoked_at` | datetime/null | 撤销时间 |
| `created_at` | datetime | 创建时间 |
| `is_valid` | bool | 当前是否仍有效 |

---

## 5. 接口清单

### 5.1 分页获取配置态 Agent 列表

#### `GET /api/admin/managed-agents`

作用：分页查询配置态 Agent 列表。

#### Query 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `page` | int | 否 | `1` | 页码，最小值 `1` |
| `page_size` | int | 否 | `20` | 每页条数，范围 `1-100` |
| `role` | string | 否 | - | 按角色过滤 |
| `status` | string | 否 | - | 按状态过滤 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentPageResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `422` | `page` / `page_size` 不合法 |

#### 响应示例

```json
{
  "items": [
    {
      "id": "6df7f65f-7d43-4f0e-bdf0-38c7f37fe84e",
      "name": "AI小灰",
      "slug": "ai-xiaohui",
      "role": "executor",
      "description": "内容执行 Agent",
      "host_platform": "openclaw",
      "deployment_mode": "create_sub_agent",
      "host_access_mode": "local",
      "status": "draft",
      "runtime_agent_id": null,
      "config_version": 1,
      "deployed_config_version": null,
      "needs_redeploy": false,
      "online_status": null,
      "data_source": "managed",
      "created_at": "2026-04-03T12:00:00",
      "updated_at": "2026-04-03T12:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 5.2 创建配置态 Agent

#### `POST /api/admin/managed-agents`

作用：创建一个新的配置态 Agent 草稿，同时自动初始化 `host_config` 与 `prompt_asset`。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 显示名称，长度 `1-100` |
| `slug` | string | 是 | 稳定标识，长度 `1-100` |
| `role` | string | 是 | 角色：`planner / executor / reviewer / patrol` |
| `description` | string | 否 | 描述，默认空字符串 |
| `host_platform` | string | 否 | 宿主平台，默认 `openclaw` |
| `deployment_mode` | string | 是 | 部署模式：`create_sub_agent / bind_existing_agent / bind_main_agent` |
| `host_access_mode` | string | 否 | 访问方式：`local / remote`，默认 `local` |
| `host_agent_identifier` | string/null | 否 | 宿主平台中的 Agent 标识 |
| `workdir_path` | string/null | 否 | 宿主平台工作目录 |

#### 成功返回

- 状态码：`201`
- 返回体：`ManagedAgentDetail`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 例如 slug 冲突，错误信息示例：`slug 'ai-xiaohui' 已被使用` |
| `403` | 管理员鉴权失败 |
| `422` | 请求体字段缺失或格式不合法 |

#### 请求示例

```json
{
  "name": "AI小灰",
  "slug": "ai-xiaohui",
  "role": "executor",
  "description": "内容执行 Agent",
  "host_platform": "openclaw",
  "deployment_mode": "create_sub_agent",
  "host_access_mode": "local",
  "host_agent_identifier": "ai-xiaohui",
  "workdir_path": "~/.openclaw/workspace-ai-xiaohui"
}
```

### 5.3 获取配置态 Agent 详情

#### `GET /api/admin/managed-agents/{agent_id}`

作用：获取单个配置态 Agent 的基础详情。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentDetail`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |

### 5.4 更新配置态 Agent 基础信息

#### `PUT /api/admin/managed-agents/{agent_id}`

作用：更新配置态 Agent 的基础信息。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string/null | 否 | 新名称 |
| `description` | string/null | 否 | 新描述 |
| `host_platform` | string/null | 否 | 宿主平台 |
| `deployment_mode` | string/null | 否 | 部署模式 |
| `host_access_mode` | string/null | 否 | 访问方式 |
| `status` | string/null | 否 | 配置态状态 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentDetail`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 当前实现中，Agent 不存在等业务错误也会返回 `400` |
| `403` | 管理员鉴权失败 |
| `422` | 请求体不合法 |

### 5.5 删除配置态 Agent

#### `DELETE /api/admin/managed-agents/{agent_id}`

作用：硬删除配置态 Agent 及其关联的 `host_config / prompt_asset / schedules / comm_bindings`。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`204`
- 返回体：空

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |

### 5.6 获取宿主平台配置

#### `GET /api/admin/managed-agents/{agent_id}/host-config`

作用：获取某个配置态 Agent 的宿主配置。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentHostConfigResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 当前实现中，配置态 Agent 不存在时会走全局 `ValueError`，返回 `400` |
| `403` | 管理员鉴权失败 |
| `404` | 宿主平台配置未配置 |

### 5.7 更新宿主平台配置

#### `PUT /api/admin/managed-agents/{agent_id}/host-config`

作用：更新宿主配置；敏感字段不会明文回显。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `host_agent_identifier` | string/null | 否 | 宿主平台中的 Agent 标识 |
| `workdir_path` | string/null | 否 | 宿主工作目录 |
| `host_config_payload` | string/null | 否 | 明文配置文本，当前服务端原样存储，但返回时会脱敏 |
| `host_metadata_json` | string/null | 否 | 非敏感扩展信息 JSON 字符串 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentHostConfigResponse`

### 5.8 获取 Prompt 资产

#### `GET /api/admin/managed-agents/{agent_id}/prompt-asset`

作用：读取 Agent 的三段 Prompt 资产。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentPromptAssetResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 当前实现中，配置态 Agent 不存在时返回 `400` |
| `403` | 管理员鉴权失败 |
| `404` | Prompt 资产未配置 |

### 5.9 更新 Prompt 资产

#### `PUT /api/admin/managed-agents/{agent_id}/prompt-asset`

作用：更新 `system / persona / identity` 三段 Prompt。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `system_prompt_content` | string/null | 否 | 系统提示词 |
| `persona_prompt_content` | string/null | 否 | 人格提示词 |
| `identity_content` | string/null | 否 | 身份内容 |
| `host_render_strategy` | string/null | 否 | 渲染策略：`host_default / openclaw_workspace_files / openclaw_inline_schedule` |
| `notes` | string/null | 否 | 内部备注 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentPromptAssetResponse`

### 5.10 从模板重置 Prompt 资产

#### `POST /api/admin/managed-agents/{agent_id}/prompt-asset/reset-from-template`

作用：从 `prompts/templates/` 中按角色模板重新初始化 Prompt 资产。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentPromptAssetResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | Agent 不存在、角色模板不存在等 |
| `403` | 管理员鉴权失败 |

### 5.11 预览 Prompt 渲染结果

#### `POST /api/admin/managed-agents/{agent_id}/prompt-asset/render-preview`

作用：按当前 `host_platform + host_render_strategy` 预览实际渲染结果。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentPromptRenderPreviewResponse`

#### OpenClaw 场景示例

```json
{
  "host_platform": "openclaw",
  "host_render_strategy": "openclaw_workspace_files",
  "artifacts": [
    {
      "name": "AGENTS.md",
      "content": "你是系统提示词"
    },
    {
      "name": "SOUL.md",
      "content": "你是人格提示词"
    },
    {
      "name": "IDENTITY.md",
      "content": "你是身份内容"
    }
  ]
}
```

### 5.12 获取定时任务列表

#### `GET /api/admin/managed-agents/{agent_id}/schedules`

作用：获取该 Agent 下的全部定时任务。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentScheduleResponse[]`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |

### 5.13 创建定时任务

#### `POST /api/admin/managed-agents/{agent_id}/schedules`

作用：创建定时任务。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 定时任务名称 |
| `enabled` | bool | 否 | 是否启用，默认 `true` |
| `schedule_type` | string | 否 | `interval / cron`，默认 `interval` |
| `schedule_expr` | string | 否 | 间隔值或 cron 表达式，默认 `15m` |
| `timeout_seconds` | int | 否 | 超时秒数，默认 `1800`，最小 `60` |
| `model_override` | string/null | 否 | 模型覆盖 |
| `execution_options_json` | string/null | 否 | 宿主执行选项 JSON |
| `schedule_message_content` | string | 否 | 唤醒消息内容 |

#### 成功返回

- 状态码：`201`
- 返回体：`ManagedAgentScheduleResponse`

### 5.14 更新定时任务

#### `PUT /api/admin/managed-agents/{agent_id}/schedules/{schedule_id}`

作用：更新定时任务。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |
| `schedule_id` | string | 是 | 定时任务 ID |

#### 请求体

与“创建定时任务”相同。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentScheduleResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 当前实现中，某些业务错误会返回 `400` |
| `403` | 管理员鉴权失败 |
| `404` | 定时任务不属于该 Agent |

### 5.15 删除定时任务

#### `DELETE /api/admin/managed-agents/{agent_id}/schedules/{schedule_id}`

作用：删除定时任务。

#### 成功返回

- 状态码：`204`
- 返回体：空

### 5.16 获取宿主通讯渠道配置列表

#### `GET /api/admin/managed-agents/{agent_id}/comm-bindings`

作用：获取某个 Agent 在宿主平台上的通讯渠道配置列表。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentCommBindingResponse[]`

### 5.17 创建宿主通讯渠道配置

#### `POST /api/admin/managed-agents/{agent_id}/comm-bindings`

作用：新增一条宿主通讯渠道配置。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `provider` | string | 是 | 渠道类型：`feishu / slack / telegram / wechat / email / webhook` |
| `binding_key` | string | 是 | 平台账号或连接标识 |
| `display_name` | string/null | 否 | 展示名 |
| `enabled` | bool | 否 | 是否启用，默认 `true` |
| `routing_policy_json` | string/null | 否 | 路由策略 JSON |
| `metadata_json` | string/null | 否 | 非敏感补充信息 JSON |
| `config_payload` | string/null | 否 | 配置文本，当前服务端原样存储，返回时脱敏 |

#### 成功返回

- 状态码：`201`
- 返回体：`ManagedAgentCommBindingResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | `provider` 或 `binding_key` 为空等业务错误 |
| `403` | 管理员鉴权失败 |

### 5.18 更新宿主通讯渠道配置

#### `PUT /api/admin/managed-agents/{agent_id}/comm-bindings/{binding_id}`

作用：更新宿主通讯渠道配置。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |
| `binding_id` | string | 是 | 宿主通讯渠道配置 ID |

#### 请求体

与“创建宿主通讯渠道配置”相同。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentCommBindingResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 当前实现中，某些业务错误会返回 `400` |
| `403` | 管理员鉴权失败 |
| `404` | 宿主通讯渠道配置不属于该 Agent |

### 5.19 删除宿主通讯渠道配置

#### `DELETE /api/admin/managed-agents/{agent_id}/comm-bindings/{binding_id}`

作用：删除宿主通讯渠道配置。

#### 成功返回

- 状态码：`204`
- 返回体：空

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | 宿主通讯渠道配置不存在或不属于该 Agent |

### 5.20 创建 Bootstrap Token

#### `POST /api/admin/managed-agents/{agent_id}/bootstrap-tokens`

作用：为某个配置态 Agent 创建引导 Token。当前支持：

- `download_script`
- `register_runtime`

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `purpose` | string | 是 | `download_script / register_runtime` |
| `ttl_seconds` | int | 是 | Token 存活秒数，必须大于 `0` |
| `scope_json` | string/null | 否 | 附加范围信息 JSON，必须是 JSON object |

#### 成功返回

- 状态码：`201`
- 返回体：`ManagedAgentBootstrapTokenCreateResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 例如 `scope_json` 不是合法 JSON object、`ttl_seconds` 非法 |
| `403` | 管理员鉴权失败 |
| `404` | 配置态 Agent 不存在 |
| `422` | 请求体验证失败 |

#### 请求示例

```json
{
  "purpose": "download_script",
  "ttl_seconds": 3600,
  "scope_json": "{\"deployment_mode\":\"create_sub_agent\"}"
}
```

#### 响应示例

```json
{
  "id": "9e2f77ca-0a11-49b7-8562-0c68b0dca3e0",
  "managed_agent_id": "6df7f65f-7d43-4f0e-bdf0-38c7f37fe84e",
  "token": "bt_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "purpose": "download_script",
  "scope_json": "{\"deployment_mode\":\"create_sub_agent\"}",
  "expires_at": "2026-04-07T20:00:00",
  "created_at": "2026-04-07T19:00:00"
}
```

### 5.21 获取 Bootstrap Token 列表

#### `GET /api/admin/managed-agents/{agent_id}/bootstrap-tokens`

作用：查看某个配置态 Agent 的 Bootstrap Token 状态列表。注意：列表接口不会返回明文 token。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentBootstrapTokenListItem[]`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | 配置态 Agent 不存在 |

#### 响应示例

```json
[
  {
    "id": "9e2f77ca-0a11-49b7-8562-0c68b0dca3e0",
    "managed_agent_id": "6df7f65f-7d43-4f0e-bdf0-38c7f37fe84e",
    "token_masked": "仅创建时可见",
    "purpose": "download_script",
    "scope_json": "{\"deployment_mode\":\"create_sub_agent\"}",
    "expires_at": "2026-04-07T20:00:00",
    "used_at": null,
    "revoked_at": null,
    "created_at": "2026-04-07T19:00:00",
    "is_valid": true
  }
]
```

### 5.22 撤销 Bootstrap Token

#### `DELETE /api/admin/managed-agents/{agent_id}/bootstrap-tokens/{token_id}`

作用：撤销某个 Bootstrap Token。当前是“逻辑撤销”，不会物理删除记录。

#### 成功返回

- 状态码：`204`
- 返回体：空

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Token 不存在或不属于该 Agent |

### 5.23 获取 Bootstrap 脚本预览

#### `GET /api/admin/managed-agents/{agent_id}/bootstrap-script`

作用：为当前配置态 Agent 生成一份完整的 Bootstrap 脚本预览。接口会内部创建一个短期 `register_runtime` token，并直接嵌入脚本文本。

#### Query 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `selected_artifacts` | string[] | 否 | 全部或按渲染策略默认值 | 允许重复传参，控制是否写入 `AGENTS.md / SOUL.md / IDENTITY.md` |
| `include_schedule` | bool | 否 | `true` | 是否包含定时任务片段 |
| `include_comm_bindings` | bool | 否 | `true` | 是否包含宿主通讯渠道片段 |
| `register_ttl_seconds` | int | 否 | `3600` | 内嵌 `register_runtime` token 的有效期 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentBootstrapScriptResponse`

#### 响应字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `script` | string | 完整 shell 脚本文本 |
| `register_token_id` | string | 本次脚本内嵌的 `register_runtime` token ID |
| `register_token_expires_at` | datetime | 该 token 的过期时间 |

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 例如 `selected_artifacts` 非法、脚本渲染参数不合法 |
| `403` | 管理员鉴权失败 |
| `404` | 配置态 Agent 不存在 |
| `422` | Query 参数格式错误 |

### 5.24 获取接入说明和 curl 命令

#### `GET /api/admin/managed-agents/{agent_id}/onboarding-message`

作用：生成一段可以直接发给用户或远端 Agent 的接入说明文本，同时内部创建一个 `download_script` token 并返回对应的 `curl` 命令。

#### Query 参数

与“获取 Bootstrap 脚本预览”一致，另有：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `download_ttl_seconds` | int | 否 | `86400` | `download_script` token 的有效期 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentOnboardingMessageResponse`

#### 响应字段

| 字段 | 类型 | 说明 |
|---|---|---|
| `message` | string | 接入说明文本，已包含 curl 命令 |
| `curl_command` | string | 一键下载并执行脚本的命令 |
| `download_token_id` | string | 本次创建的 `download_script` token ID |
| `download_token_expires_at` | datetime | 该 token 的过期时间 |

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 例如脚本范围参数不合法 |
| `403` | 管理员鉴权失败 |
| `404` | 配置态 Agent 不存在 |
| `422` | Query 参数格式错误 |
