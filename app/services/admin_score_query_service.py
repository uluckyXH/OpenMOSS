"""
管理端积分排行榜查询服务
"""
from typing import Optional

from sqlalchemy import asc, case, desc, func, or_
from sqlalchemy.orm import Query, Session

from app.exceptions import (
    AdminInvalidQueryError as InvalidQueryError,
    AdminQueryError as AdminScoreQueryError,
)
from app.models.agent import Agent
from app.models.reward_log import RewardLog


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
AGENT_ROLES = {"planner", "executor", "reviewer", "patrol"}
AGENT_STATUSES = {"active", "disabled"}
SCORE_SIGNS = {"positive", "negative"}


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


def _build_reward_stats_subquery(db: Session):
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
            func.count(RewardLog.id).label("total_records"),
            func.max(RewardLog.created_at).label("last_score_at"),
        )
        .group_by(RewardLog.agent_id)
        .subquery()
    )


def _build_rank_subquery(db: Session):
    """计算按 total_score 的 dense rank"""
    return (
        db.query(
            Agent.id.label("agent_id"),
            func.dense_rank().over(order_by=Agent.total_score.desc()).label("rank"),
        )
        .subquery()
    )


def _apply_leaderboard_filters(
    query: Query,
    role: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    score_min: Optional[int] = None,
    score_max: Optional[int] = None,
) -> Query:
    """统一应用排行榜过滤条件"""
    if role:
        query = query.filter(Agent.role == role)
    if status:
        query = query.filter(Agent.status == status)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Agent.name.ilike(pattern),
                Agent.description.ilike(pattern),
            )
        )
    if score_min is not None:
        query = query.filter(Agent.total_score >= score_min)
    if score_max is not None:
        query = query.filter(Agent.total_score <= score_max)
    return query


def _apply_score_log_filters(
    query: Query,
    agent_id: Optional[str] = None,
    sub_task_id: Optional[str] = None,
    score_sign: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Query:
    """统一应用全局积分流水过滤条件"""
    if agent_id:
        query = query.filter(RewardLog.agent_id == agent_id)
    if sub_task_id:
        query = query.filter(RewardLog.sub_task_id == sub_task_id)
    if score_sign == "positive":
        query = query.filter(RewardLog.score_delta > 0)
    elif score_sign == "negative":
        query = query.filter(RewardLog.score_delta < 0)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(RewardLog.reason.ilike(pattern))
    return query


def _paginate_query(query: Query, total: int, page: int, page_size: int, serializer) -> dict:
    """分页执行查询并序列化结果"""
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


def _serialize_leaderboard_row(row) -> dict:
    mapping = row._mapping
    return {
        "rank": _int_or_zero(mapping["rank"]) or 1,
        "agent_id": mapping["agent_id"],
        "agent_name": mapping["agent_name"],
        "role": mapping["role"],
        "status": mapping["status"],
        "total_score": _int_or_zero(mapping["total_score"]),
        "reward_count": _int_or_zero(mapping["reward_count"]),
        "penalty_count": _int_or_zero(mapping["penalty_count"]),
        "total_records": _int_or_zero(mapping["total_records"]),
        "last_score_at": mapping["last_score_at"],
        "created_at": mapping["created_at"],
    }


def _serialize_score_log_row(row) -> dict:
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "agent_id": mapping["agent_id"],
        "agent_name": mapping["agent_name"],
        "sub_task_id": mapping["sub_task_id"],
        "reason": mapping["reason"],
        "score_delta": _int_or_zero(mapping["score_delta"]),
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


def _build_order_clause(sort_by: str, sort_order: str, sort_map: dict):
    """构建排序表达式"""
    if sort_by not in sort_map:
        raise InvalidQueryError(
            f"无效的 sort_by '{sort_by}'，可选: {', '.join(sorted(sort_map.keys()))}"
        )
    _validate_sort_order(sort_order)

    column = sort_map[sort_by]
    return asc(column) if sort_order == "asc" else desc(column)


def _validate_sort_order(sort_order: str) -> None:
    """校验排序方向"""
    if sort_order not in ("asc", "desc"):
        raise InvalidQueryError("sort_order 只能是 asc 或 desc")


def _int_or_zero(value) -> int:
    """将聚合结果规范为 int"""
    return int(value or 0)
