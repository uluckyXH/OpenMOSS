# task_cli README

> 更新时间：2026-04-08

`tools/task_cli/` 是 OpenMOSS 后续 `task-cli.py` 的共享源码目录。
这里主要负责两件事：

- 承接 `task-cli.py` 的源码拆分
- 记录 `task-cli` 模块化改造进度

旧 [task-cli.py](/Volumes/MacSSD/Repositories/OpenMOSS/skills/task-cli.py) 的公共逻辑会逐步迁到这里，最后再收成兼容入口，不会直接丢弃。

## 1. 目录说明

```text
tools/
  task_cli/                     # task-cli 共享源码根目录
    README.md                   # 目录说明 + 开发进度
    __init__.py                 # 包入口
    main.py                     # CLI 入口与 argparse 装配
    runtime.py                  # BASE_URL、API Key、角色等运行时配置
    http.py                     # 请求发送、Header、错误处理
    output.py                   # JSON、分页、终端输出
    command_registry.py         # 命令注册表与 help 元信息
    commands/                   # 各命令域实现
      __init__.py
    profiles/                   # planner/executor/reviewer/patrol 的 help/profile
      __init__.py
    templates/                  # 后续给 Agent 渲染入口文件与 Skill 包模板
      .gitkeep
```

## 2. 模块作用

| 模块 | 作用 |
|---|---|
| `main.py` | CLI 总入口，负责挂载命令和输出 help |
| `runtime.py` | 默认配置和运行时上下文 |
| `http.py` | 请求封装、Header、错误处理 |
| `output.py` | JSON、列表、分页、终端输出 |
| `command_registry.py` | 命令元信息和 help 来源 |
| `commands/` | 各命令域实现 |
| `profiles/` | 不同角色的命令可见性和帮助信息 |
| `templates/` | Agent 专属入口文件与 Skill 包模板 |

## 3. 当前开发进度

### A. 目录骨架

#### A-1. 基础目录

- [x] 已建立 `tools/task_cli/`
- [x] 已建立 `commands/`
- [x] 已建立 `profiles/`
- [x] 已建立 `templates/`
- [x] 已建立本 README

#### A-2. 占位文件

- [x] 已建立 `__init__.py`
- [x] 已建立 `main.py`
- [x] 已建立 `runtime.py`
- [x] 已建立 `http.py`
- [x] 已建立 `output.py`
- [x] 已建立 `command_registry.py`
- [x] 已建立 `commands/__init__.py`
- [x] 已建立 `profiles/__init__.py`
- [x] 已建立 `templates/.gitkeep`

### B. 基础能力拆分

#### B-1. 运行时配置

- [x] 从旧 `skills/task-cli.py` 拆出 `BASE_URL`
- [x] 从旧 `skills/task-cli.py` 拆出 `CLI_VERSION`
- [x] 定义 `DEFAULT_API_KEY / AGENT_ID / AGENT_ROLE / CLI_PROFILE` 的运行时入口

#### B-2. HTTP 请求封装

- [x] 拆出 `_headers`
- [x] 拆出 `_request`
- [x] 统一错误输出

#### B-3. 输出封装

- [x] 拆出 `_print_json`
- [x] 拆出 `_extract_items`
- [x] 统一列表与分页输出

#### B-4. CLI 入口骨架

- [x] 在 `main.py` 建立 argparse 主入口
- [x] 建立统一子命令挂载入口
- [x] 暂不迁入具体命令逻辑

### C. 命令域拆分

#### C-1. 第一批命令域

- [x] `rules`
- [x] `tasks`
- [x] `sub_tasks`

#### C-2. 第二批命令域

- [x] `modules`
- [x] `reviews`
- [x] `scores`
- [x] `logs`

#### C-3. 第三批命令域

- [x] `notifications`
- [x] `agents`
- [ ] `admin`（旧 `task-cli.py` 暂无对应命令）

### D. 命令注册表与 Profile

#### D-1. 命令注册表

- [x] 定义 `COMMAND_REGISTRY`
- [x] 为现有命令补 `group / summary / visible_in_profiles`
- [x] 让 `help` 从注册表读取

#### D-2. 角色 Profile

- [x] 建立 `planner` Profile
- [x] 建立 `executor` Profile
- [x] 建立 `reviewer` Profile
- [x] 建立 `patrol` Profile
- [x] 让 `help` 按 Profile 输出

### E. 兼容入口与交付

#### E-1. 兼容入口

- [x] 让 `skills/task-cli.py` 收成兼容入口
- [x] 保持现有 `--key` 调用兼容
- [x] 不打断现有下载与打包链路

#### E-2. Skill 包标准化

- [x] 已为现有 4 个角色 Skill 建立 `scripts/`
- [x] 已为现有 4 个角色 Skill 建立 `scripts/task_cli/`
- [x] 已为现有 4 个角色 Skill 建立 `references/`
- [x] 已增加 `scripts/task-cli.py` 兼容占位入口
- [x] 已改造 `skills/pack-skills.py`，打包时注入共享 `task_cli` 源码
- [x] `SKILL.md` 已收口为更精简的 Skill 说明
- [x] 更细命令说明已下沉到 `references/`

#### E-3. Bootstrap 对接

- [x] 已增加 Agent 专属 `task-cli.py` 入口模板
- [x] 已增加 Agent 专属 `task-cli.py` 渲染
- [x] 已增加 `skill-bundle` 渲染服务
- [x] 已增加 `skill-bundle` 下载交付
- [x] Shell 已改为下载 Skill 包

## 4. 当前状态汇总

| 大模块 | 当前状态 |
|---|---|
| A. 目录骨架 | 已完成 |
| B. 基础能力拆分 | 已完成 |
| C. 命令域拆分 | 已完成（旧 CLI 现有命令域） |
| D. 命令注册表与 Profile | 已完成 |
| E. 兼容入口与交付 | 已完成（E-1/E-2/E-3 已完成） |

B 模块当前测试结果：

- `tests/services/test_task_cli_runtime.py` → `4 passed`
- `tests/services/test_task_cli_foundation.py` → `8 passed`
- `tests/services/test_task_cli_commands_c1.py` → `6 passed`
- `tests/services/test_task_cli_commands_c2.py` → `5 passed`
- `tests/services/test_task_cli_commands_c3.py` → `3 passed`
- `tests/services/test_task_cli_registry.py` → `4 passed`
- `tests/services/test_task_cli_profiles.py` → `5 passed`
- `tests/services/test_task_cli_app.py` → `5 passed`
- `tests/services/test_task_cli_launcher.py` → `2 passed`
- `tests/services/test_skill_bundle_service.py` → `2 passed`
- `tests/services/test_pack_skills.py` → `2 passed`

## 5. 下一步

当前已完成 `E-1. 兼容入口`、`E-2. Skill 包标准化` 和 `E-3. Bootstrap 对接`。下一步不再是继续拼接旧 `task-cli.py`，而是进入后续更细的 Skill 包交付完善和 shell 行为收口。
