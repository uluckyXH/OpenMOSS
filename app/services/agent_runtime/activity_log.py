"""
活动日志业务逻辑 — Agent 写日志 + 查询日志

从 Router 层下沉的 ORM 操作，零 HTTP 依赖。
"""
import uuid
from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog


# 日志 action 白名单
VALID_ACTIONS = {
    "coding",       # Executor: 执行过程记录
    "delivery",     # Executor: 提交交付物摘要
    "blocked",      # Executor: 遇到阻塞求助
    "reflection",   # 所有角色: 自省笔记
    "plan",         # Planner: 规划/分配记录
    "review",       # Reviewer: 审查过程记录
    "patrol",       # Patrol: 巡查记录
}

MAX_DAYS = 60
DEFAULT_DAYS = 7
DEFAULT_LIMIT = 20
MAX_LIMIT = 500


def validate_action(action: str) -> None:
    """校验 action 是否在白名单内，不合法则抛异常。"""
    from app.exceptions import ValidationError
    if action not in VALID_ACTIONS:
        raise ValidationError(
            f"无效的 action '{action}'，允许: {', '.join(sorted(VALID_ACTIONS))}"
        )


def create_activity_log(
    db: Session,
    agent_id: str,
    action: str,
    summary: str = "",
    sub_task_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> ActivityLog:
    """写入一条活动日志。"""
    validate_action(action)

    log = ActivityLog(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        sub_task_id=sub_task_id,
        action=action,
        summary=summary,
        session_id=session_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def _apply_days_filter(query, days: Optional[int]):
    """按天数过滤日志。"""
    if days is not None:
        days = min(max(days, 1), MAX_DAYS)
        cutoff = dt.now() - timedelta(days=days)
        query = query.filter(ActivityLog.created_at >= cutoff)
    return query


def list_activity_logs(
    db: Session,
    *,
    sub_task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    action: Optional[str] = None,
    days: Optional[int] = DEFAULT_DAYS,
    limit: Optional[int] = DEFAULT_LIMIT,
) -> list:
    """查看活动日志，支持多条件过滤。"""
    query = db.query(ActivityLog)
    if sub_task_id:
        query = query.filter(ActivityLog.sub_task_id == sub_task_id)
    if agent_id:
        query = query.filter(ActivityLog.agent_id == agent_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    query = _apply_days_filter(query, days)
    actual_limit = min(max(limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    return query.order_by(ActivityLog.created_at.desc()).limit(actual_limit).all()


def list_my_activity_logs(
    db: Session,
    agent_id: str,
    *,
    action: Optional[str] = None,
    days: Optional[int] = DEFAULT_DAYS,
    limit: Optional[int] = DEFAULT_LIMIT,
) -> list:
    """查看指定 Agent 自己的活动日志。"""
    query = db.query(ActivityLog).filter(ActivityLog.agent_id == agent_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    query = _apply_days_filter(query, days)
    actual_limit = min(max(limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    return query.order_by(ActivityLog.created_at.desc()).limit(actual_limit).all()
