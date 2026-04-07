"""命令注册表。"""

from __future__ import annotations

from dataclasses import dataclass, field


ALL_PROFILES = frozenset({"planner", "executor", "reviewer", "patrol"})

GROUP_TITLES = {
    "core": "核心命令",
    "planning": "任务与编排",
    "review": "审查与反馈",
    "score": "积分",
    "observe": "观察与运行",
}


@dataclass(frozen=True)
class SubcommandMeta:
    summary: str
    visible_in_profiles: frozenset[str] = field(default_factory=lambda: ALL_PROFILES)


@dataclass(frozen=True)
class CommandMeta:
    summary: str
    group: str
    visible_in_profiles: frozenset[str] = field(default_factory=lambda: ALL_PROFILES)
    subcommands: dict[str, SubcommandMeta] = field(default_factory=dict)


COMMAND_REGISTRY: dict[str, CommandMeta] = {
    "help": CommandMeta(summary="查看当前 Profile 可用命令", group="core"),
    "register": CommandMeta(summary="注册 Agent", group="core"),
    "rules": CommandMeta(summary="获取规则提示词", group="core"),
    "update": CommandMeta(summary="自动更新 CLI 工具和 SKILL.md", group="core"),
    "task": CommandMeta(
        summary="任务管理",
        group="planning",
        subcommands={
            "create": SubcommandMeta("创建任务", frozenset({"planner"})),
            "list": SubcommandMeta("查看任务列表", frozenset({"planner", "reviewer", "patrol"})),
            "get": SubcommandMeta("查看任务详情", frozenset({"planner", "reviewer", "patrol"})),
            "edit": SubcommandMeta("编辑任务", frozenset({"planner"})),
            "status": SubcommandMeta("更新任务状态", frozenset({"planner"})),
            "cancel": SubcommandMeta("取消任务", frozenset({"planner"})),
        },
    ),
    "module": CommandMeta(
        summary="模块管理",
        group="planning",
        visible_in_profiles=frozenset({"planner"}),
        subcommands={
            "create": SubcommandMeta("创建模块", frozenset({"planner"})),
            "list": SubcommandMeta("查看模块列表", frozenset({"planner"})),
        },
    ),
    "st": CommandMeta(
        summary="子任务管理",
        group="planning",
        subcommands={
            "create": SubcommandMeta("创建子任务", frozenset({"planner"})),
            "list": SubcommandMeta("查看子任务列表", frozenset({"planner", "reviewer", "patrol"})),
            "get": SubcommandMeta("查看子任务详情", frozenset({"planner", "executor", "reviewer", "patrol"})),
            "mine": SubcommandMeta("查看我的子任务", frozenset({"executor"})),
            "available": SubcommandMeta("查看可认领的子任务", frozenset({"executor", "patrol"})),
            "latest": SubcommandMeta("获取某任务下我的最新子任务", frozenset({"executor"})),
            "claim": SubcommandMeta("认领子任务", frozenset({"executor"})),
            "start": SubcommandMeta("开始执行", frozenset({"executor"})),
            "submit": SubcommandMeta("提交成果", frozenset({"executor"})),
            "edit": SubcommandMeta("编辑子任务", frozenset({"planner"})),
            "cancel": SubcommandMeta("取消子任务", frozenset({"planner"})),
            "block": SubcommandMeta("标记异常", frozenset({"executor"})),
            "session": SubcommandMeta("更新会话 ID", frozenset({"executor"})),
            "reassign": SubcommandMeta("重新分配", frozenset({"planner"})),
        },
    ),
    "review": CommandMeta(
        summary="审查管理",
        group="review",
        visible_in_profiles=frozenset({"executor", "reviewer"}),
        subcommands={
            "create": SubcommandMeta("提交审查", frozenset({"reviewer"})),
            "list": SubcommandMeta("查看审查记录", frozenset({"executor", "reviewer"})),
            "get": SubcommandMeta("查看审查详情", frozenset({"executor", "reviewer"})),
        },
    ),
    "score": CommandMeta(
        summary="积分管理",
        group="score",
        subcommands={
            "me": SubcommandMeta("查看我的积分", frozenset({"planner", "executor", "reviewer"})),
            "logs": SubcommandMeta("查看积分明细", frozenset({"planner", "executor", "reviewer"})),
            "agent-logs": SubcommandMeta("查看指定 Agent 的积分明细", frozenset({"planner"})),
            "leaderboard": SubcommandMeta("积分排行榜", frozenset({"planner", "executor", "reviewer", "patrol"})),
            "adjust": SubcommandMeta("手动调整 Agent 积分", frozenset({"planner", "reviewer"})),
        },
    ),
    "log": CommandMeta(
        summary="活动日志",
        group="observe",
        subcommands={
            "create": SubcommandMeta("写入日志", frozenset({"planner", "executor", "reviewer"})),
            "mine": SubcommandMeta("查看我的日志", frozenset({"planner", "executor", "reviewer", "patrol"})),
            "list": SubcommandMeta("查看活动日志", frozenset({"planner", "executor", "reviewer", "patrol"})),
        },
    ),
    "notification": CommandMeta(summary="查看通知配置", group="observe"),
    "agents": CommandMeta(summary="查看 Agent 列表", group="observe"),
}


def is_visible(visible_in_profiles: frozenset[str], profile_name: str | None) -> bool:
    return profile_name is None or profile_name in visible_in_profiles


def get_command_meta(command_name: str) -> CommandMeta | None:
    return COMMAND_REGISTRY.get(command_name)


def iter_visible_commands(profile_name: str | None):
    for command_name, meta in COMMAND_REGISTRY.items():
        if is_visible(meta.visible_in_profiles, profile_name):
            yield command_name, meta


def iter_visible_subcommands(command_name: str, profile_name: str | None):
    meta = get_command_meta(command_name)
    if meta is None:
        return []
    visible = []
    for subcommand_name, sub_meta in meta.subcommands.items():
        if is_visible(sub_meta.visible_in_profiles, profile_name):
            visible.append((subcommand_name, sub_meta))
    return visible
