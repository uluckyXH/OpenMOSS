"""
管理端任务查询服务
"""
from typing import Optional

from sqlalchemy import asc, case, desc, func, or_
from sqlalchemy.orm import Query, Session

from app.exceptions import (
    AdminInvalidQueryError as InvalidQueryError,
    AdminQueryError as AdminTaskQueryError,
    AdminResourceNotFoundError as ResourceNotFoundError,
)
from app.models.agent import Agent
from app.models.module import Module
from app.models.sub_task import SubTask
from app.models.task import Task


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
TASK_TYPES = {"once", "recurring"}
TASK_STATUSES = {"planning", "active", "in_progress", "completed", "archived", "cancelled"}
SUB_TASK_STATUSES = {
    "pending",
    "assigned",
    "in_progress",
    "review",
    "rework",
    "blocked",
    "done",
    "cancelled",
}
SUB_TASK_PRIORITIES = {"high", "medium", "low"}


def _build_task_stats_subquery(db: Session):
    """按 task_id 聚合子任务统计"""
    return (
        db.query(
            SubTask.task_id.label("task_id"),
            func.count(SubTask.id).label("sub_task_count"),
            *[
                func.coalesce(
                    func.sum(case((SubTask.status == status, 1), else_=0)),
                    0,
                ).label(f"{status}_count")
                for status in (
                    "pending",
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
        .group_by(SubTask.task_id)
        .subquery()
    )


def _build_task_module_count_subquery(db: Session):
    """按 task_id 聚合模块数量"""
    return (
        db.query(
            Module.task_id.label("task_id"),
            func.count(Module.id).label("module_count"),
        )
        .group_by(Module.task_id)
        .subquery()
    )


def _build_module_stats_subquery(db: Session):
    """按 module_id 聚合子任务统计"""
    return (
        db.query(
            SubTask.module_id.label("module_id"),
            func.count(SubTask.id).label("sub_task_count"),
            *[
                func.coalesce(
                    func.sum(case((SubTask.status == status, 1), else_=0)),
                    0,
                ).label(f"{status}_count")
                for status in (
                    "pending",
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
        .filter(SubTask.module_id.isnot(None))
        .group_by(SubTask.module_id)
        .subquery()
    )


def _build_sub_task_query(db: Session, include_detail_fields: bool) -> Query:
    """构建子任务基础查询"""
    columns = [
        SubTask.id.label("id"),
        SubTask.task_id.label("task_id"),
        Task.name.label("task_name"),
        SubTask.module_id.label("module_id"),
        Module.name.label("module_name"),
        SubTask.name.label("name"),
        SubTask.description.label("description"),
        SubTask.type.label("type"),
        SubTask.status.label("status"),
        SubTask.priority.label("priority"),
        SubTask.assigned_agent.label("assigned_agent"),
        Agent.name.label("assigned_agent_name"),
        SubTask.current_session_id.label("current_session_id"),
        SubTask.rework_count.label("rework_count"),
        SubTask.created_at.label("created_at"),
        SubTask.updated_at.label("updated_at"),
        SubTask.completed_at.label("completed_at"),
    ]

    if include_detail_fields:
        columns.extend(
            [
                SubTask.deliverable.label("deliverable"),
                SubTask.acceptance.label("acceptance"),
            ]
        )

    return (
        db.query(*columns)
        .join(Task, Task.id == SubTask.task_id)
        .outerjoin(Module, Module.id == SubTask.module_id)
        .outerjoin(Agent, Agent.id == SubTask.assigned_agent)
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


def _serialize_task_row(row) -> dict:
    mapping = row._mapping
    return {
        "id": mapping["id"],
        "name": mapping["name"],
        "description": mapping["description"] or "",
        "type": mapping["type"],
        "status": mapping["status"],
        "module_count": _int_or_zero(mapping["module_count"]),
        "sub_task_count": _int_or_zero(mapping["sub_task_count"]),
        "pending_count": _int_or_zero(mapping["pending_count"]),
        "assigned_count": _int_or_zero(mapping["assigned_count"]),
        "in_progress_count": _int_or_zero(mapping["in_progress_count"]),
        "review_count": _int_or_zero(mapping["review_count"]),
        "rework_count": _int_or_zero(mapping["rework_count"]),
        "blocked_count": _int_or_zero(mapping["blocked_count"]),
        "done_count": _int_or_zero(mapping["done_count"]),
        "cancelled_count": _int_or_zero(mapping["cancelled_count"]),
        "created_at": mapping["created_at"],
        "updated_at": mapping["updated_at"],
    }


def _serialize_module_row(row, include_task_name: bool = False) -> dict:
    mapping = row._mapping
    data = {
        "id": mapping["id"],
        "task_id": mapping["task_id"],
        "name": mapping["name"],
        "description": mapping["description"] or "",
        "sub_task_count": _int_or_zero(mapping["sub_task_count"]),
        "pending_count": _int_or_zero(mapping["pending_count"]),
        "assigned_count": _int_or_zero(mapping["assigned_count"]),
        "in_progress_count": _int_or_zero(mapping["in_progress_count"]),
        "review_count": _int_or_zero(mapping["review_count"]),
        "rework_count": _int_or_zero(mapping["rework_count"]),
        "blocked_count": _int_or_zero(mapping["blocked_count"]),
        "done_count": _int_or_zero(mapping["done_count"]),
        "cancelled_count": _int_or_zero(mapping["cancelled_count"]),
        "created_at": mapping["created_at"],
    }
    if include_task_name:
        data["task_name"] = mapping["task_name"]
    return data


def _serialize_sub_task_row(row, include_detail_fields: bool = False) -> dict:
    mapping = row._mapping
    data = {
        "id": mapping["id"],
        "task_id": mapping["task_id"],
        "task_name": mapping["task_name"],
        "module_id": mapping["module_id"],
        "module_name": mapping["module_name"],
        "name": mapping["name"],
        "description": mapping["description"] or "",
        "type": mapping["type"],
        "status": mapping["status"],
        "priority": mapping["priority"],
        "assigned_agent": mapping["assigned_agent"],
        "assigned_agent_name": mapping["assigned_agent_name"],
        "current_session_id": mapping["current_session_id"],
        "rework_count": _int_or_zero(mapping["rework_count"]),
        "created_at": mapping["created_at"],
        "updated_at": mapping["updated_at"],
        "completed_at": mapping["completed_at"],
    }
    if include_detail_fields:
        data["deliverable"] = mapping["deliverable"] or ""
        data["acceptance"] = mapping["acceptance"] or ""
    return data


def _ensure_task_exists(db: Session, task_id: str) -> None:
    """校验任务存在"""
    exists = db.query(Task.id).filter(Task.id == task_id).first()
    if not exists:
        raise ResourceNotFoundError(f"任务 {task_id} 不存在")


def _ensure_module_exists(db: Session, module_id: str, task_id: Optional[str] = None) -> Module:
    """校验模块存在，可选校验其所属任务"""
    module = db.query(Module).filter(Module.id == module_id).first()
    if not module:
        raise ResourceNotFoundError(f"模块 {module_id} 不存在")
    if task_id and module.task_id != task_id:
        raise InvalidQueryError(f"模块 {module_id} 不属于任务 {task_id}")
    return module


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
    if sort_order not in ("asc", "desc"):
        raise InvalidQueryError("sort_order 只能是 asc 或 desc")

    column = sort_map[sort_by]
    return asc(column) if sort_order == "asc" else desc(column)


def _int_or_zero(value) -> int:
    return int(value or 0)
