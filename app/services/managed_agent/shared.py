"""
managed_agent 子系统共享工具。
"""

import re
import uuid
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy.orm import Session

from app.models.managed_agent import ManagedAgent, ManagedAgentHostConfig, ManagedAgentPromptAsset


def _generate_slug(name: str) -> str:
    """从名称生成 slug。"""
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff-]", "-", name.strip().lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = str(uuid.uuid4())[:8]
    return slug


def _bump_config_version(db: Session, managed_agent: ManagedAgent) -> None:
    """递增配置版本。"""
    managed_agent.config_version = (managed_agent.config_version or 0) + 1
    managed_agent.updated_at = datetime.now()
    db.flush()


def _mask(value: Optional[str]) -> Optional[str]:
    """简单脱敏。"""
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}***{value[-2:]}"


def _default_render_strategy(host_platform: str, deployment_mode: str) -> str:
    """根据宿主平台和部署模式给出默认渲染策略。"""
    if host_platform == "openclaw":
        if deployment_mode == "bind_main_agent":
            return "openclaw_inline_schedule"
        return "openclaw_workspace_files"
    return "host_default"


def _ensure_host_config(db: Session, agent: ManagedAgent) -> ManagedAgentHostConfig:
    """确保宿主配置记录存在。"""
    host_config = db.query(ManagedAgentHostConfig).filter(
        ManagedAgentHostConfig.managed_agent_id == agent.id
    ).first()
    if host_config:
        return host_config

    host_config = ManagedAgentHostConfig(
        id=str(uuid.uuid4()),
        managed_agent_id=agent.id,
        host_platform=agent.host_platform,
    )
    db.add(host_config)
    db.flush()
    return host_config


def _ensure_prompt_asset(db: Session, agent: ManagedAgent) -> ManagedAgentPromptAsset:
    """确保 Prompt 资产记录存在。"""
    prompt_asset = db.query(ManagedAgentPromptAsset).filter(
        ManagedAgentPromptAsset.managed_agent_id == agent.id
    ).first()
    if prompt_asset:
        return prompt_asset

    prompt_asset = ManagedAgentPromptAsset(
        id=str(uuid.uuid4()),
        managed_agent_id=agent.id,
        template_role=agent.role,
        host_render_strategy=_default_render_strategy(agent.host_platform, agent.deployment_mode),
        authority_source="database",
    )
    db.add(prompt_asset)
    db.flush()
    return prompt_asset


def _normalize_host_config_kwargs(kwargs: Dict[str, object]) -> Dict[str, object]:
    """标准化宿主配置字段。"""
    data = dict(kwargs)
    if "host_config_payload" in data:
        data["host_config_payload_encrypted"] = data.pop("host_config_payload")
    return {
        key: value
        for key, value in data.items()
        if key in {
            "host_agent_identifier",
            "workdir_path",
            "host_config_payload_encrypted",
            "host_metadata_json",
        }
    }


def _normalize_prompt_asset_kwargs(kwargs: Dict[str, object]) -> Dict[str, object]:
    """标准化 Prompt 资产字段。"""
    data = dict(kwargs)
    for field_name in {"system_prompt_content", "persona_prompt_content", "identity_content"}:
        if field_name in data and data[field_name] is None:
            data[field_name] = ""

    return {
        key: value
        for key, value in data.items()
        if key in {
            "system_prompt_content",
            "persona_prompt_content",
            "identity_content",
            "host_render_strategy",
            "notes",
        }
    }


def _normalize_schedule_kwargs(
    kwargs: Dict[str, object],
    existing_execution_options_json: Optional[str] = None,
) -> Dict[str, object]:
    """标准化定时任务字段。"""
    data = dict(kwargs)
    if "schedule_message_content" in data and data["schedule_message_content"] is None:
        data["schedule_message_content"] = ""

    return {
        key: value
        for key, value in data.items()
        if key in {
            "name",
            "enabled",
            "schedule_type",
            "schedule_expr",
            "timeout_seconds",
            "model_override",
            "execution_options_json",
            "schedule_message_content",
        }
    }


def _normalize_comm_binding_kwargs(kwargs: Dict[str, object]) -> Dict[str, object]:
    """标准化宿主通讯渠道配置字段。"""
    data = dict(kwargs)
    if "config_payload" in data:
        data["config_payload_encrypted"] = data.pop("config_payload")

    return {
        key: value
        for key, value in data.items()
        if key in {
            "provider",
            "binding_key",
            "display_name",
            "enabled",
            "routing_policy_json",
            "metadata_json",
            "config_payload_encrypted",
        }
    }
