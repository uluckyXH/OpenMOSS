"""
活动日志路由 — Agent 写日志 + 查询日志
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt, timedelta
import uuid

from app.database import get_db
from app.auth.dependencies import get_current_agent
from app.models.activity_log import ActivityLog
from app.models.agent import Agent


router = APIRouter(prefix="/logs", tags=["ActivityLog"])


# ============================================================
# 日志 action 白名单
# ============================================================

VALID_ACTIONS = {
    "coding",       # Executor: 执行过程记录
    "delivery",     # Executor: 提交交付物摘要
    "blocked",      # Executor: 遇到阻塞求助
    "reflection",   # 所有角色: 自省笔记
    "plan",         # Planner: 规划/分配记录
    "review",       # Reviewer: 审查过程记录
    "patrol",       # Patrol: 巡查记录
}

MAX_DAYS = 60
DEFAULT_DAYS = 7
DEFAULT_LIMIT = 20
MAX_LIMIT = 500


# ============================================================
# 请求/响应模型
# ============================================================

class LogCreateRequest(BaseModel):
    sub_task_id: Optional[str] = Field(None, description="关联子任务 ID")
    action: str = Field(..., description=f"操作类型，允许: {', '.join(sorted(VALID_ACTIONS))}")
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

def _apply_days_filter(query, days: int):
    """按天数过滤日志"""
    if days is not None:
        days = min(max(days, 1), MAX_DAYS)
        cutoff = dt.now() - timedelta(days=days)
        query = query.filter(ActivityLog.created_at >= cutoff)
    return query


@router.post("", response_model=LogResponse, summary="写入活动日志")
async def create_log(
    req: LogCreateRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 写入一条活动日志"""
    if req.action not in VALID_ACTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"无效的 action '{req.action}'，允许: {', '.join(sorted(VALID_ACTIONS))}"
        )

    log = ActivityLog(
        id=str(uuid.uuid4()),
        agent_id=agent.id,
        sub_task_id=req.sub_task_id,
        action=req.action,
        summary=req.summary,
        session_id=req.session_id,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=List[LogResponse], summary="查看活动日志")
async def list_logs(
    sub_task_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    action: Optional[str] = None,
    days: Optional[int] = DEFAULT_DAYS,
    limit: Optional[int] = DEFAULT_LIMIT,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """查看活动日志，支持按子任务/Agent/操作类型/天数/条数过滤"""
    query = db.query(ActivityLog)
    if sub_task_id:
        query = query.filter(ActivityLog.sub_task_id == sub_task_id)
    if agent_id:
        query = query.filter(ActivityLog.agent_id == agent_id)
    if action:
        query = query.filter(ActivityLog.action == action)
    query = _apply_days_filter(query, days)
    actual_limit = min(max(limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    return query.order_by(ActivityLog.created_at.desc()).limit(actual_limit).all()


@router.get("/mine", response_model=List[LogResponse], summary="查看我的活动日志")
async def get_my_logs(
    action: Optional[str] = None,
    days: Optional[int] = DEFAULT_DAYS,
    limit: Optional[int] = DEFAULT_LIMIT,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 查看自己的活动日志，可选按操作类型、天数和条数过滤"""
    query = db.query(ActivityLog).filter(ActivityLog.agent_id == agent.id)
    if action:
        query = query.filter(ActivityLog.action == action)
    query = _apply_days_filter(query, days)
    actual_limit = min(max(limit or DEFAULT_LIMIT, 1), MAX_LIMIT)
    return query.order_by(ActivityLog.created_at.desc()).limit(actual_limit).all()
