"""配置态 Agent 定时任务路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    ManagedAgentScheduleCreateRequest,
    ManagedAgentScheduleResponse,
    ManagedAgentScheduleUpdateRequest,
)
from app.services import managed_agent as svc


router = APIRouter(prefix="/admin/managed-agents")


@router.get("/{agent_id}/schedules", response_model=list[ManagedAgentScheduleResponse])
def list_schedules(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取 Agent 的所有定时任务。"""
    try:
        schedules = svc.list_schedules(db, agent_id)
        return [ManagedAgentScheduleResponse.model_validate(item) for item in schedules]
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/schedules", response_model=ManagedAgentScheduleResponse, status_code=201)
def create_schedule(
    agent_id: str,
    req: ManagedAgentScheduleCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建定时任务。"""
    try:
        schedule = svc.create_schedule(
            db,
            agent_id,
            **req.model_dump(),
        )
        return ManagedAgentScheduleResponse.model_validate(schedule)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.put("/{agent_id}/schedules/{schedule_id}", response_model=ManagedAgentScheduleResponse)
def update_schedule(
    agent_id: str,
    schedule_id: str,
    req: ManagedAgentScheduleUpdateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新定时任务。"""
    try:
        schedule = svc.update_schedule_for_agent(
            db,
            agent_id,
            schedule_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return ManagedAgentScheduleResponse.model_validate(schedule)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{agent_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    agent_id: str,
    schedule_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """删除定时任务。"""
    try:
        svc.delete_schedule_for_agent(db, agent_id, schedule_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

