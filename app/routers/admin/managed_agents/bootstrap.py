"""配置态 Agent Bootstrap 路由。"""

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError, ValidationError
from app.schemas.managed_agent import (
    ManagedAgentBootstrapScriptResponse,
    ManagedAgentBootstrapTokenCreateRequest,
    ManagedAgentBootstrapTokenCreateResponse,
    ManagedAgentBootstrapTokenListItem,
    ManagedAgentOnboardingMessageResponse,
)
from app.services import bootstrap as bootstrap_svc


router = APIRouter(prefix="/admin/managed-agents")


def _parse_scope_json(scope_json: str | None) -> dict | None:
    """把 scope_json 解析为字典。"""
    if scope_json is None:
        return None
    try:
        parsed = json.loads(scope_json)
    except json.JSONDecodeError as exc:
        raise ValidationError("scope_json 必须是合法 JSON") from exc
    if parsed is not None and not isinstance(parsed, dict):
        raise ValidationError("scope_json 必须是 JSON object")
    return parsed


def _build_script_scope(
    selected_artifacts: list[str] | None,
    include_schedule: bool,
    include_comm_bindings: bool,
) -> dict:
    """构造脚本下载 token 的 scope。"""
    scope = {
        "include_schedule": include_schedule,
        "include_comm_bindings": include_comm_bindings,
    }
    if selected_artifacts is not None:
        scope["selected_artifacts"] = selected_artifacts
    return scope


@router.post(
    "/{agent_id}/bootstrap-tokens",
    response_model=ManagedAgentBootstrapTokenCreateResponse,
    status_code=201,
)
def create_bootstrap_token(
    agent_id: str,
    req: ManagedAgentBootstrapTokenCreateRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """创建某个配置态 Agent 的 Bootstrap Token。"""
    try:
        created = bootstrap_svc.create_bootstrap_token(
            db,
            managed_agent_id=agent_id,
            purpose=req.purpose,
            ttl_seconds=req.ttl_seconds,
            scope=_parse_scope_json(req.scope_json),
        )
        created["scope_json"] = req.scope_json
        return ManagedAgentBootstrapTokenCreateResponse.model_validate(created)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/bootstrap-tokens", response_model=list[ManagedAgentBootstrapTokenListItem])
def list_bootstrap_tokens(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """列出某个配置态 Agent 的 Bootstrap Token 状态。"""
    try:
        tokens = bootstrap_svc.list_bootstrap_tokens(db, agent_id)
        return [
            ManagedAgentBootstrapTokenListItem.model_validate(bootstrap_svc.serialize_bootstrap_token(item))
            for item in tokens
        ]
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.delete("/{agent_id}/bootstrap-tokens/{token_id}", status_code=204)
def revoke_bootstrap_token(
    agent_id: str,
    token_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """撤销某个配置态 Agent 的 Bootstrap Token。"""
    try:
        bootstrap_svc.revoke_bootstrap_token(db, token_id, managed_agent_id=agent_id)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/bootstrap-script", response_model=ManagedAgentBootstrapScriptResponse)
def get_bootstrap_script(
    agent_id: str,
    _: bool = Depends(verify_admin),
    selected_artifacts: list[str] | None = Query(None),
    include_schedule: bool = Query(True),
    include_comm_bindings: bool = Query(True),
    register_ttl_seconds: int = Query(3600, gt=0),
    bundle_ttl_seconds: int = Query(86400, gt=0),
    db: Session = Depends(get_db),
):
    """生成当前配置态 Agent 的 Bootstrap 脚本预览。"""
    try:
        register_token = bootstrap_svc.create_bootstrap_token(
            db,
            managed_agent_id=agent_id,
            purpose="register_runtime",
            ttl_seconds=register_ttl_seconds,
        )
        bundle_scope = _build_script_scope(
            selected_artifacts=selected_artifacts,
            include_schedule=include_schedule,
            include_comm_bindings=include_comm_bindings,
        )
        bundle_token = bootstrap_svc.create_or_reissue_bootstrap_token(
            db,
            managed_agent_id=agent_id,
            purpose="download_script",
            ttl_seconds=bundle_ttl_seconds,
            scope=bundle_scope,
            min_remaining_seconds=bootstrap_svc.DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS,
        )
        script = bootstrap_svc.render_bootstrap_script(
            db,
            managed_agent_id=agent_id,
            register_token=register_token["token"],
            skill_bundle_token=bundle_token["token"],
            selected_artifacts=bundle_scope.get("selected_artifacts"),
            include_schedule=bundle_scope["include_schedule"],
            include_comm_bindings=bundle_scope["include_comm_bindings"],
        )
        return ManagedAgentBootstrapScriptResponse(
            script=script,
            register_token_id=register_token["id"],
            register_token_expires_at=register_token["expires_at"],
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/onboarding-message", response_model=ManagedAgentOnboardingMessageResponse)
def get_onboarding_message(
    agent_id: str,
    _: bool = Depends(verify_admin),
    selected_artifacts: list[str] | None = Query(None),
    include_schedule: bool = Query(True),
    include_comm_bindings: bool = Query(True),
    download_ttl_seconds: int = Query(86400, gt=0),
    db: Session = Depends(get_db),
):
    """生成当前配置态 Agent 的接入说明和 curl 命令。"""
    try:
        download_scope = _build_script_scope(
            selected_artifacts=selected_artifacts,
            include_schedule=include_schedule,
            include_comm_bindings=include_comm_bindings,
        )
        download_token = bootstrap_svc.create_or_reissue_bootstrap_token(
            db,
            managed_agent_id=agent_id,
            purpose="download_script",
            ttl_seconds=download_ttl_seconds,
            scope=download_scope,
            min_remaining_seconds=bootstrap_svc.DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS,
        )
        curl_command = bootstrap_svc.render_curl_command(agent_id, download_token["token"])
        message = bootstrap_svc.render_onboarding_message(
            db,
            managed_agent_id=agent_id,
            download_token=download_token["token"],
        )
        return ManagedAgentOnboardingMessageResponse(
            message=message,
            curl_command=curl_command,
            download_token_id=download_token["id"],
            download_token_expires_at=download_token["expires_at"],
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))

