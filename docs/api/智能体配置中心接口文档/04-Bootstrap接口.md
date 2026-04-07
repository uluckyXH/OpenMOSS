# Bootstrap 接口

> 最后同步：2026-04-07
> 接口前缀：`/api/bootstrap`
> 对应代码：`app/routers/bootstrap.py`

## 1. 模块概览

当前已实现：

- 脚本下载
- 运行态注册闭环

当前未实现：

- `task-cli.py` 下载

## 2. 请求头

```http
X-Bootstrap-Token: <bootstrap_token>
Content-Type: application/json
```

## 3. 通用错误码

| 状态码 | 含义 | 说明 |
|---|---|---|
| `403` | Token 无效 | Token 已过期、已撤销、已使用或 purpose 不匹配 |
| `404` | 资源不存在 | 配置态 Agent 不存在 |
| `409` | 状态冲突 | 该配置态 Agent 已有运行态实例，或名称冲突 |
| `422` | 请求头缺失 | `X-Bootstrap-Token` 缺失 |

## 4. 已实现接口

### 4.1 下载部署脚本

#### `GET /api/bootstrap/agents/{managed_agent_id}/script`

作用：使用 `download_script` 类型的 Bootstrap Token 下载渲染后的完整部署脚本。服务端会在返回脚本前，临时创建一个短期 `register_runtime` token 并嵌入脚本。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `managed_agent_id` | string | 是 | 配置态 Agent ID |

#### Header

| Header | 必填 | 说明 |
|---|---|---|
| `X-Bootstrap-Token` | 是 | `download_script` 类型 token |

#### 成功返回

- 状态码：`200`
- 返回体：纯文本 shell 脚本

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | `X-Bootstrap-Token` 无效、已过期，或 purpose 不为 `download_script` |
| `404` | 配置态 Agent 不存在 |
| `422` | 缺少 `X-Bootstrap-Token` |

### 4.2 注册运行态 Agent

#### `POST /api/bootstrap/agents/{managed_agent_id}/register`

作用：使用 `register_runtime` 类型的 Bootstrap Token 完成运行态注册。

#### Path 参数

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `managed_agent_id` | string | 是 | 配置态 Agent ID |

#### Header

| Header | 必填 | 说明 |
|---|---|---|
| `X-Bootstrap-Token` | 是 | `register_runtime` 类型 token |

#### 成功返回

- 状态码：`201`

响应字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | string | 新创建的运行态 Agent ID |
| `name` | string | 运行态 Agent 名称，来自配置态 Agent |
| `role` | string | 运行态 Agent 角色，来自配置态 Agent |
| `api_key` | string | 新生成的长期身份凭证 |
| `message` | string | 固定提示消息 |

#### 错误码

| 状态码 | 说明 |
|---|---|
| `403` | `X-Bootstrap-Token` 无效或已过期 |
| `404` | 配置态 Agent 不存在 |
| `409` | 该配置态 Agent 已有运行态实例，或运行态名称冲突 |
| `422` | 缺少 `X-Bootstrap-Token` |

#### 响应示例

```json
{
  "id": "5b2d02e1-f28f-4f60-ae3a-57f6bb51f441",
  "name": "AI小灰",
  "role": "executor",
  "api_key": "ak_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "message": "Bootstrap 注册成功，请保存 API Key"
}
```

## 5. 当前未实现接口

- `GET /api/bootstrap/agents/{managed_agent_id}/task-cli?token=...`
