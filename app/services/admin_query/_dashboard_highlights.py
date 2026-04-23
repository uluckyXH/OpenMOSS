"""
管理端仪表盘查询服务
"""
from datetime import date, datetime as dt, timedelta

from sqlalchemy import asc, case, desc, func, or_
from sqlalchemy.orm import Session, aliased

from app.models.activity_log import ActivityLog
from app.models.agent import Agent
from app.models.request_log import RequestLog
from app.models.review_record import ReviewRecord
from app.models.reward_log import RewardLog
from app.models.sub_task import SubTask
from app.models.task import Task


TASK_STATUSES = ("planning", "active", "in_progress", "completed", "archived", "cancelled")
SUB_TASK_STATUSES = ("pending", "assigned", "in_progress", "review", "rework", "blocked", "done", "cancelled")
AGENT_STATUSES = ("active", "disabled")
AGENT_ROLES = ("planner", "executor", "reviewer", "patrol")
REVIEW_RESULTS = ("approved", "rejected")
REVIEW_WINDOW_DAYS = 7
OPEN_SUB_TASK_STATUSES = ("assigned", "in_progress", "review", "rework", "blocked")
DEFAULT_TREND_DAYS = 7
MAX_TREND_DAYS = 30


def get_dashboard_highlights(
    db: Session,
    limit: int = 5,
    inactive_hours: int = 24,
) -> dict:
    """查询管理端仪表盘 Phase 2 高亮面板"""
    now = dt.now()
    inactive_cutoff = now - timedelta(hours=inactive_hours)

    request_stats = _build_agent_last_request_subquery(db)
    activity_stats = _build_agent_last_activity_subquery(db)
    workload_stats = _build_agent_open_workload_subquery(db)
    last_seen_expr = _build_agent_last_seen_expr(
        request_stats.c.last_request_at,
        activity_stats.c.last_activity_at,
    )

    return {
        "generated_at": now,
        "limit": limit,
        "inactive_hours": inactive_hours,
        "blocked_sub_tasks": _list_sub_task_highlights(db, "blocked", limit),
        "pending_review_sub_tasks": _list_sub_task_highlights(db, "review", limit),
        "busy_agents": _list_busy_agents(db, limit, workload_stats, request_stats, activity_stats),
        "low_activity_agents": _list_low_activity_agents(
            db,
            limit,
            inactive_cutoff,
            workload_stats,
            request_stats,
            activity_stats,
            last_seen_expr,
        ),
        "recent_reviews": _list_recent_reviews(db, limit),
    }


def _build_agent_last_request_subquery(db: Session):
    """按 Agent 聚合最近请求时间"""
    return (
        db.query(
            RequestLog.agent_id.label("agent_id"),
            func.max(RequestLog.timestamp).label("last_request_at"),
        )
        .filter(RequestLog.agent_id.isnot(None))
        .group_by(RequestLog.agent_id)
        .subquery()
    )


def _build_agent_last_activity_subquery(db: Session):
    """按 Agent 聚合最近活动时间"""
    return (
        db.query(
            ActivityLog.agent_id.label("agent_id"),
            func.max(ActivityLog.created_at).label("last_activity_at"),
        )
        .filter(ActivityLog.agent_id.isnot(None))
        .group_by(ActivityLog.agent_id)
        .subquery()
    )


def _build_agent_open_workload_subquery(db: Session):
    """按 Agent 聚合开放子任务数量"""
    return (
        db.query(
            SubTask.assigned_agent.label("agent_id"),
            func.coalesce(
                func.sum(case((SubTask.status.in_(OPEN_SUB_TASK_STATUSES), 1), else_=0)),
                0,
            ).label("open_sub_task_count"),
        )
        .filter(SubTask.assigned_agent.isnot(None))
        .group_by(SubTask.assigned_agent)
        .subquery()
    )


def _build_agent_last_seen_expr(last_request_col, last_activity_col):
    """组合最近请求和最近活动时间，得到 Agent 的最近活跃时间"""
    return case(
        (last_request_col.is_(None), last_activity_col),
        (last_activity_col.is_(None), last_request_col),
        (last_request_col >= last_activity_col, last_request_col),
        else_=last_activity_col,
    )


def _list_sub_task_highlights(db: Session, status: str, limit: int) -> list[dict]:
    """查询 blocked/review 高亮子任务"""
    assigned_agent = aliased(Agent)
    rows = (
        db.query(
            SubTask.id.label("id"),
            Task.id.label("task_id"),
            Task.name.label("task_name"),
            SubTask.name.label("name"),
            SubTask.status.label("status"),
            SubTask.assigned_agent.label("assigned_agent"),
            assigned_agent.name.label("assigned_agent_name"),
            SubTask.updated_at.label("updated_at"),
            SubTask.rework_count.label("rework_count"),
        )
        .join(Task, Task.id == SubTask.task_id)
        .outerjoin(assigned_agent, assigned_agent.id == SubTask.assigned_agent)
        .filter(SubTask.status == status)
        .order_by(desc(SubTask.updated_at), desc(SubTask.id))
        .limit(limit)
        .all()
    )
    return [_serialize_sub_task_highlight_row(row) for row in rows]


def _list_busy_agents(db: Session, limit: int, workload_stats, request_stats, activity_stats) -> list[dict]:
    """查询当前最忙的 Agent 列表"""
    open_count = func.coalesce(workload_stats.c.open_sub_task_count, 0)
    disabled_last = case((Agent.status == "disabled", 1), else_=0)

    rows = (
        db.query(
            Agent.id.label("id"),
            Agent.name.label("name"),
            Agent.role.label("role"),
            Agent.status.label("status"),
            Agent.total_score.label("total_score"),
            open_count.label("open_sub_task_count"),
            request_stats.c.last_request_at.label("last_request_at"),
            activity_stats.c.last_activity_at.label("last_activity_at"),
        )
        .outerjoin(workload_stats, workload_stats.c.agent_id == Agent.id)
        .outerjoin(request_stats, request_stats.c.agent_id == Agent.id)
        .outerjoin(activity_stats, activity_stats.c.agent_id == Agent.id)
        .filter(open_count > 0)
        .order_by(
            desc(open_count),
            asc(disabled_last),
            desc(request_stats.c.last_request_at),
            desc(activity_stats.c.last_activity_at),
            asc(Agent.created_at),
        )
        .limit(limit)
        .all()
    )
    return [_serialize_agent_highlight_row(row) for row in rows]


def _list_low_activity_agents(
    db: Session,
    limit: int,
    inactive_cutoff: dt,
    workload_stats,
    request_stats,
    activity_stats,
    last_seen_expr,
) -> list[dict]:
    """查询长时间不活跃的 Agent 列表"""
    no_activity_first = case((last_seen_expr.is_(None), 0), else_=1)

    rows = (
        db.query(
            Agent.id.label("id"),
            Agent.name.label("name"),
            Agent.role.label("role"),
            Agent.status.label("status"),
            Agent.total_score.label("total_score"),
            func.coalesce(workload_stats.c.open_sub_task_count, 0).label("open_sub_task_count"),
            request_stats.c.last_request_at.label("last_request_at"),
            activity_stats.c.last_activity_at.label("last_activity_at"),
        )
        .outerjoin(workload_stats, workload_stats.c.agent_id == Agent.id)
        .outerjoin(request_stats, request_stats.c.agent_id == Agent.id)
        .outerjoin(activity_stats, activity_stats.c.agent_id == Agent.id)
        .filter(or_(last_seen_expr.is_(None), last_seen_expr < inactive_cutoff))
        .order_by(
            asc(no_activity_first),
            asc(last_seen_expr),
            asc(Agent.created_at),
        )
        .limit(limit)
        .all()
    )
    return [_serialize_agent_highlight_row(row) for row in rows]


def _list_recent_reviews(db: Session, limit: int) -> list[dict]:
    """查询最近审查记录"""
    reviewer_agent = aliased(Agent)
    rows = (
        db.query(
            ReviewRecord.id.label("id"),
            Task.id.label("task_id"),
            Task.name.label("task_name"),
            ReviewRecord.sub_task_id.label("sub_task_id"),
            SubTask.name.label("sub_task_name"),
            ReviewRecord.reviewer_agent.label("reviewer_agent"),
            reviewer_agent.name.label("reviewer_agent_name"),
            ReviewRecord.result.label("result"),
            ReviewRecord.score.label("score"),
            ReviewRecord.created_at.label("created_at"),
        )
        .join(SubTask, SubTask.id == ReviewRecord.sub_task_id)
        .join(Task, Task.id == SubTask.task_id)
        .outerjoin(reviewer_agent, reviewer_agent.id == ReviewRecord.reviewer_agent)
        .order_by(desc(ReviewRecord.created_at), desc(ReviewRecord.id))
        .limit(limit)
        .all()
    )
    return [_serialize_recent_review_row(row) for row in rows]


def _serialize_sub_task_highlight_row(row) -> dict:
    """序列化高亮子任务列表项"""
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "task_id": mapping["task_id"],
        "task_name": mapping["task_name"],
        "name": mapping["name"],
        "status": mapping["status"],
        "assigned_agent": mapping["assigned_agent"],
        "assigned_agent_name": mapping["assigned_agent_name"],
        "updated_at": mapping["updated_at"],
        "rework_count": _int_or_zero(mapping["rework_count"]),
    }


def _serialize_agent_highlight_row(row) -> dict:
    """序列化高亮 Agent 列表项"""
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "name": mapping["name"],
        "role": mapping["role"],
        "status": mapping["status"],
        "total_score": _int_or_zero(mapping["total_score"]),
        "open_sub_task_count": _int_or_zero(mapping["open_sub_task_count"]),
        "last_request_at": mapping["last_request_at"],
        "last_activity_at": mapping["last_activity_at"],
    }


def _serialize_recent_review_row(row) -> dict:
    """序列化最近审查列表项"""
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "task_id": mapping["task_id"],
        "task_name": mapping["task_name"],
        "sub_task_id": mapping["sub_task_id"],
        "sub_task_name": mapping["sub_task_name"],
        "reviewer_agent": mapping["reviewer_agent"],
        "reviewer_agent_name": mapping["reviewer_agent_name"],
        "result": mapping["result"],
        "score": _int_or_zero(mapping["score"]),
        "created_at": mapping["created_at"],
    }


def _int_or_zero(value) -> int:
    return int(value or 0)
