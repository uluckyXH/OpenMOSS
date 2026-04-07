"""task_cli 运行时配置。

当前阶段先收拢：
- BASE_URL
- CLI_VERSION
- DEFAULT_API_KEY
- AGENT_ID / AGENT_NAME / AGENT_ROLE
- CLI_PROFILE
"""

from dataclasses import dataclass
import os
from typing import Optional


ROLE_CHOICES = ("planner", "executor", "reviewer", "patrol")
DEFAULT_BASE_URL = "http://192.168.31.128:6565"
DEFAULT_CLI_VERSION = 2


@dataclass(frozen=True)
class RuntimeConfig:
    """task_cli 运行时上下文。"""

    base_url: str
    cli_version: int
    default_api_key: Optional[str] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None
    cli_profile: Optional[str] = None


def _read_env_int(env_name: str, default: int) -> int:
    """读取整数环境变量，非法值时回退默认值。"""
    value = os.getenv(env_name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_runtime_config(
    *,
    default_base_url: str = DEFAULT_BASE_URL,
    default_cli_version: int = DEFAULT_CLI_VERSION,
    default_api_key: Optional[str] = None,
    agent_id: Optional[str] = None,
    agent_name: Optional[str] = None,
    agent_role: Optional[str] = None,
    cli_profile: Optional[str] = None,
) -> RuntimeConfig:
    """构造运行时配置。

    优先级：
    1. 显式传参
    2. 环境变量
    3. 默认值
    """

    return RuntimeConfig(
        base_url=os.getenv("OPENMOSS_BASE_URL", default_base_url),
        cli_version=_read_env_int("OPENMOSS_CLI_VERSION", default_cli_version),
        default_api_key=os.getenv("OPENMOSS_DEFAULT_API_KEY", default_api_key),
        agent_id=os.getenv("OPENMOSS_AGENT_ID", agent_id),
        agent_name=os.getenv("OPENMOSS_AGENT_NAME", agent_name),
        agent_role=os.getenv("OPENMOSS_AGENT_ROLE", agent_role),
        cli_profile=os.getenv("OPENMOSS_CLI_PROFILE", cli_profile),
    )


def resolve_api_key(cli_key: Optional[str], runtime: RuntimeConfig) -> Optional[str]:
    """优先使用命令行传入的 key，其次回退到运行时默认 key。"""
    return cli_key or runtime.default_api_key
