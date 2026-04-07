"""task_cli CLI 入口基础骨架。"""

import argparse

from .command_registry import (
    GROUP_TITLES,
    get_command_meta,
    iter_visible_commands,
    iter_visible_subcommands,
)
from .profiles import get_profile_meta
from .runtime import RuntimeConfig, resolve_api_key


def build_root_parser(*, default_api_key: str | None = None) -> tuple[argparse.ArgumentParser, argparse._SubParsersAction]:
    """创建根 parser 与一级 subparsers。"""
    parser = argparse.ArgumentParser(
        description="OpenMOSS 任务调度 CLI 工具",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--key", default=default_api_key, help="API Key（注册后获取，可由专属 task-cli.py 预置）")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    return parser, subparsers


def finalize_runtime_key(args, runtime: RuntimeConfig) -> None:
    """统一收敛命令行 key 与运行时默认 key。"""
    args.key = resolve_api_key(getattr(args, "key", None), runtime)


def print_group_help(
    args,
    *,
    parser,
    help_map: dict[str, argparse.ArgumentParser],
    group_help_renderer=None,
) -> None:
    """当二级子命令缺失时，打印对应分组帮助。"""
    if hasattr(args, "func"):
        args.func(args)
        return

    if group_help_renderer is not None:
        rendered = group_help_renderer(getattr(args, "command", ""))
        if rendered:
            print(rendered)
            return

    group_parser = help_map.get(getattr(args, "command", ""))
    if group_parser is not None:
        group_parser.print_help()
        return

    parser.print_help()


def render_profile_help_text(profile_name: str | None) -> str:
    lines = ["OpenMOSS task-cli 帮助"]
    profile = get_profile_meta(profile_name)
    if profile is not None:
        lines.append(f"当前 Profile: {profile.title} ({profile.name})")
        lines.append(f"说明: {profile.summary}")
    else:
        lines.append("当前 Profile: 通用")

    grouped: dict[str, list[tuple[str, str]]] = {}
    for command_name, meta in iter_visible_commands(profile_name):
        grouped.setdefault(meta.group, []).append((command_name, meta.summary))

    for group_name, commands in grouped.items():
        lines.append("")
        lines.append(f"{GROUP_TITLES.get(group_name, group_name)}:")
        for command_name, summary in commands:
            lines.append(f"  {command_name:<12} {summary}")

    lines.append("")
    lines.append("可用方式:")
    lines.append("  task-cli.py help")
    lines.append("  task-cli.py help <command>")
    return "\n".join(lines)


def render_command_help_text(command_name: str, profile_name: str | None) -> str | None:
    meta = get_command_meta(command_name)
    if meta is None:
        return None

    lines = [f"{command_name} - {meta.summary}"]
    profile = get_profile_meta(profile_name)
    if profile is not None:
        lines.append(f"当前 Profile: {profile.title} ({profile.name})")

    subcommands = iter_visible_subcommands(command_name, profile_name)
    if not subcommands:
        return "\n".join(lines)

    lines.append("")
    lines.append("可用子命令:")
    for subcommand_name, sub_meta in subcommands:
        lines.append(f"  {subcommand_name:<12} {sub_meta.summary}")
    return "\n".join(lines)
