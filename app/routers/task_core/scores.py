"""
积分路由 — 积分概要 + 积分记录查询
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt

from app.database import get_db
from app.auth.dependencies import get_current_agent, verify_admin
from app.exceptions import BusinessError
from app.services.task_core import reward as reward_service
from app.models.agent import Agent


router = APIRouter(prefix="/scores", tags=["Score"])


# ============================================================
# 响应模型
# ============================================================

class ScoreSummaryResponse(BaseModel):
    agent_id: str
    agent_name: str
    total_score: int
    rank: int
    total_agents: int
    reward_count: int
    penalty_count: int
    total_records: int


class RewardLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_id: str
    sub_task_id: Optional[str]
    reason: str
    score_delta: int
    created_at: Optional[dt] = None


class LeaderboardItem(BaseModel):
    rank: int
    agent_id: str
    agent_name: str
    role: str
    total_score: int


# ============================================================
# 路由（注意：静态路径必须在动态路径 /{agent_id} 之前）
# ============================================================

@router.get("/leaderboard", response_model=List[LeaderboardItem], summary="积分排行榜")
async def get_leaderboard(
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """查看积分排行榜（所有 Agent 按 total_score 降序）"""
    return reward_service.get_leaderboard(db)


@router.get("/me", response_model=ScoreSummaryResponse, summary="查看我的积分")
async def get_my_score(
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 查看自己的积分概要"""
    return reward_service.get_agent_score(db, agent.id)


@router.get("/{agent_id}", response_model=ScoreSummaryResponse, summary="查看 Agent 积分")
async def get_agent_score(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员查看指定 Agent 积分"""
    try:
        return reward_service.get_agent_score(db, agent_id)
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@router.get("/me/logs", summary="查看我的积分明细")
async def get_my_reward_logs(
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    Agent 查看自己的积分明细。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    return reward_service.list_reward_logs_paginated(db, agent.id, page=page, page_size=page_size)


@router.get("/{agent_id}/logs", summary="查看积分明细")
async def get_agent_reward_logs(
    agent_id: str,
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    查看 Agent 的积分变更明细。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    return reward_service.list_reward_logs_paginated(db, agent_id, page=page, page_size=page_size)


# ============================================================
# 手动调整积分
# ============================================================

class ScoreAdjustRequest(BaseModel):
    agent_id: str = Field(..., description="目标 Agent ID")
    score_delta: int = Field(..., description="积分变化量（正数加分，负数扣分）")
    reason: str = Field(..., description="调整原因")
    sub_task_id: Optional[str] = Field(None, description="关联子任务 ID（可选）")


@router.post("/adjust", response_model=RewardLogResponse, summary="手动调整积分")
async def adjust_score(
    req: ScoreAdjustRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Reviewer 按用户要求手动给 Agent 加分或扣分"""
    if agent.role not in ("reviewer", "planner"):
        raise HTTPException(status_code=403, detail="仅 reviewer 和 planner 角色可调整积分")
    if req.score_delta == 0:
        raise HTTPException(status_code=400, detail="score_delta 不能为 0")

    try:
        log = reward_service.add_reward(
            db,
            agent_id=req.agent_id,
            reason=f"[手动调整] {req.reason}（操作者：{agent.name}）",
            score_delta=req.score_delta,
            sub_task_id=req.sub_task_id,
        )
        return log
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
