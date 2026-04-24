"""
managed_agent 运行态身份服务。
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError
from app.models.agent import Agent
from app.models.managed_agent import ManagedAgent
from app.services.agent_runtime import generate_api_key

from .core import get_managed_agent_or_404
from .shared import _mask


def _serialize_runtime_identity(
    managed_agent: ManagedAgent,
    runtime_agent: Agent | None,
) -> dict[str, object]:
    """序列化配置态 Agent 关联的运行态身份摘要。"""
    return {
        "registered": bool(managed_agent.runtime_agent_id and runtime_agent),
        "runtime_agent_id": managed_agent.runtime_agent_id,
        "api_key_masked": _mask(runtime_agent.api_key) if runtime_agent else None,
    }


def compute_runtime_identity_for_agents(
    db: Session,
    agents: Sequence[ManagedAgent],
) -> dict[str, dict[str, object]]:
    """批量计算配置态 Agent 的运行态身份摘要。"""
    runtime_ids = [
        agent.runtime_agent_id
        for agent in agents
        if agent.runtime_agent_id
    ]
    runtime_agents = {}
    if runtime_ids:
        runtime_agents = {
            item.id: item
            for item in db.query(Agent).filter(Agent.id.in_(runtime_ids)).all()
        }

    return {
        agent.id: _serialize_runtime_identity(
            agent,
            runtime_agents.get(agent.runtime_agent_id) if agent.runtime_agent_id else None,
        )
        for agent in agents
    }


def compute_runtime_identity_for_agent(
    db: Session,
    managed_agent: ManagedAgent,
) -> dict[str, object]:
    """计算单个配置态 Agent 的运行态身份摘要。"""
    return compute_runtime_identity_for_agents(db, [managed_agent]).get(
        managed_agent.id,
        {
            "registered": False,
            "runtime_agent_id": managed_agent.runtime_agent_id,
            "api_key_masked": None,
        },
    )


def reset_runtime_api_key_for_managed_agent(
    db: Session,
    managed_agent_id: str,
) -> dict[str, object]:
    """重置配置态 Agent 关联运行态 Agent 的 API Key，并仅本次返回明文。"""
    managed_agent = get_managed_agent_or_404(db, managed_agent_id)
    if not managed_agent.runtime_agent_id:
        raise ConflictError("该配置态 Agent 尚未完成运行态注册，无法重置 API Key")

    runtime_agent = db.query(Agent).filter(Agent.id == managed_agent.runtime_agent_id).first()
    if not runtime_agent:
        raise NotFoundError(f"运行态 Agent 不存在: {managed_agent.runtime_agent_id}")

    runtime_agent.api_key = generate_api_key()
    db.commit()
    db.refresh(runtime_agent)

    return {
        "runtime_agent_id": runtime_agent.id,
        "api_key": runtime_agent.api_key,
        "api_key_masked": _mask(runtime_agent.api_key),
        "message": "API Key 已重置，请立即复制，关闭后不可再次查看完整值",
    }
