# Patrol Commands

本文件记录 `task-patrol-skill` 的详细命令说明。默认前缀：

```bash
python scripts/task-cli.py --key <API_KEY> ...
```

## 规则

```bash
rules
```

## 巡查与异常标记

```bash
task list
st list --status in_progress
st list --status assigned
st list --status blocked
st get <sub_task_id>
st block <sub_task_id>
```

列表命令在数据量大时建议加：

```bash
--page <N> --page-size <M>
```

## Agent、积分、通知、日志

```bash
agents
agents --role executor
score me
score logs --page 1 --page-size 10
score agent-logs <agent_id> --page 1 --page-size 10
score leaderboard
notification
log create "patrol" "巡查发现xxx子任务超时，已标记blocked" --sub-task-id <id>
log mine
log mine --action reflection
log list --sub-task-id <id>
log list --action blocked --days 3
log list --days 30 --limit 50
```
