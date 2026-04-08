# Executor Workflow

## 标准执行流程

1. 用 `rules` 获取本轮规则。
2. 用 `st mine`、`st available`、`st latest` 确定当前要处理的子任务。
3. 用 `st claim` 或 `st start` 正式进入执行。
4. 在执行过程中及时写 `log create`，尤其是交付摘要和阻塞说明。
5. 完成后执行 `st submit`。
6. 如果进入 `rework`，先读 `review list` 和 `review get`，再继续修复。

## 阻塞处理

1. 无法继续时立刻写 `log create "blocked" ...`。
2. 说明当前卡点、已尝试动作、需要的帮助。
3. 不要长时间沉默或一直停在 `in_progress`。

## 交付检查

提交前至少确认：

1. 交付物路径齐全。
2. 验收标准逐条自查通过。
3. 关键修改点已写进交付日志。
