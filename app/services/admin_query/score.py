"""管理端积分查询与调分实现。"""

from typing import Optional

from sqlalchemy import asc, case, desc, func
from sqlalchemy.orm import Session

from app.exceptions import BusinessError
from app.models.agent import Agent
from app.models.reward_log import RewardLog
from app.services.task_core import reward as reward_service

from ._score_common import (
    AGENT_ROLES,
    AGENT_STATUSES,
    DEFAULT_PAGE_SIZE,
    SCORE_SIGNS,
    InvalidQueryError,
    _apply_leaderboard_filters,
    _apply_score_log_filters,
    _build_order_clause,
    _build_rank_subquery,
    _build_reward_stats_subquery,
    _int_or_zero,
    _paginate_query,
    _serialize_leaderboard_row,
    _serialize_score_log_row,
    _validate_optional_enum,
    _validate_page_args,
    _validate_sort_order,
)


class AdminScoreWriteError(BusinessError):
    """管理端积分写操作通用错误。"""


def get_score_summary(db: Session) -> dict:
    """查询管理端积分页顶部概览统计"""
    row = db.query(
        func.count(Agent.id).label("total_agents"),
        func.coalesce(
            func.sum(case((Agent.total_score > 0, 1), else_=0)),
            0,
        ).label("positive_score_agents"),
        func.coalesce(
            func.sum(case((Agent.total_score == 0, 1), else_=0)),
            0,
        ).label("zero_score_agents"),
        func.coalesce(
            func.sum(case((Agent.total_score < 0, 1), else_=0)),
            0,
        ).label("negative_score_agents"),
        func.coalesce(func.max(Agent.total_score), 0).label("top_score"),
        func.coalesce(func.avg(Agent.total_score), 0.0).label("average_score"),
    ).first()

    last_score_at = db.query(func.max(RewardLog.created_at)).scalar()
    mapping = row._mapping
    return {
        "total_agents": _int_or_zero(mapping["total_agents"]),
        "positive_score_agents": _int_or_zero(mapping["positive_score_agents"]),
        "zero_score_agents": _int_or_zero(mapping["zero_score_agents"]),
        "negative_score_agents": _int_or_zero(mapping["negative_score_agents"]),
        "top_score": _int_or_zero(mapping["top_score"]),
        "average_score": round(float(mapping["average_score"] or 0.0), 2),
        "last_score_at": last_score_at,
    }


def list_score_leaderboard(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    role: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
    sort_by: str = "total_score",
    sort_order: str = "desc",
) -> dict:
    """分页查询管理端积分排行榜"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("role", role, AGENT_ROLES)
    _validate_optional_enum("status", status, AGENT_STATUSES)
    if score_min is not None and score_max is not None and score_min > score_max:
        raise InvalidQueryError("score_min 不能大于 score_max")

    total_query = _apply_leaderboard_filters(
        db.query(func.count(Agent.id)),
        role=role,
        status=status,
        keyword=keyword,
        score_min=score_min,
        score_max=score_max,
    )
    total = _int_or_zero(total_query.scalar())

    reward_stats = _build_reward_stats_subquery(db)
    rank_stats = _build_rank_subquery(db)

    query = (
        db.query(
            func.coalesce(rank_stats.c.rank, 1).label("rank"),
            Agent.id.label("agent_id"),
            Agent.name.label("agent_name"),
            Agent.role.label("role"),
            Agent.status.label("status"),
            Agent.total_score.label("total_score"),
            func.coalesce(reward_stats.c.reward_count, 0).label("reward_count"),
            func.coalesce(reward_stats.c.penalty_count, 0).label("penalty_count"),
            func.coalesce(reward_stats.c.total_records, 0).label("total_records"),
            reward_stats.c.last_score_at.label("last_score_at"),
            Agent.created_at.label("created_at"),
        )
        .outerjoin(reward_stats, reward_stats.c.agent_id == Agent.id)
        .outerjoin(rank_stats, rank_stats.c.agent_id == Agent.id)
    )
    query = _apply_leaderboard_filters(
        query,
        role=role,
        status=status,
        keyword=keyword,
        score_min=score_min,
        score_max=score_max,
    )

    sort_map = {
        "total_score": Agent.total_score,
        "rank": rank_stats.c.rank,
        "created_at": Agent.created_at,
        "last_score_at": reward_stats.c.last_score_at,
    }
    query = query.order_by(
        _build_order_clause(sort_by, sort_order, sort_map),
        Agent.id.asc(),
    )

    return _paginate_query(query, total, page, page_size, _serialize_leaderboard_row)


def list_score_logs(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    agent_id: Optional[str] = None,
    sub_task_id: Optional[str] = None,
    score_sign: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_order: str = "desc",
) -> dict:
    """分页查询管理端全局积分流水"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("score_sign", score_sign, SCORE_SIGNS)
    _validate_sort_order(sort_order)

    total_query = _apply_score_log_filters(
        db.query(func.count(RewardLog.id)),
        agent_id=agent_id,
        sub_task_id=sub_task_id,
        score_sign=score_sign,
        keyword=keyword,
    )
    total = _int_or_zero(total_query.scalar())

    query = (
        db.query(
            RewardLog.id.label("id"),
            RewardLog.agent_id.label("agent_id"),
            Agent.name.label("agent_name"),
            RewardLog.sub_task_id.label("sub_task_id"),
            RewardLog.reason.label("reason"),
            RewardLog.score_delta.label("score_delta"),
            RewardLog.created_at.label("created_at"),
        )
        .join(Agent, Agent.id == RewardLog.agent_id)
    )
    query = _apply_score_log_filters(
        query,
        agent_id=agent_id,
        sub_task_id=sub_task_id,
        score_sign=score_sign,
        keyword=keyword,
    )

    created_at_order = desc(RewardLog.created_at) if sort_order == "desc" else asc(RewardLog.created_at)
    id_order = desc(RewardLog.id) if sort_order == "desc" else asc(RewardLog.id)
    query = query.order_by(created_at_order, id_order)

    return _paginate_query(query, total, page, page_size, _serialize_score_log_row)


def adjust_score(
    db: Session,
    agent_id: str,
    score_delta: int,
    reason: str,
    sub_task_id: str = None,
) -> dict:
    """管理员手动调分，并返回最新总分。"""
    normalized_reason = (reason or "").strip()
    final_reason = f"[管理端调分] {normalized_reason}"
    if score_delta == 0:
        raise InvalidQueryError("score_delta 不能为 0")
    if not normalized_reason:
        raise InvalidQueryError("reason 不能为空")
    if len(final_reason) > 100:
        raise InvalidQueryError("reason 长度不能超过 100 个字符")

    try:
        reward_log = reward_service.add_reward(
            db,
            agent_id=agent_id,
            reason=final_reason,
            score_delta=score_delta,
            sub_task_id=sub_task_id,
        )
    except BusinessError as exc:
        raise AdminScoreWriteError(str(exc), status_code=exc.status_code) from exc

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise AdminScoreWriteError(f"Agent {agent_id} 不存在", status_code=404)

    return {
        "id": reward_log.id,
        "agent_id": reward_log.agent_id,
        "sub_task_id": reward_log.sub_task_id,
        "reason": reward_log.reason,
        "score_delta": reward_log.score_delta,
        "created_at": reward_log.created_at,
        "current_total_score": int(agent.total_score or 0),
    }


__all__ = [
    "AdminScoreWriteError",
    "get_score_summary",
    "list_score_leaderboard",
    "list_score_logs",
    "adjust_score",
]
