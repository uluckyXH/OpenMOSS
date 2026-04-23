"""task-core 功能域路由包。"""

from fastapi import APIRouter

from .review_records import router as review_records_router
from .rules import router as rules_router
from .scores import router as scores_router
from .sub_tasks import router as sub_tasks_router
from .tasks import router as tasks_router


router = APIRouter()
router.include_router(tasks_router)
router.include_router(sub_tasks_router)
router.include_router(rules_router)
router.include_router(review_records_router)
router.include_router(scores_router)

__all__ = ["router"]
