"""review 命令域。"""

from __future__ import annotations

from typing import Any, Callable


RequestFn = Callable[..., Any]
PrintJsonFn = Callable[[Any], None]
ExtractItemsFn = Callable[[Any], list[Any]]


def cmd_review_create(args, *, request: RequestFn) -> None:
    body = {
        "sub_task_id": args.sub_task_id,
        "result": args.result,
        "score": args.score,
        "comment": args.comment or "",
        "issues": args.issues or "",
    }
    data = request("post", "/review-records", args.key, json=body)
    emoji = "✅" if args.result == "approved" else "❌"
    print(f"{emoji} 审查已提交 (round {data['round']}): {args.result}, 评分 {args.score}/5")


def cmd_review_list(args, *, request: RequestFn, extract_items: ExtractItemsFn) -> None:
    params = {}
    if args.sub_task_id:
        params["sub_task_id"] = args.sub_task_id
    if hasattr(args, "page") and args.page:
        params["page"] = args.page
    if hasattr(args, "page_size") and args.page_size:
        params["page_size"] = args.page_size
    data = request("get", "/review-records", args.key, params=params)
    items = extract_items(data)
    for review in items:
        emoji = "✅" if review["result"] == "approved" else "❌"
        print(f"  {emoji} Round {review['round']}: {review['result']} (评分 {review['score']}/5) {review.get('comment', '')}")


def cmd_review_get(args, *, request: RequestFn, print_json: PrintJsonFn) -> None:
    data = request("get", f"/review-records/{args.id}", args.key)
    print_json(data)


def register_review_commands(
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

    review_parser = subparsers.add_parser("review", help="审查管理")
    review_sub = review_parser.add_subparsers(dest="rev_cmd")

    parser = review_sub.add_parser("create", help="提交审查")
    parser.add_argument("sub_task_id", help="子任务 ID")
    parser.add_argument("result", choices=["approved", "rejected"])
    parser.add_argument("score", type=int, help="评分 1-5")
    parser.add_argument("--comment", help="审查评价")
    parser.add_argument("--issues", help="问题描述（驳回时必填）")
    parser.set_defaults(func=_bind(cmd_review_create, request=request))

    parser = review_sub.add_parser("list", help="查看审查记录")
    parser.add_argument("--sub-task-id", help="按子任务过滤")
    parser.add_argument("--page", type=int, help="页码")
    parser.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    parser.set_defaults(func=_bind(cmd_review_list, request=request, extract_items=extract_items))

    parser = review_sub.add_parser("get", help="查看审查详情")
    parser.add_argument("id", help="审查记录 ID")
    parser.set_defaults(func=_bind(cmd_review_get, request=request, print_json=print_json))

    return review_parser
