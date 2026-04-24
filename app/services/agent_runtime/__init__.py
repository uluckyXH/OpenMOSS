"""agent-runtime 功能域服务包。

对外仅通过本文件导入，其他模块不应直接 import 子模块文件。
"""
# --- agent ---
from .agent import (
    delete_agent,
    generate_api_key,
    get_agent_by_id,
    get_agent_related_counts,
    has_any_agent,
    list_agents,
    register_agent,
    reset_agent_api_key,
    update_agent_profile,
    update_agent_status,
    upsert_agent_presence,
)
# --- feed ---
from .feed import (
    get_feed_agent_summaries,
    list_feed_agents,
    list_feed_logs,
)
# --- activity_log ---
from .activity_log import (
    DEFAULT_DAYS,
    DEFAULT_LIMIT,
    MAX_LIMIT,
    VALID_ACTIONS,
    create_activity_log,
    list_activity_logs,
    list_my_activity_logs,
    validate_action,
)

__all__ = [
    # agent
    "delete_agent",
    "generate_api_key",
    "get_agent_by_id",
    "get_agent_related_counts",
    "has_any_agent",
    "list_agents",
    "register_agent",
    "reset_agent_api_key",
    "update_agent_profile",
    "update_agent_status",
    "upsert_agent_presence",
    # feed
    "get_feed_agent_summaries",
    "list_feed_agents",
    "list_feed_logs",
    # activity_log
    "DEFAULT_DAYS",
    "DEFAULT_LIMIT",
    "MAX_LIMIT",
    "VALID_ACTIONS",
    "create_activity_log",
    "list_activity_logs",
    "list_my_activity_logs",
    "validate_action",
]
