"""
管理端仪表盘路由
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.schemas.admin.dashboard import (
    AdminDashboardHighlightsResponse,
    AdminDashboardOverviewResponse,
    AdminDashboardTrendsResponse,
)
from app.services.admin_query import dashboard as admin_dashboard_query_service


router = APIRouter(prefix="/admin", tags=["Admin Dashboard"])


@router.get(
    "/dashboard/overview",
    response_model=AdminDashboardOverviewResponse,
    summary="管理端查看仪表盘概览",
)
async def get_admin_dashboard_overview(
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端 Dashboard Phase 1 概览统计"""
    return admin_dashboard_query_service.get_dashboard_overview(db)


@router.get(
    "/dashboard/highlights",
    response_model=AdminDashboardHighlightsResponse,
    summary="管理端查看仪表盘高亮面板",
)
async def get_admin_dashboard_highlights(
    limit: int = Query(5, ge=1, le=50, description="每组高亮列表返回条数"),
    inactive_hours: int = Query(24, ge=1, le=720, description="低活跃判定窗口，单位小时"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端 Dashboard Phase 2 的待处理和风险高亮面板"""
    return admin_dashboard_query_service.get_dashboard_highlights(
        db,
        limit=limit,
        inactive_hours=inactive_hours,
    )


@router.get(
    "/dashboard/trends",
    response_model=AdminDashboardTrendsResponse,
    summary="管理端查看仪表盘趋势数据",
)
async def get_admin_dashboard_trends(
    days: int = Query(7, ge=1, le=30, description="趋势天数窗口，范围 1-30"),
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看管理端 Dashboard Phase 3 的趋势统计"""
    return admin_dashboard_query_service.get_dashboard_trends(
        db,
        days=days,
    )
