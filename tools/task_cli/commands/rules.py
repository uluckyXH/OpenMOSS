"""rules 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]


def cmd_rules(args, *, request: RequestFn, cli_version: int) -> None:
    data = request("get", "/rules", args.key, params={"cli_version": cli_version})
    print(data.get("content", ""))
    if data.get("update_available"):
        print(f"\n⚠️ 工具更新可用 (v{cli_version} → v{data.get('latest_version', '?')})")
        if data.get("update_instructions"):
            print(data["update_instructions"])


def register_rules_commands(
    subparsers,
    *,
    request: RequestFn,
    cli_version: int,
):
    parser = subparsers.add_parser("rules", help="获取规则提示词")

    def _run(args):
        return cmd_rules(args, request=request, cli_version=cli_version)

    parser.set_defaults(func=_run)
    return parser
