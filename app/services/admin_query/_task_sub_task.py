"""管理端子任务查询实现。"""

from typing import Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ._task_common import (
    DEFAULT_PAGE_SIZE,
    SUB_TASK_PRIORITIES,
    SUB_TASK_STATUSES,
    TASK_TYPES,
    ResourceNotFoundError,
    SubTask,
    _build_order_clause,
    _build_sub_task_query,
    _ensure_module_exists,
    _ensure_task_exists,
    _paginate_query,
    _serialize_sub_task_row,
    _validate_optional_enum,
    _validate_page_args,
)


def list_task_sub_tasks(
    db: Session,
    task_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    module_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询某任务下的子任务列表"""
    _ensure_task_exists(db, task_id)
    if module_id:
        _ensure_module_exists(db, module_id, task_id=task_id)
    return _list_sub_tasks(
        db,
        page=page,
        page_size=page_size,
        task_id=task_id,
        module_id=module_id,
        status=status,
        assigned_agent=assigned_agent,
        priority=priority,
        task_type=task_type,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def list_module_sub_tasks(
    db: Session,
    module_id: str,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询某模块下的子任务列表"""
    _ensure_module_exists(db, module_id)
    return _list_sub_tasks(
        db,
        page=page,
        page_size=page_size,
        module_id=module_id,
        status=status,
        assigned_agent=assigned_agent,
        priority=priority,
        task_type=task_type,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def list_sub_tasks(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    task_id: Optional[str] = None,
    module_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询全局子任务列表"""
    if task_id:
        _ensure_task_exists(db, task_id)
    if module_id:
        _ensure_module_exists(db, module_id, task_id=task_id)
    return _list_sub_tasks(
        db,
        page=page,
        page_size=page_size,
        task_id=task_id,
        module_id=module_id,
        status=status,
        assigned_agent=assigned_agent,
        priority=priority,
        task_type=task_type,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )


def get_sub_task_detail(db: Session, sub_task_id: str) -> dict:
    """查询单个子任务详情"""
    row = (
        _build_sub_task_query(db, include_detail_fields=True)
        .filter(SubTask.id == sub_task_id)
        .first()
    )
    if not row:
        raise ResourceNotFoundError(f"子任务 {sub_task_id} 不存在")
    return _serialize_sub_task_row(row, include_detail_fields=True)


def _list_sub_tasks(
    db: Session,
    page: int,
    page_size: int,
    task_id: Optional[str] = None,
    module_id: Optional[str] = None,
    status: Optional[str] = None,
    assigned_agent: Optional[str] = None,
    priority: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict:
    """分页查询子任务列表的通用实现"""
    _validate_page_args(page, page_size)
    _validate_optional_enum("status", status, SUB_TASK_STATUSES)
    _validate_optional_enum("priority", priority, SUB_TASK_PRIORITIES)
    _validate_optional_enum("type", task_type, TASK_TYPES)

    query = _build_sub_task_query(db, include_detail_fields=False)

    if task_id:
        query = query.filter(SubTask.task_id == task_id)
    if module_id:
        query = query.filter(SubTask.module_id == module_id)
    if status:
        query = query.filter(SubTask.status == status)
    if assigned_agent:
        query = query.filter(SubTask.assigned_agent == assigned_agent)
    if priority:
        query = query.filter(SubTask.priority == priority)
    if task_type:
        query = query.filter(SubTask.type == task_type)
    if keyword and keyword.strip():
        pattern = f"%{keyword.strip()}%"
        query = query.filter(
            or_(
                SubTask.name.ilike(pattern),
                SubTask.description.ilike(pattern),
            )
        )

    sort_map = {
        "created_at": SubTask.created_at,
        "updated_at": SubTask.updated_at,
        "priority": SubTask.priority,
        "status": SubTask.status,
        "rework_count": SubTask.rework_count,
    }
    query = query.order_by(_build_order_clause(sort_by, sort_order, sort_map))

    return _paginate_query(query, page, page_size, _serialize_sub_task_row)


__all__ = [
    "get_sub_task_detail",
    "list_module_sub_tasks",
    "list_sub_tasks",
    "list_task_sub_tasks",
]

