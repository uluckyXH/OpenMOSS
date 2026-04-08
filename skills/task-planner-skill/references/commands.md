# Planner Commands

本文件记录 `task-planner-skill` 的详细命令说明。默认前缀：

```bash
python scripts/task-cli.py --key <API_KEY> ...
```

## 规则

```bash
rules
```

执行前先拉取规则；如 CLI 提示版本更新，先处理更新。

## 任务管理

```bash
task list
task list --status active
task create "任务名" --desc "描述" --type once
task get <task_id>
task edit <task_id> --name "新名" --desc "新描述"
task status <task_id> active
task cancel <task_id>
```

## 模块管理

```bash
module list <task_id>
module create <task_id> "模块名" --desc "描述"
```

## 子任务管理

```bash
st list --task-id <task_id>
st list --status blocked
st create <task_id> "子任务名" --deliverable "交付物" --acceptance "验收标准" --assign <agent_id>
st get <sub_task_id>
st edit <sub_task_id> --name "新名" --acceptance "新标准"
st cancel <sub_task_id>
st reassign <sub_task_id> <agent_id>
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
log create "plan" "规划了xxx任务，分配给了xxx"
log mine
log mine --action reflection
log list --sub-task-id <id>
log list --action blocked --days 3
log list --days 30 --limit 50
```
