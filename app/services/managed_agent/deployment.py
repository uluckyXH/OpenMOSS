"""
部署快照 CRUD 服务

管理 deployment snapshot 的创建、确认、失败、忽略等操作。
设计文档：dev-docs/agent-config-center/13-选择式脚本生成与部署变更集设计.md §7
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.managed_agent import ManagedAgentDeploymentSnapshot

from .core import get_managed_agent_or_404


# ---------------------------------------------------------------------------
# snapshot_json 构建
# ---------------------------------------------------------------------------

def build_snapshot_json(
    *,
    prompt_artifact_keys: list[str],
    schedules: list[dict[str, Any]],
    comm_bindings: list[dict[str, Any]],
) -> str:
    """构建 snapshot_json 文本。

    只存 ID + 最小标识信息，不存内容。
    schedules 列表项需包含 id / name。
    comm_bindings 列表项需包含 id / provider / binding_key。
    """
    payload = {
        "prompt_artifact_keys": sorted(prompt_artifact_keys),
        "schedules": [
            {"id": s["id"], "name": s.get("name", "")}
            for s in schedules
        ],
        "comm_bindings": [
            {"id": b["id"], "provider": b.get("provider", ""), "binding_key": b.get("binding_key", "")}
            for b in comm_bindings
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def parse_snapshot_json(raw: str) -> dict[str, Any]:
    """解析 snapshot_json 文本为字典。"""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {"prompt_artifact_keys": [], "schedules": [], "comm_bindings": []}
    if not isinstance(data, dict):
        return {"prompt_artifact_keys": [], "schedules": [], "comm_bindings": []}
    return data


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------

def create_deployment_snapshot(
    db: Session,
    *,
    managed_agent_id: str,
    script_intent: str,
    config_version: int,
    snapshot_json: str,
    timeout_seconds: int = 1800,
) -> ManagedAgentDeploymentSnapshot:
    """创建 pending 状态的部署快照。"""
    get_managed_agent_or_404(db, managed_agent_id)

    now = datetime.now()
    row = ManagedAgentDeploymentSnapshot(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        script_intent=script_intent,
        config_version=config_version,
        snapshot_json=snapshot_json,
        status="pending",
        created_at=now,
        expires_at=now + timedelta(seconds=timeout_seconds),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def expire_stale_pending_snapshots(db: Session) -> int:
    """将已过期的 pending 部署快照标记为 timeout。"""
    now = datetime.now()
    rows = (
        db.query(ManagedAgentDeploymentSnapshot)
        .filter(ManagedAgentDeploymentSnapshot.status == "pending")
        .filter(ManagedAgentDeploymentSnapshot.expires_at.isnot(None))
        .filter(ManagedAgentDeploymentSnapshot.expires_at < now)
        .all()
    )

    for row in rows:
        elapsed = int((now - row.created_at).total_seconds()) if row.created_at else None
        detail = {
            "message": f"部署脚本在 {elapsed} 秒内未回传结果，已自动标记超时",
            "elapsed_seconds": elapsed,
        }
        row.status = "timeout"
        row.failure_detail_json = json.dumps(detail, ensure_ascii=False)

    if rows:
        db.commit()
    return len(rows)


def confirm_deployment_snapshot(
    db: Session,
    snapshot_id: str,
    managed_agent_id: str,
) -> ManagedAgentDeploymentSnapshot:
    """确认部署成功，追平 deployed_config_version。"""
    snapshot = _get_snapshot_or_404(db, snapshot_id, managed_agent_id)
    if snapshot.status != "pending":
        raise ValidationError(f"快照状态为 {snapshot.status}，无法确认")

    now = datetime.now()
    snapshot.status = "confirmed"
    snapshot.confirmed_at = now

    managed_agent = get_managed_agent_or_404(db, managed_agent_id)
    managed_agent.deployed_config_version = snapshot.config_version
    managed_agent.updated_at = now

    db.commit()
    db.refresh(snapshot)
    return snapshot


def fail_deployment_snapshot(
    db: Session,
    snapshot_id: str,
    managed_agent_id: str,
    *,
    exit_code: Optional[int] = None,
    last_stage: Optional[str] = None,
    message: Optional[str] = None,
) -> ManagedAgentDeploymentSnapshot:
    """标记部署失败。"""
    snapshot = _get_snapshot_or_404(db, snapshot_id, managed_agent_id)
    if snapshot.status != "pending":
        raise ValidationError(f"快照状态为 {snapshot.status}，无法标记失败")

    detail: dict[str, Any] = {}
    if exit_code is not None:
        detail["exit_code"] = exit_code
    if last_stage is not None:
        detail["last_stage"] = last_stage
    if message is not None:
        detail["message"] = message

    snapshot.status = "failed"
    snapshot.failure_detail_json = json.dumps(detail, ensure_ascii=False) if detail else None

    db.commit()
    db.refresh(snapshot)
    return snapshot


def get_latest_confirmed_snapshot(
    db: Session,
    managed_agent_id: str,
) -> Optional[ManagedAgentDeploymentSnapshot]:
    """获取最近一次 confirmed 的快照。"""
    return (
        db.query(ManagedAgentDeploymentSnapshot)
        .filter(ManagedAgentDeploymentSnapshot.managed_agent_id == managed_agent_id)
        .filter(ManagedAgentDeploymentSnapshot.status == "confirmed")
        .order_by(ManagedAgentDeploymentSnapshot.confirmed_at.desc())
        .first()
    )


def list_deployment_snapshots(
    db: Session,
    managed_agent_id: str,
) -> list[ManagedAgentDeploymentSnapshot]:
    """列出某个 Agent 的所有部署快照。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return (
        db.query(ManagedAgentDeploymentSnapshot)
        .filter(ManagedAgentDeploymentSnapshot.managed_agent_id == managed_agent_id)
        .order_by(ManagedAgentDeploymentSnapshot.created_at.desc())
        .all()
    )


def dismiss_snapshot_resources(
    db: Session,
    managed_agent_id: str,
    *,
    schedule_ids: Optional[list[str]] = None,
    comm_binding_ids: Optional[list[str]] = None,
    prompt_artifact_keys: Optional[list[str]] = None,
) -> Optional[ManagedAgentDeploymentSnapshot]:
    """从最近 confirmed 快照中移除指定资源，使 diff 不再产出该删除项。"""
    snapshot = get_latest_confirmed_snapshot(db, managed_agent_id)
    if snapshot is None:
        return None

    data = parse_snapshot_json(snapshot.snapshot_json)
    modified = False

    if schedule_ids:
        dismiss_set = set(schedule_ids)
        original_len = len(data.get("schedules", []))
        data["schedules"] = [
            s for s in data.get("schedules", []) if s.get("id") not in dismiss_set
        ]
        if len(data["schedules"]) != original_len:
            modified = True

    if comm_binding_ids:
        dismiss_set = set(comm_binding_ids)
        original_len = len(data.get("comm_bindings", []))
        data["comm_bindings"] = [
            b for b in data.get("comm_bindings", []) if b.get("id") not in dismiss_set
        ]
        if len(data["comm_bindings"]) != original_len:
            modified = True

    if prompt_artifact_keys:
        dismiss_set = set(prompt_artifact_keys)
        original_len = len(data.get("prompt_artifact_keys", []))
        data["prompt_artifact_keys"] = [
            k for k in data.get("prompt_artifact_keys", []) if k not in dismiss_set
        ]
        if len(data["prompt_artifact_keys"]) != original_len:
            modified = True

    if modified:
        snapshot.snapshot_json = json.dumps(data, ensure_ascii=False, sort_keys=True)
        db.commit()
        db.refresh(snapshot)

    return snapshot


def serialize_deployment_snapshot(snapshot: ManagedAgentDeploymentSnapshot) -> dict[str, Any]:
    """序列化部署快照。"""
    is_likely_timeout = (
        snapshot.status == "pending"
        and snapshot.expires_at is not None
        and datetime.now() > snapshot.expires_at
    )
    return {
        "id": snapshot.id,
        "managed_agent_id": snapshot.managed_agent_id,
        "script_intent": snapshot.script_intent,
        "config_version": snapshot.config_version,
        "snapshot_json": snapshot.snapshot_json,
        "status": snapshot.status,
        "failure_detail_json": snapshot.failure_detail_json,
        "created_at": snapshot.created_at,
        "expires_at": snapshot.expires_at,
        "confirmed_at": snapshot.confirmed_at,
        "is_likely_timeout": is_likely_timeout,
    }


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _get_snapshot_or_404(
    db: Session,
    snapshot_id: str,
    managed_agent_id: str,
) -> ManagedAgentDeploymentSnapshot:
    """按 ID 获取快照，必须归属指定 Agent。"""
    row = (
        db.query(ManagedAgentDeploymentSnapshot)
        .filter(ManagedAgentDeploymentSnapshot.id == snapshot_id)
        .filter(ManagedAgentDeploymentSnapshot.managed_agent_id == managed_agent_id)
        .first()
    )
    if not row:
        raise NotFoundError(f"部署快照不存在: {snapshot_id}")
    return row
