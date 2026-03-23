# Team Space Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Team Space feature - enabling multi-agent collaboration through standardized team management, member self-introductions, and automatic SOUL.md updates.

**Architecture:** Backend FastAPI with SQLAlchemy ORM, Frontend Vue 3 with TypeScript. Follow existing OpenMOSS patterns for models, services, routers, and API clients.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy, Vue 3, TypeScript, Pinia, Axios

---

## File Structure Overview

| Layer | Files | Responsibility |
|-------|-------|----------------|
| Models | `app/models/team.py` | Database models: Team, TeamMember, TeamProfile, TeamProfileTemplate |
| Schemas | `app/schemas/team.py` | Request/Response models |
| Services | `app/services/team_service.py` | Business logic: CRUD, profile generation, task triggers |
| Routers | `app/routers/teams.py` | Agent endpoints: `/api/teams/*` |
| Routers | `app/routers/admin_teams.py` | Admin endpoints: `/api/admin/teams/*` |
| Main | `app/main.py` | Register routers |
| Frontend API | `webui/src/api/client.ts` | Add teamApi, adminTeamApi |
| Frontend View | `webui/src/views/TeamsView.vue` | Team management UI |
| Frontend Router | `webui/src/router/index.ts` | Add `/teams` route |
| Frontend Layout | `webui/src/views/AppLayout.vue` | Add Teams to navigation |

---

## Chunk 1: Backend Data Models

### Task 1: Create Team Models

**Files:**
- Create: `app/models/team.py`
- Modify: `app/database.py` (import models)

- [ ] **Step 1: Write the Team models**

```python
"""
Team Space 数据模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, Index, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Team(Base):
    """团队"""
    __tablename__ = "team"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, unique=True, comment="团队名称")
    description = Column(Text, default="", comment="团队描述")
    status = Column(String(20), default="active", index=True, comment="状态: active/disabled")
    created_at = Column(DateTime, default=datetime.now, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")
    profile = relationship("TeamProfile", back_populates="team", uselist=False, cascade="all, delete-orphan")


class TeamMember(Base):
    """团队成员"""
    __tablename__ = "team_member"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("team.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_id = Column(String(36), nullable=False, index=True)
    self_introduction = Column(Text, default=None, comment="自我介绍内容，NULL 表示未完成")
    added_at = Column(DateTime, default=datetime.now, comment="加入时间")

    # 联合唯一索引
    __table_args__ = (
        Index("ix_team_member_team_agent", "team_id", "agent_id", unique=True),
    )

    # 关系
    team = relationship("Team", back_populates="members")


class TeamProfile(Base):
    """团队介绍文件"""
    __tablename__ = "team_profile"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id = Column(String(36), ForeignKey("team.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    content = Column(Text, default="", comment="完整的团队介绍 markdown")
    version = Column(Integer, default=1, comment="版本号，每次更新 +1")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    # 关系
    team = relationship("Team", back_populates="profile")


class TeamProfileTemplate(Base):
    """介绍生成模板"""
    __tablename__ = "team_profile_template"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    content = Column(Text, nullable=False, default="", comment="jinja2 模板")
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间")

    @staticmethod
    def get_default_template() -> str:
        """获取默认模板"""
        return """# {{team_name}} 团队介绍

## 团队简介
{{team_description}}

## 团队成员
{{members}}

## 加入我们
如需与本团队合作，请联系团队负责人。
"""
```

- [ ] **Step 2: Update models/__init__.py to export models**

```python
"""
OpenMOSS 数据模型包
"""
from app.models.request_log import RequestLog  # noqa: F401
from app.models.team import Team, TeamMember, TeamProfile, TeamProfileTemplate  # 新增
```

---

## Chunk 2: Backend Schemas

### Task 2: Create Team Schemas

**Files:**
- Create: `app/schemas/team.py`

- [ ] **Step 1: Write the Team schemas**

```python
"""
Team Space 请求/响应模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ============================================================
# Admin API - 请求模型
# ============================================================

class AdminTeamCreateRequest(BaseModel):
    """创建团队请求"""
    name: str = Field(..., description="团队名称", max_length=100)
    description: str = Field("", description="团队描述")


class AdminTeamUpdateRequest(BaseModel):
    """更新团队请求"""
    name: Optional[str] = Field(None, description="团队名称", max_length=100)
    description: Optional[str] = Field(None, description="团队描述")
    status: Optional[str] = Field(None, description="状态: active/disabled")


class AdminTeamMemberAddRequest(BaseModel):
    """添加成员请求"""
    agent_id: str = Field(..., description="Agent ID")


# ============================================================
# Admin API - 响应模型
# ============================================================

class AdminTeamMemberItem(BaseModel):
    """团队成员（管理员视图）"""
    id: str
    agent_id: str
    agent_name: str
    role: str
    self_introduction: Optional[str]
    added_at: datetime

    class Config:
        from_attributes = True


class AdminTeamDetail(BaseModel):
    """团队详情（管理员视图）"""
    id: str
    name: str
    description: str
    status: str
    member_count: int
    members: List[AdminTeamMemberItem]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminTeamItem(BaseModel):
    """团队列表项（管理员视图）"""
    id: str
    name: str
    description: str
    status: str
    member_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AdminTeamPageResponse(BaseModel):
    """团队分页响应"""
    items: List[AdminTeamItem]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# Agent API - 响应模型
# ============================================================

class AgentTeamInfo(BaseModel):
    """Agent 视角的团队信息"""
    id: str
    name: str
    description: str
    status: str

    class Config:
        from_attributes = True


class AgentTeamIntroRequest(BaseModel):
    """Agent 提交自我介绍请求"""
    self_introduction: str = Field(..., description="自我介绍内容")


class AgentTeamProfileResponse(BaseModel):
    """团队介绍响应"""
    content: str
    version: int
    updated_at: datetime
```

---

## Chunk 3: Backend Service Layer

### Task 3: Create Team Service

**Files:**
- Create: `app/services/team_service.py`

- [ ] **Step 1: Write the Team service**

```python
"""
Team Space 业务逻辑
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.team import Team, TeamMember, TeamProfile, TeamProfileTemplate
from app.models.agent import Agent


# ============================================================
# 团队 CRUD
# ============================================================

def create_team(db: Session, name: str, description: str = "") -> Team:
    """创建团队"""
    # 检查名称重复
    existing = db.query(Team).filter(Team.name == name).first()
    if existing:
        raise ValueError("团队名称已存在")

    team = Team(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        status="active",
    )
    db.add(team)
    db.commit()
    db.refresh(team)

    # 自动创建 TeamProfile
    profile = TeamProfile(
        id=str(uuid.uuid4()),
        team_id=team.id,
        content="",
        version=1,
    )
    db.add(profile)
    db.commit()

    return team


def get_team_by_id(db: Session, team_id: str) -> Team:
    """获取团队详情"""
    return db.query(Team).filter(Team.id == team_id).first()


def list_teams(db: Session, page: int = 1, page_size: int = 20) -> dict:
    """分页查询团队列表"""
    query = db.query(Team)
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    # 补充 member_count
    result = []
    for team in items:
        member_count = db.query(func.count(TeamMember.id)).filter(
            TeamMember.team_id == team.id
        ).scalar() or 0
        result.append({
            "id": team.id,
            "name": team.name,
            "description": team.description,
            "status": team.status,
            "member_count": member_count,
            "created_at": team.created_at,
            "updated_at": team.updated_at,
        })

    return {
        "items": result,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


def update_team(db: Session, team_id: str, name: str = None, description: str = None, status: str = None) -> Team:
    """更新团队"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("团队不存在")

    if name and name != team.name:
        # 检查名称重复
        existing = db.query(Team).filter(Team.name == name, Team.id != team_id).first()
        if existing:
            raise ValueError("团队名称已存在")
        team.name = name

    if description is not None:
        team.description = description

    if status and status in ("active", "disabled"):
        team.status = status

    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team_id: str) -> None:
    """删除团队"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("团队不存在")

    if team.status == "active":
        raise ValueError("请先禁用团队再删除")

    db.delete(team)
    db.commit()


# ============================================================
# 成员管理
# ============================================================

def add_team_member(db: Session, team_id: str, agent_id: str) -> TeamMember:
    """添加团队成员"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("团队不存在")

    if team.status == "disabled":
        raise ValueError("团队已禁用，无法添加成员")

    # 检查 Agent 是否已存在
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ValueError("Agent 不存在")

    # 检查 Agent 是否已有团队
    existing = db.query(TeamMember).filter(TeamMember.agent_id == agent_id).first()
    if existing:
        raise ValueError("该 Agent 已有归属团队")

    member = TeamMember(
        id=str(uuid.uuid4()),
        team_id=team_id,
        agent_id=agent_id,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    # 触发自我介绍任务（由调用方创建 SubTask）

    return member


def remove_team_member(db: Session, team_id: str, agent_id: str) -> None:
    """移除团队成员"""
    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.agent_id == agent_id,
    ).first()
    if not member:
        raise ValueError("成员不存在")

    db.delete(member)
    db.commit()

    # 重新生成团队介绍（如果还有成员）
    generate_team_profile(db, team_id)


def get_team_members(db: Session, team_id: str) -> list:
    """获取团队成员列表"""
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    result = []
    for m in members:
        agent = db.query(Agent).filter(Agent.id == m.agent_id).first()
        result.append({
            "id": m.id,
            "agent_id": m.agent_id,
            "agent_name": agent.name if agent else "未知",
            "role": agent.role if agent else "未知",
            "self_introduction": m.self_introduction,
            "added_at": m.added_at,
        })
    return result


# ============================================================
# Agent 端点
# ============================================================

def get_agent_team(db: Session, agent_id: str) -> Team:
    """获取 Agent 所属团队"""
    member = db.query(TeamMember).filter(TeamMember.agent_id == agent_id).first()
    if not member:
        return None

    team = db.query(Team).filter(Team.id == member.team_id).first()
    return team


def update_agent_intro(db: Session, agent_id: str, self_introduction: str) -> TeamMember:
    """更新 Agent 自我介绍"""
    member = db.query(TeamMember).filter(TeamMember.agent_id == agent_id).first()
    if not member:
        raise ValueError("您尚未加入任何团队")

    team = db.query(Team).filter(Team.id == member.team_id).first()
    if team.status == "disabled":
        raise ValueError("团队已禁用，无法更新自我介绍")

    member.self_introduction = self_introduction
    db.commit()
    db.refresh(member)

    # 重新生成团队介绍
    generate_team_profile(db, team.id)

    return member


# ============================================================
# 团队介绍生成
# ============================================================

def generate_team_profile(db: Session, team_id: str) -> TeamProfile:
    """生成团队介绍内容"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("团队不存在")

    # 获取模板
    template_obj = db.query(TeamProfileTemplate).first()
    template = template_obj.content if template_obj else TeamProfileTemplate.get_default_template()

    # 获取成员
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()

    # 生成成员介绍
    member_blocks = []
    for m in members:
        agent = db.query(Agent).filter(Agent.id == m.agent_id).first()
        if m.self_introduction:
            member_blocks.append(m.self_introduction)
        else:
            agent_name = agent.name if agent else "未知"
            member_blocks.append(f"**{agent_name}** - 自我介绍待完成")

    # 渲染模板
    rendered = template.replace("{{team_name}}", team.name)
    rendered = rendered.replace("{{team_description}}", team.description or "暂无描述")
    rendered = rendered.replace("{{members}}", "\n\n".join(member_blocks))

    # 更新或创建 TeamProfile
    profile = db.query(TeamProfile).filter(TeamProfile.team_id == team_id).first()
    if profile:
        profile.content = rendered
        profile.version += 1
    else:
        profile = TeamProfile(
            id=str(uuid.uuid4()),
            team_id=team_id,
            content=rendered,
            version=1,
        )
        db.add(profile)

    db.commit()
    db.refresh(profile)
    return profile


def get_team_profile(db: Session, team_id: str) -> TeamProfile:
    """获取团队介绍"""
    return db.query(TeamProfile).filter(TeamProfile.team_id == team_id).first()


# ============================================================
# 模板管理
# ============================================================

def get_template(db: Session) -> TeamProfileTemplate:
    """获取模板"""
    template = db.query(TeamProfileTemplate).first()
    if not template:
        # 首次启动时创建默认模板
        template = TeamProfileTemplate(
            id=str(uuid.uuid4()),
            content=TeamProfileTemplate.get_default_template(),
        )
        db.add(template)
        db.commit()
        db.refresh(template)
    return template


def update_template(db: Session, content: str) -> TeamProfileTemplate:
    """更新模板"""
    template = db.query(TeamProfileTemplate).first()
    if not template:
        template = TeamProfileTemplate(
            id=str(uuid.uuid4()),
            content=content,
        )
        db.add(template)
    else:
        template.content = content

    db.commit()
    db.refresh(template)
    return template

---

## Chunk 4: Backend Routers

### Task 4: Create Agent Router

**Files:**
- Create: `app/routers/teams.py`

- [ ] **Step 1: Write the Agent Team router**

```python
"""
Agent 端点 - 团队相关
"""
from fastapi import APIRouter, Depends, HTTPException
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
    req: BaseModel,  # 需要定义 request body
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
```

---

### Task 5: Create Admin Router

**Files:**
- Create: `app/routers/admin_teams.py`

- [ ] **Step 1: Write the Admin Team router**

```python
"""
Admin 端点 - 团队管理
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.team import (
    AdminTeamCreateRequest,
    AdminTeamUpdateRequest,
    AdminTeamMemberAddRequest,
    AdminTeamDetail,
    AdminTeamPageResponse,
    AdminTeamItem,
    AdminTeamMemberItem,
)
from app.services import team_service


router = APIRouter(prefix="/admin/teams", tags=["Admin Team"])


# ============================================================
# 团队管理
# ============================================================

@router.get("", response_model=AdminTeamPageResponse, summary="获取团队列表")
async def list_teams(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查询团队列表"""
    result = team_service.list_teams(db, page, page_size)
    items = [AdminTeamItem(**item) for item in result["items"]]
    return AdminTeamPageResponse(
        items=items,
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
        total_pages=result["total_pages"],
    )


@router.post("", summary="创建团队")
async def create_team(
    req: AdminTeamCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建团队"""
    try:
        team = team_service.create_team(db, req.name, req.description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": team.id, "name": team.name}


@router.get("/{team_id}", response_model=AdminTeamDetail, summary="获取团队详情")
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
    members = [AdminTeamMemberItem(**m) for m in members_data]
    member_count = len(members_data)

    return AdminTeamDetail(
        id=team.id,
        name=team.name,
        description=team.description,
        status=team.status,
        member_count=member_count,
        members=members,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


@router.put("/{team_id}", summary="更新团队")
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


@router.delete("/{team_id}", summary="删除团队")
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

@router.post("/{team_id}/members", summary="添加成员")
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


@router.delete("/{team_id}/members/{agent_id}", summary="移除成员")
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

@router.get("/{team_id}/profile", summary="获取团队介绍")
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


@router.put("/{team_id}/profile", summary="手动更新团队介绍")
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


# ============================================================
# 模板管理
# ============================================================

@router.get("/template", summary="获取介绍生成模板")
async def get_template(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取介绍生成模板"""
    template = team_service.get_template(db)
    return {"content": template.content}


@router.put("/template", summary="更新介绍生成模板")
async def update_template(
    req: dict,  # {"content": "..."}
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新介绍生成模板"""
    template = team_service.update_template(db, req.get("content", ""))
    return {"message": "模板已更新"}

---

## Chunk 5: Backend Main Registration

### Task 6: Register routers in main.py

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: Import and register routers**

```python
# 在现有的 include_router 之后添加
from app.routers import teams, admin_teams  # 新增

# 注册路由
app.include_router(teams.router, prefix=API_PREFIX)
app.include_router(admin_teams.router, prefix=API_PREFIX)
```

---

## Chunk 6: Frontend Implementation

### Task 7: Add API Client

**Files:**
- Modify: `webui/src/api/client.ts`

- [ ] **Step 1: Add team API client**

```typescript
// ============================================================
// Team Space API
// ============================================================

// Agent 端点
export const teamApi = {
  getMyTeam: () => api.get('/teams/me'),
  getTeamProfile: () => api.get('/teams/me/profile'),
  updateIntro: (data: { self_introduction: string }) =>
    api.put('/teams/me/intro', data),
}

// Admin 端点
export const adminTeamApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    api.get<AdminPageResponse<AdminTeamItem>>('/admin/teams', { params }),
  get: (teamId: string) => api.get<AdminTeamDetail>(`/admin/teams/${teamId}`),
  create: (data: { name: string; description?: string }) =>
    api.post('/admin/teams', data),
  update: (teamId: string, data: { name?: string; description?: string; status?: string }) =>
    api.put(`/admin/teams/${teamId}`, data),
  delete: (teamId: string) => api.delete(`/admin/teams/${teamId}`),

  // 成员管理
  listMembers: (teamId: string) =>
    api.get(`/admin/teams/${teamId}/members`),
  addMember: (teamId: string, agentId: string) =>
    api.post(`/admin/teams/${teamId}/members`, { agent_id: agentId }),
  removeMember: (teamId: string, agentId: string) =>
    api.delete(`/admin/teams/${teamId}/members/${agentId}`),

  // 团队介绍
  getProfile: (teamId: string) =>
    api.get(`/admin/teams/${teamId}/profile`),
  updateProfile: (teamId: string) =>
    api.put(`/admin/teams/${teamId}/profile`),

  // 模板
  getTemplate: () => api.get('/admin/teams/template'),
  updateTemplate: (content: string) =>
    api.put('/admin/teams/template', { content }),
}

// 类型定义
export interface AdminTeamItem {
  id: string
  name: string
  description: string
  status: string
  member_count: number
  created_at: string
  updated_at: string
}

export interface AdminTeamMemberItem {
  id: string
  agent_id: string
  agent_name: string
  role: string
  self_introduction: string | null
  added_at: string
}

export interface AdminTeamDetail {
  id: string
  name: string
  description: string
  status: string
  member_count: number
  members: AdminTeamMemberItem[]
  created_at: string
  updated_at: string
}
```

### Task 8: Add Router

**Files:**
- Modify: `webui/src/router/index.ts`

- [ ] **Step 1: Add teams route**

```typescript
{
  path: 'teams',
  name: 'teams',
  component: () => import('@/views/TeamsView.vue'),
},
```

### Task 9: Add Navigation

**Files:**
- Modify: `webui/src/views/AppLayout.vue`

- [ ] **Step 1: Add Teams to navigation menu**

```typescript
import { Users } from 'lucide-vue-next'

// 在 menuItems 数组中添加
{ title: '团队空间', icon: Users, path: '/teams' },
```

### Task 10: Create TeamsView

**Files:**
- Create: `webui/src/views/TeamsView.vue`

- [ ] **Step 1: Write the TeamsView component**

```vue
<template>
  <div class="teams-view">
    <header class="page-header">
      <h1>团队空间</h1>
      <div class="header-actions">
        <button @click="showCreateModal = true" class="btn-primary">
          创建团队
        </button>
        <button @click="showTemplateModal = true" class="btn-secondary">
          团队介绍模板
        </button>
      </div>
    </header>

    <!-- 团队列表 -->
    <div class="teams-table">
      <table>
        <thead>
          <tr>
            <th>团队名称</th>
            <th>成员数</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="team in teams" :key="team.id">
            <td>{{ team.name }}</td>
            <td>{{ team.member_count }}</td>
            <td>
              <span :class="['status-badge', team.status]">
                {{ team.status === 'active' ? '启用' : '禁用' }}
              </span>
            </td>
            <td>
              <button @click="selectTeam(team)" class="btn-link">查看</button>
              <button @click="editTeam(team)" class="btn-link">编辑</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 团队详情侧边栏 -->
    <div v-if="selectedTeam" class="team-detail-sidebar">
      <div class="sidebar-header">
        <h2>{{ selectedTeam.name }}</h2>
        <button @click="selectedTeam = null" class="btn-close">&times;</button>
      </div>

      <div class="member-list">
        <h3>成员列表</h3>
        <div v-for="member in selectedTeam.members" :key="member.id" class="member-item">
          <span class="member-name">{{ member.agent_name }}</span>
          <span class="member-role">({{ member.role }})</span>
          <span class="member-status">
            {{ member.self_introduction ? '已完成' : '待完成' }}
          </span>
        </div>
        <button @click="showAddMemberModal = true" class="btn-secondary">
          + 添加成员
        </button>
      </div>

      <div class="profile-preview">
        <h3>团队介绍预览</h3>
        <pre>{{ teamProfile }}</pre>
        <button @click="refreshProfile" class="btn-secondary">
          刷新预览
        </button>
      </div>
    </div>

    <!-- 创建团队弹窗 -->
    <div v-if="showCreateModal" class="modal-overlay">
      <div class="modal">
        <h2>创建团队</h2>
        <form @submit.prevent="createTeam">
          <input v-model="newTeam.name" placeholder="团队名称" required />
          <textarea v-model="newTeam.description" placeholder="团队描述"></textarea>
          <div class="modal-actions">
            <button type="button" @click="showCreateModal = false">取消</button>
            <button type="submit" class="btn-primary">创建</button>
          </div>
        </form>
      </div>
    </div>

    <!-- 添加成员弹窗 -->
    <div v-if="showAddMemberModal" class="modal-overlay">
      <div class="modal">
        <h2>添加成员</h2>
        <select v-model="newMember.agentId" required>
          <option value="" disabled>选择 Agent</option>
          <option v-for="agent in availableAgents" :key="agent.id" :value="agent.id">
            {{ agent.name }} ({{ agent.role }})
          </option>
        </select>
        <div class="modal-actions">
          <button type="button" @click="showAddMemberModal = false">取消</button>
          <button @click="addMember" class="btn-primary">添加</button>
        </div>
      </div>
    </div>

    <!-- 模板编辑弹窗 -->
    <div v-if="showTemplateModal" class="modal-overlay">
      <div class="modal">
        <h2>团队介绍生成模板</h2>
        <textarea v-model="templateContent" rows="15"></textarea>
        <div class="modal-actions">
          <button type="button" @click="showTemplateModal = false">取消</button>
          <button @click="saveTemplate" class="btn-primary">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { adminTeamApi, adminAgentApi } from '@/api/client'

const teams = ref([])
const selectedTeam = ref(null)
const teamProfile = ref('')
const showCreateModal = ref(false)
const showAddMemberModal = ref(false)
const showTemplateModal = ref(false)

const newTeam = ref({ name: '', description: '' })
const newMember = ref({ agentId: '' })
const availableAgents = ref([])
const templateContent = ref('')

// 加载团队列表
async function loadTeams() {
  const res = await adminTeamApi.list({ page: 1, page_size: 100 })
  teams.value = res.data.items
}

// 选择团队
async function selectTeam(team) {
  const res = await adminTeamApi.get(team.id)
  selectedTeam.value = res.data
  await refreshProfile()
}

// 刷新团队介绍预览
async function refreshProfile() {
  if (!selectedTeam.value) return
  const res = await adminTeamApi.getProfile(selectedTeam.value.id)
  teamProfile.value = res.data.content
}

// 创建团队
async function createTeam() {
  await adminTeamApi.create(newTeam.value)
  showCreateModal.value = false
  newTeam.value = { name: '', description: '' }
  await loadTeams()
}

// 编辑团队
async function editTeam(team) {
  // 实现编辑逻辑
}

// 添加成员
async function addMember() {
  if (!selectedTeam.value || !newMember.value.agentId) return
  await adminTeamApi.addMember(selectedTeam.value.id, newMember.value.agentId)
  showAddMemberModal.value = false
  newMember.value = { agentId: '' }
  await selectTeam({ id: selectedTeam.value.id })
}

// 加载可用 Agent
async function loadAvailableAgents() {
  const res = await adminAgentApi.list({ status: 'active' })
  availableAgents.value = res.data.items
}

// 加载模板
async function loadTemplate() {
  const res = await adminTeamApi.getTemplate()
  templateContent.value = res.data.content
}

// 保存模板
async function saveTemplate() {
  await adminTeamApi.updateTemplate(templateContent.value)
  showTemplateModal.value = false
}

onMounted(() => {
  loadTeams()
  loadAvailableAgents()
  loadTemplate()
})
</script>

<style scoped>
.teams-view { padding: 20px; }
.page-header { display: flex; justify-content: space-between; margin-bottom: 20px; }
.header-actions { display: flex; gap: 10px; }
.teams-table table { width: 100%; border-collapse: collapse; }
.teams-table th, .teams-table td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
.status-badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; }
.status-badge.active { background: #e6ffe6; color: #006600; }
.status-badge.disabled { background: #ffe6e6; color: #990000; }
.team-detail-sidebar {
  position: fixed; right: 0; top: 0; width: 400px; height: 100%;
  background: white; box-shadow: -2px 0 10px rgba(0,0,0,0.1); padding: 20px; overflow-y: auto;
}
.member-item { padding: 10px; border-bottom: 1px solid #eee; }
.member-status { font-size: 12px; color: #666; margin-left: 10px; }
.profile-preview pre {
  background: #f5f5f5; padding: 15px; border-radius: 4px;
  max-height: 300px; overflow-y: auto; white-space: pre-wrap;
}
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,0.5);
  display: flex; align-items: center; justify-content: center;
}
.modal { background: white; padding: 20px; border-radius: 8px; width: 400px; }
.modal-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 20px; }
.btn-primary { background: #0066cc; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; }
.btn-secondary { background: #f0f0f0; color: #333; padding: 8px 16px; border: 1px solid #ddd; border-radius: 4px; cursor: pointer; }
.btn-link { background: none; color: #0066cc; border: none; cursor: pointer; margin-right: 10px; }
</style>
```
</think>


<minimax:tool_call>
<invoke name="Read">
<parameter name="file_path">/Users/leon_zheng/PycharmProjects/wenge/OpenMOSS/app/database.py