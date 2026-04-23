"""Bootstrap 脚本渲染：把配置态 Agent 的上下文渲染为可执行 shell 脚本。"""

from __future__ import annotations

import json
import shlex
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import config
from app.exceptions import NotFoundError, ValidationError
from app.services.host_renderers import get_renderer
from app.services.managed_agent import (
    get_host_config,
    get_prompt_asset,
    list_comm_bindings,
    list_schedules,
)
from app.services.managed_agent.core import get_managed_agent_or_404


REPO_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_ROOT = REPO_ROOT / "shells" / "templates"
SUPPORTED_COMM_PROVIDER_TEMPLATES = {
    "feishu": "comm_providers/feishu/bind_account.sh.tpl",
}


def _load_template(relative_path: str) -> str:
    """读取 shell 模板。"""
    path = TEMPLATE_ROOT / relative_path
    if not path.exists():
        raise NotFoundError(f"Shell 模板不存在: {relative_path}")
    return path.read_text(encoding="utf-8").rstrip()


def _replace_exact_placeholders(template: str, values: dict[str, str]) -> str:
    """只替换明确占位符，避免破坏 shell `${VAR:-default}` 语法。"""
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace(f"${{{key}}}", value)
    return rendered


def _build_assignment_block(values: dict[str, Any]) -> str:
    """把变量映射渲染成 shell 赋值块。"""
    lines: list[str] = []
    for key, value in values.items():
        if value is None:
            continue
        lines.append(f"{key}={shlex.quote(str(value))}")
    return "\n".join(lines)


def _bool_flag(value: bool) -> str:
    return "1" if value else "0"


def _parse_json_object(raw_json: Optional[str], field_name: str, strict: bool = True) -> dict[str, Any]:
    """解析 JSON object。"""
    if not raw_json:
        return {}

    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        if strict:
            raise ValidationError(f"{field_name} 必须是合法 JSON object") from exc
        return {}

    if not isinstance(parsed, dict):
        if strict:
            raise ValidationError(f"{field_name} 必须是合法 JSON object")
        return {}
    return parsed


def _resolve_bootstrap_context(
    db: Session,
    managed_agent_id: str,
) -> dict[str, Any]:
    """读取脚本渲染需要的核心上下文。"""
    managed_agent = get_managed_agent_or_404(db, managed_agent_id)
    host_config = get_host_config(db, managed_agent_id)
    prompt_asset = get_prompt_asset(db, managed_agent_id)

    if not host_config:
        raise ValidationError("宿主平台配置缺失，无法生成 Bootstrap 脚本")
    if not prompt_asset:
        raise ValidationError("Prompt 资产缺失，无法生成 Bootstrap 脚本")

    renderer = get_renderer(managed_agent.host_platform)
    errors = renderer.validate_config(managed_agent, host_config, prompt_asset)
    if errors:
        raise ValidationError("；".join(errors))

    return {
        "managed_agent": managed_agent,
        "host_config": host_config,
        "prompt_asset": prompt_asset,
        "renderer": renderer,
        "host_payload": _parse_json_object(
            host_config.host_config_payload_encrypted,
            "host_config_payload",
            strict=False,
        ),
    }


def _select_prompt_artifacts(
    prompt_artifacts: list[dict[str, str]],
    host_render_strategy: str,
    selected_artifacts: Optional[list[str]],
) -> list[dict[str, str]]:
    """按用户选择筛选 Prompt 产物。"""
    artifact_names = {item["name"] for item in prompt_artifacts}
    if selected_artifacts is None:
        if host_render_strategy == "openclaw_inline_schedule":
            return []
        return prompt_artifacts

    unknown = [name for name in selected_artifacts if name not in artifact_names]
    if unknown:
        raise ValidationError(f"未知的 Prompt 产物选择: {', '.join(unknown)}")

    selected_name_set = set(selected_artifacts)
    return [item for item in prompt_artifacts if item["name"] in selected_name_set]


def render_bootstrap_script(
    db: Session,
    managed_agent_id: str,
    register_token: str,
    skill_bundle_token: str,
    selected_artifacts: Optional[list[str]] = None,
    include_schedule: bool = True,
    include_comm_bindings: bool = True,
    restart_gateway: Optional[bool] = None,
) -> str:
    """渲染完整 Bootstrap shell 脚本。"""
    if not register_token:
        raise ValidationError("register_token 不能为空")
    if not skill_bundle_token:
        raise ValidationError("skill_bundle_token 不能为空")

    context = _resolve_bootstrap_context(db, managed_agent_id)
    managed_agent = context["managed_agent"]
    host_config = context["host_config"]
    prompt_asset = context["prompt_asset"]
    renderer = context["renderer"]
    host_payload = context["host_payload"]

    shell_context = renderer.render_bootstrap_shell_context(
        managed_agent=managed_agent,
        host_config=host_config,
        prompt_asset=prompt_asset,
    )
    prompt_artifacts = _select_prompt_artifacts(
        shell_context["artifacts"],
        prompt_asset.host_render_strategy,
        selected_artifacts,
    )
    prompt_artifact_map = {item["name"]: item["content"] for item in prompt_artifacts}

    enabled_schedules = list_schedules(db, managed_agent_id) if include_schedule else []
    enabled_schedules = [item for item in enabled_schedules if item.enabled]

    enabled_bindings = list_comm_bindings(db, managed_agent_id) if include_comm_bindings else []
    enabled_bindings = [item for item in enabled_bindings if item.enabled]

    host_agent_identifier = host_config.host_agent_identifier or managed_agent.slug
    workdir_path = host_config.workdir_path or f"~/.openclaw/workspace-{host_agent_identifier}"
    should_restart_gateway = (
        bool(host_payload.get("restart_gateway"))
        if restart_gateway is None
        else restart_gateway
    )

    first_schedule = enabled_schedules[0] if enabled_schedules else None
    parts: list[str] = [
        _load_template("common/bootstrap_header.sh.tpl"),
        _build_assignment_block(
            {
                "REQUIRE_OPENCLAW": "1" if managed_agent.host_platform == "openclaw" else "0",
                "OPENMOSS_URL": config.server_external_url,
                "BOOTSTRAP_REGISTER_PATH": f"/api/bootstrap/agents/{managed_agent.id}/register",
                "BOOTSTRAP_REGISTER_TOKEN": register_token,
                "BOOTSTRAP_SKILL_BUNDLE_PATH": f"/api/bootstrap/agents/{managed_agent.id}/skill-bundle",
                "BOOTSTRAP_SKILL_BUNDLE_TOKEN": skill_bundle_token,
                "AGENT_ID": host_agent_identifier,
                "AGENT_NAME": managed_agent.name,
                "AGENT_ROLE": managed_agent.role,
                "AGENT_DESCRIPTION": managed_agent.description or "",
                "AGENT_WORKSPACE": workdir_path,
                "SKILL_DIR_NAME": f"task-{managed_agent.role}-skill",
                "WRITE_AGENTS_MD": _bool_flag("AGENTS.md" in prompt_artifact_map),
                "WRITE_SOUL_MD": _bool_flag("SOUL.md" in prompt_artifact_map),
                "WRITE_IDENTITY_MD": _bool_flag("IDENTITY.md" in prompt_artifact_map),
                "SCHEDULE_EXPR": first_schedule.schedule_expr if first_schedule else None,
                "SCHEDULE_TIMEOUT_SECONDS": first_schedule.timeout_seconds if first_schedule else None,
                "OPENCLAW_CONFIG_PATH": host_payload.get("openclaw_config_path"),
                "RESTART_GATEWAY": _bool_flag(bool(should_restart_gateway)),
            }
        ),
        _load_template("common/dependency_checks.sh.tpl"),
        _load_template("common/summary.sh.tpl"),
        _load_template(f"hosts/{managed_agent.host_platform}/{managed_agent.deployment_mode}.sh.tpl"),
        _load_template("common/path_setup.sh.tpl"),
    ]

    if prompt_artifacts:
        parts.append(
            _replace_exact_placeholders(
                _load_template(f"hosts/{managed_agent.host_platform}/write_prompt_artifacts.sh.tpl"),
                {
                    "AGENTS_MD_CONTENT": prompt_artifact_map.get("AGENTS.md", ""),
                    "SOUL_MD_CONTENT": prompt_artifact_map.get("SOUL.md", ""),
                    "IDENTITY_MD_CONTENT": prompt_artifact_map.get("IDENTITY.md", ""),
                },
            )
        )

    if "IDENTITY.md" in prompt_artifact_map:
        parts.append(_load_template(f"hosts/{managed_agent.host_platform}/apply_identity.sh.tpl"))

    parts.append(_load_template("openmoss/register_runtime.sh.tpl"))
    parts.append(_load_template("openmoss/download_skill_bundle.sh.tpl"))

    for schedule in enabled_schedules:
        schedule_context = renderer.render_schedule_context(
            managed_agent=managed_agent,
            host_config=host_config,
            prompt_asset=prompt_asset,
            schedule=schedule,
        )
        execution_options = schedule_context.get("execution_options", {})
        parts.append(
            _build_assignment_block(
                {
                    "INCLUDE_SCHEDULE": "1",
                    "SCHEDULE_JOB_NAME": schedule.name,
                    "SCHEDULE_MODE": schedule.schedule_type,
                    "SCHEDULE_EXPR": schedule.schedule_expr,
                    "SCHEDULE_MESSAGE": schedule_context.get("schedule_message"),
                    "SCHEDULE_TIMEOUT_SECONDS": schedule.timeout_seconds,
                    "SCHEDULE_SESSION_MODE": execution_options.get("session_mode", "isolated"),
                    "SCHEDULE_THINKING": execution_options.get("thinking_mode"),
                    "SCHEDULE_ANNOUNCE": _bool_flag(execution_options.get("announce", True)),
                    "SCHEDULE_MODEL_OVERRIDE": schedule.model_override,
                }
            )
        )
        parts.append(_load_template(f"hosts/{managed_agent.host_platform}/create_schedule.sh.tpl"))

    for binding in enabled_bindings:
        template_path = SUPPORTED_COMM_PROVIDER_TEMPLATES.get(binding.provider)
        if not template_path:
            raise ValidationError(f"暂不支持生成通讯渠道脚本: {binding.provider}")

        binding_payload = _parse_json_object(
            binding.config_payload_encrypted,
            f"{binding.provider}.config_payload",
            strict=True,
        )
        if binding.provider == "feishu":
            app_id = binding_payload.get("app_id") or binding_payload.get("appId")
            app_secret = binding_payload.get("app_secret") or binding_payload.get("appSecret")
            if not app_id or not app_secret:
                raise ValidationError("feishu.config_payload 需包含 app_id/app_secret")

            parts.append(
                _build_assignment_block(
                    {
                        "INCLUDE_FEISHU_BINDING": "1",
                        "FEISHU_ACCOUNT_ID": binding.binding_key,
                        "FEISHU_ACCOUNT_NAME": binding.display_name
                        or binding_payload.get("account_name")
                        or binding_payload.get("name"),
                        "FEISHU_APP_ID": app_id,
                        "FEISHU_APP_SECRET": app_secret,
                    }
                )
            )
            parts.append(_load_template(template_path))

    if should_restart_gateway:
        parts.append(_load_template(f"hosts/{managed_agent.host_platform}/restart_gateway.sh.tpl"))

    parts.append(_load_template("common/finalize.sh.tpl"))
    return "\n\n".join(part for part in parts if part)
