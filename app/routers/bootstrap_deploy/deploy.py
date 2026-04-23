"""
部署回传路由 — 公开 API（脚本调用，非 admin）

脚本执行完毕后通过此端点回传执行结果。
使用 bootstrap token 认证。
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import DeployReportRequest
from app.services.bootstrap import validate_bootstrap_token
from app.services.managed_agent.deployment import (
    confirm_deployment_snapshot,
    fail_deployment_snapshot,
)


router = APIRouter(prefix="/deploy", tags=["Deploy"])


@router.post("/{managed_agent_id}/report")
def report_deployment_result(
    managed_agent_id: str,
    body: DeployReportRequest,
    x_bootstrap_token: str = Header(..., alias="X-Bootstrap-Token"),
    db: Session = Depends(get_db),
):
    """脚本执行结果回传（confirmed / failed）。"""
    try:
        validate_bootstrap_token(
            db,
            token=x_bootstrap_token,
            managed_agent_id=managed_agent_id,
            purpose="register_runtime",
        )

        if body.status == "confirmed":
            snapshot = confirm_deployment_snapshot(
                db, body.snapshot_id, managed_agent_id,
            )
        else:
            snapshot = fail_deployment_snapshot(
                db, body.snapshot_id, managed_agent_id,
                exit_code=body.exit_code,
                last_stage=body.last_stage,
                message=body.message,
            )

        return {"snapshot_id": snapshot.id, "status": snapshot.status}

    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
