# 智能体配置中心接口文档

> 最后同步：2026-04-07
> 适用范围：智能体配置中心重构当前已落地后端接口
> 当前代码状态：已实现配置态 Agent 管理主链、Agent 心跳接口、Bootstrap Token 管理、脚本预览、接入说明和 Bootstrap 注册/脚本下载闭环；`task-cli.py` 下载尚未落地

## 1. 文档说明

本目录只记录**当前仓库中已经落地的接口**，不把设计稿中的未来接口混进来。

- 管理端配置态 Agent 接口：见 [01-管理端-配置态Agent接口.md](01-管理端-配置态Agent接口.md)
- Agent 侧运行态接口：见 [02-Agent侧运行态接口.md](02-Agent侧运行态接口.md)
- Bootstrap 接口：见 [04-Bootstrap接口.md](04-Bootstrap接口.md)
- 鉴权、错误码与字段约定：见 [03-鉴权与错误码说明.md](03-鉴权与错误码说明.md)

## 2. 当前已实现范围

### 2.1 管理端配置态 Agent

接口前缀：`/api/admin/managed-agents`

已实现接口：

- `GET /api/admin/managed-agents`
- `POST /api/admin/managed-agents`
- `GET /api/admin/managed-agents/{agent_id}`
- `PUT /api/admin/managed-agents/{agent_id}`
- `DELETE /api/admin/managed-agents/{agent_id}`
- `GET /api/admin/managed-agents/{agent_id}/host-config`
- `PUT /api/admin/managed-agents/{agent_id}/host-config`
- `GET /api/admin/managed-agents/{agent_id}/prompt-asset`
- `PUT /api/admin/managed-agents/{agent_id}/prompt-asset`
- `POST /api/admin/managed-agents/{agent_id}/prompt-asset/reset-from-template`
- `POST /api/admin/managed-agents/{agent_id}/prompt-asset/render-preview`
- `GET /api/admin/managed-agents/{agent_id}/schedules`
- `POST /api/admin/managed-agents/{agent_id}/schedules`
- `PUT /api/admin/managed-agents/{agent_id}/schedules/{schedule_id}`
- `DELETE /api/admin/managed-agents/{agent_id}/schedules/{schedule_id}`
- `GET /api/admin/managed-agents/{agent_id}/comm-bindings`
- `POST /api/admin/managed-agents/{agent_id}/comm-bindings`
- `PUT /api/admin/managed-agents/{agent_id}/comm-bindings/{binding_id}`
- `DELETE /api/admin/managed-agents/{agent_id}/comm-bindings/{binding_id}`
- `POST /api/admin/managed-agents/{agent_id}/bootstrap-tokens`
- `GET /api/admin/managed-agents/{agent_id}/bootstrap-tokens`
- `DELETE /api/admin/managed-agents/{agent_id}/bootstrap-tokens/{token_id}`
- `GET /api/admin/managed-agents/{agent_id}/bootstrap-script`
- `GET /api/admin/managed-agents/{agent_id}/onboarding-message`

### 2.2 Agent 侧运行态接口

接口前缀：`/api/agents`

已实现接口：

- `POST /api/agents/register`
- `POST /api/agents`
- `GET /api/agents`
- `PUT /api/agents/{agent_id}/status`
- `POST /api/agents/me/heartbeat`
- `GET /api/agents/me/skill`

### 2.3 Bootstrap 接口

接口前缀：`/api/bootstrap`

已实现接口：

- `GET /api/bootstrap/agents/{managed_agent_id}/script`
- `POST /api/bootstrap/agents/{managed_agent_id}/register`

## 3. 当前未实现但设计中已预留的接口

以下接口**在设计文档中存在，但当前代码里还没有实现**：

- `GET /api/bootstrap/agents/{id}/task-cli?token=...`

这些接口暂时不要拿来对接前端或对外文档。

## 4. 使用建议

- 当前管理端接口已经适合用于后端联调、前端页面开发和 Postman 调试。
- 当前错误码仍存在少量 `400` / `404` 口径不完全统一的情况，文档已按**当前真实实现**记录，不按理想态推断。
- 敏感配置字段目前返回的是脱敏值，不会直接回显明文。
