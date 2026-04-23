"""
任务路由 — 任务和模块的 CRUD
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt

from app.database import get_db
from app.auth.dependencies import get_current_agent, verify_admin, require_role
from app.exceptions import BusinessError
from app.services.task_core import task as task_service
from app.models.agent import Agent


router = APIRouter(prefix="/tasks", tags=["Task"])


# ============================================================
# 请求/响应模型
# ============================================================

class TaskCreateRequest(BaseModel):
    name: str = Field(..., description="任务名称")
    description: str = Field("", description="任务描述")
    type: str = Field("once", description="类型: once/recurring")


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    type: str
    status: str
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None


class TaskStatusRequest(BaseModel):
    status: str = Field(..., description="状态: planning/active/in_progress/completed/archived/cancelled")


class TaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")


class ModuleCreateRequest(BaseModel):
    name: str = Field(..., description="模块名称")
    description: str = Field("", description="模块描述")


class ModuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    name: str
    description: str


# ============================================================
# 任务路由
# ============================================================

@router.post("", response_model=TaskResponse, summary="创建任务")
async def create_task(
    req: TaskCreateRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """规划师创建任务"""
    try:
        task = task_service.create_task(db, req.name, req.description, req.type)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return task


@router.get("", summary="查看任务列表")
async def list_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    查看所有任务，可按状态过滤。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    from app.services.pagination import paginate
    query = db.query(task_service.Task)
    if status:
        query = query.filter(task_service.Task.status == status)
    query = query.order_by(task_service.Task.created_at.desc())
    return paginate(query, page=page, page_size=page_size)


@router.get("/{task_id}", response_model=TaskResponse, summary="查看任务详情")
async def get_task(
    task_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取单个任务详情"""
    task = task_service.get_task(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.put("/{task_id}/status", response_model=TaskResponse, summary="更新任务状态")
async def update_task_status(
    task_id: str,
    req: TaskStatusRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """更新任务状态（如 planning → active）"""
    try:
        task = task_service.update_task_status(db, task_id, req.status)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return task


@router.put("/{task_id}", response_model=TaskResponse, summary="编辑任务")
async def update_task(
    task_id: str,
    req: TaskUpdateRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """编辑任务名称/描述（仅 planning/active 状态可编辑）"""
    try:
        task = task_service.update_task(db, task_id, name=req.name, description=req.description)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return task


@router.post("/{task_id}/cancel", response_model=TaskResponse, summary="取消任务")
async def cancel_task(
    task_id: str,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """取消任务（已完成/已归档/已取消的不能取消）"""
    try:
        task = task_service.cancel_task(db, task_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return task


# ============================================================
# 模块路由（挂在 /tasks/{task_id}/modules 下）
# ============================================================

@router.post("/{task_id}/modules", response_model=ModuleResponse, summary="创建模块")
async def create_module(
    task_id: str,
    req: ModuleCreateRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """在任务下创建模块"""
    try:
        module = task_service.create_module(db, task_id, req.name, req.description)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return module


@router.get("/{task_id}/modules", response_model=List[ModuleResponse], summary="查看模块列表")
async def list_modules(
    task_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """查看任务下的所有模块"""
    return task_service.list_modules(db, task_id)
