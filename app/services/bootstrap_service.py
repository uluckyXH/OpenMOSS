"""
Bootstrap 相关服务。

第一步先落 token 生命周期管理：
- 创建
- 校验
- 列表
- 撤销

脚本渲染和注册闭环后续再补。
"""

from __future__ import annotations

import hashlib
import io
import json
import secrets
import shlex
from types import SimpleNamespace
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import config
from app.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.agent import Agent
from app.models.managed_agent import ManagedAgent, ManagedAgentBootstrapToken
from app.services.agent_service import generate_api_key
from app.services.host_renderers import get_renderer
from app.services.managed_agent import (
    get_host_config,
    get_prompt_asset,
    list_comm_bindings,
    list_schedules,
)
from app.services.managed_agent.core import get_managed_agent_or_404
from tools.task_cli.runtime import DEFAULT_CLI_VERSION


BOOTSTRAP_PURPOSES = {"download_script", "register_runtime"}
DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS = 3600
REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_ROOT = REPO_ROOT / "shells" / "templates"
TASK_CLI_TEMPLATE_ROOT = REPO_ROOT / "tools" / "task_cli" / "templates"
SHARED_TASK_CLI_DIR = REPO_ROOT / "tools" / "task_cli"
SKILLS_ROOT = REPO_ROOT / "skills"
SKILL_BUNDLE_SKIP_NAMES = {".gitkeep", "README.md"}
SKILL_BUNDLE_SKIP_DIRS = {"__pycache__", "templates"}
SUPPORTED_COMM_PROVIDER_TEMPLATES = {
    "feishu": "comm_providers/feishu/bind_account.sh.tpl",
}


def hash_bootstrap_token(token: str) -> str:
    """对明文 token 做哈希。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_bootstrap_token_value() -> str:
    """生成新的 bootstrap token 明文。"""
    return f"bt_{secrets.token_urlsafe(32)}"


def _serialize_scope(scope: Optional[dict[str, Any]]) -> Optional[str]:
    """稳定序列化 scope，便于同 scope token 复用。"""
    if scope is None:
        return None
    return json.dumps(scope, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _serialize_created_bootstrap_token(
    row: ManagedAgentBootstrapToken,
    token: str,
) -> dict[str, Any]:
    """把新建/复用后的 token 记录序列化为创建响应。"""
    return {
        "id": row.id,
        "managed_agent_id": row.managed_agent_id,
        "token": token,
        "purpose": row.purpose,
        "expires_at": row.expires_at,
        "created_at": row.created_at,
    }


def _load_template(relative_path: str) -> str:
    """读取 shell 模板。"""
    path = TEMPLATE_ROOT / relative_path
    if not path.exists():
        raise NotFoundError(f"Shell 模板不存在: {relative_path}")
    return path.read_text(encoding="utf-8").rstrip()


def _load_task_cli_template(relative_path: str) -> str:
    """读取 task_cli 模板。"""
    path = TASK_CLI_TEMPLATE_ROOT / relative_path
    if not path.exists():
        raise NotFoundError(f"task_cli 模板不存在: {relative_path}")
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


def _python_literal(value: Any) -> str:
    """渲染为稳定的 Python 字面量。"""
    if value is None:
        return "None"
    return json.dumps(value, ensure_ascii=False)


def _write_zip_dir_entry(zip_file: zipfile.ZipFile, arcname: str) -> None:
    """显式写入目录项，便于 bundle 结构检查。"""
    if not arcname.endswith("/"):
        arcname = f"{arcname}/"
    zip_file.writestr(arcname, b"")


def _should_skip_bundle_file(file_name: str) -> bool:
    return file_name in SKILL_BUNDLE_SKIP_NAMES or file_name.endswith(".pyc")


def _iter_bundle_files(root_dir: Path):
    """遍历 bundle 文件，跳过缓存和模板目录。"""
    for path in sorted(root_dir.rglob("*")):
        if path.is_dir():
            continue
        rel_path = path.relative_to(root_dir)
        if any(part in SKILL_BUNDLE_SKIP_DIRS for part in rel_path.parts):
            continue
        if _should_skip_bundle_file(path.name):
            continue
        yield path, rel_path.as_posix()


def get_skill_bundle_dir_name(role: str) -> str:
    """按角色解析标准 Skill 目录名。"""
    return f"task-{role}-skill"


def _resolve_skill_template_dir(role: str) -> Path:
    """按角色解析 Skill 模板目录。"""
    skill_dir = SKILLS_ROOT / get_skill_bundle_dir_name(role)
    if not skill_dir.is_dir():
        raise NotFoundError(f"Skill 模板目录不存在: {skill_dir.name}")
    return skill_dir


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


def is_bootstrap_token_valid(
    bootstrap_token: ManagedAgentBootstrapToken,
    at: Optional[datetime] = None,
) -> bool:
    """判断 token 当前是否有效。"""
    now = at or datetime.now()

    if bootstrap_token.revoked_at is not None:
        return False
    if bootstrap_token.expires_at <= now:
        return False
    if bootstrap_token.purpose == "register_runtime" and bootstrap_token.used_at is not None:
        return False
    return True


def create_bootstrap_token(
    db: Session,
    managed_agent_id: str,
    purpose: str,
    ttl_seconds: int,
    scope: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """创建 bootstrap token，并返回一次性明文 token。"""
    get_managed_agent_or_404(db, managed_agent_id)

    if purpose not in BOOTSTRAP_PURPOSES:
        raise ValidationError(f"不支持的 bootstrap token purpose: {purpose}")
    if ttl_seconds <= 0:
        raise ValidationError("ttl_seconds 必须大于 0")

    token = _issue_bootstrap_token_value()
    now = datetime.now()
    row = ManagedAgentBootstrapToken(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        token_hash=hash_bootstrap_token(token),
        purpose=purpose,
        scope_json=_serialize_scope(scope),
        expires_at=now + timedelta(seconds=ttl_seconds),
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return _serialize_created_bootstrap_token(row, token)


def create_or_reissue_bootstrap_token(
    db: Session,
    managed_agent_id: str,
    purpose: str,
    ttl_seconds: int,
    scope: Optional[dict[str, Any]] = None,
    min_remaining_seconds: int = 0,
) -> dict[str, Any]:
    """优先复用同 scope 的有效 token 记录，避免重复创建。

    注意：当前数据库只存 token_hash，不存明文 token。
    因此复用时会对同一条记录重新签发一个新的明文 token，
    旧明文 token 随即失效，但记录 id / expires_at 不变。
    """
    get_managed_agent_or_404(db, managed_agent_id)

    if purpose not in BOOTSTRAP_PURPOSES:
        raise ValidationError(f"不支持的 bootstrap token purpose: {purpose}")
    if ttl_seconds <= 0:
        raise ValidationError("ttl_seconds 必须大于 0")
    if min_remaining_seconds < 0:
        raise ValidationError("min_remaining_seconds 不能小于 0")

    now = datetime.now()
    serialized_scope = _serialize_scope(scope)
    query = (
        db.query(ManagedAgentBootstrapToken)
        .filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
        .filter(ManagedAgentBootstrapToken.purpose == purpose)
        .filter(ManagedAgentBootstrapToken.revoked_at.is_(None))
        .filter(ManagedAgentBootstrapToken.expires_at > now)
    )
    if purpose == "register_runtime":
        query = query.filter(ManagedAgentBootstrapToken.used_at.is_(None))

    if serialized_scope is None:
        query = query.filter(ManagedAgentBootstrapToken.scope_json.is_(None))
    else:
        query = query.filter(ManagedAgentBootstrapToken.scope_json == serialized_scope)

    reusable = (
        query.order_by(
            ManagedAgentBootstrapToken.expires_at.desc(),
            ManagedAgentBootstrapToken.created_at.desc(),
        )
        .first()
    )

    if reusable:
        remaining_seconds = (reusable.expires_at - now).total_seconds()
        if remaining_seconds > min_remaining_seconds:
            token = _issue_bootstrap_token_value()
            reusable.token_hash = hash_bootstrap_token(token)
            reusable.created_at = now
            db.commit()
            db.refresh(reusable)
            return _serialize_created_bootstrap_token(reusable, token)

    return create_bootstrap_token(
        db,
        managed_agent_id=managed_agent_id,
        purpose=purpose,
        ttl_seconds=ttl_seconds,
        scope=scope,
    )


def list_bootstrap_tokens(db: Session, managed_agent_id: str) -> list[ManagedAgentBootstrapToken]:
    """列出某个 Agent 的 bootstrap token。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return (
        db.query(ManagedAgentBootstrapToken)
        .filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
        .order_by(ManagedAgentBootstrapToken.created_at.desc())
        .all()
    )


def get_bootstrap_token_or_404(
    db: Session,
    token_id: str,
    managed_agent_id: Optional[str] = None,
) -> ManagedAgentBootstrapToken:
    """按 id 获取 bootstrap token。"""
    query = db.query(ManagedAgentBootstrapToken).filter(ManagedAgentBootstrapToken.id == token_id)
    if managed_agent_id is not None:
        query = query.filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
    token = query.first()
    if not token:
        raise NotFoundError(f"Bootstrap Token 不存在: {token_id}")
    return token


def validate_bootstrap_token(
    db: Session,
    token: str,
    managed_agent_id: str,
    purpose: str,
) -> ManagedAgentBootstrapToken:
    """校验 bootstrap token，返回对应记录。"""
    if purpose not in BOOTSTRAP_PURPOSES:
        raise ValidationError(f"不支持的 bootstrap token purpose: {purpose}")

    token_hash = hash_bootstrap_token(token)
    row = (
        db.query(ManagedAgentBootstrapToken)
        .filter(ManagedAgentBootstrapToken.token_hash == token_hash)
        .filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
        .filter(ManagedAgentBootstrapToken.purpose == purpose)
        .first()
    )
    if not row or not is_bootstrap_token_valid(row):
        raise ForbiddenError("无效或已过期的 Bootstrap Token")
    return row


def revoke_bootstrap_token(
    db: Session,
    token_id: str,
    managed_agent_id: Optional[str] = None,
) -> ManagedAgentBootstrapToken:
    """撤销 bootstrap token。"""
    row = get_bootstrap_token_or_404(db, token_id, managed_agent_id=managed_agent_id)
    if row.revoked_at is None:
        row.revoked_at = datetime.now()
        db.commit()
        db.refresh(row)
    return row


def mark_bootstrap_token_used(
    db: Session,
    token_id: str,
    managed_agent_id: Optional[str] = None,
) -> ManagedAgentBootstrapToken:
    """标记 bootstrap token 已使用。"""
    row = get_bootstrap_token_or_404(db, token_id, managed_agent_id=managed_agent_id)
    if row.used_at is None:
        row.used_at = datetime.now()
        db.commit()
        db.refresh(row)
    return row


def serialize_bootstrap_token(bootstrap_token: ManagedAgentBootstrapToken) -> dict[str, Any]:
    """序列化 bootstrap token 列表项，不返回明文 token。"""
    return {
        "id": bootstrap_token.id,
        "managed_agent_id": bootstrap_token.managed_agent_id,
        "token_masked": "仅创建时可见",
        "purpose": bootstrap_token.purpose,
        "scope_json": bootstrap_token.scope_json,
        "expires_at": bootstrap_token.expires_at,
        "used_at": bootstrap_token.used_at,
        "revoked_at": bootstrap_token.revoked_at,
        "created_at": bootstrap_token.created_at,
        "is_valid": is_bootstrap_token_valid(bootstrap_token),
    }


def deserialize_bootstrap_scope(bootstrap_token: ManagedAgentBootstrapToken) -> dict[str, Any]:
    """把 token.scope_json 解析为作用域字典。"""
    return _parse_json_object(bootstrap_token.scope_json, "bootstrap_scope", strict=False)


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


def render_curl_command(managed_agent_id: str, download_token: str) -> str:
    """渲染一键下载并执行脚本的 curl 命令。"""
    if not download_token:
        raise ValidationError("download_token 不能为空")

    script_url = f"{config.server_external_url}/api/bootstrap/agents/{managed_agent_id}/script"
    return (
        f"curl -fsSL -H {shlex.quote(f'X-Bootstrap-Token: {download_token}')} "
        f"{shlex.quote(script_url)} | bash"
    )


def render_onboarding_message(
    db: Session,
    managed_agent_id: str,
    download_token: Optional[str] = None,
) -> str:
    """渲染接入说明文本。"""
    context = _resolve_bootstrap_context(db, managed_agent_id)
    managed_agent = context["managed_agent"]
    host_config = context["host_config"]
    prompt_asset = context["prompt_asset"]
    renderer = context["renderer"]

    message = renderer.render_onboarding_message(
        managed_agent=managed_agent,
        host_config=host_config,
        prompt_asset=prompt_asset,
    )
    if download_token:
        curl_command = render_curl_command(managed_agent.id, download_token)
        return f"{message}\n\n推荐执行命令：\n{curl_command}"
    return message


def render_task_cli_launcher(
    *,
    managed_agent,
    runtime_agent,
    runtime_api_key: str,
    base_url: Optional[str] = None,
    cli_version: Optional[int] = None,
) -> str:
    """渲染当前 Agent 专属的 task-cli 入口。"""
    if not runtime_api_key:
        raise ValidationError("runtime_api_key 不能为空")

    launcher = _load_task_cli_template("task_cli_launcher.py.tpl")
    return _replace_exact_placeholders(
        launcher,
        {
            "BASE_URL_LITERAL": _python_literal((base_url or config.server_external_url).rstrip("/")),
            "CLI_VERSION_LITERAL": str(cli_version or config.cli_version or DEFAULT_CLI_VERSION),
            "DEFAULT_API_KEY_LITERAL": _python_literal(runtime_api_key),
            "AGENT_ID_LITERAL": _python_literal(runtime_agent.id),
            "AGENT_NAME_LITERAL": _python_literal(runtime_agent.name),
            "AGENT_ROLE_LITERAL": _python_literal(runtime_agent.role or managed_agent.role),
            "CLI_PROFILE_LITERAL": _python_literal(runtime_agent.role or managed_agent.role),
        },
    )


def render_skill_bundle_layout(
    *,
    managed_agent,
    runtime_agent,
    runtime_api_key: str,
    base_url: Optional[str] = None,
    cli_version: Optional[int] = None,
) -> dict[str, bytes]:
    """渲染当前 Agent 专属 Skill Bundle 的文件布局。"""
    bundle_role = runtime_agent.role or managed_agent.role
    skill_dir = _resolve_skill_template_dir(bundle_role)
    bundle_root = skill_dir.name

    rendered_launcher = render_task_cli_launcher(
        managed_agent=managed_agent,
        runtime_agent=runtime_agent,
        runtime_api_key=runtime_api_key,
        base_url=base_url,
        cli_version=cli_version,
    ).encode("utf-8")

    files: dict[str, bytes] = {}
    for file_path, rel_path in _iter_bundle_files(skill_dir):
        if rel_path == "scripts/task-cli.py":
            continue
        if rel_path.startswith("scripts/task_cli/"):
            continue
        files[f"{bundle_root}/{rel_path}"] = file_path.read_bytes()

    files[f"{bundle_root}/scripts/task-cli.py"] = rendered_launcher

    if not SHARED_TASK_CLI_DIR.is_dir():
        raise NotFoundError("共享 task_cli 源码目录不存在")

    for file_path, rel_path in _iter_bundle_files(SHARED_TASK_CLI_DIR):
        files[f"{bundle_root}/scripts/task_cli/{rel_path}"] = file_path.read_bytes()

    return files


def build_skill_bundle_zip(
    *,
    managed_agent,
    runtime_agent,
    runtime_api_key: str,
    base_url: Optional[str] = None,
    cli_version: Optional[int] = None,
) -> bytes:
    """构建当前 Agent 专属 Skill Bundle zip。"""
    bundle_role = runtime_agent.role or managed_agent.role
    bundle_root = get_skill_bundle_dir_name(bundle_role)
    files = render_skill_bundle_layout(
        managed_agent=managed_agent,
        runtime_agent=runtime_agent,
        runtime_api_key=runtime_api_key,
        base_url=base_url,
        cli_version=cli_version,
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zip_file:
        _write_zip_dir_entry(zip_file, bundle_root)
        _write_zip_dir_entry(zip_file, f"{bundle_root}/scripts")
        _write_zip_dir_entry(zip_file, f"{bundle_root}/scripts/task_cli")
        _write_zip_dir_entry(zip_file, f"{bundle_root}/references")
        for path in sorted(files):
            zip_file.writestr(path, files[path])
    return buf.getvalue()


def build_skill_bundle_zip_for_managed_agent(
    db: Session,
    managed_agent_id: str,
    *,
    base_url: Optional[str] = None,
    cli_version: Optional[int] = None,
) -> tuple[str, bytes]:
    """按配置态 Agent 构建当前专属 Skill Bundle zip。"""
    managed_agent = get_managed_agent_or_404(db, managed_agent_id)
    if not managed_agent.runtime_agent_id:
        raise ConflictError("该配置态 Agent 尚未完成运行态注册，无法生成 Skill Bundle")

    runtime_agent = db.query(Agent).filter(Agent.id == managed_agent.runtime_agent_id).first()
    if not runtime_agent:
        raise NotFoundError(f"运行态 Agent 不存在: {managed_agent.runtime_agent_id}")

    bundle_name = f"{get_skill_bundle_dir_name(runtime_agent.role or managed_agent.role)}.zip"
    bundle_zip = build_skill_bundle_zip(
        managed_agent=managed_agent,
        runtime_agent=runtime_agent,
        runtime_api_key=runtime_agent.api_key,
        base_url=base_url,
        cli_version=cli_version,
    )
    return bundle_name, bundle_zip


def build_skill_bundle_zip_for_runtime_agent(
    db: Session,
    runtime_agent: Agent,
    *,
    base_url: Optional[str] = None,
    cli_version: Optional[int] = None,
) -> tuple[str, bytes]:
    """按运行态 Agent 构建 Skill Bundle。

    优先复用已绑定的 managed_agent；若旧版本运行态尚未进入配置中心，
    则回退到按角色 Skill 模板构建 bundle，便于旧单文件 CLI 平滑迁移。
    """
    managed_agent = (
        db.query(ManagedAgent)
        .filter(ManagedAgent.runtime_agent_id == runtime_agent.id)
        .first()
    )
    if managed_agent is None:
        managed_agent = SimpleNamespace(
            id=None,
            name=runtime_agent.name,
            role=runtime_agent.role,
            description=runtime_agent.description or "",
        )

    bundle_name = f"{get_skill_bundle_dir_name(runtime_agent.role or managed_agent.role)}.zip"
    bundle_zip = build_skill_bundle_zip(
        managed_agent=managed_agent,
        runtime_agent=runtime_agent,
        runtime_api_key=runtime_agent.api_key,
        base_url=base_url,
        cli_version=cli_version,
    )
    return bundle_name, bundle_zip


def bootstrap_register(
    db: Session,
    managed_agent_id: str,
    token: str,
) -> Agent:
    """使用 register_runtime token 完成运行态注册并回写配置态。"""
    bootstrap_token = validate_bootstrap_token(
        db,
        token=token,
        managed_agent_id=managed_agent_id,
        purpose="register_runtime",
    )
    managed_agent = get_managed_agent_or_404(db, managed_agent_id)

    if managed_agent.runtime_agent_id:
        existing_runtime = db.query(Agent).filter(Agent.id == managed_agent.runtime_agent_id).first()
        if existing_runtime:
            raise ConflictError("该配置态 Agent 已有运行态实例")

    same_name_agent = db.query(Agent).filter(Agent.name == managed_agent.name).first()
    if same_name_agent:
        raise ConflictError(f"名称 '{managed_agent.name}' 已被注册")

    runtime_agent = Agent(
        id=str(uuid.uuid4()),
        name=managed_agent.name,
        role=managed_agent.role,
        description=managed_agent.description or "",
        api_key=generate_api_key(),
    )
    db.add(runtime_agent)
    db.flush()

    managed_agent.runtime_agent_id = runtime_agent.id
    managed_agent.deployed_config_version = managed_agent.config_version
    managed_agent.status = "deployed"
    bootstrap_token.used_at = datetime.now()

    db.commit()
    db.refresh(runtime_agent)
    return runtime_agent


__all__ = [
    "BOOTSTRAP_PURPOSES",
    "create_bootstrap_token",
    "create_or_reissue_bootstrap_token",
    "deserialize_bootstrap_scope",
    "bootstrap_register",
    "get_bootstrap_token_or_404",
    "hash_bootstrap_token",
    "is_bootstrap_token_valid",
    "list_bootstrap_tokens",
    "mark_bootstrap_token_used",
    "get_skill_bundle_dir_name",
    "render_bootstrap_script",
    "render_curl_command",
    "render_onboarding_message",
    "render_skill_bundle_layout",
    "render_task_cli_launcher",
    "build_skill_bundle_zip",
    "build_skill_bundle_zip_for_managed_agent",
    "build_skill_bundle_zip_for_runtime_agent",
    "revoke_bootstrap_token",
    "serialize_bootstrap_token",
    "validate_bootstrap_token",
]
