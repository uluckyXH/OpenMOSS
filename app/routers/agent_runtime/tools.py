"""
工具下载路由 — Agent 获取最新 CLI 脚本
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse

from app.auth.dependencies import get_current_agent
from app.config import config
from app.models.agent import Agent


router = APIRouter(prefix="/tools", tags=["Tools"])

# parents[0]=agent_runtime/, parents[1]=routers/, parents[2]=app/, parents[3]=repo root
CLI_PATH = Path(__file__).resolve().parents[3] / "skills" / "task-cli.py"


@router.get("/cli", summary="下载最新 task-cli.py")
async def download_cli(
    request: Request,
    agent: Agent = Depends(get_current_agent),
):
    """返回最新的 task-cli.py，自动将 BASE_URL 替换为服务地址。

    优先使用 config.server_external_url，未配置时用请求 Host 头兜底。
    """
    if not CLI_PATH.exists():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="CLI 脚本文件不存在")

    content = CLI_PATH.read_text(encoding="utf-8")

    # 计算服务地址（优先 external_url，Host 头兜底）
    if config.has_external_url:
        base_url = config.server_external_url
    else:
        host = request.headers.get("host", "127.0.0.1:6565")
        scheme = "https" if request.url.scheme == "https" else "http"
        base_url = f"{scheme}://{host}"

    # 替换 BASE_URL（匹配 task-cli.py 中的 BASE_URL = "..." 行）
    import re
    content = re.sub(
        r'BASE_URL\s*=\s*"[^"]*"',
        f'BASE_URL = "{base_url}"',
        content,
        count=1,
    )

    return PlainTextResponse(content, media_type="text/plain; charset=utf-8")
