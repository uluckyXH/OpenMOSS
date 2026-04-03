"""
Agent 路由 — 注册、查询、管理
"""
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.auth.dependencies import get_current_agent, verify_admin
from app.services import agent_service
from app.models.agent import Agent
from app.config import config


router = APIRouter(prefix="/agents", tags=["Agent"])


# ============================================================
# 请求/响应模型
# ============================================================

class AgentRegisterRequest(BaseModel):
    name: str = Field(..., description="Agent 名称", max_length=100)
    role: str = Field(..., description="角色: planner/executor/reviewer/patrol")
    description: str = Field("", description="职责简要")


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    role: str
    description: str
    status: str
    total_score: int


class AgentRegisterResponse(BaseModel):
    id: str
    name: str
    role: str
    api_key: str
    message: str = "注册成功，请保存 API Key"


class AgentStatusRequest(BaseModel):
    status: str = Field(..., description="状态: active/disabled")


class AgentHeartbeatResponse(BaseModel):
    agent_id: str
    heartbeat_at: datetime
    heartbeat_ip: Optional[str] = None
    message: str = "心跳已记录"


def _resolve_request_ip(request: Request) -> Optional[str]:
    """按常见代理头顺序解析请求来源 IP。"""
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip() or None

    x_real_ip = request.headers.get("X-Real-IP")
    if x_real_ip:
        return x_real_ip.strip() or None

    if request.client:
        return request.client.host

    return None


# ============================================================
# Agent 自注册（用注册令牌）
# ============================================================

@router.post("/register", response_model=AgentRegisterResponse, summary="Agent 自动注册")
async def register_agent(
    req: AgentRegisterRequest,
    x_registration_token: str = Header(..., alias="X-Registration-Token"),
    db: Session = Depends(get_db),
):
    """Agent 使用注册令牌自注册，获取 API Key"""
    if not config.allow_registration:
        raise HTTPException(status_code=403, detail="Agent 自注册已关闭，请联系管理员创建")
    if x_registration_token != config.registration_token:
        raise HTTPException(status_code=403, detail="注册令牌无效")

    try:
        agent = agent_service.register_agent(db, req.name, req.role, req.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AgentRegisterResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        api_key=agent.api_key,
    )


# ============================================================
# 管理员创建 Agent
# ============================================================

@router.post("", response_model=AgentRegisterResponse, summary="管理员创建 Agent")
async def create_agent(
    req: AgentRegisterRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员直接创建 Agent"""
    try:
        agent = agent_service.register_agent(db, req.name, req.role, req.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return AgentRegisterResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        api_key=agent.api_key,
    )


# ============================================================
# 查询 Agent 列表（Agent 和管理员都可用）
# ============================================================

@router.get("", response_model=List[AgentResponse], summary="查看 Agent 列表")
async def list_agents(
    role: Optional[str] = None,
    status: Optional[str] = None,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """查看已注册的 Agent 列表，可按角色和状态过滤"""
    agents = agent_service.list_agents(db, role=role, status=status)
    return agents


# ============================================================
# 更新 Agent 状态
# ============================================================

@router.put("/{agent_id}/status", response_model=AgentResponse, summary="更新 Agent 状态")
async def update_status(
    agent_id: str,
    req: AgentStatusRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员更新 Agent 状态"""
    try:
        agent = agent_service.update_agent_status(db, agent_id, req.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return agent


@router.post("/me/heartbeat", response_model=AgentHeartbeatResponse, summary="Agent 上报心跳")
async def report_heartbeat(
    request: Request,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """Agent 使用当前 API Key 上报在线心跳。"""
    presence = agent_service.upsert_agent_presence(
        db,
        agent_id=agent.id,
        heartbeat_ip=_resolve_request_ip(request),
    )

    return AgentHeartbeatResponse(
        agent_id=agent.id,
        heartbeat_at=presence.last_heartbeat_at,
        heartbeat_ip=presence.last_heartbeat_ip,
    )


# ============================================================
# Agent 获取自己的 SKILL.md（API Key 已自动填入）
# ============================================================

@router.get("/me/skill", summary="获取角色对应的 SKILL.md")
async def get_my_skill(
    agent: Agent = Depends(get_current_agent),
):
    """根据 Agent 角色返回对应的 SKILL.md，`<注册后填入>` 自动替换为实际 API Key。"""
    from pathlib import Path
    from fastapi.responses import PlainTextResponse

    role = agent.role
    skill_dir = Path(__file__).resolve().parents[2] / "skills" / f"task-{role}-skill"
    skill_path = skill_dir / "SKILL.md"

    if not skill_path.exists():
        raise HTTPException(status_code=404, detail=f"未找到 {role} 角色的 SKILL.md")

    content = skill_path.read_text(encoding="utf-8")

    # 替换 API Key 占位符
    content = content.replace("<注册后填入>", agent.api_key)

    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
