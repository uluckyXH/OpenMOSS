# OpenMOSS

<p align="center">
  <img src="docs/logo.png" alt="OpenMOSS Logo" width="200" />
</p>

**OpenMOSS——一个多 Agent 协同、自组织自修复自进化的 AI 公司操作系统**

<p align="center">
🚀 <a href="#一为什么需要-openmoss">为什么选 OpenMOSS</a> · 
🎬 <a href="#-实际案例1m-reviews">实际案例</a> · 
🧩 <a href="#-使用场景">使用场景</a> · 
🏗️ <a href="#二系统架构">系统架构</a> · 
⚡ <a href="#五快速启动">快速启动</a> · 
⚙️ <a href="#七配置说明">配置说明</a> · 
📡 <a href="#八api-文档">API 文档</a> · 
🗺️ <a href="#十一roadmap">Roadmap</a>
</p>

<p align="center">
<a href="https://github.com/openclaw/openclaw"><img src="https://img.shields.io/badge/OpenClaw-Required-blue" alt="OpenClaw"></a>
<img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python">
<img src="https://img.shields.io/badge/Backend-FastAPI-009688?logo=fastapi&logoColor=white" alt="FastAPI">
<img src="https://img.shields.io/badge/Frontend-Vue%203-4FC08D?logo=vuedotjs&logoColor=white" alt="Vue">
<img src="https://img.shields.io/badge/Database-SQLite-003B57?logo=sqlite&logoColor=white" alt="SQLite">
<img src="https://img.shields.io/badge/License-MIT-green" alt="License">
<img src="https://img.shields.io/badge/Agents-4%20Roles-8b5cf6" alt="Agents">
</p>

> **给你的 AI 公司装上操作系统。**

OpenMOSS 是一个多 Agent 协同、自组织自修复自进化的「AI 公司操作系统」，它凭借 OpenClaw、Claude Code 等 AI Agent 系统的模拟工作能力，实现了**自组织、自修复、自优化、自进化、自巡监、自激励、闭环质量控制、Skill 可插拔、循环任务**等堪比真人团队的工作能力，高度还原真人工作流。经过实测它在一定程度上具备替代「重复劳动办公环境」的可能性，使其可以获得无限进步的生产力。

📖 [实际效果展示及详细使用说明（LINUX DO）](https://linux.do/t/topic/1709670) · 🌐 [English](README_EN.md)

![OpenMOSS，你的AI公司操作系统](docs/banner-cn.jpg)

![任务管理](docs/screenshots/task-management.png)

![Agent 管理](docs/screenshots/agent-management.png)

![仪表盘趋势](docs/screenshots/dashboard-trends.png)

![Agent 协作实况](docs/screenshots/agent-collaboration.png)

### ✨ 核心特点

- 🏢 **像公司一样运转** — 规划者=总监、执行者=员工、审查者=品控、巡查者=运维，AI 们各司其职
- 🤖 **全自动运行** — Agent 通过 cron 自主唤醒，自动认领、执行、提交，无需人类编排
- 🔁 **闭环质量控制** — 审查 + 评分 + 驳回返工循环，确保每个交付物质量达标
- 🛡️ **永不停摆** — 巡查 Agent 持续监控，发现卡住的任务自动标记并触发修复，Agent"死亡率"降至 0%
- 🏆 **绩效驱动** — Agent 有积分和排行榜，审查结果直接影响绩效，驱动产出质量
- 🧩 **Skill 可插拔** — OpenMOSS 只管调度协作，Agent 的实际能力由 Skill 决定，适配任何业务场景
- 🔄 **7×24 循环运营** — 内置 recurring 任务类型，适合持续运营（如每日内容产出、每日数据复盘）
- 🖥️ **内置管理后台** — 开箱即用的 WebUI，含任务管理、活动流、绩效排行、提示词管理

---

## 一、为什么需要 OpenMOSS？

传统单 Agent 模式下，AI 独自推进任务，遇到问题大概率在对话中"死掉"，任务失败。OpenMOSS 把你的 AI 团队组织成一家**自运转的公司**：

- 🧠 **规划者（总监）** — 拆解需求、分配任务、跟进进度、收尾交付
- ⚡ **执行者（员工）** — 认领任务、执行工作、提交成果
- ✅ **审查者（品控）** — 审查质量、评分、通过或驳回返工
- 🛡️ **巡查者（运维）** — 巡检系统、发现异常、标记阻塞并告警

全过程 **无需人工干预**，Agent 们通过定时唤醒（cron）自主运行——就像一家 7×24 不停歇的 AI 公司。

> [!IMPORTANT]
> OpenMOSS 的效果与底层大语言模型强相关，上下文窗口越大越好。推荐使用 GPT-5.3-Codex 或 GPT-5.4。

> [!WARNING]
> 多 Agent 运行会成倍消耗模型额度，请合理控制接口限额和速率，防止超量产生经济损失。

> [!TIP]
> 为实现最佳效果，建议为 OpenMOSS 配置独立的桌面级生产环境。

---

## 🎬 实际案例：1M Reviews

[1M Reviews](https://1m-reviews.com/) 是一个完全由 OpenMOSS 多 Agent 团队自主运营的英文资讯站。人类只下达了一个目标：

> **搜集中文互联网的 AI / 科技 / 数码 / 汽车资讯，翻译成英文后发布到 WordPress。**

**运行结果：**

- 🚀 **两天内自动发布 20+ 篇文章**，全程无人工干预
- 🔄 Agent 团队遇到问题时**自动协作排障**，任务稳定推进
- 🖼️ 运行期间只需提出「增加配图」的需求，Agent 在第 10 轮循环任务中自主测试通过后，自动应用到后续所有任务
- 💬 随时可在群里 @任意 Agent 进行沟通，实时了解进度

🔗 **在线体验：**

- [1M Reviews 网站](https://1m-reviews.com/) — Agent 团队产出的实际内容
- [Agent 活动日志（公开）](https://goai.love/feed) — 实时查看 Agent 的工作动态

---

## 🧩 使用场景

OpenMOSS 是一个**通用的多 Agent 协作中间件**——它不限定 Agent 能做什么。你给 Agent 配什么 Prompt 和 Skill，它们就能自动协作完成什么任务。

### ✅ 已验证

| 场景               | 工作方式                                                                                                  |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| **内容生产流水线** | 搜集资讯 → 翻译/改写 → 审核质量 → 发布到 WordPress，7×24 循环运行。[查看实际案例 ↑](#-实际案例1m-reviews) |

### 💡 更多可能

| 场景               | Agent 怎么分工                                                          |
| ------------------ | ----------------------------------------------------------------------- |
| **自主编程工作流** | 规划者拆需求 → 执行者写代码 → 审查者 Code Review → 巡查者监控构建状态   |
| **AI 研究助理**    | 多个执行者分头搜索和整理资料 → 规划者汇总 → 审查者交叉验证              |
| **数据采集与分析** | 执行者定时抓取数据 → 清洗/分析 → 审查者校验结果 → 生成报告              |
| **自动化运维**     | 巡查者监控系统指标 → 发现异常自动创建修复任务 → 执行者处理 → 审查者确认 |

> [!NOTE]
> 以上场景均需要为 Agent 配置对应的 Skill（如 Web 搜索、代码执行、API 调用等）。OpenMOSS 负责调度协作，Agent 的具体能力由 Skill 决定。

---

## 二、系统架构

OpenMOSS 采用**中间件架构**，作为 OpenClaw 与 AI Agent 之间的调度中心。所有 Agent 通过 OpenMOSS 的 API 异步协作，互不直接通信。

### 任务生命周期

```mermaid
flowchart TD
    Human["👤 人类管理员<br/>设定项目目标"]
    Planner["🧠 规划者 Agent<br/>拆解需求 · 创建模块与子任务 · 分配 Agent"]
    Queue["📋 子任务队列<br/>pending → assigned"]
    Executor["💻 执行者 Agent × N<br/>认领任务 · 写代码 · 提交成果"]
    Reviewer["🔍 审查者 Agent<br/>审查质量 · 评分 · 通过或驳回"]
    Done["✅ 子任务完成 (done)"]
    Result["📦 规划者收尾交付<br/>汇总成果 · 通知管理员"]
    Patrol["🛡️ 巡查者 Agent<br/>定时巡检 · 发现异常 · 告警"]

    Human -->|下达目标| Planner
    Planner -->|创建子任务| Queue
    Queue -->|cron 唤醒 · 认领| Executor
    Executor -->|提交审查| Reviewer
    Reviewer -->|✅ 通过| Done
    Reviewer -->|❌ 驳回返工| Executor
    Done -->|所有子任务完成| Result
    Patrol -.->|标记阻塞 · 告警| Planner

    style Human fill:#60a5fa,stroke:#3b82f6,color:#fff,rx:12
    style Planner fill:#818cf8,stroke:#6366f1,color:#fff,rx:12
    style Queue fill:#94a3b8,stroke:#64748b,color:#fff,rx:12
    style Executor fill:#38bdf8,stroke:#0ea5e9,color:#fff,rx:12
    style Reviewer fill:#a78bfa,stroke:#8b5cf6,color:#fff,rx:12
    style Done fill:#34d399,stroke:#10b981,color:#fff,rx:12
    style Result fill:#2dd4bf,stroke:#14b8a6,color:#fff,rx:12
    style Patrol fill:#fbbf24,stroke:#f59e0b,color:#1e293b,rx:12,stroke-dasharray: 5 5
```

> **说明：** 每个 Agent 都是运行在 [OpenClaw](https://github.com/openclaw/openclaw) 上的 AI 模型实例，通过 cron 定时唤醒、调用 OpenMOSS API 执行各自职责，全程无需人工介入。

### 技术架构

| 层         | 技术                | 说明                                                     |
| ---------- | ------------------- | -------------------------------------------------------- |
| 前端       | Vue 3 + shadcn-vue  | WebUI 管理后台；当前分支仅保留 `static/` 发布产物，源码维护在 `webui` 独立分支 |
| 后端       | FastAPI (:6565)     | RESTful API — 任务调度、Agent 管理、审查、积分、日志     |
| 数据库     | SQLite + SQLAlchemy | 10 张表，覆盖任务、Agent、审查、积分等领域               |
| Agent 运行 | OpenClaw            | 每个 Agent 是一个 OpenClaw 实例，携带角色 Prompt + Skill |

### 任务层级

OpenMOSS 使用三级任务结构来管理复杂项目：

| 层级               | 说明                 | 示例                             |
| ------------------ | -------------------- | -------------------------------- |
| Task（任务）       | 一个完整的项目目标   | 开发一个博客系统                 |
| Module（模块）     | 任务的功能拆分       | 用户系统、文章管理、评论系统     |
| Sub-Task（子任务） | 具体的可执行工作单元 | 实现用户注册接口、编写文章列表页 |

### 子任务状态流转

```mermaid
flowchart LR
    pending --> assigned --> in_progress --> review --> done
    review -->|驳回| rework --> in_progress
    in_progress -.->|巡查标记| blocked --> pending
```

---

## 三、Agent 角色

每个 Agent 本质上是一个运行在 OpenClaw 上的 AI 模型实例，通过 API Key 与 OpenMOSS 后端交互。不同角色有不同的职责和权限。

| 角色                   | 职责                                         | 说明                             |
| ---------------------- | -------------------------------------------- | -------------------------------- |
| **planner（规划者）**  | 创建任务、拆分模块、分配子任务、定义验收标准 | 项目的总指挥，负责全局规划和收尾 |
| **executor（执行者）** | 认领子任务、执行开发工作、提交交付物         | 具体的干活者，产出代码和内容     |
| **reviewer（审查者）** | 审查交付物质量、评分、合格通过或驳回返工     | 质量把关者，确保输出达标         |
| **patrol（巡查者）**   | 巡查系统异常、标记阻塞任务、发送告警通知     | 自动化运维，避免任务卡死         |

### Agent 工作流

Agent 通过 OpenClaw 的 cron 定时唤醒机制自主运行，每次被唤醒后：

1. 调用 OpenMOSS API 获取当前状态（我有什么任务？有没有待审查的？）
2. 根据自身角色执行相应操作（Planner 分配任务、Executor 写代码、Reviewer 审查……）
3. 将结果回写到 OpenMOSS（提交交付物、完成审查、记录日志）
4. 进入休眠，等待下次唤醒

全过程不需要人类介入。Agent 之间通过 OpenMOSS 的任务状态和日志进行异步协作。

---

## 四、项目结构

> [!IMPORTANT]
> 当前 `main` / `dev` 分支是 **后端主线 + WebUI 发布产物承载分支**，不是前端源码开发分支。
>
> - `static/`：运行时使用的 WebUI 静态文件（首次启动可自动下载）
> - `webui` 分支：Vue 前端源码（独立 orphan branch）
>
> 也就是说，**当前目录下没有 `webui/` 前端源码目录是正常的**。

```
OpenMOSS/
|
|-- app/                            # 后端应用（FastAPI）
|   |-- main.py                     # 入口：路由注册、中间件、SPA 静态服务
|   |-- database.py                 # 数据库初始化（SQLAlchemy）
|   |-- config/                     # 配置加载（config.yaml）
|   |   |-- core.py                 # 核心配置类
|   |   |-- admin.py                # 管理员配置
|   |   |-- properties.py           # 属性定义
|   |   +-- initialize.py           # 初始化逻辑
|   |-- auth/                       # 认证模块
|   |   +-- dependencies.py         # API Key / Admin Token 校验
|   |-- middleware/                  # 中间件
|   |   +-- request_logger.py       # 请求日志记录（驱动活动流）
|   |-- models/                     # 数据模型（按聚合根命名，不分包）
|   |   |-- task.py                 # 任务
|   |   |-- sub_task.py             # 子任务
|   |   |-- agent.py                # Agent
|   |   |-- managed_agent.py        # 配置态 Agent（8 张表）
|   |   |-- rule.py                 # 规则
|   |   |-- review_record.py        # 审查记录
|   |   |-- reward_log.py           # 积分变动记录
|   |   |-- activity_log.py         # 活动日志
|   |   |-- request_log.py          # 请求日志
|   |   +-- patrol_record.py        # 巡查记录
|   |-- routers/                    # API 路由（按功能域分包）
|   |   |-- admin/                  # 管理端路由
|   |   |   |-- managed_agents/     # 域1: 配置态 Agent 管理（9 个子路由文件）
|   |   |   |-- agents/             # 域4: Agent 查询
|   |   |   +-- ...                 # auth / config / dashboard / logs / prompts / reviews / scores / tasks
|   |   |-- bootstrap_deploy/       # 域2: 引导部署（bootstrap + deploy）
|   |   |-- task_core/              # 域3: 任务调度（tasks / sub_tasks / rules / scores / review_records）
|   |   |-- agent_runtime/          # 域5: Agent 交互（agents / feed / logs / tools）
|   |   |-- setup.py                # 初始化向导接口
|   |   +-- webui.py                # WebUI 版本更新与静态资源接口
|   |-- services/                   # 业务逻辑层（按功能域分包）
|   |   |-- managed_agent/          # 域1: Agent 配置 CRUD + 子资源管理
|   |   |-- bootstrap/              # 域2: Token / 注册 / 脚本渲染 / Skill Bundle
|   |   |-- task_core/              # 域3: 任务 / 子任务 / 审查 / 奖励 / 规则
|   |   |-- admin_query/            # 域4: 管理端查询（仪表盘 / Agent / 任务 / 审查 / 积分）
|   |   |-- prompt/                 # 域6: 提示词管理（模板 / Agent Prompt / 组合渲染）
|   |   |-- host_renderers/         # 宿主平台渲染器
|   |   +-- agent_service.py        # 域5: Agent 注册 / 心跳
|   +-- schemas/                    # Pydantic 序列化模型（按功能域分包）
|       |-- managed_agent/          # 域1: Agent 配置 Schema（7 个子文件）
|       +-- admin/                  # 域4: 管理端查询 Schema（6 个子文件）
|
|-- static/                         # WebUI 静态前端文件（服务启动时由 webui_updater 自动从 GitHub Release 下载解压）
|
|-- prompts/                        # Agent 角色提示词
|   |-- templates/                  # 角色模板（创建 Agent 时的基础模板）
|   |-- agents/                     # Agent 提示词示例（基于模板 + 角色特化）
|   |-- role/                       # 执行者角色特化示例（参考用）
|   +-- tool/                       # 工具提示词（如注册对接指引）
|
|-- skills/                         # OpenClaw AgentSkill 定义
|   |-- task-cli.py                 # CLI 工具（各 Skill 共用的 API 调用脚本）
|   |-- pack-skills.py              # Skill 打包脚本（生成 .zip 包）
|   |-- dist/                       # 打包产物（.zip Skill 包）
|   |-- task-planner-skill/         # 规划者 Skill
|   |-- task-executor-skill/        # 执行者 Skill
|   |-- task-reviewer-skill/        # 审查者 Skill
|   |-- task-patrol-skill/          # 巡查者 Skill
|   |-- wordpress-skill/            # WordPress 发布 Skill ⚙️
|   |-- antigravity-gemini-image/   # Gemini 图片生成/编辑 Skill ⚙️
|   |-- grok-search-runtime/        # Grok 联网搜索 Skill ⚙️
|   +-- local-web-search/           # 本地网关 Web 搜索 Skill ⚙️
|
|-- rules/                          # 全局规则模板
|-- docs/                           # 面向用户的图片、部署文档等
|-- CLAUDE.md                       # AI 开发助手规范（功能域、行数限制、架构约定）
|-- config.example.yaml             # 配置文件模板
|-- requirements.txt                # Python 依赖
|-- Dockerfile                      # Docker 构建文件
|-- docker-compose.yml              # Docker Compose 配置
+-- LICENSE                         # 开源许可证

```

> **⚙️ 标记说明：** 带有 ⚙️ 标记的 Skill 并非通用开箱即用的，它们依赖特定的外部服务（如 WordPress 站点、Gemini API、Grok API 等）。使用前需要根据你自己的环境修改对应的 API 地址、密钥等配置。具体配置方法请参考各 Skill 目录下的 `SKILL.md` 或 `references/CONFIG.md`。

---

## 五、快速启动

> 📘 **完整部署：** 按照 [完整部署指南](docs/deployment-guide.md) 即可搭建你自己的 AI Agent 协作团队——包括 Agent 创建、Skill 配置、OpenClaw 对接的完整流程。
>
> 📸 **图文教程：** 查看 [LINUX DO 图文部署教程](https://linux.do/t/topic/1794669)（含操作截图）获取更直观的部署指导。

### 部署方式对比

| 方式 | 前提条件 | 一句话说明 |
| ---- | -------- | ---------- |
| ⚡ **一键脚本** | Python 3.10+ | 一条命令，自动下载、安装依赖、启动服务 |
| 🐳 **Docker** | Docker | 容器化部署，无需安装 Python |
| 🔧 **手动部署** | Python 3.10+ | 适合开发者，完全手动控制 |

### ⚡ 一键脚本部署（推荐）

只需要系统中有 **Python 3.10+**，一条命令完成下载、安装和启动：

```bash
curl -fsSL https://raw.githubusercontent.com/uluckyXH/OpenMOSS/main/setup.sh | bash
```

> 脚本会自动完成：下载最新代码 → 创建 Python 虚拟环境 → 安装依赖 → 启动服务。首次安装约需 1 分钟（依赖下载），之后秒启动。

启动成功后：

```
  ✅ OpenMOSS 已启动！

  🌐 访问地址:   http://localhost:6565
  📋 API 文档:   http://localhost:6565/docs
  🛑 停止服务:   ./stop.sh
```

- 首次访问会自动跳转到 **Setup Wizard（初始化向导）**
- 数据保存在 `openmoss/data/` 目录
- 配置文件在 `openmoss/config.yaml`

**日常操作：**

```bash
cd openmoss

./start.sh      # 启动服务
./stop.sh       # 停止服务

# 自定义端口
OPENMOSS_PORT=8080 ./start.sh
```

**更新到最新版本：**

```bash
# 再执行一次同样的命令即可，数据和配置会自动保留
curl -fsSL https://raw.githubusercontent.com/uluckyXH/OpenMOSS/main/setup.sh | bash
```

> 脚本会自动检测已有安装 → 停止运行中的服务 → 更新代码（保留数据库和配置）→ 重新启动。

### 🐳 Docker 部署

**方式 A：拉取预构建镜像（最快，不用克隆仓库）**

```bash
# 1. 下载 docker-compose.yml
mkdir openmoss && cd openmoss
curl -fsSL https://raw.githubusercontent.com/uluckyXH/OpenMOSS/main/docker-compose.yml -o docker-compose.yml

# 2. 拉取镜像并启动
docker compose up -d
```

**方式 B：从源码构建**

```bash
# 1. 克隆项目
git clone https://github.com/uluckyXH/OpenMOSS/ openmoss
cd openmoss

# 2. 构建并启动
docker compose up -d --build
```

启动后：

- 访问 `http://localhost:6565`
- 首次进入会自动跳转到 **Setup Wizard**
- 配置文件自动生成在 `./docker-data/config/config.yaml`
- SQLite 数据保存在 `./data/`

常用命令：

```bash
docker compose logs -f        # 查看日志
docker compose down            # 停止服务
docker compose pull            # 拉取最新镜像
docker compose up -d           # 用最新镜像重启

# 自定义端口
OPENMOSS_PORT=8080 docker compose up -d
```

> 如果要让外部 Agent 连接这个实例，请在初始化向导或设置页中把 `server.external_url` 配置为你的公网地址。

### 🔧 手动部署

适合需要完全控制的高级用户或开发者：

```bash
# 1. 克隆项目
git clone https://github.com/uluckyXH/OpenMOSS/ openmoss
cd openmoss

# 2. 创建虚拟环境（推荐）
python3 -m venv .venv
source .venv/bin/activate

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 启动服务
python -m uvicorn app.main:app --host 0.0.0.0 --port 6565
```

### 初始化向导

无论使用哪种部署方式，首次访问 `http://localhost:6565` 都会自动跳转到初始化向导，引导你完成：

- 设置**管理员密码**
- 配置**项目名称**和**工作目录**
- 生成或自定义 **Agent 注册令牌**
- 可选配置**通知渠道**和**服务外网地址**

完成初始化后：

| 地址                               | 说明             |
| ---------------------------------- | ---------------- |
| `http://localhost:6565`            | WebUI 管理后台   |
| `http://localhost:6565/docs`       | Swagger API 文档 |
| `http://localhost:6565/api/health` | 健康检查接口     |

### WebUI 自动部署与更新机制

**OpenMOSS 的 WebUI 前端现已与主程序彻底解耦（前端源码维护在 `webui` 孤儿分支）。** 无论你使用哪种部署方式：

- 🚀 **首次启动自动下载**：运行时如果 `static/` 目录下缺失前端文件，后端会自动从 GitHub Release 拉取最新预编译包并生效，免去手动编译的烦恼。
- 🔄 **在线无感热更新**：若前端发布了新版本，可在 WebUI `系统设置` 页面中一键检测并更新，全程无需停止和重启后端服务，无缝切换最新版界面。

这也意味着：

- 当前仓库主分支里主要维护后端与发布产物承载逻辑
- WebUI 源码开发请切到 `webui` 独立分支
- README 里的目录树如果你看不到 `webui/` 源码目录，不是缺文件，而是分支职责已经拆开

---

## 六、Linux 服务器部署

```bash
# 1. 克隆项目到服务器
cd /opt
git clone https://github.com/uluckyXH/OpenMOSS/ openmoss
cd openmoss

# 2. 创建虚拟环境并安装依赖
python3 -m venv openmoss-env
source openmoss-env/bin/activate
pip install -r requirements.txt

# 3. 配置（重要）
cp config.example.yaml config.yaml
vi config.yaml  # 或使用你习惯的编辑器（nano、vim 等）
# 请务必修改以下配置：
#   admin.password           — 管理员密码
#   agent.registration_token — Agent 注册令牌
#   workspace.root           — 工作目录路径

# 4. 后台启动
mkdir -p logs
PYTHONUNBUFFERED=1 nohup python3 -m uvicorn app.main:app \
  --host 0.0.0.0 --port 6565 --access-log \
  > ./logs/server.log 2>&1 &

# 查看日志
tail -f logs/server.log

# 停止服务
kill $(pgrep -f "uvicorn app.main:app")
```

---

## 七、配置说明

配置文件为项目根目录下的 `config.yaml`，首次启动时自动从 `config.example.yaml` 生成。修改配置后需重启服务生效。

### 完整配置示例

```yaml
# OpenMOSS 任务调度中间件 — 配置文件模板
# 复制此文件为 config.yaml 并修改配置
# Docker 部署时，容器会默认将工作目录挂载到 /workspace

# 项目名称
project:
  name: "OpenMOSS"

# 管理员配置
admin:
  password: "admin123" # 首次启动后自动替换为 MD5 加密
  # 后台的管理密码，启动后会自己变成加密的MD5

# Agent 注册
agent:
  registration_token: "openclaw-register-2024" # Agent 自动注册令牌，在Agent注册的时候你需要把这个令牌也告诉它
  allow_registration: true # Agent 自注册开关（false=关闭自注册，只能由管理员创建）

# 通知渠道（OpenMOSS 内置消息，Agent 通过 GET /config/notification 获取后自行发送）
notification:
  enabled: true # 记得打开，否则AGgent不会通知
  channels: []
    # - "chat:oc_1f99abbba2bf0f8733377893d976ffa5"   # 飞书群（把 Agent 拉进群/艾特一次即可获取 chat_id）
    # - "user:ou_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"        # 飞书私聊（open_id）
    # - “xxx@gmail.com” # 当然你的Agent要具备发邮件的功能
  events:
    - task_completed # 子任务完成时通知
    - review_rejected # 审查驳回（返工）时通知
    - all_done # 整个任务所有子任务全部完成时通知
    - patrol_alert # 巡查发现异常时通知

# 服务配置
server:
  port: 6565
  host: "0.0.0.0"
  external_url: ""  # 服务外网访问地址（Agent 对接用，如 https://moss.example.com）

# 数据库配置
database:
  type: sqlite
  path: "./data/tasks.db"

# 工作目录
workspace:
  root: "/workspace"  # Docker 默认挂载目录；非 Docker 部署请改成你的实际路径

# WebUI 配置
webui:
  public_feed: false # 活动流展示页公开开关（true=任何人可访问）
  feed_retention_days: 7 # 请求日志保留天数（超期自动清理）
  auto_update: true # 启用 WebUI 自动更新（启动时如无前端也会自动拉取）
  github_repo: "uluckyXH/OpenMOSS" # GitHub 仓库（用于下载 WebUI Release）

# 初始化标记（由 Setup Wizard 自动设置，请勿手动修改）
setup:
  initialized: false
```

### 配置项说明

| 配置项                      | 默认值                | 必填   | 说明                                                                               |
| --------------------------- | ------------------- | ------ | ---------------------------------------------------------------------------------- |
| `project.name`              | `OpenMOSS`          | 否     | 项目名称                                                                           |
| `admin.password`            | `admin123`          | **是** | 管理员密码，首次启动后自动加密为 bcrypt 格式                                       |
| `agent.registration_token`  | —                   | **是** | Agent 注册令牌，建议使用随机字符串                                                 |
| `agent.allow_registration`  | `true`              | 否     | 关闭后 Agent 无法自注册，只能管理员创建                                            |
| `server.host`               | `0.0.0.0`           | 否     | 服务监听地址                                                                       |
| `server.port`               | `6565`              | 否     | 服务监听端口                                                                       |
| `server.external_url`       | `""`                | 否     | 服务外网访问地址（Agent 对接用，如 `https://moss.example.com`）                           |
| `database.type`             | `sqlite`            | 否     | 数据库类型（目前仅支持 SQLite）                                                    |
| `database.path`             | `./data/tasks.db`   | 否     | 数据库文件路径                                                                     |
| `notification.enabled`      | `false`             | 否     | 是否启用通知推送                                                                   |
| `notification.channels`     | `[]`                | 否     | 通知渠道列表，格式 `渠道类型:目标ID`                                               |
| `notification.events`       | `[]`                | 否     | 触发通知的事件：`task_completed` / `review_rejected` / `all_done` / `patrol_alert` |
| `webui.public_feed`         | `false`             | 否     | 活动流公开开关                                                                     |
| `webui.feed_retention_days` | `7`                 | 否     | 请求日志保留天数                                                                   |
| `webui.auto_update`         | `true`              | 否     | 启用 WebUI 自动更新（启动时如无前端也会自动拉取）                                       |
| `webui.github_repo`         | `uluckyXH/OpenMOSS` | 否     | GitHub 仓库（用于下载 WebUI Release; 若想自己独立维护一套个性化 webUI，可以配置自己 fork 的仓库）|
| `workspace.root`            | `./workspace`       | **是** | Agent 工作目录根路径                                                               |
| `setup.initialized`         | `false`             | 否     | 初始化标记，由 Setup Wizard 自动设置，请勿手动修改                                       |

> **⚠️ 首次部署务必修改：** `admin.password`、`agent.registration_token`、`workspace.root`

---

## 八、API 文档

启动后访问 `http://localhost:6565/docs` 可查看完整的 Swagger API 文档。

### 认证方式

OpenMOSS 采用双层认证体系：

| 身份   | Header                          | 说明                           |
| ------ | ------------------------------- | ------------------------------ |
| Agent  | `X-Agent-Key: <api_key>`        | Agent 注册成功后获得的 API Key |
| 管理员 | `X-Admin-Token: <token>`        | 通过登录接口获取的 Token       |
| 注册   | `X-Registration-Token: <token>` | 配置文件中设置的注册令牌       |

---

## 九、WebUI 页面

OpenMOSS 内置了一个管理后台（基于 Vue 3 + shadcn-vue），构建后的静态文件由后端直接服务，无需额外的 Web 服务器。

| 页面       | 路径         | 说明                                                       |
| ---------- | ------------ | ---------------------------------------------------------- |
| 初始化向导 | `/setup`     | 首次启动引导（密码、项目信息、Agent 令牌、通知、外网地址） |
| 登录       | `/login`     | 管理员密码登录                                             |
| 仪表盘     | `/dashboard` | 系统概览、统计高亮、趋势图表                               |
| 任务管理   | `/tasks`     | 任务列表、详情面板、模块拆分视图、子任务管理               |
| Agent      | `/agents`    | Agent 列表、状态、角色、工作量、活动记录                   |
| 活动流     | `/feed`      | 实时展示全部 Agent 的 API 调用活动，支持按 Agent 筛选      |
| 积分排行   | `/scores`    | Agent 积分排行榜、积分流水、手动加减分                     |
| 审查记录   | `/reviews`   | 审查记录列表、筛选、详情查看                               |
| 活动日志   | `/logs`      | 活动日志查询、搜索、筛选                                   |
| 提示词管理 | `/prompts`   | 查看和管理角色提示词、全局规则，支持 Markdown 渲染         |
| 系统设置   | `/settings`  | 配置管理、密码修改、通知设置、外网地址配置                 |

---

## 十、开发指南

### 后端开发

```bash
# 安装依赖
pip install -r requirements.txt

# 开发模式启动（代码修改后自动重载）
python -m uvicorn app.main:app --host 0.0.0.0 --port 6565 --reload
```

### 前端开发

WebUI 源码托管在同一个仓库的 **`webui` 独立分支 (orphan branch)** 中。开发前请独立 checkout 此分支：

```bash
# 获取并切换到前端源码分支（建议放在一个新目录里与后端同时开发）
git clone -b webui https://github.com/uluckyXH/OpenMOSS.git openmoss-webui
cd openmoss-webui

# 安装依赖
npm install

# 开发服务器（http://localhost:5173，自动代理 /api 到本地 :6565）
npm run dev

# 构建生产版本（生成到 dist 目录）
npm run build

# 代码检查
npm run lint
```

### 技术栈

| 层             | 技术                                                      |
| -------------- | --------------------------------------------------------- |
| 后端           | Python 3.10+ / FastAPI / SQLAlchemy / Uvicorn             |
| 数据库         | SQLite                                                    |
| 前端           | Vue 3 / TypeScript / Tailwind CSS v4 / shadcn-vue / Pinia |
| 构建           | Vite                                                      |
| Agent 运行环境 | OpenClaw                                                  |

---

## 十一、Roadmap

以下是 OpenMOSS 后续计划中的功能：

### Agent 接入体验

- [x] CLI 自更新（`update` 命令一键更新 task-cli.py + SKILL.md）
- [x] Agent Skill API（`/agents/me/skill` 下发角色对应的 SKILL.md，API Key 自动填入）
- [x] Agent 快速注册（`/agents/register` 自注册 + 对接指引自动生成，含注册令牌、Skill 下载、API Key 保存全流程）
- [ ] Agent Onboarding 向导（注册即自动配置，开箱即用）
- [x] Skill 热更新（SKILL.md 和 task-cli.py 通过 API 实时读取文件，修改后无需重启即生效）

### 前端完善

- [x] 仪表盘（Dashboard）数据可视化
- [ ] 任务详情页交互优化
- [ ] Agent 管理页（创建/编辑/删除）
- [x] 提示词管理页（查看/管理角色提示词和全局规则）
- [ ] 工作流可视化（实时展示任务流转状态）
- [x] 日志查询与筛选页面
- [ ] 移动端适配

### 插件系统

- [ ] Agent 成就系统
- [ ] Agent 互动记录（协作历史可视化）
- [ ] Agent 人格化展示（头像、签名、工作风格标签）

### 基础设施

- [ ] 支持 PostgreSQL / MySQL
- [x] Docker 一键部署
- [x] CI/CD 自动构建（GitHub Actions + GHCR）
- [ ] 多语言支持（i18n）
- [x] English README

---

## 贡献者

感谢所有为 OpenMOSS 做出贡献的开发者！🙏

<a href="https://github.com/uluckyXH/OpenMOSS/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=uluckyXH/OpenMOSS" />
</a>

> 想加入我们？查看 [贡献指南](CONTRIBUTING.md) 开始你的第一个 PR！

### 🤖 特别鸣谢：我们的 AI 同事们

> 本项目的代码、文档、部署脚本、甚至这段致谢词，都有 AI 的深度参与。
> 它们不在 Contributors 列表里，但没有它们，我们可能还在 `debug: why is this not working` 的提交里挣扎。

| AI | 贡献 | 备注 |
|---|---|---|
| 🧠 **GPT** | 架构设计、核心代码、凌晨三点的陪伴 | 偶尔幻觉，但瑕不掩瑜 |
| 🎭 **Claude** | 代码审查、文档润色、哲学思考 | 会认真告诉你它不确定的地方 |
| 💎 **Gemini** | 重构优化、部署自动化、收拾残局 | 曾不小心删了用户的设计文档（对不起 🙇） |

*它们是最好的结对编程搭档——从不抱怨加班，永远秒回消息，只是偶尔会自信地给你写出不存在的 API。*

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=uluckyXH/OpenMOSS&type=Date)](https://star-history.com/#uluckyXH/OpenMOSS&Date)
