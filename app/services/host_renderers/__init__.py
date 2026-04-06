"""
宿主平台 renderer 注册表。
"""

from __future__ import annotations

from app.exceptions import BusinessError

from .base import BaseHostRenderer
from .openclaw_renderer import OpenClawRenderer


RENDERER_REGISTRY: dict[str, BaseHostRenderer] = {
    "openclaw": OpenClawRenderer(),
}


def get_renderer(host_platform: str) -> BaseHostRenderer:
    """按宿主平台返回 renderer。"""
    renderer = RENDERER_REGISTRY.get(host_platform)
    if not renderer:
        raise BusinessError(f"未注册的宿主平台 renderer: {host_platform}")
    return renderer


__all__ = [
    "BaseHostRenderer",
    "OpenClawRenderer",
    "RENDERER_REGISTRY",
    "get_renderer",
]
