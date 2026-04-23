"""
管理端活动日志查询服务
"""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Query, Session

from app.exceptions import (
    AdminInvalidQueryError as InvalidQueryError,
    AdminQueryError as AdminLogQueryError,
)
from app.models.activity_log import ActivityLog
from app.models.agent import Agent


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_DAYS = 60

VALID_ACTIONS = {
    "coding", "delivery", "blocked", "reflection",
    "plan", "review", "patrol",
}


def list_activity_logs(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    agent_id: Optional[str] = None,
    action: Optional[str] = None,
    sub_task_id: Optional[str] = None,
    keyword: Optional[str] = None,
    days: Optional[int] = None,
    sort_order: str = "desc",
) -> dict:
    """分页查询管理端全局活动日志"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("action", action, VALID_ACTIONS)
    _validate_sort_order(sort_order)

    # 计算总数
    count_query = _apply_filters(
        db.query(func.count(ActivityLog.id)),
        agent_id=agent_id,
        action=action,
        sub_task_id=sub_task_id,
        keyword=keyword,
        days=days,
    )
    total = int(count_query.scalar() or 0)

    # 查询数据（JOIN agents 表获取 agent_name 和 agent_role）
    query = (
        db.query(
            ActivityLog.id.label("id"),
            ActivityLog.agent_id.label("agent_id"),
            Agent.name.label("agent_name"),
            Agent.role.label("agent_role"),
            ActivityLog.sub_task_id.label("sub_task_id"),
            ActivityLog.action.label("action"),
            ActivityLog.summary.label("summary"),
            ActivityLog.session_id.label("session_id"),
            ActivityLog.created_at.label("created_at"),
        )
        .join(Agent, Agent.id == ActivityLog.agent_id)
    )
    query = _apply_filters(
        query,
        agent_id=agent_id,
        action=action,
        sub_task_id=sub_task_id,
        keyword=keyword,
        days=days,
    )

    created_at_order = desc(ActivityLog.created_at) if sort_order == "desc" else asc(ActivityLog.created_at)
    id_order = desc(ActivityLog.id) if sort_order == "desc" else asc(ActivityLog.id)
    query = query.order_by(created_at_order, id_order)

    return _paginate_query(query, total, page, page_size)


# ============================================================
# 内部工具函数
# ============================================================

def _apply_filters(
    query: Query,
    agent_id: Optional[str] = None,
    action: Optional[str] = None,
    sub_task_id: Optional[str] = None,
    keyword: Optional[str] = None,
    days: Optional[int] = None,
) -> Query:
    """统一应用过滤条件"""
    if agent_id:
        query = query.filter(ActivityLog.agent_id == agent_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    if sub_task_id:
        query = query.filter(ActivityLog.sub_task_id == sub_task_id)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(ActivityLog.summary.ilike(pattern))
    if days is not None:
        actual_days = min(max(days, 1), MAX_DAYS)
        cutoff = datetime.now() - timedelta(days=actual_days)
        query = query.filter(ActivityLog.created_at >= cutoff)
    return query


def _paginate_query(query: Query, total: int, page: int, page_size: int) -> dict:
    """分页执行查询并序列化结果"""
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [_serialize_row(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


def _serialize_row(row) -> dict:
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "agent_id": mapping["agent_id"],
        "agent_name": mapping["agent_name"],
        "agent_role": mapping["agent_role"],
        "sub_task_id": mapping["sub_task_id"],
        "action": mapping["action"],
        "summary": mapping["summary"],
        "session_id": mapping["session_id"],
        "created_at": mapping["created_at"],
    }


def _validate_page_args(page: int, page_size: int) -> None:
    """校验分页参数"""
    if page < 1:
        raise InvalidQueryError("page 必须 >= 1")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise InvalidQueryError(f"page_size 必须在 1-{MAX_PAGE_SIZE} 之间")


def _validate_optional_enum(field_name: str, value: Optional[str], allowed_values: set[str]) -> None:
    """校验可选枚举参数"""
    if value is None:
        return
    if value not in allowed_values:
        raise InvalidQueryError(
            f"无效的 {field_name} '{value}'，可选: {', '.join(sorted(allowed_values))}"
        )


def _validate_sort_order(sort_order: str) -> None:
    """校验排序方向"""
    if sort_order not in ("asc", "desc"):
        raise InvalidQueryError("sort_order 只能是 asc 或 desc")
