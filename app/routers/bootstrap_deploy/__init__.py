"""bootstrap-deploy 功能域路由包。"""

from fastapi import APIRouter

from .bootstrap import router as bootstrap_router
from .deploy import router as deploy_router


router = APIRouter()
router.include_router(bootstrap_router)
router.include_router(deploy_router)

__all__ = ["router"]
