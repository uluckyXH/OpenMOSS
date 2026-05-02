import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from scripts import openclaw_agent_helper_server as helper_server


class OpenClawAgentHelperServerTest(unittest.TestCase):
    def test_wait_for_artifact_times_out_when_preexisting_file_never_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")

            start = time.time()
            with self.assertRaises(TimeoutError):
                helper_server.wait_for_artifact(
                    str(artifact),
                    timeout_seconds=2,
                    poll_interval_seconds=1,
                )
            self.assertGreaterEqual(time.time() - start, 1)

    def test_wait_for_artifact_accepts_preexisting_file_after_content_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")

            def mutate_artifact():
                time.sleep(1.1)
                artifact.write_text("new content\n", encoding="utf-8")

            worker = threading.Thread(target=mutate_artifact, daemon=True)
            worker.start()
            helper_server.wait_for_artifact(
                str(artifact),
                timeout_seconds=4,
                poll_interval_seconds=1,
            )
            worker.join(timeout=1)
            self.assertEqual(artifact.read_text(encoding="utf-8"), "new content\n")

    def test_wait_for_artifact_accepts_change_that_happened_before_wait_started_when_baseline_passed_in(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")
            baseline = helper_server.capture_artifact_fingerprint(str(artifact))
            artifact.write_text("new content written during agent run\n", encoding="utf-8")

            helper_server.wait_for_artifact(
                str(artifact),
                timeout_seconds=2,
                poll_interval_seconds=1,
                previous_fingerprint=baseline,
            )
            self.assertEqual(
                artifact.read_text(encoding="utf-8"),
                "new content written during agent run\n",
            )

    def test_wait_for_artifact_accepts_already_changed_file_even_when_remaining_budget_is_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")
            baseline = helper_server.capture_artifact_fingerprint(str(artifact))
            artifact.write_text("new content already finished\n", encoding="utf-8")

            helper_server.wait_for_artifact(
                str(artifact),
                timeout_seconds=0,
                poll_interval_seconds=1,
                previous_fingerprint=baseline,
            )

    def test_http_handler_does_not_spend_full_wait_budget_after_run_budget_already_consumed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "artifact.md"
            artifact.write_text("old content\n", encoding="utf-8")

            def fake_run_agent(**kwargs):
                time.sleep(1.2)
                return {"runId": "fake-run", "result": {"payloads": [{"text": "OK"}]}}

            server = helper_server.ThreadingHTTPServer(("127.0.0.1", 0), helper_server.Handler)
            port = server.server_address[1]
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.addCleanup(server.shutdown)
            self.addCleanup(server.server_close)
            self.addCleanup(thread.join, 1)

            payload = {
                "agent_id": "main",
                "session_key": "test-session",
                "prompt": "不要修改文件，只回复 OK",
                "artifact_absolute_path": str(artifact),
                "timeout_seconds": 2,
                "poll_interval_seconds": 5,
            }

            with patch.object(helper_server, "run_agent", side_effect=fake_run_agent), \
                 patch.object(helper_server, "map_container_path_to_host", side_effect=lambda path, **kwargs: path), \
                 patch.object(helper_server, "rewrite_container_workspace_paths_in_text", side_effect=lambda text, **kwargs: text):
                req = urllib.request.Request(
                    f"http://127.0.0.1:{port}",
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json; charset=utf-8"},
                    method="POST",
                )
                start = time.time()
                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(req, timeout=10)
                elapsed = time.time() - start
                body = ctx.exception.read().decode("utf-8", "replace")

            self.assertEqual(ctx.exception.code, 500)
            self.assertIn("artifact not ready", body)
            self.assertLess(elapsed, 3.0)


if __name__ == "__main__":
    unittest.main()
