from __future__ import annotations

import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ide.server import app_v2
from ide.server.state import CUSTODY_CONFIRMATION_TOKEN, LocalStateService, state_custody_report


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
        self.assertIn(str(root), environment["PYTHONPATH"].split(os.pathsep))
        self.assertIn(str(root), environment["PATH"].split(os.pathsep))
        self.assertEqual(environment["PATH"].split(os.pathsep)[-1], str(root))

    def test_custody_endpoint_is_a_read_only_preview(self):
        original_root = app_v2.REPO_ROOT
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            workspace = Path(directory) / "quest"
            root.mkdir()
            workspace.mkdir()
            canonical = root / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 3}, "player": {"level": 2}}), encoding="utf-8")
            app_v2.REPO_ROOT = root
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                response = client.get("/api/state/custody", headers={"host": "127.0.0.1"})
                body = response.json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(body["status"], "approval-required")
                self.assertEqual(body["source_revision"], 3)
                self.assertFalse(body["migration_write_performed"])
                self.assertFalse((root / "progress.json").stat().st_size == 0)
            finally:
                app_v2.REPO_ROOT = original_root
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

    def test_custody_preview_never_chooses_a_newest_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "canonical.json"
            proposed = root / "local" / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 3}, "player": {"coins": 55}}), encoding="utf-8")

            missing = state_custody_report(canonical, proposed)
            self.assertEqual(missing["status"], "approval-required")
            self.assertIsNone(missing["destination_revision"])

            proposed.parent.mkdir()
            proposed.write_bytes(canonical.read_bytes())
            same = state_custody_report(canonical, proposed)
            self.assertEqual(same["status"], "already-local")
            self.assertFalse(same["approval_required"])

            proposed.write_text(json.dumps({"meta": {"revision": 99}, "player": {"coins": 999}}), encoding="utf-8")
            conflict = state_custody_report(canonical, proposed)
            self.assertEqual(conflict["status"], "conflict")
            self.assertTrue(conflict["approval_required"])
            self.assertEqual(conflict["source_revision"], 3)
            self.assertEqual(conflict["destination_revision"], 99)

    def test_custody_preview_resumes_gateway_migrated_destination_after_local_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "canonical.json"
            proposed = root / "local" / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 3}, "player": {"coins": 55}}), encoding="utf-8")

            source_service = LocalStateService(canonical, threading.RLock())
            source_service.migrate_local_state(
                proposed,
                expected_source_revision=3,
                confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
                forbidden_paths=(root / "legacy" / "progress.json",),
            )
            local_service = LocalStateService(proposed, threading.RLock())
            advanced = json.loads(proposed.read_text(encoding="utf-8"))
            advanced["player"]["coins"] = 56
            persisted = local_service.persist(advanced)
            self.assertEqual(persisted["revision"], 4)

            report = state_custody_report(canonical, proposed)

        self.assertEqual(report["status"], "already-local")
        self.assertFalse(report["approval_required"])
        self.assertTrue(report["custody_marker_verified"])
        self.assertTrue(report["custody_resume_authorized"])
        self.assertEqual(report["source_revision"], 3)
        self.assertEqual(report["destination_revision"], 4)

    def test_custody_preview_rejects_advanced_destination_when_reviewed_source_changed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            canonical = root / "canonical.json"
            proposed = root / "local" / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 3}, "player": {"coins": 55}}), encoding="utf-8")
            source_service = LocalStateService(canonical, threading.RLock())
            source_service.migrate_local_state(
                proposed,
                expected_source_revision=3,
                confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
            )
            local_service = LocalStateService(proposed, threading.RLock())
            advanced = json.loads(proposed.read_text(encoding="utf-8"))
            advanced["player"]["coins"] = 56
            local_service.persist(advanced)
            canonical.write_text(json.dumps({"meta": {"revision": 4}, "player": {"coins": 57}}), encoding="utf-8")

            report = state_custody_report(canonical, proposed)

        self.assertEqual(report["status"], "conflict")
        self.assertTrue(report["approval_required"])
        self.assertFalse(report["custody_marker_verified"])
        self.assertFalse(report["custody_resume_authorized"])

    def test_custody_migration_route_is_opt_in_and_uses_derived_destination(self):
        original_root = app_v2.REPO_ROOT
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            workspace = Path(directory) / "quest"
            local_root = Path(directory) / "local-state"
            root.mkdir()
            workspace.mkdir()
            canonical = root / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 3}, "player": {"coins": 55}}), encoding="utf-8")
            app_v2.REPO_ROOT = root
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                headers = {"host": "127.0.0.1"}
                denied = client.post(
                    "/api/state/custody/migrate",
                    headers=headers,
                    json={"expected_source_revision": 3, "confirmation_token": "NOPE"},
                )
                self.assertEqual(denied.status_code, 403)

                with patch.dict("os.environ", {"QUESTLAB_LOCAL_STATE_ROOT": str(local_root)}):
                    migrated = client.post(
                        "/api/state/custody/migrate",
                        headers=headers,
                        json={
                            "expected_source_revision": 3,
                            "confirmation_token": CUSTODY_CONFIRMATION_TOKEN,
                        },
                    )
                body = migrated.json()
                self.assertEqual(migrated.status_code, 200)
                self.assertEqual(body["status"], "migrated")
                self.assertTrue(body["migration_write_performed"])
                self.assertEqual(body["revision"], 3)
                marker_path = Path(body["marker_path"])
                destination_path = marker_path.parent / "progress.json"
                self.assertNotEqual(destination_path, canonical)
                self.assertEqual(json.loads(marker_path.read_text(encoding="utf-8"))["source_revision"], 3)
                self.assertEqual(canonical.read_bytes(), destination_path.read_bytes())
            finally:
                app_v2.REPO_ROOT = original_root
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress


if __name__ == "__main__":
    unittest.main()
