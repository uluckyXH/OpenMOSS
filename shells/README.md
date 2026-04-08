# shells

模板脚本目录说明。

这里存放的是按职责拆分后的 shell 模板片段，用于后续组合生成完整对接脚本。

## 1. 目录树

```text
shells/
├── README.md                                          # 当前目录说明
└── templates/
    ├── common/                                        # 通用片段，不区分平台和 provider
    │   ├── bootstrap_header.sh.tpl                    # bash 头部、通用函数
    │   ├── dependency_checks.sh.tpl                   # 通用依赖检查
    │   ├── path_setup.sh.tpl                          # 工作目录和常用路径推导
    │   ├── summary.sh.tpl                             # 执行前摘要输出
    │   └── finalize.sh.tpl                            # 执行后结果输出
    ├── openmoss/                                      # 与 OpenMOSS 服务交互的片段
    │   ├── register_runtime.sh.tpl                    # 注册运行态 Agent，获取 API_KEY
    │   └── download_skill_bundle.sh.tpl               # 下载并解压 Agent 专属 Skill Bundle
    ├── hosts/                                         # 宿主平台差异片段
    │   └── openclaw/                                  # OpenClaw 平台专用模板
    │       ├── create_sub_agent.sh.tpl                # 创建子 Agent
    │       ├── bind_existing_agent.sh.tpl             # 绑定已有 Agent
    │       ├── bind_main_agent.sh.tpl                 # 绑定 main agent
    │       ├── write_prompt_artifacts.sh.tpl          # 写入 AGENTS.md / SOUL.md / IDENTITY.md
    │       ├── apply_identity.sh.tpl                  # 应用 IDENTITY.md 到 OpenClaw
    │       ├── create_schedule.sh.tpl                 # 创建或更新 cron 定时任务
    │       └── restart_gateway.sh.tpl                 # 可选的网关重启
    └── comm_providers/                                # 通讯提供方差异片段
        └── feishu/                                    # 飞书相关模板
            └── bind_account.sh.tpl                    # 写入飞书账号和 bindings
```

## 2. 每层目录作用

### `templates/common/`

放跨平台、跨场景都可能复用的基础片段。

当前文件说明：

- `bootstrap_header.sh.tpl`
  - 脚本头部
  - 包含 `#!/usr/bin/env bash`、`set -euo pipefail`
  - 定义 `die`、`log`、`section` 这类通用函数
- `dependency_checks.sh.tpl`
  - 依赖检查
  - 默认检查 `bash / curl / python3`
  - 通过 `REQUIRE_OPENCLAW=1` 控制是否额外检查 `openclaw`
- `path_setup.sh.tpl`
  - 统一推导路径
  - 包括 `SKILL_DIR`、`AGENTS_FILE`、`SOUL_FILE`、`IDENTITY_FILE`
  - 并确保工作目录、技能目录存在
- `summary.sh.tpl`
  - 部署概览输出
  - 用来在脚本开头把核心参数打印出来
- `finalize.sh.tpl`
  - 收尾输出
  - 用来在脚本末尾输出最终产物位置

### `templates/openmoss/`

放和 OpenMOSS 服务交互相关的片段。

当前文件说明：

- `register_runtime.sh.tpl`
  - 向 OpenMOSS 注册运行态 Agent
  - 从注册响应中提取 `API_KEY`
  - 当前是旧注册链路的抽离版本
  - 后续可以平滑替换为 bootstrap token 注册链路
- `download_skill_bundle.sh.tpl`
  - 从 OpenMOSS 下载当前 Agent 专属 `skill-bundle`
  - 使用 `download_script` token 下载 zip
  - 解压为标准 Skill 目录结构
  - 准备好 `scripts/task-cli.py` 入口供后续宿主调用

### `templates/hosts/`

放宿主平台差异逻辑。每个子目录对应一个宿主平台。

#### `templates/hosts/openclaw/`

专门放 OpenClaw 宿主环境相关的片段。

当前文件说明：

- `create_sub_agent.sh.tpl`
  - 创建新的 OpenClaw 子 Agent
  - 适用于 `deployment_mode = create_sub_agent`
- `bind_existing_agent.sh.tpl`
  - 绑定一个已经存在的 OpenClaw Agent
  - 适用于 `deployment_mode = bind_existing_agent`
- `bind_main_agent.sh.tpl`
  - 绑定 OpenClaw 的 main agent
  - 适用于 `deployment_mode = bind_main_agent`
- `write_prompt_artifacts.sh.tpl`
  - 把渲染好的 Prompt 文件写入工作目录
  - 支持按开关分别写入：
    - `AGENTS.md`
    - `SOUL.md`
    - `IDENTITY.md`
- `apply_identity.sh.tpl`
  - 在写入 `IDENTITY.md` 之后执行 OpenClaw 的 identity 应用逻辑
- `create_schedule.sh.tpl`
  - 创建或跳过 OpenClaw cron 任务
  - 支持 interval / cron 两种模式
  - 支持 `thinking`、`announce`、`model_override` 等调度选项
- `restart_gateway.sh.tpl`
  - 可选的网关重启逻辑
  - 只在 `RESTART_GATEWAY=1` 时执行

### `templates/comm_providers/`

放通讯提供方差异逻辑。

#### `templates/comm_providers/feishu/`

当前文件说明：

- `bind_account.sh.tpl`
  - 用于把飞书账号配置写入 OpenClaw 本地配置
  - 同时写入对应的 `bindings`
  - 本质上是从旧 `deploy-agent.sh` 的飞书绑定步骤抽离出来的 provider 片段

## 3. 模板组合顺序参考

生成完整脚本时，可按这个顺序组合：

1. `common/bootstrap_header.sh.tpl`
2. `common/dependency_checks.sh.tpl`
3. `common/path_setup.sh.tpl`
4. `common/summary.sh.tpl`
5. `hosts/<platform>/bind_or_create_*.tpl`
6. `hosts/<platform>/write_prompt_artifacts.sh.tpl`
7. `hosts/<platform>/apply_identity.sh.tpl`
8. `openmoss/register_runtime.sh.tpl`
9. `openmoss/download_skill_bundle.sh.tpl`
10. `hosts/<platform>/create_schedule.sh.tpl`
11. `comm_providers/<provider>/*.tpl`
12. `hosts/<platform>/restart_gateway.sh.tpl`
13. `common/finalize.sh.tpl`
