"""agents 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]


def cmd_agent_list(args, *, request: RequestFn) -> None:
    params = {}
    if args.role:
        params["role"] = args.role
    data = request("get", "/agents", args.key, params=params)
    for agent in data:
        desc = f" — {agent['description']}" if agent.get("description") else ""
        print(
            f"  [{agent['status']}] {agent['name']} ({agent['role']}) "
            f"ID:{agent['id']} 积分:{agent['total_score']}{desc}"
        )


def register_agent_commands(subparsers, *, request: RequestFn):
    parser = subparsers.add_parser("agents", help="查看 Agent 列表")
    parser.add_argument("--role", help="按角色过滤")

    def _run(args):
        return cmd_agent_list(args, request=request)

    parser.set_defaults(func=_run)
    return parser
