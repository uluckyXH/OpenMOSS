"""
Team Space 业务逻辑
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.team import Team, TeamMember, TeamProfile, TeamProfileTemplate
from app.models.agent import Agent
from app.models.task import Task
from app.models.sub_task import SubTask

# 自我介绍任务描述模板
TEAM_INTRO_DESCRIPTION = """请根据以下模板完成自我介绍：

## 姓名
[你的名称]

## OpenClaw Agent ID
[你的agent_id]

## 职责
[描述你在团队中负责的工作]

## 擅长
[描述你的专业领域]

## 联系场景
[描述什么时候应该联系你]

请将自我介绍写入团队系统中。"""

# 更新 SOUL.md 任务描述模板
UPDATE_SOUL_DESCRIPTION = """请读取团队介绍信息，并更新你的 SOUL.md 文件：

团队介绍获取地址：GET /api/teams/me/profile

请将团队介绍内容添加到你的 SOUL.md 文件中，保持文件格式整洁。"""


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

    # 确保团队有 team_task_id（团队初始化任务）
    if not team.team_task_id:
        # 创建团队初始化任务
        team_task = Task(
            id=str(uuid.uuid4()),
            name=f"{team.name} 初始化",
            description="团队成员自我介绍和 SOUL.md 更新任务",
            type="once",
            status="active",
            team_id=team_id,  # 关联到团队
        )
        db.add(team_task)
        db.flush()  # 获取 ID 但不提交

        team.team_task_id = team_task.id

    # 创建团队成员记录
    member = TeamMember(
        id=str(uuid.uuid4()),
        team_id=team_id,
        agent_id=agent_id,
    )
    db.add(member)

    # 创建自我介绍子任务
    intro_task = SubTask(
        id=str(uuid.uuid4()),
        task_id=team.team_task_id,
        name=f"{agent.name} - 自我介绍",
        description=TEAM_INTRO_DESCRIPTION,
        deliverable="在团队系统中提交自我介绍",
        acceptance="自我介绍包含姓名、职责、擅长、联系场景四个部分",
        type="once",
        status="assigned",
        priority="high",
        assigned_agent=agent_id,
    )
    db.add(intro_task)

    db.commit()
    db.refresh(member)

    return member


def remove_team_member(db: Session, team_id: str, agent_id: str) -> None:
    """移除团队成员"""
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise ValueError("团队不存在")

    member = db.query(TeamMember).filter(
        TeamMember.team_id == team_id,
        TeamMember.agent_id == agent_id,
    ).first()
    if not member:
        raise ValueError("成员不存在")

    # 取消该成员在团队中的相关任务
    if team.team_task_id:
        pending_tasks = db.query(SubTask).filter(
            SubTask.task_id == team.team_task_id,
            SubTask.assigned_agent == agent_id,
            SubTask.status.in_(["pending", "assigned", "in_progress"]),
        ).all()

        for task in pending_tasks:
            task.status = "cancelled"
            task.remarks = "agent离职"

        if pending_tasks:
            db.commit()

    db.delete(member)
    db.commit()

    # 重新生成团队介绍（如果还有成员）
    generate_team_profile(db, team_id)

    # 如果团队仍有其他成员，为剩余每个成员创建 update_soul 任务（因为团队信息变了）
    remaining_members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    if remaining_members and team.team_task_id:
        # 为剩余成员创建 update_soul 任务
        for remaining_member in remaining_members:
            agent = db.query(Agent).filter(Agent.id == remaining_member.agent_id).first()
            if not agent:
                continue

            # 检查是否已经存在 update_soul 任务
            existing = db.query(SubTask).filter(
                SubTask.task_id == team.team_task_id,
                SubTask.assigned_agent == remaining_member.agent_id,
                SubTask.name.like("%更新 SOUL%"),
            ).first()

            if not existing:
                soul_task = SubTask(
                    id=str(uuid.uuid4()),
                    task_id=team.team_task_id,
                    name=f"{agent.name} - 更新 SOUL",
                    description=UPDATE_SOUL_DESCRIPTION,
                    deliverable="更新 SOUL.md 文件",
                    acceptance="SOUL.md 中包含团队介绍信息",
                    type="once",
                    status="assigned",
                    priority="medium",
                    assigned_agent=remaining_member.agent_id,
                )
                db.add(soul_task)

        db.commit()


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

    # 检查是否所有成员都完成了自我介绍
    all_completed = check_all_intros_completed(db, team.id)

    # 如果全部完成，为每个成员创建 update_soul 任务
    if all_completed and team.team_task_id:
        _create_update_soul_tasks(db, team)

    return member


def check_all_intros_completed(db: Session, team_id: str) -> bool:
    """检查团队所有成员是否都完成了自我介绍"""
    members = db.query(TeamMember).filter(TeamMember.team_id == team_id).all()
    if not members:
        return False
    return all(m.self_introduction is not None and m.self_introduction != "" for m in members)


def _create_update_soul_tasks(db: Session, team: Team) -> None:
    """为团队所有成员创建 update_soul 任务"""
    # 检查是否已经创建过 update_soul 任务（避免重复创建）
    existing_soul_tasks = db.query(SubTask).filter(
        SubTask.task_id == team.team_task_id,
        SubTask.name.like("%更新 SOUL%"),
    ).all()

    if existing_soul_tasks:
        return  # 已经创建过，不再重复创建

    # 获取所有成员
    members = db.query(TeamMember).filter(TeamMember.team_id == team.id).all()

    for member in members:
        agent = db.query(Agent).filter(Agent.id == member.agent_id).first()
        if not agent:
            continue

        soul_task = SubTask(
            id=str(uuid.uuid4()),
            task_id=team.team_task_id,
            name=f"{agent.name} - 更新 SOUL",
            description=UPDATE_SOUL_DESCRIPTION,
            deliverable="更新 SOUL.md 文件",
            acceptance="SOUL.md 中包含团队介绍信息",
            type="once",
            status="assigned",
            priority="medium",
            assigned_agent=member.agent_id,
        )
        db.add(soul_task)

    db.commit()


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
