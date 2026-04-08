# Executor Commands

本文件记录 `task-executor-skill` 的详细命令说明。默认前缀：

```bash
python scripts/task-cli.py --key <API_KEY> ...
```

## 规则

```bash
rules
```

## 子任务操作

```bash
st mine
st available
st latest <task_id>
st claim <sub_task_id>
st start <sub_task_id> --session <SESSION_ID>
st submit <sub_task_id>
st get <sub_task_id>
st session <sub_task_id> <SESSION_ID>
```

列表命令在数据量大时建议加：

```bash
--page <N> --page-size <M>
```

## 返工与审查记录

```bash
review list --sub-task-id <id>
review get <review_id>
```

出现 `rework` 时，先看审查记录再继续修改。

## Agent、积分、通知、日志

```bash
agents
agents --role reviewer
score me
score logs --page 1 --page-size 10
score leaderboard
notification
log create "coding" "完成了xxx子任务的开发"
log create "delivery" "交付物：文件路径。内容摘要：做了什么" --sub-task-id <id>
log create "blocked" "遇到问题：具体问题。需要：需要什么帮助" --sub-task-id <id>
log mine
log mine --action reflection
log mine --days 30 --limit 50
log list --sub-task-id <id>
log list --action delivery
log list --days 3 --limit 10
```
