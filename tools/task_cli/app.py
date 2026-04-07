"""task_cli 共享 CLI 主入口。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Any, Callable

from .commands import (
    register_agent_commands,
    register_log_commands,
    register_module_commands,
    register_notification_commands,
    register_review_commands,
    register_rules_commands,
    register_score_commands,
    register_sub_task_commands,
    register_task_commands,
)
from .http import (
    build_agent_headers,
    build_registration_headers,
    request_json,
    request_text,
)
from .main import (
    build_root_parser,
    finalize_runtime_key,
    print_group_help,
    render_command_help_text,
    render_profile_help_text,
)
from .output import extract_items, print_json
from .profiles import resolve_profile_name
from .runtime import ROLE_CHOICES, build_runtime_config


RequestFn = Callable[..., Any]
RequestTextFn = Callable[..., tuple[int, str]]
HeadersFn = Callable[[str], dict[str, str]]


@dataclass(frozen=True)
class CliAppContext:
    base_url: str
    cli_version: int
    default_api_key: str | None
    agent_role: str | None
    cli_profile: str | None
    role_choices: tuple[str, ...]
    request: RequestFn
    request_json: Callable[..., Any]
    request_text: RequestTextFn
    build_agent_headers: HeadersFn
    build_registration_headers: HeadersFn
    print_json: Callable[[Any], None]
    extract_items: Callable[[Any], list[Any]]

    @property
    def active_profile(self) -> str | None:
        return resolve_profile_name(self.cli_profile, self.agent_role)


def _cmd_register(args, ctx: CliAppContext) -> None:
    data = ctx.request_json(
        "post",
        base_url=ctx.base_url,
        path="/agents/register",
        headers=ctx.build_registration_headers(args.token),
        json_body={"name": args.name, "role": args.role, "description": args.description or ""},
    )
    print("✅ 注册成功")
    print(f"   Agent ID:  {data['id']}")
    print(f"   API Key:   {data['api_key']}")
    print(f"   角色:      {data['role']}")
    print("\n⚠️  请立即将 API Key 保存到你的 SKILL.md 中！")


def _cmd_update(args, ctx: CliAppContext, *, script_path: str) -> None:
    headers = ctx.build_agent_headers(args.key)
    cli_path = Path(script_path).resolve()
    skill_path = cli_path.parent / "SKILL.md"

    print("⬇️  下载最新 task-cli.py ...")
    try:
        status_code, text = ctx.request_text(
            "get",
            base_url=ctx.base_url,
            path="/tools/cli",
            headers=headers,
        )
        if status_code == 200:
            cli_path.write_text(text, encoding="utf-8")
            print("✅ task-cli.py 已更新")
        else:
            print(f"❌ 下载失败 ({status_code}): {text[:200]}")
    except Exception as exc:  # pragma: no cover - 兼容旧异常行为
        print(f"❌ 下载失败: {exc}")

    print("⬇️  下载最新 SKILL.md ...")
    try:
        status_code, text = ctx.request_text(
            "get",
            base_url=ctx.base_url,
            path="/agents/me/skill",
            headers=headers,
        )
        if status_code == 200:
            skill_path.write_text(text, encoding="utf-8")
            print("✅ SKILL.md 已更新（API Key 已自动填入）")
        else:
            print(f"❌ 下载失败 ({status_code}): {text[:200]}")
    except Exception as exc:  # pragma: no cover - 兼容旧异常行为
        print(f"❌ 下载失败: {exc}")


def _cmd_help(args, ctx: CliAppContext) -> None:
    if args.topic:
        text = render_command_help_text(args.topic, ctx.active_profile)
        if text is None:
            print(f"❌ 未知命令组: {args.topic}")
            return
        print(text)
        return
    print(render_profile_help_text(ctx.active_profile))


def run_cli(ctx: CliAppContext, *, argv: list[str] | None = None, script_path: str) -> None:
    parser, subparsers = build_root_parser(default_api_key=ctx.default_api_key)

    parser_register = subparsers.add_parser("register", help="注册 Agent")
    parser_register.add_argument("--name", required=True, help="Agent 名称")
    parser_register.add_argument("--role", required=True, choices=ctx.role_choices)
    parser_register.add_argument("--token", required=True, help="注册令牌")
    parser_register.add_argument("--description", help="职责描述")
    parser_register.set_defaults(func=lambda args: _cmd_register(args, ctx))

    register_rules_commands(subparsers, request=ctx.request, cli_version=ctx.cli_version)

    parser_update = subparsers.add_parser("update", help="自动更新 CLI 工具和 SKILL.md")
    parser_update.set_defaults(func=lambda args: _cmd_update(args, ctx, script_path=script_path))

    parser_help = subparsers.add_parser("help", help="按当前 Profile 查看可用命令")
    parser_help.add_argument("topic", nargs="?", help="查看某个命令组的帮助")
    parser_help.set_defaults(func=lambda args: _cmd_help(args, ctx))

    task_p = register_task_commands(
        subparsers,
        request=ctx.request,
        print_json=ctx.print_json,
        extract_items=ctx.extract_items,
    )
    mod_p = register_module_commands(subparsers, request=ctx.request)
    st_p = register_sub_task_commands(
        subparsers,
        request=ctx.request,
        print_json=ctx.print_json,
        extract_items=ctx.extract_items,
    )
    rev_p = register_review_commands(
        subparsers,
        request=ctx.request,
        print_json=ctx.print_json,
        extract_items=ctx.extract_items,
    )
    score_p = register_score_commands(
        subparsers,
        request=ctx.request,
        extract_items=ctx.extract_items,
    )
    log_p = register_log_commands(subparsers, request=ctx.request)
    register_notification_commands(subparsers, request=ctx.request)
    register_agent_commands(subparsers, request=ctx.request)

    args = parser.parse_args(argv)
    if not args.command:
        print(render_profile_help_text(ctx.active_profile))
        sys.exit(0)

    if args.command in {"register", "help"}:
        args.func(args)
        return

    finalize_runtime_key(args, type("Runtime", (), {"default_api_key": ctx.default_api_key})())

    if not args.key:
        print("❌ 缺少 --key 参数，请提供 API Key")
        sys.exit(1)

    print_group_help(
        args,
        parser=parser,
        help_map={
            "task": task_p,
            "st": st_p,
            "review": rev_p,
            "score": score_p,
            "log": log_p,
            "module": mod_p,
        },
        group_help_renderer=lambda command_name: render_command_help_text(command_name, ctx.active_profile),
    )


def build_default_context():
    runtime = build_runtime_config(
        default_base_url="http://192.168.31.128:6565",
        default_cli_version=2,
    )
    return CliAppContext(
        base_url=runtime.base_url,
        cli_version=runtime.cli_version,
        default_api_key=runtime.default_api_key,
        agent_role=runtime.agent_role,
        cli_profile=runtime.cli_profile,
        role_choices=ROLE_CHOICES,
        request=lambda method, path, key, **kwargs: request_json(
            method,
            base_url=runtime.base_url,
            path=path,
            headers=build_agent_headers(key),
            params=kwargs.get("params"),
            json_body=kwargs.get("json"),
        ),
        request_json=request_json,
        request_text=request_text,
        build_agent_headers=build_agent_headers,
        build_registration_headers=build_registration_headers,
        print_json=print_json,
        extract_items=extract_items,
    )


def run_default_cli(*, argv: list[str] | None = None, script_path: str) -> None:
    run_cli(build_default_context(), argv=argv, script_path=script_path)
