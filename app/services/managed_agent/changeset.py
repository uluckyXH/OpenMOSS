"""
部署变更集计算

对比上次部署快照与本次用户选择，生成变更集并校验。
设计文档：dev-docs/agent-config-center/13-选择式脚本生成与部署变更集设计.md §7.6
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from app.exceptions import ValidationError
from app.models.managed_agent import (
    ManagedAgentCommBinding,
    ManagedAgentSchedule,
)
from app.schemas.managed_agent import (
    DeployChangeset,
    DeployChangesetItem,
    DeployScriptRequest,
)

from .comm_binding import list_comm_bindings
from .deployment import get_latest_confirmed_snapshot, parse_snapshot_json
from .schedule import list_schedules


# ---------------------------------------------------------------------------
# 变更集计算
# ---------------------------------------------------------------------------

def compute_changeset(
    db: Session,
    managed_agent_id: str,
    request: DeployScriptRequest,
    *,
    renderer_prompt_keys: list[str],
) -> DeployChangeset:
    """对比上次 confirmed 快照与本次选择，生成变更集。

    Args:
        db: 数据库会话
        managed_agent_id: Agent ID
        request: 部署请求
        renderer_prompt_keys: 当前平台 renderer 支持的 prompt key 列表
    """
    items: list[DeployChangesetItem] = []
    errors: list[str] = []

    # 获取上次快照
    old_snapshot_data: Optional[dict[str, Any]] = None
    if request.script_intent == "sync":
        last_snapshot = get_latest_confirmed_snapshot(db, managed_agent_id)
        if last_snapshot is not None:
            old_snapshot_data = parse_snapshot_json(last_snapshot.snapshot_json)

    # Prompt 变更
    _compute_prompt_changes(
        items=items,
        errors=errors,
        old_data=old_snapshot_data,
        new_keys=request.prompt_artifact_keys,
        renderer_prompt_keys=renderer_prompt_keys,
    )

    # Schedule 变更
    _compute_schedule_changes(
        db=db,
        items=items,
        errors=errors,
        managed_agent_id=managed_agent_id,
        old_data=old_snapshot_data,
        new_ids=request.schedule_ids,
    )

    # Comm Binding 变更
    _compute_comm_binding_changes(
        db=db,
        items=items,
        errors=errors,
        managed_agent_id=managed_agent_id,
        old_data=old_snapshot_data,
        new_ids=request.comm_binding_ids,
    )

    return DeployChangeset(
        items=items,
        validation_errors=errors,
        is_valid=len(errors) == 0,
    )


# ---------------------------------------------------------------------------
# Prompt 变更
# ---------------------------------------------------------------------------

def _compute_prompt_changes(
    *,
    items: list[DeployChangesetItem],
    errors: list[str],
    old_data: Optional[dict[str, Any]],
    new_keys: list[str],
    renderer_prompt_keys: list[str],
) -> None:
    """计算 Prompt 资产的变更。"""
    valid_keys = set(renderer_prompt_keys)
    for key in new_keys:
        if key not in valid_keys:
            errors.append(f"不支持的 Prompt 资产 key: {key}")

    old_keys = set(old_data.get("prompt_artifact_keys", [])) if old_data else set()
    new_key_set = set(new_keys)

    for key in sorted(new_key_set - old_keys):
        items.append(DeployChangesetItem(
            resource_type="prompt",
            change_type="add",
            resource_key=key,
            label=f"Prompt: {key}",
        ))

    for key in sorted(new_key_set & old_keys):
        items.append(DeployChangesetItem(
            resource_type="prompt",
            change_type="update",
            resource_key=key,
            label=f"Prompt: {key}",
        ))

    for key in sorted(old_keys - new_key_set):
        items.append(DeployChangesetItem(
            resource_type="prompt",
            change_type="remove",
            resource_key=key,
            label=f"Prompt: {key}",
        ))


# ---------------------------------------------------------------------------
# Schedule 变更
# ---------------------------------------------------------------------------

def _compute_schedule_changes(
    *,
    db: Session,
    items: list[DeployChangesetItem],
    errors: list[str],
    managed_agent_id: str,
    old_data: Optional[dict[str, Any]],
    new_ids: list[str],
) -> None:
    """计算 Schedule 的变更。"""
    all_schedules = list_schedules(db, managed_agent_id)
    schedule_map = {s.id: s for s in all_schedules}

    # 校验所选 ID 归属当前 Agent
    for sid in new_ids:
        if sid not in schedule_map:
            errors.append(f"Schedule {sid} 不存在或不属于当前 Agent")

    # 校验所选 schedule 配置完整性
    for sid in new_ids:
        schedule = schedule_map.get(sid)
        if schedule:
            _validate_schedule_completeness(schedule, errors)

    old_ids = {s["id"] for s in old_data.get("schedules", [])} if old_data else set()
    old_schedule_map = {
        s["id"]: s for s in old_data.get("schedules", [])
    } if old_data else {}
    new_id_set = set(new_ids)

    for sid in sorted(new_id_set - old_ids):
        schedule = schedule_map.get(sid)
        label = f"Schedule: {schedule.name}" if schedule else f"Schedule: {sid}"
        items.append(DeployChangesetItem(
            resource_type="schedule",
            change_type="add",
            resource_id=sid,
            label=label,
            enabled=schedule.enabled if schedule else None,
        ))

    for sid in sorted(new_id_set & old_ids):
        schedule = schedule_map.get(sid)
        label = f"Schedule: {schedule.name}" if schedule else f"Schedule: {sid}"
        items.append(DeployChangesetItem(
            resource_type="schedule",
            change_type="update",
            resource_id=sid,
            label=label,
            enabled=schedule.enabled if schedule else None,
        ))

    for sid in sorted(old_ids - new_id_set):
        old_info = old_schedule_map.get(sid, {})
        label = f"Schedule: {old_info.get('name', sid)}"
        items.append(DeployChangesetItem(
            resource_type="schedule",
            change_type="remove",
            resource_id=sid,
            label=label,
        ))


def _validate_schedule_completeness(
    schedule: ManagedAgentSchedule,
    errors: list[str],
) -> None:
    """校验 schedule 配置完整性。"""
    if not schedule.schedule_type:
        errors.append(f"Schedule \"{schedule.name}\" 缺少 schedule_type")
    if not schedule.schedule_expr:
        errors.append(f"Schedule \"{schedule.name}\" 缺少 schedule_expr")
    if not schedule.timeout_seconds:
        errors.append(f"Schedule \"{schedule.name}\" 缺少 timeout_seconds")
    if not (schedule.schedule_message_content or "").strip():
        errors.append(f"Schedule \"{schedule.name}\" 缺少 schedule_message_content")


# ---------------------------------------------------------------------------
# Comm Binding 变更
# ---------------------------------------------------------------------------

def _compute_comm_binding_changes(
    *,
    db: Session,
    items: list[DeployChangesetItem],
    errors: list[str],
    managed_agent_id: str,
    old_data: Optional[dict[str, Any]],
    new_ids: list[str],
) -> None:
    """计算 Comm Binding 的变更。"""
    all_bindings = list_comm_bindings(db, managed_agent_id)
    binding_map = {b.id: b for b in all_bindings}

    for bid in new_ids:
        if bid not in binding_map:
            errors.append(f"Comm Binding {bid} 不存在或不属于当前 Agent")

    old_ids = {b["id"] for b in old_data.get("comm_bindings", [])} if old_data else set()
    old_binding_map = {
        b["id"]: b for b in old_data.get("comm_bindings", [])
    } if old_data else {}
    new_id_set = set(new_ids)

    for bid in sorted(new_id_set - old_ids):
        binding = binding_map.get(bid)
        label = f"Comm: {binding.binding_key}" if binding else f"Comm: {bid}"
        items.append(DeployChangesetItem(
            resource_type="comm_binding",
            change_type="add",
            resource_id=bid,
            label=label,
            enabled=binding.enabled if binding else None,
        ))

    for bid in sorted(new_id_set & old_ids):
        binding = binding_map.get(bid)
        label = f"Comm: {binding.binding_key}" if binding else f"Comm: {bid}"
        items.append(DeployChangesetItem(
            resource_type="comm_binding",
            change_type="update",
            resource_id=bid,
            label=label,
            enabled=binding.enabled if binding else None,
        ))

    for bid in sorted(old_ids - new_id_set):
        old_info = old_binding_map.get(bid, {})
        label = f"Comm: {old_info.get('binding_key', bid)}"
        items.append(DeployChangesetItem(
            resource_type="comm_binding",
            change_type="remove",
            resource_id=bid,
            label=label,
        ))
