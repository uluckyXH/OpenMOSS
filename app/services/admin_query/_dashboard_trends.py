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


def get_dashboard_trends(db: Session, days: int = DEFAULT_TREND_DAYS) -> dict:
    """查询管理端仪表盘 Phase 3 趋势统计"""
    actual_days = max(1, min(days, MAX_TREND_DAYS))
    start_dt, end_dt, dates = _build_trend_window(actual_days)

    return {
        "generated_at": dt.now(),
        "days": actual_days,
        "start_date": dates[0].isoformat(),
        "end_date": dates[-1].isoformat(),
        "sub_task_created_trend": _build_count_trend(
            dates,
            _query_count_trend_rows(db, SubTask.id, SubTask.created_at, start_dt, end_dt),
        ),
        "sub_task_completed_trend": _build_count_trend(
            dates,
            _query_count_trend_rows(db, SubTask.id, SubTask.completed_at, start_dt, end_dt),
        ),
        "review_trend": _build_review_trend(
            dates,
            _query_review_trend_rows(db, start_dt, end_dt),
        ),
        "score_delta_trend": _build_score_trend(
            dates,
            _query_score_trend_rows(db, start_dt, end_dt),
        ),
        "request_trend": _build_count_trend(
            dates,
            _query_count_trend_rows(db, RequestLog.id, RequestLog.timestamp, start_dt, end_dt),
        ),
        "activity_trend": _build_count_trend(
            dates,
            _query_count_trend_rows(db, ActivityLog.id, ActivityLog.created_at, start_dt, end_dt),
        ),
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


def _build_trend_window(days: int) -> tuple[dt, dt, list[date]]:
    """构建趋势时间窗口和连续日期桶"""
    today = dt.now().date()
    start_date = today - timedelta(days=days - 1)
    dates = [start_date + timedelta(days=index) for index in range(days)]
    start_dt = dt.combine(start_date, dt.min.time())
    end_dt = dt.combine(today + timedelta(days=1), dt.min.time())
    return start_dt, end_dt, dates


def _query_count_trend_rows(db: Session, id_column, datetime_column, start_dt: dt, end_dt: dt):
    """按日期查询单指标数量趋势"""
    return (
        db.query(
            func.date(datetime_column).label("day"),
            func.count(id_column).label("count"),
        )
        .filter(datetime_column.isnot(None), datetime_column >= start_dt, datetime_column < end_dt)
        .group_by(func.date(datetime_column))
        .all()
    )


def _query_review_trend_rows(db: Session, start_dt: dt, end_dt: dt):
    """按日期查询审查趋势"""
    return (
        db.query(
            func.date(ReviewRecord.created_at).label("day"),
            func.count(ReviewRecord.id).label("total"),
            func.coalesce(
                func.sum(case((ReviewRecord.result == "approved", 1), else_=0)),
                0,
            ).label("approved"),
            func.coalesce(
                func.sum(case((ReviewRecord.result == "rejected", 1), else_=0)),
                0,
            ).label("rejected"),
        )
        .filter(ReviewRecord.created_at >= start_dt, ReviewRecord.created_at < end_dt)
        .group_by(func.date(ReviewRecord.created_at))
        .all()
    )


def _query_score_trend_rows(db: Session, start_dt: dt, end_dt: dt):
    """按日期查询积分变化趋势"""
    return (
        db.query(
            func.date(RewardLog.created_at).label("day"),
            func.coalesce(
                func.sum(case((RewardLog.score_delta > 0, RewardLog.score_delta), else_=0)),
                0,
            ).label("positive_score_delta"),
            func.coalesce(
                func.sum(case((RewardLog.score_delta < 0, RewardLog.score_delta), else_=0)),
                0,
            ).label("negative_score_delta"),
            func.coalesce(func.sum(RewardLog.score_delta), 0).label("net_score_delta"),
        )
        .filter(RewardLog.created_at >= start_dt, RewardLog.created_at < end_dt)
        .group_by(func.date(RewardLog.created_at))
        .all()
    )


def _build_count_trend(dates: list[date], rows) -> list[dict]:
    """把查询行补成连续计数趋势"""
    row_map = {str(row.day): _int_or_zero(row.count) for row in rows}
    return [
        {
            "date": day.isoformat(),
            "count": row_map.get(day.isoformat(), 0),
        }
        for day in dates
    ]


def _build_review_trend(dates: list[date], rows) -> list[dict]:
    """把查询行补成连续审查趋势"""
    row_map = {
        str(row.day): {
            "total": _int_or_zero(row.total),
            "approved": _int_or_zero(row.approved),
            "rejected": _int_or_zero(row.rejected),
        }
        for row in rows
    }
    return [
        {
            "date": day.isoformat(),
            "total": row_map.get(day.isoformat(), {}).get("total", 0),
            "approved": row_map.get(day.isoformat(), {}).get("approved", 0),
            "rejected": row_map.get(day.isoformat(), {}).get("rejected", 0),
        }
        for day in dates
    ]


def _build_score_trend(dates: list[date], rows) -> list[dict]:
    """把查询行补成连续积分趋势"""
    row_map = {
        str(row.day): {
            "positive_score_delta": _int_or_zero(row.positive_score_delta),
            "negative_score_delta": _int_or_zero(row.negative_score_delta),
            "net_score_delta": _int_or_zero(row.net_score_delta),
        }
        for row in rows
    }
    return [
        {
            "date": day.isoformat(),
            "positive_score_delta": row_map.get(day.isoformat(), {}).get("positive_score_delta", 0),
            "negative_score_delta": row_map.get(day.isoformat(), {}).get("negative_score_delta", 0),
            "net_score_delta": row_map.get(day.isoformat(), {}).get("net_score_delta", 0),
        }
        for day in dates
    ]


