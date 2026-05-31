# OpenMOSS Cloudflare API Migration Checklist

目标：保持原 OpenMOSS WebUI 不重写，只把原 FastAPI 后端迁移到 Cloudflare Worker + D1。

## 已对接的 WebUI 关键接口

- Auth / Setup / WebUI
  - `POST /api/admin/login`
  - `GET /api/setup/status`
  - `POST /api/setup/initialize`
  - `GET /api/webui/version`
  - `GET /api/webui/version/check`
  - `POST /api/admin/webui/update`
- Dashboard / Admin
  - `GET /api/admin/config`
  - `PUT /api/admin/config`
  - `PUT /api/admin/config/password`
  - `GET /api/admin/dashboard/overview`
  - `GET /api/admin/dashboard/highlights`
  - `GET /api/admin/dashboard/trends`
- Managed Agents
  - `GET/POST /api/admin/managed-agents`
  - `GET/PUT/DELETE /api/admin/managed-agents/:id`
  - `POST /api/admin/managed-agents/:id/runtime-api-key/reset`
  - `GET/PUT /api/admin/managed-agents/:id/host-config`
  - `GET/POST /api/admin/managed-agents/:id/schedules`
  - `DELETE /api/admin/managed-agents/:id/schedules/:schedule_id`
  - `GET/POST /api/admin/managed-agents/:id/comm-bindings`
  - `GET/POST /api/admin/managed-agents/:id/bootstrap-tokens`
  - `GET /api/admin/managed-agents/:id/bootstrap-script`
  - `GET /api/admin/managed-agents/:id/onboarding-message`
  - `GET /api/admin/managed-agents/:id/deployment-state`
  - `POST /api/admin/managed-agents/:id/deploy-preview`
  - `POST /api/admin/managed-agents/:id/deploy-script`
  - `GET /api/admin/managed-agents/:id/deployment-snapshots`
  - `POST /api/admin/managed-agents/:id/deployment-snapshot/dismiss`
- Prompt / Rules
  - `GET/PUT /api/admin/prompts/templates/:role`
  - `GET/POST /api/admin/prompts/agents`
  - `GET/PUT/DELETE /api/admin/prompts/agents/:slug`
  - `GET /api/admin/prompts/compose/:slug`
  - `GET /api/admin/prompts/onboarding/:role`
  - `GET /api/rules`
  - `GET /api/rules/list`
  - `GET/PUT/DELETE /api/rules/:id`
  - `POST /api/rules`
- Admin data lists/details
  - `GET /api/admin/agents`, `/api/admin/agents/:id`
  - `GET /api/admin/tasks`, `/api/admin/tasks/:id`, `/api/admin/tasks/:id/modules`
  - `GET /api/admin/modules/:id`
  - `GET /api/admin/sub-tasks`, `/api/admin/sub-tasks/:id`
  - `GET /api/admin/scores/*`, `/api/admin/logs`, `/api/admin/review-records`
- Runtime API
  - `POST/GET/PUT /api/tasks*`
  - `POST/GET /api/sub-tasks*` plus `claim/start/submit/complete/rework/block/reassign/cancel/session`
  - `POST/GET /api/review-records*`
  - `POST/GET /api/logs*`
  - `GET/POST /api/scores*`
  - `GET /api/feed/*`
  - `GET /api/tools/cli`

## Cloudflare-specific notes

- Admin password for this demo build: `admin123`.
- Prompts and Managed Agent config are persisted in D1, not local files.
- Host deployment/bootstrap APIs return portable shell scripts/onboarding payloads instead of mutating a host filesystem directly.
- Pages serves the original WebUI build; Worker serves API compatibility layer.
