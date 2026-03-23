"""
子任务路由 — CRUD + 状态操作
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt

from app.database import get_db
from app.auth.dependencies import get_current_agent, verify_admin, require_role
from app.services import sub_task_service
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

    class Config:
        from_attributes = True


class ClaimRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="OpenClaw 会话 ID")


class StartRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="OpenClaw 会话 ID")


class ReworkRequest(BaseModel):
    rework_agent: Optional[str] = Field(None, description="返工指派的 Agent ID（可选，不填则原 Agent）")


class ReassignRequest(BaseModel):
    agent_id: str = Field(..., description="新分配的 Agent ID")


class SubTaskUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, description="子任务名称")
    description: Optional[str] = Field(None, description="具体内容")
    deliverable: Optional[str] = Field(None, description="交付物描述")
    acceptance: Optional[str] = Field(None, description="验收标准")
    priority: Optional[str] = Field(None, description="优先级: high/medium/low")
    type: Optional[str] = Field(None, description="类型: once/recurring")
    remarks: Optional[str] = Field(None, description="备注，如取消原因")
    status: Optional[str] = Field(None, description="状态: pending/assigned")
    assigned_agent: Optional[str] = Field(None, description="指派 Agent ID")
    recurring_config: Optional[dict] = Field(None, description="循环任务配置")


# ============================================================
# CRUD
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
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
    from app.services.pagination import paginate
    from app.models.sub_task import SubTask
    query = db.query(SubTask)
    if task_id:
        query = query.filter(SubTask.task_id == task_id)
    if module_id:
        query = query.filter(SubTask.module_id == module_id)
    if status:
        query = query.filter(SubTask.status == status)
    query = query.order_by(SubTask.created_at.desc())
    return paginate(query, page=page, page_size=page_size)


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
    from app.services.pagination import paginate
    from app.models.sub_task import SubTask
    query = db.query(SubTask).filter(SubTask.assigned_agent == agent.id)
    if status:
        query = query.filter(SubTask.status == status)
    query = query.order_by(SubTask.created_at.desc())
    return paginate(query, page=page, page_size=page_size)


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
    from app.services.pagination import paginate
    from app.models.sub_task import SubTask
    query = db.query(SubTask).filter(SubTask.status == "pending")
    query = query.order_by(SubTask.created_at.desc())
    return paginate(query, page=page, page_size=page_size)


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
    from app.models.sub_task import SubTask
    sub_task = (
        db.query(SubTask)
        .filter(SubTask.task_id == task_id, SubTask.assigned_agent == agent.id)
        .order_by(SubTask.updated_at.desc())
        .first()
    )
    if not sub_task:
        raise HTTPException(status_code=404, detail="该任务下没有分配给你的子任务")
    return sub_task


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


# ============================================================
# 状态操作
# ============================================================

@router.post("/{sub_task_id}/claim", response_model=SubTaskResponse, summary="认领子任务")
async def claim_sub_task(
    sub_task_id: str,
    req: ClaimRequest = ClaimRequest(),
    agent: Agent = Depends(require_role("executor")),
    db: Session = Depends(get_db),
):
    """执行者认领子任务：pending → assigned"""
    try:
        return sub_task_service.claim_sub_task(db, sub_task_id, agent.id, req.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/start", response_model=SubTaskResponse, summary="开始执行")
async def start_sub_task(
    sub_task_id: str,
    req: StartRequest = StartRequest(),
    agent: Agent = Depends(require_role("executor")),
    db: Session = Depends(get_db),
):
    """开始执行子任务：assigned/rework → in_progress"""
    try:
        return sub_task_service.start_sub_task(db, sub_task_id, req.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/submit", response_model=SubTaskResponse, summary="提交成果")
async def submit_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("executor")),
    db: Session = Depends(get_db),
):
    """提交成果：in_progress → review"""
    try:
        return sub_task_service.submit_sub_task(db, sub_task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/complete", response_model=SubTaskResponse, summary="审查通过")
async def complete_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("reviewer")),
    db: Session = Depends(get_db),
):
    """审查通过：review → done"""
    try:
        return sub_task_service.complete_sub_task(db, sub_task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/rework", response_model=SubTaskResponse, summary="驳回返工")
async def rework_sub_task(
    sub_task_id: str,
    req: ReworkRequest = ReworkRequest(),
    agent: Agent = Depends(require_role("reviewer")),
    db: Session = Depends(get_db),
):
    """驳回返工：review → rework"""
    try:
        return sub_task_service.rework_sub_task(db, sub_task_id, req.rework_agent)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/block", response_model=SubTaskResponse, summary="标记异常")
async def block_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("patrol")),
    db: Session = Depends(get_db),
):
    """巡查 Agent 标记异常：→ blocked"""
    try:
        return sub_task_service.block_sub_task(db, sub_task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/reassign", response_model=SubTaskResponse, summary="重新分配")
async def reassign_sub_task(
    sub_task_id: str,
    req: ReassignRequest,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """规划师重新分配：blocked → assigned"""
    try:
        return sub_task_service.reassign_sub_task(db, sub_task_id, req.agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


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
            priority=req.priority, type=req.type, remarks=req.remarks,
            status=req.status, assigned_agent=req.assigned_agent,
            recurring_config=req.recurring_config,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{sub_task_id}/cancel", response_model=SubTaskResponse, summary="取消子任务")
async def cancel_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("planner")),
    db: Session = Depends(get_db),
):
    """取消子任务（已完成/已取消的不能取消）"""
    try:
        return sub_task_service.cancel_sub_task(db, sub_task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class SessionUpdateRequest(BaseModel):
    session_id: str = Field(..., description="新的 OpenClaw 会话 ID")


@router.post("/{sub_task_id}/session", response_model=SubTaskResponse, summary="更新会话 ID")
async def update_session(
    sub_task_id: str,
    req: SessionUpdateRequest,
    agent: Agent = Depends(require_role("executor")),
    db: Session = Depends(get_db),
):
    """更新 in_progress 子任务的当前会话 ID（cron 唤醒后绑定新会话）"""
    try:
        return sub_task_service.update_session(db, sub_task_id, req.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
