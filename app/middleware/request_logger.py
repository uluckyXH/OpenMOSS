"""
请求日志中间件 — 拦截 Agent API 请求并写入 request_log 表
"""
import json
import logging
import uuid
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.database import SessionLocal
from app.models.agent import Agent
from app.models.request_log import RequestLog


logger = logging.getLogger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    拦截所有 /api/ 请求，识别 Agent 身份，记录到 request_log 表。
    仅记录 Agent 请求（带 Authorization: Bearer ak_xxx），
    跳过管理员请求、无认证请求、认证失败请求。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # 只拦截 /api/ 开头的请求
        if not path.startswith("/api/"):
            return await call_next(request)

        # 只记录 Agent 请求（Bearer token），跳过管理员和无认证请求
        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return await call_next(request)

        api_key = auth_header[7:]

        # 读取请求参数
        body_text = None
        if request.method == "GET":
            # GET 请求：记录 query 参数
            params = dict(request.query_params)
            if params:
                body_text = json.dumps(params, ensure_ascii=False)
        elif request.method in ("POST", "PUT", "PATCH"):
            # POST/PUT/PATCH：读取请求体
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_text = body_bytes.decode("utf-8", errors="replace")
                    if len(body_text) > 10000:
                        body_text = body_text[:10000] + "...(truncated)"
            except Exception:
                body_text = None

        # 执行原始请求
        response = await call_next(request)

        # 跳过认证失败的请求
        if response.status_code in (401, 403):
            return response

        # 异步查询 Agent 信息并写入日志
        try:
            db = SessionLocal()
            try:
                agent = db.query(Agent).filter(Agent.api_key == api_key).first()
                if agent:
                    log = RequestLog(
                        id=str(uuid.uuid4()),
                        timestamp=datetime.now(),
                        method=request.method,
                        path=path,
                        agent_id=agent.id,
                        agent_name=agent.name,
                        agent_role=agent.role,
                        request_body=body_text,
                        response_status=response.status_code,
                    )
                    db.add(log)
                    db.commit()
            finally:
                db.close()
        except Exception:
            # 日志记录失败不应影响正常请求
            logger.exception("请求日志写入失败")

        return response
