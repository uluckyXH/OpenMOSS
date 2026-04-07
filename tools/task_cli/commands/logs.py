"""log 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]


def cmd_log_create(args, *, request: RequestFn) -> None:
    body = {"action": args.action, "summary": args.summary}
    if args.sub_task_id:
        body["sub_task_id"] = args.sub_task_id
    data = request("post", "/logs", args.key, json=body)
    print(f"✅ 日志已写入: {data['action']}")


def cmd_log_mine(args, *, request: RequestFn) -> None:
    params = {}
    if args.action:
        params["action"] = args.action
    if args.days:
        params["days"] = args.days
    if args.limit:
        params["limit"] = args.limit
    data = request("get", "/logs/mine", args.key, params=params)
    if not data:
        print("暂无日志记录")
        return
    for log in data:
        print(f"  [{log['action']}] {log['summary']}")


def cmd_log_list(args, *, request: RequestFn) -> None:
    params = {}
    if args.sub_task_id:
        params["sub_task_id"] = args.sub_task_id
    if args.action:
        params["action"] = args.action
    if args.days:
        params["days"] = args.days
    if args.limit:
        params["limit"] = args.limit
    data = request("get", "/logs", args.key, params=params)
    if not data:
        print("暂无日志记录")
        return
    for log in data:
        print(f"  [{log['action']}] {log['summary']}")


def register_log_commands(subparsers, *, request: RequestFn):
    def _bind(handler, **extra_kwargs):
        def _run(args):
            return handler(args, **extra_kwargs)

        return _run

    log_parser = subparsers.add_parser("log", help="活动日志")
    log_sub = log_parser.add_subparsers(dest="log_cmd")

    parser = log_sub.add_parser("create", help="写入日志")
    parser.add_argument("action", help="操作类型")
    parser.add_argument("summary", help="操作摘要")
    parser.add_argument("--sub-task-id", help="关联子任务 ID")
    parser.set_defaults(func=_bind(cmd_log_create, request=request))

    parser = log_sub.add_parser("mine", help="查看我的日志")
    parser.add_argument("--action", help="按操作类型过滤（如 reflection）")
    parser.add_argument("--days", type=int, help="最近N天（默认7，最大60）")
    parser.add_argument("--limit", type=int, help="返回条数（默认20，最大500）")
    parser.set_defaults(func=_bind(cmd_log_mine, request=request))

    parser = log_sub.add_parser("list", help="查看活动日志（含其他 Agent）")
    parser.add_argument("--sub-task-id", help="按子任务 ID 过滤")
    parser.add_argument("--action", help="按操作类型过滤")
    parser.add_argument("--days", type=int, help="最近N天（默认7，最大60）")
    parser.add_argument("--limit", type=int, help="返回条数（默认20，最大100）")
    parser.set_defaults(func=_bind(cmd_log_list, request=request))

    return log_parser
