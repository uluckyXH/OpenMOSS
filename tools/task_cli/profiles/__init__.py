"""角色 Profile 定义。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileMeta:
    name: str
    title: str
    summary: str


PROFILE_REGISTRY = {
    "planner": ProfileMeta("planner", "Planner", "偏任务编排与推进"),
    "executor": ProfileMeta("executor", "Executor", "偏执行闭环与交付"),
    "reviewer": ProfileMeta("reviewer", "Reviewer", "偏审查与质量反馈"),
    "patrol": ProfileMeta("patrol", "Patrol", "偏巡检、观察与监控"),
}


def resolve_profile_name(cli_profile: str | None, agent_role: str | None) -> str | None:
    if cli_profile in PROFILE_REGISTRY:
        return cli_profile
    if agent_role in PROFILE_REGISTRY:
        return agent_role
    return None


def get_profile_meta(profile_name: str | None) -> ProfileMeta | None:
    if profile_name is None:
        return None
    return PROFILE_REGISTRY.get(profile_name)
