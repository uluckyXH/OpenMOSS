"""
Agent 运行态路由包

将 agents / feed / tools / logs 收拢到 agent_runtime/ 子包。
main.py 通过此 __init__.py 统一导入。
"""
from app.routers.agent_runtime.agents import router as agents_router
from app.routers.agent_runtime.feed import router as feed_router
from app.routers.agent_runtime.tools import router as tools_router
from app.routers.agent_runtime.logs import router as logs_router

__all__ = [
    "agents_router",
    "feed_router",
    "tools_router",
    "logs_router",
]
