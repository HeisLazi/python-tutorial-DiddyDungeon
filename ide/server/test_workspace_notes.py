from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2
from ide.server.state import LocalStateService


class WorkspaceNoteRouteTests(unittest.TestCase):
    def setUp(self):
        self.original_workspace = app_v2.WORKSPACE
        self.original_progress = app_v2.PROGRESS_PATH
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.workspace = root / "quest"
        self.workspace.mkdir()
        self.canonical = root / "platform" / "progress.json"
        self.canonical.parent.mkdir()
        self.canonical.write_text(
            json.dumps({"meta": {"revision": 7}, "player": {"level": 2, "xp": 50}}),
            encoding="utf-8",
        )
        app_v2.WORKSPACE = self.workspace
        app_v2.PROGRESS_PATH = self.canonical
        self.client = TestClient(app_v2.app, base_url="http://127.0.0.1")

    def tearDown(self):
        app_v2.WORKSPACE = self.original_workspace
        app_v2.PROGRESS_PATH = self.original_progress
        self.directory.cleanup()

    def test_concept_note_round_trip_is_workspace_only(self):
        before = self.canonical.read_bytes()
        absent = self.client.get("/api/notes/lists", headers={"host": "127.0.0.1"})
        self.assertEqual(absent.status_code, 200)
        self.assertFalse(absent.json()["note"]["exists"])

        saved = self.client.put(
            "/api/notes/lists",
            headers={"host": "127.0.0.1"},
            json={"content": "# Lists\r\n\r\nUse `.append()` carefully.\r\n"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        note = saved.json()["note"]
        self.assertEqual(note["concept_id"], "lists")
        self.assertEqual(note["path"], "notes/lists.md")
        self.assertEqual(note["content"], "# Lists\n\nUse `.append()` carefully.\n")
        self.assertTrue(note["exists"])
        self.assertEqual((self.workspace / "notes" / "lists.md").read_text(encoding="utf-8"), note["content"])
        self.assertEqual(self.canonical.read_bytes(), before)

        listing = self.client.get("/api/notes", headers={"host": "127.0.0.1"})
        self.assertEqual(listing.status_code, 200)
        self.assertEqual(listing.json()["notes"][0]["concept_id"], "lists")
        loaded = self.client.get("/api/notes/LISTS", headers={"host": "127.0.0.1"})
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(loaded.json()["note"]["revision"], note["revision"])

    def test_generic_file_api_cannot_bypass_notes_boundary(self):
        payload = {"path": "notes/lists.md", "content": "provider must not bypass"}
        self.assertEqual(
            self.client.put("/api/file", headers={"host": "127.0.0.1"}, json=payload).status_code,
            403,
        )
        self.assertEqual(
            self.client.get("/api/file?path=notes/lists.md", headers={"host": "127.0.0.1"}).status_code,
            403,
        )
        tree = self.client.get("/api/tree", headers={"host": "127.0.0.1"})
        self.assertEqual(tree.status_code, 200)
        self.assertNotIn("notes", {item["path"] for item in tree.json()["items"]})

    def test_note_identifier_and_content_limits_are_enforced(self):
        unsafe = self.client.put(
            "/api/notes/..%2Fprogress",
            headers={"host": "127.0.0.1"},
            json={"content": "no"},
        )
        self.assertIn(unsafe.status_code, {404, 422})
        control = self.client.put(
            "/api/notes/lists",
            headers={"host": "127.0.0.1"},
            json={"content": "bad\u0007note"},
        )
        self.assertEqual(control.status_code, 422)
        oversized = self.client.put(
            "/api/notes/lists",
            headers={"host": "127.0.0.1"},
            json={"content": "x" * (app_v2.MAX_WORKSPACE_NOTE_BYTES + 1)},
        )
        self.assertEqual(oversized.status_code, 422)

    def test_note_write_does_not_create_state_revision_or_event(self):
        before = json.loads(self.canonical.read_text(encoding="utf-8"))
        response = self.client.put(
            "/api/notes/loops",
            headers={"host": "127.0.0.1"},
            json={"content": "A loop repeats a block."},
        )
        self.assertEqual(response.status_code, 200)
        after = json.loads(self.canonical.read_text(encoding="utf-8"))
        self.assertEqual(after, before)


class TutorPracticeProjectionTests(unittest.TestCase):
    def test_practice_projection_contains_safe_unified_selectors(self):
        service = LocalStateService(Path("/tmp/questlab-unused-progress.json"), threading.RLock())
        projection = service.practice_projection({"practice_sessions": []})
        self.assertEqual(projection["tutor_file"], "tutor.py")
        self.assertEqual(projection["notes_directory"], "notes")
        self.assertEqual(projection["difficulty"], {"min": 1, "max": 5})
        self.assertEqual(
            [item["id"] for item in projection["question_types"]],
            ["true_false", "multiple_choice", "short_explanation", "code_trace", "bug_hunt"],
        )
        self.assertTrue(any(item["id"] == "lists" for item in projection["concepts"]))
        serialized = json.dumps(projection)
        self.assertNotIn("answer", serialized.casefold())
        self.assertNotIn("prompt", serialized.casefold())

    def test_codex_projection_links_notes_without_exposing_note_contents(self):
        service = LocalStateService(Path("/tmp/questlab-unused-progress.json"), threading.RLock())
        projection = service.codex_projection(
            {
                "codex": {
                    "encounters": [
                        {
                            "id": "01-blackjack-empty-table",
                            "project_id": "01-blackjack",
                            "mob_name": "The Empty Table",
                            "concept": "Variables",
                            "status": "defeated",
                        }
                    ]
                }
            }
        )
        entry = projection["entries"][0]
        self.assertEqual(entry["notes_path"], "notes/variables.md")
        page = next(page for page in projection["pages"] if page["id"] == "variables")
        self.assertEqual(page["notes_path"], "notes/variables.md")
        # Generic examples are intentionally allowed to teach ordinary names
        # such as ``answer``; the projection still contains no encounter
        # prompt, answer key, or raw provider submission.
        self.assertNotIn("answer_key", entry)
        self.assertNotIn("prompt", entry)


if __name__ == "__main__":
    unittest.main()
