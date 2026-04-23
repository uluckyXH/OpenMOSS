"""管理端任务与模块查询实现。"""

from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ._task_common import (
    DEFAULT_PAGE_SIZE,
    TASK_STATUSES,
    TASK_TYPES,
    Module,
    ResourceNotFoundError,
    Task,
    _build_module_stats_subquery,
    _build_order_clause,
    _build_task_module_count_subquery,
    _build_task_stats_subquery,
    _ensure_task_exists,
    _paginate_query,
    _serialize_module_row,
    _serialize_task_row,
    _validate_optional_enum,
    _validate_page_args,
)


def list_tasks(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询任务列表（含任务级统计）"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("status", status, TASK_STATUSES)
    _validate_optional_enum("type", task_type, TASK_TYPES)

    task_stats = _build_task_stats_subquery(db)
    module_counts = _build_task_module_count_subquery(db)

    query = (
        db.query(
            Task.id.label("id"),
            Task.name.label("name"),
            Task.description.label("description"),
            Task.type.label("type"),
            Task.status.label("status"),
            func.coalesce(module_counts.c.module_count, 0).label("module_count"),
            func.coalesce(task_stats.c.sub_task_count, 0).label("sub_task_count"),
            func.coalesce(task_stats.c.pending_count, 0).label("pending_count"),
            func.coalesce(task_stats.c.assigned_count, 0).label("assigned_count"),
            func.coalesce(task_stats.c.in_progress_count, 0).label("in_progress_count"),
            func.coalesce(task_stats.c.review_count, 0).label("review_count"),
            func.coalesce(task_stats.c.rework_count, 0).label("rework_count"),
            func.coalesce(task_stats.c.blocked_count, 0).label("blocked_count"),
            func.coalesce(task_stats.c.done_count, 0).label("done_count"),
            func.coalesce(task_stats.c.cancelled_count, 0).label("cancelled_count"),
            Task.created_at.label("created_at"),
            Task.updated_at.label("updated_at"),
        )
        .outerjoin(module_counts, module_counts.c.task_id == Task.id)
        .outerjoin(task_stats, task_stats.c.task_id == Task.id)
    )

    if status:
        query = query.filter(Task.status == status)
    if task_type:
        query = query.filter(Task.type == task_type)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                Task.name.ilike(pattern),
                Task.description.ilike(pattern),
            )
        )

    sort_map = {
        "created_at": Task.created_at,
        "updated_at": Task.updated_at,
        "name": Task.name,
        "status": Task.status,
    }
    query = query.order_by(_build_order_clause(sort_by, sort_order, sort_map))

    return _paginate_query(query, page, page_size, _serialize_task_row)


def get_task_detail(db: Session, task_id: str) -> dict:
    """查询单个任务详情（含任务级统计）"""
    task_stats = _build_task_stats_subquery(db)
    module_counts = _build_task_module_count_subquery(db)

    row = (
        db.query(
            Task.id.label("id"),
            Task.name.label("name"),
            Task.description.label("description"),
            Task.type.label("type"),
            Task.status.label("status"),
            func.coalesce(module_counts.c.module_count, 0).label("module_count"),
            func.coalesce(task_stats.c.sub_task_count, 0).label("sub_task_count"),
            func.coalesce(task_stats.c.pending_count, 0).label("pending_count"),
            func.coalesce(task_stats.c.assigned_count, 0).label("assigned_count"),
            func.coalesce(task_stats.c.in_progress_count, 0).label("in_progress_count"),
            func.coalesce(task_stats.c.review_count, 0).label("review_count"),
            func.coalesce(task_stats.c.rework_count, 0).label("rework_count"),
            func.coalesce(task_stats.c.blocked_count, 0).label("blocked_count"),
            func.coalesce(task_stats.c.done_count, 0).label("done_count"),
            func.coalesce(task_stats.c.cancelled_count, 0).label("cancelled_count"),
            Task.created_at.label("created_at"),
            Task.updated_at.label("updated_at"),
        )
        .outerjoin(module_counts, module_counts.c.task_id == Task.id)
        .outerjoin(task_stats, task_stats.c.task_id == Task.id)
        .filter(Task.id == task_id)
        .first()
    )

    if not row:
        raise ResourceNotFoundError(f"任务 {task_id} 不存在")

    return _serialize_task_row(row)


def list_task_modules(
    db: Session,
    task_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询某任务下的模块列表（含模块级统计）"""
    _validate_page_args(page, page_size)
    _ensure_task_exists(db, task_id)

    module_stats = _build_module_stats_subquery(db)

    query = (
        db.query(
            Module.id.label("id"),
            Module.task_id.label("task_id"),
            Module.name.label("name"),
            Module.description.label("description"),
            func.coalesce(module_stats.c.sub_task_count, 0).label("sub_task_count"),
            func.coalesce(module_stats.c.pending_count, 0).label("pending_count"),
            func.coalesce(module_stats.c.assigned_count, 0).label("assigned_count"),
            func.coalesce(module_stats.c.in_progress_count, 0).label("in_progress_count"),
            func.coalesce(module_stats.c.review_count, 0).label("review_count"),
            func.coalesce(module_stats.c.rework_count, 0).label("rework_count"),
            func.coalesce(module_stats.c.blocked_count, 0).label("blocked_count"),
            func.coalesce(module_stats.c.done_count, 0).label("done_count"),
            func.coalesce(module_stats.c.cancelled_count, 0).label("cancelled_count"),
            Module.created_at.label("created_at"),
        )
        .outerjoin(module_stats, module_stats.c.module_id == Module.id)
        .filter(Module.task_id == task_id)
    )

    sort_map = {
        "created_at": Module.created_at,
        "name": Module.name,
    }
    query = query.order_by(_build_order_clause(sort_by, sort_order, sort_map))

    return _paginate_query(query, page, page_size, _serialize_module_row)


def get_module_detail(db: Session, module_id: str) -> dict:
    """查询单个模块详情（含模块级统计）"""
    module_stats = _build_module_stats_subquery(db)

    row = (
        db.query(
            Module.id.label("id"),
            Module.task_id.label("task_id"),
            Task.name.label("task_name"),
            Module.name.label("name"),
            Module.description.label("description"),
            func.coalesce(module_stats.c.sub_task_count, 0).label("sub_task_count"),
            func.coalesce(module_stats.c.pending_count, 0).label("pending_count"),
            func.coalesce(module_stats.c.assigned_count, 0).label("assigned_count"),
            func.coalesce(module_stats.c.in_progress_count, 0).label("in_progress_count"),
            func.coalesce(module_stats.c.review_count, 0).label("review_count"),
            func.coalesce(module_stats.c.rework_count, 0).label("rework_count"),
            func.coalesce(module_stats.c.blocked_count, 0).label("blocked_count"),
            func.coalesce(module_stats.c.done_count, 0).label("done_count"),
            func.coalesce(module_stats.c.cancelled_count, 0).label("cancelled_count"),
            Module.created_at.label("created_at"),
        )
        .join(Task, Task.id == Module.task_id)
        .outerjoin(module_stats, module_stats.c.module_id == Module.id)
        .filter(Module.id == module_id)
        .first()
    )

    if not row:
        raise ResourceNotFoundError(f"模块 {module_id} 不存在")

    return _serialize_module_row(row, include_task_name=True)


__all__ = [
    "get_module_detail",
    "get_task_detail",
    "list_task_modules",
    "list_tasks",
]

