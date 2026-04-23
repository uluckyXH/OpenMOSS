"""Bootstrap Token 生命周期管理：创建、校验、撤销、列表。"""

from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.models.managed_agent import ManagedAgentBootstrapToken
from app.services.managed_agent.core import get_managed_agent_or_404


BOOTSTRAP_PURPOSES = {"download_script", "register_runtime"}
DOWNLOAD_SCRIPT_MIN_REUSE_REMAINING_SECONDS = 3600


def hash_bootstrap_token(token: str) -> str:
    """对明文 token 做哈希。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_bootstrap_token_value() -> str:
    return f"bt_{secrets.token_urlsafe(32)}"


def _serialize_scope(scope: Optional[dict[str, Any]]) -> Optional[str]:
    if scope is None:
        return None
    return json.dumps(scope, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _serialize_created_bootstrap_token(
    row: ManagedAgentBootstrapToken,
    token: str,
) -> dict[str, Any]:
    return {
        "id": row.id,
        "managed_agent_id": row.managed_agent_id,
        "token": token,
        "purpose": row.purpose,
        "expires_at": row.expires_at,
        "created_at": row.created_at,
    }


def is_bootstrap_token_valid(
    bootstrap_token: ManagedAgentBootstrapToken,
    at: Optional[datetime] = None,
) -> bool:
    """判断 token 当前是否有效。"""
    now = at or datetime.now()

    if bootstrap_token.revoked_at is not None:
        return False
    if bootstrap_token.expires_at <= now:
        return False
    if bootstrap_token.purpose == "register_runtime" and bootstrap_token.used_at is not None:
        return False
    return True


def create_bootstrap_token(
    db: Session,
    managed_agent_id: str,
    purpose: str,
    ttl_seconds: int,
    scope: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """创建 bootstrap token，并返回一次性明文 token。"""
    get_managed_agent_or_404(db, managed_agent_id)

    if purpose not in BOOTSTRAP_PURPOSES:
        raise ValidationError(f"不支持的 bootstrap token purpose: {purpose}")
    if ttl_seconds <= 0:
        raise ValidationError("ttl_seconds 必须大于 0")

    token = _issue_bootstrap_token_value()
    now = datetime.now()
    row = ManagedAgentBootstrapToken(
        id=str(uuid.uuid4()),
        managed_agent_id=managed_agent_id,
        token_hash=hash_bootstrap_token(token),
        purpose=purpose,
        scope_json=_serialize_scope(scope),
        expires_at=now + timedelta(seconds=ttl_seconds),
        created_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    return _serialize_created_bootstrap_token(row, token)


def create_or_reissue_bootstrap_token(
    db: Session,
    managed_agent_id: str,
    purpose: str,
    ttl_seconds: int,
    scope: Optional[dict[str, Any]] = None,
    min_remaining_seconds: int = 0,
) -> dict[str, Any]:
    """优先复用同 scope 的有效 token 记录，避免重复创建。

    注意：当前数据库只存 token_hash，不存明文 token。
    因此复用时会对同一条记录重新签发一个新的明文 token，
    旧明文 token 随即失效，但记录 id / expires_at 不变。
    """
    get_managed_agent_or_404(db, managed_agent_id)

    if purpose not in BOOTSTRAP_PURPOSES:
        raise ValidationError(f"不支持的 bootstrap token purpose: {purpose}")
    if ttl_seconds <= 0:
        raise ValidationError("ttl_seconds 必须大于 0")
    if min_remaining_seconds < 0:
        raise ValidationError("min_remaining_seconds 不能小于 0")

    now = datetime.now()
    serialized_scope = _serialize_scope(scope)
    query = (
        db.query(ManagedAgentBootstrapToken)
        .filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
        .filter(ManagedAgentBootstrapToken.purpose == purpose)
        .filter(ManagedAgentBootstrapToken.revoked_at.is_(None))
        .filter(ManagedAgentBootstrapToken.expires_at > now)
    )
    if purpose == "register_runtime":
        query = query.filter(ManagedAgentBootstrapToken.used_at.is_(None))

    if serialized_scope is None:
        query = query.filter(ManagedAgentBootstrapToken.scope_json.is_(None))
    else:
        query = query.filter(ManagedAgentBootstrapToken.scope_json == serialized_scope)

    reusable = (
        query.order_by(
            ManagedAgentBootstrapToken.expires_at.desc(),
            ManagedAgentBootstrapToken.created_at.desc(),
        )
        .first()
    )

    if reusable:
        remaining_seconds = (reusable.expires_at - now).total_seconds()
        if remaining_seconds > min_remaining_seconds:
            token = _issue_bootstrap_token_value()
            reusable.token_hash = hash_bootstrap_token(token)
            reusable.created_at = now
            db.commit()
            db.refresh(reusable)
            return _serialize_created_bootstrap_token(reusable, token)

    return create_bootstrap_token(
        db,
        managed_agent_id=managed_agent_id,
        purpose=purpose,
        ttl_seconds=ttl_seconds,
        scope=scope,
    )


def list_bootstrap_tokens(db: Session, managed_agent_id: str) -> list[ManagedAgentBootstrapToken]:
    """列出某个 Agent 的 bootstrap token。"""
    get_managed_agent_or_404(db, managed_agent_id)
    return (
        db.query(ManagedAgentBootstrapToken)
        .filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
        .order_by(ManagedAgentBootstrapToken.created_at.desc())
        .all()
    )


def get_bootstrap_token_or_404(
    db: Session,
    token_id: str,
    managed_agent_id: Optional[str] = None,
) -> ManagedAgentBootstrapToken:
    """按 id 获取 bootstrap token。"""
    query = db.query(ManagedAgentBootstrapToken).filter(ManagedAgentBootstrapToken.id == token_id)
    if managed_agent_id is not None:
        query = query.filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
    token = query.first()
    if not token:
        raise NotFoundError(f"Bootstrap Token 不存在: {token_id}")
    return token


def validate_bootstrap_token(
    db: Session,
    token: str,
    managed_agent_id: str,
    purpose: str,
) -> ManagedAgentBootstrapToken:
    """校验 bootstrap token，返回对应记录。"""
    if purpose not in BOOTSTRAP_PURPOSES:
        raise ValidationError(f"不支持的 bootstrap token purpose: {purpose}")

    token_hash = hash_bootstrap_token(token)
    row = (
        db.query(ManagedAgentBootstrapToken)
        .filter(ManagedAgentBootstrapToken.token_hash == token_hash)
        .filter(ManagedAgentBootstrapToken.managed_agent_id == managed_agent_id)
        .filter(ManagedAgentBootstrapToken.purpose == purpose)
        .first()
    )
    if not row or not is_bootstrap_token_valid(row):
        raise ForbiddenError("无效或已过期的 Bootstrap Token")
    return row


def revoke_bootstrap_token(
    db: Session,
    token_id: str,
    managed_agent_id: Optional[str] = None,
) -> ManagedAgentBootstrapToken:
    """撤销 bootstrap token。"""
    row = get_bootstrap_token_or_404(db, token_id, managed_agent_id=managed_agent_id)
    if row.revoked_at is None:
        row.revoked_at = datetime.now()
        db.commit()
        db.refresh(row)
    return row


def mark_bootstrap_token_used(
    db: Session,
    token_id: str,
    managed_agent_id: Optional[str] = None,
) -> ManagedAgentBootstrapToken:
    """标记 bootstrap token 已使用。"""
    row = get_bootstrap_token_or_404(db, token_id, managed_agent_id=managed_agent_id)
    if row.used_at is None:
        row.used_at = datetime.now()
        db.commit()
        db.refresh(row)
    return row


def serialize_bootstrap_token(bootstrap_token: ManagedAgentBootstrapToken) -> dict[str, Any]:
    """序列化 bootstrap token 列表项，不返回明文 token。"""
    return {
        "id": bootstrap_token.id,
        "managed_agent_id": bootstrap_token.managed_agent_id,
        "token_masked": "仅创建时可见",
        "purpose": bootstrap_token.purpose,
        "scope_json": bootstrap_token.scope_json,
        "expires_at": bootstrap_token.expires_at,
        "used_at": bootstrap_token.used_at,
        "revoked_at": bootstrap_token.revoked_at,
        "created_at": bootstrap_token.created_at,
        "is_valid": is_bootstrap_token_valid(bootstrap_token),
    }


def deserialize_bootstrap_scope(bootstrap_token: ManagedAgentBootstrapToken) -> dict[str, Any]:
    """把 token.scope_json 解析为作用域字典。"""
    if not bootstrap_token.scope_json:
        return {}
    try:
        parsed = json.loads(bootstrap_token.scope_json)
    except json.JSONDecodeError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed
