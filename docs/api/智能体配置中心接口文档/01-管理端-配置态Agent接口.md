# 管理端配置态 Agent 接口

> 最后同步：2026-04-13
> 接口前缀：`/api/admin/managed-agents`
> 鉴权方式：`X-Admin-Token`
> 对应代码：`app/routers/admin/managed_agents.py`

## 1. 模块概览

本模块用于管理端维护配置态 Agent，当前已覆盖：

- 宿主平台能力查询
- Prompt 模板示例查询
- 配置态 Agent 基础 CRUD
- 列表/详情内嵌配置就绪度 `readiness`
- 宿主平台配置管理
- Prompt 资产管理
- Prompt 渲染预览
- 定时任务管理
- 宿主通讯渠道配置管理（通用）
- **Feishu 结构化通讯绑定**（schema 发现 / 预校验 / 结构化 CRUD）
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

### 4.2 宿主平台元数据响应 `ManagedAgentHostPlatformMetaResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | array | 当前后端真实支持的宿主平台能力列表 |

`items[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | 宿主平台标识 |
| `label` | string | 前端展示名称 |
| `description` | string | 平台简介，用于创建弹窗或平台说明区 |
| `access_modes` | array | 支持的宿主访问方式：`local / remote` |
| `deployment_modes` | array | 支持的部署模式 |
| `capabilities.renderer` | bool | 是否已实现 renderer |
| `capabilities.bootstrap_script` | bool | 是否支持生成 bootstrap script |
| `capabilities.skill_bundle` | bool | 是否支持生成 skill-bundle |
| `capabilities.prompt_preview` | bool | 是否支持 prompt 渲染预览 |
| `capabilities.schedule` | bool | 是否支持 schedule |
| `capabilities.comm_binding` | bool | 是否支持宿主通讯渠道配置 |
| `supported_comm_providers` | array | 当前已支持的通讯渠道 provider 列表；按当前真实实现，OpenClaw 仅返回 `feishu` |
| `ui_hints` | object | 前端动态渲染提示；只描述展示和表单，不代表新平台能力已经实现 |

`ui_hints` 结构说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `host_config.description` | string | 平台配置 Tab 顶部说明 |
| `host_config.fields[]` | array | 平台配置字段列表，按顺序渲染 |
| `prompt.description` | string | Prompt Tab 顶部说明 |
| `prompt.render_strategies[]` | array | 渲染策略选项 |
| `prompt.sections[]` | array | Prompt 段落定义 |
| `schedule` | object/null | 定时任务 Tab 的说明和默认值 |
| `comm` | object/null | 宿主通讯渠道 Tab 的说明 |
| `bootstrap` | object/null | 部署接入 Tab 的说明 |

`host_config.fields[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | 对应宿主配置 API 入参；标准字段包括 `host_agent_identifier / workdir_path / host_config_payload / host_metadata_json` |
| `label` | string | 展示标签 |
| `type` | string | 控件类型：`text / textarea / password / json / select` |
| `placeholder` | string/null | 占位提示 |
| `description` | string/null | 字段帮助说明 |
| `required` | bool | 是否必填，仅用于前端校验 |
| `sensitive` | bool/null | 是否敏感字段；敏感字段保存后只回显脱敏结果 |
| `group` | string/null | 前端分组名 |

`prompt.render_strategies[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `value` | string | 渲染策略值；OpenClaw 当前只向前端暴露 `openclaw_workspace_files` |
| `label` | string | 展示标签 |
| `description` | string | 策略说明 |
| `is_default` | bool/null | 是否为默认策略；只有一个策略时前端可自动选中并隐藏选择器 |

`prompt.sections[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | 对应 Prompt 资产 API 入参；标准字段包括 `system_prompt_content / persona_prompt_content / identity_content` |
| `label` | string | 展示标签；OpenClaw 使用文件语义，如 `工作规则（AGENTS.md）` |
| `placeholder` | string/null | 占位提示 |
| `required` | bool | 是否必填；OpenClaw 当前三段都是可选 |
| `description` | string/null | 一句话简介，适合常显在标题下方 |
| `detail` | string/null | 完整说明，适合放在帮助展开内容里 |

说明：

- `ui_hints` 来自后端代码注册表，不来自数据库，也不是用户配置。
- 当前真实支持的平台只有 `openclaw`；Claude Code / Codex CLI 等只属于未来设计示例。
- `ui_hints` 只驱动前端展示和表单，后端真实能力仍以 `capabilities`、renderer、bootstrap 实现为准。

### 4.3 列表项 / 详情 `ManagedAgentListItem` / `ManagedAgentDetail`

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
| `config_version` | int | 当前目标部署版本；首次部署前默认保持 `1`，部署后首次再修改才会推进到下一版本 |
| `deployed_config_version` | int/null | 当前已部署版本；未部署时为 `null` |
| `needs_redeploy` | bool | 是否需要重新部署 |
| `online_status` | string/null | 在线状态，当前未实际写入 |
| `data_source` | string | 当前固定为 `managed` |
| `readiness` | object | 配置就绪度，列表和详情接口都会返回 |
| `runtime_identity` | object | 运行态身份摘要，包含脱敏 API Key；完整 API Key 不会在详情接口回显 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

版本字段规则：

- `config_version` 表示当前目标部署版本，不是每次编辑都会递增的修订计数。
- 首次部署前，`config_version` 固定保持 `1`，多次编辑不会持续递增。
- 部署成功后，`deployed_config_version` 会更新为当前 `config_version`。
- 已部署后首次再修改配置，`config_version` 才推进到下一个待部署版本。
- 已经存在待部署版本时，继续编辑仍保持当前 `config_version`，直到下一次部署成功。
- `needs_redeploy = true` 表示 `config_version != deployed_config_version`。

`readiness` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `host_config` | bool | 宿主平台配置是否已有实质内容；当前规则为 `host_agent_identifier` 或 `workdir_path` 至少一个非空 |
| `prompt_asset` | bool | Prompt 资产是否已有实质内容；当前规则为 `system_prompt_content / persona_prompt_content / identity_content` 任意一个非空 |
| `schedules_count` | int | 定时任务数量，`0` 表示未配置；定时任务不是部署必填项 |
| `comm_bindings_count` | int | 宿主通讯渠道数量，`0` 表示未配置；通讯渠道不是部署必填项 |
| `deploy_ready` | bool | 是否满足部署前置条件；当前规则为 `host_config`。OpenClaw Prompt 文件都是可选配置，不再阻塞部署 |

说明：

- `readiness` 是后端统一计算的配置就绪度，前端不应再自行请求 `host-config` / `prompt-asset` 做探测判断。
- `GET /api/admin/managed-agents` 会批量计算 `readiness`，避免列表页 N+1 请求。

`runtime_identity` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `registered` | bool | 是否已完成运行态 Agent 注册 |
| `runtime_agent_id` | string/null | 关联的运行态 Agent ID |
| `api_key_masked` | string/null | 脱敏后的运行态 API Key；未注册时为 `null` |

说明：

- 完整 `api_key` 只在 bootstrap 注册成功或主动重置成功当次返回。
- 详情接口只返回 `api_key_masked`，前端基础信息页应使用该字段展示“API Key 已生成”状态。
- 如果用户丢失完整 `api_key`，应调用重置接口生成新 key，不提供普通查看完整旧 key 的接口。

### 4.4 宿主配置响应 `ManagedAgentHostConfigResponse`

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

### 4.5 Prompt 资产响应 `ManagedAgentPromptAssetResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | Prompt 资产 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `template_role` | string/null | 初始化时使用的角色模板 |
| `system_prompt_content` | string | 工作规则内容，对应 OpenClaw `AGENTS.md` |
| `persona_prompt_content` | string | 人格设定内容，对应 OpenClaw `SOUL.md` |
| `identity_content` | string | 身份信息内容，对应 OpenClaw `IDENTITY.md` |
| `host_render_strategy` | string | 渲染策略 |
| `authority_source` | string | 当前固定为 `database` |
| `notes` | string/null | 备注 |
| `updated_at` | datetime | 更新时间 |

### 4.6 Prompt 渲染预览响应 `ManagedAgentPromptRenderPreviewResponse`

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

### 4.7 定时任务响应 `ManagedAgentScheduleResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 定时任务 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `name` | string | 定时任务名称 |
| `enabled` | bool | 是否启用 |
| `schedule_type` | string | `interval / cron` |
| `schedule_expr` | string | 间隔值或 5 段 cron 表达式 |
| `timeout_seconds` | int | 超时秒数 |
| `model_override` | string/null | 模型覆盖，当前仍保留字段但不建议作为主配置使用 |
| `execution_options_json` | string/null | 宿主侧执行选项 JSON |
| `schedule_message_content` | string | 定时唤醒提示词 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 4.8 宿主通讯渠道响应 `ManagedAgentCommBindingResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 绑定 ID |
| `managed_agent_id` | string | 所属配置态 Agent ID |
| `provider` | string | 渠道类型。枚举预留为 `feishu / slack / telegram / wechat / email / webhook`，但当前真实落地仅支持 `openclaw + feishu` |
| `binding_key` | string | 平台账号或连接标识 |
| `display_name` | string/null | 展示名 |
| `enabled` | bool | 是否启用 |
| `routing_policy_json` | string/null | 路由策略 JSON |
| `metadata_json` | string/null | 非敏感补充信息 JSON |
| `config_payload_masked` | string/null | 脱敏后的配置文本 |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

### 4.9 Bootstrap Token 响应

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

### 4.10 Feishu 结构化通讯绑定响应 `FeishuCommBindingResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 绑定 ID |
| `provider` | string | 固定为 `feishu` |
| `account_id` | string | OpenClaw 内部账号标识（映射自通用表 `binding_key`） |
| `account_name` | string/null | 展示名（映射自通用表 `display_name`） |
| `enabled` | bool | 是否启用 |
| `app_id_masked` | string | 飞书 App ID（原值返回，不脱敏） |
| `app_secret_masked` | string | 飞书 App Secret（固定返回 `***`） |
| `created_at` | datetime | 创建时间 |
| `updated_at` | datetime | 更新时间 |

说明：

- 该响应体仅用于 Feishu 结构化接口（`comm-bindings-structured/feishu`），不影响通用 `comm-bindings` 接口的返回格式。
- `app_secret_masked` 始终为 `***`，不回显任何部分明文；`app_id_masked` 当前阶段返回原值。

---

## 5. 接口清单

### 5.1 获取当前支持的宿主平台能力

#### `GET /api/admin/managed-agents/meta/host-platforms`

作用：返回当前后端真实支持的宿主平台能力。前端应基于该接口决定可选宿主平台、部署模式、访问方式，以及是否展示 schedule、comm-binding、bootstrap 等能力入口。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentHostPlatformMetaResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |

#### 响应示例

```json
{
  "items": [
    {
      "key": "openclaw",
      "label": "OpenClaw",
      "description": "OpenClaw Agent 平台，当前 OpenMOSS 已落地支持的首个宿主平台。",
      "access_modes": ["local", "remote"],
      "deployment_modes": [
        "create_sub_agent",
        "bind_existing_agent",
        "bind_main_agent"
      ],
      "capabilities": {
        "renderer": true,
        "bootstrap_script": true,
        "skill_bundle": true,
        "prompt_preview": true,
        "schedule": true,
        "comm_binding": true
      },
      "supported_comm_providers": ["feishu"],
      "ui_hints": {
        "host_config": {
          "description": "配置此 Agent 在 OpenClaw 平台上的运行参数。",
          "fields": [
            {
              "key": "host_agent_identifier",
              "label": "Agent ID",
              "type": "text",
              "placeholder": "content-executor-01",
              "description": "OpenClaw 中的系统唯一标识。仅限英文小写字母、数字、下划线和连字符（a-z 0-9 _ -），首字符为字母或数字，最长 64 位。合法示例：content-executor-01、review-agent-01。",
              "required": true,
              "group": "基本"
            },
            {
              "key": "workdir_path",
              "label": "工作空间（Workspace）",
              "type": "text",
              "placeholder": "~/.openclaw/workspace-{Agent ID}",
              "description": "Agent 的专属文件空间，也是默认的文件操作目录，用于存放提示词（AGENTS.md/SOUL.md）、记忆、技能和任务产出。通常为 ~/.openclaw/workspace-{Agent ID}，留空时将根据 Agent ID 自动生成。",
              "required": false,
              "group": "基本"
            },
            {
              "key": "host_config_payload",
              "label": "平台配置数据",
              "type": "textarea",
              "description": "除标准字段外的宿主平台扩展配置。留空表示不修改现有值；输入新内容会替换旧值，保存后仅返回脱敏结果。",
              "required": false,
              "sensitive": true,
              "group": "高级"
            },
            {
              "key": "host_metadata_json",
              "label": "扩展元数据",
              "type": "json",
              "placeholder": "{}",
              "description": "平台侧的额外元数据，JSON 格式。",
              "required": false,
              "group": "高级"
            }
          ]
        },
        "prompt": {
          "description": "定义 Agent 在 OpenClaw Workspace 中的工作规则、人格设定和身份信息。这些内容都是可选配置，保存后会渲染为 AGENTS.md、SOUL.md、IDENTITY.md。",
          "render_strategies": [
            {
              "value": "openclaw_workspace_files",
              "label": "Workspace 文件",
              "description": "渲染为 OpenClaw Workspace 文件：AGENTS.md、SOUL.md、IDENTITY.md。",
              "is_default": true
            }
          ],
          "sections": [
            {
              "key": "system_prompt_content",
              "label": "工作规则（AGENTS.md）",
              "placeholder": "填写 Agent 的工作流程、工具使用规则和协作约束。",
              "required": false,
              "description": "定义 Agent 的工作规则和执行流程。",
              "detail": "对应 OpenClaw Workspace 中的 AGENTS.md。用于描述 Agent 的操作手册，包括工作流程、安全边界、工具使用规则、记忆策略和协作约束。这是最核心的行为规则文件，可根据实际情况决定是否添加或修改。"
            },
            {
              "key": "persona_prompt_content",
              "label": "人格设定（SOUL.md）",
              "placeholder": "填写 Agent 的性格、语气和沟通风格。",
              "required": false,
              "description": "定义 Agent 的性格和说话风格。",
              "detail": "对应 OpenClaw Workspace 中的 SOUL.md。用于描述 Agent 的语气、态度、个性和与用户的关系边界，决定 Agent 是偏工具化还是更有独立个性。"
            },
            {
              "key": "identity_content",
              "label": "身份信息（IDENTITY.md）",
              "placeholder": "填写 Agent 的名称、外显身份和展示信息。",
              "required": false,
              "description": "定义 Agent 的名称和外显身份。",
              "detail": "对应 OpenClaw Workspace 中的 IDENTITY.md。用于描述 Agent 的名字、emoji、头像等对外展示信息，比人格设定更轻量，主要用于标识而非行为规则。"
            }
          ]
        },
        "schedule": {
          "description": "配置 OpenClaw Agent 的定时唤醒任务。定时任务不是部署必填项，但一旦创建就应一次性提交完整配置。",
          "supported_types": ["interval", "cron"],
          "default_expr": "15m",
          "default_timeout": 1800,
          "required_fields": [
            "schedule_type",
            "schedule_expr",
            "timeout_seconds",
            "schedule_message_content"
          ],
          "expr_help": {
            "interval": "间隔格式：数字 + 单位，单位支持 s/m/h/d，例如 15m、1h、2d。",
            "cron": "cron 格式：标准 5 段表达式，例如 0 9 * * *。"
          },
          "message_label": "定时唤醒提示词"
        },
        "comm": {
          "description": "配置宿主平台侧通讯渠道。当前后端只落地 Feishu，其他 provider 仍是预留枚举。"
        },
        "bootstrap": {
          "description": "生成 OpenClaw 接入脚本、注册 token 和 skill-bundle 下载入口。",
          "deploy_guide": "将生成的脚本复制到 OpenClaw 部署机器执行，完成 Agent 文件写入和运行态注册。",
          "onboarding_guide": "接入说明会生成带一次性 bootstrap token 的 curl 命令，token 过期后需要重新生成。"
        }
      }
    }
  ]
}
```

### 5.1.1 获取 Prompt 模板示例

#### `GET /api/admin/managed-agents/meta/prompt-templates`

作用：返回 Agent 管理域当前可用的角色 Prompt 模板示例，供前端做“一键填充示例”或“按角色载入默认内容”。该接口只是读取当前仓库中的模板文件，不代表重新启用旧 Prompt 管理作为 Agent Prompt 主入口。

#### Query 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `role` | string | 否 | - | 按角色过滤，支持 `planner / executor / reviewer / patrol` |

#### 成功返回

- 状态码：`200`
- 返回体：对象，字段如下

| 字段 | 类型 | 说明 |
|---|---|---|
| `items` | array | 模板示例列表 |

`items[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `role` | string | 模板角色 |
| `label` | string | 角色展示名 |
| `filename` | string | 当前命中的模板文件名，兼容 `{role}.md` / `task-{role}.md` |
| `content` | string | 模板原文内容 |

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `422` | `role` 不在允许枚举中 |

#### 响应示例

```json
{
  "items": [
    {
      "role": "executor",
      "label": "任务执行者",
      "filename": "executor.md",
      "content": "# 角色：任务执行者（Task Executor）\n\n## 身份\n\n你是一个任务执行者..."
    }
  ]
}
```

补充说明：

- 前端默认应始终传 `role`，正常填充示例场景下只需要当前 Agent 角色对应的那一条模板。
- 不传 `role` 时会返回当前仓库中所有可用的角色模板示例，这个行为更适合内部调试或模板管理场景，不建议前端默认使用。
- 该接口适合给前端填充 `AGENTS.md` 示例内容，也可以作为定时唤醒提示词的参考模版来源。
- 模板文件继续保留在 `prompts/templates/*`，当前没有删除。

### 5.2 分页获取配置态 Agent 列表

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
      "name": "内容执行 Agent",
      "slug": "content-executor-01",
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
      "readiness": {
        "host_config": true,
        "prompt_asset": false,
        "schedules_count": 2,
        "comm_bindings_count": 0,
        "deploy_ready": false
      },
      "runtime_identity": {
        "registered": false,
        "runtime_agent_id": null,
        "api_key_masked": null
      },
      "created_at": "2026-04-03T12:00:00",
      "updated_at": "2026-04-03T12:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### 5.3 创建配置态 Agent

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

补充说明：

- 新建配置态 Agent 时，`config_version` 初始为 `1`
- 返回体会包含 `readiness`；如果创建请求已提供 `host_agent_identifier` 或 `workdir_path`，则 `readiness.host_config = true`
- 在首次部署成功前，反复修改配置不会持续递增版本号
- 首次部署成功后，再次修改配置时，`config_version` 才会推进到新的待部署版本

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 例如 slug 冲突，错误信息示例：`slug 'content-executor-01' 已被使用` |
| `403` | 管理员鉴权失败 |
| `422` | 请求体字段缺失或格式不合法 |

#### 请求示例

```json
{
  "name": "内容执行 Agent",
  "slug": "content-executor-01",
  "role": "executor",
  "description": "内容执行 Agent",
  "host_platform": "openclaw",
  "deployment_mode": "create_sub_agent",
  "host_access_mode": "local",
  "host_agent_identifier": "content-executor-01",
  "workdir_path": "~/.openclaw/workspace-content-executor-01"
}
```

### 5.4 获取配置态 Agent 详情

#### `GET /api/admin/managed-agents/{agent_id}`

作用：获取单个配置态 Agent 的基础详情。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentDetail`

补充说明：

- 返回体会包含后端统一计算的 `readiness`，前端详情页不需要再额外请求子资源探测配置完整度。

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |

### 5.5 更新配置态 Agent 基础信息

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

### 5.6 重置运行态 API Key

#### `POST /api/admin/managed-agents/{agent_id}/runtime-api-key/reset`

作用：重置当前配置态 Agent 关联运行态 Agent 的长期身份凭证。该接口仅在重置成功当次返回完整新 `api_key`；详情接口只返回脱敏后的 `runtime_identity.api_key_masked`。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`200`
- 返回体：

```json
{
  "runtime_agent_id": "runtime-agent-id",
  "api_key": "ak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "api_key_masked": "ak_x***xx",
  "message": "API Key 已重置，请立即复制，关闭后不可再次查看完整值"
}
```

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | 配置态 Agent 或关联运行态 Agent 不存在 |
| `409` | 配置态 Agent 尚未完成运行态注册，无法重置 |

### 5.7 删除配置态 Agent

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

### 5.8 获取宿主平台配置

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

### 5.9 更新宿主平台配置

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

### 5.10 获取 Prompt 资产

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

### 5.11 更新 Prompt 资产

#### `PUT /api/admin/managed-agents/{agent_id}/prompt-asset`

作用：更新 OpenClaw 工作规则、人格设定、身份信息三段可选 Prompt 文件内容。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `system_prompt_content` | string/null | 否 | 工作规则内容，对应 OpenClaw `AGENTS.md` |
| `persona_prompt_content` | string/null | 否 | 人格设定内容，对应 OpenClaw `SOUL.md` |
| `identity_content` | string/null | 否 | 身份信息内容，对应 OpenClaw `IDENTITY.md` |
| `host_render_strategy` | string/null | 否 | 渲染策略。OpenClaw 前端当前只暴露 `openclaw_workspace_files`；`host_default / openclaw_inline_schedule` 仅作为后端兼容枚举保留 |
| `notes` | string/null | 否 | 内部备注 |

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentPromptAssetResponse`

### 5.12 从模板重置 Prompt 资产

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

### 5.13 预览 Prompt 渲染结果

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
      "content": "这里是工作规则内容"
    },
    {
      "name": "SOUL.md",
      "content": "这里是人格设定内容"
    },
    {
      "name": "IDENTITY.md",
      "content": "这里是身份信息内容"
    }
  ]
}
```

### 5.14 获取定时任务列表

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

### 5.15 创建定时任务

#### `POST /api/admin/managed-agents/{agent_id}/schedules`

作用：创建定时任务。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `name` | string | 是 | 定时任务名称 |
| `enabled` | bool | 否 | 是否启用，默认 `true` |
| `schedule_type` | string | 是 | `interval / cron` |
| `schedule_expr` | string | 是 | 间隔值或 5 段 cron 表达式。`interval` 支持 `15m`、`1h`、`2d`；`cron` 支持 `0 9 * * *` 这类标准 5 段 cron |
| `timeout_seconds` | int | 是 | 超时秒数，最小 `60` |
| `model_override` | string/null | 否 | 模型覆盖 |
| `execution_options_json` | string/null | 否 | 宿主执行选项 JSON |
| `schedule_message_content` | string | 是 | 定时唤醒提示词，支持多行文本 |

说明：

- 前端可以分步填写，但提交创建接口时应一次性提交完整 schedule。
- `schedule_message_content` 不能为空白字符串。

#### 成功返回

- 状态码：`201`
- 返回体：`ManagedAgentScheduleResponse`

### 5.16 更新定时任务

#### `PUT /api/admin/managed-agents/{agent_id}/schedules/{schedule_id}`

作用：更新定时任务。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |
| `schedule_id` | string | 是 | 定时任务 ID |

#### 请求体

支持部分更新，但更新后的整条 schedule 仍必须保持完整可用。

例如：

- 可以只改 `name`
- 可以只改 `model_override`
- 不允许把 `schedule_message_content` 清空
- 如果只改 `schedule_type`，则必须保证与当前或本次提交的 `schedule_expr` 仍然匹配

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentScheduleResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | `schedule_expr` 与 `schedule_type` 不匹配、`schedule_message_content` 为空白，或其他业务错误 |
| `403` | 管理员鉴权失败 |
| `404` | 定时任务不属于该 Agent |
| `422` | 创建时缺少必填字段，或更新时显式传 `null` 给必填字段 |

### 5.17 删除定时任务

#### `DELETE /api/admin/managed-agents/{agent_id}/schedules/{schedule_id}`

作用：删除定时任务。

#### 成功返回

- 状态码：`204`
- 返回体：空

### 5.18 获取宿主通讯渠道配置列表

#### `GET /api/admin/managed-agents/{agent_id}/comm-bindings`

作用：获取某个 Agent 在宿主平台上的通讯渠道配置列表。

#### 成功返回

- 状态码：`200`
- 返回体：`ManagedAgentCommBindingResponse[]`

### 5.19 创建宿主通讯渠道配置

#### `POST /api/admin/managed-agents/{agent_id}/comm-bindings`

作用：新增一条宿主通讯渠道配置。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `provider` | string | 是 | 渠道类型。枚举预留为 `feishu / slack / telegram / wechat / email / webhook`，但当前真实落地仅支持 `openclaw + feishu` |
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
| `400` | `provider` 或 `binding_key` 为空等业务错误；当前脚本生成真实支持的 provider 仅为 `feishu` |
| `403` | 管理员鉴权失败 |

### 5.20 更新宿主通讯渠道配置

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

### 5.21 删除宿主通讯渠道配置

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

### 5.22 创建 Bootstrap Token

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

补充说明：

- 该接口属于“手动新建”，每次调用都会创建一条新的 Bootstrap Token 记录。
- 自动生成脚本 / 接入说明时使用的“同 scope 优先复用”规则，仅作用于 `bootstrap-script / onboarding-message` 两个接口。

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

### 5.23 获取 Bootstrap Token 列表

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

### 5.24 撤销 Bootstrap Token

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

### 5.25 获取 Bootstrap 脚本预览

#### `GET /api/admin/managed-agents/{agent_id}/bootstrap-script`

作用：为当前配置态 Agent 生成一份完整的 Bootstrap 脚本预览。接口会内部创建一个短期 `register_runtime` token，并直接嵌入脚本文本；脚本里用于下载 Skill Bundle 的 `download_script` token 会按同 scope 优先复用。

#### Query 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|
| `selected_artifacts` | string[] | 否 | 全部或按渲染策略默认值 | 允许重复传参，控制是否写入 `AGENTS.md / SOUL.md / IDENTITY.md` |
| `include_schedule` | bool | 否 | `true` | 是否包含定时任务片段 |
| `include_comm_bindings` | bool | 否 | `true` | 是否包含宿主通讯渠道片段 |
| `register_ttl_seconds` | int | 否 | `3600` | 内嵌 `register_runtime` token 的有效期 |
| `bundle_ttl_seconds` | int | 否 | `86400` | 脚本内嵌的 Skill Bundle 下载 token 总有效期 |

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

补充说明：

- `register_runtime` token 仍按每次“生成脚本预览”单独新建，默认 1 小时、一次性使用。
- `download_script` token 会按 `selected_artifacts + include_schedule + include_comm_bindings` 组成的 scope 查找可复用记录。
- 若存在同 scope 且剩余有效期大于 1 小时的 `download_script` token，系统会复用该记录，不新增列表项。
- 若同 scope token 已临近过期（剩余时间小于等于 1 小时）或不存在，则创建新记录。
- 由于服务端只存 `token_hash`，复用时会重新签发该记录对应的明文 token；因此再次生成后的脚本应以最新返回结果为准，旧脚本文本中的下载 token 会失效。

### 5.26 获取接入说明和 curl 命令

#### `GET /api/admin/managed-agents/{agent_id}/onboarding-message`

作用：生成一段可以直接发给用户或远端 Agent 的接入说明文本，同时内部获取一个 `download_script` token 并返回对应的 `curl` 命令。

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
| `download_token_id` | string | 当前使用的 `download_script` token ID；可能是复用记录，也可能是新建记录 |
| `download_token_expires_at` | datetime | 该 token 的过期时间 |

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 例如脚本范围参数不合法 |
| `403` | 管理员鉴权失败 |
| `404` | 配置态 Agent 不存在 |
| `422` | Query 参数格式错误 |

补充说明：

- `download_script` token 默认总有效期为 24 小时。
- 该接口会按 scope 优先复用同一条健康的 `download_script` 记录；scope 规则与“获取 Bootstrap 脚本预览”一致。
- 若存在同 scope 且剩余有效期大于 1 小时的 token，则返回同一条记录的 `download_token_id`，不会新增列表项。
- 若同 scope token 已临近过期（剩余时间小于等于 1 小时）或不存在，则创建新记录。
- 由于服务端只存 `token_hash`，复用时会重新签发该记录对应的明文 token；因此再次生成接入说明后，应以最新 `curl_command` 为准，旧命令中的下载 token 会失效。

### 5.27 获取 Feishu 通讯绑定 Schema

#### `GET /api/admin/managed-agents/meta/host-platforms/openclaw/comm-providers/feishu/schema`

作用：返回 Feishu 通讯绑定的字段定义（能力发现），供前端动态渲染表单。

#### 成功返回

- 状态码：`200`
- 返回体：

| 字段 | 类型 | 说明 |
|---|---|---|
| `provider` | string | `feishu` |
| `label` | string | 展示名 |
| `description` | string | 功能说明 |
| `supports_multiple_bindings` | bool | 是否支持同一 Agent 绑定多个账号 |
| `fields` | array | 字段定义列表 |

`fields[]` 字段说明：

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` | string | 字段标识 |
| `label` | string | 展示标签 |
| `type` | string | 控件类型：`text / password / switch` |
| `required` | bool | 是否必填 |
| `placeholder` | string/null | 占位提示 |
| `description` | string/null | 帮助说明 |
| `sensitive` | bool/null | 是否敏感字段 |
| `default` | any/null | 默认值 |
| `advanced` | bool/null | 是否建议放入高级区域 |

#### 响应示例

```json
{
  "provider": "feishu",
  "label": "飞书（Feishu）",
  "description": "为 Agent 配置飞书通讯渠道。绑定后即可在飞书中与该 Agent 对话，Agent 通过飞书机器人自动收发消息。支持绑定多个飞书账号，对应不同的飞书应用。",
  "supports_multiple_bindings": true,
  "fields": [
    {
      "key": "account_id",
      "label": "OpenClaw 内部账号标识",
      "type": "text",
      "required": false,
      "advanced": true,
      "placeholder": "留空自动生成（推荐）",
      "description": "OpenClaw 中用于标识这条飞书机器人账号配置的内部 key。对应的账号配置会在 OpenClaw 中保存该机器人的 app_id、app_secret 等信息。它不是飞书官方账号 ID，也不是在飞书侧看到的名称，而是 OpenClaw 内部用来区分、存储和引用这条飞书机器人配置的键。留空时系统会根据当前 Agent 的 OpenClaw Agent ID 自动生成。"
    },
    {
      "key": "app_id",
      "label": "飞书 App ID",
      "type": "text",
      "required": true,
      "placeholder": "cli_xxxxxxxxxxxx",
      "description": "飞书开放平台的应用凭证，可在「凭证与基础信息」页面获取。"
    },
    {
      "key": "app_secret",
      "label": "飞书 App Secret",
      "type": "password",
      "required": true,
      "sensitive": true,
      "placeholder": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      "description": "飞书应用密钥，与 App ID 配对使用，可在「凭证与基础信息」页面获取。提交后加密存储。"
    },
    {
      "key": "account_name",
      "label": "账号备注名",
      "type": "text",
      "required": false,
      "placeholder": "我的飞书助手",
      "description": "给 OpenClaw 配置中这条飞书账号写的备注名。主要用于自己识别和管理，不是功能性参数；可能会在部分界面展示，但不保证处处显示，不填也不影响飞书绑定本身。"
    },
    {"key": "enabled", "label": "是否启用", "type": "switch", "required": false, "default": true}
  ]
}
```

### 5.28 预校验 Feishu 通讯绑定

#### `POST /api/admin/managed-agents/meta/host-platforms/openclaw/comm-providers/feishu/validate`

作用：在正式提交创建之前，预校验 Feishu 绑定参数。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `account_id` | string | 否 | OpenClaw 内部账号标识；可不传，留空时后端会按 `{host_agent_identifier}-feishu` 自动生成建议值并用于创建 |
| `app_id` | string | 否 | 飞书 App ID |
| `app_secret` | string | 否 | 飞书 App Secret |
| `account_name` | string/null | 否 | 账号备注名 |
| `enabled` | bool | 否 | 是否启用 |

#### 成功返回

- 状态码：`200`
- 返回体：

| 字段 | 类型 | 说明 |
|---|---|---|
| `valid` | bool | 是否通过校验 |
| `errors` | string[] | 不通过时的错误列表 |

#### 响应示例

```json
{"valid": false, "errors": ["app_id 不能为空", "app_secret 不能为空"]}
```

### 5.29 获取 Feishu 通讯绑定建议默认值

#### `GET /api/admin/managed-agents/{agent_id}/comm-bindings-structured/feishu/suggest`

作用：为“新建 Feishu 绑定”表单返回建议默认值，主要用于自动填充 `account_id`。该接口不会保留或锁定该值，正式创建时后端仍会再次做唯一性校验。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`200`
- 返回体：`FeishuCommSuggestResponse`

| 字段 | 类型 | 说明 |
|---|---|---|
| `account_id` | string/null | 建议的 OpenClaw 内部账号标识；如果当前无法生成则为 `null` |
| `host_agent_identifier` | string/null | 当前 Agent 的 OpenClaw Agent ID |
| `message` | string/null | 无法生成时的提示信息 |

#### 响应示例

已配置 `host_agent_identifier`：

```json
{
  "account_id": "xiaohui-feishu",
  "host_agent_identifier": "xiaohui",
  "message": null
}
```

未配置 `host_agent_identifier`：

```json
{
  "account_id": null,
  "host_agent_identifier": null,
  "message": "当前 Agent 尚未配置 OpenClaw Agent ID，无法自动生成飞书账号标识。请先完成平台配置。"
}
```

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |

### 5.30 列出 Feishu 结构化通讯绑定

#### `GET /api/admin/managed-agents/{agent_id}/comm-bindings-structured/feishu`

作用：列出该 Agent 下的 Feishu 通讯绑定，返回结构化 DTO 而非通用表字段。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |

#### 成功返回

- 状态码：`200`
- 返回体：`FeishuCommBindingResponse[]`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |

### 5.31 创建 Feishu 结构化通讯绑定

#### `POST /api/admin/managed-agents/{agent_id}/comm-bindings-structured/feishu`

作用：为 Agent 创建一条 Feishu 通讯绑定。前端只需提交 Feishu 语义字段，`provider` 由路由隐含，`binding_key` 由后端从 `account_id` 映射；如果未传 `account_id`，后端会基于当前 Agent 的 `host_agent_identifier` 自动生成。

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `account_id` | string/null | 否 | OpenClaw 内部账号标识，映射到通用表 `binding_key`；留空时后端自动生成 |
| `app_id` | string | 是 | 飞书 App ID |
| `app_secret` | string | 是 | 飞书 App Secret（敏感） |
| `account_name` | string/null | 否 | 账号备注名，映射到通用表 `display_name` |
| `enabled` | bool | 否 | 默认 `true` |

#### 成功返回

- 状态码：`201`
- 返回体：`FeishuCommBindingResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | `app_id` / `app_secret` 为空等校验错误；或未传 `account_id` 且当前 Agent 未配置 `host_agent_identifier` |
| `403` | 管理员鉴权失败 |
| `404` | Agent 不存在 |
| `409` | 同 Agent 下已存在相同 `account_id` 的 Feishu 绑定 |

#### 请求示例

```json
{
  "app_id": "cli_a9348a45ebb8dbef",
  "app_secret": "<secret>",
  "account_name": "内容助手飞书",
  "enabled": true
}
```

补充说明：

- `account_id` 建议作为高级字段展示，普通用户通常不需要手填。
- 如果前端想提前展示默认值，建议先调用 `GET .../comm-bindings-structured/feishu/suggest` 获取建议值。
- 正式创建时后端仍会再次校验唯一性。

### 5.32 更新 Feishu 结构化通讯绑定

#### `PUT /api/admin/managed-agents/{agent_id}/comm-bindings-structured/feishu/{binding_id}`

作用：部分更新 Feishu 通讯绑定。只传需要修改的字段；未传的字段保持原值。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |
| `binding_id` | string | 是 | 绑定 ID |

#### 请求体

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `account_id` | string | 否 | 更新 OpenClaw 内部账号标识（高级字段） |
| `app_id` | string | 否 | 更新飞书 App ID |
| `app_secret` | string | 否 | 更新飞书 App Secret |
| `account_name` | string/null | 否 | 更新账号备注名 |
| `enabled` | bool | 否 | 更新启用状态 |

说明：

- `account_id` 支持通过此接口修改，但属于高级字段；如果修改，需要重新部署脚本才能在 OpenClaw 侧生效。
- 只更新 `app_secret` 时，后端会自动保留原有 `app_id`，反之亦然。

#### 成功返回

- 状态码：`200`
- 返回体：`FeishuCommBindingResponse`

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 校验错误（如字段为空白字符串），或该绑定不是 Feishu 类型 |
| `403` | 管理员鉴权失败 |
| `404` | 绑定不存在或不属于该 Agent |
| `409` | 修改后的 `account_id` 与同 Agent 下现有 Feishu 绑定冲突 |

### 5.33 删除 Feishu 结构化通讯绑定

#### `DELETE /api/admin/managed-agents/{agent_id}/comm-bindings-structured/feishu/{binding_id}`

作用：删除 Feishu 通讯绑定。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `agent_id` | string | 是 | 配置态 Agent ID |
| `binding_id` | string | 是 | 绑定 ID |

#### 成功返回

- 状态码：`204`
- 返回体：空

#### 错误码

| 状态码 | 说明 |
|---|---|
| `400` | 该绑定不是 Feishu 类型 |
| `403` | 管理员鉴权失败 |
| `404` | 绑定不存在或不属于该 Agent |
