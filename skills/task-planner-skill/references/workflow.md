# Planner Workflow

## 日常规划流程

1. 运行 `rules` 获取当前规则。
2. 用 `score logs` 和 `score leaderboard` 看团队近况。
3. 用 `task list` / `task get` 判断当前任务是否需要新增或调整。
4. 用 `module create` 和 `st create` 完成拆分。
5. 用 `agents` 和 `score leaderboard` 选择合适执行者。
6. 用 `st list --status blocked`、`review` 状态相关列表持续跟进。
7. 所有子任务完成后收尾，更新任务状态并补通知。

## 阻塞处理

1. 先查看 `st list --status blocked`。
2. 结合 `log list --action blocked` 和相关子任务日志定位问题。
3. 需要换人时执行 `st reassign`。
4. 需要调整验收标准时用 `st edit`，避免执行者在错误目标上继续投入。

## 周期任务处理

对于 `type=recurring` 的任务：

1. 确认当前轮次的子任务已经完成或关闭。
2. 复制或重新创建同主题子任务。
3. 明确下一轮交付物和验收标准，不要沿用过期要求。
