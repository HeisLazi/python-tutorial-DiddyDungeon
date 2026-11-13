import json
import tempfile
import threading
import unittest
from pathlib import Path

from ide.server.new_game import fresh_progress, initialize_new_save
from ide.server.state import LocalStateService


class NewGameTests(unittest.TestCase):
    def test_starter_campaign_is_playable_and_starts_fresh(self):
        progress = fresh_progress()
        self.assertEqual(progress["player"]["level"], 1)
        self.assertEqual(progress["player"]["coins"], 0)
        project = next(p for p in progress["projects"] if p["branch"] == "00-lantern-vale")
        self.assertEqual(project["status"], "active")
        self.assertEqual(project["mobs"][0]["status"], "available")
        self.assertTrue(all(mob["status"] == "locked" for mob in project["mobs"][1:]))

    def test_new_save_is_accepted_by_state_service_and_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            save = Path(directory) / "data" / "progress.json"
            self.assertTrue(initialize_new_save(save))
            service = LocalStateService(save, threading.RLock())
            self.assertEqual(service.snapshot()["player"]["level"], 1)
            existing = save.read_bytes()
            self.assertFalse(initialize_new_save(save))
            self.assertEqual(save.read_bytes(), existing)
            json.loads(existing)

    def test_relative_path_is_rejected(self):
        with self.assertRaises(ValueError):
            initialize_new_save(Path("progress.json"))


if __name__ == "__main__":
    unittest.main()
