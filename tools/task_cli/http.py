"""task_cli HTTP 请求封装。"""

from __future__ import annotations

import json
import sys
from typing import Any, Optional
from urllib import error, parse, request

from .output import print_connection_error, print_http_error


def build_agent_headers(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def build_registration_headers(token: str) -> dict[str, str]:
    return {"X-Registration-Token": token, "Content-Type": "application/json"}


def build_admin_headers(token: str) -> dict[str, str]:
    return {"X-Admin-Token": token, "Content-Type": "application/json"}


def _build_url(base_url: str, path: str, params: Optional[dict[str, Any]] = None) -> str:
    url = f"{base_url}/api{path}"
    if params:
        url = f"{url}?{parse.urlencode(params)}"
    return url


def _stdlib_request(
    method: str,
    url: str,
    headers: dict[str, str],
    *,
    json_body: Any = None,
) -> tuple[int, bytes]:
    data = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")

    req = request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with request.urlopen(req) as resp:
            return resp.status, resp.read()
    except error.HTTPError as exc:
        return exc.code, exc.read()
    except error.URLError:
        raise ConnectionError(url) from None


def request_text(
    method: str,
    *,
    base_url: str,
    path: str,
    headers: dict[str, str],
    params: Optional[dict[str, Any]] = None,
    json_body: Any = None,
) -> tuple[int, str]:
    """发送请求并返回原始文本。"""
    status_code, content = request_bytes(
        method,
        base_url=base_url,
        path=path,
        headers=headers,
        params=params,
        json_body=json_body,
    )
    return status_code, content.decode("utf-8", errors="replace")


def request_bytes(
    method: str,
    *,
    base_url: str,
    path: str,
    headers: dict[str, str],
    params: Optional[dict[str, Any]] = None,
    json_body: Any = None,
) -> tuple[int, bytes]:
    """发送请求并返回原始字节。"""
    url = _build_url(base_url, path, params=params)

    try:
        import requests  # type: ignore
    except ImportError:
        return _stdlib_request(method, url, headers, json_body=json_body)

    try:
        response = getattr(requests, method.lower())(url, headers=headers, json=json_body)
        content = getattr(response, "content", None)
        if content is None:
            content = getattr(response, "text", "").encode("utf-8")
        return response.status_code, content
    except requests.ConnectionError:
        raise ConnectionError(url) from None


def request_json(
    method: str,
    *,
    base_url: str,
    path: str,
    headers: dict[str, str],
    params: Optional[dict[str, Any]] = None,
    json_body: Any = None,
):
    """统一请求封装，自动处理错误并返回 JSON。"""
    try:
        status_code, text = request_text(
            method,
            base_url=base_url,
            path=path,
            headers=headers,
            params=params,
            json_body=json_body,
        )
    except ConnectionError:
        print_connection_error(base_url)
        sys.exit(1)

    if status_code >= 400:
        try:
            detail = json.loads(text).get("detail", text)
        except json.JSONDecodeError:
            detail = text
        print_http_error(status_code, detail)
        sys.exit(1)

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print_http_error(status_code, text)
        sys.exit(1)
