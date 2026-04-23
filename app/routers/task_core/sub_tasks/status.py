"""
子任务路由 — 状态机操作端点
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.auth.dependencies import require_role
from app.exceptions import BusinessError
from app.services.task_core import sub_task as sub_task_service
from app.models.agent import Agent
from .crud import SubTaskResponse


router = APIRouter(prefix="/sub-tasks", tags=["SubTask"])


# ============================================================
# 请求模型（状态操作专用）
# ============================================================

class ClaimRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="OpenClaw 会话 ID")


class StartRequest(BaseModel):
    session_id: Optional[str] = Field(None, description="OpenClaw 会话 ID")


class ReworkRequest(BaseModel):
    rework_agent: Optional[str] = Field(None, description="返工指派的 Agent ID（可选，不填则原 Agent）")


class ReassignRequest(BaseModel):
    agent_id: str = Field(..., description="新分配的 Agent ID")


class SessionUpdateRequest(BaseModel):
    session_id: str = Field(..., description="新的 OpenClaw 会话 ID")


# ============================================================
# 状态机端点
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
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


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
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{sub_task_id}/submit", response_model=SubTaskResponse, summary="提交成果")
async def submit_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("executor")),
    db: Session = Depends(get_db),
):
    """提交成果：in_progress → review"""
    try:
        return sub_task_service.submit_sub_task(db, sub_task_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{sub_task_id}/complete", response_model=SubTaskResponse, summary="审查通过")
async def complete_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("reviewer")),
    db: Session = Depends(get_db),
):
    """审查通过：review → done"""
    try:
        return sub_task_service.complete_sub_task(db, sub_task_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


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
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.post("/{sub_task_id}/block", response_model=SubTaskResponse, summary="标记异常")
async def block_sub_task(
    sub_task_id: str,
    agent: Agent = Depends(require_role("patrol")),
    db: Session = Depends(get_db),
):
    """巡查 Agent 标记异常：→ blocked"""
    try:
        return sub_task_service.block_sub_task(db, sub_task_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


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
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


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
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
