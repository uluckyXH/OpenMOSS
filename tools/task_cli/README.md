# task_cli README

> 更新时间：2026-04-07

`tools/task_cli/` 是 OpenMOSS 后续 `task-cli.py` 的共享源码目录。
这里主要负责两件事：

- 承接 `task-cli.py` 的源码拆分
- 记录 `task-cli` 模块化改造进度

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

- [ ] 从旧 `skills/task-cli.py` 拆出 `BASE_URL`
- [ ] 从旧 `skills/task-cli.py` 拆出 `CLI_VERSION`
- [ ] 定义 `DEFAULT_API_KEY / AGENT_ID / AGENT_ROLE / CLI_PROFILE` 的运行时入口

#### B-2. HTTP 请求封装

- [ ] 拆出 `_headers`
- [ ] 拆出 `_request`
- [ ] 统一错误输出

#### B-3. 输出封装

- [ ] 拆出 `_print_json`
- [ ] 拆出 `_extract_items`
- [ ] 统一列表与分页输出

#### B-4. CLI 入口骨架

- [ ] 在 `main.py` 建立 argparse 主入口
- [ ] 建立统一子命令挂载入口
- [ ] 暂不迁入具体命令逻辑

### C. 命令域拆分

#### C-1. 第一批命令域

- [ ] `rules`
- [ ] `tasks`
- [ ] `sub_tasks`

#### C-2. 第二批命令域

- [ ] `modules`
- [ ] `reviews`
- [ ] `scores`
- [ ] `logs`

#### C-3. 第三批命令域

- [ ] `notifications`
- [ ] `agents`
- [ ] `admin`

### D. 命令注册表与 Profile

#### D-1. 命令注册表

- [ ] 定义 `COMMAND_REGISTRY`
- [ ] 为各命令补 `group / summary / visible_in_profiles`
- [ ] 让 help 从注册表读取

#### D-2. 角色 Profile

- [ ] 建立 `planner` Profile
- [ ] 建立 `executor` Profile
- [ ] 建立 `reviewer` Profile
- [ ] 建立 `patrol` Profile
- [ ] 让 help 按 Profile 输出

### E. 兼容入口与交付

#### E-1. 兼容入口

- [ ] 让 `skills/task-cli.py` 收成兼容入口
- [ ] 保持现有 `--key` 调用兼容
- [ ] 不打断现有下载与打包链路

#### E-2. Skill 包标准化

- [ ] 增加 `scripts/`
- [ ] 增加 `references/`
- [ ] 改造 `skills/pack-skills.py`

#### E-3. Bootstrap 对接

- [ ] 增加 Agent 专属 `task-cli.py` 渲染
- [ ] 增加 `skill-bundle` 交付
- [ ] Shell 改为下载 Skill 包

## 4. 当前状态汇总

| 大模块 | 当前状态 |
|---|---|
| A. 目录骨架 | 已完成 |
| B. 基础能力拆分 | 未开始 |
| C. 命令域拆分 | 未开始 |
| D. 命令注册表与 Profile | 未开始 |
| E. 兼容入口与交付 | 未开始 |

## 5. 下一步

下一步只做 `B. 基础能力拆分`：

- 先拆 `runtime.py`
- 再拆 `http.py`
- 再拆 `output.py`
- 暂时不碰具体命令域
