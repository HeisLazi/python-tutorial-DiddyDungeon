from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from ide.server import app_v2
from ide import workspace_transfer


class WorkspaceTransferApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_v2.app, base_url="http://127.0.0.1")

    def test_status_redacts_workspace_path(self):
        with patch.object(
            app_v2.workspace_transfer,
            "status",
            return_value={
                "ok": True,
                "workspace": "C:/private/project",
                "transfer_branch": "questlab-files/01-blackjack",
                "remote_commit": "abc123",
                "files": [],
            },
        ):
            response = self.client.get("/api/workspace-transfer", headers={"host": "127.0.0.1"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("workspace", response.json())
        self.assertEqual(response.json()["transfer_branch"], "questlab-files/01-blackjack")

    def test_push_requires_explicit_confirmation(self):
        response = self.client.post(
            "/api/workspace-transfer",
            json={"action": "push"},
            headers={"host": "127.0.0.1"},
        )
        self.assertEqual(response.status_code, 400)

    def test_push_and_pull_apply_use_allowlist_tokens(self):
        with patch.object(
            app_v2.workspace_transfer,
            "push",
            return_value={"ok": True, "applied": True, "workspace": "/private/project", "files": []},
        ) as push_mock, patch.object(
            app_v2.workspace_transfer,
            "pull",
            return_value={"ok": True, "applied": True, "workspace": "/private/project", "backup_directory": "/tmp/secret"},
        ) as pull_mock:
            pushed = self.client.post(
                "/api/workspace-transfer",
                json={"action": "push", "confirmation": workspace_transfer.CONFIRM_PUSH},
                headers={"host": "127.0.0.1"},
            )
            pulled = self.client.post(
                "/api/workspace-transfer",
                json={
                    "action": "pull_apply",
                    "confirmation": workspace_transfer.CONFIRM_PULL,
                    "allow_overwrite": True,
                },
                headers={"host": "127.0.0.1"},
            )

        self.assertEqual(pushed.status_code, 200)
        self.assertEqual(pulled.status_code, 200)
        self.assertNotIn("workspace", pushed.json())
        self.assertNotIn("backup_directory", pulled.json())
        self.assertTrue(pulled.json()["backup_created"])
        push_mock.assert_called_once()
        pull_mock.assert_called_once()
        self.assertEqual(pull_mock.call_args.kwargs["allow_overwrite"], True)


if __name__ == "__main__":
    unittest.main()
