"""
管理端审查记录查询服务
"""
from datetime import datetime as dt, timedelta
from typing import Optional

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Query, Session, aliased

from app.exceptions import (
    AdminInvalidQueryError as InvalidQueryError,
    AdminQueryError as AdminReviewQueryError,
    AdminResourceNotFoundError as ResourceNotFoundError,
)
from app.models.agent import Agent
from app.models.module import Module
from app.models.review_record import ReviewRecord
from app.models.sub_task import SubTask
from app.models.task import Task


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
REVIEW_RESULTS = {"approved", "rejected"}


def list_review_records(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    task_id: Optional[str] = None,
    sub_task_id: Optional[str] = None,
    reviewer_agent: Optional[str] = None,
    result: Optional[str] = None,
    keyword: Optional[str] = None,
    days: Optional[int] = None,
    sort_order: str = "desc",
) -> dict:
    """分页查询管理端审查记录列表"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("result", result, REVIEW_RESULTS)
    _validate_optional_positive_int("days", days)
    _validate_sort_order(sort_order)

    reviewer_alias = aliased(Agent)
    rework_alias = aliased(Agent)

    # 阶段 1：在轻量查询上做 count 和分页取 ID，避免对详情字段直接重分页
    base_query = (
        db.query(ReviewRecord.id)
        .join(SubTask, SubTask.id == ReviewRecord.sub_task_id)
        .join(Task, Task.id == SubTask.task_id)
        .outerjoin(reviewer_alias, reviewer_alias.id == ReviewRecord.reviewer_agent)
        .outerjoin(rework_alias, rework_alias.id == ReviewRecord.rework_agent)
    )
    base_query = _apply_review_filters(
        base_query,
        task_id=task_id,
        sub_task_id=sub_task_id,
        reviewer_agent=reviewer_agent,
        result=result,
        keyword=keyword,
        days=days,
        reviewer_alias=reviewer_alias,
        rework_alias=rework_alias,
    )

    total = base_query.count()
    total_pages = max(1, (total + page_size - 1) // page_size)
    if total == 0:
        return _empty_page(page, page_size)

    created_at_order = desc(ReviewRecord.created_at) if sort_order == "desc" else asc(ReviewRecord.created_at)
    id_order = desc(ReviewRecord.id) if sort_order == "desc" else asc(ReviewRecord.id)
    page_ids = [
        row[0]
        for row in base_query.order_by(created_at_order, id_order)
        .offset((page - 1) * page_size)
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

    reviewer_detail = aliased(Agent)
    rework_detail = aliased(Agent)
    query = (
        db.query(
            ReviewRecord.id.label("id"),
            Task.id.label("task_id"),
            Task.name.label("task_name"),
            SubTask.module_id.label("module_id"),
            Module.name.label("module_name"),
            ReviewRecord.sub_task_id.label("sub_task_id"),
            SubTask.name.label("sub_task_name"),
            ReviewRecord.reviewer_agent.label("reviewer_agent"),
            reviewer_detail.name.label("reviewer_agent_name"),
            ReviewRecord.round.label("round"),
            ReviewRecord.result.label("result"),
            ReviewRecord.score.label("score"),
            ReviewRecord.issues.label("issues"),
            ReviewRecord.comment.label("comment"),
            ReviewRecord.rework_agent.label("rework_agent"),
            rework_detail.name.label("rework_agent_name"),
            ReviewRecord.created_at.label("created_at"),
        )
        .join(SubTask, SubTask.id == ReviewRecord.sub_task_id)
        .join(Task, Task.id == SubTask.task_id)
        .outerjoin(Module, Module.id == SubTask.module_id)
        .outerjoin(reviewer_detail, reviewer_detail.id == ReviewRecord.reviewer_agent)
        .outerjoin(rework_detail, rework_detail.id == ReviewRecord.rework_agent)
        .filter(ReviewRecord.id.in_(page_ids))
        .order_by(created_at_order, id_order)
    )

    return {
        "items": [_serialize_review_list_row(row) for row in query.all()],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_more": page < total_pages,
    }


def get_review_detail(db: Session, review_id: str) -> dict:
    """查询单条管理端审查记录详情"""
    reviewer_alias = aliased(Agent)
    rework_alias = aliased(Agent)

    row = (
        db.query(
            ReviewRecord.id.label("id"),
            Task.id.label("task_id"),
            Task.name.label("task_name"),
            SubTask.module_id.label("module_id"),
            Module.name.label("module_name"),
            ReviewRecord.sub_task_id.label("sub_task_id"),
            SubTask.name.label("sub_task_name"),
            SubTask.description.label("sub_task_description"),
            SubTask.deliverable.label("sub_task_deliverable"),
            SubTask.acceptance.label("sub_task_acceptance"),
            ReviewRecord.reviewer_agent.label("reviewer_agent"),
            reviewer_alias.name.label("reviewer_agent_name"),
            ReviewRecord.round.label("round"),
            ReviewRecord.result.label("result"),
            ReviewRecord.score.label("score"),
            ReviewRecord.issues.label("issues"),
            ReviewRecord.comment.label("comment"),
            ReviewRecord.rework_agent.label("rework_agent"),
            rework_alias.name.label("rework_agent_name"),
            ReviewRecord.created_at.label("created_at"),
        )
        .join(SubTask, SubTask.id == ReviewRecord.sub_task_id)
        .join(Task, Task.id == SubTask.task_id)
        .outerjoin(Module, Module.id == SubTask.module_id)
        .outerjoin(reviewer_alias, reviewer_alias.id == ReviewRecord.reviewer_agent)
        .outerjoin(rework_alias, rework_alias.id == ReviewRecord.rework_agent)
        .filter(ReviewRecord.id == review_id)
        .first()
    )

    if not row:
        raise ResourceNotFoundError(f"审查记录 {review_id} 不存在")

    return _serialize_review_detail_row(row)


def _apply_review_filters(
    query: Query,
    task_id: Optional[str],
    sub_task_id: Optional[str],
    reviewer_agent: Optional[str],
    result: Optional[str],
    keyword: Optional[str],
    days: Optional[int],
    reviewer_alias,
    rework_alias,
) -> Query:
    """统一应用审查记录过滤条件"""
    if task_id:
        query = query.filter(SubTask.task_id == task_id)
    if sub_task_id:
        query = query.filter(ReviewRecord.sub_task_id == sub_task_id)
    if reviewer_agent:
        query = query.filter(ReviewRecord.reviewer_agent == reviewer_agent)
    if result:
        query = query.filter(ReviewRecord.result == result)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Task.name.ilike(pattern),
                SubTask.name.ilike(pattern),
                ReviewRecord.comment.ilike(pattern),
                ReviewRecord.issues.ilike(pattern),
                reviewer_alias.name.ilike(pattern),
                rework_alias.name.ilike(pattern),
            )
        )
    if days is not None:
        query = query.filter(ReviewRecord.created_at >= dt.now() - timedelta(days=days))
    return query


def _serialize_review_list_row(row) -> dict:
    """序列化列表项"""
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "task_id": mapping["task_id"],
        "task_name": mapping["task_name"],
        "module_id": mapping["module_id"],
        "module_name": mapping["module_name"],
        "sub_task_id": mapping["sub_task_id"],
        "sub_task_name": mapping["sub_task_name"],
        "reviewer_agent": mapping["reviewer_agent"],
        "reviewer_agent_name": mapping["reviewer_agent_name"],
        "round": int(mapping["round"] or 0),
        "result": mapping["result"],
        "score": int(mapping["score"] or 0),
        "issues": mapping["issues"] or "",
        "comment": mapping["comment"] or "",
        "rework_agent": mapping["rework_agent"],
        "rework_agent_name": mapping["rework_agent_name"],
        "created_at": mapping["created_at"],
    }


def _serialize_review_detail_row(row) -> dict:
    """序列化详情项"""
    data = _serialize_review_list_row(row)
    mapping = row._mapping
    data.update(
        {
            "sub_task_description": mapping["sub_task_description"] or "",
            "sub_task_deliverable": mapping["sub_task_deliverable"] or "",
            "sub_task_acceptance": mapping["sub_task_acceptance"] or "",
        }
    )
    return data


def _empty_page(page: int, page_size: int) -> dict:
    """空分页响应"""
    return {
        "items": [],
        "total": 0,
        "page": page,
        "page_size": page_size,
        "total_pages": 1,
        "has_more": False,
    }


def _validate_page_args(page: int, page_size: int) -> None:
    """校验分页参数"""
    if page < 1:
        raise InvalidQueryError("page 必须 >= 1")
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise InvalidQueryError(f"page_size 必须在 1-{MAX_PAGE_SIZE} 之间")


def _validate_optional_positive_int(name: str, value: Optional[int]) -> None:
    """校验可选正整数"""
    if value is not None and value <= 0:
        raise InvalidQueryError(f"{name} 必须 >= 1")


def _validate_optional_enum(name: str, value: Optional[str], choices: set) -> None:
    """校验可选枚举值"""
    if value and value not in choices:
        joined = ", ".join(sorted(choices))
        raise InvalidQueryError(f"{name} 非法，可选值: {joined}")


def _validate_sort_order(sort_order: str) -> None:
    """校验排序方向"""
    if sort_order not in {"asc", "desc"}:
        raise InvalidQueryError("sort_order 非法，可选值: asc, desc")
