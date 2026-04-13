"""
管理端 Agent 查询服务
"""
from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy import asc, case, desc, func, or_
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

    # ── 阶段 1: 在轻量基表上做 count + 分页取 ID ──
    # 只在需要时 join 时间子查询（仅 last_*_within_days 筛选 或 last_*_at 排序时才需要）
    needs_request_join = (
        last_request_within_days is not None or sort_by == "last_request_at"
    )
    needs_activity_join = (
        last_activity_within_days is not None or sort_by == "last_activity_at"
    )

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

    # 基表筛选
    if role:
        base_query = base_query.filter(Agent.role == role)
    if status:
        base_query = base_query.filter(Agent.status == status)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        base_query = base_query.filter(
            or_(
                Agent.name.ilike(pattern),
                Agent.description.ilike(pattern),
            )
        )
    if last_request_within_days is not None:
        request_cutoff = dt.now() - timedelta(days=last_request_within_days)
        base_query = base_query.filter(
            request_stats.c.last_request_at >= request_cutoff
        )
    if last_activity_within_days is not None:
        activity_cutoff = dt.now() - timedelta(days=last_activity_within_days)
        base_query = base_query.filter(
            activity_stats.c.last_activity_at >= activity_cutoff
        )

    # count 在轻量查询上执行
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

    # 基表排序 + 分页取当前页 ID
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

    # ── 阶段 2: 只对当前页的 ID 做重聚合查询 ──
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
            _build_order_clause(sort_by, sort_order, {
                "created_at": Agent.created_at,
                "name": Agent.name,
                "total_score": Agent.total_score,
                "last_request_at": request_stats.c.last_request_at,
                "last_activity_at": activity_stats.c.last_activity_at,
            }),
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
    # 不再额外查 _ensure_agent_exists，主查询的 if not row 已处理 404

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
    """将聚合结果规范为 int"""
    return int(value or 0)
