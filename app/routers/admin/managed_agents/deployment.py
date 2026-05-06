"""配置态 Agent 部署变更集与快照路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import verify_admin
from app.database import get_db
from app.exceptions import BusinessError
from app.schemas.managed_agent import (
    DeployPreviewRequest,
    DeployPreviewResponse,
    DeployScriptRequest,
    DeploySnapshotDismissRequest,
    DeploymentSnapshotDetailResponse,
    DeploymentSnapshotListItem,
    DeploymentStateResponse,
)
from app.services import bootstrap as bootstrap_svc
from app.services import managed_agent as svc


router = APIRouter(prefix="/admin/managed-agents")

_OPENCLAW_PROMPT_KEYS = ["system_prompt", "persona_prompt", "identity"]


def _get_renderer_prompt_keys(host_platform: str) -> list[str]:
    """获取当前平台 renderer 支持的 prompt artifact key 列表。"""
    if host_platform == "openclaw":
        return _OPENCLAW_PROMPT_KEYS
    return []


def _build_deployment_snapshot_conflict_detail(snapshot) -> dict:
    """构造同类 pending 快照冲突响应。"""
    data = svc.serialize_deployment_snapshot(snapshot)
    created_at = data["created_at"]
    expires_at = data["expires_at"]
    return {
        "error_code": "DEPLOYMENT_SNAPSHOT_CONFLICT",
        "message": "当前 Agent 已存在一份未完成的同类部署脚本。确认重新生成后，旧脚本和旧 Token 将失效。",
        "conflict_snapshot": {
            "id": data["id"],
            "script_intent": data["script_intent"],
            "created_at": created_at.isoformat() if created_at else None,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_likely_timeout": data["is_likely_timeout"],
        },
    }


def _build_deploy_request_from_snapshot(snapshot) -> DeployScriptRequest:
    """从快照资源清单恢复变更集计算请求。"""
    snapshot_data = svc.parse_snapshot_json(snapshot.snapshot_json)
    return DeployScriptRequest(
        script_intent=snapshot.script_intent,
        prompt_artifact_keys=snapshot_data.get("prompt_artifact_keys", []),
        schedule_ids=[
            item.get("id")
            for item in snapshot_data.get("schedules", [])
            if item.get("id")
        ],
        comm_binding_ids=[
            item.get("id")
            for item in snapshot_data.get("comm_bindings", [])
            if item.get("id")
        ],
    )


def _build_snapshot_download_context(
    db: Session,
    *,
    agent_id: str,
    snapshot,
) -> dict:
    """为 pending 快照生成可执行接入命令，不新增重复 Token 记录。"""
    serialized = svc.serialize_deployment_snapshot(snapshot)
    if snapshot.status != "pending":
        return {
            "curl_command": None,
            "onboarding_message": None,
            "download_token_id": None,
            "download_token_expires_at": None,
            "download_available": False,
            "download_unavailable_reason": f"快照状态为 {snapshot.status}，不可继续下载执行脚本",
        }
    if serialized["is_likely_timeout"]:
        return {
            "curl_command": None,
            "onboarding_message": None,
            "download_token_id": None,
            "download_token_expires_at": None,
            "download_available": False,
            "download_unavailable_reason": "部署快照已超过超时截止时间，请重新生成部署脚本",
        }

    ttl_seconds = 86400
    if snapshot.expires_at:
        remaining_seconds = int((snapshot.expires_at - datetime.now()).total_seconds())
        ttl_seconds = max(60, min(86400, remaining_seconds))

    download_token = bootstrap_svc.create_or_reissue_bootstrap_token(
        db,
        managed_agent_id=agent_id,
        purpose="download_script",
        ttl_seconds=ttl_seconds,
        scope={
            "deployment_snapshot_id": snapshot.id,
            "script_intent": snapshot.script_intent,
        },
        min_remaining_seconds=0,
        deployment_snapshot_id=snapshot.id,
    )
    curl_command = bootstrap_svc.render_curl_command(agent_id, download_token["token"])
    onboarding_message = bootstrap_svc.render_onboarding_message(
        db,
        managed_agent_id=agent_id,
        download_token=download_token["token"],
    )
    return {
        "curl_command": curl_command,
        "onboarding_message": onboarding_message,
        "download_token_id": download_token["id"],
        "download_token_expires_at": download_token["expires_at"],
        "download_available": True,
        "download_unavailable_reason": None,
    }


@router.get("/{agent_id}/deployment-state", response_model=DeploymentStateResponse)
def get_agent_deployment_state(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """获取脚本生成入口需要的部署阶段与推荐意图。"""
    try:
        return DeploymentStateResponse.model_validate(
            svc.compute_deployment_state(db, agent_id)
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/deploy-preview", response_model=DeployPreviewResponse)
def deploy_preview(
    agent_id: str,
    body: DeployPreviewRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """变更预检：返回 diff 结果 + 校验状态。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        prompt_keys = _get_renderer_prompt_keys(agent.host_platform)

        request_for_changeset = DeployScriptRequest(
            script_intent=body.script_intent,
            prompt_artifact_keys=body.prompt_artifact_keys,
            schedule_ids=body.schedule_ids,
            comm_binding_ids=body.comm_binding_ids,
        )

        changeset = svc.compute_changeset(
            db,
            agent_id,
            request_for_changeset,
            renderer_prompt_keys=prompt_keys,
        )

        has_removals = any(item.change_type == "remove" for item in changeset.items)

        return DeployPreviewResponse(
            script_intent=body.script_intent,
            changeset=changeset,
            has_removals=has_removals,
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/deploy-script")
def deploy_script(
    agent_id: str,
    body: DeployScriptRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """生成部署脚本并写入 pending 快照。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        prompt_keys = _get_renderer_prompt_keys(agent.host_platform)

        changeset = svc.compute_changeset(
            db,
            agent_id,
            body,
            renderer_prompt_keys=prompt_keys,
        )
        if not changeset.is_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "变更集校验失败",
                    "errors": changeset.validation_errors,
                },
            )

        if body.script_intent == "sync" and not (
            body.prompt_artifact_keys or body.schedule_ids or body.comm_binding_ids
        ):
            raise HTTPException(status_code=422, detail="sync 意图必须选择至少一类资源")

        conflict_snapshot = svc.get_pending_deployment_snapshot_conflict(
            db,
            agent_id,
            body.script_intent,
        )
        if conflict_snapshot is not None and not body.replace_pending_snapshot:
            raise HTTPException(
                status_code=409,
                detail=_build_deployment_snapshot_conflict_detail(conflict_snapshot),
            )
        if conflict_snapshot is not None:
            svc.cancel_pending_deployment_snapshots(
                db,
                agent_id,
                body.script_intent,
            )

        schedules = svc.list_schedules(db, agent_id)
        schedule_map = {item.id: item for item in schedules}
        bindings = svc.list_comm_bindings(db, agent_id)
        binding_map = {item.id: item for item in bindings}

        snapshot_json = svc.build_snapshot_json(
            prompt_artifact_keys=body.prompt_artifact_keys,
            schedules=[
                {"id": schedule_id, "name": schedule_map[schedule_id].name}
                for schedule_id in body.schedule_ids
                if schedule_id in schedule_map
            ],
            comm_bindings=[
                {
                    "id": binding_id,
                    "provider": binding_map[binding_id].provider,
                    "binding_key": binding_map[binding_id].binding_key,
                }
                for binding_id in body.comm_binding_ids
                if binding_id in binding_map
            ],
        )

        snapshot = svc.create_deployment_snapshot(
            db,
            managed_agent_id=agent_id,
            script_intent=body.script_intent,
            config_version=agent.config_version,
            snapshot_json=snapshot_json,
            timeout_seconds=body.snapshot_timeout_seconds,
        )
        bootstrap_svc.create_or_reissue_bootstrap_token(
            db,
            managed_agent_id=agent_id,
            purpose="download_script",
            ttl_seconds=body.download_ttl_seconds,
            scope={
                "deployment_snapshot_id": snapshot.id,
                "script_intent": snapshot.script_intent,
            },
            min_remaining_seconds=bootstrap_svc.DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS,
            deployment_snapshot_id=snapshot.id,
        )

        return {
            "snapshot_id": snapshot.id,
            "status": snapshot.status,
            "config_version": snapshot.config_version,
            "changeset": changeset.model_dump(),
        }
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post("/{agent_id}/deployment-snapshot/dismiss")
def dismiss_deployment_snapshot_resources(
    agent_id: str,
    body: DeploySnapshotDismissRequest,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """忽略已删除资源的清理提醒。"""
    try:
        svc.get_managed_agent_or_404(db, agent_id)
        snapshot = svc.dismiss_snapshot_resources(
            db,
            agent_id,
            schedule_ids=body.schedule_ids or None,
            comm_binding_ids=body.comm_binding_ids or None,
            prompt_artifact_keys=body.prompt_artifact_keys or None,
        )
        if snapshot is None:
            return {"message": "没有已确认的快照"}
        return {"message": "ok", "snapshot_id": snapshot.id}
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/{agent_id}/deployment-snapshots")
def list_agent_deployment_snapshots(
    agent_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看部署历史。"""
    try:
        snapshots = svc.list_deployment_snapshots(db, agent_id)
        return [svc.serialize_deployment_snapshot(item) for item in snapshots]
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get(
    "/{agent_id}/deployment-snapshots/{snapshot_id}",
    response_model=DeploymentSnapshotDetailResponse,
)
def get_agent_deployment_snapshot(
    agent_id: str,
    snapshot_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """查看部署快照详情，恢复 changeset 与接入说明。"""
    try:
        agent = svc.get_managed_agent_or_404(db, agent_id)
        snapshot = svc.get_deployment_snapshot_or_404(db, snapshot_id, agent_id)
        request_for_changeset = _build_deploy_request_from_snapshot(snapshot)
        changeset = svc.compute_changeset(
            db,
            agent_id,
            request_for_changeset,
            renderer_prompt_keys=_get_renderer_prompt_keys(agent.host_platform),
        )
        has_removals = any(item.change_type == "remove" for item in changeset.items)
        payload = svc.serialize_deployment_snapshot(snapshot)
        payload.update(
            {
                "changeset": changeset,
                "has_removals": has_removals,
                **_build_snapshot_download_context(
                    db,
                    agent_id=agent_id,
                    snapshot=snapshot,
                ),
            }
        )
        return DeploymentSnapshotDetailResponse.model_validate(payload)
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))


@router.post(
    "/{agent_id}/deployment-snapshots/{snapshot_id}/cancel",
    response_model=DeploymentSnapshotListItem,
)
def cancel_agent_deployment_snapshot(
    agent_id: str,
    snapshot_id: str,
    _: bool = Depends(verify_admin),
    db: Session = Depends(get_db),
):
    """手动取消 pending 部署快照，并撤销关联 Token。"""
    try:
        snapshot = svc.cancel_deployment_snapshot(db, snapshot_id, agent_id)
        return DeploymentSnapshotListItem.model_validate(
            svc.serialize_deployment_snapshot(snapshot)
        )
    except BusinessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc))
