"""配置态 Agent 管理路由子包。"""

from fastapi import APIRouter

from .bootstrap import router as bootstrap_router
from .comm_bindings import router as comm_bindings_router
from .crud import router as crud_router
from .deployment import router as deployment_router
from .host_config import router as host_config_router
from .meta import router as meta_router
from .prompt_asset import router as prompt_asset_router
from .readiness import router as readiness_router
from .schedules import router as schedules_router


router = APIRouter(tags=["Admin - 配置态 Agent"])
router.include_router(meta_router)
router.include_router(crud_router)
router.include_router(host_config_router)
router.include_router(prompt_asset_router)
router.include_router(schedules_router)
router.include_router(comm_bindings_router)
router.include_router(bootstrap_router)
router.include_router(deployment_router)
router.include_router(readiness_router)

