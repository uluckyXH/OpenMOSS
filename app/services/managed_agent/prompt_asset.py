"""
managed_agent Prompt 资产与模板示例服务。
"""

from datetime import datetime
from pathlib import Path
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


ROLE_TEMPLATE_LABELS = {
    "planner": "任务规划师",
    "executor": "任务执行者",
    "reviewer": "任务审查者",
    "patrol": "任务巡查者",
}

ROLE_TEMPLATE_ORDER = ("planner", "executor", "reviewer", "patrol")


def _template_dir() -> Path:
    """返回角色模板目录。"""
    return Path(__file__).resolve().parents[3] / "prompts" / "templates"


def _resolve_role_template_file(role: str) -> Optional[Path]:
    """按角色解析模板文件路径，兼容 {role}.md / task-{role}.md。"""
    template_dir = _template_dir()
    for candidate_name in (f"{role}.md", f"task-{role}.md"):
        candidate = template_dir / candidate_name
        if candidate.exists():
            return candidate
    return None


def list_prompt_templates(role: Optional[str] = None) -> list[Dict[str, str]]:
    """列出 Agent 管理域可用的角色模板示例。"""
    roles = [role] if role else list(ROLE_TEMPLATE_ORDER)
    items: list[Dict[str, str]] = []

    for current_role in roles:
        template_file = _resolve_role_template_file(current_role)
        if not template_file:
            continue
        items.append(
            {
                "role": current_role,
                "label": ROLE_TEMPLATE_LABELS.get(current_role, current_role),
                "filename": template_file.name,
                "content": template_file.read_text(encoding="utf-8"),
            }
        )

    return items


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
    role = agent.role
    template_file = _resolve_role_template_file(role)

    if not template_file:
        raise BusinessError(f"角色模板不存在: {role}")

    prompt_asset.system_prompt_content = template_file.read_text(encoding="utf-8")

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
