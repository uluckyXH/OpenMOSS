"""
管理端任务查询路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin_task import (
    AdminModuleDetail,
    AdminModulePageResponse,
    AdminSubTaskDetail,
    AdminSubTaskPageResponse,
    AdminTaskDetail,
    AdminTaskPageResponse,
)
from app.services import admin_task_query_service


router = APIRouter(prefix="/admin", tags=["Admin Task"])


@router.get("/tasks", response_model=AdminTaskPageResponse, summary="管理端查看任务列表")
async def list_admin_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(None, description="任务状态"),
    task_type: Optional[str] = Query(None, alias="type", description="任务类型 once/recurring"),
    keyword: Optional[str] = Query(None, description="按任务名或描述搜索"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查询管理端任务列表"""
    return admin_task_query_service.list_tasks(
        db,
        page=page,
        page_size=page_size,
        status=status,
        task_type=task_type,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/tasks/{task_id}", response_model=AdminTaskDetail, summary="管理端查看任务详情")
async def get_admin_task_detail(
    task_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端任务详情"""
    return admin_task_query_service.get_task_detail(db, task_id)


@router.get("/tasks/{task_id}/modules", response_model=AdminModulePageResponse, summary="管理端查看任务模块列表")
async def list_admin_task_modules(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看某任务下的模块列表"""
    return admin_task_query_service.list_task_modules(
        db,
        task_id=task_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/modules/{module_id}", response_model=AdminModuleDetail, summary="管理端查看模块详情")
async def get_admin_module_detail(
    module_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端模块详情"""
    return admin_task_query_service.get_module_detail(db, module_id)


@router.get(
    "/tasks/{task_id}/sub-tasks",
    response_model=AdminSubTaskPageResponse,
    summary="管理端查看任务子任务列表",
)
async def list_admin_task_sub_tasks(
    task_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    module_id: Optional[str] = Query(None, description="按模块过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    assigned_agent: Optional[str] = Query(None, description="按 Agent ID 过滤"),
    priority: Optional[str] = Query(None, description="按优先级过滤"),
    task_type: Optional[str] = Query(None, alias="type", description="按类型过滤 once/recurring"),
    keyword: Optional[str] = Query(None, description="按名称或描述搜索"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看某任务下的子任务列表"""
    return admin_task_query_service.list_task_sub_tasks(
        db,
        task_id=task_id,
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


@router.get(
    "/modules/{module_id}/sub-tasks",
    response_model=AdminSubTaskPageResponse,
    summary="管理端查看模块子任务列表",
)
async def list_admin_module_sub_tasks(
    module_id: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    assigned_agent: Optional[str] = Query(None, description="按 Agent ID 过滤"),
    priority: Optional[str] = Query(None, description="按优先级过滤"),
    task_type: Optional[str] = Query(None, alias="type", description="按类型过滤 once/recurring"),
    keyword: Optional[str] = Query(None, description="按名称或描述搜索"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看某模块下的子任务列表"""
    return admin_task_query_service.list_module_sub_tasks(
        db,
        module_id=module_id,
        page=page,
        page_size=page_size,
        status=status,
        assigned_agent=assigned_agent,
        priority=priority,
        task_type=task_type,
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.get("/sub-tasks", response_model=AdminSubTaskPageResponse, summary="管理端查看全局子任务列表")
async def list_admin_sub_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    task_id: Optional[str] = Query(None, description="按任务过滤"),
    module_id: Optional[str] = Query(None, description="按模块过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    assigned_agent: Optional[str] = Query(None, description="按 Agent ID 过滤"),
    priority: Optional[str] = Query(None, description="按优先级过滤"),
    task_type: Optional[str] = Query(None, alias="type", description="按类型过滤 once/recurring"),
    keyword: Optional[str] = Query(None, description="按名称或描述搜索"),
    sort_by: str = Query("created_at", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看全局子任务列表"""
    return admin_task_query_service.list_sub_tasks(
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


@router.get("/sub-tasks/{sub_task_id}", response_model=AdminSubTaskDetail, summary="管理端查看子任务详情")
async def get_admin_sub_task_detail(
    sub_task_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端子任务详情"""
    return admin_task_query_service.get_sub_task_detail(db, sub_task_id)
