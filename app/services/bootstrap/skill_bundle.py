"""Skill Bundle 构建：打包角色技能包、渲染 task-cli 入口。"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import config
from app.exceptions import NotFoundError, ValidationError
from app.models.agent import Agent
from app.models.managed_agent import ManagedAgent
from app.services.managed_agent.core import get_managed_agent_or_404
from app.services.bootstrap.script_render import _replace_exact_placeholders
from tools.task_cli.runtime import DEFAULT_CLI_VERSION


REPO_ROOT = Path(__file__).resolve().parents[3]
TASK_CLI_TEMPLATE_ROOT = REPO_ROOT / "tools" / "task_cli" / "templates"
SHARED_TASK_CLI_DIR = REPO_ROOT / "tools" / "task_cli"
SKILLS_ROOT = REPO_ROOT / "skills"
SKILL_BUNDLE_SKIP_NAMES = {".gitkeep", "README.md"}
SKILL_BUNDLE_SKIP_DIRS = {"__pycache__", "templates"}


def _load_task_cli_template(relative_path: str) -> str:
    """读取 task_cli 模板。"""
    path = TASK_CLI_TEMPLATE_ROOT / relative_path
    if not path.exists():
        raise NotFoundError(f"task_cli 模板不存在: {relative_path}")
    return path.read_text(encoding="utf-8").rstrip()


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
    skill_dir = SKILLS_ROOT / get_skill_bundle_dir_name(role)
    if not skill_dir.is_dir():
        raise NotFoundError(f"Skill 模板目录不存在: {skill_dir.name}")
    return skill_dir


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
    from app.exceptions import ConflictError

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
