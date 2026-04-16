"""
通讯平台适配器注册表。

通过 (host_platform, comm_provider) 二元组查找对应的适配器实例。
"""

from __future__ import annotations

from typing import Optional

from app.exceptions import NotFoundError

from .base import CommProviderAdapter
from .openclaw.comm.feishu import OpenClawFeishuAdapter


# (host_platform, comm_provider) → adapter instance
_COMM_PROVIDER_ADAPTERS: dict[tuple[str, str], CommProviderAdapter] = {
    ("openclaw", "feishu"): OpenClawFeishuAdapter(),
}


def get_comm_provider_adapter(
    host_platform: str,
    comm_provider: str,
) -> CommProviderAdapter:
    """查找通讯平台适配器。

    Raises:
        NotFoundError: 找不到 (host_platform, comm_provider) 组合
    """
    adapter = _COMM_PROVIDER_ADAPTERS.get((host_platform, comm_provider))
    if adapter is None:
        raise NotFoundError(
            f"不支持的通讯平台组合: {host_platform} + {comm_provider}"
        )
    return adapter


def list_comm_providers_for_platform(host_platform: str) -> list[str]:
    """返回指定宿主平台支持的所有通讯平台标识。"""
    return sorted(
        provider
        for (platform, provider) in _COMM_PROVIDER_ADAPTERS
        if platform == host_platform
    )
