"""管理端 Agent 概览查询实现。"""

from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.agent import Agent

from ._agent_common import (
    AGENT_ROLES,
    AGENT_STATUSES,
    DEFAULT_PAGE_SIZE,
    ResourceNotFoundError,
    _build_agent_last_activity_subquery,
    _build_agent_last_request_subquery,
    _build_agent_rank_subquery,
    _build_agent_reward_stats_subquery,
    _build_agent_workload_stats_subquery,
    _build_order_clause,
    _serialize_agent_detail_row,
    _serialize_agent_list_row,
    _validate_optional_enum,
    _validate_optional_positive_int,
    _validate_page_args,
)


def list_agents(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    role: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    last_request_within_days: Optional[int] = None,
    last_activity_within_days: Optional[int] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询管理端 Agent 列表"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("role", role, AGENT_ROLES)
    _validate_optional_enum("status", status, AGENT_STATUSES)
    _validate_optional_positive_int("last_request_within_days", last_request_within_days)
    _validate_optional_positive_int("last_activity_within_days", last_activity_within_days)

    needs_request_join = last_request_within_days is not None or sort_by == "last_request_at"
    needs_activity_join = last_activity_within_days is not None or sort_by == "last_activity_at"

    request_stats = _build_agent_last_request_subquery(db)
    activity_stats = _build_agent_last_activity_subquery(db)

    base_query = db.query(Agent.id)
    if needs_request_join:
        base_query = base_query.outerjoin(
            request_stats, request_stats.c.agent_id == Agent.id
        )
    if needs_activity_join:
        base_query = base_query.outerjoin(
            activity_stats, activity_stats.c.agent_id == Agent.id
        )

    if role:
        base_query = base_query.filter(Agent.role == role)
    if status:
        base_query = base_query.filter(Agent.status == status)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        base_query = base_query.filter(
            or_(Agent.name.ilike(pattern), Agent.description.ilike(pattern))
        )
    if last_request_within_days is not None:
        request_cutoff = dt.now() - timedelta(days=last_request_within_days)
        base_query = base_query.filter(request_stats.c.last_request_at >= request_cutoff)
    if last_activity_within_days is not None:
        activity_cutoff = dt.now() - timedelta(days=last_activity_within_days)
        base_query = base_query.filter(activity_stats.c.last_activity_at >= activity_cutoff)

    total = base_query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)

    if total == 0:
        return {
            "items": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
            "total_pages": 1,
            "has_more": False,
        }

    base_sort_map = {
        "created_at": Agent.created_at,
        "name": Agent.name,
        "total_score": Agent.total_score,
        "last_request_at": request_stats.c.last_request_at,
        "last_activity_at": activity_stats.c.last_activity_at,
    }
    base_query = base_query.order_by(
        _build_order_clause(sort_by, sort_order, base_sort_map),
        Agent.id.asc(),
    )
    page_ids = [
        row[0]
        for row in base_query.offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    ]

    if not page_ids:
        return {
            "items": [],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "has_more": page < total_pages,
        }

    workload_stats = _build_agent_workload_stats_subquery(db)
    rank_stats = _build_agent_rank_subquery(db)

    enriched_query = (
        db.query(
            Agent.id.label("id"),
            Agent.name.label("name"),
            Agent.role.label("role"),
            Agent.description.label("description"),
            Agent.status.label("status"),
            Agent.total_score.label("total_score"),
            func.coalesce(rank_stats.c.rank, 1).label("rank"),
            func.coalesce(workload_stats.c.assigned_count, 0).label("assigned_count"),
            func.coalesce(workload_stats.c.in_progress_count, 0).label("in_progress_count"),
            func.coalesce(workload_stats.c.review_count, 0).label("review_count"),
            func.coalesce(workload_stats.c.rework_count, 0).label("rework_count"),
            func.coalesce(workload_stats.c.blocked_count, 0).label("blocked_count"),
            request_stats.c.last_request_at.label("last_request_at"),
            activity_stats.c.last_activity_at.label("last_activity_at"),
            Agent.created_at.label("created_at"),
        )
        .outerjoin(workload_stats, workload_stats.c.agent_id == Agent.id)
        .outerjoin(request_stats, request_stats.c.agent_id == Agent.id)
        .outerjoin(activity_stats, activity_stats.c.agent_id == Agent.id)
        .outerjoin(rank_stats, rank_stats.c.agent_id == Agent.id)
        .filter(Agent.id.in_(page_ids))
        .order_by(
            _build_order_clause(
                sort_by,
                sort_order,
                {
                    "created_at": Agent.created_at,
                    "name": Agent.name,
                    "total_score": Agent.total_score,
                    "last_request_at": request_stats.c.last_request_at,
                    "last_activity_at": activity_stats.c.last_activity_at,
                },
            ),
            Agent.id.asc(),
        )
    )

    items = [_serialize_agent_list_row(row) for row in enriched_query.all()]
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


def get_agent_detail(db: Session, agent_id: str) -> dict:
    """查询单个 Agent 详情"""
    workload_stats = _build_agent_workload_stats_subquery(db)
    request_stats = _build_agent_last_request_subquery(db)
    activity_stats = _build_agent_last_activity_subquery(db)
    reward_stats = _build_agent_reward_stats_subquery(db)
    rank_stats = _build_agent_rank_subquery(db)

    total_agents = db.query(func.count(Agent.id)).scalar() or 0

    row = (
        db.query(
            Agent.id.label("id"),
            Agent.name.label("name"),
            Agent.role.label("role"),
            Agent.description.label("description"),
            Agent.status.label("status"),
            Agent.total_score.label("total_score"),
            func.coalesce(rank_stats.c.rank, 1).label("rank"),
            func.coalesce(workload_stats.c.assigned_count, 0).label("assigned_count"),
            func.coalesce(workload_stats.c.in_progress_count, 0).label("in_progress_count"),
            func.coalesce(workload_stats.c.review_count, 0).label("review_count"),
            func.coalesce(workload_stats.c.rework_count, 0).label("rework_count"),
            func.coalesce(workload_stats.c.blocked_count, 0).label("blocked_count"),
            func.coalesce(workload_stats.c.done_count, 0).label("done_count"),
            func.coalesce(workload_stats.c.cancelled_count, 0).label("cancelled_count"),
            func.coalesce(reward_stats.c.reward_count, 0).label("reward_count"),
            func.coalesce(reward_stats.c.penalty_count, 0).label("penalty_count"),
            func.coalesce(reward_stats.c.total_reward_records, 0).label("total_reward_records"),
            request_stats.c.last_request_at.label("last_request_at"),
            activity_stats.c.last_activity_at.label("last_activity_at"),
            Agent.created_at.label("created_at"),
        )
        .outerjoin(workload_stats, workload_stats.c.agent_id == Agent.id)
        .outerjoin(request_stats, request_stats.c.agent_id == Agent.id)
        .outerjoin(activity_stats, activity_stats.c.agent_id == Agent.id)
        .outerjoin(reward_stats, reward_stats.c.agent_id == Agent.id)
        .outerjoin(rank_stats, rank_stats.c.agent_id == Agent.id)
        .filter(Agent.id == agent_id)
        .first()
    )

    if not row:
        raise ResourceNotFoundError(f"Agent {agent_id} 不存在")

    return _serialize_agent_detail_row(row, total_agents=total_agents)


__all__ = ["get_agent_detail", "list_agents"]
