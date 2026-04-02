"""
任务业务逻辑
"""
import uuid
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.module import Module
from app.models.sub_task import SubTask
from app.models.rule import Rule
from app.models.activity_log import ActivityLog
from app.models.review_record import ReviewRecord
from app.models.reward_log import RewardLog
from app.models.patrol_record import PatrolRecord


def create_task(db: Session, name: str, description: str = "", type: str = "once") -> Task:
    """创建任务"""
    valid_types = {"once", "recurring"}
    if type not in valid_types:
        raise ValueError(f"无效类型 '{type}'，可选: {', '.join(valid_types)}")

    task = Task(
        id=str(uuid.uuid4()),
        name=name,
        description=description,
        type=type,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, status: str = None) -> list:
    """查询任务列表"""
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    return query.order_by(Task.created_at.desc()).all()


def get_task(db: Session, task_id: str) -> Task:
    """获取单个任务"""
    return db.query(Task).filter(Task.id == task_id).first()


def update_task_status(db: Session, task_id: str, status: str) -> Task:
    """更新任务状态"""
    valid_statuses = {"planning", "active", "in_progress", "completed", "archived"}
    if status not in valid_statuses:
        raise ValueError(f"无效状态 '{status}'，可选: {', '.join(valid_statuses)}")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")

    task.status = status
    db.commit()
    db.refresh(task)
    return task


def update_task(db: Session, task_id: str, name: str = None, description: str = None) -> Task:
    """编辑任务（仅 planning/active 状态可编辑）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")
    if task.status not in ("planning", "active"):
        raise ValueError(f"任务状态为 {task.status}，只有 planning/active 状态可编辑")

    if name is not None:
        task.name = name
    if description is not None:
        task.description = description
    db.commit()
    db.refresh(task)
    return task


def cancel_task(db: Session, task_id: str) -> Task:
    """取消任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")
    if task.status in ("completed", "archived", "cancelled"):
        raise ValueError(f"任务状态为 {task.status}，无法取消")

    task.status = "cancelled"
    db.commit()
    db.refresh(task)
    return task


def restart_task(db: Session, task_id: str, status: str = "active") -> Task:
    """重启已取消的任务"""
    if status not in ("planning", "active"):
        raise ValueError("重启状态仅支持 planning/active")

    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")
    if task.status != "cancelled":
        raise ValueError(f"任务状态为 {task.status}，只有已取消的任务可以重启")

    task.status = status
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str) -> None:
    """彻底删除任务（含关联模块/子任务/规则/日志）"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")

    sub_task_ids = [row[0] for row in db.query(SubTask.id).filter(SubTask.task_id == task_id).all()]

    if sub_task_ids:
        db.query(Rule).filter(Rule.sub_task_id.in_(sub_task_ids)).delete(synchronize_session=False)
        db.query(ActivityLog).filter(ActivityLog.sub_task_id.in_(sub_task_ids)).delete(synchronize_session=False)
        db.query(ReviewRecord).filter(ReviewRecord.sub_task_id.in_(sub_task_ids)).delete(synchronize_session=False)
        db.query(RewardLog).filter(RewardLog.sub_task_id.in_(sub_task_ids)).delete(synchronize_session=False)
        db.query(PatrolRecord).filter(PatrolRecord.sub_task_id.in_(sub_task_ids)).delete(synchronize_session=False)
        db.query(SubTask).filter(SubTask.id.in_(sub_task_ids)).delete(synchronize_session=False)

    db.query(Rule).filter(Rule.task_id == task_id).delete(synchronize_session=False)
    db.query(Module).filter(Module.task_id == task_id).delete(synchronize_session=False)

    db.delete(task)
    db.commit()


def create_module(db: Session, task_id: str, name: str, description: str = "") -> Module:
    """创建模块"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")

    module = Module(
        id=str(uuid.uuid4()),
        task_id=task_id,
        name=name,
        description=description,
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def list_modules(db: Session, task_id: str) -> list:
    """查询任务下的模块"""
    return db.query(Module).filter(Module.task_id == task_id).all()
