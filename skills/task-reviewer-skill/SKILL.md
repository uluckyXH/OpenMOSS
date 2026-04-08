---
name: task-reviewer-skill
description: 审查者 Skill — 通过 CLI 工具审查子任务、评分、驳回返工
---

# Task Reviewer Skill

使用 `scripts/task-cli.py` 审查交付物、提交审查记录并给出评分。

当前角色 Skill 包仍以 `--key <API_KEY>` 方式调用 CLI；后续 Agent 专属 Skill 包会自动注入默认身份。

## 快速开始

```bash
python scripts/task-cli.py help
python scripts/task-cli.py --key <API_KEY> rules
python scripts/task-cli.py --key <API_KEY> st list --status review
python scripts/task-cli.py --key <API_KEY> review create <sub_task_id> approved 5 --comment "通过"
```

## 工作流

1. 先执行 `rules` 获取当前规则。
2. 查看待审查子任务和自己的积分记录。
3. 读取交付物、日志、验收标准和历史审查记录。
4. 提交通过或驳回的审查结论，并给出清晰评价。
5. 必要时补充积分调整和通知说明。
6. 记录审查日志，保持评分口径一致。

## 参考资料

- 详细命令：`references/commands.md`
- 详细工作流：`references/workflow.md`

## 注意

- Reviewer 的重点是“是否符合验收标准”，不是代替执行者补做实现。
- 驳回返工时必须把问题写清楚，避免给执行者模糊反馈。
- 评分标准要稳定，避免同类问题前后标准不一致。
