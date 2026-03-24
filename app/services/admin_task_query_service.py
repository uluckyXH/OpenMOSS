"""
管理端任务查询服务
"""
from typing import Optional

from sqlalchemy import asc, case, desc, func, or_
from sqlalchemy.orm import Query, Session

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


class AdminTaskQueryError(ValueError):
    """管理端查询通用错误"""


class InvalidQueryError(AdminTaskQueryError):
    """非法查询参数"""


class ResourceNotFoundError(AdminTaskQueryError):
    """资源不存在"""


def list_tasks(
    db: Session,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    keyword: Optional[str] = None,
    team_id: Optional[str] = None,
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
    if team_id:
        query = query.filter(Task.team_id == team_id)

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
        Task.team_id.label("team_id"),
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
        "team_id": mapping.get("team_id"),
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
    """将聚合结果规范为 int"""
    return int(value or 0)
