---
name: task-planner-skill
description: 任务规划师 Skill — 通过 CLI 工具创建任务、拆分模块、分配子任务
---

# Task Planner Skill

使用 `scripts/task-cli.py` 管理任务、模块和子任务分配。

当前角色 Skill 包仍以 `--key <API_KEY>` 方式调用 CLI；后续 Agent 专属 Skill 包会自动注入默认身份。

## 快速开始

```bash
python scripts/task-cli.py help
python scripts/task-cli.py --key <API_KEY> rules
python scripts/task-cli.py --key <API_KEY> task create "任务名" --desc "描述" --type once
python scripts/task-cli.py --key <API_KEY> st list --status blocked
```

## 工作流

1. 先执行 `rules` 获取当前规则。
2. 检查积分与最近日志，确认没有持续扣分项。
3. 创建或更新任务，必要时补充模块。
4. 创建子任务并分配给合适的执行者。
5. 跟踪 `blocked`、`rework`、`review` 状态，及时调整。
6. 所有子任务完成后收尾并发送通知。

## 参考资料

- 详细命令：`references/commands.md`
- 详细工作流：`references/workflow.md`

## 注意

- 规划师重点负责任务拆分、分配、重分配和收尾，不直接代替执行者交付代码。
- 分配前优先看 `score leaderboard`、`agents` 和最近日志，避免把任务交给长期不稳定的执行者。
- 遇到 `blocked` 子任务时优先处理，不要让阻塞长期堆积。
