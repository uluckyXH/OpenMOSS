"""管理端 Agent 日志查询实现。"""

from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.request_log import RequestLog
from app.models.reward_log import RewardLog

from ._agent_common import (
    DEFAULT_PAGE_SIZE,
    REQUEST_METHODS,
    InvalidQueryError,
    _build_order_clause,
    _ensure_agent_exists_lightweight,
    _int_or_zero,
    _paginate_query,
    _validate_optional_enum,
    _validate_optional_positive_int,
    _validate_page_args,
)


def list_agent_score_logs(
    db: Session,
    agent_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sub_task_id: Optional[str] = None,
    sort_order: str = "desc",
) -> dict:
    """分页查询 Agent 积分明细"""
    _validate_page_args(page, page_size)
    _ensure_agent_exists_lightweight(db, agent_id)

    query = db.query(
        RewardLog.id.label("id"),
        RewardLog.agent_id.label("agent_id"),
        RewardLog.sub_task_id.label("sub_task_id"),
        RewardLog.reason.label("reason"),
        RewardLog.score_delta.label("score_delta"),
        RewardLog.created_at.label("created_at"),
    ).filter(RewardLog.agent_id == agent_id)

    if sub_task_id:
        query = query.filter(RewardLog.sub_task_id == sub_task_id)

    order_clause = _build_order_clause(
        "created_at",
        sort_order,
        {"created_at": RewardLog.created_at},
    )
    query = query.order_by(order_clause, RewardLog.id.asc())

    return _paginate_query(query, page, page_size, _serialize_score_log_row)


def list_agent_activity_logs(
    db: Session,
    agent_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    action: Optional[str] = None,
    days: Optional[int] = None,
    sub_task_id: Optional[str] = None,
) -> dict:
    """分页查询 Agent 活动日志"""
    _validate_page_args(page, page_size)
    _ensure_agent_exists_lightweight(db, agent_id)
    if days is not None and days < 1:
        raise InvalidQueryError("days 必须 >= 1")

    query = db.query(
        ActivityLog.id.label("id"),
        ActivityLog.agent_id.label("agent_id"),
        ActivityLog.sub_task_id.label("sub_task_id"),
        ActivityLog.action.label("action"),
        ActivityLog.summary.label("summary"),
        ActivityLog.session_id.label("session_id"),
        ActivityLog.created_at.label("created_at"),
    ).filter(ActivityLog.agent_id == agent_id)

    if action:
        query = query.filter(ActivityLog.action == action)
    if sub_task_id:
        query = query.filter(ActivityLog.sub_task_id == sub_task_id)
    if days is not None:
        cutoff = dt.now() - timedelta(days=days)
        query = query.filter(ActivityLog.created_at >= cutoff)

    query = query.order_by(ActivityLog.created_at.desc(), ActivityLog.id.asc())

    return _paginate_query(query, page, page_size, _serialize_activity_log_row)


def list_agent_request_logs(
    db: Session,
    agent_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    days: Optional[int] = None,
    method: Optional[str] = None,
    path_keyword: Optional[str] = None,
) -> dict:
    """分页查询 Agent 请求日志"""
    _validate_page_args(page, page_size)
    _ensure_agent_exists_lightweight(db, agent_id)
    _validate_optional_positive_int("days", days)

    normalized_method = method.strip().upper() if method and method.strip() else None
    _validate_optional_enum("method", normalized_method, REQUEST_METHODS)

    query = db.query(
        RequestLog.id.label("id"),
        RequestLog.timestamp.label("timestamp"),
        RequestLog.method.label("method"),
        RequestLog.path.label("path"),
        RequestLog.response_status.label("response_status"),
        RequestLog.request_body.label("request_body"),
    ).filter(RequestLog.agent_id == agent_id)

    if days is not None:
        cutoff = dt.now() - timedelta(days=days)
        query = query.filter(RequestLog.timestamp >= cutoff)
    if normalized_method:
        query = query.filter(RequestLog.method == normalized_method)
    if path_keyword and path_keyword.strip():
        query = query.filter(RequestLog.path.ilike(f"%{path_keyword.strip()}%"))

    query = query.order_by(RequestLog.timestamp.desc(), RequestLog.id.asc())

    return _paginate_query(query, page, page_size, _serialize_request_log_row)


def _serialize_score_log_row(row) -> dict:
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "agent_id": mapping["agent_id"],
        "sub_task_id": mapping["sub_task_id"],
        "reason": mapping["reason"],
        "score_delta": _int_or_zero(mapping["score_delta"]),
        "created_at": mapping["created_at"],
    }


def _serialize_activity_log_row(row) -> dict:
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "agent_id": mapping["agent_id"],
        "sub_task_id": mapping["sub_task_id"],
        "action": mapping["action"],
        "summary": mapping["summary"] or "",
        "session_id": mapping["session_id"],
        "created_at": mapping["created_at"],
    }


def _serialize_request_log_row(row) -> dict:
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "timestamp": mapping["timestamp"],
        "method": mapping["method"],
        "path": mapping["path"],
        "response_status": mapping["response_status"],
        "request_body": mapping["request_body"],
    }


__all__ = [
    "list_agent_activity_logs",
    "list_agent_request_logs",
    "list_agent_score_logs",
]

