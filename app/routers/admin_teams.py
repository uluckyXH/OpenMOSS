"""
Admin 端点 - 团队管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.services import team_service


router = APIRouter(prefix="/admin/teams", tags=["Admin Team"])


# ============================================================
# Request/Response Models (inline for simplicity)
# ============================================================

class AdminTeamCreateRequest(BaseModel):
    name: str
    description: str = ""
    working_dir: str = ""


class AdminTeamUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None


class AdminTeamMemberAddRequest(BaseModel):
    agent_id: str


# ============================================================
# 团队管理
# ============================================================

@router.get("")
async def list_teams(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查询团队列表"""
    result = team_service.list_teams(db, page, page_size)
    return result


@router.post("")
async def create_team(
    req: AdminTeamCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建团队"""
    try:
        team = team_service.create_team(db, req.name, req.description, req.working_dir or None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": team.id, "name": team.name, "working_dir": team.working_dir}


@router.get("/{team_id}")
async def get_team(
    team_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取团队详情（含成员）"""
    team = team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    members_data = team_service.get_team_members(db, team_id)
    member_count = len(members_data)

    return {
        "id": team.id,
        "name": team.name,
        "description": team.description,
        "status": team.status,
        "working_dir": team.working_dir,
        "member_count": member_count,
        "members": members_data,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
    }


@router.put("/{team_id}")
async def update_team(
    team_id: str,
    req: AdminTeamUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新团队"""
    try:
        team = team_service.update_team(
            db, team_id,
            name=req.name,
            description=req.description,
            status=req.status,
        )
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": team.id, "name": team.name, "status": team.status}


@router.delete("/{team_id}")
async def delete_team(
    team_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除团队"""
    try:
        team_service.delete_team(db, team_id)
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        if "请先禁用" in str(e):
            raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    return {"message": "团队已删除"}


# ============================================================
# 成员管理
# ============================================================

@router.post("/{team_id}/members")
async def add_member(
    team_id: str,
    req: AdminTeamMemberAddRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """添加团队成员"""
    try:
        member = team_service.add_team_member(db, team_id, req.agent_id)
    except ValueError as e:
        detail = str(e)
        if "不存在" in detail:
            raise HTTPException(status_code=404, detail=detail)
        if "已有归属团队" in detail:
            raise HTTPException(status_code=400, detail=detail)
        if "已禁用" in detail:
            raise HTTPException(status_code=403, detail=detail)
        raise HTTPException(status_code=400, detail=detail)
    return {"agent_id": member.agent_id, "message": "成员已添加"}


@router.delete("/{team_id}/members/{agent_id}")
async def remove_member(
    team_id: str,
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """移除团队成员"""
    try:
        team_service.remove_team_member(db, team_id, agent_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"message": "成员已移除"}


# ============================================================
# 团队介绍
# ============================================================

@router.get("/{team_id}/profile")
async def get_profile(
    team_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取团队介绍"""
    profile = team_service.get_team_profile(db, team_id)
    if not profile:
        return {"content": "", "version": 0}
    return {"content": profile.content, "version": profile.version, "updated_at": profile.updated_at}


@router.put("/{team_id}/profile")
async def update_profile(
    team_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """手动触发团队介绍生成"""
    try:
        profile = team_service.generate_team_profile(db, team_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"version": profile.version}


class AdminProfileUpdateRequest(BaseModel):
    content: str


@router.patch("/{team_id}/profile")
async def update_profile_content(
    team_id: str,
    req: AdminProfileUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新团队介绍内容（管理员手动编辑）"""
    # 先检查团队是否存在
    team = team_service.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="团队不存在")

    profile = team_service.update_team_profile(db, team_id, req.content)
    return {"version": profile.version, "content": profile.content}


# ============================================================
# 模板管理
# ============================================================

@router.get("/template")
async def get_template(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取介绍生成模板"""
    template = team_service.get_template(db)
    return {"content": template.content}


@router.put("/template")
async def update_template(
    req: dict,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新介绍生成模板"""
    template = team_service.update_template(db, req.get("content", ""))
    return {"message": "模板已更新"}


# ============================================================
# 知识经验管理
# ============================================================

class KnowledgeCreate(BaseModel):
    title: str
    content: str
    author_agent_id: Optional[str] = None


class KnowledgeUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


class KnowledgeResponse(BaseModel):
    id: str
    team_id: str
    title: str
    content: str
    author_agent_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/{team_id}/knowledge", summary="获取团队知识列表")
def list_team_knowledge(
    team_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    return team_service.list_knowledge(db, team_id, page, page_size)


@router.post("/{team_id}/knowledge", summary="创建知识", response_model=KnowledgeResponse)
def create_team_knowledge(
    team_id: str,
    data: KnowledgeCreate,
    db: Session = Depends(get_db),
    admin: dict = Depends(verify_admin)
):
    author = data.author_agent_id or f"admin-{admin.get('username', 'unknown')}"
    knowledge = team_service.create_knowledge(db, team_id, author, data.title, data.content)
    return knowledge


@router.get("/{team_id}/knowledge/{knowledge_id}", summary="获取知识详情", response_model=KnowledgeResponse)
def get_team_knowledge(
    team_id: str,
    knowledge_id: str,
    db: Session = Depends(get_db)
):
    knowledge = team_service.get_knowledge(db, knowledge_id)
    if not knowledge or knowledge.team_id != team_id:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return knowledge


@router.put("/{team_id}/knowledge/{knowledge_id}", summary="更新知识", response_model=KnowledgeResponse)
def update_team_knowledge(
    team_id: str,
    knowledge_id: str,
    data: KnowledgeUpdate,
    db: Session = Depends(get_db),
    admin: dict = Depends(verify_admin)
):
    knowledge = team_service.get_knowledge(db, knowledge_id)
    if not knowledge or knowledge.team_id != team_id:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    knowledge = team_service.update_knowledge(db, knowledge_id, data.title, data.content)
    return knowledge


@router.delete("/{team_id}/knowledge/{knowledge_id}", summary="删除知识")
def delete_team_knowledge(
    team_id: str,
    knowledge_id: str,
    db: Session = Depends(get_db),
    admin: dict = Depends(verify_admin)
):
    knowledge = team_service.get_knowledge(db, knowledge_id)
    if not knowledge or knowledge.team_id != team_id:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    team_service.delete_knowledge(db, knowledge_id)
    return {"status": "deleted", "id": knowledge_id}
