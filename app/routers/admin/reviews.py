"""
管理端审查记录路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin.review import AdminReviewDetail, AdminReviewPageResponse
from app.services.admin_query import review as admin_review_query_service


router = APIRouter(prefix="/admin", tags=["Admin Review"])


@router.get(
    "/review-records",
    response_model=AdminReviewPageResponse,
    summary="管理端查看审查记录列表",
)
async def list_admin_review_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    task_id: Optional[str] = Query(None, description="按任务过滤"),
    sub_task_id: Optional[str] = Query(None, description="按子任务过滤"),
    reviewer_agent: Optional[str] = Query(None, description="按审查 Agent 过滤"),
    result: Optional[str] = Query(None, description="按审查结果过滤 approved/rejected"),
    keyword: Optional[str] = Query(None, description="按任务名、子任务名、意见关键字搜索"),
    days: Optional[int] = Query(None, ge=1, description="最近 N 天"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看管理端审查记录列表"""
    return admin_review_query_service.list_review_records(
        db,
        page=page,
        page_size=page_size,
        task_id=task_id,
        sub_task_id=sub_task_id,
        reviewer_agent=reviewer_agent,
        result=result,
        keyword=keyword,
        days=days,
        sort_order=sort_order,
    )


@router.get(
    "/review-records/{review_id}",
    response_model=AdminReviewDetail,
    summary="管理端查看审查记录详情",
)
async def get_admin_review_detail(
    review_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看单条管理端审查记录详情"""
    return admin_review_query_service.get_review_detail(db, review_id)
