"""task 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]
PrintJsonFn = Callable[[Any], None]
ExtractItemsFn = Callable[[Any], list[Any]]


def cmd_task_create(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    data = request(
        "post",
        "/tasks",
        args.key,
        json={"name": args.name, "description": args.desc or "", "type": args.type},
    )
    print(f"✅ 任务已创建: {data['id']}")
    print_json(data)


def cmd_task_list(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if args.status:
        params["status"] = args.status
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", "/tasks", args.key, params=params)
    items = extract_items(data)
    if not items:
        print("暂无任务")
        return
    for task in items:
        print(f"  [{task['status']}] {task['name']} (ID:{task['id']})")


def cmd_task_get(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    data = request("get", f"/tasks/{args.id}", args.key)
    print_json(data)


def cmd_task_edit(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    body = {}
    if args.name:
        body["name"] = args.name
    if args.desc:
        body["description"] = args.desc
    data = request("put", f"/tasks/{args.id}", args.key, json=body)
    print("✅ 任务已更新")
    print_json(data)


def cmd_task_status(args, *, request: RequestFn) -> None:
    data = request("put", f"/tasks/{args.id}/status", args.key, json={"status": args.status})
    print(f"✅ 任务状态已更新: {data['status']}")


def cmd_task_cancel(args, *, request: RequestFn) -> None:
    data = request("post", f"/tasks/{args.id}/cancel", args.key, json={})
    print(f"✅ 任务已取消: {data['id']}")


def register_task_commands(
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

    task_parser = subparsers.add_parser("task", help="任务管理")
    task_sub = task_parser.add_subparsers(dest="task_cmd")

    parser = task_sub.add_parser("create", help="创建任务")
    parser.add_argument("name", help="任务名称")
    parser.add_argument("--desc", help="任务描述")
    parser.add_argument("--type", default="once", choices=["once", "recurring"])
    parser.set_defaults(func=_bind(cmd_task_create, request=request, print_json=print_json))

    parser = task_sub.add_parser("list", help="查看任务列表")
    parser.add_argument("--status", help="按状态过滤")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_task_list, request=request, extract_items=extract_items))

    parser = task_sub.add_parser("get", help="查看任务详情")
    parser.add_argument("id", help="任务 ID")
    parser.set_defaults(func=_bind(cmd_task_get, request=request, print_json=print_json))

    parser = task_sub.add_parser("edit", help="编辑任务")
    parser.add_argument("id", help="任务 ID")
    parser.add_argument("--name", help="新名称")
    parser.add_argument("--desc", help="新描述")
    parser.set_defaults(func=_bind(cmd_task_edit, request=request, print_json=print_json))

    parser = task_sub.add_parser("status", help="更新任务状态")
    parser.add_argument("id", help="任务 ID")
    parser.add_argument("status", help="新状态")
    parser.set_defaults(func=_bind(cmd_task_status, request=request))

    parser = task_sub.add_parser("cancel", help="取消任务")
    parser.add_argument("id", help="任务 ID")
    parser.set_defaults(func=_bind(cmd_task_cancel, request=request))

    return task_parser
