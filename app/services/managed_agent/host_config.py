"""
managed_agent 宿主配置服务。
"""

from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.managed_agent import ManagedAgentHostConfig

from .core import get_managed_agent_or_404
from .shared import _bump_config_version, _ensure_host_config, _mask, _normalize_host_config_kwargs


def get_host_config(db: Session, managed_agent_id: str) -> Optional[ManagedAgentHostConfig]:
    """获取宿主平台配置。"""
    return db.query(ManagedAgentHostConfig).filter(
        ManagedAgentHostConfig.managed_agent_id == managed_agent_id
    ).first()


def update_host_config(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentHostConfig:
    """更新宿主平台配置。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    host_config = _ensure_host_config(db, agent)
    normalized = _normalize_host_config_kwargs(kwargs)

    changed = False
    for key, value in normalized.items():
        if hasattr(host_config, key) and getattr(host_config, key) != value:
            setattr(host_config, key, value)
            changed = True

    if host_config.host_platform != agent.host_platform:
        host_config.host_platform = agent.host_platform
        changed = True

    if changed:
        host_config.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(host_config)
    return host_config


def serialize_host_config(host_config: ManagedAgentHostConfig) -> Dict[str, object]:
    """把宿主配置模型转成 API 响应 dict。"""
    return {
        "id": host_config.id,
        "managed_agent_id": host_config.managed_agent_id,
        "host_platform": host_config.host_platform,
        "host_agent_identifier": host_config.host_agent_identifier,
        "workdir_path": host_config.workdir_path,
        "host_config_payload_masked": _mask(host_config.host_config_payload_encrypted),
        "host_metadata_json": host_config.host_metadata_json,
        "created_at": host_config.created_at,
        "updated_at": host_config.updated_at,
    }
