"""管理端 Agent 路由子包。"""
from fastapi import APIRouter

from .crud import router as crud_router
from .logs import router as logs_router


router = APIRouter(tags=["Admin Agent"])
router.include_router(crud_router)
router.include_router(logs_router)
