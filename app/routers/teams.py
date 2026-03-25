"""
Agent 端点 - 团队相关
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.auth.dependencies import get_current_agent
from app.models.agent import Agent
from app.services import team_service


router = APIRouter(prefix="/teams", tags=["Agent Team"])


class TeamInfoResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str


class TeamProfileContentResponse(BaseModel):
    content: str
    version: int


class AgentTeamIntroRequest(BaseModel):
    """Agent 提交自我介绍请求"""
    self_introduction: str


@router.get("/me", response_model=TeamInfoResponse, summary="获取所属团队信息")
async def get_my_team(
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取当前 Agent 所属团队信息"""
    team = team_service.get_agent_team(db, agent.id)
    if not team:
        raise HTTPException(status_code=404, detail="您尚未加入任何团队")
    if team.status == "disabled":
        raise HTTPException(status_code=403, detail="团队已禁用，无法访问")
    return TeamInfoResponse(id=team.id, name=team.name, description=team.description, status=team.status)


@router.get("/me/profile", response_model=TeamProfileContentResponse, summary="获取团队介绍")
async def get_team_profile(
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取团队介绍"""
    team = team_service.get_agent_team(db, agent.id)
    if not team:
        raise HTTPException(status_code=404, detail="您尚未加入任何团队")
    if team.status == "disabled":
        raise HTTPException(status_code=403, detail="团队已禁用，无法访问")

    profile = team_service.get_team_profile(db, team.id)
    if not profile:
        return TeamProfileContentResponse(content="", version=0)

    return TeamProfileContentResponse(content=profile.content, version=profile.version)


@router.put("/me/intro", summary="提交自我介绍")
async def update_self_introduction(
    req: AgentTeamIntroRequest,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """提交自我介绍"""
    team = team_service.get_agent_team(db, agent.id)
    if not team:
        raise HTTPException(status_code=404, detail="您尚未加入任何团队")
    if team.status == "disabled":
        raise HTTPException(status_code=403, detail="团队已禁用，无法提交自我介绍")

    try:
        team_service.update_agent_intro(db, agent.id, req.self_introduction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"message": "自我介绍已更新"}


# === 知识经验 ===

class KnowledgeCreate(BaseModel):
    title: str
    content: str


class KnowledgeUploadResponse(BaseModel):
    id: str
    title: str
    content: str
    author_agent_id: str
    team_id: str
    created_at: datetime
    updated_at: datetime


@router.get("/my/knowledge", summary="获取本团队知识列表")
def get_my_team_knowledge(
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_agent)
):
    """获取当前 Agent 所属团队的知识列表"""
    team = team_service.get_agent_team(db, current_agent["agent_id"])
    if not team:
        raise HTTPException(status_code=404, detail="未找到所属团队")
    if team.status == "disabled":
        raise HTTPException(status_code=403, detail="团队已禁用，无法访问")
    return team_service.get_team_knowledge(db, team.id, current_agent["agent_id"])


@router.get("/my/knowledge/{knowledge_id}", summary="获取知识详情")
def get_knowledge_detail(
    knowledge_id: str,
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_agent)
):
    """获取单条知识详情"""
    knowledge = team_service.get_knowledge(db, knowledge_id)
    if not knowledge:
        raise HTTPException(status_code=404, detail="知识不存在")
    # 验证 agent 属于知识所在团队
    team = team_service.get_agent_team(db, current_agent["agent_id"])
    if not team or team.id != knowledge.team_id:
        raise HTTPException(status_code=403, detail="无权限访问该知识")
    if team.status == "disabled":
        raise HTTPException(status_code=403, detail="团队已禁用，无法访问")
    return knowledge


@router.post("/my/knowledge", summary="上传知识到本团队", response_model=KnowledgeUploadResponse)
def upload_knowledge(
    data: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_agent)
):
    """向所属团队上传新知识"""
    team = team_service.get_agent_team(db, current_agent["agent_id"])
    if not team:
        raise HTTPException(status_code=404, detail="未找到所属团队")
    if team.status == "disabled":
        raise HTTPException(status_code=403, detail="团队已禁用，无法上传知识")
    knowledge = team_service.create_knowledge(
        db, team.id, current_agent["agent_id"], data.title, data.content
    )
    return {
        "id": knowledge.id,
        "title": knowledge.title,
        "content": knowledge.content,
        "author_agent_id": knowledge.author_agent_id,
        "team_id": knowledge.team_id,
        "created_at": knowledge.created_at,
        "updated_at": knowledge.updated_at
    }


@router.get("/my/knowledge/search", summary="跨团队搜索知识")
def search_all_knowledge(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_agent: dict = Depends(get_current_agent)
):
    """跨团队搜索知识，返回带团队来源标识"""
    # 验证是已注册的 agent
    agent = db.query(Agent).filter(Agent.id == current_agent["agent_id"]).first()
    if not agent:
        raise HTTPException(status_code=403, detail="未注册 Agent")
    return team_service.search_knowledge(db, q, page, page_size)
