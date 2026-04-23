# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common commands

### Backend setup and local run
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 6565 --reload
```

`app.config.AppConfig` reads `OPENMOSS_CONFIG` first, otherwise `config.yaml`. If the file is missing, it is copied from `config.example.yaml` on startup.

### Tests
```bash
pytest
pytest -q
pytest tests/test_health.py -q
pytest tests/api/test_bootstrap.py -q
pytest tests/services/test_pack_skills.py -q
pytest path/to/test_file.py::test_name -q
```

`pytest.ini` sets `testpaths = tests` and `asyncio_mode = auto`.

### Docker
```bash
docker build -t openmoss .
docker compose up -d --build
docker compose logs -f
docker compose down
```

### Skill packaging / CLI work
```bash
python skills/pack-skills.py
pytest tests/services/test_task_cli_app.py -q
pytest tests/services/test_task_cli_registry.py -q
pytest tests/services/test_pack_skills.py -q
```

### Frontend note
The current `main` / `dev` branch does **not** contain the Vue source. It only serves compiled assets from `static/`. Frontend source lives on the separate `webui` orphan branch; `npm run dev`, `npm run build`, and `npm run lint` only apply there.

### Lint note
There is no root Python lint/format command configured in this branch. Do not invent one. The README only documents `npm run lint` for the separate `webui` branch.

## Architecture overview

### 1. App entrypoint and startup behavior
- `app/main.py` creates the FastAPI app, mounts all `/api` routers, then serves the SPA from `static/` for non-API routes.
- Startup does more than just boot FastAPI:
  - `app/database.py:init_db()` creates tables and seeds `rules/global-rule-example.md`
  - `app.services.managed_agent.auto_backfill_from_runtime(...)` syncs older runtime agents into the newer config-center model
  - expired `request_log` rows are deleted based on `webui.feed_retention_days`
  - `app/services/webui_updater.py` downloads `static/` from GitHub Releases if the WebUI build is missing

### 2. Auth model
- Agent-facing APIs use `Authorization: Bearer <api_key>` (`app/auth/dependencies.py`).
- Admin APIs use `X-Admin-Token` (`app/routers/admin/auth.py`).
- Admin tokens are stored in memory only, so all admin sessions are invalidated on process restart.

### 3. Core task domain
- The main workflow is `Task -> Module -> SubTask`.
- Core stateful logic lives in `app/services/task_core/`, not routers:
  - `task.py`
  - `sub_task.py`
  - `review.py`
  - `reward.py`
  - `rule.py`
- `app/services/task_core/sub_task.py` is the key state machine. It enforces transitions like `pending -> assigned -> in_progress -> review -> done`, with `rework` and `blocked` side paths.
- `app/services/task_core/review.py` is intentionally transactional: it writes the review record, changes sub-task state, and applies score changes in one transaction.

### 4. Logging and feed pipeline
- `app/middleware/request_logger.py` records authenticated agent `/api/*` requests into `request_log`.
- Admin requests and unauthenticated requests are intentionally skipped.
- The activity feed / audit-style views depend on this middleware, so auth/header changes can accidentally break feed visibility.

### 5. Config and persistence
- `app/config/` owns YAML config loading, partial updates, initialization flow, and automatic admin password upgrade to bcrypt.
- Formal runtime support is currently SQLite only; `AppConfig.database_url` raises on other DB types.
- `app/database.py` also performs silent Agent status migration on startup.

### 6. Managed-agent / configuration-center subsystem
This repo has **two related Agent concepts**:

- runtime agents: `app/models/agent.py`
- config-state agents: `app/models/managed_agent.py`

The newer managed-agent subsystem is the configuration center used by the admin UI and bootstrap flow:

- admin APIs live in `app/routers/admin/managed_agents/` (9-file subpackage)
- core logic lives in `app/services/managed_agent/`

Bootstrap flow spans multiple layers:

1. admin creates or updates a managed agent
2. a bootstrap token is created
3. `app/services/bootstrap/` renders a shell script using:
   - host renderers in `app/services/host_renderers/`
   - shell templates in `shells/templates/`
4. the target runtime executes the script
5. `/api/bootstrap/agents/{id}/register` creates a runtime `Agent` and links it back to `ManagedAgent.runtime_agent_id`

When editing bootstrap/onboarding behavior, expect changes across schemas, admin router, bootstrap service, host renderer, and shell templates.

### 7. Skills and CLI distribution
- Role skills live under `skills/task-planner-skill/`, `skills/task-executor-skill/`, `skills/task-reviewer-skill/`, and `skills/task-patrol-skill/`.
- `skills/task-cli.py` is now a compatibility entrypoint; the shared implementation lives in `tools/task_cli/`.
- `python skills/pack-skills.py` builds distributable zip bundles in `skills/dist/` by combining:
  - role-specific files from each skill directory
  - shared CLI source from `tools/task_cli/`
- Edit the source directories, not `skills/dist/`.
- Relevant test coverage for this area is in `tests/services/test_task_cli_*` and `tests/services/test_pack_skills.py`.
- `/api/tools/cli` serves the latest CLI script with `BASE_URL` rewritten from current server config or request host.
- `/api/agents/me/skill` serves role-specific `SKILL.md` with the actual API key injected.

### 8. WebUI split
- On `main` / `dev`, this repo is the backend plus runtime `static/` assets.
- The Vue source is maintained separately on the `webui` orphan branch.
- If a task asks for frontend source changes and there is no `webui/` directory, that is expected.

### 9. Docs and source of truth
- `dev-docs/` contains design notes, drafts, and migration context; it is useful for intent but not always the final implementation.
- Prefer current code and tests over `dev-docs/` when they disagree.

## Development conventions

All Python code under `app/` must follow these conventions. See `dev-docs/开发规范.md` for full details, `dev-docs/全项目模块拆分规划.md` for the refactoring plan.

### Functional domains

The project is organized into 6 functional domains. Each domain is an independent unit that can be assigned to a separate developer/team.

| Domain | Purpose | Router | Service | Schema | Test |
|---|---|---|---|---|---|
| **agent-config** | Admin manages config-state Agents | `routers/admin/managed_agents/` | `services/managed_agent/` | `schemas/managed_agent/` | `test_managed_agents_api`, `test_deployment_service`, `test_host_renderers`, `test_migration_service` |
| **bootstrap-deploy** | Token, script rendering, registration | `routers/bootstrap_deploy/` | `services/bootstrap/` | (shared with agent-config) | `test_bootstrap`, `test_deploy_api`, `tests/services/bootstrap/*`, `test_skill_bundle_service` |
| **task-core** | Task assignment, sub-task state machine, review | `routers/task_core/` | `services/task_core/` | — | `test_tasks_api`, `test_sub_tasks_api`, `test_sub_task_service` |
| **admin-query** | Dashboard, stats, audit logs (read-only) | `routers/admin/dashboard.py`, `routers/admin/tasks.py`, etc. | `services/admin_query/` | `schemas/admin/` | `test_admin_query_exceptions`, `test_admin_query_task`, `test_admin_query_dashboard`, `test_admin_query_score` |
| **agent-runtime** | Agent-side: heartbeat, skill download, CLI | `routers/agent_runtime/` | `services/agent_service.py` | — | ✅ Good coverage |
| **infra** | Config, DB, auth, middleware, startup | `config/`, `database.py`, `auth/` | `services/pagination.py`, etc. | — | ✅ Basic coverage |

Cross-domain imports must go through the target domain's `__init__.py`. `infra` is a shared dependency for all domains.

### Domain-specific test commands

```bash
# agent-config
pytest tests/api/test_managed_agents_api.py tests/services/test_deployment_service.py tests/services/test_host_renderers.py tests/services/test_migration_service.py -q

# bootstrap-deploy
pytest tests/api/test_bootstrap.py tests/api/test_deploy_api.py tests/services/bootstrap tests/services/test_skill_bundle_service.py -q

# task-core
pytest tests/api/test_tasks_api.py tests/api/test_sub_tasks_api.py tests/services/test_sub_task_service.py -q

# admin-query
pytest tests/api/test_admin_query_exceptions.py tests/services/test_admin_query_*.py -q

# agent-runtime
pytest tests/api/test_agents_heartbeat_api.py tests/api/test_agents_skill_bundle_api.py tests/services/test_heartbeat.py tests/services/test_task_cli_*.py tests/services/test_pack_skills.py -q

# infra
pytest tests/test_health.py tests/test_database_init.py tests/services/test_schema_compat.py -q
```

### Files exceeding standards (need refactoring)

These files still exceed size limits. See `dev-docs/全项目模块拆分规划.md` for planned action:

| File | Lines | Limit | Domain | Planned action |
|---|---|---|---|---|
| `services/managed_agent/platforms/.../feishu.py` | 446 | 300 | agent-config | 随改随拆 |
| `services/webui_updater.py` | 431 | 300 | infra | 随改随拆 |

### Domain subpackage rule

Router / Service / Schema must be organized by functional domain subpackages. If a domain has 2+ files in a layer, those files must be in a domain subpackage. Model files stay as single files (organized by aggregate root).

Remaining layers not yet grouped into domain subpackages (planned in `dev-docs/全项目模块拆分规划.md`):

None at the moment. New scattered Router / Service / Schema files must be grouped into a domain subpackage before they grow further.

### File size guidelines

The primary rule is **organize by functional domain** (see above). Line counts are a secondary reference — when a file gets too long, consider splitting it within its domain subpackage:

| Layer | Consider splitting at | Typical range |
|---|---|---|
| Router file | ~300 lines | 50–250 |
| Service file | ~300 lines | 50–250 |
| Schema file | ~250 lines | 30–200 |
| Model file | ~250 lines | 20–200 |
| `__init__.py` | ~150 lines | 10–120 |

These are guidelines, not hard limits. A 310-line file with a clear single responsibility is fine. The goal is keeping code organized and readable, not enforcing arbitrary numbers.

### Layered architecture

```
Router  →  Service  →  Model
```

**Strict rules:**
- Routers **never** import models or do `db.query(...)` directly. They only call service functions.
- Services **never** import Pydantic Schemas. Function parameters use primitive types (`str`, `int`, `dict`).
- Services **never** import `fastapi`, `HTTPException`, or anything HTTP-related.
- Services raise `BusinessError` subclasses (`NotFoundError`, `ValidationError`, `ConflictError`, `ForbiddenError`). The router layer catches them and converts to `HTTPException`.
- Cross-service calls go through the package `__init__.py`, never direct submodule imports.

### Router function pattern

Every router function should do exactly three things:

```python
@router.post("/{id}/xxx", response_model=XxxResponse, status_code=201)
def create_xxx(id: str, req: XxxRequest, db: Session = Depends(get_db), _=Depends(verify_admin)):
    try:
        result = svc.create_xxx(db, id, **req.model_dump())
        return svc.serialize_xxx(result)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
```

### Subpackage conventions

**Rule: organize by functional domain, not by file size.** All Router/Service/Schema files belonging to a domain with 2+ files MUST be in a domain subpackage. Model files stay flat.

```
services/xxx/
├── __init__.py     # ONLY re-exports, zero business logic
├── core.py         # Main resource CRUD
├── feature_a.py    # Sub-feature
└── shared.py       # Internal helpers (NOT re-exported)
```

External modules import only from `__init__.py`:
```python
# Correct
from app.services.managed_agent import create_schedule

# Wrong — never import internal files directly
from app.services.managed_agent.schedule import create_schedule
```

### Exception hierarchy

```
BusinessError (400)
├── NotFoundError (404)
├── ValidationError (400)
├── ConflictError (409)
├── ForbiddenError (403)
└── AdminQueryError (400)
```

Services only raise these. Routers catch and convert to `HTTPException`.

### Naming conventions

| What | Pattern | Example |
|---|---|---|
| Service CRUD function | `create_xxx` / `get_xxx` / `update_xxx` / `delete_xxx` / `list_xxx` | `create_schedule(db, ...)` |
| Lookup-or-fail | `get_xxx_or_404(db, id)` | `get_managed_agent_or_404(db, id)` |
| Serializer | `serialize_xxx(row)` | `serialize_comm_binding(row)` |
| Test file | `test_{layer}_{domain}.py` | `test_deployment_service.py` |
| Test function | `test_{scenario}_{expected}` | `test_create_with_invalid_key_raises_error` |

### Import order

```python
# 1. Standard library
import json

# 2. Third-party
from fastapi import APIRouter

# 3. Project internals (grouped by layer)
from app.database import get_db
from app.exceptions import BusinessError
from app.services import managed_agent as svc
```

### Testing

- Service tests use `db_session` fixture (direct function calls, no HTTP)
- API tests use `client` + `admin_headers` fixtures (full HTTP round-trip)
- Each test function gets an isolated in-memory SQLite database
- Use `_create_xxx()` helper functions at the top of test files for setup

### Git and PR rules

- One PR per resource domain — changing schedules should not touch comm_binding code
- Refactoring PRs (file splits, import changes) must be separate from feature PRs
- Every PR must pass all existing tests before merge
