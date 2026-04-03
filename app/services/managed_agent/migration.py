"""
managed_agent 迁移与回填服务。
"""

import uuid
from typing import Dict

from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.managed_agent import ManagedAgent, ManagedAgentHostConfig, ManagedAgentPromptAsset
from app.services.schema_compat_service import detect_legacy_tables, get_schema_capabilities

from .shared import _default_render_strategy, _generate_slug


def build_migration_report(db: Session) -> Dict[str, object]:
    """生成当前数据库的最小迁移报告。"""
    detection = detect_legacy_tables(db)
    capabilities = get_schema_capabilities(db)
    can_auto_backfill = (
        capabilities["supports_runtime_agent_registry"]
        and capabilities["supports_managed_agent_config_center"]
        and detection["legacy_agent_columns_ok"]
        and detection["managed_agent_columns_ok"]
    )

    return {
        "database_backend": capabilities["database_backend"],
        "can_auto_backfill": can_auto_backfill,
        "backfill_needed": capabilities["backfill_needed"],
        "legacy_runtime_agent_count": detection["legacy_runtime_agent_count"],
        "managed_agent_count": detection["managed_agent_count"],
        "unmanaged_runtime_agent_count": detection["unmanaged_runtime_agent_count"],
        "missing_legacy_runtime_tables": detection["missing_legacy_runtime_tables"],
        "missing_managed_agent_tables": detection["missing_managed_agent_tables"],
        "legacy_agent_columns_ok": detection["legacy_agent_columns_ok"],
        "managed_agent_columns_ok": detection["managed_agent_columns_ok"],
    }


def _build_unique_slug(db: Session, name: str) -> str:
    """为回填出来的 managed_agent 生成稳定且唯一的 slug。"""
    slug = _generate_slug(name)
    base_slug = slug
    counter = 1

    while db.query(ManagedAgent).filter(ManagedAgent.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


def auto_backfill_from_runtime(db: Session) -> Dict[str, object]:
    """把已有的运行态 agent 回填到 managed_agent。"""
    report = build_migration_report(db)
    summary = {
        "created": 0,
        "skipped": 0,
        "failed": 0,
        "can_auto_backfill": report["can_auto_backfill"],
        "backfill_needed": report["backfill_needed"],
        "legacy_runtime_agent_count": report["legacy_runtime_agent_count"],
        "managed_agent_count_before": report["managed_agent_count"],
    }

    if not report["can_auto_backfill"]:
        return summary

    agents = db.query(Agent).all()

    for runtime_agent in agents:
        try:
            existing = db.query(ManagedAgent).filter(
                ManagedAgent.runtime_agent_id == runtime_agent.id
            ).first()
            if existing:
                summary["skipped"] += 1
                continue

            managed = ManagedAgent(
                id=str(uuid.uuid4()),
                name=runtime_agent.name,
                slug=_build_unique_slug(db, runtime_agent.name),
                role=runtime_agent.role,
                description=runtime_agent.description or "",
                host_platform="openclaw",
                deployment_mode="bind_existing_agent",
                host_access_mode="local",
                status="deployed",
                runtime_agent_id=runtime_agent.id,
                config_version=1,
                deployed_config_version=1,
            )
            db.add(managed)
            db.flush()

            db.add(
                ManagedAgentHostConfig(
                    id=str(uuid.uuid4()),
                    managed_agent_id=managed.id,
                    host_platform=managed.host_platform,
                )
            )
            db.add(
                ManagedAgentPromptAsset(
                    id=str(uuid.uuid4()),
                    managed_agent_id=managed.id,
                    template_role=managed.role,
                    host_render_strategy=_default_render_strategy(
                        managed.host_platform, managed.deployment_mode
                    ),
                    authority_source="database",
                )
            )

            db.commit()
            summary["created"] += 1
        except Exception as exc:
            db.rollback()
            summary["failed"] += 1
            print(f"[ManagedAgent] 回填失败 (跳过): agent={runtime_agent.name}, error={exc}")

    if summary["created"] or summary["failed"]:
        print(
            "[ManagedAgent] 回填完成: "
            f"成功={summary['created']}, 跳过={summary['skipped']}, 失败={summary['failed']}"
        )

    return summary
