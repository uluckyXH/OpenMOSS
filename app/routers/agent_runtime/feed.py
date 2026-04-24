"""
活动流路由 — 公开展示页 API（受 public_feed 开关控制）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime as dt

from app.database import get_db
from app.config import config
from app.services import agent_runtime as feed_service


router = APIRouter(prefix="/feed", tags=["Feed"])


# ============================================================
# 响应模型
# ============================================================

class FeedStatusResponse(BaseModel):
    enabled: bool


class FeedLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: Optional[dt] = None
    method: str
    path: str
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    agent_role: Optional[str] = None
    request_body: Optional[str] = None
    response_status: Optional[int] = None


class FeedAgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: str
    status: str
    total_score: int
    created_at: Optional[dt] = None


class SubTaskBrief(BaseModel):
    id: str
    name: str
    module_name: Optional[str] = None


class RecentAction(BaseModel):
    method: str
    path: str
    request_body: Optional[str] = None
    response_status: Optional[int] = None
    timestamp: Optional[dt] = None


class AgentSummaryResponse(BaseModel):
    id: str
    name: str
    role: str
    total_score: int
    today_request_count: int
    today_submit_count: int
    today_review_count: int
    current_sub_task: Optional[SubTaskBrief] = None
    recent_actions: List[RecentAction]


# ============================================================
# 开关检查
# ============================================================

def _check_feed_enabled():
    """检查活动流展示页是否启用"""
    if not config.public_feed_enabled:
        raise HTTPException(status_code=403, detail="活动流展示页未启用")


# ============================================================
# 路由
# ============================================================

@router.get("/status", response_model=FeedStatusResponse, summary="展示页开关状态")
async def feed_status():
    """返回活动流展示页是否启用（不受开关限制）"""
    return {"enabled": config.public_feed_enabled}


@router.get("/logs", response_model=List[FeedLogResponse], summary="获取活动日志")
async def feed_logs(
    after: Optional[str] = Query(None, description="增量查询：仅返回此时间之后的记录 (ISO 格式)"),
    agent_id: Optional[str] = Query(None, description="筛选指定 Agent"),
    limit: int = Query(50, ge=1, le=200, description="返回条数"),
    db: Session = Depends(get_db),
):
    """获取请求日志列表（受 public_feed 开关控制）"""
    _check_feed_enabled()

    after_dt = None
    if after:
        try:
            after_dt = dt.fromisoformat(after)
        except ValueError:
            raise HTTPException(400, "after 参数格式错误，需要 ISO 格式时间")

    return feed_service.list_feed_logs(db, after=after_dt, agent_id=agent_id, limit=limit)


@router.get("/agents", response_model=List[FeedAgentResponse], summary="获取 Agent 列表")
async def feed_agents(db: Session = Depends(get_db)):
    """获取所有 Agent 列表（受 public_feed 开关控制）"""
    _check_feed_enabled()
    return feed_service.list_feed_agents(db)


@router.get("/agent-summary", response_model=List[AgentSummaryResponse], summary="获取 Agent 汇总面板数据")
async def feed_agent_summary(db: Session = Depends(get_db)):
    """
    一次返回所有 Agent 的汇总数据：今日统计、当前任务、近期动作。
    用于 Agent 个体卡片渲染。受 public_feed 开关控制。
    """
    _check_feed_enabled()
    return feed_service.get_feed_agent_summaries(db)
