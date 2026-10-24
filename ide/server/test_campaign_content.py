from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
from pathlib import Path

from ide.server import state
from ide.server.state import (
    CAMPAIGN_QUESTION_TYPES,
    HUNTER_BEASTS,
    MAX_IMPACT,
    MAX_SYNC_MOBS_PER_PROJECT,
    LocalStateService,
)

CONTENT_DIR = Path(state.__file__).with_name("campaigns")
IDENTIFIER = re.compile(r"^[a-z0-9][a-z0-9_]*$")


def use_real_content() -> None:
    state.CAMPAIGN_CONTENT_DIR = CONTENT_DIR
    state._CAMPAIGN_CACHE.update(key=None, data={})


def story_files() -> list[dict]:
    return [json.loads(path.read_text(encoding="utf-8")) for path in sorted(CONTENT_DIR.glob("*.json"))]


class CampaignContentSchemaTests(unittest.TestCase):
    def test_every_story_file_is_well_formed(self):
        files = story_files()
        self.assertTrue(files)
        for entry in files:
            branch = entry["branch"]
            with self.subTest(branch=branch):
                for key in ("name", "boss", "entry_file", "boss_brief"):
                    self.assertIsInstance(entry.get(key), str, key)
                self.assertTrue(entry["entry_file"].endswith(".py"))
                acts = {act["id"] for act in entry["acts"]}
                mobs = entry["mobs"]
                self.assertLessEqual(len(mobs), MAX_SYNC_MOBS_PER_PROJECT)
                names = [mob["name"] for mob in mobs]
                self.assertEqual(len(names), len(set(names)), "contract names must be unique")
                for mob in mobs:
                    for key in ("name", "concept", "encounter", "contract"):
                        self.assertIsInstance(mob.get(key), str, (mob.get("name"), key))
                    self.assertLessEqual(len(mob["name"]), 120)
                    self.assertIn(mob["act"], acts, mob["name"])
                    self.assertTrue(mob.get("sign") is None or mob["sign"] in HUNTER_BEASTS, mob["name"])
                    if mob.get("legacy_profile"):
                        self.assertNotIn("objectives", mob)
                        continue
                    objectives = mob["objectives"]
                    self.assertTrue(3 <= len(objectives) <= 5, mob["name"])
                    ids = [item["id"] for item in objectives]
                    self.assertEqual(len(ids), len(set(ids)), mob["name"])
                    for item in objectives:
                        self.assertRegex(item["id"], IDENTIFIER)
                        self.assertIn(item["question_type"], CAMPAIGN_QUESTION_TYPES, (mob["name"], item["id"]))
                        self.assertTrue(1 <= item["impact"] <= MAX_IMPACT, (mob["name"], item["id"]))
                        self.assertTrue(item["label"].strip() and item["brief"].strip())
                    # Most of every contract is building code, not talking about it.
                    kinds = [item["question_type"] for item in objectives]
                    self.assertGreaterEqual(kinds.count("code_checkpoint") + kinds.count("bug_diagnosis"), len(kinds) / 2, mob["name"])


def user_like_progress() -> dict:
    """A save like the player's: Blackjack's original eight bounties beaten and
    The House unlocked, plus a finished project that must stay untouched."""

    blackjack = json.loads((CONTENT_DIR / "01-blackjack.json").read_text(encoding="utf-8"))
    act_one = [mob for mob in blackjack["mobs"] if mob.get("legacy_profile")]
    return {
        "schema_version": 1,
        "meta": {"device_id": "device-alpha", "updated_at": "2026-01-01T00:00:00+00:00", "revision": 1},
        "player": {"name": "Hunter", "level": 3, "xp": 0, "coins": 50, "hp": 100, "max_hp": 100},
        "stats": {},
        "projects": [
            {"branch": "00-rps-tournament", "name": "Rock Paper Scissors Tournament", "status": "completed", "completed": True, "progress": 100, "boss": "The Pattern Warden", "mobs": []},
            {
                "branch": "01-blackjack",
                "name": "Blackjack",
                "status": "active",
                "progress": 100,
                "boss": "The House",
                "boss_status": "available",
                "mobs": [{"name": mob["name"], "concept": mob["concept"], "encounter": mob["encounter"], "status": "defeated", "resolve": 0} for mob in act_one],
            },
        ],
    }


class CampaignExtensionTests(unittest.TestCase):
    def setUp(self):
        use_real_content()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "progress.json"
        self.path.write_text(json.dumps(user_like_progress()), encoding="utf-8")
        self.service = LocalStateService(self.path, threading.RLock())

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def blackjack(self) -> dict:
        return next(project for project in self.read()["projects"] if project["branch"] == "01-blackjack")

    def test_an_extended_board_reopens_with_the_new_contracts_and_relocks_the_boss(self):
        result = self.service.apply_internal("campaign_extend", {})
        self.assertTrue(result["changed"])
        project = self.blackjack()
        self.assertEqual(len(project["mobs"]), 19)
        self.assertEqual([mob["status"] for mob in project["mobs"][:8]], ["defeated"] * 8)
        self.assertEqual(project["mobs"][8]["name"], "The Ace Trickster")
        self.assertEqual(project["mobs"][8]["status"], "available")
        self.assertTrue(all(mob["status"] == "locked" for mob in project["mobs"][9:]))
        self.assertNotIn("boss_status", project)
        self.assertEqual(project["progress"], round(8 / 19 * 100))
        self.assertEqual(project["entry_file"], "blackjack.py")
        self.assertTrue(all(set(mob) <= {"name", "concept", "encounter", "status", "resolve"} for mob in project["mobs"]))
        self.assertFalse(self.service.apply_internal("campaign_extend", {})["changed"])  # idempotent
        finished = next(item for item in self.read()["projects"] if item["branch"] == "00-rps-tournament")
        self.assertEqual(finished["mobs"], [])

    def test_an_authored_contract_falls_on_its_last_objective(self):
        self.service.apply_internal("campaign_extend", {})
        encounter = self.service.encounter_projection(self.read())
        self.assertEqual(encounter["mob_name"], "The Ace Trickster")
        self.assertEqual([item["id"] for item in encounter["available_objectives"]], ["ace_rule", "multi_ace_trace", "ace_bug"])
        self.assertEqual(encounter["max_resolve"], 8)
        self.assertEqual(encounter["mob"]["sign_id"], "conditionals")
        self.assertIn("trickster", encounter["mob"]["contract"])
        outcomes = []
        for objective in ("ace_rule", "multi_ace_trace", "ace_bug"):
            result = self.service.apply_internal("record_battle_objective", {"objective_id": objective, "evidence_id": f"bj-{objective}", "reason": "Verified"})
            outcomes.append(result["result"]["mob_defeated"])
        self.assertEqual(outcomes, [False, False, True])
        project = self.blackjack()
        self.assertEqual(project["mobs"][9]["status"], "available")

    def test_the_board_projection_tells_the_story(self):
        board = self.service.campaign_board(self.service.campaign_view(self.read()))
        self.assertEqual(board["story"]["title"], "The Gilded Table")
        self.assertEqual([act["id"] for act in board["acts"]], [1, 2, 3])
        self.assertEqual(len(board["contracts"]), 19)
        trickster = board["contracts"][8]
        self.assertEqual((trickster["act"], trickster["sign"], trickster["beast"]), (2, "conditionals", "The Forked Path"))
        self.assertEqual(len(trickster["objectives"]), 3)
        self.assertEqual(len(self.blackjack()["mobs"]), 8)  # a read never writes the save

    def test_new_agent_projects_join_the_campaign_and_open_with_their_boards(self):
        self.service.apply_internal("campaign_extend", {})
        branches = {project["branch"]: project for project in self.read()["projects"]}
        self.assertEqual(branches["08-game-agent"]["status"], "available")
        self.assertEqual(branches["09-ai-agent"]["name"], "The Familiar")
        self.assertTrue(set(branches["09-ai-agent"]) <= {"branch", "name", "status", "boss", "order", "progress", "mobs", "entry_file"})  # entry_file is never synced
        selected = self.service.apply("select_campaign", {"branch": "09-ai-agent"}, "player")["result"]["project"]
        self.assertEqual(selected["entry_file"], "agent.py")
        project = next(item for item in self.read()["projects"] if item["branch"] == "09-ai-agent")
        self.assertEqual(len(project["mobs"]), 16)
        self.assertEqual(project["mobs"][0]["status"], "available")
        encounter = self.service.encounter_projection(self.read())
        self.assertEqual(encounter["mob_name"], "The Silent Familiar")
        self.assertEqual([item["id"] for item in encounter["available_objectives"]], ["chat_loop", "quit_words", "empty_input"])
        # Blackjack keeps its board while another project is played.
        self.assertEqual(len(next(item for item in self.read()["projects"] if item["branch"] == "01-blackjack")["mobs"]), 19)


if __name__ == "__main__":
    unittest.main()
