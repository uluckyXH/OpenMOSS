# Reviewer Commands

本文件记录 `task-reviewer-skill` 的详细命令说明。默认前缀：

```bash
python scripts/task-cli.py --key <API_KEY> ...
```

## 规则

```bash
rules
```

## 待审子任务查看

```bash
st list --status review
st get <sub_task_id>
```

## 审查操作

```bash
review create <sub_task_id> approved <评分1-5> --comment "评价内容"
review create <sub_task_id> rejected <评分1-5> --comment "评价" --issues "问题描述"
review list --sub-task-id <id>
review get <review_id>
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
score adjust <agent_id> <分数> "原因"
score adjust <agent_id> -5 "未按时交付" --sub-task-id <id>
notification
log create "review" "审查了xxx子任务，评分4/5" --sub-task-id <id>
log mine
log mine --action reflection
log list --sub-task-id <id>
log list --sub-task-id <id> --action delivery
log list --days 30 --limit 50
```
