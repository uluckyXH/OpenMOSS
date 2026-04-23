"""Onboarding 消息渲染：生成接入说明文本和 curl 一键部署命令。"""

from __future__ import annotations

import shlex
from typing import Optional

from sqlalchemy.orm import Session

from app.config import config
from app.exceptions import ValidationError
from app.services.bootstrap.script_render import _resolve_bootstrap_context


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
