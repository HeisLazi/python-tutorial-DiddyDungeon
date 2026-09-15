from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2


def context_progress() -> dict:
    return {
        "meta": {"revision": 7, "updated_at": "2026-09-15T00:00:00+00:00", "device_id": "local-forge"},
        "player": {"level": 2, "xp": 50, "xp_next": 100, "lifetime_xp": 150, "coins": 55, "hp": 100, "max_hp": 100},
        "learning_state": {
            "project": "01-blackjack",
            "concept": "Input loops and control flow",
            "phase": "forge",
            "reference_mode": False,
            "clean_clear_eligible": True,
        },
        "assist": {"mode": "clean", "reference_mode_uses": 0, "guided_milestones": 0},
        "projects": [
            {
                "branch": "01-blackjack",
                "name": "Blackjack",
                "status": "active",
                "progress": 38,
                "boss": "The House",
                "mobs": [
                    {"name": "The Empty Table", "status": "defeated", "concept": "Variables"},
                    {"name": "The Dealer's Hand", "status": "defeated", "concept": "Lists"},
                    {"name": "The Count Keeper", "status": "defeated", "concept": "Loops"},
                    {
                        "name": "The Hitman",
                        "status": "available",
                        "concept": "Input loops and control flow",
                        "encounter": "Reason about repeated player choices.",
                        "max_resolve": 8,
                        "resolve": 8,
                    },
                    {"name": "The Bust Hound", "status": "locked", "concept": "Conditionals"},
                ],
            }
        ],
        "encounter_state": {
            "project_id": "01-blackjack",
            "mob_name": "The Hitman",
            "status": "active",
            "resolve": 8,
            "max_resolve": 8,
            "completed_objectives": [],
            "attempts": 0,
            "question_types": [],
        },
        "state_events": [],
    }


class PyrContextBridgeTests(unittest.TestCase):
    def test_context_is_bounded_live_and_does_not_mutate_player_state(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            (workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.PYR_CONTEXT_INPUT.update({"active_path": None, "selection": "", "terminal_tail": ""})
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                response = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={
                        "active_path": "main.py",
                        "selection": "\x1b[31mwhile\x1b[0m choice:\n    print(choice)",
                        "terminal_tail": "\x1b[2KTraceback\r\nValueError: bad input\r\n",
                    },
                )
                self.assertEqual(response.status_code, 200)
                context = response.json()["context"]
                self.assertEqual(context["revision"], 7)
                self.assertEqual(context["active_file"]["path"], "main.py")
                self.assertEqual(context["active_file"]["content"], "print('hello')\n")
                self.assertEqual(context["selection"]["text"], "while choice:\n    print(choice)")
                self.assertEqual(context["terminal"]["tail"], "Traceback\nValueError: bad input\n")
                self.assertEqual(context["quest"]["mob"]["name"], "The Hitman")
                self.assertEqual(context["quest"]["mob"]["concept"], "Input loops and control flow")
                self.assertEqual(context["quest"]["assistance"]["mode"], "clean")
                self.assertNotIn("The Bust Hound", json.dumps(context["quest"]["mob"]))

                persisted = json.loads(canonical.read_text(encoding="utf-8"))
                self.assertEqual(persisted["meta"]["revision"], 7)
                self.assertEqual(persisted["state_events"], [])

                fetched = client.get("/api/pyr/context", headers={"host": "127.0.0.1"})
                self.assertEqual(fetched.status_code, 200)
                self.assertEqual(fetched.json()["context"]["active_file"]["path"], "main.py")
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

    def test_context_rejects_state_file_and_bounds_large_text(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            (workspace / "progress.json").write_text("{}", encoding="utf-8")
            canonical = root / "progress.json"
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.PYR_CONTEXT_INPUT.update({"active_path": None, "selection": "", "terminal_tail": ""})
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                rejected = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"active_path": "progress.json"},
                )
                self.assertEqual(rejected.status_code, 403)

                bounded = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"selection": "x" * 25_000, "terminal_tail": "y" * 25_000},
                )
                self.assertEqual(bounded.status_code, 200)
                context = bounded.json()["context"]
                self.assertTrue(context["selection"]["truncated"])
                self.assertTrue(context["terminal"]["truncated"])
                self.assertLessEqual(len(context["selection"]["text"].encode()), 20_000)
                self.assertLessEqual(len(context["terminal"]["tail"].encode()), 20_000)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress


if __name__ == "__main__":
    unittest.main()
