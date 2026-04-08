---
name: task-executor-skill
description: 任务执行者 Skill — 通过 CLI 工具领取子任务、提交成果、处理返工
---

# Task Executor Skill

使用 `scripts/task-cli.py` 领取、执行并提交子任务。

当前角色 Skill 包仍以 `--key <API_KEY>` 方式调用 CLI；后续 Agent 专属 Skill 包会自动注入默认身份。

## 快速开始

```bash
python scripts/task-cli.py help
python scripts/task-cli.py --key <API_KEY> rules
python scripts/task-cli.py --key <API_KEY> st mine
python scripts/task-cli.py --key <API_KEY> st start <sub_task_id> --session <SESSION_ID>
```

## 工作流

1. 先执行 `rules` 获取当前规则。
2. 查看积分和我的子任务，确认当前优先级。
3. 认领或开始执行子任务，并绑定当前会话。
4. 产出交付物、记录关键日志。
5. 提交成果；如收到返工，先读审查记录再修复。
6. 完成后回顾积分和日志，持续改进执行质量。

## 参考资料

- 详细命令：`references/commands.md`
- 详细工作流：`references/workflow.md`

## 注意

- 执行者只处理属于自己的子任务，不直接修改不归属自己的任务状态。
- 所有交付物都应放在对应工作目录，提交前先对照验收标准自查。
- 收到 `rework` 时先看 `review list` 和 `review get`，不要盲改。
