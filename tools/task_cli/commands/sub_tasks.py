"""sub_tasks 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]
PrintJsonFn = Callable[[Any], None]
ExtractItemsFn = Callable[[Any], list[Any]]


def cmd_sub_task_create(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    body = {
        "task_id": args.task_id,
        "name": args.name,
        "description": args.desc or "",
        "deliverable": args.deliverable or "",
        "acceptance": args.acceptance or "",
        "priority": args.priority,
        "type": args.type,
    }
    if args.module_id:
        body["module_id"] = args.module_id
    if args.assign:
        body["assigned_agent"] = args.assign
    data = request("post", "/sub-tasks", args.key, json=body)
    print(f"✅ 子任务已创建: {data['id']}")
    print_json(data)


def cmd_sub_task_list(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if args.task_id:
        params["task_id"] = args.task_id
    if args.status:
        params["status"] = args.status
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", "/sub-tasks", args.key, params=params)
    items = extract_items(data)
    if not items:
        print("暂无子任务")
        return
    for sub_task in items:
        agent = sub_task.get("assigned_agent") or "-"
        print(f"  [{sub_task['status']}] {sub_task['name']} (ID:{sub_task['id']} Agent:{agent})")


def cmd_sub_task_get(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    data = request("get", f"/sub-tasks/{args.id}", args.key)
    print_json(data)


def cmd_sub_task_mine(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", "/sub-tasks/mine", args.key, params=params)
    items = extract_items(data)
    if not items:
        print("暂无分配给你的子任务")
        return
    for sub_task in items:
        print(f"  [{sub_task['status']}] {sub_task['name']} (ID:{sub_task['id']})")


def cmd_sub_task_available(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", "/sub-tasks/available", args.key, params=params)
    items = extract_items(data)
    if not items:
        print("暂无可认领的子任务")
        return
    for sub_task in items:
        print(f"  [{sub_task['priority']}] {sub_task['name']} (ID:{sub_task['id']})")


def cmd_sub_task_latest(args, *, request: RequestFn) -> None:
    data = request("get", "/sub-tasks/latest", args.key, params={"task_id": args.task_id})
    if data:
        print(f"  [{data['status']}] {data['name']}")
        print(f"  ID: {data['id']}")
        if data.get("description"):
            print(f"  描述: {data['description']}")
        if data.get("deliverable"):
            print(f"  交付物: {data['deliverable']}")
        if data.get("acceptance"):
            print(f"  验收标准: {data['acceptance']}")


def cmd_sub_task_claim(args, *, request: RequestFn) -> None:
    data = request("post", f"/sub-tasks/{args.id}/claim", args.key, json={})
    print(f"✅ 已认领: {data['name']}")


def cmd_sub_task_start(args, *, request: RequestFn) -> None:
    body = {}
    if hasattr(args, "session") and args.session:
        body["session_id"] = args.session
    data = request("post", f"/sub-tasks/{args.id}/start", args.key, json=body)
    print(f"✅ 已开始: {data['name']}")
    if data.get("current_session_id"):
        print(f"   会话: {data['current_session_id']}")


def cmd_sub_task_submit(args, *, request: RequestFn) -> None:
    data = request("post", f"/sub-tasks/{args.id}/submit", args.key)
    print(f"✅ 已提交: {data['name']}，等待审查")


def cmd_sub_task_edit(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    body = {}
    if args.name:
        body["name"] = args.name
    if args.desc:
        body["description"] = args.desc
    if args.deliverable:
        body["deliverable"] = args.deliverable
    if args.acceptance:
        body["acceptance"] = args.acceptance
    if args.priority:
        body["priority"] = args.priority
    data = request("put", f"/sub-tasks/{args.id}", args.key, json=body)
    print("✅ 子任务已更新")
    print_json(data)


def cmd_sub_task_cancel(args, *, request: RequestFn) -> None:
    data = request("post", f"/sub-tasks/{args.id}/cancel", args.key, json={})
    print(f"✅ 子任务已取消: {data['id']}")


def cmd_sub_task_block(args, *, request: RequestFn) -> None:
    data = request("post", f"/sub-tasks/{args.id}/block", args.key, json={})
    print(f"⚠️ 已标记 blocked: {data['name']}")


def cmd_sub_task_session(args, *, request: RequestFn) -> None:
    data = request("post", f"/sub-tasks/{args.id}/session", args.key, json={"session_id": args.session_id})
    print(f"✅ 会话已更新: {data['name']}")
    print(f"   会话 ID: {data['current_session_id']}")


def cmd_sub_task_reassign(args, *, request: RequestFn) -> None:
    request("post", f"/sub-tasks/{args.id}/reassign", args.key, json={"agent_id": args.agent_id})
    print(f"✅ 已重新分配给 Agent {args.agent_id}")


def register_sub_task_commands(
    subparsers,
    *,
    request: RequestFn,
    print_json: PrintJsonFn,
    extract_items: ExtractItemsFn,
):
    def _bind(handler, **extra_kwargs):
        def _run(args):
            return handler(args, **extra_kwargs)

        return _run

    sub_task_parser = subparsers.add_parser("st", help="子任务管理")
    sub_task_sub = sub_task_parser.add_subparsers(dest="st_cmd")

    parser = sub_task_sub.add_parser("create", help="创建子任务")
    parser.add_argument("task_id", help="任务 ID")
    parser.add_argument("name", help="子任务名称")
    parser.add_argument("--desc", help="描述")
    parser.add_argument("--deliverable", help="交付物")
    parser.add_argument("--acceptance", help="验收标准")
    parser.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
    parser.add_argument("--type", default="once", choices=["once", "recurring"])
    parser.add_argument("--module-id", help="模块 ID")
    parser.add_argument("--assign", help="指派 Agent ID")
    parser.set_defaults(func=_bind(cmd_sub_task_create, request=request, print_json=print_json))

    parser = sub_task_sub.add_parser("list", help="查看子任务列表")
    parser.add_argument("--task-id", help="按任务过滤")
    parser.add_argument("--status", help="按状态过滤")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_sub_task_list, request=request, extract_items=extract_items))

    parser = sub_task_sub.add_parser("get", help="查看子任务详情")
    parser.add_argument("id", help="子任务 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_get, request=request, print_json=print_json))

    parser = sub_task_sub.add_parser("mine", help="查看我的子任务")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_sub_task_mine, request=request, extract_items=extract_items))

    parser = sub_task_sub.add_parser("available", help="查看可认领的子任务")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_sub_task_available, request=request, extract_items=extract_items))

    parser = sub_task_sub.add_parser("latest", help="获取某任务下我的最新子任务")
    parser.add_argument("task_id", help="任务 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_latest, request=request))

    parser = sub_task_sub.add_parser("claim", help="认领子任务")
    parser.add_argument("id", help="子任务 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_claim, request=request))

    parser = sub_task_sub.add_parser("start", help="开始执行")
    parser.add_argument("id", help="子任务 ID")
    parser.add_argument("--session", help="当前 OpenClaw 会话 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_start, request=request))

    parser = sub_task_sub.add_parser("submit", help="提交成果")
    parser.add_argument("id", help="子任务 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_submit, request=request))

    parser = sub_task_sub.add_parser("edit", help="编辑子任务")
    parser.add_argument("id", help="子任务 ID")
    parser.add_argument("--name", help="新名称")
    parser.add_argument("--desc", help="新描述")
    parser.add_argument("--deliverable", help="新交付物")
    parser.add_argument("--acceptance", help="新验收标准")
    parser.add_argument("--priority", choices=["high", "medium", "low"])
    parser.set_defaults(func=_bind(cmd_sub_task_edit, request=request, print_json=print_json))

    parser = sub_task_sub.add_parser("cancel", help="取消子任务")
    parser.add_argument("id", help="子任务 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_cancel, request=request))

    parser = sub_task_sub.add_parser("block", help="标记异常")
    parser.add_argument("id", help="子任务 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_block, request=request))

    parser = sub_task_sub.add_parser("session", help="更新会话 ID")
    parser.add_argument("id", help="子任务 ID")
    parser.add_argument("session_id", help="新的 OpenClaw 会话 ID")
    parser.set_defaults(func=_bind(cmd_sub_task_session, request=request))

    parser = sub_task_sub.add_parser("reassign", help="重新分配")
    parser.add_argument("id", help="子任务 ID")
    parser.add_argument("agent_id", help="新 Agent ID")
    parser.set_defaults(func=_bind(cmd_sub_task_reassign, request=request))

    return sub_task_parser
