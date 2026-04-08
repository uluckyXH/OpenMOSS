#!/usr/bin/env python3
"""
OpenMOSS 任务调度 CLI 工具
所有角色通用，通过 --key 传入 API Key 认证。

用法：python task-cli.py --key <API_KEY> <命令> [参数]

服务地址在下方 BASE_URL 中配置。
"""
import sys
from types import SimpleNamespace

try:
    from tools.task_cli.app import CliAppContext, run_cli
    from tools.task_cli.commands import (
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
    from tools.task_cli.main import (
        build_root_parser,
        finalize_runtime_key,
        print_group_help,
        render_command_help_text,
        render_profile_help_text,
    )
    from tools.task_cli.profiles import resolve_profile_name
    from tools.task_cli.http import (
        build_agent_headers,
        build_registration_headers,
        request_bytes,
        request_json,
        request_text,
    )
    from tools.task_cli.output import extract_items, print_json
    from tools.task_cli.runtime import (
        ROLE_CHOICES,
        build_runtime_config,
        resolve_api_key,
    )
except ImportError:
    import json
    import argparse
    import shutil
    import tempfile
    from urllib import error, parse, request
    import zipfile

    CliAppContext = None
    run_cli = None
    register_agent_commands = None
    register_module_commands = None
    register_notification_commands = None
    register_review_commands = None
    register_score_commands = None
    register_log_commands = None
    register_rules_commands = None
    register_task_commands = None
    register_sub_task_commands = None
    render_command_help_text = None
    render_profile_help_text = None

    def build_agent_headers(key):
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    def build_registration_headers(token):
        return {"X-Registration-Token": token, "Content-Type": "application/json"}

    def request_text(method, *, base_url, path, headers, params=None, json_body=None):
        url = f"{base_url}/api{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with request.urlopen(req) as resp:
                return resp.status, resp.read().decode("utf-8")
        except error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        except error.URLError:
            raise ConnectionError(url) from None

    def request_bytes(method, *, base_url, path, headers, params=None, json_body=None):
        url = f"{base_url}/api{path}"
        if params:
            url = f"{url}?{parse.urlencode(params)}"
        data = None
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
        req = request.Request(url, data=data, headers=headers, method=method.upper())
        try:
            with request.urlopen(req) as resp:
                return resp.status, resp.read()
        except error.HTTPError as exc:
            return exc.code, exc.read()
        except error.URLError:
            raise ConnectionError(url) from None

    def request_json(method, *, base_url, path, headers, params=None, json_body=None):
        try:
            status_code, text = request_text(
                method,
                base_url=base_url,
                path=path,
                headers=headers,
                params=params,
                json_body=json_body,
            )
        except ConnectionError:
            print(f"❌ 无法连接到服务: {base_url}")
            sys.exit(1)

        if status_code >= 400:
            try:
                detail = json.loads(text).get("detail", text)
            except json.JSONDecodeError:
                detail = text
            print(f"❌ 错误 ({status_code}): {detail}")
            sys.exit(1)

        return json.loads(text)

    def build_root_parser(*, default_api_key=None):
        parser = argparse.ArgumentParser(
            description="OpenMOSS 任务调度 CLI 工具",
            formatter_class=argparse.RawTextHelpFormatter,
        )
        parser.add_argument("--key", default=default_api_key, help="API Key（注册后获取，可由专属 task-cli.py 预置）")
        subparsers = parser.add_subparsers(dest="command", help="可用命令")
        return parser, subparsers

    def extract_items(data):
        if isinstance(data, dict) and "items" in data:
            total = data.get("total", 0)
            page = data.get("page", 1)
            page_size = data.get("page_size", 0)
            if page_size > 0:
                print(f"  [第 {page} 页，共 {data.get('total_pages', 1)} 页，{total} 条记录]")
            else:
                print(f"  [共 {total} 条记录]")
            return data["items"]
        return data if isinstance(data, list) else []

    def print_json(data):
        print(json.dumps(data, ensure_ascii=False, indent=2))

    def finalize_runtime_key(args, runtime):
        args.key = resolve_api_key(getattr(args, "key", None), runtime)

    def print_group_help(args, *, parser, help_map, group_help_renderer=None):
        if hasattr(args, "func"):
            args.func(args)
            return
        if group_help_renderer is not None:
            rendered = group_help_renderer(getattr(args, "command", ""))
            if rendered:
                print(rendered)
                return
        group_parser = help_map.get(getattr(args, "command", ""))
        if group_parser is not None:
            group_parser.print_help()
            return
        parser.print_help()

    def resolve_profile_name(cli_profile, agent_role):
        return cli_profile or agent_role

    ROLE_CHOICES = ("planner", "executor", "reviewer", "patrol")

    def build_runtime_config(
        *,
        default_base_url,
        default_cli_version,
        default_api_key=None,
        agent_id=None,
        agent_name=None,
        agent_role=None,
        cli_profile=None,
    ):
        return SimpleNamespace(
            base_url=default_base_url,
            cli_version=default_cli_version,
            default_api_key=default_api_key,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_role=agent_role,
            cli_profile=cli_profile,
        )

    def resolve_api_key(cli_key, runtime):
        return cli_key or runtime.default_api_key

# ============================================================
# 配置：修改为你的任务调度服务地址
# ============================================================
RUNTIME = build_runtime_config(
    default_base_url="http://192.168.31.128:6565",
    default_cli_version=2,
)
BASE_URL = RUNTIME.base_url
CLI_VERSION = RUNTIME.cli_version  # CLI 版本号，更新后递增
DEFAULT_API_KEY = RUNTIME.default_api_key
AGENT_ID = RUNTIME.agent_id
AGENT_NAME = RUNTIME.agent_name
AGENT_ROLE = RUNTIME.agent_role
CLI_PROFILE = RUNTIME.cli_profile
ACTIVE_PROFILE = resolve_profile_name(CLI_PROFILE, AGENT_ROLE)


def _headers(key: str) -> dict:
    return build_agent_headers(key)


def _reg_headers(token: str) -> dict:
    return build_registration_headers(token)


def _print_json(data):
    print_json(data)


def _extract_items(data):
    return extract_items(data)


def _request(method, path, key, **kwargs):
    json_body = kwargs.pop("json", None)
    params = kwargs.pop("params", None)
    return request_json(
        method,
        base_url=BASE_URL,
        path=path,
        headers=build_agent_headers(key),
        params=params,
        json_body=json_body,
    )


# ============================================================
# 注册命令（不需要 key）
# ============================================================

def cmd_register(args):
    """注册 Agent"""
    data = request_json(
        "post",
        base_url=BASE_URL,
        path="/agents/register",
        headers=_reg_headers(args.token),
        json_body={"name": args.name, "role": args.role, "description": args.description or ""},
    )
    print(f"✅ 注册成功")
    print(f"   Agent ID:  {data['id']}")
    print(f"   API Key:   {data['api_key']}")
    print(f"   角色:      {data['role']}")
    print(f"\n⚠️  请立即将 API Key 保存到你的 SKILL.md 中！")


# ============================================================
# 规则
# ============================================================

def cmd_rules(args):
    """获取规则"""
    data = _request("get", "/rules", args.key, params={"cli_version": CLI_VERSION})
    print(data.get("content", ""))
    if data.get("update_available"):
        print(f"\n⚠️ 工具更新可用 (v{CLI_VERSION} → v{data.get('latest_version', '?')})")
        if data.get("update_instructions"):
            print(data["update_instructions"])


# ============================================================
# 任务
# ============================================================

def cmd_task_create(args):
    """创建任务"""
    data = _request("post", "/tasks", args.key,
                    json={"name": args.name, "description": args.desc or "", "type": args.type})
    print(f"✅ 任务已创建: {data['id']}")
    _print_json(data)


def cmd_task_list(args):
    """查看任务列表"""
    params = {}
    if args.status:
        params["status"] = args.status
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", "/tasks", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("暂无任务")
        return
    for t in items:
        print(f"  [{t['status']}] {t['name']} (ID:{t['id']})")


def cmd_task_get(args):
    """查看任务详情"""
    data = _request("get", f"/tasks/{args.id}", args.key)
    _print_json(data)


def cmd_task_edit(args):
    """编辑任务"""
    body = {}
    if args.name:
        body["name"] = args.name
    if args.desc:
        body["description"] = args.desc
    data = _request("put", f"/tasks/{args.id}", args.key, json=body)
    print(f"✅ 任务已更新")
    _print_json(data)


def cmd_task_status(args):
    """更新任务状态"""
    data = _request("put", f"/tasks/{args.id}/status", args.key, json={"status": args.status})
    print(f"✅ 任务状态已更新: {data['status']}")


def cmd_task_cancel(args):
    """取消任务"""
    data = _request("post", f"/tasks/{args.id}/cancel", args.key, json={})
    print(f"✅ 任务已取消: {data['id']}")


# ============================================================
# 模块
# ============================================================

def cmd_module_create(args):
    """创建模块"""
    data = _request("post", f"/tasks/{args.task_id}/modules", args.key,
                    json={"name": args.name, "description": args.desc or ""})
    print(f"✅ 模块已创建: {data['id']}")


def cmd_module_list(args):
    """查看模块列表"""
    data = _request("get", f"/tasks/{args.task_id}/modules", args.key)
    for m in data:
        print(f"  {m['name']} (ID:{m['id']})")


# ============================================================
# 子任务
# ============================================================

def cmd_sub_task_create(args):
    """创建子任务"""
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
    data = _request("post", "/sub-tasks", args.key, json=body)
    print(f"✅ 子任务已创建: {data['id']}")
    _print_json(data)


def cmd_sub_task_list(args):
    """查看子任务列表"""
    params = {}
    if args.task_id:
        params["task_id"] = args.task_id
    if args.status:
        params["status"] = args.status
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", "/sub-tasks", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("暂无子任务")
        return
    for st in items:
        agent = st.get("assigned_agent") or "-"
        print(f"  [{st['status']}] {st['name']} (ID:{st['id']} Agent:{agent})")


def cmd_sub_task_get(args):
    """查看子任务详情"""
    data = _request("get", f"/sub-tasks/{args.id}", args.key)
    _print_json(data)


def cmd_sub_task_mine(args):
    """查看我的子任务"""
    params = {}
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", "/sub-tasks/mine", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("暂无分配给你的子任务")
        return
    for st in items:
        print(f"  [{st['status']}] {st['name']} (ID:{st['id']})")


def cmd_sub_task_available(args):
    """查看可认领的子任务"""
    params = {}
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", "/sub-tasks/available", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("暂无可认领的子任务")
        return
    for st in items:
        print(f"  [{st['priority']}] {st['name']} (ID:{st['id']})")

def cmd_sub_task_latest(args):
    """获取某任务下分配给我的最新子任务"""
    data = _request("get", "/sub-tasks/latest", args.key, params={"task_id": args.task_id})
    if data:
        print(f"  [{data['status']}] {data['name']}")
        print(f"  ID: {data['id']}")
        if data.get('description'):
            print(f"  描述: {data['description']}")
        if data.get('deliverable'):
            print(f"  交付物: {data['deliverable']}")
        if data.get('acceptance'):
            print(f"  验收标准: {data['acceptance']}")


def cmd_sub_task_claim(args):
    """认领子任务"""
    data = _request("post", f"/sub-tasks/{args.id}/claim", args.key, json={})
    print(f"✅ 已认领: {data['name']}")


def cmd_sub_task_start(args):
    """开始执行"""
    body = {}
    if hasattr(args, 'session') and args.session:
        body["session_id"] = args.session
    data = _request("post", f"/sub-tasks/{args.id}/start", args.key, json=body)
    print(f"✅ 已开始: {data['name']}")
    if data.get('current_session_id'):
        print(f"   会话: {data['current_session_id']}")


def cmd_sub_task_submit(args):
    """提交成果"""
    data = _request("post", f"/sub-tasks/{args.id}/submit", args.key)
    print(f"✅ 已提交: {data['name']}，等待审查")


def cmd_sub_task_edit(args):
    """编辑子任务"""
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
    data = _request("put", f"/sub-tasks/{args.id}", args.key, json=body)
    print(f"✅ 子任务已更新")
    _print_json(data)


def cmd_sub_task_cancel(args):
    """取消子任务"""
    data = _request("post", f"/sub-tasks/{args.id}/cancel", args.key, json={})
    print(f"✅ 子任务已取消: {data['id']}")


def cmd_sub_task_block(args):
    """标记子任务异常"""
    data = _request("post", f"/sub-tasks/{args.id}/block", args.key, json={})
    print(f"⚠️ 已标记 blocked: {data['name']}")


def cmd_sub_task_session(args):
    """更新子任务的会话 ID"""
    data = _request("post", f"/sub-tasks/{args.id}/session", args.key,
                     json={"session_id": args.session_id})
    print(f"✅ 会话已更新: {data['name']}")
    print(f"   会话 ID: {data['current_session_id']}")


def cmd_sub_task_reassign(args):
    """重新分配子任务"""
    data = _request("post", f"/sub-tasks/{args.id}/reassign", args.key,
                    json={"agent_id": args.agent_id})
    print(f"✅ 已重新分配给 Agent {args.agent_id}")


# ============================================================
# 审查记录
# ============================================================

def cmd_review_create(args):
    """提交审查记录"""
    body = {
        "sub_task_id": args.sub_task_id,
        "result": args.result,
        "score": args.score,
        "comment": args.comment or "",
        "issues": args.issues or "",
    }
    data = _request("post", "/review-records", args.key, json=body)
    emoji = "✅" if args.result == "approved" else "❌"
    print(f"{emoji} 审查已提交 (round {data['round']}): {args.result}, 评分 {args.score}/5")


def cmd_review_list(args):
    """查看审查记录"""
    params = {}
    if args.sub_task_id:
        params["sub_task_id"] = args.sub_task_id
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", "/review-records", args.key, params=params)
    items = _extract_items(data)
    for r in items:
        emoji = "✅" if r["result"] == "approved" else "❌"
        print(f"  {emoji} Round {r['round']}: {r['result']} (评分 {r['score']}/5) {r.get('comment', '')}")


def cmd_review_get(args):
    """查看单条审查详情"""
    data = _request("get", f"/review-records/{args.id}", args.key)
    _print_json(data)


# ============================================================
# 积分
# ============================================================

def cmd_score_me(args):
    """查看我的积分"""
    data = _request("get", "/scores/me", args.key)
    print(f"  Agent: {data['agent_name']}")
    print(f"  总积分: {data['total_score']}")
    print(f"  加分次数: {data['reward_count']}  扣分次数: {data['penalty_count']}")


def cmd_score_logs(args):
    """查看积分明细"""
    params = {}
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", "/scores/me/logs", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("暂无积分记录")
        return
    for log in items:
        sign = "+" if log["score_delta"] > 0 else ""
        print(f"  {sign}{log['score_delta']}  {log['reason']}")


def cmd_score_agent_logs(args):
    """查看指定 Agent 的积分明细"""
    params = {}
    if hasattr(args, 'page') and args.page:
        params["page"] = args.page
    if hasattr(args, 'page_size') and args.page_size:
        params["page_size"] = args.page_size
    data = _request("get", f"/scores/{args.agent_id}/logs", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("该 Agent 暂无积分记录")
        return
    for log in items:
        sign = "+" if log["score_delta"] > 0 else ""
        print(f"  {sign}{log['score_delta']}  {log['reason']}")


def cmd_score_leaderboard(args):
    """积分排行榜"""
    data = _request("get", "/scores/leaderboard", args.key)
    for item in data:
        print(f"  #{item['rank']} {item['agent_name']} ({item['role']}): {item['total_score']}分")


def cmd_score_adjust(args):
    """手动调整 Agent 积分"""
    body = {
        "agent_id": args.agent_id,
        "score_delta": args.delta,
        "reason": args.reason,
    }
    if args.sub_task_id:
        body["sub_task_id"] = args.sub_task_id
    data = _request("post", "/scores/adjust", args.key, json=body)
    sign = "+" if data["score_delta"] > 0 else ""
    print(f"✅ 积分已调整: {sign}{data['score_delta']}  原因: {data['reason']}")


# ============================================================
# 活动日志
# ============================================================

def cmd_log_create(args):
    """写入活动日志"""
    body = {"action": args.action, "summary": args.summary}
    if args.sub_task_id:
        body["sub_task_id"] = args.sub_task_id
    data = _request("post", "/logs", args.key, json=body)
    print(f"✅ 日志已写入: {data['action']}")


def cmd_log_mine(args):
    """查看我的活动日志"""
    params = {}
    if args.action:
        params["action"] = args.action
    if args.days:
        params["days"] = args.days
    if args.limit:
        params["limit"] = args.limit
    data = _request("get", "/logs/mine", args.key, params=params)
    if not data:
        print("暂无日志记录")
        return
    for log in data:
        print(f"  [{log['action']}] {log['summary']}")


def cmd_log_list(args):
    """查看活动日志（可查看所有 Agent 的日志）"""
    params = {}
    if args.sub_task_id:
        params["sub_task_id"] = args.sub_task_id
    if args.action:
        params["action"] = args.action
    if args.days:
        params["days"] = args.days
    if args.limit:
        params["limit"] = args.limit
    data = _request("get", "/logs", args.key, params=params)
    if not data:
        print("暂无日志记录")
        return
    for log in data:
        print(f"  [{log['action']}] {log['summary']}")


# ============================================================
# 通知配置
# ============================================================

def cmd_notification(args):
    """查看通知配置"""
    data = _request("get", "/config/notification", args.key)  # → /api/config/notification
    print(f"  启用: {data['enabled']}")
    print(f"  渠道: {', '.join(data['channels']) if data['channels'] else '未配置'}")
    print(f"  事件: {', '.join(data['events']) if data['events'] else '未配置'}")


# ============================================================
# Agent 查询
# ============================================================

def cmd_agent_list(args):
    """查看 Agent 列表"""
    params = {}
    if args.role:
        params["role"] = args.role
    data = _request("get", "/agents", args.key, params=params)
    for a in data:
        desc = f" — {a['description']}" if a.get('description') else ""
        print(f"  [{a['status']}] {a['name']} ({a['role']}) ID:{a['id']} 积分:{a['total_score']}{desc}")


# ============================================================
# 自更新
# ============================================================

def cmd_update(args):
    """自动更新当前 Skill Bundle。"""
    import pathlib
    import runpy

    headers = _headers(args.key)
    cli_path = pathlib.Path(__file__).resolve()

    if cli_path.parent.name == "scripts" and (cli_path.parent.parent / "SKILL.md").exists():
        layout = "bundle"
        skill_root = cli_path.parent.parent
    else:
        layout = "legacy"
        skill_root = cli_path.parent

    def _extract_bundle_root(temp_dir):
        roots = [path for path in temp_dir.iterdir() if path.is_dir()]
        if len(roots) != 1:
            raise RuntimeError("skill-bundle 结构无效，无法定位根目录")
        return roots[0]

    def _apply_bundle(bundle_bytes):
        with tempfile.TemporaryDirectory(prefix="openmoss-skill-bundle-") as tmp_dir:
            tmp_root = pathlib.Path(tmp_dir)
            bundle_path = tmp_root / "bundle.zip"
            bundle_path.write_bytes(bundle_bytes)
            extract_dir = tmp_root / "extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(bundle_path, "r") as zip_file:
                zip_file.extractall(extract_dir)

            source_root = _extract_bundle_root(extract_dir)
            shutil.rmtree(skill_root / "references", ignore_errors=True)
            shutil.rmtree(skill_root / "scripts" / "task_cli", ignore_errors=True)
            skill_root.mkdir(parents=True, exist_ok=True)
            for path in sorted(source_root.rglob("*")):
                rel_path = path.relative_to(source_root)
                dest = skill_root / rel_path
                if path.is_dir():
                    dest.mkdir(parents=True, exist_ok=True)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, dest)

        if layout == "legacy":
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

    print("⬇️  下载最新 Skill Bundle ...")
    try:
        status_code, content = request_bytes(
            "get",
            base_url=BASE_URL,
            path="/agents/me/skill-bundle",
            headers=headers,
        )
        if status_code == 200:
            _apply_bundle(content)
            print("✅ Skill Bundle 已更新")
            print(f"   目录: {skill_root}")
            if layout == "legacy":
                print("ℹ️  旧版单文件目录已迁移到 Skill Bundle 结构，标准入口为 scripts/task-cli.py")
            return
        print(f"❌ 下载失败 ({status_code}): {content.decode('utf-8', errors='replace')[:200]}")
    except Exception as e:
        print(f"❌ 下载失败: {e}")


def cmd_help(args):
    if render_profile_help_text is None:
        print("当前分发版本暂不支持 Profile help")
        return

    if args.topic:
        text = render_command_help_text(args.topic, ACTIVE_PROFILE)
        if text is None:
            print(f"❌ 未知命令组: {args.topic}")
            return
        print(text)
        return

    print(render_profile_help_text(ACTIVE_PROFILE))

    # 下载最新 SKILL.md
    print("⬇️  下载最新 SKILL.md ...")
    try:
        status_code, text = request_text(
            "get",
            base_url=BASE_URL,
            path="/agents/me/skill",
            headers=headers,
        )
        if status_code == 200:
            skill_path = pathlib.Path(__file__).resolve().parent / "SKILL.md"
            skill_path.write_text(text, encoding="utf-8")
            print("✅ SKILL.md 已更新（API Key 已自动填入）")
        else:
            print(f"❌ 下载失败 ({status_code}): {text[:200]}")
    except Exception as e:
        print(f"❌ 下载失败: {e}")


# ============================================================
# 主入口
# ============================================================

def _legacy_main():
    parser, subparsers = build_root_parser(default_api_key=DEFAULT_API_KEY)

    # --- register ---
    p = subparsers.add_parser("register", help="注册 Agent")
    p.add_argument("--name", required=True, help="Agent 名称")
    p.add_argument("--role", required=True, choices=ROLE_CHOICES)
    p.add_argument("--token", required=True, help="注册令牌")
    p.add_argument("--description", help="职责描述")
    p.set_defaults(func=cmd_register)

    # --- rules ---
    if register_rules_commands is not None:
        register_rules_commands(subparsers, request=_request, cli_version=CLI_VERSION)
    else:
        p = subparsers.add_parser("rules", help="获取规则提示词")
        p.set_defaults(func=cmd_rules)

    # --- update ---
    p = subparsers.add_parser("update", help="自动更新 CLI 工具和 SKILL.md")
    p.set_defaults(func=cmd_update)

    # --- help ---
    p = subparsers.add_parser("help", help="按当前 Profile 查看可用命令")
    p.add_argument("topic", nargs="?", help="查看某个命令组的帮助")
    p.set_defaults(func=cmd_help)

    # --- task ---
    if register_task_commands is not None:
        task_p = register_task_commands(
            subparsers,
            request=_request,
            print_json=_print_json,
            extract_items=_extract_items,
        )
    else:
        task_p = subparsers.add_parser("task", help="任务管理")
        task_sub = task_p.add_subparsers(dest="task_cmd")

        p = task_sub.add_parser("create", help="创建任务")
        p.add_argument("name", help="任务名称")
        p.add_argument("--desc", help="任务描述")
        p.add_argument("--type", default="once", choices=["once", "recurring"])
        p.set_defaults(func=cmd_task_create)

        p = task_sub.add_parser("list", help="查看任务列表")
        p.add_argument("--status", help="按状态过滤")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_task_list)

        p = task_sub.add_parser("get", help="查看任务详情")
        p.add_argument("id", help="任务 ID")
        p.set_defaults(func=cmd_task_get)

        p = task_sub.add_parser("edit", help="编辑任务")
        p.add_argument("id", help="任务 ID")
        p.add_argument("--name", help="新名称")
        p.add_argument("--desc", help="新描述")
        p.set_defaults(func=cmd_task_edit)

        p = task_sub.add_parser("status", help="更新任务状态")
        p.add_argument("id", help="任务 ID")
        p.add_argument("status", help="新状态")
        p.set_defaults(func=cmd_task_status)

        p = task_sub.add_parser("cancel", help="取消任务")
        p.add_argument("id", help="任务 ID")
        p.set_defaults(func=cmd_task_cancel)

    # --- module ---
    if register_module_commands is not None:
        mod_p = register_module_commands(subparsers, request=_request)
    else:
        mod_p = subparsers.add_parser("module", help="模块管理")
        mod_sub = mod_p.add_subparsers(dest="mod_cmd")

        p = mod_sub.add_parser("create", help="创建模块")
        p.add_argument("task_id", help="任务 ID")
        p.add_argument("name", help="模块名称")
        p.add_argument("--desc", help="模块描述")
        p.set_defaults(func=cmd_module_create)

        p = mod_sub.add_parser("list", help="查看模块列表")
        p.add_argument("task_id", help="任务 ID")
        p.set_defaults(func=cmd_module_list)

    # --- sub-task ---
    if register_sub_task_commands is not None:
        st_p = register_sub_task_commands(
            subparsers,
            request=_request,
            print_json=_print_json,
            extract_items=_extract_items,
        )
    else:
        st_p = subparsers.add_parser("st", help="子任务管理")
        st_sub = st_p.add_subparsers(dest="st_cmd")

        p = st_sub.add_parser("create", help="创建子任务")
        p.add_argument("task_id", help="任务 ID")
        p.add_argument("name", help="子任务名称")
        p.add_argument("--desc", help="描述")
        p.add_argument("--deliverable", help="交付物")
        p.add_argument("--acceptance", help="验收标准")
        p.add_argument("--priority", default="medium", choices=["high", "medium", "low"])
        p.add_argument("--type", default="once", choices=["once", "recurring"])
        p.add_argument("--module-id", help="模块 ID")
        p.add_argument("--assign", help="指派 Agent ID")
        p.set_defaults(func=cmd_sub_task_create)

        p = st_sub.add_parser("list", help="查看子任务列表")
        p.add_argument("--task-id", help="按任务过滤")
        p.add_argument("--status", help="按状态过滤")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_sub_task_list)

        p = st_sub.add_parser("get", help="查看子任务详情")
        p.add_argument("id", help="子任务 ID")
        p.set_defaults(func=cmd_sub_task_get)

        p = st_sub.add_parser("mine", help="查看我的子任务")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_sub_task_mine)

        p = st_sub.add_parser("available", help="查看可认领的子任务")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_sub_task_available)

        p = st_sub.add_parser("latest", help="获取某任务下我的最新子任务")
        p.add_argument("task_id", help="任务 ID")
        p.set_defaults(func=cmd_sub_task_latest)

        p = st_sub.add_parser("claim", help="认领子任务")
        p.add_argument("id", help="子任务 ID")
        p.set_defaults(func=cmd_sub_task_claim)

        p = st_sub.add_parser("start", help="开始执行")
        p.add_argument("id", help="子任务 ID")
        p.add_argument("--session", help="当前 OpenClaw 会话 ID")
        p.set_defaults(func=cmd_sub_task_start)

        p = st_sub.add_parser("submit", help="提交成果")
        p.add_argument("id", help="子任务 ID")
        p.set_defaults(func=cmd_sub_task_submit)

        p = st_sub.add_parser("edit", help="编辑子任务")
        p.add_argument("id", help="子任务 ID")
        p.add_argument("--name", help="新名称")
        p.add_argument("--desc", help="新描述")
        p.add_argument("--deliverable", help="新交付物")
        p.add_argument("--acceptance", help="新验收标准")
        p.add_argument("--priority", choices=["high", "medium", "low"])
        p.set_defaults(func=cmd_sub_task_edit)

        p = st_sub.add_parser("cancel", help="取消子任务")
        p.add_argument("id", help="子任务 ID")
        p.set_defaults(func=cmd_sub_task_cancel)

        p = st_sub.add_parser("block", help="标记异常")
        p.add_argument("id", help="子任务 ID")
        p.set_defaults(func=cmd_sub_task_block)

        p = st_sub.add_parser("session", help="更新会话 ID")
        p.add_argument("id", help="子任务 ID")
        p.add_argument("session_id", help="新的 OpenClaw 会话 ID")
        p.set_defaults(func=cmd_sub_task_session)

        p = st_sub.add_parser("reassign", help="重新分配")
        p.add_argument("id", help="子任务 ID")
        p.add_argument("agent_id", help="新 Agent ID")
        p.set_defaults(func=cmd_sub_task_reassign)

    # --- review ---
    if register_review_commands is not None:
        rev_p = register_review_commands(
            subparsers,
            request=_request,
            print_json=_print_json,
            extract_items=_extract_items,
        )
    else:
        rev_p = subparsers.add_parser("review", help="审查管理")
        rev_sub = rev_p.add_subparsers(dest="rev_cmd")

        p = rev_sub.add_parser("create", help="提交审查")
        p.add_argument("sub_task_id", help="子任务 ID")
        p.add_argument("result", choices=["approved", "rejected"])
        p.add_argument("score", type=int, help="评分 1-5")
        p.add_argument("--comment", help="审查评价")
        p.add_argument("--issues", help="问题描述（驳回时必填）")
        p.set_defaults(func=cmd_review_create)

        p = rev_sub.add_parser("list", help="查看审查记录")
        p.add_argument("--sub-task-id", help="按子任务过滤")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_review_list)

        p = rev_sub.add_parser("get", help="查看审查详情")
        p.add_argument("id", help="审查记录 ID")
        p.set_defaults(func=cmd_review_get)

    # --- score ---
    if register_score_commands is not None:
        score_p = register_score_commands(
            subparsers,
            request=_request,
            extract_items=_extract_items,
        )
    else:
        score_p = subparsers.add_parser("score", help="积分管理")
        score_sub = score_p.add_subparsers(dest="score_cmd")

        p = score_sub.add_parser("me", help="查看我的积分")
        p.set_defaults(func=cmd_score_me)

        p = score_sub.add_parser("logs", help="查看积分明细")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_score_logs)

        p = score_sub.add_parser("agent-logs", help="查看指定 Agent 的积分明细")
        p.add_argument("agent_id", help="目标 Agent ID")
        p.add_argument("--page", type=int, help="页码")
        p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
        p.set_defaults(func=cmd_score_agent_logs)

        p = score_sub.add_parser("leaderboard", help="积分排行榜")
        p.set_defaults(func=cmd_score_leaderboard)

        p = score_sub.add_parser("adjust", help="手动调整 Agent 积分（仅 reviewer/planner）")
        p.add_argument("agent_id", help="目标 Agent ID")
        p.add_argument("delta", type=int, help="积分变化量（正数加分，负数扣分）")
        p.add_argument("reason", help="调整原因")
        p.add_argument("--sub-task-id", help="关联子任务 ID（可选）")
        p.set_defaults(func=cmd_score_adjust)

    # --- log ---
    if register_log_commands is not None:
        log_p = register_log_commands(subparsers, request=_request)
    else:
        log_p = subparsers.add_parser("log", help="活动日志")
        log_sub = log_p.add_subparsers(dest="log_cmd")

        p = log_sub.add_parser("create", help="写入日志")
        p.add_argument("action", help="操作类型")
        p.add_argument("summary", help="操作摘要")
        p.add_argument("--sub-task-id", help="关联子任务 ID")
        p.set_defaults(func=cmd_log_create)

        p = log_sub.add_parser("mine", help="查看我的日志")
        p.add_argument("--action", help="按操作类型过滤（如 reflection）")
        p.add_argument("--days", type=int, help="最近N天（默认7，最大60）")
        p.add_argument("--limit", type=int, help="返回条数（默认20，最大500）")
        p.set_defaults(func=cmd_log_mine)

        p = log_sub.add_parser("list", help="查看活动日志（含其他 Agent）")
        p.add_argument("--sub-task-id", help="按子任务 ID 过滤")
        p.add_argument("--action", help="按操作类型过滤")
        p.add_argument("--days", type=int, help="最近N天（默认7，最大60）")
        p.add_argument("--limit", type=int, help="返回条数（默认20，最大100）")
        p.set_defaults(func=cmd_log_list)

    # --- notification ---
    if register_notification_commands is not None:
        register_notification_commands(subparsers, request=_request)
    else:
        p = subparsers.add_parser("notification", help="查看通知配置")
        p.set_defaults(func=cmd_notification)

    # --- agents ---
    if register_agent_commands is not None:
        register_agent_commands(subparsers, request=_request)
    else:
        p = subparsers.add_parser("agents", help="查看 Agent 列表")
        p.add_argument("--role", help="按角色过滤")
        p.set_defaults(func=cmd_agent_list)

    # 解析
    args = parser.parse_args()
    if not args.command:
        if render_profile_help_text is not None:
            print(render_profile_help_text(ACTIVE_PROFILE))
        else:
            parser.print_help()
        sys.exit(0)

    # register 不需要 key
    if args.command in {"register", "help"}:
        args.func(args)
        return

    # 其他命令需要 key
    finalize_runtime_key(args, RUNTIME)

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
        group_help_renderer=(
            (lambda command_name: render_command_help_text(command_name, ACTIVE_PROFILE))
            if render_command_help_text is not None
            else None
        ),
    )


def main():
    if run_cli is not None and CliAppContext is not None:
        ctx = CliAppContext(
            base_url=BASE_URL,
            cli_version=CLI_VERSION,
            default_api_key=DEFAULT_API_KEY,
            agent_id=AGENT_ID,
            agent_name=AGENT_NAME,
            agent_role=AGENT_ROLE,
            cli_profile=CLI_PROFILE,
            role_choices=ROLE_CHOICES,
            request=_request,
            request_json=request_json,
            request_text=request_text,
            request_bytes=request_bytes,
            build_agent_headers=build_agent_headers,
            build_registration_headers=build_registration_headers,
            print_json=print_json,
            extract_items=extract_items,
        )
        return run_cli(ctx, argv=sys.argv[1:], script_path=__file__)
    return _legacy_main()


if __name__ == "__main__":
    main()
