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


def get_dashboard_overview(db: Session) -> dict:
    """查询管理端仪表盘 Phase 1 概览统计"""
    now = dt.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    review_window_start = now - timedelta(days=REVIEW_WINDOW_DAYS)

    task_status_distribution = _count_by_column(db, Task.status, TASK_STATUSES)
    sub_task_status_distribution = _count_by_column(db, SubTask.status, SUB_TASK_STATUSES)
    agent_status_distribution = _count_by_column(db, Agent.status, AGENT_STATUSES)
    agent_role_distribution = _count_by_column(db, Agent.role, AGENT_ROLES)
    review_result_distribution = _count_by_column(
        db,
        ReviewRecord.result,
        REVIEW_RESULTS,
        ReviewRecord.created_at >= review_window_start,
    )

    today_completed_sub_task_count = _int_or_zero(
        db.query(func.count(SubTask.id))
        .filter(SubTask.completed_at >= today_start)
        .scalar()
    )

    today_review_row = (
        db.query(
            func.count(ReviewRecord.id).label("today_review_count"),
            func.coalesce(
                func.sum(case((ReviewRecord.result == "rejected", 1), else_=0)),
                0,
            ).label("today_rejected_review_count"),
        )
        .filter(ReviewRecord.created_at >= today_start)
        .first()
    )
    today_review_mapping = today_review_row._mapping
    today_review_count = _int_or_zero(today_review_mapping["today_review_count"])
    today_rejected_review_count = _int_or_zero(today_review_mapping["today_rejected_review_count"])
    today_reject_rate = round(
        (today_rejected_review_count / today_review_count * 100) if today_review_count else 0.0,
        2,
    )

    today_net_score_delta = _int_or_zero(
        db.query(func.coalesce(func.sum(RewardLog.score_delta), 0))
        .filter(RewardLog.created_at >= today_start)
        .scalar()
    )

    return {
        "generated_at": now,
        "review_window_days": REVIEW_WINDOW_DAYS,
        "core_cards": {
            "open_task_count": sum(
                task_status_distribution[status]
                for status in ("planning", "active", "in_progress")
            ),
            "active_sub_task_count": sum(
                sub_task_status_distribution[status]
                for status in ("assigned", "in_progress", "review", "rework", "blocked")
            ),
            "review_queue_count": sub_task_status_distribution["review"],
            "blocked_sub_task_count": sub_task_status_distribution["blocked"],
            "active_agent_count": agent_status_distribution["active"],
            "today_completed_sub_task_count": today_completed_sub_task_count,
        },
        "secondary_cards": {
            "disabled_agent_count": agent_status_distribution["disabled"],
            "today_review_count": today_review_count,
            "today_rejected_review_count": today_rejected_review_count,
            "today_reject_rate": today_reject_rate,
            "today_net_score_delta": today_net_score_delta,
        },
        "distributions": {
            "task_status_distribution": task_status_distribution,
            "sub_task_status_distribution": sub_task_status_distribution,
            "agent_status_distribution": agent_status_distribution,
            "agent_role_distribution": agent_role_distribution,
            "review_result_distribution_7d": review_result_distribution,
        },
    }


def _count_by_column(db: Session, column, allowed_values: tuple[str, ...], *filters) -> dict:
    """按固定枚举字段分组计数，并补齐缺失枚举值"""
    counts = {value: 0 for value in allowed_values}

    query = db.query(column.label("value"), func.count().label("count"))
    if filters:
        query = query.filter(*filters)

    rows = query.group_by(column).all()
    for row in rows:
        if row.value in counts:
            counts[row.value] = _int_or_zero(row.count)

    return counts


def _int_or_zero(value) -> int:
    """把可空聚合值安全转成 int"""
    return int(value or 0)

