"""
管理端 Agent 查询服务
"""
from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy import asc, case, desc, func
from sqlalchemy.orm import Query, Session

from app.exceptions import (
    AdminInvalidQueryError as InvalidQueryError,
    AdminQueryError as AdminAgentQueryError,
    AdminResourceNotFoundError as ResourceNotFoundError,
)
from app.models.activity_log import ActivityLog
from app.models.agent import Agent
from app.models.request_log import RequestLog
from app.models.reward_log import RewardLog
from app.models.sub_task import SubTask


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
AGENT_ROLES = {"planner", "executor", "reviewer", "patrol"}
AGENT_STATUSES = {"active", "disabled"}
REQUEST_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def _build_agent_workload_stats_subquery(db: Session):
    """按 Agent 聚合子任务工作负载"""
    return (
        db.query(
            SubTask.assigned_agent.label("agent_id"),
            *[
                func.coalesce(
                    func.sum(case((SubTask.status == status, 1), else_=0)),
                    0,
                ).label(f"{status}_count")
                for status in (
                    "assigned",
                    "in_progress",
                    "review",
                    "rework",
                    "blocked",
                    "done",
                    "cancelled",
                )
            ],
        )
        .filter(SubTask.assigned_agent.isnot(None))
        .group_by(SubTask.assigned_agent)
        .subquery()
    )


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


def _build_agent_reward_stats_subquery(db: Session):
    """按 Agent 聚合积分记录统计"""
    return (
        db.query(
            RewardLog.agent_id.label("agent_id"),
            func.coalesce(
                func.sum(case((RewardLog.score_delta > 0, 1), else_=0)),
                0,
            ).label("reward_count"),
            func.coalesce(
                func.sum(case((RewardLog.score_delta < 0, 1), else_=0)),
                0,
            ).label("penalty_count"),
            func.count(RewardLog.id).label("total_reward_records"),
        )
        .group_by(RewardLog.agent_id)
        .subquery()
    )


def _build_agent_rank_subquery(db: Session):
    """计算 Agent 按 total_score 的排名"""
    return (
        db.query(
            Agent.id.label("agent_id"),
            func.dense_rank().over(order_by=Agent.total_score.desc()).label("rank"),
        )
        .subquery()
    )


def _paginate_query(query: Query, page: int, page_size: int, serializer) -> dict:
    """分页执行查询并序列化结果"""
    total = query.order_by(None).count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    total_pages = max(1, (total + page_size - 1) // page_size)
    return {
        "items": [serializer(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


def _serialize_agent_list_row(row) -> dict:
    mapping = row._mapping
    counts = _build_workload_counts(mapping)
    return {
        "id": mapping["id"],
        "name": mapping["name"],
        "role": mapping["role"],
        "description": mapping["description"] or "",
        "status": mapping["status"],
        "total_score": _int_or_zero(mapping["total_score"]),
        "rank": _int_or_zero(mapping["rank"]) or 1,
        **counts,
        "last_request_at": mapping["last_request_at"],
        "last_activity_at": mapping["last_activity_at"],
        "created_at": mapping["created_at"],
    }


def _serialize_agent_detail_row(row, total_agents: int) -> dict:
    mapping = row._mapping
    counts = _build_workload_counts(mapping)
    return {
        "id": mapping["id"],
        "name": mapping["name"],
        "role": mapping["role"],
        "description": mapping["description"] or "",
        "status": mapping["status"],
        "total_score": _int_or_zero(mapping["total_score"]),
        "rank": _int_or_zero(mapping["rank"]) or 1,
        "total_agents": total_agents,
        **counts,
        "done_count": _int_or_zero(mapping["done_count"]),
        "cancelled_count": _int_or_zero(mapping["cancelled_count"]),
        "reward_count": _int_or_zero(mapping["reward_count"]),
        "penalty_count": _int_or_zero(mapping["penalty_count"]),
        "total_reward_records": _int_or_zero(mapping["total_reward_records"]),
        "last_request_at": mapping["last_request_at"],
        "last_activity_at": mapping["last_activity_at"],
        "created_at": mapping["created_at"],
    }


def _build_workload_counts(mapping) -> dict:
    assigned_count = _int_or_zero(mapping["assigned_count"])
    in_progress_count = _int_or_zero(mapping["in_progress_count"])
    review_count = _int_or_zero(mapping["review_count"])
    rework_count = _int_or_zero(mapping["rework_count"])
    blocked_count = _int_or_zero(mapping["blocked_count"])
    return {
        "open_sub_task_count": (
            assigned_count
            + in_progress_count
            + review_count
            + rework_count
            + blocked_count
        ),
        "assigned_count": assigned_count,
        "in_progress_count": in_progress_count,
        "review_count": review_count,
        "rework_count": rework_count,
        "blocked_count": blocked_count,
    }


def _ensure_agent_exists(db: Session, agent_id: str) -> Agent:
    """确保 Agent 存在（返回完整 ORM 对象）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ResourceNotFoundError(f"Agent {agent_id} 不存在")
    return agent


def _ensure_agent_exists_lightweight(db: Session, agent_id: str) -> None:
    """仅检查 Agent 是否存在（只查 id 列，不加载完整对象）"""
    exists = db.query(Agent.id).filter(Agent.id == agent_id).first()
    if not exists:
        raise ResourceNotFoundError(f"Agent {agent_id} 不存在")


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


def _validate_optional_positive_int(field_name: str, value: Optional[int]) -> None:
    """校验可选正整数参数"""
    if value is None:
        return
    if value < 1:
        raise InvalidQueryError(f"{field_name} 必须 >= 1")


def _build_order_clause(sort_by: str, sort_order: str, sort_map: dict):
    """构建排序表达式"""
    if sort_by not in sort_map:
        raise InvalidQueryError(
            f"无效的 sort_by '{sort_by}'，可选: {', '.join(sorted(sort_map.keys()))}"
        )
    if sort_order not in ("asc", "desc"):
        raise InvalidQueryError("sort_order 只能是 asc 或 desc")

    column = sort_map[sort_by]
    return asc(column) if sort_order == "asc" else desc(column)


def _int_or_zero(value) -> int:
    return int(value or 0)
