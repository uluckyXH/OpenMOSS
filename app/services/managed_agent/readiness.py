"""
managed_agent 配置就绪度计算。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.managed_agent import (
    ManagedAgent,
    ManagedAgentCommBinding,
    ManagedAgentHostConfig,
    ManagedAgentPromptAsset,
    ManagedAgentSchedule,
)


def _empty_readiness() -> dict[str, object]:
    """默认就绪度。"""
    return {
        "host_config": False,
        "prompt_asset": False,
        "schedules_count": 0,
        "comm_bindings_count": 0,
        "deploy_ready": False,
    }


def compute_readiness_for_agents(
    db: Session,
    agents: Sequence[ManagedAgent],
) -> dict[str, dict[str, object]]:
    """批量计算配置态 Agent 就绪度。"""
    agent_ids = [agent.id for agent in agents]
    if not agent_ids:
        return {}

    host_configs = {
        item.managed_agent_id: item
        for item in db.query(ManagedAgentHostConfig)
        .filter(ManagedAgentHostConfig.managed_agent_id.in_(agent_ids))
        .all()
    }
    prompt_assets = {
        item.managed_agent_id: item
        for item in db.query(ManagedAgentPromptAsset)
        .filter(ManagedAgentPromptAsset.managed_agent_id.in_(agent_ids))
        .all()
    }
    schedule_counts = dict(
        db.query(ManagedAgentSchedule.managed_agent_id, func.count(ManagedAgentSchedule.id))
        .filter(ManagedAgentSchedule.managed_agent_id.in_(agent_ids))
        .group_by(ManagedAgentSchedule.managed_agent_id)
        .all()
    )
    comm_binding_counts = dict(
        db.query(ManagedAgentCommBinding.managed_agent_id, func.count(ManagedAgentCommBinding.id))
        .filter(ManagedAgentCommBinding.managed_agent_id.in_(agent_ids))
        .group_by(ManagedAgentCommBinding.managed_agent_id)
        .all()
    )

    readiness_map: dict[str, dict[str, object]] = {}
    for agent_id in agent_ids:
        host_config = host_configs.get(agent_id)
        prompt_asset = prompt_assets.get(agent_id)
        host_ready = bool(
            host_config
            and (
                (host_config.host_agent_identifier or "").strip()
                or (host_config.workdir_path or "").strip()
            )
        )
        prompt_ready = bool(
            prompt_asset
            and (
                (prompt_asset.system_prompt_content or "").strip()
                or (prompt_asset.persona_prompt_content or "").strip()
                or (prompt_asset.identity_content or "").strip()
            )
        )

        readiness_map[agent_id] = {
            "host_config": host_ready,
            "prompt_asset": prompt_ready,
            "schedules_count": int(schedule_counts.get(agent_id, 0)),
            "comm_bindings_count": int(comm_binding_counts.get(agent_id, 0)),
            "deploy_ready": host_ready,
        }

    return readiness_map


def compute_readiness_for_agent(db: Session, agent: ManagedAgent) -> dict[str, object]:
    """计算单个配置态 Agent 就绪度。"""
    return compute_readiness_for_agents(db, [agent]).get(agent.id, _empty_readiness())
