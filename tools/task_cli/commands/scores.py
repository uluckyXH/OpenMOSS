"""score 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]
ExtractItemsFn = Callable[[Any], list[Any]]


def cmd_score_me(args, *, request: RequestFn) -> None:
    data = request("get", "/scores/me", args.key)
    print(f"  Agent: {data['agent_name']}")
    print(f"  总积分: {data['total_score']}")
    print(f"  加分次数: {data['reward_count']}  扣分次数: {data['penalty_count']}")


def cmd_score_logs(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", "/scores/me/logs", args.key, params=params)
    items = extract_items(data)
    if not items:
        print("暂无积分记录")
        return
    for log in items:
        sign = "+" if log["score_delta"] > 0 else ""
        print(f"  {sign}{log['score_delta']}  {log['reason']}")


def cmd_score_agent_logs(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", f"/scores/{args.agent_id}/logs", args.key, params=params)
    items = extract_items(data)
    if not items:
        print("该 Agent 暂无积分记录")
        return
    for log in items:
        sign = "+" if log["score_delta"] > 0 else ""
        print(f"  {sign}{log['score_delta']}  {log['reason']}")


def cmd_score_leaderboard(args, *, request: RequestFn) -> None:
    data = request("get", "/scores/leaderboard", args.key)
    for item in data:
        print(f"  #{item['rank']} {item['agent_name']} ({item['role']}): {item['total_score']}分")


def cmd_score_adjust(args, *, request: RequestFn) -> None:
    body = {
        "agent_id": args.agent_id,
        "score_delta": args.delta,
        "reason": args.reason,
    }
    if args.sub_task_id:
        body["sub_task_id"] = args.sub_task_id
    data = request("post", "/scores/adjust", args.key, json=body)
    sign = "+" if data["score_delta"] > 0 else ""
    print(f"✅ 积分已调整: {sign}{data['score_delta']}  原因: {data['reason']}")


def register_score_commands(subparsers, *, request: RequestFn, extract_items: ExtractItemsFn):
    def _bind(handler, **extra_kwargs):
        def _run(args):
            return handler(args, **extra_kwargs)

        return _run

    score_parser = subparsers.add_parser("score", help="积分管理")
    score_sub = score_parser.add_subparsers(dest="score_cmd")

    parser = score_sub.add_parser("me", help="查看我的积分")
    parser.set_defaults(func=_bind(cmd_score_me, request=request))

    parser = score_sub.add_parser("logs", help="查看积分明细")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_score_logs, request=request, extract_items=extract_items))

    parser = score_sub.add_parser("agent-logs", help="查看指定 Agent 的积分明细")
    parser.add_argument("agent_id", help="目标 Agent ID")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_score_agent_logs, request=request, extract_items=extract_items))

    parser = score_sub.add_parser("leaderboard", help="积分排行榜")
    parser.set_defaults(func=_bind(cmd_score_leaderboard, request=request))

    parser = score_sub.add_parser("adjust", help="手动调整 Agent 积分（仅 reviewer/planner）")
    parser.add_argument("agent_id", help="目标 Agent ID")
    parser.add_argument("delta", type=int, help="积分变化量（正数加分，负数扣分）")
    parser.add_argument("reason", help="调整原因")
    parser.add_argument("--sub-task-id", help="关联子任务 ID（可选）")
    parser.set_defaults(func=_bind(cmd_score_adjust, request=request))

    return score_parser
