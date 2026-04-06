"""
managed_agent Prompt 资产服务。
"""

import os
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.exceptions import BusinessError
from app.models.managed_agent import ManagedAgentPromptAsset
from app.services.host_renderers import get_renderer

from .core import get_managed_agent_or_404
from .shared import (
    _bump_config_version,
    _default_render_strategy,
    _ensure_host_config,
    _ensure_prompt_asset,
    _normalize_prompt_asset_kwargs,
)


def get_prompt_asset(db: Session, managed_agent_id: str) -> Optional[ManagedAgentPromptAsset]:
    """获取 Prompt 资产。"""
    return db.query(ManagedAgentPromptAsset).filter(
        ManagedAgentPromptAsset.managed_agent_id == managed_agent_id
    ).first()


def update_prompt_asset(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentPromptAsset:
    """更新 Prompt 资产。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    prompt_asset = _ensure_prompt_asset(db, agent)
    normalized = _normalize_prompt_asset_kwargs(kwargs)

    changed = False
    for key, value in normalized.items():
        if hasattr(prompt_asset, key) and getattr(prompt_asset, key) != value:
            setattr(prompt_asset, key, value)
            changed = True

    if changed:
        prompt_asset.authority_source = "database"
        prompt_asset.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(prompt_asset)
    return prompt_asset


def reset_prompt_from_template(db: Session, managed_agent_id: str) -> ManagedAgentPromptAsset:
    """从角色模板重新初始化 Prompt 资产。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    prompt_asset = _ensure_prompt_asset(db, agent)

    template_dir = os.path.join(os.getcwd(), "prompts", "templates")
    role = agent.role
    candidate_files = [
        os.path.join(template_dir, f"{role}.md"),
        os.path.join(template_dir, f"task-{role}.md"),
    ]
    template_file = next((path for path in candidate_files if os.path.exists(path)), None)

    if not template_file:
        raise BusinessError(f"角色模板不存在: {role}")

    with open(template_file, "r", encoding="utf-8") as f:
        prompt_asset.system_prompt_content = f.read()

    prompt_asset.template_role = role
    prompt_asset.host_render_strategy = _default_render_strategy(
        agent.host_platform, agent.deployment_mode
    )
    prompt_asset.authority_source = "database"
    prompt_asset.updated_at = datetime.now()
    _bump_config_version(db, agent)

    db.commit()
    db.refresh(prompt_asset)
    return prompt_asset


def render_prompt_preview(db: Session, managed_agent_id: str) -> Dict[str, object]:
    """按宿主平台渲染 Prompt 预览。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    host_config = _ensure_host_config(db, agent)
    prompt_asset = _ensure_prompt_asset(db, agent)
    renderer = get_renderer(agent.host_platform)

    artifacts = renderer.render_prompt_artifacts(
        managed_agent=agent,
        host_config=host_config,
        prompt_asset=prompt_asset,
    )

    return {
        "host_platform": agent.host_platform,
        "host_render_strategy": prompt_asset.host_render_strategy,
        "artifacts": artifacts,
    }
