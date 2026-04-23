"""Bootstrap 注册：使用 register_runtime token 完成运行态注册并回写配置态。"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.exceptions import ConflictError
from app.models.agent import Agent
from app.services.agent_service import generate_api_key
from app.services.managed_agent.core import get_managed_agent_or_404
from app.services.bootstrap.token import validate_bootstrap_token


def bootstrap_register(
    db: Session,
    managed_agent_id: str,
    token: str,
) -> Agent:
    """使用 register_runtime token 完成运行态注册并回写配置态。"""
    bootstrap_token = validate_bootstrap_token(
        db,
        token=token,
        managed_agent_id=managed_agent_id,
        purpose="register_runtime",
    )
    managed_agent = get_managed_agent_or_404(db, managed_agent_id)

    if managed_agent.runtime_agent_id:
        existing_runtime = db.query(Agent).filter(Agent.id == managed_agent.runtime_agent_id).first()
        if existing_runtime:
            raise ConflictError("该配置态 Agent 已有运行态实例")

    same_name_agent = db.query(Agent).filter(Agent.name == managed_agent.name).first()
    if same_name_agent:
        raise ConflictError(f"名称 '{managed_agent.name}' 已被注册")

    runtime_agent = Agent(
        id=str(uuid.uuid4()),
        name=managed_agent.name,
        role=managed_agent.role,
        description=managed_agent.description or "",
        api_key=generate_api_key(),
    )
    db.add(runtime_agent)
    db.flush()

    managed_agent.runtime_agent_id = runtime_agent.id
    managed_agent.deployed_config_version = managed_agent.config_version
    managed_agent.status = "deployed"
    bootstrap_token.used_at = datetime.now()

    db.commit()
    db.refresh(runtime_agent)
    return runtime_agent
