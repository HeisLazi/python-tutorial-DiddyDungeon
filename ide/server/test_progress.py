from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2


class ProgressRevisionTests(unittest.TestCase):
    def test_local_mutations_increment_revision_without_paths(self):
        original_path = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            app_v2.PROGRESS_PATH = Path(directory) / "progress.json"
            try:
                progress = {"player": {"coins": 0}}
                first = app_v2.write_progress_atomic(progress)
                second = app_v2.write_progress_atomic(progress)
                persisted = json.loads(app_v2.PROGRESS_PATH.read_text(encoding="utf-8"))
            finally:
                app_v2.PROGRESS_PATH = original_path

        self.assertEqual(first["revision"], 1)
        self.assertEqual(second["revision"], 2)
        self.assertEqual(persisted["meta"]["revision"], 2)
        self.assertEqual(persisted["meta"]["device_id"], "local-forge")
        self.assertNotIn("workspace", persisted["meta"])
        self.assertNotIn("path", persisted["meta"])

    def test_editor_cannot_bypass_state_service_with_direct_progress_write(self):
        client = TestClient(app_v2.app, base_url="http://127.0.0.1")
        for method, path in ((client.put, "/api/file"), (client.post, "/api/format")):
            response = method(
                path,
                headers={"host": "127.0.0.1"},
                json={"path": "progress.json", "content": "{}"},
            )
            self.assertEqual(response.status_code, 403)

    def test_terminal_environment_points_cli_at_repo_state_not_workspace_cwd(self):
        original_root = app_v2.REPO_ROOT
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            workspace = Path(directory) / "quest"
            root.mkdir()
            workspace.mkdir()
            canonical = root / "progress.json"
            app_v2.REPO_ROOT = root
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            try:
                environment = app_v2.terminal_environment("ai")
            finally:
                app_v2.REPO_ROOT = original_root
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

        self.assertEqual(environment["QUESTLAB_CANONICAL_STATE_PATH"], str(canonical))
        self.assertEqual(environment["QUESTLAB_STATE_PATH"], str(canonical))
        self.assertEqual(environment["QUESTLAB_LEGACY_STATE_PATH"], str(workspace / "progress.json"))
        self.assertEqual(environment["QUESTLAB_TERMINAL_ROLE"], "ai")
        self.assertIn(str(root), environment["PYTHONPATH"].split(":"))
        self.assertIn(str(root), environment["PATH"].split(":"))


if __name__ == "__main__":
    unittest.main()
