"""
OpenMOSS 任务调度中间件 — 主入口
"""
import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.config import config
from app.auth.dependencies import get_current_agent
from app.exceptions import BusinessError
from app.routers.admin import (
    auth_router as admin_auth,
    agents_router as admin_agents,
    config_router as admin_config,
    dashboard_router as admin_dashboard,
    logs_router as admin_logs,
    reviews_router as admin_reviews,
    scores_router as admin_scores,
    tasks_router as admin_tasks,
    prompts_router as admin_prompts,
    managed_agents_router as admin_managed_agents,
)
from app.routers import (
    agents,
    bootstrap,
    feed,
    review_records,
    rules,
    scores,
    setup,
    sub_tasks,
    tasks,
    tools,
    webui,
    logs,
)
from app.middleware.request_logger import RequestLoggerMiddleware


def _cleanup_old_request_logs():
    """启动时清理过期的请求日志"""
    from datetime import datetime, timedelta
    from app.database import SessionLocal
    from app.models.request_log import RequestLog

    days = config.feed_retention_days
    cutoff = datetime.now() - timedelta(days=days)

    db = SessionLocal()
    try:
        deleted = db.query(RequestLog).filter(RequestLog.timestamp < cutoff).delete()
        db.commit()
        if deleted > 0:
            print(f"[RequestLog] 已清理 {deleted} 条超过 {days} 天的请求日志")
    except Exception as e:
        print(f"[RequestLog] 清理失败: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    init_db()

    # 自动回填：把已有运行态 Agent 同步到配置态
    from app.database import SessionLocal
    from app.services.managed_agent import auto_backfill_from_runtime
    _backfill_db = SessionLocal()
    try:
        auto_backfill_from_runtime(_backfill_db)
    finally:
        _backfill_db.close()

    # 清理过期请求日志
    _cleanup_old_request_logs()

    # 确保 WebUI 前端存在（首次部署 / Docker 启动时自动从 GitHub Release 拉取）
    from app.services.webui_updater import webui_updater
    await webui_updater.ensure_webui_exists()

    print(f"[{config.project_name}] 服务启动 → http://{config.server_host}:{config.server_port}")
    print(f"[{config.project_name}] 数据库: {config.database_path}")
    print(f"[{config.project_name}] 宿主公共工作目录: {config.workspace_root}")
    print(f"[{config.project_name}] 注册令牌: {config.registration_token}")
    yield
    print(f"[{config.project_name}] 服务关闭")


app = FastAPI(
    title=f"{config.project_name} 任务调度中间件",
    description="基于 OpenClaw 的自组织自协作自进化多 Agent 作业平台",
    version="1.0.0",
    lifespan=lifespan,
)

# 请求日志中间件（记录 Agent API 调用）
app.add_middleware(RequestLoggerMiddleware)

# CORS 跨域支持（前后端分离部署时需要，必须在最外层）
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# 全局异常处理
# ============================================================

@app.exception_handler(BusinessError)
async def business_error_handler(request: Request, exc: BusinessError):
    """显式业务异常 → 按约定状态码返回。"""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """未显式收口的 ValueError → 安全兜底，不暴露内部细节。"""
    traceback.print_exc()
    return JSONResponse(status_code=400, content={"detail": "请求参数或业务状态非法"})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """未处理异常 → 500，日志记录堆栈，客户端只看到通用提示"""
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "服务内部错误，请联系管理员"},
    )


@app.get("/api/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": config.project_name, "version": "1.0.0"}


@app.get("/api/config/notification", tags=["Config"])
async def get_notification_config(agent=Depends(get_current_agent)):
    """Agent 获取全局通知配置。"""
    notification = config.notification_config
    return {
        "enabled": notification.get("enabled", False),
        "channels": notification.get("channels", []),
        "events": notification.get("events", []),
    }


# 注册路由（统一 /api 前缀）
API_PREFIX = "/api"
# --- Agent 侧 API ---
app.include_router(agents.router, prefix=API_PREFIX)
app.include_router(bootstrap.router, prefix=API_PREFIX)
app.include_router(tasks.router, prefix=API_PREFIX)
app.include_router(sub_tasks.router, prefix=API_PREFIX)
app.include_router(rules.router, prefix=API_PREFIX)
app.include_router(review_records.router, prefix=API_PREFIX)
app.include_router(scores.router, prefix=API_PREFIX)
app.include_router(logs.router, prefix=API_PREFIX)
app.include_router(feed.router, prefix=API_PREFIX)
app.include_router(tools.router, prefix=API_PREFIX)
app.include_router(setup.router, prefix=API_PREFIX)

# --- 管理端 API ---
app.include_router(admin_auth, prefix=API_PREFIX)
app.include_router(admin_agents, prefix=API_PREFIX)
app.include_router(admin_config, prefix=API_PREFIX)
app.include_router(admin_dashboard, prefix=API_PREFIX)
app.include_router(admin_logs, prefix=API_PREFIX)
app.include_router(admin_reviews, prefix=API_PREFIX)
app.include_router(admin_scores, prefix=API_PREFIX)
app.include_router(admin_tasks, prefix=API_PREFIX)
app.include_router(admin_prompts, prefix=API_PREFIX)
app.include_router(admin_managed_agents, prefix=API_PREFIX)

# --- WebUI ---
app.include_router(webui.router, prefix=API_PREFIX)


# ============================================================
# WebUI 静态文件服务（启动时如果没有会被 webui_updater 自动下载）
# ============================================================

_webui_dist = os.path.join(os.path.dirname(__file__), "..", "static")
_assets_dir = os.path.join(_webui_dist, "assets")

# 必须在初始化路由前确保 assets 目录存在，避免 StaticFiles 初始化报错
# (lifespan 中 webui_updater 会覆盖并填充实际的文件)
os.makedirs(_assets_dir, exist_ok=True)

# 挂载静态资源（JS/CSS/图片等）
app.mount("/assets", StaticFiles(directory=_assets_dir), name="webui-assets")

# 所有未匹配路径 → 先尝试返回静态文件，再回退到 index.html（SPA 前端路由）
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if full_path == "api" or full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    # 先检查是否有对应的静态文件（如 logo-200.png, favicon.ico 等）
    static_file = os.path.join(_webui_dist, full_path)
    if full_path and os.path.isfile(static_file):
        return FileResponse(static_file)
    # 否则返回 index.html（SPA 路由）
    index = os.path.join(_webui_dist, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return JSONResponse(status_code=404, content={"detail": "WebUI not found"})

print(f"[WebUI] 已挂载前端: {os.path.abspath(_webui_dist)}")
