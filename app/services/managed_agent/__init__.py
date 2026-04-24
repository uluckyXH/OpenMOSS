"""managed_agent 子系统服务包。"""
# --- core ---
from .core import (
    create_managed_agent,
    delete_managed_agent,
    get_managed_agent,
    get_managed_agent_or_404,
    list_managed_agents,
    update_managed_agent,
)
# --- host config / prompt asset ---
from .host_config import get_host_config, serialize_host_config, update_host_config
from .prompt_asset import (
    get_prompt_asset,
    list_prompt_templates,
    render_prompt_preview,
    reset_prompt_from_template,
    update_prompt_asset,
)
# --- schedules / comm bindings ---
from .schedule import (
    create_schedule,
    delete_schedule,
    delete_schedule_for_agent,
    get_schedule_or_404,
    get_schedule_for_agent_or_404,
    list_schedules,
    update_schedule,
    update_schedule_for_agent,
)
from .comm_binding import (
    create_comm_binding,
    delete_comm_binding,
    delete_comm_binding_for_agent,
    get_comm_binding_or_404,
    get_comm_binding_for_agent_or_404,
    list_comm_bindings,
    serialize_comm_binding,
    update_comm_binding,
    update_comm_binding_for_agent,
)
# --- derived views ---
from .readiness import compute_readiness_for_agent, compute_readiness_for_agents
from .runtime_identity import (
    compute_runtime_identity_for_agent,
    compute_runtime_identity_for_agents,
    reset_runtime_api_key_for_managed_agent,
)
from .platform_meta import list_supported_host_platforms
# --- deployment / changeset ---
from .changeset import compute_changeset
from .deployment import (
    build_snapshot_json,
    confirm_deployment_snapshot,
    create_deployment_snapshot,
    dismiss_snapshot_resources,
    expire_stale_pending_snapshots,
    fail_deployment_snapshot,
    get_latest_confirmed_snapshot,
    list_deployment_snapshots,
    parse_snapshot_json,
    serialize_deployment_snapshot,
)
# --- migration ---
from .migration import auto_backfill_from_runtime, build_migration_report
__all__ = [
    "auto_backfill_from_runtime",
    "build_migration_report",
    "build_snapshot_json",
    "compute_changeset",
    "compute_readiness_for_agent",
    "compute_readiness_for_agents",
    "compute_runtime_identity_for_agent",
    "compute_runtime_identity_for_agents",
    "confirm_deployment_snapshot",
    "create_comm_binding",
    "create_deployment_snapshot",
    "create_managed_agent",
    "create_schedule",
    "delete_comm_binding",
    "delete_comm_binding_for_agent",
    "delete_managed_agent",
    "delete_schedule",
    "delete_schedule_for_agent",
    "dismiss_snapshot_resources",
    "expire_stale_pending_snapshots",
    "fail_deployment_snapshot",
    "get_comm_binding_or_404",
    "get_comm_binding_for_agent_or_404",
    "get_host_config",
    "get_latest_confirmed_snapshot",
    "get_managed_agent",
    "get_managed_agent_or_404",
    "get_prompt_asset",
    "get_schedule_or_404",
    "get_schedule_for_agent_or_404",
    "list_comm_bindings",
    "list_deployment_snapshots",
    "list_managed_agents",
    "list_prompt_templates",
    "list_supported_host_platforms",
    "list_schedules",
    "parse_snapshot_json",
    "render_prompt_preview",
    "reset_prompt_from_template",
    "reset_runtime_api_key_for_managed_agent",
    "serialize_comm_binding",
    "serialize_deployment_snapshot",
    "serialize_host_config",
    "update_comm_binding",
    "update_comm_binding_for_agent",
    "update_host_config",
    "update_managed_agent",
    "update_prompt_asset",
    "update_schedule",
    "update_schedule_for_agent",
]
