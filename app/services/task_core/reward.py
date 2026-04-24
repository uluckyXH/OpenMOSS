"""
奖励评分业务逻辑 — 积分增减 + Agent 累计分同步
"""
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import func, update

from app.exceptions import NotFoundError
from app.models.reward_log import RewardLog
from app.models.agent import Agent


# 评分规则：审查分 → 积分变化
SCORE_RULES = {
    5: +5,   # 超出预期
    4: +5,   # 完全达标
    3: 0,    # 基本达标
    2: -5,   # 部分不足
    1: -5,   # 严重不足
}


def add_reward(
    db: Session,
    agent_id: str,
    reason: str,
    score_delta: int,
    sub_task_id: str = None,
    auto_commit: bool = True,
) -> RewardLog:
    """写入一条积分变更记录，并同步更新 Agent 的 total_score"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    # 写入记录
    log = RewardLog(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        sub_task_id=sub_task_id,
        reason=reason,
        score_delta=score_delta,
    )
    db.add(log)

    # 原子更新 Agent 累计分（SQL 层 total_score = total_score + delta，防止并发丢失更新）
    db.execute(
        update(Agent)
        .where(Agent.id == agent_id)
        .values(total_score=Agent.total_score + score_delta)
    )

    if auto_commit:
        db.commit()
        db.refresh(log)
    else:
        db.flush()
    return log


def apply_review_score(
    db: Session,
    agent_id: str,
    sub_task_id: str,
    review_score: int,
    auto_commit: bool = True,
) -> RewardLog:
    """根据审查评分自动计算并写入积分变更"""
    delta = SCORE_RULES.get(review_score, 0)
    if delta == 0:
        return None  # 评分 3 不加不扣，不写记录

    reason = f"审查评分 {review_score} 分"
    return add_reward(db, agent_id, reason, delta, sub_task_id, auto_commit=auto_commit)


def get_agent_score(db: Session, agent_id: str) -> dict:
    """获取 Agent 的积分概要（含排名）"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise NotFoundError(f"Agent {agent_id} 不存在")

    # 统计加分/扣分次数
    logs = db.query(RewardLog).filter(RewardLog.agent_id == agent_id).all()
    plus_count = sum(1 for l in logs if l.score_delta > 0)
    minus_count = sum(1 for l in logs if l.score_delta < 0)

    # 计算排名（积分比自己高的 Agent 数 + 1）
    higher_count = db.query(Agent).filter(Agent.total_score > agent.total_score).count()
    rank = higher_count + 1
    total_agents = db.query(Agent).count()

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "total_score": agent.total_score,
        "rank": rank,
        "total_agents": total_agents,
        "reward_count": plus_count,
        "penalty_count": minus_count,
        "total_records": len(logs),
    }


def list_reward_logs(
    db: Session,
    agent_id: str = None,
    sub_task_id: str = None,
) -> list:
    """查询积分记录"""
    query = db.query(RewardLog)
    if agent_id:
        query = query.filter(RewardLog.agent_id == agent_id)
    if sub_task_id:
        query = query.filter(RewardLog.sub_task_id == sub_task_id)
    return query.order_by(RewardLog.created_at.desc()).all()


def get_leaderboard(db: Session) -> list[dict]:
    """获取积分排行榜（所有 Agent 按 total_score 降序）。"""
    agents = db.query(Agent).order_by(Agent.total_score.desc()).all()
    return [
        {
            "rank": i + 1,
            "agent_id": a.id,
            "agent_name": a.name,
            "role": a.role,
            "total_score": a.total_score,
        }
        for i, a in enumerate(agents)
    ]


def list_reward_logs_paginated(db: Session, agent_id: str, *, page: int = 1, page_size: int = 0) -> dict:
    """查询指定 Agent 的积分记录（分页）。"""
    from app.services.pagination import paginate
    query = db.query(RewardLog).filter(RewardLog.agent_id == agent_id)
    query = query.order_by(RewardLog.created_at.desc())
    return paginate(query, page=page, page_size=page_size)

