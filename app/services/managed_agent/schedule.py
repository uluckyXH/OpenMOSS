"""
managed_agent 定时任务服务。
"""

import re
import uuid
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError, ValidationError
from app.models.managed_agent import ManagedAgentSchedule

from .core import get_managed_agent_or_404
from .shared import _bump_config_version, _normalize_schedule_kwargs


INTERVAL_EXPR_PATTERN = re.compile(r"^[1-9]\d*[smhd]$")


def _is_valid_cron_value(value: str, minimum: int, maximum: int) -> bool:
    """校验单个 cron 数值、范围或步进片段。"""
    if not value.isdigit():
        return False
    numeric = int(value)
    return minimum <= numeric <= maximum


def _is_valid_cron_part(part: str, minimum: int, maximum: int) -> bool:
    """校验单个 cron 字段的一个逗号分隔片段。"""
    if not part:
        return False

    base = part
    if "/" in part:
        base, step = part.split("/", 1)
        if not step.isdigit() or int(step) <= 0:
            return False

    if base == "*":
        return True

    if "-" in base:
        start, end = base.split("-", 1)
        if not (
            _is_valid_cron_value(start, minimum, maximum)
            and _is_valid_cron_value(end, minimum, maximum)
        ):
            return False
        return int(start) <= int(end)

    return _is_valid_cron_value(base, minimum, maximum)


def _is_valid_cron_field(field: str, minimum: int, maximum: int) -> bool:
    """校验标准 5 段 cron 中的单个字段。"""
    return all(_is_valid_cron_part(part, minimum, maximum) for part in field.split(","))


def _is_valid_cron_expr(expr: str) -> bool:
    """校验标准 5 段 cron 表达式。"""
    fields = expr.split()
    if len(fields) != 5:
        return False

    ranges = (
        (0, 59),  # minute
        (0, 23),  # hour
        (1, 31),  # day of month
        (1, 12),  # month
        (0, 7),  # day of week
    )
    return all(
        _is_valid_cron_field(field, minimum, maximum)
        for field, (minimum, maximum) in zip(fields, ranges)
    )


def _validate_schedule_expression(schedule_type: str, schedule_expr: str) -> None:
    """按定时任务类型校验表达式，避免保存后部署阶段才失败。"""
    if schedule_type not in {"interval", "cron"}:
        raise ValidationError("schedule_type 只支持 interval 或 cron")

    if not schedule_expr or not schedule_expr.strip():
        raise ValidationError("schedule_expr 不能为空")

    expr = schedule_expr.strip()
    if schedule_type == "interval":
        if not INTERVAL_EXPR_PATTERN.fullmatch(expr):
            raise ValidationError("interval 类型的 schedule_expr 必须使用 5m、15m、1h、2d 这类格式")
        return

    if not _is_valid_cron_expr(expr):
        raise ValidationError("cron 类型的 schedule_expr 必须是标准 5 段 cron 表达式，例如 0 9 * * *")


def _validate_schedule_payload(
    schedule_type: object,
    schedule_expr: object,
    timeout_seconds: object,
    schedule_message_content: object,
) -> None:
    """校验 schedule 的完整性，确保保存后即可直接进入脚本生成。"""
    if schedule_type is None:
        raise ValidationError("schedule_type 不能为空")
    if schedule_expr is None:
        raise ValidationError("schedule_expr 不能为空")
    if timeout_seconds is None:
        raise ValidationError("timeout_seconds 不能为空")

    if not isinstance(timeout_seconds, int) or timeout_seconds < 60:
        raise ValidationError("timeout_seconds 必须大于等于 60 秒")

    if not isinstance(schedule_message_content, str) or not schedule_message_content.strip():
        raise ValidationError("schedule_message_content 不能为空，且必须填写定时唤醒提示词")

    _validate_schedule_expression(str(schedule_type), str(schedule_expr))


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
    _validate_schedule_payload(
        normalized.get("schedule_type"),
        normalized.get("schedule_expr"),
        normalized.get("timeout_seconds"),
        normalized.get("schedule_message_content"),
    )

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
    _validate_schedule_payload(
        normalized.get("schedule_type", schedule.schedule_type),
        normalized.get("schedule_expr", schedule.schedule_expr),
        normalized.get("timeout_seconds", schedule.timeout_seconds),
        normalized.get("schedule_message_content", schedule.schedule_message_content),
    )

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
