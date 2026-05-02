# OpenMOSS 后台督办板

## 最近巡检
- 时间：2026-04-26 22:31 CST
- 巡检范围：workspace backfill / novel-factory audit

## 督办任务
### 任务ID: produce-high-confidence-backfill-checklist
- 当前状态: done
- 最新进展: 无新增进展。`workspace-backfill-high-confidence-checklist-20260426.md` 仍是 22 条高置信 task，`workspace-backfill-evidence-map-20260426.json` 仍只落了 7 组 task 名证据；本轮没看到新的 closeout/live verify/request_log 绝对路径把剩余 19 条抬进清单。
- 阻塞项: 无
- 下一步动作: 继续只接受显式 `workspace_root / task_workspace_dir / artifact_absolute_path` 的新证据，再决定是否扩充 checklist。

### 任务ID: start-high-confidence-backfill-script
- 当前状态: done
- 最新进展: 无新增回填进展。`workspace-backfill-dryrun-20260426.json` 仍是 `candidate_count=0`、`skipped_count=200`，其中 198 条 `already_populated`、2 条 `missing_artifact_path`；`workspace-field-coverage-breakdown-20260426.json` 仍是 218 条里 199 条已补全、19 条仍缺三字段。本轮补跑 `tests/test_workspace_backfill_dryrun.py`、`tests/test_workspace_field_coverage_audit.py`、`tests/test_backfill_workspace_context_from_map.py`，结果 `9 passed`。
- 阻塞项: 无
- 下一步动作: 只有高置信 mapping、`data/tasks.db` 或外部新证据源变化后，才重开 dry-run/apply。

### 任务ID: resolve-remaining-19-workspace-backfill-tail
- 当前状态: blocked
- 最新进展: 无新增进展。`workspace-backfill-remaining-19-assessment-20260426.md` 和 `workspace-backfill-exception-manifest-20260426.json` 仍把尾项固定为 19 条，结构还是 11 条历史前态空工件、2 条 missing-artifact probe、2 条 notify closeout、2 条 deliverable 无 workspace trace、2 条故意保留孤儿；`current-progress-board.md` 也继续维持 canonical dry-run=`0` 与“不再继续本机盲扫”的口径。
- 阻塞项: 历史任务没有稳定持久化 `workspace_root / task_workspace_dir / artifact_absolute_path`；剩余样本缺外部 closeout 原件、request_log 三字段或可恢复的真实 workspace 实物，本机常规可见层面的高置信绝对路径证据已经基本挖空。
- 下一步动作: 继续按 exception manifest 等待外部新证据；没有新证据就维持 blocked。

### 任务ID: verify-standard-task-flow-runner-and-acceptance-guards
- 当前状态: completed
- 最新进展: 已重新实跑 `python -m unittest tests.test_standard_task_flow_runner tests.test_standard_task_flow_acceptance_runner -v`，当前结果为 **8/8 通过**；runner 默认回退逻辑、acceptance 预检与静默样本验收都已能稳定跑通。
- 当前结论: 这条阻塞已经不再是依赖缺失或测试红灯问题；此前一度冒出来的 Git 追踪治理问题也已收口，runner / tests 已回到 Git 受控路径。
- 下一步动作: 后续若继续把这套入口当主路径，重点转去盯 docs/novel-factory 的口径漂移、历史快照边界和 live 样本同步，而不是再按“缺 sqlalchemy”或“Git 未纳管”重复排障。

### 任务ID: keep-novel-factory-audit-surface-in-sync
- 当前状态: in_progress
- 最新进展: `current-progress-board.md`、`review-correction-notes.md`、`standard-task-entry-live-runtime-runbook.md` 已同步把 runner / tests 的两层口径收口：
  1. 默认 host runner 现在会自动避开不可写共享树并回退到 `output_dir_fallback`
  2. 相关 runner / tests 已回到 Git 受控路径，不再只是本地工作树事实
- 阻塞项: 当前主要不是 runner 逻辑红灯，也不是 Git 纳管缺口；而是文档面要持续防止两类旧漂移：
  - 还把默认共享树写死成 `repo_shared_workspace`
  - 还把本地工作树资产写得像已受 Git 保护的稳定仓库资产
- 下一步动作: 继续盯 `docs/novel-factory`、`scripts/novel_factory`、`tests/` 和 `data/tasks.db`；一旦出现新的 live 样本、Git 纳管动作或口径漂移，先复核再回写督办板。
