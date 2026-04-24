"""
活动日志路由 — Agent 写日志 + 查询日志
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt

from app.database import get_db
from app.auth.dependencies import get_current_agent
from app.exceptions import BusinessError
from app.services import agent_runtime as activity_log_service
from app.models.agent import Agent


router = APIRouter(prefix="/logs", tags=["ActivityLog"])


# ============================================================
# 请求/响应模型
# ============================================================

class LogCreateRequest(BaseModel):
    sub_task_id: Optional[str] = Field(None, description="关联子任务 ID")
    action: str = Field(..., description=f"操作类型，允许: {', '.join(sorted(activity_log_service.VALID_ACTIONS))}")
    summary: str = Field("", description="操作摘要：做了什么、结果是什么")
    session_id: Optional[str] = Field(None, description="OpenClaw 会话 ID")


class LogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    sub_task_id: Optional[str]
    action: str
    summary: str
    session_id: Optional[str]
    created_at: Optional[dt] = None


# ============================================================
# 路由
# ============================================================

@router.post("", response_model=LogResponse, summary="写入活动日志")
async def create_log(
    req: LogCreateRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 写入一条活动日志"""
    try:
        return activity_log_service.create_activity_log(
            db,
            agent_id=agent.id,
            action=req.action,
            summary=req.summary,
            sub_task_id=req.sub_task_id,
            session_id=req.session_id,
        )
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get("", response_model=List[LogResponse], summary="查看活动日志")
async def list_logs(
    sub_task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    action: Optional[str] = None,
    days: Optional[int] = activity_log_service.DEFAULT_DAYS,
    limit: Optional[int] = activity_log_service.DEFAULT_LIMIT,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """查看活动日志，支持按子任务/Agent/操作类型/天数/条数过滤"""
    return activity_log_service.list_activity_logs(
        db, sub_task_id=sub_task_id, agent_id=agent_id,
        action=action, days=days, limit=limit,
    )


@router.get("/mine", response_model=List[LogResponse], summary="查看我的活动日志")
async def get_my_logs(
    action: Optional[str] = None,
    days: Optional[int] = activity_log_service.DEFAULT_DAYS,
    limit: Optional[int] = activity_log_service.DEFAULT_LIMIT,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 查看自己的活动日志，可选按操作类型、天数和条数过滤"""
    return activity_log_service.list_my_activity_logs(
        db, agent.id, action=action, days=days, limit=limit,
    )
