"""
子任务路由 — CRUD 端点
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime as dt

from app.database import get_db
from app.auth.dependencies import get_current_agent, require_role
from app.exceptions import BusinessError
from app.services.task_core import sub_task as sub_task_service
from app.services.pagination import paginate
from app.models.agent import Agent


router = APIRouter(prefix="/sub-tasks", tags=["SubTask"])


# ============================================================
# 请求/响应模型
# ============================================================

class SubTaskCreateRequest(BaseModel):
    task_id: str = Field(..., description="所属任务 ID")
    name: str = Field(..., description="子任务名称")
    description: str = Field("", description="具体内容")
    deliverable: str = Field("", description="交付物描述")
    acceptance: str = Field("", description="验收标准")
    priority: str = Field("medium", description="优先级: high/medium/low")
    module_id: Optional[str] = Field(None, description="所属模块 ID（可选）")
    assigned_agent: Optional[str] = Field(None, description="指派 Agent ID（可选）")
    type: str = Field("once", description="类型: once/recurring")


class SubTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str
    module_id: Optional[str]
    name: str
    description: str
    deliverable: str
    acceptance: str
    type: str
    status: str
    priority: str
    assigned_agent: Optional[str]
    current_session_id: Optional[str]
    rework_count: int
    created_at: Optional[dt] = None
    updated_at: Optional[dt] = None
    completed_at: Optional[dt] = None


class SubTaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="子任务名称")
    description: Optional[str] = Field(None, description="具体内容")
    deliverable: Optional[str] = Field(None, description="交付物描述")
    acceptance: Optional[str] = Field(None, description="验收标准")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")


# ============================================================
# CRUD 端点
# ============================================================

@router.post("", response_model=SubTaskResponse, summary="创建子任务")
async def create_sub_task(
    req: SubTaskCreateRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """规划师创建子任务"""
    try:
        sub_task = sub_task_service.create_sub_task(
            db,
            task_id=req.task_id,
            name=req.name,
            description=req.description,
            deliverable=req.deliverable,
            acceptance=req.acceptance,
            priority=req.priority,
            module_id=req.module_id,
            assigned_agent=req.assigned_agent,
            type=req.type,
        )
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return sub_task


@router.get("", summary="查看子任务列表")
async def list_sub_tasks(
    task_id: Optional[str] = None,
    module_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    查看子任务列表，可按任务/模块/状态过滤。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    rows = sub_task_service.list_sub_tasks(db, task_id=task_id, module_id=module_id, status=status)
    # 兼容已有分页接口：当 page_size > 0 时在内存做分页
    if page_size > 0:
        total = len(rows)
        page = max(1, page)
        page_size = min(page_size, 100)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        items = rows[start:start + page_size]
        return {
            "items": items, "total": total, "page": page,
            "page_size": page_size, "total_pages": total_pages,
            "has_more": page < total_pages,
        }
    return {"items": rows, "total": len(rows), "page": 1, "page_size": 0, "total_pages": 1, "has_more": False}


@router.get("/mine", summary="查看我的子任务")
async def get_my_sub_tasks(
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    获取分配给自己的子任务。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    rows = sub_task_service.list_sub_tasks(db, assigned_agent=agent.id, status=status)
    if page_size > 0:
        total = len(rows)
        page = max(1, page)
        page_size = min(page_size, 100)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        items = rows[start:start + page_size]
        return {
            "items": items, "total": total, "page": page,
            "page_size": page_size, "total_pages": total_pages,
            "has_more": page < total_pages,
        }
    return {"items": rows, "total": len(rows), "page": 1, "page_size": 0, "total_pages": 1, "has_more": False}


@router.get("/available", summary="查看待认领子任务")
async def get_available_sub_tasks(
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    获取待认领的子任务（status=pending）。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    rows = sub_task_service.list_sub_tasks(db, status="pending")
    if page_size > 0:
        total = len(rows)
        page = max(1, page)
        page_size = min(page_size, 100)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        items = rows[start:start + page_size]
        return {
            "items": items, "total": total, "page": page,
            "page_size": page_size, "total_pages": total_pages,
            "has_more": page < total_pages,
        }
    return {"items": rows, "total": len(rows), "page": 1, "page_size": 0, "total_pages": 1, "has_more": False}


@router.get("/latest", response_model=SubTaskResponse, summary="获取最新子任务")
async def get_latest_sub_task(
    task_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    快速获取某任务下分配给自己的最新一个子任务。
    适用于执行者唤醒后快速定位当前工作。
    """
    rows = sub_task_service.list_sub_tasks(db, task_id=task_id, assigned_agent=agent.id)
    if not rows:
        raise HTTPException(status_code=404, detail="该任务下没有分配给你的子任务")
    # list_sub_tasks 已按 created_at desc 排序，取第一条
    return rows[0]


@router.get("/{sub_task_id}", response_model=SubTaskResponse, summary="查看子任务详情")
async def get_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取单个子任务详情"""
    sub_task = sub_task_service.get_sub_task(db, sub_task_id)
    if not sub_task:
        raise HTTPException(status_code=404, detail="子任务不存在")
    return sub_task


@router.put("/{sub_task_id}", response_model=SubTaskResponse, summary="编辑子任务")
async def update_sub_task(
    sub_task_id: str,
    req: SubTaskUpdateRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """编辑子任务（仅 pending/assigned 状态可编辑）"""
    try:
        return sub_task_service.update_sub_task(
            db, sub_task_id,
            name=req.name, description=req.description,
            deliverable=req.deliverable, acceptance=req.acceptance,
            priority=req.priority,
        )
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{sub_task_id}/cancel", response_model=SubTaskResponse, summary="取消子任务")
async def cancel_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """取消子任务（已完成/已取消的不能取消）"""
    try:
        return sub_task_service.cancel_sub_task(db, sub_task_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
