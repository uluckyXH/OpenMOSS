"""
managed_agent 定时任务服务。
"""

import uuid
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.managed_agent import ManagedAgentSchedule

from .core import get_managed_agent_or_404
from .shared import _bump_config_version, _normalize_schedule_kwargs


def list_schedules(db: Session, managed_agent_id: str) -> List[ManagedAgentSchedule]:
    """获取 Agent 的所有定时任务。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return db.query(ManagedAgentSchedule).filter(
        ManagedAgentSchedule.managed_agent_id == managed_agent_id
    ).all()


def get_schedule_or_404(db: Session, schedule_id: str) -> ManagedAgentSchedule:
    """获取定时任务，不存在则抛异常。"""
    schedule = db.query(ManagedAgentSchedule).filter(
        ManagedAgentSchedule.id == schedule_id
    ).first()
    if not schedule:
        raise NotFoundError(f"定时任务不存在: {schedule_id}")
    return schedule


def get_schedule_for_agent_or_404(
    db: Session,
    managed_agent_id: str,
    schedule_id: str,
) -> ManagedAgentSchedule:
    """获取属于指定 Agent 的定时任务。"""
    schedule = db.query(ManagedAgentSchedule).filter(
        ManagedAgentSchedule.id == schedule_id,
        ManagedAgentSchedule.managed_agent_id == managed_agent_id,
    ).first()
    if not schedule:
        raise NotFoundError(f"定时任务不存在: {schedule_id}")
    return schedule


def create_schedule(db: Session, managed_agent_id: str, **kwargs) -> ManagedAgentSchedule:
    """创建定时任务。"""
    agent = get_managed_agent_or_404(db, managed_agent_id)
    normalized = _normalize_schedule_kwargs(kwargs)

    schedule = ManagedAgentSchedule(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        **normalized,
    )
    db.add(schedule)
    _bump_config_version(db, agent)
    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule(db: Session, schedule_id: str, **kwargs) -> ManagedAgentSchedule:
    """更新定时任务。"""
    schedule = get_schedule_or_404(db, schedule_id)
    agent = get_managed_agent_or_404(db, schedule.managed_agent_id)
    normalized = _normalize_schedule_kwargs(kwargs, schedule.execution_options_json)

    changed = False
    for key, value in normalized.items():
        if hasattr(schedule, key) and getattr(schedule, key) != value:
            setattr(schedule, key, value)
            changed = True

    if changed:
        schedule.updated_at = datetime.now()
        _bump_config_version(db, agent)

    db.commit()
    db.refresh(schedule)
    return schedule


def update_schedule_for_agent(
    db: Session,
    managed_agent_id: str,
    schedule_id: str,
    **kwargs,
) -> ManagedAgentSchedule:
    """更新属于指定 Agent 的定时任务。"""
    schedule = get_schedule_for_agent_or_404(db, managed_agent_id, schedule_id)
    return update_schedule(db, schedule.id, **kwargs)


def delete_schedule(db: Session, schedule_id: str) -> None:
    """删除定时任务。"""
    schedule = get_schedule_or_404(db, schedule_id)
    agent = get_managed_agent_or_404(db, schedule.managed_agent_id)
    db.delete(schedule)
    _bump_config_version(db, agent)
    db.commit()


def delete_schedule_for_agent(db: Session, managed_agent_id: str, schedule_id: str) -> None:
    """删除属于指定 Agent 的定时任务。"""
    schedule = get_schedule_for_agent_or_404(db, managed_agent_id, schedule_id)
    delete_schedule(db, schedule.id)
