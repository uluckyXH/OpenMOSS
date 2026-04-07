"""
Bootstrap 路由。

当前已提供：
- 脚本下载
- POST /api/bootstrap/agents/{id}/register
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import BusinessError
from app.services.bootstrap_service import (
    bootstrap_register,
    create_bootstrap_token,
    deserialize_bootstrap_scope,
    render_bootstrap_script,
    validate_bootstrap_token,
)


router = APIRouter(prefix="/bootstrap", tags=["Bootstrap"])


class BootstrapRegisterResponse(BaseModel):
    id: str
    name: str
    role: str
    api_key: str
    message: str = "Bootstrap 注册成功，请保存 API Key"


@router.get("/agents/{managed_agent_id}/script", response_class=PlainTextResponse)
async def download_bootstrap_script(
    managed_agent_id: str,
    x_bootstrap_token: str = Header(..., alias="X-Bootstrap-Token"),
    db: Session = Depends(get_db),
):
    """使用 download_script token 下载渲染后的部署脚本。"""
    try:
        download_token = validate_bootstrap_token(
            db,
            token=x_bootstrap_token,
            managed_agent_id=managed_agent_id,
            purpose="download_script",
        )
        scope = deserialize_bootstrap_scope(download_token)
        register_token = create_bootstrap_token(
            db,
            managed_agent_id=managed_agent_id,
            purpose="register_runtime",
            ttl_seconds=3600,
        )
        script = render_bootstrap_script(
            db,
            managed_agent_id=managed_agent_id,
            register_token=register_token["token"],
            selected_artifacts=scope.get("selected_artifacts"),
            include_schedule=scope.get("include_schedule", True),
            include_comm_bindings=scope.get("include_comm_bindings", True),
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return PlainTextResponse(script, media_type="text/x-shellscript")


@router.post("/agents/{managed_agent_id}/register", response_model=BootstrapRegisterResponse, status_code=201)
async def register_runtime_agent(
    managed_agent_id: str,
    x_bootstrap_token: str = Header(..., alias="X-Bootstrap-Token"),
    db: Session = Depends(get_db),
):
    """使用 register_runtime token 完成运行态注册。"""
    try:
        agent = bootstrap_register(
            db,
            managed_agent_id=managed_agent_id,
            token=x_bootstrap_token,
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

    return BootstrapRegisterResponse(
        id=agent.id,
        name=agent.name,
        role=agent.role,
        api_key=agent.api_key,
    )
