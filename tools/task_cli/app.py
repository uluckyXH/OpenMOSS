"""task_cli 共享 CLI 主入口。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Callable
import zipfile

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
    request_bytes,
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
from .runtime import DEFAULT_CLI_VERSION, ROLE_CHOICES, build_runtime_config


RequestFn = Callable[..., Any]
RequestTextFn = Callable[..., tuple[int, str]]
RequestBytesFn = Callable[..., tuple[int, bytes]]
HeadersFn = Callable[[str], dict[str, str]]


@dataclass(frozen=True)
class CliAppContext:
    base_url: str
    cli_version: int
    default_api_key: str | None
    agent_id: str | None
    agent_name: str | None
    agent_role: str | None
    cli_profile: str | None
    role_choices: tuple[str, ...]
    request: RequestFn
    request_json: Callable[..., Any]
    request_text: RequestTextFn
    request_bytes: RequestBytesFn
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


def _detect_skill_layout(script_path: str) -> tuple[str, Path]:
    """根据当前入口文件路径识别 Skill 目录结构。"""
    cli_path = Path(script_path).resolve()
    if cli_path.parent.name == "scripts":
        bundle_root = cli_path.parent.parent
        if (bundle_root / "SKILL.md").exists():
            return "bundle", bundle_root
    return "legacy", cli_path.parent


def _extract_bundle_root(temp_dir: Path) -> Path:
    """从临时解压目录中定位 bundle 根目录。"""
    candidates = [path for path in temp_dir.iterdir() if path.is_dir()]
    if len(candidates) != 1:
        raise RuntimeError("skill-bundle 结构无效，无法定位根目录")
    return candidates[0]


def _copy_bundle_tree(source_root: Path, target_root: Path) -> None:
    """把解压后的 bundle 内容覆盖到目标目录。"""
    if target_root.exists():
        shutil.rmtree(target_root / "references", ignore_errors=True)
        shutil.rmtree(target_root / "scripts" / "task_cli", ignore_errors=True)

    target_root.mkdir(parents=True, exist_ok=True)
    for path in sorted(source_root.rglob("*")):
        relative_path = path.relative_to(source_root)
        destination = target_root / relative_path
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)


def _write_legacy_launcher(cli_path: Path) -> None:
    """为旧单文件目录写入兼容入口，转发到新 bundle 入口。"""
    cli_path.write_text(
        """#!/usr/bin/env python3
from __future__ import annotations

import runpy
from pathlib import Path


def main() -> int:
    entry = Path(__file__).resolve().parent / "scripts" / "task-cli.py"
    if not entry.exists():
        raise SystemExit("未找到新的 Skill Bundle 入口: scripts/task-cli.py")
    runpy.run_path(str(entry), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""",
        encoding="utf-8",
    )


def _apply_skill_bundle_update(bundle_bytes: bytes, *, script_path: str) -> tuple[str, Path]:
    """把下载到的 skill-bundle 应用到本地目录。"""
    layout, target_root = _detect_skill_layout(script_path)
    cli_path = Path(script_path).resolve()

    with tempfile.TemporaryDirectory(prefix="openmoss-skill-bundle-") as tmp_dir:
        temp_root = Path(tmp_dir)
        bundle_path = temp_root / "bundle.zip"
        bundle_path.write_bytes(bundle_bytes)

        extract_dir = temp_root / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(bundle_path, "r") as zip_file:
            zip_file.extractall(extract_dir)

        source_root = _extract_bundle_root(extract_dir)
        _copy_bundle_tree(source_root, target_root)

    if layout == "legacy":
        _write_legacy_launcher(cli_path)

    return layout, target_root


def _cmd_legacy_text_update(args, ctx: CliAppContext, *, skill_root: Path, script_path: str) -> None:
    """旧版文本更新路径，仅用于服务端尚未提供 bundle 接口时兜底。"""
    headers = ctx.build_agent_headers(args.key)
    cli_path = Path(script_path).resolve()

    print("⚠️ 服务端未提供 skill-bundle 更新接口，回退到旧版文本更新")

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
            skill_path = skill_root / "SKILL.md"
            skill_path.write_text(text, encoding="utf-8")
            print("✅ SKILL.md 已更新")
        else:
            print(f"❌ 下载失败 ({status_code}): {text[:200]}")
    except Exception as exc:  # pragma: no cover - 兼容旧异常行为
        print(f"❌ 下载失败: {exc}")


def _cmd_update(args, ctx: CliAppContext, *, script_path: str) -> None:
    headers = ctx.build_agent_headers(args.key)
    layout, skill_root = _detect_skill_layout(script_path)

    print("⬇️  下载最新 Skill Bundle ...")
    try:
        status_code, content = ctx.request_bytes(
            "get",
            base_url=ctx.base_url,
            path="/agents/me/skill-bundle",
            headers=headers,
        )
        if status_code == 200:
            applied_layout, applied_root = _apply_skill_bundle_update(content, script_path=script_path)
            print("✅ Skill Bundle 已更新")
            print(f"   目录: {applied_root}")
            if applied_layout == "legacy":
                print("ℹ️  旧版单文件目录已迁移到 Skill Bundle 结构，标准入口为 scripts/task-cli.py")
            return
        if status_code == 404:
            _cmd_legacy_text_update(args, ctx, skill_root=skill_root, script_path=script_path)
            return
        print(f"❌ 下载失败 ({status_code}): {content.decode('utf-8', errors='replace')[:200]}")
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

    parser_update = subparsers.add_parser("update", help="自动更新当前 Skill Bundle")
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
        default_cli_version=DEFAULT_CLI_VERSION,
    )
    return CliAppContext(
        base_url=runtime.base_url,
        cli_version=runtime.cli_version,
        default_api_key=runtime.default_api_key,
        agent_id=runtime.agent_id,
        agent_name=runtime.agent_name,
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
        request_bytes=request_bytes,
        build_agent_headers=build_agent_headers,
        build_registration_headers=build_registration_headers,
        print_json=print_json,
        extract_items=extract_items,
    )


def run_default_cli(*, argv: list[str] | None = None, script_path: str) -> None:
    run_cli(build_default_context(), argv=argv, script_path=script_path)


def build_skill_context(
    *,
    base_url: str,
    cli_version: int = DEFAULT_CLI_VERSION,
    default_api_key: str | None = None,
    agent_id: str | None = None,
    agent_name: str | None = None,
    agent_role: str | None = None,
    cli_profile: str | None = None,
) -> CliAppContext:
    runtime = build_runtime_config(
        default_base_url=base_url,
        default_cli_version=cli_version,
        default_api_key=default_api_key,
        agent_id=agent_id,
        agent_name=agent_name,
        agent_role=agent_role,
        cli_profile=cli_profile,
    )
    return CliAppContext(
        base_url=runtime.base_url,
        cli_version=runtime.cli_version,
        default_api_key=runtime.default_api_key,
        agent_id=runtime.agent_id,
        agent_name=runtime.agent_name,
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
        request_bytes=request_bytes,
        build_agent_headers=build_agent_headers,
        build_registration_headers=build_registration_headers,
        print_json=print_json,
        extract_items=extract_items,
    )


def run_skill_cli(
    *,
    script_path: str,
    argv: list[str] | None = None,
    base_url: str,
    cli_version: int = DEFAULT_CLI_VERSION,
    default_api_key: str | None = None,
    agent_id: str | None = None,
    agent_name: str | None = None,
    agent_role: str | None = None,
    cli_profile: str | None = None,
) -> None:
    run_cli(
        build_skill_context(
            base_url=base_url,
            cli_version=cli_version,
            default_api_key=default_api_key,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_role=agent_role,
            cli_profile=cli_profile,
        ),
        argv=argv,
        script_path=script_path,
    )
