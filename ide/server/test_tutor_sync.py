from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2


class TutorSyncTests(unittest.TestCase):
    def test_api_revision_changes_when_tutor_file_changes(self):
        original_path = app_v2.TUTOR_PATH
        original_workspace = app_v2.WORKSPACE
        with tempfile.TemporaryDirectory() as directory:
            app_v2.WORKSPACE = Path(directory)
            app_v2.TUTOR_PATH = app_v2.WORKSPACE / "tutor.py"
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                first = client.get("/api/tutor", headers={"host": "127.0.0.1"})
                self.assertEqual(first.status_code, 200)
                first_payload = first.json()
                self.assertTrue(first_payload["revision"])

                second = client.put(
                    "/api/tutor",
                    headers={"host": "127.0.0.1"},
                    json={"content": first_payload["content"] + "\nprint('external')\n"},
                )
                self.assertEqual(second.status_code, 200)
                self.assertNotEqual(second.json()["revision"], first_payload["revision"])
            finally:
                app_v2.TUTOR_PATH = original_path
                app_v2.WORKSPACE = original_workspace


if __name__ == "__main__":
    unittest.main()
