#!/usr/bin/env python3
import json
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = str(Path(__file__).resolve().parents[1])
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from app.services.workspace_path_mapper import (
    map_container_path_to_host,
    rewrite_container_workspace_paths_in_text,
)

OPENCLAW_BIN = "/home/joviji/.nvm/versions/node/v22.22.1/bin/openclaw"
OPENCLAW_JSON = "/home/joviji/.openclaw/openclaw.json"
GATEWAY_URL = "ws://127.0.0.1:18789"
HOST = "0.0.0.0"
PORT = 28790
CONTAINER_WORKSPACE_ROOT = "/workspace"
HOST_WORKSPACE_ROOT = "/home/joviji/.openclaw/workspace/openmoss/workspace"


def load_token() -> str:
    data = json.loads(Path(OPENCLAW_JSON).read_text(encoding="utf-8"))
    return str(data["gateway"]["auth"]["token"])


def extract_json(text: str) -> dict:
    start = text.find("{")
    if start < 0:
        raise ValueError(f"no json object in output: {text[-400:]}")
    return json.loads(text[start:])


def run_agent(*, agent_id: str, session_key: str, prompt: str, timeout_seconds: int) -> dict:
    params = {
        "message": prompt,
        "agentId": agent_id,
        "sessionKey": session_key,
        "deliver": False,
        "timeout": timeout_seconds,
        "idempotencyKey": f"openmoss-helper-{int(time.time() * 1000)}",
    }
    cmd = [
        OPENCLAW_BIN,
        "gateway",
        "call",
        "agent",
        "--token",
        load_token(),
        "--url",
        GATEWAY_URL,
        "--expect-final",
        "--json",
        "--timeout",
        str((timeout_seconds + 30) * 1000),
        "--params",
        json.dumps(params, ensure_ascii=False),
    ]
    completed = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds + 60, check=False)
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(stderr or stdout or f"openclaw exit={completed.returncode}")
    return extract_json(stdout)


def capture_artifact_fingerprint(path: str) -> tuple[int, int] | None:
    artifact = Path(path)
    if not artifact.exists() or not artifact.is_file():
        return None
    stat = artifact.stat()
    if stat.st_size <= 0:
        return None
    return (stat.st_size, stat.st_mtime_ns)


def wait_for_artifact(
    path: str,
    timeout_seconds: float,
    poll_interval_seconds: int,
    *,
    previous_fingerprint: tuple[int, int] | None = None,
) -> None:
    deadline = time.time() + timeout_seconds
    baseline = previous_fingerprint
    if baseline is None:
        baseline = capture_artifact_fingerprint(path)
    while True:
        current = capture_artifact_fingerprint(path)
        if current is not None and current != baseline:
            return
        remaining_seconds = deadline - time.time()
        if remaining_seconds <= 0:
            break
        sleep_seconds = min(max(0.0, float(poll_interval_seconds)), remaining_seconds)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)
    raise TimeoutError(f"artifact not ready: {path}")


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
            agent_id = str(payload["agent_id"])
            session_key = str(payload["session_key"])
            prompt = str(payload["prompt"])
            artifact_absolute_path = str(payload["artifact_absolute_path"])
            timeout_seconds = int(payload.get("timeout_seconds") or 300)
            poll_interval_seconds = int(payload.get("poll_interval_seconds") or 5)

            host_artifact_absolute_path = map_container_path_to_host(
                artifact_absolute_path,
                container_workspace_root=CONTAINER_WORKSPACE_ROOT,
                host_workspace_root=HOST_WORKSPACE_ROOT,
            )
            host_prompt = rewrite_container_workspace_paths_in_text(
                prompt,
                container_workspace_root=CONTAINER_WORKSPACE_ROOT,
                host_workspace_root=HOST_WORKSPACE_ROOT,
            )

            previous_fingerprint = capture_artifact_fingerprint(host_artifact_absolute_path)
            run_started_at = time.time()
            result = run_agent(
                agent_id=agent_id,
                session_key=session_key,
                prompt=host_prompt,
                timeout_seconds=timeout_seconds,
            )
            remaining_wait_seconds = max(0.0, timeout_seconds - (time.time() - run_started_at))
            wait_for_artifact(
                host_artifact_absolute_path,
                remaining_wait_seconds,
                poll_interval_seconds,
                previous_fingerprint=previous_fingerprint,
            )
            payloads = ((result.get("result") or {}).get("payloads") or [])
            first_payload = payloads[0] if payloads and isinstance(payloads[0], dict) else {}
            reply_text = str(first_payload.get("text") or result.get("summary") or "completed")
            response = {
                "ok": True,
                "run_id": result.get("runId") or result.get("run_id") or "",
                "history": {
                    "messages": [
                        {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "output_text",
                                    "text": reply_text,
                                }
                            ],
                        }
                    ]
                },
                "reply": reply_text,
                "host_artifact_absolute_path": host_artifact_absolute_path,
            }
            body = json.dumps(response, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"openclaw_helper_listening http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
