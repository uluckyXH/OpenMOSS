"""配置态 Agent 部署变更集与快照路由。"""

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
    DeploymentStateResponse,
)
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
