"""notification 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]


def cmd_notification(args, *, request: RequestFn) -> None:
    data = request("get", "/config/notification", args.key)
    print(f"  启用: {data['enabled']}")
    print(f"  渠道: {', '.join(data['channels']) if data['channels'] else '未配置'}")
    print(f"  事件: {', '.join(data['events']) if data['events'] else '未配置'}")


def register_notification_commands(subparsers, *, request: RequestFn):
    parser = subparsers.add_parser("notification", help="查看通知配置")

    def _run(args):
        return cmd_notification(args, request=request)

    parser.set_defaults(func=_run)
    return parser
