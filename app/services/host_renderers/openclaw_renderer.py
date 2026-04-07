"""
OpenClaw 宿主平台渲染器。
"""

from __future__ import annotations

import json
import shlex
from typing import Any

from .base import BaseHostRenderer


class OpenClawRenderer(BaseHostRenderer):
    """OpenClaw 宿主平台渲染器。"""

    host_platform = "openclaw"

    def validate_config(self, managed_agent: Any, host_config: Any, prompt_asset: Any) -> list[str]:
        errors: list[str] = []

        if managed_agent.host_platform != self.host_platform:
            errors.append("managed_agent.host_platform 必须为 openclaw")

        if host_config.host_platform != self.host_platform:
            errors.append("host_config.host_platform 必须为 openclaw")

        if not host_config.host_agent_identifier:
            errors.append("OpenClaw 渲染需要 host_agent_identifier")

        if not host_config.workdir_path:
            errors.append("OpenClaw 渲染需要 workdir_path")

        if prompt_asset.host_render_strategy not in {
            "openclaw_workspace_files",
            "openclaw_inline_schedule",
        }:
            errors.append("OpenClaw 渲染策略必须为 openclaw_workspace_files 或 openclaw_inline_schedule")

        return errors

    def render_prompt_artifacts(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
    ) -> list[dict[str, str]]:
        return [
            {"name": "AGENTS.md", "content": prompt_asset.system_prompt_content or ""},
            {"name": "SOUL.md", "content": prompt_asset.persona_prompt_content or ""},
            {"name": "IDENTITY.md", "content": prompt_asset.identity_content or ""},
        ]

    def render_schedule_context(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
        schedule: Any,
    ) -> dict[str, Any]:
        execution_options = self._parse_execution_options(schedule.execution_options_json)
        session_mode = execution_options.get("session_mode") or "isolated"
        thinking_mode = execution_options.get("thinking_mode")
        announce = execution_options.get("announce", True)
        schedule_flag = "--every" if schedule.schedule_type != "cron" else "--cron"
        schedule_message = (
            schedule.schedule_message_content or self._default_schedule_message(host_config.workdir_path)
        )

        command_args = [
            "openclaw",
            "cron",
            "add",
            "--name",
            f"{host_config.host_agent_identifier} 定时任务（{schedule.schedule_expr}）",
            schedule_flag,
            schedule.schedule_expr,
            "--session",
            str(session_mode),
            "--agent",
            str(host_config.host_agent_identifier),
            "--message",
            schedule_message,
            "--timeout-seconds",
            str(schedule.timeout_seconds),
        ]

        if thinking_mode:
            command_args.extend(["--thinking", str(thinking_mode)])

        if announce:
            command_args.append("--announce")
        else:
            command_args.append("--no-deliver")

        if schedule.model_override:
            command_args.extend(["--model", str(schedule.model_override)])

        return {
            "host_platform": self.host_platform,
            "host_render_strategy": prompt_asset.host_render_strategy,
            "schedule_type": schedule.schedule_type,
            "schedule_expr": schedule.schedule_expr,
            "schedule_message": schedule_message,
            "prompt_artifacts": self.render_prompt_artifacts(
                managed_agent=managed_agent,
                host_config=host_config,
                prompt_asset=prompt_asset,
            ),
            "execution_options": execution_options,
            "cron_command": shlex.join(command_args),
        }

    def render_bootstrap_shell_context(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
    ) -> dict[str, Any]:
        return {
            "host_platform": self.host_platform,
            "deployment_mode": managed_agent.deployment_mode,
            "host_agent_identifier": host_config.host_agent_identifier,
            "workdir_path": host_config.workdir_path,
            "artifacts": self.render_prompt_artifacts(
                managed_agent=managed_agent,
                host_config=host_config,
                prompt_asset=prompt_asset,
            ),
        }

    def render_onboarding_message(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
    ) -> str:
        artifacts = self.render_prompt_artifacts(
            managed_agent=managed_agent,
            host_config=host_config,
            prompt_asset=prompt_asset,
        )
        artifact_names = ", ".join(item["name"] for item in artifacts)
        return (
            f"OpenClaw Agent `{host_config.host_agent_identifier}` 已准备接入。\n"
            f"工作目录：`{host_config.workdir_path}`\n"
            f"需写入的 Prompt 文件：{artifact_names}"
        )

    @staticmethod
    def _parse_execution_options(raw_json: str | None) -> dict[str, Any]:
        if not raw_json:
            return {}

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return {}

        return data if isinstance(data, dict) else {}

    @staticmethod
    def _default_schedule_message(workdir_path: str) -> str:
        agents_file = f"{workdir_path}/AGENTS.md"
        skill_file = f"{workdir_path}/task-executor-skill/SKILL.md"
        return (
            "# OpenClaw 定时任务\n"
            "执行前：\n"
            f"1) 读取并严格遵守：{agents_file}\n"
            f"2) API Key 在同目录 SKILL.md 的 API_KEY 字段（文件：{skill_file}）\n"
            "要求：\n"
            "- 本 cron 以 AGENTS.md 为唯一准绳\n"
            "- 严格按 AGENTS.md 中“每次唤醒时的检查流程”完整执行"
        )
