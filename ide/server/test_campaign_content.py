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
    state.CAMPAIGN_BOUNTIES_PATH = None
    state.CAMPAIGN_CONTENT_DIR = CONTENT_DIR
    state._CAMPAIGN_CACHE.update(key=None, data={})


def state_module_base() -> Path:
    from ide.server.conftest import LEGACY_BOARDS

    return LEGACY_BOARDS


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
                    ids = [item["id"] for item in objectives]
                    self.assertEqual(len(ids), len(set(ids)), mob["name"])
                    for item in objectives:
                        self.assertRegex(item["id"], IDENTIFIER)
                        self.assertIn(item["question_type"], CAMPAIGN_QUESTION_TYPES, (mob["name"], item["id"]))
                        self.assertTrue(1 <= item["impact"] <= MAX_IMPACT, (mob["name"], item["id"]))
                        self.assertTrue(item["label"].strip() and item["brief"].strip())
                    # Setup steps (make the folder, make the file) open a workshop
                    # bounty and sit outside its fight shape; a first-run check
                    # is that fight's build.
                    steps = [item for item in objectives if item["question_type"] == "setup_check"]
                    for item in steps:
                        self.assertTrue(state.setup_check_spec(item.get("check")), (mob["name"], item["id"]))
                    setup = [item for item in steps if "run" not in item["check"]]
                    self.assertTrue(not steps or mob.get("kind") == "workshop", mob["name"])
                    self.assertLessEqual(len(setup), 3, mob["name"])
                    self.assertEqual(objectives[:len(setup)], setup, mob["name"])  # setup comes first
                    fight = objectives[len(setup):]
                    kinds = [item["question_type"] for item in fight]
                    code = kinds.count("code_checkpoint") + kinds.count("bug_diagnosis") + sum(1 for item in fight if "run" in item.get("check", {}))
                    tier = mob.get("tier")
                    self.assertIn(tier, {None, "light", "quick", "elite"}, mob["name"])
                    self.assertIn(mob.get("kind"), {None, "workshop", "debug", "memory", "creative"}, mob["name"])
                    for item in objectives:
                        for name in [item.get("file"), *item.get("see", [])]:
                            self.assertTrue(name is None or state.project_file_name(name), (mob["name"], name))
                    if tier == "light":
                        # A lighter fight: one coding task and two questions, early on
                        # or as the bounty that opens an act.
                        self.assertEqual((len(kinds), code), (3, 1), mob["name"])
                        opens_act = next(item for item in mobs if item["act"] == mob["act"]) is mob
                        self.assertTrue(mob["act"] <= 2 or opens_act, mob["name"])
                    elif tier == "quick":
                        self.assertEqual((len(kinds), code), (2, 1), mob["name"])
                    elif tier == "elite":
                        self.assertTrue(4 <= len(kinds) <= 5 and code >= 3, mob["name"])
                    else:
                        # A standard contract: three or four goals, mostly building code.
                        self.assertTrue(3 <= len(kinds) <= 4, mob["name"])
                        self.assertGreaterEqual(code, len(kinds) / 2, mob["name"])

    def test_full_length_campaigns_teach_the_whole_craft(self):
        # A rebuilt (multi-file) campaign: 18-20 bounties in four acts, a
        # workshop thread through every act, debugging, a rebuild from memory,
        # a creative bounty, repeated concepts and a project the grader can see.
        full = [entry for entry in story_files() if entry.get("multi_file")]
        self.assertTrue(full)
        for entry in full:
            with self.subTest(branch=entry["branch"]):
                mobs = entry["mobs"]
                self.assertTrue(18 <= len(mobs) <= MAX_SYNC_MOBS_PER_PROJECT, len(mobs))
                self.assertEqual(len(entry["acts"]), 4)
                kinds = [mob.get("kind") for mob in mobs]
                for act in entry["acts"]:
                    self.assertTrue(any(mob.get("kind") == "workshop" for mob in mobs if mob["act"] == act["id"]), act["title"])
                self.assertGreaterEqual(kinds.count("debug"), 2)
                self.assertGreaterEqual(kinds.count("memory"), 1)
                self.assertGreaterEqual(kinds.count("creative"), 1)
                signs = [mob["sign"] for mob in mobs]
                self.assertGreaterEqual(sum(signs.count(sign) >= 3 for sign in set(signs)), 3)
                goals = [item for mob in mobs for item in mob["objectives"]]
                self.assertTrue(55 <= len(goals) <= 75, len(goals))
                code = sum(item["question_type"] in {"code_checkpoint", "bug_diagnosis"} for item in goals)
                self.assertTrue(0.6 <= code / len(goals) <= 0.8, code / len(goals))
                files = entry["project_files"]
                # The project lives in its own folder, never the workspace root.
                self.assertTrue(state.project_dir_name(entry["project_dir"]))
                self.assertEqual(entry["entry_file"].split("/")[0], entry["project_dir"])
                self.assertIn(entry["entry_file"].split("/")[-1], files)
                self.assertTrue(all(state.project_file_name(name) for name in files))
                named = {name for item in goals for name in [item.get("file"), *item.get("see", [])] if name}
                self.assertLessEqual(named, set(files))
                self.assertIn("README.md", named)

    def test_goal_files_stay_inside_the_project_folder(self):
        for name in ("casino.py", "README.md", "pyproject.toml", "crawler/world.py", "tests/test_world.py"):
            self.assertTrue(state.project_file_name(name), name)
        for name in ("../escape.py", "crawler/../escape.py", "a/b/c.py", ".hidden.py", "tutor.py", "dungeon.py", "/etc/passwd.txt", "notes.exe"):
            self.assertIsNone(state.project_file_name(name), name)

    def test_fights_vary_in_length_and_mix(self):
        files = story_files()
        for entry in files:
            if "project_dir" in entry:  # a full-length campaign mixes every kind of fight
                with self.subTest(branch=entry["branch"]):
                    self.assertEqual({"light", "quick", "elite"} - {mob.get("tier") for mob in entry["mobs"]}, set())
        files.sort(key=lambda entry: entry["order"])
        gauntlets = [tuple(entry["boss_gauntlet"]) for entry in files]
        code_phases = {"required_behavior", "edge_cases", "twist_2", "twist_3", "twist_4"}
        shapes = [(len(g), sum(phase in code_phases for phase in g)) for g in gauntlets]
        self.assertEqual(len(set(shapes)), len(shapes), shapes)  # every boss fights differently
        self.assertEqual(shapes, sorted(shapes))  # and each campaign's boss asks for more than the last
        self.assertEqual(shapes[-1][1], 5)  # the final boss is five coding phases
        for entry in files:
            with self.subTest(branch=entry["branch"]):
                self.assertEqual(entry["boss_gauntlet"][0], "required_behavior")
                self.assertEqual(len(entry["boss_gauntlet"]), len(set(entry["boss_gauntlet"])))
                self.assertLessEqual(set(entry["boss_gauntlet"]), set(state.BOSS_REQUIREMENTS))
                for phase in entry["boss_gauntlet"]:
                    if phase.startswith("twist_"):
                        authored = entry["boss_phases"][phase]
                        self.assertTrue(authored["label"].strip())
                        self.assertGreater(len(authored["quest"]), 150)

    def test_the_engine_uses_every_authored_contract_as_written(self):
        use_real_content()
        for entry in story_files():
            project = {"branch": entry["branch"]}
            for index, mob in enumerate(entry["mobs"]):
                if mob.get("legacy_profile"):
                    continue
                with self.subTest(branch=entry["branch"], contract=mob["name"]):
                    profile = LocalStateService._encounter_profile(index, project, mob)
                    self.assertEqual(list(profile["objectives"]), [item["id"] for item in mob["objectives"]])
                    self.assertEqual(profile["max_resolve"], sum(item["impact"] for item in mob["objectives"]))


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

    def add_old_casino(self, **changes) -> None:
        """Casino as the player's save holds it: the old board, seeded but unplayed."""

        state = self.read()
        old = json.loads(state_module_base().read_text(encoding="utf-8"))["04-casino-slots"]["mobs"]
        casino = {"branch": "04-casino-slots", "name": "Casino / Slots", "status": "available", "progress": 0, "boss": "Lady Luck", "order": 4,
                  "mobs": [{"name": mob["name"], "concept": mob["concept"], "encounter": mob["encounter"], "status": "available" if index == 0 else "locked"} for index, mob in enumerate(old)]}
        casino.update(changes)
        state["projects"].append(casino)
        self.path.write_text(json.dumps(state), encoding="utf-8")

    def casino(self) -> dict:
        return next(project for project in self.read()["projects"] if project["branch"] == "04-casino-slots")

    def test_an_unplayed_rewritten_board_is_reseeded_whole_and_follows_its_new_boss(self):
        self.add_old_casino()
        blackjack_before = self.blackjack()
        self.service.apply_internal("campaign_extend", {})
        casino = self.casino()
        authored = [mob["name"] for mob in json.loads((CONTENT_DIR / "04-casino-slots.json").read_text(encoding="utf-8"))["mobs"]]
        self.assertEqual([mob["name"] for mob in casino["mobs"]], authored)
        self.assertEqual(len(casino["mobs"]), 20)
        self.assertEqual([mob["status"] for mob in casino["mobs"]], ["available"] + ["locked"] * 19)
        self.assertEqual(casino["boss"], "Ekse Ouens P Diddy")
        self.assertTrue(casino["multi_file"])
        self.assertEqual(casino["entry_file"], "silver_reels/casino.py")
        blackjack_after = self.blackjack()
        self.assertEqual([(mob["name"], mob["status"]) for mob in blackjack_after["mobs"][:8]], [(mob["name"], mob["status"]) for mob in blackjack_before["mobs"][:8]])
        once = self.read()
        self.service.apply_internal("campaign_extend", {})
        self.assertEqual(self.read()["projects"], once["projects"])  # doing it again changes nothing

    def test_a_board_with_any_progress_is_never_reseeded(self):
        self.add_old_casino()
        state = self.read()
        casino = next(project for project in state["projects"] if project["branch"] == "04-casino-slots")
        casino["mobs"][0]["status"] = "defeated"
        self.path.write_text(json.dumps(state), encoding="utf-8")
        self.service.apply_internal("campaign_extend", {})
        self.assertEqual(self.casino()["mobs"][0]["name"], "The Coin Rat")
        self.assertEqual(self.casino()["mobs"][1]["name"], "The Spin Imp")
        self.assertEqual(self.casino()["mobs"][0]["status"], "defeated")
        self.assertEqual(len(self.casino()["mobs"]), 20)  # old board kept, then topped up to the cap

    def test_a_goal_can_name_the_file_it_is_graded_on(self):
        board = self.service.campaign_board(self.service.campaign_view({**self.read(), "projects": [
            {"branch": "04-casino-slots", "name": "Casino / Slots", "status": "active", "boss": "Ekse Ouens P Diddy", "mobs": [
                {"name": "The File Splitter", "concept": "Modules", "encounter": "Split it.", "status": "available"}]}]}))
        splitter = board["contracts"][0]
        self.assertEqual(splitter["kind"], "workshop")
        self.assertEqual([item.get("file") for item in splitter["objectives"]], ["reels.py", "payouts.py", "casino.py", None])

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
        self.assertEqual(finished["mobs"], [])  # a finished retired campaign is kept exactly as it was

    def test_asking_pyr_in_a_fight_costs_that_fights_rewards(self):
        import shutil

        def fight(asks):
            directory = tempfile.TemporaryDirectory()
            self.addCleanup(directory.cleanup)
            path = Path(directory.name) / "progress.json"
            shutil.copyfile(self.path, path)
            service = LocalStateService(path, threading.RLock())
            service.apply_internal("campaign_extend", {})
            for _ in range(asks):
                service.apply_internal("record_pyr_assist", {"reason": "Asked PYR during a fight"})
            encounter = service.encounter_projection(json.loads(path.read_text(encoding="utf-8")))
            for objective in ("ace_rule", "multi_ace_trace", "ace_bug"):
                result = service.apply_internal("record_battle_objective", {"objective_id": objective, "evidence_id": f"bj-{objective}", "reason": "Verified"})["result"]
            return encounter, result, json.loads(path.read_text(encoding="utf-8"))

        clean_encounter, clean, _ = fight(0)
        self.assertEqual((clean_encounter["pyr_assists"], clean_encounter["reward_scale"]), (0, 100))
        self.assertEqual(clean["reward_scale"], 100)
        once_encounter, once, once_state = fight(1)
        self.assertEqual((once_encounter["pyr_assists"], once_encounter["reward_scale"]), (1, 80))
        self.assertEqual(once["reward_xp"], clean["reward_xp"] * 80 // 100)
        self.assertEqual(once["reward_coins"], clean["reward_coins"] * 80 // 100)
        trickster = next(mob for mob in once_state["projects"][1]["mobs"] if mob["name"] == "The Ace Trickster")
        self.assertEqual(trickster["assist"], "assisted")  # it no longer counts toward a Clean Clear
        self.assertEqual(once_state["assist"]["pyr_asks"], 1)
        _twice_encounter, twice, _ = fight(2)
        self.assertEqual(twice["reward_scale"], 60)
        self.assertIsNone(twice["loot"])  # from the second ask on, no loot
        _many_encounter, many, many_state = fight(5)
        self.assertEqual(many["reward_scale"], 40)  # never below 40%
        self.assertNotIn("pyr_assists", many_state["encounter_state"] if many_state["encounter_state"].get("mob_name") != "The Ace Trickster" else {})
        self.assertEqual(self.service.encounter_projection(many_state)["pyr_assists"], 0)  # the next fight starts clean

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

    def test_only_the_current_campaigns_remain_and_played_retired_ones_are_kept(self):
        state_now = self.read()
        legacy = json.loads(state_module_base().read_text(encoding="utf-8"))

        def board(branch, cleared=0):
            return [{"name": mob["name"], "concept": mob["concept"], "encounter": mob["encounter"], "status": "defeated" if index < cleared else "locked"} for index, mob in enumerate(legacy[branch]["mobs"])]

        state_now["projects"] += [
            {"branch": "02-detective-game", "name": "Guess Who / Detective Game", "status": "available", "boss": "The False Alibi", "order": 2, "progress": 0, "mobs": board("02-detective-game")},
            {"branch": "03-pokemon-battle", "name": "Pokemon-Style Battle", "status": "available", "boss": "The Champion", "order": 3, "progress": 0, "mobs": board("03-pokemon-battle", cleared=1)},
            {"branch": "09-ai-agent", "name": "The Familiar", "status": "available", "boss": "The Rogue Familiar", "order": 9, "progress": 0, "mobs": []},
        ]
        self.path.write_text(json.dumps(state_now), encoding="utf-8")
        self.service.apply_internal("campaign_extend", {})
        projects = self.read()["projects"]
        # Untouched retired campaigns leave; anything played or finished stays.
        self.assertEqual([item["branch"] for item in projects], ["00-rps-tournament", "01-blackjack", "03-pokemon-battle", "00-lantern-vale", "04-casino-slots", "05-dungeon-crawler"])
        self.assertEqual([mob["status"] for mob in projects[2]["mobs"]][:2], ["defeated", "locked"])
        current = {item["branch"]: item for item in projects if item["branch"] not in state.RETIRED_CAMPAIGNS}
        self.assertEqual({branch: item["order"] for branch, item in current.items()}, {"00-lantern-vale": 0, "01-blackjack": 1, "04-casino-slots": 2, "05-dungeon-crawler": 3})
        self.assertTrue(set(current["05-dungeon-crawler"]) <= {"branch", "name", "status", "boss", "order", "progress", "mobs", "entry_file", "multi_file"})
        once = self.read()
        self.assertFalse(self.service.apply_internal("campaign_extend", {})["changed"])  # idempotent
        self.assertEqual(self.read()["projects"], once["projects"])
        selected = self.service.apply("select_campaign", {"branch": "05-dungeon-crawler"}, "player")["result"]["project"]
        self.assertEqual(selected["entry_file"], "deep_crawler/play.py")
        crawler = next(item for item in self.read()["projects"] if item["branch"] == "05-dungeon-crawler")
        self.assertEqual(len(crawler["mobs"]), 20)
        self.assertEqual(crawler["mobs"][0]["status"], "available")
        encounter = self.service.encounter_projection(self.read())
        self.assertEqual(encounter["mob_name"], "The Hollow Adventurer")
        self.assertEqual([item["id"] for item in encounter["available_objectives"]], ["make_folders", "make_package", "package_shape", "package_vs_module", "import_path"])
        # Blackjack keeps its board while another project is played.
        self.assertEqual(len(next(item for item in self.read()["projects"] if item["branch"] == "01-blackjack")["mobs"]), 19)

    def test_a_finished_board_that_synced_empty_shows_cleared(self):
        state_now = self.read()
        state_now["projects"].append({"branch": "05-dungeon-crawler", "name": "The Deep Crawler", "status": "completed", "completed": True, "boss": "Die Tozza van Zamalek", "order": 3, "progress": 100, "mobs": []})
        self.path.write_text(json.dumps(state_now), encoding="utf-8")
        self.service.apply_internal("campaign_extend", {})
        crawler = next(item for item in self.read()["projects"] if item["branch"] == "05-dungeon-crawler")
        self.assertEqual(len(crawler["mobs"]), 20)
        self.assertEqual({mob["status"] for mob in crawler["mobs"]}, {"defeated"})

    def test_an_untouched_project_opens_with_its_whole_story_board(self):
        state_now = self.read()
        state_now["projects"].append({"branch": "05-dungeon-crawler", "name": "The Deep Crawler", "status": "available", "boss": "Die Tozza van Zamalek", "order": 3, "progress": 0, "mobs": []})
        self.path.write_text(json.dumps(state_now), encoding="utf-8")
        self.service.apply("select_campaign", {"branch": "05-dungeon-crawler"}, "player")
        crawler = next(item for item in self.read()["projects"] if item["branch"] == "05-dungeon-crawler")
        self.assertEqual(len(crawler["mobs"]), 20)
        self.assertEqual(crawler["entry_file"], "deep_crawler/play.py")
        self.assertEqual([mob["status"] for mob in crawler["mobs"]][:2], ["available", "locked"])

    def test_the_synced_campaign_stays_small_and_a_pull_rebuilds_every_board(self):
        import copy
        from ide.server.state import MAX_SYNC_CAMPAIGN_BYTES, load_campaign_bounties

        self.service.apply_internal("campaign_extend", {})
        progress = self.read()
        content = load_campaign_bounties()
        for index, project in enumerate(progress["projects"]):
            # Worst realistic case: every campaign finished except one fully cleared board.
            authored = content.get(project["branch"], {}).get("mobs", [])  # a finished retired campaign has none
            project["mobs"] = [{"name": mob["name"], "concept": mob["concept"], "encounter": mob["encounter"], "status": "defeated", "resolve": 0, "max_resolve": 9, "impact_applied": 9, "objective_attempts": 4} for mob in authored]
            finished = index != 1
            project.update({"completed": finished, "status": "completed" if finished else "active", "progress": 100})
        projection = LocalStateService._sync_projection(progress)
        LocalStateService._validate_sync_projection(projection)
        size = len(json.dumps(projection["campaign"], separators=(",", ":")).encode())
        self.assertLess(size, MAX_SYNC_CAMPAIGN_BYTES)
        pulled = copy.deepcopy(progress)
        pulled["projects"] = copy.deepcopy(projection["campaign"]["projects"])
        self.service._extend_campaign(pulled)
        for before, after in zip(progress["projects"], pulled["projects"]):
            self.assertEqual([(mob["name"], mob["status"], mob["concept"]) for mob in after["mobs"]], [(mob["name"], mob["status"], mob["concept"]) for mob in before["mobs"]], before["branch"])

    def test_an_in_progress_board_round_trips_through_sync(self):
        import copy

        self.service.apply_internal("campaign_extend", {})
        progress = self.read()
        projection = LocalStateService._sync_projection(progress)
        blackjack = next(item for item in projection["campaign"]["projects"] if item["branch"] == "01-blackjack")
        self.assertEqual(len(blackjack["mobs"]), 9)  # eight cleared + the open contract; locked ones are restored
        self.assertNotIn("encounter", blackjack["mobs"][0])
        pulled = copy.deepcopy(progress)
        pulled["projects"] = copy.deepcopy(projection["campaign"]["projects"])
        self.service._extend_campaign(pulled)
        original = next(item for item in progress["projects"] if item["branch"] == "01-blackjack")
        restored = next(item for item in pulled["projects"] if item["branch"] == "01-blackjack")
        self.assertEqual([(mob["name"], mob["status"]) for mob in restored["mobs"]], [(mob["name"], mob["status"]) for mob in original["mobs"]])


if __name__ == "__main__":
    unittest.main()
