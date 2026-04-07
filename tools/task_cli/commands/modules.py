"""module 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]


def cmd_module_create(args, *, request: RequestFn) -> None:
    data = request(
        "post",
        f"/tasks/{args.task_id}/modules",
        args.key,
        json={"name": args.name, "description": args.desc or ""},
    )
    print(f"✅ 模块已创建: {data['id']}")


def cmd_module_list(args, *, request: RequestFn) -> None:
    data = request("get", f"/tasks/{args.task_id}/modules", args.key)
    for module in data:
        print(f"  {module['name']} (ID:{module['id']})")


def register_module_commands(subparsers, *, request: RequestFn):
    def _bind(handler, **extra_kwargs):
        def _run(args):
            return handler(args, **extra_kwargs)

        return _run

    module_parser = subparsers.add_parser("module", help="模块管理")
    module_sub = module_parser.add_subparsers(dest="mod_cmd")

    parser = module_sub.add_parser("create", help="创建模块")
    parser.add_argument("task_id", help="任务 ID")
    parser.add_argument("name", help="模块名称")
    parser.add_argument("--desc", help="模块描述")
    parser.set_defaults(func=_bind(cmd_module_create, request=request))

    parser = module_sub.add_parser("list", help="查看模块列表")
    parser.add_argument("task_id", help="任务 ID")
    parser.set_defaults(func=_bind(cmd_module_list, request=request))

    return module_parser
