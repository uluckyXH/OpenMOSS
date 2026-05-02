import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.config import config
from app.services import dispatch_openclaw_runner


class DispatchOpenClawRunnerConfigTest(unittest.TestCase):
    def setUp(self):
        self.original_data = config.raw.copy()

    def tearDown(self):
        config._data = self.original_data

    def test_resolve_gateway_url_defaults_to_host_docker_internal_inside_container(self):
        config._data = {
            **self.original_data,
            "dispatch": {"openclaw": {}},
        }
        with patch("app.services.dispatch_openclaw_runner.Path.exists", return_value=True):
            self.assertEqual(
                dispatch_openclaw_runner._resolve_gateway_url(),
                "ws://host.docker.internal:18789",
            )

    def test_resolve_gateway_url_defaults_to_loopback_outside_container(self):
        config._data = {
            **self.original_data,
            "dispatch": {"openclaw": {}},
        }
        with patch.object(Path, "exists", return_value=False):
            self.assertEqual(
                dispatch_openclaw_runner._resolve_gateway_url(),
                "ws://127.0.0.1:18789",
            )

    def test_explicit_gateway_url_still_wins(self):
        config._data = {
            **self.original_data,
            "dispatch": {"openclaw": {"gateway_url": "ws://example.test:9999"}},
        }
        with patch.object(Path, "exists", return_value=True):
            self.assertEqual(
                dispatch_openclaw_runner._resolve_gateway_url(),
                "ws://example.test:9999",
            )


class DispatchOpenClawArtifactGuardTest(unittest.TestCase):
    def test_artifact_became_ready_rejects_preexisting_unchanged_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")
            baseline = dispatch_openclaw_runner._capture_artifact_fingerprint(artifact)

            self.assertFalse(dispatch_openclaw_runner._artifact_became_ready(artifact, baseline))

    def test_artifact_became_ready_accepts_preexisting_file_after_content_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")
            baseline = dispatch_openclaw_runner._capture_artifact_fingerprint(artifact)
            artifact.write_text("new content with extra bytes\n", encoding="utf-8")

            self.assertTrue(dispatch_openclaw_runner._artifact_became_ready(artifact, baseline))


class DispatchOpenClawRunnerExecutionTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_sub_task_via_openclaw_uses_local_client_inside_running_loop_when_available(self):
        task = SimpleNamespace(id="task-1", name="Loop Safe Smoke")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = task
        sub_task = SimpleNamespace(
            id="subtask-1",
            task_id="task-1",
            name="真实 writer smoke",
            description="验证 running loop 下的 OpenClaw 执行",
            deliverable="写一段正文",
            acceptance="真实落盘",
            semantic_role="writer",
            system_role="executor",
            reviewer_role="planner",
            review_focus="running loop local client",
            artifact_path="03_writer/03_draft.md",
            upstream_inputs=["inputs/brief.md"],
            assigned_agent="executor-1",
            workspace_root="/workspace",
            task_workspace_dir="dispatch-smoke/loop-safe",
            artifact_absolute_path="/tmp/03_draft.md",
        )
        executor = SimpleNamespace(id="executor-1", role="executor")
        payload = {
            "dispatch_request_id": "req-1",
            "task": {"id": "task-1", "name": "Loop Safe Smoke"},
            "sub_task": {"upstream_inputs": ["inputs/brief.md"]},
            "workspace": {
                "workspace_root": "/workspace",
                "task_workspace_dir": "dispatch-smoke/loop-safe",
                "artifact_absolute_path": "/tmp/03_draft.md",
            },
        }

        async def fake_run_sub_task(**kwargs):
            return {"run_id": "thread-run", "history": {"messages": []}, "kwargs": kwargs}

        client = MagicMock()
        client.run_sub_task = fake_run_sub_task

        with patch("app.services.dispatch_openclaw_runner._runner_enabled", return_value=True), \
             patch("app.services.dispatch_openclaw_runner._resolve_gateway_url", return_value="ws://gateway.test"), \
             patch("app.services.dispatch_openclaw_runner._resolve_gateway_token", return_value="token-1"), \
             patch("app.services.dispatch_openclaw_runner._resolve_helper_url", return_value=""), \
             patch("app.services.dispatch_openclaw_runner._run_via_helper_subprocess", side_effect=AssertionError("helper should not run when local client works")), \
             patch("app.services.dispatch_openclaw_runner._GatewayClient", return_value=client):
            result = dispatch_openclaw_runner.run_sub_task_via_openclaw(
                db,
                sub_task,
                payload=payload,
                executor=executor,
                reviewer=SimpleNamespace(id="reviewer-1"),
                session_id="dispatch-session",
            )

        self.assertEqual(result["run_id"], "thread-run")
        self.assertIn("dispatch consumer 已通过 OpenClaw gateway agent 执行", result["summary"])

    async def test_run_sub_task_via_openclaw_falls_back_to_helper_inside_running_loop_when_local_client_lacks_nacl(self):
        task = SimpleNamespace(id="task-1", name="Loop Safe Smoke")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = task
        sub_task = SimpleNamespace(
            id="subtask-1",
            task_id="task-1",
            name="真实 writer smoke",
            description="验证 running loop 下的 OpenClaw fallback",
            deliverable="写一段正文",
            acceptance="真实落盘",
            semantic_role="writer",
            system_role="executor",
            reviewer_role="planner",
            review_focus="helper fallback",
            artifact_path="03_writer/03_draft.md",
            upstream_inputs=["inputs/brief.md"],
            assigned_agent="executor-1",
            workspace_root="/workspace",
            task_workspace_dir="dispatch-smoke/loop-safe",
            artifact_absolute_path="/tmp/03_draft.md",
        )
        executor = SimpleNamespace(id="executor-1", role="executor")
        payload = {
            "dispatch_request_id": "req-1",
            "task": {"id": "task-1", "name": "Loop Safe Smoke"},
            "sub_task": {"upstream_inputs": ["inputs/brief.md"]},
            "workspace": {
                "workspace_root": "/workspace",
                "task_workspace_dir": "dispatch-smoke/loop-safe",
                "artifact_absolute_path": "/tmp/03_draft.md",
            },
        }

        async def fake_run_sub_task(**kwargs):
            raise ModuleNotFoundError("No module named 'nacl'")

        client = MagicMock()
        client.run_sub_task = fake_run_sub_task

        with patch("app.services.dispatch_openclaw_runner._runner_enabled", return_value=True), \
             patch("app.services.dispatch_openclaw_runner._resolve_gateway_url", return_value="ws://gateway.test"), \
             patch("app.services.dispatch_openclaw_runner._resolve_gateway_token", return_value="token-1"), \
             patch("app.services.dispatch_openclaw_runner._resolve_helper_url", return_value=""), \
             patch("app.services.dispatch_openclaw_runner._run_via_helper_subprocess", return_value={"run_id": "helper-run", "history": {"messages": []}}) as helper_run, \
             patch("app.services.dispatch_openclaw_runner._GatewayClient", return_value=client):
            result = dispatch_openclaw_runner.run_sub_task_via_openclaw(
                db,
                sub_task,
                payload=payload,
                executor=executor,
                reviewer=SimpleNamespace(id="reviewer-1"),
                session_id="dispatch-session",
            )

        helper_run.assert_called_once()
        self.assertEqual(result["run_id"], "helper-run")
        self.assertIn("dispatch consumer 已通过 OpenClaw gateway agent 执行", result["summary"])

    async def test_run_sub_task_via_openclaw_prefers_helper_http_when_helper_url_configured(self):
        task = SimpleNamespace(id="task-1", name="HTTP Helper Smoke")
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = task
        sub_task = SimpleNamespace(
            id="subtask-1",
            task_id="task-1",
            name="真实 writer smoke",
            description="验证 helper http 优先",
            deliverable="写一段正文",
            acceptance="真实落盘",
            semantic_role="writer",
            system_role="executor",
            reviewer_role="planner",
            review_focus="helper http",
            artifact_path="03_writer/03_draft.md",
            upstream_inputs=["inputs/brief.md"],
            assigned_agent="executor-1",
            workspace_root="/workspace",
            task_workspace_dir="dispatch-smoke/http-helper",
            artifact_absolute_path="/tmp/03_draft.md",
        )
        executor = SimpleNamespace(id="executor-1", role="executor")
        payload = {
            "dispatch_request_id": "req-http",
            "task": {"id": "task-1", "name": "HTTP Helper Smoke"},
            "sub_task": {"upstream_inputs": ["inputs/brief.md"]},
            "workspace": {
                "workspace_root": "/workspace",
                "task_workspace_dir": "dispatch-smoke/http-helper",
                "artifact_absolute_path": "/tmp/03_draft.md",
            },
        }

        with patch("app.services.dispatch_openclaw_runner._runner_enabled", return_value=True), \
             patch("app.services.dispatch_openclaw_runner._resolve_gateway_url", return_value="ws://gateway.test"), \
             patch("app.services.dispatch_openclaw_runner._resolve_gateway_token", return_value="token-1"), \
             patch("app.services.dispatch_openclaw_runner._resolve_helper_url", return_value="http://helper.local/run"), \
             patch("app.services.dispatch_openclaw_runner._run_via_helper_http", return_value={"run_id": "http-helper-run", "history": {"messages": []}}) as helper_http, \
             patch("app.services.dispatch_openclaw_runner._GatewayClient", side_effect=AssertionError("local gateway client should be bypassed when helper_url is configured")):
            result = dispatch_openclaw_runner.run_sub_task_via_openclaw(
                db,
                sub_task,
                payload=payload,
                executor=executor,
                reviewer=SimpleNamespace(id="reviewer-1"),
                session_id="dispatch-session",
            )

        helper_http.assert_called_once()
        self.assertEqual(result["run_id"], "http-helper-run")
        self.assertEqual(result["session_id"], "agent:tg-wenqu:main")
        self.assertIn("dispatch consumer 已通过 OpenClaw gateway agent 执行", result["summary"])


class _FakeWebSocket:
    async def recv(self):
        return json.dumps({"payload": {"nonce": "nonce-1"}}, ensure_ascii=False)


class _FakeWebSocketContext:
    def __init__(self, ws):
        self.ws = ws

    async def __aenter__(self):
        return self.ws

    async def __aexit__(self, exc_type, exc, tb):
        return False


class DispatchOpenClawGatewayClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_gateway_client_accepts_artifact_that_changed_during_send_even_when_no_wait_budget_remains(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")

            client = dispatch_openclaw_runner._GatewayClient(url="ws://gateway.test", token="token-1")
            fake_ws = _FakeWebSocket()

            async def fake_request(ws, method, params):
                self.assertIs(ws, fake_ws)
                if method == "connect":
                    return {}
                if method == "chat.send":
                    artifact.write_text("new content already written\n", encoding="utf-8")
                    await __import__("asyncio").sleep(2.05)
                    return {"runId": "run-1"}
                if method == "chat.history":
                    return {"messages": [{"role": "assistant", "content": [{"type": "text", "text": "done"}]}]}
                raise AssertionError(method)

            with patch("app.services.dispatch_openclaw_runner.websockets.connect", return_value=_FakeWebSocketContext(fake_ws)), \
                 patch.object(client, "_request", side_effect=fake_request), \
                 patch.object(client, "_make_device", return_value={"id": "device-1"}):
                result = await client.run_sub_task(
                    session_key="agent:tg-wenqu:main",
                    prompt="生成正文并写文件",
                    artifact_absolute_path=str(artifact),
                    timeout_seconds=2,
                    poll_interval_seconds=1,
                )

            self.assertEqual(result["run_id"], "run-1")
            self.assertEqual(artifact.read_text(encoding="utf-8"), "new content already written\n")

    async def test_gateway_client_does_not_spend_full_wait_budget_after_send_budget_already_consumed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")

            client = dispatch_openclaw_runner._GatewayClient(url="ws://gateway.test", token="token-1")
            fake_ws = _FakeWebSocket()

            async def fake_request(ws, method, params):
                self.assertIs(ws, fake_ws)
                if method == "connect":
                    return {}
                if method == "chat.send":
                    await __import__("asyncio").sleep(1.2)
                    return {"runId": "run-1"}
                if method == "chat.history":
                    return {"messages": []}
                raise AssertionError(method)

            with patch("app.services.dispatch_openclaw_runner.websockets.connect", return_value=_FakeWebSocketContext(fake_ws)), \
                 patch.object(client, "_request", side_effect=fake_request), \
                 patch.object(client, "_make_device", return_value={"id": "device-1"}):
                start = time.time()
                with self.assertRaises(RuntimeError) as ctx:
                    await client.run_sub_task(
                        session_key="agent:tg-wenqu:main",
                        prompt="不要修改文件，只回复 done",
                        artifact_absolute_path=str(artifact),
                        timeout_seconds=2,
                        poll_interval_seconds=5,
                    )
                elapsed = time.time() - start

            self.assertIn("OpenClaw runner timeout", str(ctx.exception))
            self.assertLess(elapsed, 3.0)
            self.assertEqual(artifact.read_text(encoding="utf-8"), "old content\n")


if __name__ == "__main__":
    unittest.main()
