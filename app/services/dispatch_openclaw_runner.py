from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import websockets
from sqlalchemy.orm import Session

from app.config import config
from app.models.agent import Agent
from app.models.sub_task import SubTask
from app.models.task import Task

DEFAULT_GATEWAY_URL = "ws://127.0.0.1:18789"
DEFAULT_DOCKER_GATEWAY_URL = "ws://host.docker.internal:18789"
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_INTERVAL_SECONDS = 3
DEFAULT_AGENT_ID = "tg-wenqu"
DEFAULT_SEMANTIC_ROLE_AGENT_MAP = {
    "writer": "tg-wenqu",
    "outline": "tg-wenqu",
    "planner": "tg-jiran",
    "reviewer": "tg-siheng",
    "qa": "tg-siheng",
    "critic": "tg-siheng",
    "editor": "tg-qingluan",
    "polish": "tg-qingluan",
    "developer": "tg-luban",
    "engineer": "tg-luban",
    "coder": "tg-luban",
}
DEFAULT_SYSTEM_ROLE_AGENT_MAP = {
    "executor": "tg-wenqu",
    "planner": "tg-jiran",
    "reviewer": "tg-siheng",
}
DEFAULT_HELPER_PYTHON_CANDIDATES = [
    str(Path.home() / ".hermes" / "hermes-agent" / "venv" / "bin" / "python3"),
]
SUBPROCESS_HELPER_SCRIPT = r'''
import asyncio
import base64
import hashlib
import json
import sys
import time
import uuid
from pathlib import Path

import websockets
from nacl.signing import SigningKey


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def make_device(client_id: str, client_mode: str, role: str, scopes: list[str], token: str, nonce: str):
    signing_key = SigningKey.generate()
    public_key = signing_key.verify_key.encode()
    device_id = hashlib.sha256(public_key).hexdigest()
    signed_at = int(time.time() * 1000)
    payload = "|".join([
        "v2", device_id, client_id, client_mode, role, ",".join(scopes), str(signed_at), token or "", nonce,
    ])
    signature = signing_key.sign(payload.encode("utf-8")).signature
    return {
        "id": device_id,
        "publicKey": b64url(public_key),
        "signature": b64url(signature),
        "signedAt": signed_at,
        "nonce": nonce,
    }


async def request(ws, method: str, params: dict):
    request_id = str(uuid.uuid4())
    await ws.send(json.dumps({"type": "req", "id": request_id, "method": method, "params": params}, ensure_ascii=False))
    while True:
        message = json.loads(await ws.recv())
        if message.get("type") == "res" and message.get("id") == request_id:
            if message.get("ok"):
                return message.get("payload") or {}
            raise RuntimeError(message.get("error", {}).get("message") or f"rpc failed: {method}")


async def request_with_budget(ws, method: str, params: dict, timeout_seconds: float, *, fallback: dict | None = None):
    if timeout_seconds <= 0:
        return fallback or {}
    try:
        return await asyncio.wait_for(request(ws, method, params), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        return fallback or {}


def history_tail_text(history: dict) -> str:
    messages = history.get("messages") or []
    condensed = []
    for message in messages[-3:]:
        role = str(message.get("role") or "")
        for part in message.get("content") or []:
            part_type = part.get("type")
            if part_type == "text":
                text = str(part.get("text") or "").strip()
                if text:
                    condensed.append(f"{role}: {text[:200]}")
            elif part_type == "toolCall":
                condensed.append(f"{role}: toolCall {part.get('name')}")
    return " | ".join(condensed)


def capture_artifact_fingerprint(path: Path):
    if not path.exists() or not path.is_file():
        return None
    stat = path.stat()
    if stat.st_size <= 0:
        return None
    return (stat.st_size, stat.st_mtime_ns)


async def main():
    payload = json.loads(sys.stdin.read())
    artifact_path = Path(payload["artifact_absolute_path"])
    previous_fingerprint = capture_artifact_fingerprint(artifact_path)
    async with websockets.connect(payload["gateway_url"], max_size=10_000_000) as ws:
        challenge = json.loads(await ws.recv())
        nonce = str(((challenge.get("payload") or {}).get("nonce") or "")).strip()
        if not nonce:
            raise RuntimeError("connect.challenge missing nonce")
        client_id = "cli"
        client_mode = "cli"
        role = "operator"
        scopes = ["operator.admin", "operator.read", "operator.write", "operator.approvals", "operator.pairing"]
        device = make_device(client_id, client_mode, role, scopes, payload["gateway_token"], nonce)
        await request(ws, "connect", {
            "minProtocol": 3,
            "maxProtocol": 3,
            "client": {
                "id": client_id,
                "instanceId": str(uuid.uuid4()),
                "mode": client_mode,
                "platform": "Linux x86_64",
                "version": "2026.3.28",
            },
            "role": role,
            "scopes": scopes,
            "caps": ["tool-events"],
            "auth": {"token": payload["gateway_token"]},
            "device": device,
            "locale": "zh-CN",
            "userAgent": "openmoss-dispatch-runner",
        })
        run_started_at = time.time()
        send_result = await request(ws, "chat.send", {
            "deliver": False,
            "idempotencyKey": str(uuid.uuid4()),
            "message": payload["prompt"],
            "sessionKey": payload["session_key"],
        })
        remaining_wait_seconds = max(0.0, int(payload["timeout_seconds"]) - (time.time() - run_started_at))
        deadline = time.time() + remaining_wait_seconds
        last_history = {}
        while True:
            current_fingerprint = capture_artifact_fingerprint(artifact_path)
            if current_fingerprint is not None and current_fingerprint != previous_fingerprint:
                history_budget = max(0.0, deadline - time.time())
                history = await request_with_budget(
                    ws,
                    "chat.history",
                    {"sessionKey": payload["session_key"], "limit": 20},
                    history_budget,
                )
                print(json.dumps({"ok": True, "run_id": send_result.get("runId", ""), "history": history}, ensure_ascii=False))
                return
            remaining_seconds = deadline - time.time()
            if remaining_seconds <= 0:
                break
            sleep_seconds = min(max(0.0, float(payload["poll_interval_seconds"])), remaining_seconds)
            if sleep_seconds > 0:
                await asyncio.sleep(sleep_seconds)
            history_budget = deadline - time.time()
            if history_budget <= 0:
                break
            last_history = await request_with_budget(
                ws,
                "chat.history",
                {"sessionKey": payload["session_key"], "limit": 20},
                history_budget,
                fallback=last_history,
            )
        raise RuntimeError(
            f"OpenClaw runner timeout: session_key={payload['session_key']} artifact={payload['artifact_absolute_path']} last_history_tail={history_tail_text(last_history)}"
        )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        raise
'''


def _dispatch_openclaw_config() -> dict[str, Any]:
    dispatch = config.raw.get("dispatch") or {}
    return dispatch.get("openclaw") or {}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _gateway_config_path() -> Path:
    cfg = _dispatch_openclaw_config()
    configured = str(cfg.get("gateway_config_path") or "").strip()
    if configured:
        return Path(configured)
    return Path.home() / ".openclaw" / "openclaw.json"


def _resolve_gateway_token() -> str:
    cfg = _dispatch_openclaw_config()
    explicit = str(cfg.get("gateway_token") or "").strip()
    if explicit:
        return explicit

    env_token = str(os.getenv("OPENCLAW_GATEWAY_TOKEN") or "").strip()
    if env_token:
        return env_token

    config_path = _gateway_config_path()
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            token = str((((data.get("gateway") or {}).get("auth") or {}).get("token") or "")).strip()
            if token:
                return token
        except Exception:
            return ""
    return ""


def _resolve_gateway_url() -> str:
    cfg = _dispatch_openclaw_config()
    configured = str(cfg.get("gateway_url") or "").strip()
    if configured:
        return configured
    if Path("/.dockerenv").exists():
        return DEFAULT_DOCKER_GATEWAY_URL
    return DEFAULT_GATEWAY_URL


def _resolve_helper_python() -> str:
    cfg = _dispatch_openclaw_config()
    explicit = str(cfg.get("helper_python") or os.getenv("OPENCLAW_HELPER_PYTHON") or "").strip()
    if explicit:
        return explicit
    for candidate in DEFAULT_HELPER_PYTHON_CANDIDATES:
        if candidate and Path(candidate).exists():
            return candidate
    return ""


def _resolve_helper_url() -> str:
    cfg = _dispatch_openclaw_config()
    return str(cfg.get("helper_url") or os.getenv("OPENCLAW_HELPER_URL") or "").strip()


def _capture_artifact_fingerprint(path: Path) -> tuple[int, int] | None:
    if not path.exists() or not path.is_file():
        return None
    stat = path.stat()
    if stat.st_size <= 0:
        return None
    return (stat.st_size, stat.st_mtime_ns)


def _artifact_became_ready(path: Path, previous_fingerprint: tuple[int, int] | None = None) -> bool:
    current = _capture_artifact_fingerprint(path)
    return current is not None and current != previous_fingerprint


def _run_via_helper_subprocess(*, gateway_url: str, gateway_token: str, session_key: str, prompt: str, artifact_absolute_path: str, timeout_seconds: int, poll_interval_seconds: int) -> dict[str, Any]:
    helper_python = _resolve_helper_python()
    if not helper_python:
        raise RuntimeError("OpenClaw runner 缺少 nacl 依赖，且未配置 helper_python")
    payload = {
        "gateway_url": gateway_url,
        "gateway_token": gateway_token,
        "session_key": session_key,
        "prompt": prompt,
        "artifact_absolute_path": artifact_absolute_path,
        "timeout_seconds": timeout_seconds,
        "poll_interval_seconds": poll_interval_seconds,
    }
    completed = subprocess.run(
        [helper_python, "-c", SUBPROCESS_HELPER_SCRIPT],
        input=json.dumps(payload, ensure_ascii=False),
        text=True,
        capture_output=True,
        timeout=timeout_seconds + 30,
        check=False,
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if stdout:
        try:
            data = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"OpenClaw helper 返回非 JSON: {stdout[-400:]}") from exc
    else:
        data = {}
    if completed.returncode != 0 or not data.get("ok"):
        error_text = data.get("error") or stderr or stdout or f"helper exit={completed.returncode}"
        raise RuntimeError(f"OpenClaw helper failed: {error_text}")
    return data


def _run_via_helper_http(*, helper_url: str, agent_id: str, session_key: str, prompt: str, artifact_absolute_path: str, timeout_seconds: int, poll_interval_seconds: int) -> dict[str, Any]:
    payload = {
        "agent_id": agent_id,
        "session_key": session_key,
        "prompt": prompt,
        "artifact_absolute_path": artifact_absolute_path,
        "timeout_seconds": timeout_seconds,
        "poll_interval_seconds": poll_interval_seconds,
    }
    req = urllib.request.Request(
        helper_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_seconds + 30) as resp:
            body = resp.read().decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"OpenClaw helper HTTP failed: {exc}") from exc
    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"OpenClaw helper HTTP 返回非 JSON: {body[-400:]}") from exc
    if not data.get("ok"):
        raise RuntimeError(f"OpenClaw helper HTTP failed: {data.get('error') or body[-400:]}")
    return data


def _runner_enabled() -> bool:
    cfg = _dispatch_openclaw_config()
    if cfg.get("enabled") is not True:
        return False
    return bool(_resolve_gateway_token())


def is_openclaw_runner_available() -> bool:
    return _runner_enabled()


def _has_running_event_loop() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def _is_missing_nacl_error(exc: ModuleNotFoundError) -> bool:
    message = str(exc)
    return exc.name == "nacl" or "No module named 'nacl'" in message or 'No module named "nacl"' in message


def _run_async_in_dedicated_thread(async_fn, /, *args, **kwargs):
    result_box: dict[str, Any] = {}
    error_box: dict[str, BaseException] = {}

    def _runner() -> None:
        try:
            result_box["value"] = asyncio.run(async_fn(*args, **kwargs))
        except BaseException as exc:  # pragma: no cover - re-raised on caller thread
            error_box["error"] = exc

    thread = threading.Thread(target=_runner, daemon=False)
    thread.start()
    thread.join()
    if error_box:
        raise error_box["error"]
    return result_box["value"]


def _resolve_openclaw_agent_id(sub_task: SubTask, executor: Agent) -> str:
    cfg = _dispatch_openclaw_config()
    assigned_map = cfg.get("assigned_agent_map") or {}
    semantic_map = {**DEFAULT_SEMANTIC_ROLE_AGENT_MAP, **(cfg.get("semantic_role_map") or {})}
    system_map = {**DEFAULT_SYSTEM_ROLE_AGENT_MAP, **(cfg.get("system_role_map") or {})}

    for key in (sub_task.assigned_agent, executor.id):
        mapped = str(assigned_map.get(key or "") or "").strip()
        if mapped:
            return mapped

    semantic_role = str(sub_task.semantic_role or "").strip().lower()
    if semantic_role:
        mapped = str(semantic_map.get(semantic_role) or "").strip()
        if mapped:
            return mapped

    system_role = str(sub_task.system_role or executor.role or "").strip().lower()
    if system_role:
        mapped = str(system_map.get(system_role) or "").strip()
        if mapped:
            return mapped

    return str(cfg.get("default_agent_id") or DEFAULT_AGENT_ID).strip() or DEFAULT_AGENT_ID


def build_openclaw_session_id(sub_task: SubTask, executor: Agent) -> str:
    agent_id = _resolve_openclaw_agent_id(sub_task, executor)
    return f"agent:{agent_id}:main"


def _build_prompt(
    task: Task | None,
    sub_task: SubTask,
    *,
    payload: dict[str, Any],
    artifact_absolute_path: str,
    task_workspace_dir: str,
    workspace_root: str,
) -> str:
    task_payload = payload.get("task") or {}
    sub_task_payload = payload.get("sub_task") or {}
    dispatch_request_id = str(payload.get("dispatch_request_id") or "manual").strip()
    title = str((task.name if task else "") or task_payload.get("name") or sub_task.task_id or "未命名任务").strip()
    upstream_inputs = sub_task.upstream_inputs or sub_task_payload.get("upstream_inputs") or []
    upstream_block = "\n".join(f"- {item}" for item in upstream_inputs) if upstream_inputs else "- 无显式上游文件，按 task_workspace_dir 自行检查可用素材。"
    artifact_ref = str(sub_task.artifact_path or sub_task.deliverable or Path(artifact_absolute_path).name).strip()
    return "\n".join([
        "你是 OpenMOSS dispatch consumer 调起的真实执行 agent。",
        "只完成这一个子任务，不要闲聊，不要改无关文件。",
        "",
        f"任务标题：{title}",
        f"子任务：{sub_task.name}",
        f"描述：{sub_task.description or '无'}",
        f"语义角色：{sub_task.semantic_role or 'executor'}",
        f"系统角色：{sub_task.system_role or 'executor'}",
        f"交付要求：{sub_task.deliverable or artifact_ref}",
        f"验收标准：{sub_task.acceptance or '生成真实可提交工件'}",
        f"审查焦点：{sub_task.review_focus or '无'}",
        f"dispatch_request_id：{dispatch_request_id}",
        "",
        "工作区上下文：",
        f"- workspace_root: {workspace_root or '(empty)'}",
        f"- task_workspace_dir: {task_workspace_dir}",
        f"- artifact_absolute_path: {artifact_absolute_path}",
        f"- artifact_path: {artifact_ref}",
        "",
        "上游输入候选：",
        upstream_block,
        "",
        "执行要求：",
        "1. 先读取 task_workspace_dir 内相关上游文件，再动笔。",
        "2. 生成真实内容，禁止 placeholder、TODO、空稿、解释型水文。",
        "3. 只把最终工件写到 artifact_absolute_path；必要时创建父目录。",
        "4. 完成后只需简短回复 done，并带上实际写入路径。",
    ])


class _GatewayClient:
    def __init__(self, *, url: str, token: str):
        self.url = url
        self.token = token
        self.client_id = "cli"
        self.client_mode = "cli"
        self.role = "operator"
        self.scopes = [
            "operator.admin",
            "operator.read",
            "operator.write",
            "operator.approvals",
            "operator.pairing",
        ]

    @staticmethod
    def _make_device(*, client_id: str, client_mode: str, role: str, scopes: list[str], token: str, nonce: str) -> dict[str, Any]:
        from nacl.signing import SigningKey

        signing_key = SigningKey.generate()
        public_key = signing_key.verify_key.encode()
        device_id = hashlib.sha256(public_key).hexdigest()
        signed_at = int(time.time() * 1000)
        payload = "|".join([
            "v2",
            device_id,
            client_id,
            client_mode,
            role,
            ",".join(scopes),
            str(signed_at),
            token or "",
            nonce,
        ])
        signature = signing_key.sign(payload.encode("utf-8")).signature
        return {
            "id": device_id,
            "publicKey": _b64url(public_key),
            "signature": _b64url(signature),
            "signedAt": signed_at,
            "nonce": nonce,
        }

    async def _recv_for_request(self, ws, request_id: str) -> dict[str, Any]:
        while True:
            message = json.loads(await ws.recv())
            if message.get("type") == "res" and message.get("id") == request_id:
                return message

    async def _request(self, ws, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = str(uuid.uuid4())
        await ws.send(json.dumps({
            "type": "req",
            "id": request_id,
            "method": method,
            "params": params,
        }, ensure_ascii=False))
        response = await self._recv_for_request(ws, request_id)
        if response.get("ok"):
            return response.get("payload") or {}
        raise RuntimeError(response.get("error", {}).get("message") or f"OpenClaw RPC failed: {method}")

    async def _request_with_budget(
        self,
        ws,
        method: str,
        params: dict[str, Any],
        timeout_seconds: float,
        *,
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if timeout_seconds <= 0:
            return fallback or {}
        try:
            return await asyncio.wait_for(self._request(ws, method, params), timeout=timeout_seconds)
        except asyncio.TimeoutError:
            return fallback or {}

    async def run_sub_task(
        self,
        *,
        session_key: str,
        prompt: str,
        artifact_absolute_path: str,
        timeout_seconds: int,
        poll_interval_seconds: int,
    ) -> dict[str, Any]:
        artifact_path = Path(artifact_absolute_path)
        previous_fingerprint = _capture_artifact_fingerprint(artifact_path)

        async with websockets.connect(self.url, max_size=10_000_000) as ws:
            challenge = json.loads(await ws.recv())
            nonce = str(((challenge.get("payload") or {}).get("nonce") or "")).strip()
            if not nonce:
                raise RuntimeError("OpenClaw connect.challenge 缺少 nonce")
            device = self._make_device(
                client_id=self.client_id,
                client_mode=self.client_mode,
                role=self.role,
                scopes=self.scopes,
                token=self.token,
                nonce=nonce,
            )
            await self._request(ws, "connect", {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": self.client_id,
                    "instanceId": str(uuid.uuid4()),
                    "mode": self.client_mode,
                    "platform": "Linux x86_64",
                    "version": "2026.3.28",
                },
                "role": self.role,
                "scopes": self.scopes,
                "caps": ["tool-events"],
                "auth": {"token": self.token},
                "device": device,
                "locale": "zh-CN",
                "userAgent": "openmoss-dispatch-runner",
            })
            run_started_at = time.time()
            send_result = await self._request(ws, "chat.send", {
                "deliver": False,
                "idempotencyKey": str(uuid.uuid4()),
                "message": prompt,
                "sessionKey": session_key,
            })
            remaining_wait_seconds = max(0.0, timeout_seconds - (time.time() - run_started_at))
            deadline = time.time() + remaining_wait_seconds
            last_history: dict[str, Any] = {}
            while True:
                if _artifact_became_ready(artifact_path, previous_fingerprint):
                    history_budget = max(0.0, deadline - time.time())
                    history = await self._request_with_budget(
                        ws,
                        "chat.history",
                        {"sessionKey": session_key, "limit": 20},
                        history_budget,
                    )
                    return {
                        "run_id": send_result.get("runId", ""),
                        "history": history,
                    }
                remaining_seconds = deadline - time.time()
                if remaining_seconds <= 0:
                    break
                sleep_seconds = min(max(0.0, float(poll_interval_seconds)), remaining_seconds)
                if sleep_seconds > 0:
                    await asyncio.sleep(sleep_seconds)
                history_budget = deadline - time.time()
                if history_budget <= 0:
                    break
                last_history = await self._request_with_budget(
                    ws,
                    "chat.history",
                    {"sessionKey": session_key, "limit": 20},
                    history_budget,
                    fallback=last_history,
                )
            raise RuntimeError(
                "OpenClaw runner timeout: session_key={} artifact={} last_history_tail={}".format(
                    session_key,
                    artifact_absolute_path,
                    _history_tail_text(last_history),
                )
            )


def _history_tail_text(history: dict[str, Any]) -> str:
    messages = history.get("messages") or []
    condensed: list[str] = []
    for message in messages[-3:]:
        role = str(message.get("role") or "")
        parts = message.get("content") or []
        for part in parts:
            part_type = part.get("type")
            if part_type == "text":
                text = str(part.get("text") or "").strip()
                if text:
                    condensed.append(f"{role}: {text[:200]}")
            elif part_type == "toolCall":
                condensed.append(f"{role}: toolCall {part.get('name')}")
            elif part_type == "thinking":
                thinking = str(part.get("thinking") or "").strip()
                if thinking:
                    condensed.append(f"{role}: thinking {thinking[:120]}")
    return " | ".join(condensed)


def run_sub_task_via_openclaw(
    db: Session,
    sub_task: SubTask,
    *,
    payload: dict[str, Any],
    executor: Agent,
    reviewer: Agent,
    session_id: str,
) -> dict[str, Any]:
    del reviewer
    if not _runner_enabled():
        raise RuntimeError("dispatch.openclaw 未启用或缺少 gateway token")

    gateway_url = _resolve_gateway_url()
    gateway_token = _resolve_gateway_token()
    if not gateway_token:
        raise RuntimeError("无法解析 OpenClaw gateway token")

    task = db.query(Task).filter(Task.id == sub_task.task_id).first()
    workspace = payload.get("workspace") or {}
    workspace_root = str(workspace.get("workspace_root") or sub_task.workspace_root or config.workspace_root or "").strip()
    task_workspace_dir = str(workspace.get("task_workspace_dir") or sub_task.task_workspace_dir or "").strip()
    artifact_absolute_path = str(workspace.get("artifact_absolute_path") or sub_task.artifact_absolute_path or "").strip()
    if not task_workspace_dir or not artifact_absolute_path:
        raise RuntimeError(f"sub_task {sub_task.id} 缺少 workspace 上下文，无法走 OpenClaw runner")

    openclaw_session_id = build_openclaw_session_id(sub_task, executor)
    agent_id = _resolve_openclaw_agent_id(sub_task, executor)
    prompt = _build_prompt(
        task,
        sub_task,
        payload=payload,
        artifact_absolute_path=artifact_absolute_path,
        task_workspace_dir=task_workspace_dir,
        workspace_root=workspace_root,
    )
    cfg = _dispatch_openclaw_config()
    timeout_seconds = int(cfg.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
    poll_interval_seconds = int(cfg.get("poll_interval_seconds") or DEFAULT_POLL_INTERVAL_SECONDS)
    helper_url = _resolve_helper_url()

    if helper_url:
        run_result = _run_via_helper_http(
            helper_url=helper_url,
            agent_id=agent_id,
            session_key=openclaw_session_id,
            prompt=prompt,
            artifact_absolute_path=artifact_absolute_path,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        return {
            "artifact_absolute_path": artifact_absolute_path,
            "summary": (
                "dispatch consumer 已通过 OpenClaw gateway agent 执行："
                f"session={openclaw_session_id}；run_id={run_result.get('run_id', '')}"
            ),
            "session_id": openclaw_session_id,
            "run_id": run_result.get("run_id", ""),
            "history_tail": _history_tail_text(run_result.get("history") or {}),
        }

    client = _GatewayClient(url=gateway_url, token=gateway_token)
    if _has_running_event_loop():
        try:
            run_result = _run_async_in_dedicated_thread(
                client.run_sub_task,
                session_key=openclaw_session_id,
                prompt=prompt,
                artifact_absolute_path=artifact_absolute_path,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
        except ModuleNotFoundError as exc:
            if not _is_missing_nacl_error(exc):
                raise
            run_result = _run_via_helper_subprocess(
                gateway_url=gateway_url,
                gateway_token=gateway_token,
                session_key=openclaw_session_id,
                prompt=prompt,
                artifact_absolute_path=artifact_absolute_path,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
    else:
        try:
            run_result = asyncio.run(client.run_sub_task(
                session_key=openclaw_session_id,
                prompt=prompt,
                artifact_absolute_path=artifact_absolute_path,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            ))
        except ModuleNotFoundError as exc:
            if not _is_missing_nacl_error(exc):
                raise
            run_result = _run_via_helper_subprocess(
                gateway_url=gateway_url,
                gateway_token=gateway_token,
                session_key=openclaw_session_id,
                prompt=prompt,
                artifact_absolute_path=artifact_absolute_path,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
    return {
        "artifact_absolute_path": artifact_absolute_path,
        "summary": (
            "dispatch consumer 已通过 OpenClaw gateway agent 执行："
            f"session={openclaw_session_id}；run_id={run_result.get('run_id', '')}"
        ),
        "session_id": openclaw_session_id,
        "run_id": run_result.get("run_id", ""),
        "history_tail": _history_tail_text(run_result.get("history") or {}),
    }
