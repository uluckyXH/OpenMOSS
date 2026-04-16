"""
OpenClaw + Feishu 通讯绑定适配器。

职责：
- 定义 Feishu 绑定的表单 schema（字段定义）
- 校验 Feishu 绑定参数
- 结构化 DTO ↔ 通用 comm_binding 表的双向映射
- 提供结构化 CRUD（底层调用 comm_binding 通用服务）

设计文档：
  dev-docs/agent-config-center/12-平台适配接口与动态表单设计/
    platforms/openclaw/03-OpenClaw-Feishu通讯绑定设计.md
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.exceptions import ConflictError, ValidationError
from app.models.managed_agent import ManagedAgentCommBinding
from app.services.managed_agent.comm_binding import (
    create_comm_binding,
    delete_comm_binding_for_agent,
    get_comm_binding_for_agent_or_404,
    list_comm_bindings,
    update_comm_binding,
)
from app.services.managed_agent.core import get_managed_agent_or_404
from app.services.managed_agent.host_config import get_host_config
from app.services.managed_agent.shared import _mask

from ...base import CommProviderAdapter

PROVIDER = "feishu"


# ============================================================
# Schema 定义
# ============================================================

FEISHU_BINDING_SCHEMA: Dict[str, Any] = {
    "provider": PROVIDER,
    "label": "飞书（Feishu）",
    "description": (
        "为 Agent 配置飞书通讯渠道。"
        "绑定后即可在飞书中与该 Agent 对话，"
        "Agent 通过飞书机器人自动收发消息。"
        "支持绑定多个飞书账号，对应不同的飞书应用。"
    ),
    "supports_multiple_bindings": True,
    "fields": [
        {
            "key": "account_id",
            "label": "OpenClaw 内部账号标识",
            "type": "text",
            "required": False,
            "advanced": True,
            "placeholder": "留空自动生成（推荐）",
            "description": (
                "OpenClaw 中用于标识这条飞书机器人账号配置的内部 key。"
                "对应的账号配置会在 OpenClaw 中保存该机器人的 app_id、app_secret 等信息。"
                "它不是飞书官方账号 ID，也不是在飞书侧看到的名称，"
                "而是 OpenClaw 内部用来区分、存储和引用这条飞书机器人配置的键。"
                "留空时系统会根据当前 Agent 的 OpenClaw Agent ID 自动生成。"
            ),
        },
        {
            "key": "app_id",
            "label": "飞书 App ID",
            "type": "text",
            "required": True,
            "placeholder": "cli_xxxxxxxxxxxx",
            "description": "飞书开放平台的应用凭证，可在「凭证与基础信息」页面获取。",
        },
        {
            "key": "app_secret",
            "label": "飞书 App Secret",
            "type": "password",
            "required": True,
            "sensitive": True,
            "placeholder": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "description": "飞书应用密钥，与 App ID 配对使用，可在「凭证与基础信息」页面获取。提交后加密存储。",
        },
        {
            "key": "account_name",
            "label": "账号备注名",
            "type": "text",
            "required": False,
            "placeholder": "我的飞书助手",
            "description": (
                "给 OpenClaw 配置中这条飞书账号写的备注名。"
                "主要用于自己识别和管理，不是功能性参数；"
                "可能会在部分界面展示，但不保证处处显示，不填也不影响飞书绑定本身。"
            ),
        },
        {
            "key": "enabled",
            "label": "是否启用",
            "type": "switch",
            "required": False,
            "default": True,
            "description": "关闭后 Agent 将暂停通过此账号收发飞书消息。",
        },
    ],
}


# ============================================================
# DTO ↔ 通用表映射
# ============================================================


def _dto_to_generic_kwargs(data: Dict[str, Any]) -> Dict[str, Any]:
    """结构化 DTO → 通用 comm_binding 创建/更新参数。

    映射关系（设计文档 §5）：
    - account_id    → binding_key
    - account_name  → display_name
    - app_id + app_secret → config_payload（JSON 序列化）
    - provider      → 固定 "feishu"
    """
    kwargs: Dict[str, Any] = {"provider": PROVIDER}

    if "account_id" in data:
        kwargs["binding_key"] = data["account_id"].strip()

    if "account_name" in data:
        kwargs["display_name"] = data.get("account_name")

    if "enabled" in data:
        kwargs["enabled"] = data["enabled"]

    # app_id / app_secret → config_payload JSON
    payload_parts: Dict[str, str] = {}
    if "app_id" in data:
        payload_parts["app_id"] = data["app_id"].strip()
    if "app_secret" in data:
        payload_parts["app_secret"] = data["app_secret"].strip()
    if payload_parts:
        kwargs["config_payload"] = json.dumps(payload_parts, ensure_ascii=False)

    return kwargs


def _generic_to_dto(binding: ManagedAgentCommBinding) -> Dict[str, Any]:
    """通用 comm_binding 记录 → 结构化 Feishu DTO（GET 响应）。

    - binding_key    → account_id
    - display_name   → account_name
    - config_payload_encrypted → 解析出 app_id_masked / app_secret_masked
    """
    # 解析 config_payload
    app_id_masked = ""
    app_secret_masked = "***"
    if binding.config_payload_encrypted:
        try:
            payload = json.loads(binding.config_payload_encrypted)
            app_id_masked = payload.get("app_id", "")
            raw_secret = payload.get("app_secret", "")
            app_secret_masked = "***" if raw_secret else ""
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": binding.id,
        "provider": PROVIDER,
        "account_id": binding.binding_key,
        "account_name": binding.display_name,
        "enabled": binding.enabled,
        "app_id_masked": app_id_masked,
        "app_secret_masked": app_secret_masked,
        "created_at": binding.created_at,
        "updated_at": binding.updated_at,
    }


# ============================================================
# 校验
# ============================================================


def _validate_feishu_data(data: Dict[str, Any], *, partial: bool = False) -> List[str]:
    """校验 Feishu 绑定数据，返回错误列表。

    partial=True 时用于 UPDATE，不要求必填字段都存在。
    account_id 为可选字段（可由后端自动生成），不做必填校验。
    """
    errors: List[str] = []

    if not partial:
        # 创建时必填校验（account_id 可选，不在此校验）
        for field in ("app_id", "app_secret"):
            value = data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                errors.append(f"{field} 不能为空")
    else:
        # 更新时，如果传了就不能是空串
        for field in ("account_id", "app_id", "app_secret"):
            if field in data:
                value = data[field]
                if isinstance(value, str) and not value.strip():
                    errors.append(f"{field} 不能为空")

    # account_id 如果显式传了，也不能为空白
    if "account_id" in data and not partial:
        value = data["account_id"]
        if value is not None and isinstance(value, str) and not value.strip():
            errors.append("account_id 不能为空白字符串")

    return errors


# ============================================================
# account_id 自动生成
# ============================================================


def _get_host_agent_identifier(db: Session, managed_agent_id: str) -> str:
    """获取当前 Agent 的 host_agent_identifier，不存在则报错。"""
    host_config = get_host_config(db, managed_agent_id)
    identifier = (
        host_config.host_agent_identifier.strip()
        if host_config and host_config.host_agent_identifier
        else ""
    )
    if not identifier:
        raise ValidationError(
            "当前 Agent 尚未配置 OpenClaw Agent ID（host_agent_identifier），"
            "无法自动生成飞书账号标识，请先完成平台配置或手动填写 account_id"
        )
    return identifier


def _generate_unique_account_id(
    db: Session, managed_agent_id: str, base: str,
) -> str:
    """生成不重复的 account_id，已存在时自动追加序号。"""
    candidate = base
    suffix = 2
    while True:
        exists = db.query(ManagedAgentCommBinding).filter(
            ManagedAgentCommBinding.managed_agent_id == managed_agent_id,
            ManagedAgentCommBinding.provider == PROVIDER,
            ManagedAgentCommBinding.binding_key == candidate,
        ).first()
        if not exists:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def _resolve_account_id(db: Session, managed_agent_id: str) -> str:
    """根据 host_agent_identifier 自动生成唯一 account_id。"""
    identifier = _get_host_agent_identifier(db, managed_agent_id)
    base = f"{identifier}-feishu"
    return _generate_unique_account_id(db, managed_agent_id, base)


# ============================================================
# 唯一性校验
# ============================================================


def _check_duplicate_binding(
    db: Session,
    managed_agent_id: str,
    account_id: str,
    *,
    exclude_binding_id: str | None = None,
) -> None:
    """检查同 Agent 下是否已存在相同 provider + account_id 的绑定。"""
    query = db.query(ManagedAgentCommBinding).filter(
        ManagedAgentCommBinding.managed_agent_id == managed_agent_id,
        ManagedAgentCommBinding.provider == PROVIDER,
        ManagedAgentCommBinding.binding_key == account_id,
    )
    if exclude_binding_id:
        query = query.filter(ManagedAgentCommBinding.id != exclude_binding_id)

    if query.first():
        raise ConflictError(
            f"该 Agent 下已存在 Feishu 账号 {account_id} 的绑定"
        )


# ============================================================
# Adapter 实现
# ============================================================


class OpenClawFeishuAdapter(CommProviderAdapter):
    """OpenClaw + Feishu 通讯绑定适配器。"""

    def get_provider_key(self) -> str:
        return PROVIDER

    def get_binding_schema(self) -> Dict[str, Any]:
        return FEISHU_BINDING_SCHEMA.copy()

    def validate_binding(self, data: Dict[str, Any]) -> Dict[str, Any]:
        errors = _validate_feishu_data(data, partial=False)
        return {"valid": len(errors) == 0, "errors": errors}

    def create_binding(
        self,
        db: Session,
        managed_agent_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        # 校验
        errors = _validate_feishu_data(data, partial=False)
        if errors:
            raise ValidationError("、".join(errors))

        # account_id 自动生成
        raw_account_id = data.get("account_id")
        if not raw_account_id or not raw_account_id.strip():
            account_id = _resolve_account_id(db, managed_agent_id)
            data["account_id"] = account_id
        else:
            account_id = raw_account_id.strip()

        # 唯一性校验
        _check_duplicate_binding(db, managed_agent_id, account_id)

        # DTO → 通用参数 → 创建
        kwargs = _dto_to_generic_kwargs(data)
        binding = create_comm_binding(db, managed_agent_id, **kwargs)

        return _generic_to_dto(binding)

    def update_binding(
        self,
        db: Session,
        managed_agent_id: str,
        binding_id: str,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        # 确认归属
        binding = get_comm_binding_for_agent_or_404(db, managed_agent_id, binding_id)

        # 确认是 feishu 绑定
        if binding.provider != PROVIDER:
            raise ValidationError(f"该绑定不是 Feishu 类型（实际为 {binding.provider}）")

        # 校验
        errors = _validate_feishu_data(data, partial=True)
        if errors:
            raise ValidationError("、".join(errors))

        # account_id 变更时做唯一性校验
        if "account_id" in data:
            new_account_id = data["account_id"].strip()
            if new_account_id != binding.binding_key:
                _check_duplicate_binding(
                    db, managed_agent_id, new_account_id, exclude_binding_id=binding_id
                )

        # 处理 config_payload 的部分更新：
        # 如果只更新了 app_id 或 app_secret 其中一个，需要保留另一个
        if ("app_id" in data or "app_secret" in data) and not (
            "app_id" in data and "app_secret" in data
        ):
            existing_payload: Dict[str, str] = {}
            if binding.config_payload_encrypted:
                try:
                    existing_payload = json.loads(binding.config_payload_encrypted)
                except (json.JSONDecodeError, TypeError):
                    pass
            if "app_id" in data:
                existing_payload["app_id"] = data["app_id"].strip()
            if "app_secret" in data:
                existing_payload["app_secret"] = data["app_secret"].strip()
            data["app_id"] = existing_payload.get("app_id", "")
            data["app_secret"] = existing_payload.get("app_secret", "")

        # DTO → 通用参数 → 更新
        kwargs = _dto_to_generic_kwargs(data)
        # 除掉 provider，通用更新不应改 provider
        kwargs.pop("provider", None)
        updated = update_comm_binding(db, binding_id, **kwargs)

        return _generic_to_dto(updated)

    def list_bindings(
        self,
        db: Session,
        managed_agent_id: str,
    ) -> List[Dict[str, Any]]:
        get_managed_agent_or_404(db, managed_agent_id)

        all_bindings = list_comm_bindings(db, managed_agent_id)
        return [
            _generic_to_dto(b)
            for b in all_bindings
            if b.provider == PROVIDER
        ]

    def delete_binding(
        self,
        db: Session,
        managed_agent_id: str,
        binding_id: str,
    ) -> None:
        # 确认归属且是 feishu 类型
        binding = get_comm_binding_for_agent_or_404(db, managed_agent_id, binding_id)
        if binding.provider != PROVIDER:
            raise ValidationError(f"该绑定不是 Feishu 类型（实际为 {binding.provider}）")

        delete_comm_binding_for_agent(db, managed_agent_id, binding_id)

    def suggest_binding_defaults(
        self,
        db: Session,
        managed_agent_id: str,
    ) -> Dict[str, Any]:
        """返回创建 Feishu 绑定时的建议默认值。

        - account_id: 基于 host_agent_identifier 自动生成（含去重）
        - host_agent_identifier: 当前 Agent 的 OpenClaw Agent ID
        """
        host_config = get_host_config(db, managed_agent_id)
        identifier = (
            host_config.host_agent_identifier.strip()
            if host_config and host_config.host_agent_identifier
            else ""
        )
        if not identifier:
            return {
                "account_id": None,
                "host_agent_identifier": None,
                "message": (
                    "当前 Agent 尚未配置 OpenClaw Agent ID，"
                    "无法自动生成飞书账号标识。请先完成平台配置。"
                ),
            }

        base = f"{identifier}-feishu"
        suggested = _generate_unique_account_id(db, managed_agent_id, base)
        return {
            "account_id": suggested,
            "host_agent_identifier": identifier,
        }
