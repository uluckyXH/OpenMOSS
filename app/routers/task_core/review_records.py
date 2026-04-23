"""
审查记录路由 — 审查提交 + 查询
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime as dt

from app.database import get_db
from app.auth.dependencies import get_current_agent, require_role
from app.exceptions import BusinessError
from app.services.task_core import review as review_service
from app.models.agent import Agent


router = APIRouter(prefix="/review-records", tags=["ReviewRecord"])


# ============================================================
# 请求/响应模型
# ============================================================

class ReviewCreateRequest(BaseModel):
    sub_task_id: str = Field(..., description="子任务 ID")
    result: str = Field(..., description="审查结果: approved/rejected")
    score: int = Field(..., description="评分 1-5")
    issues: str = Field("", description="问题描述（驳回时必填）")
    comment: str = Field("", description="审查意见")
    rework_agent: Optional[str] = Field(None, description="返工指派 Agent ID（驳回时可选）")


class ReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sub_task_id: str
    reviewer_agent: str
    round: int
    result: str
    score: int
    issues: str
    comment: str
    rework_agent: Optional[str]
    created_at: Optional[dt] = None


# ============================================================
# 路由
# ============================================================

@router.post("", response_model=ReviewResponse, summary="提交审查记录")
async def create_review(
    req: ReviewCreateRequest,
    agent: Agent = Depends(require_role("reviewer")),
    db: Session = Depends(get_db),
):
    """审查者提交审查记录（先记后改：写入记录后自动推进子任务状态）"""
    try:
        record = review_service.create_review(
            db,
            sub_task_id=req.sub_task_id,
            reviewer_agent=agent.id,
            result=req.result,
            score=req.score,
            issues=req.issues,
            comment=req.comment,
            rework_agent=req.rework_agent,
        )
    except BusinessError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    return record


@router.get("", summary="查看审查记录")
async def list_reviews(
    sub_task_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 0,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """
    查看审查记录列表，可按子任务过滤。
    - page_size=0（默认）: 返回全部
    - page_size>0: 分页返回
    """
    from app.services.pagination import paginate
    from app.models.review_record import ReviewRecord
    query = db.query(ReviewRecord)
    if sub_task_id:
        query = query.filter(ReviewRecord.sub_task_id == sub_task_id)
    query = query.order_by(ReviewRecord.created_at.desc())
    return paginate(query, page=page, page_size=page_size)


@router.get("/{review_id}", response_model=ReviewResponse, summary="查看审查详情")
async def get_review(
    review_id: str,
    agent: Agent = Depends(get_current_agent),
    db: Session = Depends(get_db),
):
    """获取单条审查记录"""
    record = review_service.get_review(db, review_id)
    if not record:
        raise HTTPException(status_code=404, detail="审查记录不存在")
    return record
