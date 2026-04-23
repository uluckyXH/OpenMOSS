"""
审查记录业务逻辑 — 先记后改原则
"""
import uuid
from sqlalchemy.orm import Session

from app.exceptions import ConflictError, NotFoundError, ValidationError
from app.models.review_record import ReviewRecord
from app.models.sub_task import SubTask
from app.models.agent import Agent
from . import sub_task as sub_task_service
from . import reward as reward_service


def create_review(
    db: Session,
    sub_task_id: str,
    reviewer_agent: str,
    result: str,
    score: int,
    issues: str = "",
    comment: str = "",
    rework_agent: str = None,
) -> ReviewRecord:
    """
    创建审查记录并自动推进子任务状态。
    核心原则：先记后改，且所有操作在同一事务中完成。
    """
    # 校验 result
    if result not in ("approved", "rejected"):
        raise ValidationError(f"无效结果 '{result}'，可选: approved, rejected")

    # 校验 score
    if not (1 <= score <= 5):
        raise ValidationError(f"评分必须 1-5，当前: {score}")

    # 驳回时 issues 必填
    if result == "rejected" and not issues.strip():
        raise ValidationError("驳回时必须填写问题描述（issues）")

    # 校验子任务存在且状态为 review
    sub_task = db.query(SubTask).filter(SubTask.id == sub_task_id).first()
    if not sub_task:
        raise NotFoundError(f"子任务 {sub_task_id} 不存在")
    if sub_task.status != "review":
        raise ConflictError(f"子任务状态为 {sub_task.status}，只有 review 状态才能审查")

    # 校验返工 Agent
    if rework_agent:
        agent = db.query(Agent).filter(Agent.id == rework_agent).first()
        if not agent:
            raise NotFoundError(f"Agent {rework_agent} 不存在")

    # 记录被审查的执行者（在状态变更前保存，避免后续被修改）
    executor_agent_id = sub_task.assigned_agent

    # 计算审查轮次
    round_count = db.query(ReviewRecord).filter(
        ReviewRecord.sub_task_id == sub_task_id
    ).count() + 1

    # === 以下所有操作在同一事务中完成 ===
    try:
        # 1. 写入审查记录（不单独 commit）
        record = ReviewRecord(
            id=str(uuid.uuid4()),
            sub_task_id=sub_task_id,
            reviewer_agent=reviewer_agent,
            round=round_count,
            result=result,
            score=score,
            issues=issues,
            comment=comment,
            rework_agent=rework_agent,
        )
        db.add(record)

        # 2. 变更子任务状态（不单独 commit）
        if result == "approved":
            sub_task_service.complete_sub_task(db, sub_task_id, auto_commit=False)
        else:
            sub_task_service.rework_sub_task(db, sub_task_id, rework_agent, auto_commit=False)

        # 3. 计算积分（不单独 commit）
        if executor_agent_id:
            reward_service.apply_review_score(
                db, executor_agent_id, sub_task_id, score, auto_commit=False
            )

        # 4. 统一提交 — 全部成功才 commit
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    return record


def list_reviews(
    db: Session,
    sub_task_id: str = None,
    reviewer_agent: str = None,
) -> list:
    """查询审查记录"""
    query = db.query(ReviewRecord)
    if sub_task_id:
        query = query.filter(ReviewRecord.sub_task_id == sub_task_id)
    if reviewer_agent:
        query = query.filter(ReviewRecord.reviewer_agent == reviewer_agent)
    return query.order_by(ReviewRecord.created_at.desc()).all()


def get_review(db: Session, review_id: str) -> ReviewRecord:
    """获取单条审查记录"""
    return db.query(ReviewRecord).filter(ReviewRecord.id == review_id).first()
