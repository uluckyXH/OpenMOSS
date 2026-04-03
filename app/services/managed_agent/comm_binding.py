"""
managed_agent 宿主通讯渠道配置服务。
"""

import uuid
from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from app.models.managed_agent import ManagedAgentCommBinding

from .core import get_managed_agent_or_404
from .shared import _bump_config_version, _mask, _normalize_comm_binding_kwargs


def list_comm_bindings(db: Session, managed_agent_id: str) -> List[ManagedAgentCommBinding]:
    """获取宿主通讯渠道配置。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return db.query(ManagedAgentCommBinding).filter(
        ManagedAgentCommBinding.managed_agent_id == managed_agent_id
    ).all()


def get_comm_binding_or_404(db: Session, binding_id: str) -> ManagedAgentCommBinding:
    """获取宿主通讯渠道配置，不存在则抛异常。"""
    binding = db.query(ManagedAgentCommBinding).filter(
        ManagedAgentCommBinding.id == binding_id
    ).first()
    if not binding:
        raise ValueError(f"宿主通讯渠道配置不存在: {binding_id}")
    return binding


def create_comm_binding(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentCommBinding:
    """创建宿主通讯渠道配置。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    normalized = _normalize_comm_binding_kwargs(kwargs)

    if not normalized.get("provider") or not normalized.get("binding_key"):
        raise ValueError("provider 和 binding_key 不能为空")

    binding = ManagedAgentCommBinding(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        **normalized,
    )
    db.add(binding)
    _bump_config_version(db, agent)
    db.commit()
    db.refresh(binding)
    return binding


def update_comm_binding(db: Session, binding_id: str, **kwargs) -> ManagedAgentCommBinding:
    """更新宿主通讯渠道配置。"""
    binding = get_comm_binding_or_404(db, binding_id)
    agent = get_managed_agent_or_404(db, binding.managed_agent_id)
    normalized = _normalize_comm_binding_kwargs(kwargs)

    changed = False
    for key, value in normalized.items():
        if value is not None and hasattr(binding, key) and getattr(binding, key) != value:
            setattr(binding, key, value)
            changed = True

    if changed:
        binding.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(binding)
    return binding


def delete_comm_binding(db: Session, binding_id: str) -> None:
    """删除宿主通讯渠道配置。"""
    binding = get_comm_binding_or_404(db, binding_id)
    agent = get_managed_agent_or_404(db, binding.managed_agent_id)
    db.delete(binding)
    _bump_config_version(db, agent)
    db.commit()


def serialize_comm_binding(binding: ManagedAgentCommBinding) -> Dict[str, object]:
    """把宿主通讯渠道配置模型转成 API 响应 dict。"""
    return {
        "id": binding.id,
        "managed_agent_id": binding.managed_agent_id,
        "provider": binding.provider,
        "binding_key": binding.binding_key,
        "display_name": binding.display_name,
        "enabled": binding.enabled,
        "routing_policy_json": binding.routing_policy_json,
        "metadata_json": binding.metadata_json,
        "config_payload_masked": _mask(binding.config_payload_encrypted),
        "created_at": binding.created_at,
        "updated_at": binding.updated_at,
    }
