"""
子任务业务逻辑 — 含状态机校验
"""
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.sub_task import SubTask
from app.models.task import Task
from app.models.module import Module
from app.models.agent import Agent


# 状态机：合法的状态转移
VALID_TRANSITIONS = {
    "pending":      ["assigned"],
    "assigned":     ["in_progress", "pending"],      # 可退回 pending
    "in_progress":  ["review"],
    "review":       ["done", "rework"],
    "rework":       ["in_progress"],
    "blocked":      ["pending"],                     # 巡查标记后，规划师重新分配
    "done":         [],                              # 终态
    "cancelled":    [],                              # 终态
}


def create_sub_task(
    db: Session,
    task_id: str,
    name: str,
    description: str = "",
    deliverable: str = "",
    acceptance: str = "",
    priority: str = "medium",
    module_id: str = None,
    assigned_agent: str = None,
    type: str = "once",
) -> SubTask:
    """创建子任务"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise ValueError(f"任务 {task_id} 不存在")

    # 校验 module_id
    if module_id:
        module = db.query(Module).filter(Module.id == module_id).first()
        if not module:
            raise ValueError(f"模块 {module_id} 不存在")
        if module.task_id != task_id:
            raise ValueError(f"模块 {module_id} 不属于任务 {task_id}")

    # 校验 assigned_agent
    if assigned_agent:
        agent = db.query(Agent).filter(Agent.id == assigned_agent).first()
        if not agent:
            raise ValueError(f"Agent {assigned_agent} 不存在")

    # 如果指定了 Agent，默认状态为 assigned
    initial_status = "assigned" if assigned_agent else "pending"

    sub_task = SubTask(
        id=str(uuid.uuid4()),
        task_id=task_id,
        module_id=module_id,
        name=name,
        description=description,
        deliverable=deliverable,
        acceptance=acceptance,
        type=type,
        status=initial_status,
        priority=priority,
        assigned_agent=assigned_agent,
    )
    db.add(sub_task)
    db.commit()
    db.refresh(sub_task)
    return sub_task


def list_sub_tasks(
    db: Session,
    task_id: str = None,
    module_id: str = None,
    status: str = None,
    assigned_agent: str = None,
) -> list:
    """查询子任务列表，支持多条件过滤"""
    query = db.query(SubTask)
    if task_id:
        query = query.filter(SubTask.task_id == task_id)
    if module_id:
        query = query.filter(SubTask.module_id == module_id)
    if status:
        query = query.filter(SubTask.status == status)
    if assigned_agent:
        query = query.filter(SubTask.assigned_agent == assigned_agent)
    return query.order_by(SubTask.created_at.desc()).all()


def get_sub_task(db: Session, sub_task_id: str) -> SubTask:
    """获取单个子任务"""
    return db.query(SubTask).filter(SubTask.id == sub_task_id).first()


def _change_status(db: Session, sub_task_id: str, new_status: str, auto_commit: bool = True, **kwargs) -> SubTask:
    """内部方法：状态转移（含校验）"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")

    allowed = VALID_TRANSITIONS.get(sub_task.status, [])
    if new_status not in allowed:
        raise ValueError(
            f"状态转移不合法：{sub_task.status} → {new_status}，"
            f"允许: {', '.join(allowed) if allowed else '无（终态）'}"
        )

    sub_task.status = new_status

    # 额外字段更新
    for key, value in kwargs.items():
        if hasattr(sub_task, key):
            setattr(sub_task, key, value)

    if new_status == "done":
        sub_task.completed_at = datetime.now()

    if auto_commit:
        db.commit()
        db.refresh(sub_task)
    else:
        db.flush()  # 刷入数据库但不提交，保持在当前事务中
    return sub_task


# ============================================================
# 对外的状态操作方法
# ============================================================

def claim_sub_task(db: Session, sub_task_id: str, agent_id: str, session_id: str = None) -> SubTask:
    """认领子任务：pending → assigned"""
    return _change_status(
        db, sub_task_id, "assigned",
        assigned_agent=agent_id,
        current_session_id=session_id,
    )


def start_sub_task(db: Session, sub_task_id: str, session_id: str = None) -> SubTask:
    """开始执行：assigned/rework → in_progress"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")

    if sub_task.status not in ("assigned", "rework"):
        raise ValueError(
            f"状态转移不合法：{sub_task.status} → in_progress，"
            f"仅 assigned/rework 状态可以开始执行"
        )

    sub_task.status = "in_progress"
    if session_id:
        sub_task.current_session_id = session_id
    db.commit()
    db.refresh(sub_task)
    return sub_task


def submit_sub_task(db: Session, sub_task_id: str) -> SubTask:
    """提交成果：in_progress → review"""
    return _change_status(db, sub_task_id, "review")


def complete_sub_task(db: Session, sub_task_id: str, auto_commit: bool = True) -> SubTask:
    """审查通过：review → done"""
    return _change_status(db, sub_task_id, "done", auto_commit=auto_commit)


def rework_sub_task(db: Session, sub_task_id: str, rework_agent: str = None, auto_commit: bool = True) -> SubTask:
    """驳回返工：review → rework"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")

    kwargs = {}
    if rework_agent:
        agent = db.query(Agent).filter(Agent.id == rework_agent).first()
        if not agent:
            raise ValueError(f"Agent {rework_agent} 不存在")
        kwargs["assigned_agent"] = rework_agent
    kwargs["rework_count"] = sub_task.rework_count + 1

    return _change_status(db, sub_task_id, "rework", auto_commit=auto_commit, **kwargs)


def restart_sub_task(db: Session, sub_task_id: str, session_id: str = None) -> SubTask:
    """返工后重新开始：rework → in_progress（兼容旧调用，内部转发到 start_sub_task）"""
    return start_sub_task(db, sub_task_id, session_id)


def update_session(db: Session, sub_task_id: str, session_id: str) -> SubTask:
    """更新子任务的当前会话 ID（仅 in_progress 状态可用）"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")
    if sub_task.status != "in_progress":
        raise ValueError(f"只有 in_progress 状态才能更新会话，当前: {sub_task.status}")

    sub_task.current_session_id = session_id
    db.commit()
    db.refresh(sub_task)
    return sub_task


def block_sub_task(db: Session, sub_task_id: str) -> SubTask:
    """巡查标记异常：in_progress → blocked（特殊操作，跳过状态机）"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")

    if sub_task.status not in ("in_progress", "assigned", "rework"):
        raise ValueError(f"只能对 in_progress/assigned/rework 状态的子任务标记 blocked")

    sub_task.status = "blocked"
    sub_task.current_session_id = None  # 清空会话
    db.commit()
    db.refresh(sub_task)
    return sub_task


def reassign_sub_task(db: Session, sub_task_id: str, agent_id: str) -> SubTask:
    """重新分配：blocked → pending（规划师操作）"""
    # 校验 Agent 存在
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise ValueError(f"Agent {agent_id} 不存在")

    sub_task = _change_status(db, sub_task_id, "pending")
    sub_task.assigned_agent = agent_id
    sub_task.status = "assigned"
    sub_task.current_session_id = None
    db.commit()
    db.refresh(sub_task)
    return sub_task


def update_sub_task(
    db: Session,
    sub_task_id: str,
    name: str = None,
    description: str = None,
    deliverable: str = None,
    acceptance: str = None,
    priority: str = None,
    type: str = None,
    remarks: str = None,
    status: str = None,
    assigned_agent: str = None,
    recurring_config: dict = None,
) -> SubTask:
    """编辑子任务（仅 pending/assigned 状态可编辑）"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")
    if sub_task.status not in ("pending", "assigned"):
        raise ValueError(f"子任务状态为 {sub_task.status}，只有 pending/assigned 状态可编辑")

    # 校验 assigned_agent
    if assigned_agent is not None:
        if assigned_agent:
            agent = db.query(Agent).filter(Agent.id == assigned_agent).first()
            if not agent:
                raise ValueError(f"Agent {assigned_agent} 不存在")
        # 清空 agent 时，允许传空字符串

    if name is not None:
        sub_task.name = name
    if description is not None:
        sub_task.description = description
    if deliverable is not None:
        sub_task.deliverable = deliverable
    if acceptance is not None:
        sub_task.acceptance = acceptance
    if priority is not None:
        sub_task.priority = priority
    if type is not None:
        sub_task.type = type
    if remarks is not None:
        sub_task.remarks = remarks

    # 处理 status 和 assigned_agent 的联动
    if assigned_agent is not None:
        sub_task.assigned_agent = assigned_agent if assigned_agent else None
        # 如果分配了 agent 且当前是 pending，自动改为 assigned
        if assigned_agent and sub_task.status == "pending":
            sub_task.status = "assigned"

    # 如果手动修改了 status
    if status is not None:
        if status not in ("pending", "assigned"):
            raise ValueError(f"只有 pending/assigned 状态可编辑，非法状态: {status}")
        sub_task.status = status

    # 循环配置
    if recurring_config is not None:
        sub_task.recurring_config = recurring_config

    db.commit()
    db.refresh(sub_task)
    return sub_task


def cancel_sub_task(db: Session, sub_task_id: str) -> SubTask:
    """取消子任务"""
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise ValueError(f"子任务 {sub_task_id} 不存在")
    if sub_task.status in ("done", "cancelled"):
        raise ValueError(f"子任务状态为 {sub_task.status}，无法取消")

    sub_task.status = "cancelled"
    sub_task.current_session_id = None
    db.commit()
    db.refresh(sub_task)
    return sub_task
