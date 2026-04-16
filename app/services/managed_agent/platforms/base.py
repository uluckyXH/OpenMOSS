"""
通讯平台适配器抽象基类。

所有 (host_platform, comm_provider) 组合的适配器都应继承此基类。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session


class CommProviderAdapter(ABC):
    """通讯平台适配器接口。

    每个 (host_platform, comm_provider) 组合对应一个实现，例如：
    - OpenClaw + Feishu  → OpenClawFeishuAdapter
    - OpenClaw + Slack   → OpenClawSlackAdapter（未来）
    - CodexCli + Webhook → CodexCliWebhookAdapter（未来）
    """

    @abstractmethod
    def get_provider_key(self) -> str:
        """返回 provider 标识，如 'feishu'。"""

    @abstractmethod
    def get_binding_schema(self) -> Dict[str, Any]:
        """返回前端动态表单字段定义。

        用于 schema 发现接口，告诉前端该 provider 有哪些字段、
        哪些必填、字段类型和默认值等。
        """

    @abstractmethod
    def validate_binding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """预校验绑定数据。

        Returns:
            {"valid": True/False, "errors": [...]}
        """

    @abstractmethod
    def create_binding(
        self,
        db: Session,
        managed_agent_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """创建绑定，返回结构化响应 dict。"""

    @abstractmethod
    def update_binding(
        self,
        db: Session,
        managed_agent_id: str,
        binding_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """更新绑定，返回结构化响应 dict。"""

    @abstractmethod
    def list_bindings(
        self,
        db: Session,
        managed_agent_id: str,
    ) -> List[Dict[str, Any]]:
        """列出该 Agent 下此 provider 的所有绑定，返回结构化响应列表。"""

    @abstractmethod
    def delete_binding(
        self,
        db: Session,
        managed_agent_id: str,
        binding_id: str,
    ) -> None:
        """删除绑定。"""

    def suggest_binding_defaults(
        self,
        db: Session,
        managed_agent_id: str,
    ) -> Dict[str, Any]:
        """返回创建绑定时的建议默认值（如自动生成的 account_id）。

        非抽象方法，子类可选实现。默认返回空字典。
        """
        return {}
