"""
活动流查询服务 — 公开展示页数据聚合

从 Router 层下沉的 ORM 查询逻辑，零 HTTP 依赖。
"""
from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.module import Module
from app.models.request_log import RequestLog
from app.models.sub_task import SubTask


def list_feed_logs(
    db: Session,
    *,
    after: Optional[dt] = None,
    agent_id: Optional[str] = None,
    limit: int = 50,
) -> list:
    """获取请求日志列表，可按时间和 Agent 过滤。"""
    query = db.query(RequestLog)
    if after:
        query = query.filter(RequestLog.timestamp > after)
    if agent_id:
        query = query.filter(RequestLog.agent_id == agent_id)
    return query.order_by(RequestLog.timestamp.desc()).limit(limit).all()


def list_feed_agents(db: Session) -> list:
    """获取所有 Agent 列表（按积分降序）。"""
    return db.query(Agent).order_by(Agent.total_score.desc()).all()


def get_feed_agent_summaries(db: Session) -> list[dict]:
    """获取所有 Agent 的汇总面板数据（今日统计、当前任务、近期动作）。"""
    agents = db.query(Agent).order_by(Agent.total_score.desc()).all()
    if not agents:
        return []

    today_start = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
    agent_ids = [a.id for a in agents]

    # 批量查询今日请求数
    today_counts = dict(
        db.query(RequestLog.agent_id, func.count(RequestLog.id))
        .filter(RequestLog.agent_id.in_(agent_ids), RequestLog.timestamp >= today_start)
        .group_by(RequestLog.agent_id)
        .all()
    )

    # 批量查询今日提交数
    today_submits = dict(
        db.query(RequestLog.agent_id, func.count(RequestLog.id))
        .filter(
            RequestLog.agent_id.in_(agent_ids),
            RequestLog.timestamp >= today_start,
            RequestLog.method == "POST",
            RequestLog.path.like("%/submit"),
        )
        .group_by(RequestLog.agent_id)
        .all()
    )

    # 批量查询今日审查数
    today_reviews = dict(
        db.query(RequestLog.agent_id, func.count(RequestLog.id))
        .filter(
            RequestLog.agent_id.in_(agent_ids),
            RequestLog.timestamp >= today_start,
            RequestLog.method == "POST",
            RequestLog.path.like("%/review-records"),
        )
        .group_by(RequestLog.agent_id)
        .all()
    )

    # 批量查询当前 in_progress 子任务
    current_tasks_rows = (
        db.query(SubTask.assigned_agent, SubTask.id, SubTask.name, Module.name.label("module_name"))
        .outerjoin(Module, SubTask.module_id == Module.id)
        .filter(
            SubTask.assigned_agent.in_(agent_ids),
            SubTask.status == "in_progress",
        )
        .order_by(SubTask.updated_at.desc())
        .all()
    )
    current_tasks: dict[str, dict] = {}
    for row in current_tasks_rows:
        if row.assigned_agent not in current_tasks:
            current_tasks[row.assigned_agent] = {
                "id": row.id, "name": row.name, "module_name": row.module_name,
            }

    # 批量查询近期动作（每人最近 5 条）
    recent_logs = (
        db.query(RequestLog)
        .filter(RequestLog.agent_id.in_(agent_ids))
        .order_by(RequestLog.timestamp.desc())
        .limit(len(agent_ids) * 5)
        .all()
    )
    recent_by_agent: dict[str, list[dict]] = {}
    for log in recent_logs:
        agent_list = recent_by_agent.setdefault(log.agent_id, [])
        if len(agent_list) < 5:
            agent_list.append({
                "method": log.method,
                "path": log.path,
                "request_body": log.request_body,
                "response_status": log.response_status,
                "timestamp": log.timestamp,
            })

    # 组装结果
    result = []
    for agent in agents:
        result.append({
            "id": agent.id,
            "name": agent.name,
            "role": agent.role,
            "total_score": agent.total_score,
            "today_request_count": today_counts.get(agent.id, 0),
            "today_submit_count": today_submits.get(agent.id, 0),
            "today_review_count": today_reviews.get(agent.id, 0),
            "current_sub_task": current_tasks.get(agent.id),
            "recent_actions": recent_by_agent.get(agent.id, []),
        })

    return result
