"""
活动流路由 — 公开展示页 API（受 public_feed 开关控制）
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime as dt, timedelta

from app.database import get_db
from app.config import config
from app.models.request_log import RequestLog
from app.models.agent import Agent
from app.models.sub_task import SubTask
from app.models.module import Module


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

    query = db.query(RequestLog)

    if after:
        try:
            after_dt = dt.fromisoformat(after)
            query = query.filter(RequestLog.timestamp > after_dt)
        except ValueError:
            raise HTTPException(400, "after 参数格式错误，需要 ISO 格式时间")

    if agent_id:
        query = query.filter(RequestLog.agent_id == agent_id)

    return query.order_by(RequestLog.timestamp.desc()).limit(limit).all()


@router.get("/agents", response_model=List[FeedAgentResponse], summary="获取 Agent 列表")
async def feed_agents(db: Session = Depends(get_db)):
    """获取所有 Agent 列表（受 public_feed 开关控制）"""
    _check_feed_enabled()
    return db.query(Agent).order_by(Agent.total_score.desc()).all()


@router.get("/agent-summary", response_model=List[AgentSummaryResponse], summary="获取 Agent 汇总面板数据")
async def feed_agent_summary(db: Session = Depends(get_db)):
    """
    一次返回所有 Agent 的汇总数据：今日统计、当前任务、近期动作。
    用于 Agent 个体卡片渲染。受 public_feed 开关控制。
    """
    _check_feed_enabled()

    agents = db.query(Agent).order_by(Agent.total_score.desc()).all()
    if not agents:
        return []

    today_start = dt.now().replace(hour=0, minute=0, second=0, microsecond=0)
    agent_ids = [a.id for a in agents]

    # ── 批量查询今日请求数 ──
    today_counts = dict(
        db.query(RequestLog.agent_id, func.count(RequestLog.id))
        .filter(RequestLog.agent_id.in_(agent_ids), RequestLog.timestamp >= today_start)
        .group_by(RequestLog.agent_id)
        .all()
    )

    # ── 批量查询今日提交数（path 以 /submit 结尾的 POST）──
    today_submits = dict(
        db.query(RequestLog.agent_id, func.count(RequestLog.id))
        .filter(
            RequestLog.agent_id.in_(agent_ids),
            RequestLog.timestamp >= today_start,
            RequestLog.method == "POST",
            RequestLog.path.like("%/submit"),
        )
        .group_by(RequestLog.agent_id)
        .all()
    )

    # ── 批量查询今日审查数（POST /review-records）──
    today_reviews = dict(
        db.query(RequestLog.agent_id, func.count(RequestLog.id))
        .filter(
            RequestLog.agent_id.in_(agent_ids),
            RequestLog.timestamp >= today_start,
            RequestLog.method == "POST",
            RequestLog.path.like("%/review-records"),
        )
        .group_by(RequestLog.agent_id)
        .all()
    )

    # ── 批量查询当前 in_progress 子任务 ──
    current_tasks_rows = (
        db.query(SubTask.assigned_agent, SubTask.id, SubTask.name, Module.name.label("module_name"))
        .outerjoin(Module, SubTask.module_id == Module.id)
        .filter(
            SubTask.assigned_agent.in_(agent_ids),
            SubTask.status == "in_progress",
        )
        .order_by(SubTask.updated_at.desc())
        .all()
    )
    # 每个 agent 只取第一条（最新的）
    current_tasks: dict[str, SubTaskBrief] = {}
    for row in current_tasks_rows:
        if row.assigned_agent not in current_tasks:
            current_tasks[row.assigned_agent] = SubTaskBrief(
                id=row.id, name=row.name, module_name=row.module_name
            )

    # ── 批量查询近期动作（每人最近 5 条）──
    # 先拿所有人最近的日志，再在 Python 里分组截断
    recent_logs = (
        db.query(RequestLog)
        .filter(RequestLog.agent_id.in_(agent_ids))
        .order_by(RequestLog.timestamp.desc())
        .limit(len(agent_ids) * 5)
        .all()
    )
    recent_by_agent: dict[str, list[RecentAction]] = {}
    for log in recent_logs:
        agent_list = recent_by_agent.setdefault(log.agent_id, [])
        if len(agent_list) < 5:
            agent_list.append(RecentAction(
                method=log.method,
                path=log.path,
                request_body=log.request_body,
                response_status=log.response_status,
                timestamp=log.timestamp,
            ))

    # ── 组装结果 ──
    result = []
    for agent in agents:
        result.append(AgentSummaryResponse(
            id=agent.id,
            name=agent.name,
            role=agent.role,
            total_score=agent.total_score,
            today_request_count=today_counts.get(agent.id, 0),
            today_submit_count=today_submits.get(agent.id, 0),
            today_review_count=today_reviews.get(agent.id, 0),
            current_sub_task=current_tasks.get(agent.id),
            recent_actions=recent_by_agent.get(agent.id, []),
        ))

    return result
