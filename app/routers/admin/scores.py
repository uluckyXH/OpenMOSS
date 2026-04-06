"""
管理端积分排行榜路由
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin_score import (
    AdminScoreAdjustRequest,
    AdminScoreAdjustResponse,
    AdminScoreLeaderboardPageResponse,
    AdminScoreLogPageResponse,
    AdminScoreSummaryResponse,
)
from app.services import admin_score_query_service, admin_score_service


router = APIRouter(prefix="/admin", tags=["Admin Score"])


def _raise_admin_score_query_error(exc: Exception) -> None:
    """统一处理管理端积分查询异常"""
    if isinstance(exc, admin_score_query_service.InvalidQueryError):
        raise HTTPException(status_code=400, detail=str(exc))
    raise exc


def _raise_admin_score_write_error(exc: Exception) -> None:
    """统一处理管理端积分写操作异常"""
    if isinstance(exc, admin_score_service.AdminScoreWriteError):
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
    raise exc


@router.get("/scores/summary", response_model=AdminScoreSummaryResponse, summary="管理端查看积分概览")
async def get_admin_score_summary(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端积分排行榜顶部概览统计"""
    try:
        return admin_score_query_service.get_score_summary(db)
    except Exception as exc:
        _raise_admin_score_query_error(exc)


@router.get(
    "/scores/leaderboard",
    response_model=AdminScoreLeaderboardPageResponse,
    summary="管理端查看积分排行榜",
)
async def list_admin_score_leaderboard(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    role: Optional[str] = Query(None, description="按角色过滤"),
    status: Optional[str] = Query(None, description="按状态过滤"),
    keyword: Optional[str] = Query(None, description="按名称或描述搜索"),
    score_min: Optional[int] = Query(None, description="最低积分"),
    score_max: Optional[int] = Query(None, description="最高积分"),
    sort_by: str = Query("total_score", description="排序字段"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看管理端积分排行榜"""
    try:
        return admin_score_query_service.list_score_leaderboard(
            db,
            page=page,
            page_size=page_size,
            role=role,
            status=status,
            keyword=keyword,
            score_min=score_min,
            score_max=score_max,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_admin_score_query_error(exc)


@router.get(
    "/scores/logs",
    response_model=AdminScoreLogPageResponse,
    summary="管理端查看全局积分流水",
)
async def list_admin_score_logs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数"),
    agent_id: Optional[str] = Query(None, description="按 Agent 过滤"),
    sub_task_id: Optional[str] = Query(None, description="按子任务过滤"),
    score_sign: Optional[str] = Query(None, description="按积分方向过滤 positive/negative"),
    keyword: Optional[str] = Query(None, description="按原因搜索"),
    sort_order: str = Query("desc", description="排序方向 asc/desc"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """分页查看管理端全局积分流水"""
    try:
        return admin_score_query_service.list_score_logs(
            db,
            page=page,
            page_size=page_size,
            agent_id=agent_id,
            sub_task_id=sub_task_id,
            score_sign=score_sign,
            keyword=keyword,
            sort_order=sort_order,
        )
    except Exception as exc:
        _raise_admin_score_query_error(exc)


@router.post(
    "/scores/adjust",
    response_model=AdminScoreAdjustResponse,
    summary="管理端手动调整积分",
)
async def adjust_admin_score(
    req: AdminScoreAdjustRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """管理员在管理端直接手动给 Agent 加分或扣分"""
    try:
        return admin_score_service.adjust_score(
            db,
            agent_id=req.agent_id,
            score_delta=req.score_delta,
            reason=req.reason,
            sub_task_id=req.sub_task_id,
        )
    except Exception as exc:
        _raise_admin_score_write_error(exc)
