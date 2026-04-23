"""
子任务路由包 — 汇总 CRUD + 状态机子路由
"""
from fastapi import APIRouter

from . import crud, status

router = APIRouter()
router.include_router(crud.router)
router.include_router(status.router)
