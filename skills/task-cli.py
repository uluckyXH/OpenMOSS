#!/usr/bin/env python3
"""
OpenMOSS 任务调度 CLI 工具
所有角色通用，通过 --key 传入 API Key 认证。

用法：python task-cli.py --key <API_KEY> <命令> [参数]

服务地址在下方 BASE_URL 中配置。
"""
import sys
import json
import argparse
import requests

# ============================================================
# 配置：修改为你的任务调度服务地址
# ============================================================
BASE_URL = "http://192.168.31.128:6565"
CLI_VERSION = 1  # CLI 版本号，更新后递增


# ============================================================
# HTTP 工具
# ============================================================

def _headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _reg_headers(token: str) -> dict:
    return {"X-Registration-Token": token, "Content-Type": "application/json"}


def _admin_headers(token: str) -> dict:
    return {"X-Admin-Token": token, "Content-Type": "application/json"}


def _print_json(data):
    """格式化输出 JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _extract_items(data):
    """从分页响应中提取 items 列表，并打印分页信息"""
    if isinstance(data, dict) and "items" in data:
        total = data.get("total", 0)
        page = data.get("page", 1)
        page_size = data.get("page_size", 0)
        has_more = data.get("has_more", False)
        if page_size > 0:
            print(f"  [第 {page} 页，共 {data.get('total_pages', 1)} 页，{total} 条记录]")
        else:
            print(f"  [共 {total} 条记录]")
        return data["items"]
    # 兼容旧格式（直接返回列表）
    return data if isinstance(data, list) else []


def _request(method, path, key, **kwargs):
    """统一请求封装，自动处理错误"""
    url = f"{BASE_URL}/api{path}"
    headers = _headers(key)
    try:
        r = getattr(requests, method)(url, headers=headers, **kwargs)
        if r.status_code >= 400:
            print(f"❌ 错误 ({r.status_code}): {r.json().get('detail', r.text)}")
            sys.exit(1)
        return r.json()
    except requests.ConnectionError:
        print(f"❌ 无法连接到服务: {BASE_URL}")
        sys.exit(1)


# ============================================================
# 注册命令（不需要 key）
# ============================================================

def cmd_register(args):
    """注册 Agent"""
    r = requests.post(
        f"{BASE_URL}/api/agents/register",
        headers=_reg_headers(args.token),
        json={"name": args.name, "role": args.role, "description": args.description or ""},
    )
    if r.status_code >= 400:
        print(f"❌ 注册失败: {r.json().get('detail', r.text)}")
        sys.exit(1)
    data = r.json()
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
# 团队 (Agent 端)
# ============================================================

def cmd_team_mine(args):
    """查看所属团队信息"""
    data = _request("get", "/teams/me", args.key)
    print(f"  团队ID: {data['id']}")
    print(f"  团队名称: {data['name']}")
    print(f"  描述: {data['description'] or '-'}")
    print(f"  状态: {data['status']}")


def cmd_team_profile(args):
    """获取团队介绍"""
    data = _request("get", "/teams/me/profile", args.key)
    print(f"  版本: {data['version']}")
    if data.get('content'):
        print("\n--- 团队介绍 ---")
        print(data['content'])
    else:
        print("  (团队介绍尚未生成)")


def cmd_team_intro(args):
    """提交自我介绍"""
    data = _request("put", "/teams/me/intro", args.key, json={"self_introduction": args.content})
    print(f"✅ 自我介绍已更新")


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
    if hasattr(args, 'team_id') and args.team_id:
        params["team_id"] = args.team_id
    data = _request("get", "/tasks", args.key, params=params)
    items = _extract_items(data)
    if not items:
        print("暂无任务")
        return
    for t in items:
        team_info = f" [团队:{t.get('team_id', '-')}]" if t.get('team_id') else ""
        print(f"  [{t['status']}] {t['name']} (ID:{t['id']}){team_info}")


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
    if hasattr(args, 'type') and args.type:
        body["type"] = args.type
    if hasattr(args, 'remarks') and args.remarks:
        body["remarks"] = args.remarks
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
        print(f"  [{a['status']}] {a['name']} ({a['role']}) 积分:{a['total_score']}{desc}")


# ============================================================
# 自更新
# ============================================================

def cmd_update(args):
    """自动更新 task-cli.py 和 SKILL.md"""
    import pathlib

    headers = _headers(args.key)

    # 下载最新 CLI
    print("⬇️  下载最新 task-cli.py ...")
    try:
        r = requests.get(f"{BASE_URL}/api/tools/cli", headers=headers)
        if r.status_code == 200:
            cli_path = pathlib.Path(__file__).resolve()
            cli_path.write_text(r.text, encoding="utf-8")
            print("✅ task-cli.py 已更新")
        else:
            print(f"❌ 下载失败 ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"❌ 下载失败: {e}")

    # 下载最新 SKILL.md
    print("⬇️  下载最新 SKILL.md ...")
    try:
        r = requests.get(f"{BASE_URL}/api/agents/me/skill", headers=headers)
        if r.status_code == 200:
            skill_path = pathlib.Path(__file__).resolve().parent / "SKILL.md"
            skill_path.write_text(r.text, encoding="utf-8")
            print("✅ SKILL.md 已更新（API Key 已自动填入）")
        else:
            print(f"❌ 下载失败 ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"❌ 下载失败: {e}")


# ============================================================
# 主入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="OpenMOSS 任务调度 CLI 工具",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--key", help="API Key（注册后获取）")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # --- register ---
    p = subparsers.add_parser("register", help="注册 Agent")
    p.add_argument("--name", required=True, help="Agent 名称")
    p.add_argument("--role", required=True, choices=["planner", "executor", "reviewer", "patrol"])
    p.add_argument("--token", required=True, help="注册令牌")
    p.add_argument("--description", help="职责描述")
    p.set_defaults(func=cmd_register)

    # --- team (Agent 端团队接口) ---
    team_p = subparsers.add_parser("team", help="团队管理(Agent端)")
    team_sub = team_p.add_subparsers(dest="team_cmd")

    p = team_sub.add_parser("mine", help="查看所属团队信息")
    p.set_defaults(func=cmd_team_mine)

    p = team_sub.add_parser("profile", help="获取团队介绍")
    p.set_defaults(func=cmd_team_profile)

    p = team_sub.add_parser("intro", help="提交自我介绍")
    p.add_argument("content", help="自我介绍内容")
    p.set_defaults(func=cmd_team_intro)

    # --- rules ---
    p = subparsers.add_parser("rules", help="获取规则提示词")
    p.set_defaults(func=cmd_rules)

    # --- update ---
    p = subparsers.add_parser("update", help="自动更新 CLI 工具和 SKILL.md")
    p.set_defaults(func=cmd_update)

    # --- task ---
    task_p = subparsers.add_parser("task", help="任务管理")
    task_sub = task_p.add_subparsers(dest="task_cmd")

    p = task_sub.add_parser("create", help="创建任务")
    p.add_argument("name", help="任务名称")
    p.add_argument("--desc", help="任务描述")
    p.add_argument("--type", default="once", choices=["once", "recurring"])
    p.set_defaults(func=cmd_task_create)

    p = task_sub.add_parser("list", help="查看任务列表")
    p.add_argument("--status", help="按状态过滤")
    p.add_argument("--team-id", help="按团队ID筛选")
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
    score_p = subparsers.add_parser("score", help="积分管理")
    score_sub = score_p.add_subparsers(dest="score_cmd")

    p = score_sub.add_parser("me", help="查看我的积分")
    p.set_defaults(func=cmd_score_me)

    p = score_sub.add_parser("logs", help="查看积分明细")
    p.add_argument("--page", type=int, help="页码")
    p.add_argument("--page-size", type=int, help="每页条数（0=全部）")
    p.set_defaults(func=cmd_score_logs)

    p = score_sub.add_parser("leaderboard", help="积分排行榜")
    p.set_defaults(func=cmd_score_leaderboard)

    p = score_sub.add_parser("adjust", help="手动调整 Agent 积分（仅 reviewer/planner）")
    p.add_argument("agent_id", help="目标 Agent ID")
    p.add_argument("delta", type=int, help="积分变化量（正数加分，负数扣分）")
    p.add_argument("reason", help="调整原因")
    p.add_argument("--sub-task-id", help="关联子任务 ID（可选）")
    p.set_defaults(func=cmd_score_adjust)

    # --- log ---
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
    p = subparsers.add_parser("notification", help="查看通知配置")
    p.set_defaults(func=cmd_notification)

    # --- agents ---
    p = subparsers.add_parser("agents", help="查看 Agent 列表")
    p.add_argument("--role", help="按角色过滤")
    p.set_defaults(func=cmd_agent_list)

    # 解析
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    # register 不需要 key
    if args.command == "register":
        args.func(args)
        return

    # 其他命令需要 key
    if not args.key:
        print("❌ 缺少 --key 参数，请提供 API Key")
        sys.exit(1)

    if hasattr(args, "func"):
        args.func(args)
    else:
        # 子命令未指定时显示帮助
        if args.command == "task":
            task_p.print_help()
        elif args.command == "st":
            st_p.print_help()
        elif args.command == "review":
            rev_p.print_help()
        elif args.command == "score":
            score_p.print_help()
        elif args.command == "log":
            log_p.print_help()
        elif args.command == "module":
            mod_p.print_help()


if __name__ == "__main__":
    main()
