"""
数据库结构兼容探测服务。

当前版本的目标不是做复杂迁移，而是先给“旧运行态回填”和
“配置中心能力开关”提供一个统一、可测试的探测入口。
"""

from __future__ import annotations

from typing import Dict, Set

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.managed_agent import ManagedAgent


LEGACY_RUNTIME_TABLES = {
    "agent",
    "task",
    "module",
    "sub_task",
    "rule",
    "activity_log",
    "review_record",
    "reward_log",
    "patrol_record",
    "request_log",
}

MANAGED_AGENT_TABLES = {
    "managed_agent",
    "managed_agent_host_config",
    "managed_agent_prompt_asset",
    "managed_agent_schedule",
    "managed_agent_comm_binding",
    "managed_agent_bootstrap_token",
    "agent_runtime_presence",
}

LEGACY_AGENT_REQUIRED_COLUMNS = {
    "id",
    "name",
    "role",
    "description",
    "status",
    "api_key",
}

MANAGED_AGENT_REQUIRED_COLUMNS = {
    "id",
    "name",
    "slug",
    "role",
    "host_platform",
    "deployment_mode",
    "host_access_mode",
    "runtime_agent_id",
}


def _get_table_names(db: Session) -> Set[str]:
    """读取当前数据库中的全部表名。"""
    inspector = inspect(db.get_bind())
    return set(inspector.get_table_names())


def _get_column_names(db: Session, table_name: str) -> Set[str]:
    """读取指定表的列名。"""
    inspector = inspect(db.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def detect_legacy_tables(db: Session) -> Dict[str, object]:
    """探测旧运行态表与配置中心表的可用性。

    这里的 `has_legacy` 不再简单等于“旧表是否存在”，因为运行态表在当前版本仍然保留。
    它表示：当前数据库中是否还有“仅存在于旧运行态、尚未回填到 managed_agent”的 Agent 数据。
    """

    table_names = _get_table_names(db)

    legacy_table_flags = {table: table in table_names for table in sorted(LEGACY_RUNTIME_TABLES)}
    managed_table_flags = {table: table in table_names for table in sorted(MANAGED_AGENT_TABLES)}

    legacy_agent_columns = (
        _get_column_names(db, "agent") if legacy_table_flags.get("agent") else set()
    )
    managed_agent_columns = (
        _get_column_names(db, "managed_agent") if managed_table_flags.get("managed_agent") else set()
    )

    legacy_runtime_agent_count = 0
    managed_agent_count = 0
    unmanaged_runtime_agent_count = 0

    if legacy_table_flags.get("agent"):
        legacy_runtime_agent_count = db.query(Agent).count()

    if managed_table_flags.get("managed_agent"):
        managed_agent_count = db.query(ManagedAgent).count()

    if legacy_table_flags.get("agent") and managed_table_flags.get("managed_agent"):
        unmanaged_runtime_agent_count = (
            db.query(Agent)
            .outerjoin(ManagedAgent, ManagedAgent.runtime_agent_id == Agent.id)
            .filter(ManagedAgent.id.is_(None))
            .count()
        )
    else:
        unmanaged_runtime_agent_count = legacy_runtime_agent_count

    return {
        "has_legacy": unmanaged_runtime_agent_count > 0,
        "legacy_runtime_tables": legacy_table_flags,
        "managed_agent_tables": managed_table_flags,
        "missing_legacy_runtime_tables": sorted(table for table, exists in legacy_table_flags.items() if not exists),
        "missing_managed_agent_tables": sorted(table for table, exists in managed_table_flags.items() if not exists),
        "legacy_agent_columns_ok": LEGACY_AGENT_REQUIRED_COLUMNS.issubset(legacy_agent_columns),
        "managed_agent_columns_ok": MANAGED_AGENT_REQUIRED_COLUMNS.issubset(managed_agent_columns),
        "legacy_runtime_agent_count": legacy_runtime_agent_count,
        "managed_agent_count": managed_agent_count,
        "unmanaged_runtime_agent_count": unmanaged_runtime_agent_count,
    }


def get_schema_capabilities(db: Session) -> Dict[str, object]:
    """输出当前数据库可用能力，用于后续回填和配置中心启动判断。"""

    detection = detect_legacy_tables(db)
    bind = db.get_bind()
    backend_name = bind.dialect.name if bind is not None else "unknown"

    managed_table_flags = detection["managed_agent_tables"]

    return {
        "database_backend": backend_name,
        "supports_runtime_agent_registry": detection["legacy_runtime_tables"].get("agent", False),
        "supports_managed_agent_config_center": not detection["missing_managed_agent_tables"],
        "supports_host_config": managed_table_flags.get("managed_agent_host_config", False),
        "supports_prompt_asset": managed_table_flags.get("managed_agent_prompt_asset", False),
        "supports_schedule": managed_table_flags.get("managed_agent_schedule", False),
        "supports_comm_binding": managed_table_flags.get("managed_agent_comm_binding", False),
        "supports_bootstrap_token": managed_table_flags.get("managed_agent_bootstrap_token", False),
        "supports_runtime_presence": managed_table_flags.get("agent_runtime_presence", False),
        "has_legacy_runtime_agents": detection["has_legacy"],
        "legacy_runtime_agent_count": detection["legacy_runtime_agent_count"],
        "managed_agent_count": detection["managed_agent_count"],
        "unmanaged_runtime_agent_count": detection["unmanaged_runtime_agent_count"],
        "backfill_needed": detection["has_legacy"] and not detection["missing_managed_agent_tables"],
    }
