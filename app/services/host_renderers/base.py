"""
宿主平台 renderer 抽象基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseHostRenderer(ABC):
    """宿主平台渲染器抽象。"""

    host_platform: str = ""

    @abstractmethod
    def validate_config(self, managed_agent: Any, host_config: Any, prompt_asset: Any) -> list[str]:
        """校验宿主配置与 Prompt 配置是否满足渲染前置条件。"""

    @abstractmethod
    def render_prompt_artifacts(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
    ) -> list[dict[str, str]]:
        """把 Prompt 资产渲染成宿主平台文件产物。"""

    @abstractmethod
    def render_schedule_context(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
        schedule: Any,
    ) -> dict[str, Any]:
        """渲染定时任务上下文。"""

    @abstractmethod
    def render_bootstrap_shell_context(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
    ) -> dict[str, Any]:
        """渲染部署脚本所需上下文。"""

    @abstractmethod
    def render_onboarding_message(
        self,
        managed_agent: Any,
        host_config: Any,
        prompt_asset: Any,
    ) -> str:
        """渲染接入说明文本。"""
