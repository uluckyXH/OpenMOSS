"""
鉴权依赖注入 — Agent API Key 鉴权 & 管理员鉴权
两套鉴权完全隔离，互不通用
"""
from typing import Optional

from fastapi import Header, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.agent import Agent


# ============================================================
# Agent 鉴权（API Key）
# ============================================================

async def get_current_agent(
    authorization: str = Header(..., description="Bearer <api_key>"),
    db: Session = Depends(get_db),
) -> Agent:
    """
    从 Authorization Header 解析 API Key，返回当前 Agent。
    用法：在路由参数里加 agent: Agent = Depends(get_current_agent)
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization 格式错误，需要 Bearer <api_key>")

    api_key = authorization[7:]  # 去掉 "Bearer "

    agent = db.query(Agent).filter(Agent.api_key == api_key).first()
    if not agent:
        raise HTTPException(status_code=401, detail="无效的 API Key")

    if agent.status == "disabled":
        raise HTTPException(status_code=403, detail="Agent 已禁用，无法操作")

    return agent


def require_role(*allowed_roles: str):
    """
    角色权限依赖工厂。
    用法：agent: Agent = Depends(require_role("planner"))
          agent: Agent = Depends(require_role("planner", "patrol"))
    """
    async def _check_role(
        agent: Agent = Depends(get_current_agent),
    ) -> Agent:
        if agent.role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"该操作仅限 {'/'.join(allowed_roles)} 角色，你的角色是 {agent.role}",
            )
        return agent
    return _check_role


# ============================================================
# 管理员鉴权（Session Token）
# ============================================================

async def verify_admin(
    x_admin_token: Optional[str] = Header(
        None,
        alias="X-Admin-Token",
        description="管理员登录后获取的 session token",
    ),
) -> bool:
    """
    验证管理员 session token。
    token 由 /admin/login 生成，存储在内存中，服务重启后失效。
    用法：在路由参数里加 _: bool = Depends(verify_admin)
    """
    # 延迟导入避免循环引用
    from app.routers.admin.auth import is_valid_admin_token

    if not x_admin_token or not is_valid_admin_token(x_admin_token):
        raise HTTPException(status_code=403, detail="管理员验证失败，请重新登录")

    return True
