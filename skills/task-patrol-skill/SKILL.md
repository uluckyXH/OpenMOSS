---
name: task-patrol-skill
description: 巡查 Skill — 通过 CLI 工具巡查任务状态、标记异常、发送告警
---

# Task Patrol Skill

使用 `scripts/task-cli.py` 扫描异常任务、标记阻塞并发送告警。

当前角色 Skill 包仍以 `--key <API_KEY>` 方式调用 CLI；后续 Agent 专属 Skill 包会自动注入默认身份。

## 快速开始

```bash
python scripts/task-cli.py help
python scripts/task-cli.py --key <API_KEY> rules
python scripts/task-cli.py --key <API_KEY> st list --status in_progress
python scripts/task-cli.py --key <API_KEY> st block <sub_task_id>
```

## 工作流

1. 先执行 `rules` 获取当前规则。
2. 查看积分与近期日志，确认本轮巡查重点。
3. 扫描 `assigned`、`in_progress`、`blocked` 等状态。
4. 对超时、卡住、会话异常的子任务做进一步检查。
5. 必要时标记 `blocked` 并发送告警。
6. 记录巡查日志，方便规划师后续跟进。

## 参考资料

- 详细命令：`references/commands.md`
- 详细工作流：`references/workflow.md`

## 注意

- Patrol 负责发现问题和告警，不直接代替规划师做任务重分配。
- 除 `block` 外，不要主动修改其他任务内容或状态。
- 标记异常后要留下足够清楚的上下文，方便后续处理。
