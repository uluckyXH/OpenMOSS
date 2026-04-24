"""
初始化向导路由 — Setup Wizard
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from app.config import config
from app.database import SessionLocal
from app.services import agent_runtime as agent_service

router = APIRouter(prefix="/setup", tags=["Setup"])


class SetupStatusResponse(BaseModel):
    initialized: bool
    has_external_url: bool = False


class SetupInitializeRequest(BaseModel):
    admin_password: str = Field(..., min_length=6, description="管理员密码（至少6位）")
    current_password: Optional[str] = Field(None, description="当前管理员密码（仅数据库有数据时必填）")
    project_name: str = Field(..., min_length=1, description="项目名称")
    workspace_root: str = Field(..., min_length=1, description="宿主部署机公共工作目录路径")
    registration_token: Optional[str] = Field(None, description="Agent 注册令牌（不填则自动生成）")
    allow_registration: bool = Field(True, description="是否允许 Agent 自注册")
    notification: Optional[dict] = Field(None, description="通知配置")
    external_url: Optional[str] = Field(None, description="服务外网访问地址（Agent 对接用）")


class SetupInitializeResponse(BaseModel):
    message: str = "初始化完成"
    registration_token: str = Field(..., description="Agent 注册令牌（自动生成时需告知用户）")


def _has_existing_data() -> bool:
    """检查数据库中是否已有 Agent 记录"""
    db = SessionLocal()
    try:
        return agent_service.has_any_agent(db)
    finally:
        db.close()


@router.get("/status", response_model=SetupStatusResponse, summary="获取初始化状态")
async def get_setup_status():
    """
    返回系统是否已完成初始化。
    前端用此接口决定跳转到向导页还是登录页。
    无需认证。

    自动矫正：如果 config 标记为未初始化，但数据库已有 Agent 数据，
    说明系统之前已初始化过（标记被意外重置），自动修正为 true。
    """
    if not config.is_initialized and _has_existing_data():
        config.mark_initialized()

    return SetupStatusResponse(
        initialized=config.is_initialized,
        has_external_url=config.has_external_url,
    )


@router.post("/initialize", response_model=SetupInitializeResponse, summary="执行初始化")
async def initialize(req: SetupInitializeRequest):
    """
    一次性初始化系统配置。

    安全策略：
    - 已初始化（initialized=true）→ 403
    - 数据库无 Agent（真正首次启动）→ 无需验证身份
    - 数据库有 Agent（标记被篡改）→ 必须提供 current_password 验证身份
    """
    if config.is_initialized:
        raise HTTPException(status_code=403, detail="系统已初始化，不可重复执行")

    # 防篡改检查
    if _has_existing_data():
        if not req.current_password:
            raise HTTPException(
                status_code=403,
                detail="检测到系统已有数据，请提供当前管理员密码以验证身份"
            )
        if not config.verify_admin_password(req.current_password):
            raise HTTPException(status_code=403, detail="当前管理员密码验证失败")

    # 执行初始化（内部有锁 + 原子性二次检查，防止并发竞态）
    success = config.initialize(req.model_dump())
    if not success:
        raise HTTPException(status_code=403, detail="系统已初始化，不可重复执行")

    # 返回注册令牌（用户可能是自动生成的，需要告知）
    token = config.registration_token
    return SetupInitializeResponse(
        message="初始化完成",
        registration_token=token,
    )
