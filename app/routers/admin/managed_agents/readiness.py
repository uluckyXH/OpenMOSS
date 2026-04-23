"""配置态 Agent 就绪度与运行态身份相关路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    ManagedAgentDetail,
    ManagedAgentReadiness,
    ManagedAgentRuntimeApiKeyResetResponse,
    ManagedAgentRuntimeIdentity,
)
from app.services import managed_agent as svc


router = APIRouter(prefix="/admin/managed-agents")


def _needs_redeploy(agent) -> bool:
    """判断配置版本是否落后于已部署版本。"""
    return (
        agent.deployed_config_version is not None
        and agent.config_version != agent.deployed_config_version
    )


def apply_agent_projection(
    response,
    agent,
    readiness: dict[str, object],
    runtime_identity: dict[str, object],
):
    """补齐非模型直出字段。"""
    response.needs_redeploy = _needs_redeploy(agent)
    response.readiness = ManagedAgentReadiness.model_validate(readiness)
    response.runtime_identity = ManagedAgentRuntimeIdentity.model_validate(runtime_identity)
    return response


def agent_detail_response(db: Session, agent) -> ManagedAgentDetail:
    """生成带派生字段的详情响应。"""
    return apply_agent_projection(
        ManagedAgentDetail.model_validate(agent),
        agent,
        svc.compute_readiness_for_agent(db, agent),
        svc.compute_runtime_identity_for_agent(db, agent),
    )


@router.post("/{agent_id}/runtime-api-key/reset", response_model=ManagedAgentRuntimeApiKeyResetResponse)
def reset_runtime_api_key(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """重置配置态 Agent 关联运行态 Agent 的 API Key。"""
    try:
        return ManagedAgentRuntimeApiKeyResetResponse.model_validate(
            svc.reset_runtime_api_key_for_managed_agent(db, agent_id)
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

