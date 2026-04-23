"""配置态 Agent 宿主配置路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import ManagedAgentHostConfigRequest, ManagedAgentHostConfigResponse
from app.services import managed_agent as svc


router = APIRouter(prefix="/admin/managed-agents")


@router.get("/{agent_id}/host-config", response_model=ManagedAgentHostConfigResponse)
def get_host_config(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取宿主平台配置。"""
    svc.get_managed_agent_or_404(db, agent_id)
    host_config = svc.get_host_config(db, agent_id)
    if not host_config:
        raise HTTPException(status_code=404, detail="宿主平台配置未配置")
    return ManagedAgentHostConfigResponse.model_validate(svc.serialize_host_config(host_config))


@router.put("/{agent_id}/host-config", response_model=ManagedAgentHostConfigResponse)
def update_host_config(
    agent_id: str,
    req: ManagedAgentHostConfigRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """更新宿主平台配置。"""
    try:
        host_config = svc.update_host_config(
            db,
            agent_id,
            **req.model_dump(include=req.model_fields_set),
        )
        return ManagedAgentHostConfigResponse.model_validate(svc.serialize_host_config(host_config))
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

