"""
Agent 业务逻辑
"""
from datetime import datetime
import secrets
import uuid

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.activity_log import ActivityLog
from app.models.agent import Agent
from app.models.managed_agent import AgentRuntimePresence
from app.models.patrol_record import PatrolRecord
from app.models.request_log import RequestLog
from app.models.review_record import ReviewRecord
from app.models.reward_log import RewardLog
from app.models.sub_task import SubTask


def generate_api_key() -> str:
    """生成唯一的 API Key，格式 ak_<32位随机hex>"""
    return f"ak_{secrets.token_hex(16)}"


def register_agent(
    db: Session,
    name: str,
    role: str,
    description: str = "",
) -> Agent:
    """注册新 Agent，生成 API Key"""
    valid_roles = {"planner", "executor", "reviewer", "patrol"}
    if role not in valid_roles:
        raise ValidationError(f"无效角色 '{role}'，可选: {', '.join(valid_roles)}")

    existing = db.query(Agent).filter(Agent.name == name).first()
    if existing:
        raise ConflictError(f"名称 '{name}' 已被注册")

    agent = Agent(
        id=str(uuid.uuid4()),
        name=name,
        role=role,
        description=description,
        api_key=generate_api_key(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


def reset_agent_api_key(db: Session, agent_id: str) -> Agent:
    """重置 Agent 的 API Key"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    agent.api_key = generate_api_key()
    db.commit()
    db.refresh(agent)
    return agent


def list_agents(db: Session, role: str = None, status: str = None) -> list:
    """查询 Agent 列表，可按角色/状态过滤"""
    query = db.query(Agent)
    if role:
        query = query.filter(Agent.role == role)
    if status:
        query = query.filter(Agent.status == status)
    return query.all()


def get_agent_by_id(db: Session, agent_id: str) -> Agent:
    """根据 ID 获取 Agent"""
    return db.query(Agent).filter(Agent.id == agent_id).first()


def upsert_agent_presence(
    db: Session,
    agent_id: str,
    heartbeat_ip: str | None = None,
    at: datetime | None = None,
) -> AgentRuntimePresence:
    """写入或更新 Agent 心跳。"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    heartbeat_at = at or datetime.now()
    presence = db.query(AgentRuntimePresence).filter(
        AgentRuntimePresence.agent_id == agent_id
    ).first()

    if not presence:
        presence = AgentRuntimePresence(
            id=str(uuid.uuid4()),
            agent_id=agent_id,
        )
        db.add(presence)

    presence.last_heartbeat_at = heartbeat_at
    if heartbeat_ip is not None:
        presence.last_heartbeat_ip = heartbeat_ip

    db.commit()
    db.refresh(presence)
    return presence


def update_agent_profile(
    db: Session,
    agent_id: str,
    name: str | None = None,
    role: str | None = None,
    description: str | None = None,
) -> Agent:
    """更新 Agent 名称/角色/描述"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    if name:
        existing = db.query(Agent).filter(Agent.name == name, Agent.id != agent_id).first()
        if existing:
            raise ConflictError(f"名称 '{name}' 已被注册")
        agent.name = name

    if role:
        valid_roles = {"planner", "executor", "reviewer", "patrol"}
        if role not in valid_roles:
            raise ValidationError(f"无效角色 '{role}'，可选: {', '.join(valid_roles)}")
        agent.role = role

    if description is not None:
        agent.description = description

    db.commit()
    db.refresh(agent)
    return agent


def update_agent_status(db: Session, agent_id: str, status: str) -> Agent:
    """更新 Agent 状态"""
    valid_statuses = {"active", "disabled"}
    if status not in valid_statuses:
        raise ValidationError(f"无效状态 '{status}'，可选: {', '.join(valid_statuses)}")

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    agent.status = status
    db.commit()
    db.refresh(agent)
    return agent


def get_agent_related_counts(db: Session, agent_id: str) -> dict:
    """查询 Agent 关联数据的数量，用于删除前的风险展示"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    return {
        "agent_id": agent.id,
        "agent_name": agent.name,
        "sub_task_count": db.query(func.count(SubTask.id)).filter(SubTask.assigned_agent == agent_id).scalar() or 0,
        "review_count": db.query(func.count(ReviewRecord.id)).filter(ReviewRecord.reviewer_agent == agent_id).scalar() or 0,
        "reward_count": db.query(func.count(RewardLog.id)).filter(RewardLog.agent_id == agent_id).scalar() or 0,
        "activity_count": db.query(func.count(ActivityLog.id)).filter(ActivityLog.agent_id == agent_id).scalar() or 0,
        "patrol_count": db.query(func.count(PatrolRecord.id)).filter(PatrolRecord.agent_id == agent_id).scalar() or 0,
        "request_count": db.query(func.count(RequestLog.id)).filter(RequestLog.agent_id == agent_id).scalar() or 0,
    }


def delete_agent(db: Session, agent_id: str, confirm_name: str) -> dict:
    """安全删除 Agent，级联清理所有关联数据"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    if confirm_name != agent.name:
        raise ValidationError(f"确认名称不匹配，请输入「{agent.name}」以确认删除")

    counts = get_agent_related_counts(db, agent_id)

    db.query(SubTask).filter(SubTask.assigned_agent == agent_id).update(
        {SubTask.assigned_agent: None}, synchronize_session=False
    )
    db.query(ReviewRecord).filter(ReviewRecord.reviewer_agent == agent_id).delete(synchronize_session=False)
    db.query(RewardLog).filter(RewardLog.agent_id == agent_id).delete(synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.agent_id == agent_id).delete(synchronize_session=False)
    db.query(PatrolRecord).filter(PatrolRecord.agent_id == agent_id).delete(synchronize_session=False)
    db.query(RequestLog).filter(RequestLog.agent_id == agent_id).delete(synchronize_session=False)

    db.delete(agent)
    db.commit()

    return counts
