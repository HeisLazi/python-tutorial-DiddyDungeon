from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from ide.server.state import (
    ARMORY_EFFECT_CAPS,
    ARMORY_FLAG_EFFECTS,
    ARMORY_GEAR_SLOTS,
    ARMORY_ON_TYPES,
    ARMORY_SLOTS,
    ARMORY_TIERS,
    DUNGEON_MARKET_CATALOG,
    DUNGEON_TRINKETS,
    EQUIPMENT_CATALOG,
    LocalStateService,
    StateCommandError,
    armory_catalog,
)
from ide.server.test_campaign_content import story_files, use_real_content, user_like_progress

ALLOWED_EFFECTS = set(ARMORY_EFFECT_CAPS) | set(ARMORY_FLAG_EFFECTS) | {"on", "next_battle"}


class ArmoryContentTests(unittest.TestCase):
    def test_every_campaign_has_a_full_armory_with_safe_effects(self):
        ids, names = set(), {item["name"] for item in EQUIPMENT_CATALOG}
        names |= {item["name"] for item in DUNGEON_MARKET_CATALOG} | {item["name"] for item in DUNGEON_TRINKETS}
        legacy_names = set(names)
        for entry in story_files():
            armory = entry["armory"]
            with self.subTest(branch=entry["branch"]):
                for slot in ARMORY_GEAR_SLOTS:
                    gear = [item for item in armory if item["slot"] == slot]
                    self.assertGreaterEqual(len(gear), 5, slot)
                    self.assertEqual({item["tier"] for item in gear}, set(ARMORY_TIERS), slot)
                self.assertTrue(any(item["slot"] == "food" for item in armory))
                self.assertEqual(sum(1 for item in armory if item["slot"] == "relic"), 1)
                for item in armory:
                    self.assertIn(item["slot"], ARMORY_SLOTS)
                    self.assertIn(item["tier"], ARMORY_TIERS)
                    self.assertNotIn(item["id"], ids, "item ids are unique")
                    self.assertNotIn(item["name"], names, "item names are unique (equipping is by name)")
                    self.assertLessEqual(len(item["name"]), 120)
                    ids.add(item["id"])
                    names.add(item["name"])
                    effect = item["effect"]
                    self.assertTrue(set(effect) <= ALLOWED_EFFECTS, (item["name"], set(effect) - ALLOWED_EFFECTS))
                    for key, value in effect.items():
                        if key in ARMORY_EFFECT_CAPS:
                            self.assertTrue(0 < value <= ARMORY_EFFECT_CAPS[key], (item["name"], key))
                    if "on" in effect:
                        self.assertIn(effect["on"], ARMORY_ON_TYPES)
                    if item["slot"] in {"food", "tonic"}:
                        self.assertTrue(effect.get("heal") or effect.get("next_battle"), item["name"])
        self.assertGreaterEqual(len(ids), 20 * len(story_files()))
        self.assertTrue(legacy_names.isdisjoint(names - legacy_names))


class ArmoryBehaviourTests(unittest.TestCase):
    def setUp(self):
        use_real_content()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "progress.json"
        self.path.write_text(json.dumps(user_like_progress()), encoding="utf-8")
        self.service = LocalStateService(self.path, threading.RLock())
        self.service.apply_internal("campaign_extend", {})

    def read(self) -> dict:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def give(self, *item_ids, coins=None):
        state = self.read()
        state.setdefault("hunter", {"signs": {}, "stats_xp": {}, "spent": {}})
        armory = state["hunter"].setdefault("armory", {"owned": [], "stack": {}, "buffs": {}})
        for item_id in item_ids:
            item = armory_catalog()[item_id]
            if item["slot"] in {"food", "tonic", "aid"}:
                armory.setdefault("stack", {})[item_id] = armory.get("stack", {}).get(item_id, 0) + 1
            else:
                armory.setdefault("owned", []).append(item_id)
        if coins is not None:
            state["player"]["coins"] = coins
        self.path.write_text(json.dumps(state), encoding="utf-8")

    def objective(self, objective_id):
        return self.service.apply_internal("record_battle_objective", {"objective_id": objective_id, "evidence_id": f"ev-{objective_id}", "reason": "Verified"})["result"]

    def miss(self, objective_id):
        return self.service.apply_internal("record_battle_miss", {"objective_id": objective_id, "encounter_id": "enc", "evidence_id": f"miss-{objective_id}", "reason": "Wrong"})["result"]

    def test_a_weapon_breaks_the_guard_but_the_fight_still_takes_every_objective(self):
        self.give("bj-the-house-cutter")  # legendary: +3 impact on every objective, +6 break coins
        self.service.apply("armory_equip", {"item_id": "bj-the-house-cutter"}, "player")
        coins = self.read()["player"]["coins"]
        one = self.objective("ace_rule")  # 3 + 3 = 6 of 8
        self.assertFalse(one["mob_defeated"])
        two = self.objective("multi_ace_trace")  # 2 + 3 = 5 > 2 left: a Guard Break
        self.assertFalse(two["mob_defeated"])
        self.assertEqual(two["guard_break"], {"coins": 3 + 6, "guards": 1})
        self.assertEqual(two["resolve_after"], 3)  # what the last objective removes
        guarded = self.miss("ace_bug")
        self.assertTrue(guarded["guard_used"])
        self.assertEqual(guarded["damage"], 0)
        three = self.objective("ace_bug")
        self.assertTrue(three["mob_defeated"])
        self.assertGreaterEqual(self.read()["player"]["coins"], coins + 9)

    def test_armour_trinkets_food_and_relics_apply_in_battle(self):
        self.give("bj-the-high-roller-s-mail", "bj-counting-abacus", "bj-midnight-club-sandwich", "bj-the-house-s-broken-shoe")
        self.service.apply("armory_equip", {"item_id": "bj-the-high-roller-s-mail"}, "player")  # 45% less damage, first miss free
        self.service.apply("armory_equip", {"item_id": "bj-counting-abacus"}, "player")  # rare: start with a free mistake
        self.service.apply("armory_use", {"item_id": "bj-midnight-club-sandwich"}, "player")  # next battle: a free mistake
        self.assertEqual(self.read()["hunter"]["armory"]["buffs"], {"guards": 1})
        first = self.miss("ace_rule")
        state = self.read()
        self.assertEqual(state["hunter"]["armory"]["buffs"], {})  # the buff was taken by this battle
        self.assertTrue(first["guard_used"])
        self.assertEqual(first["guards"], 1)  # trinket 1 + food 1, one spent
        self.miss("ace_rule")  # second guard
        third = self.miss("ace_rule")  # the armour's free first miss
        self.assertEqual(third["damage"], 0)
        fourth = self.miss("ace_rule")
        self.assertEqual(fourth["damage"], (28 * 55 + 99) // 100)  # mob 9 uses the last damage bucket, 28
        summary = self.service.armory_projection(self.read())["summary"]
        self.assertEqual((summary["reduction"], summary["start_guards"], summary["coin_bonus"]), (45, 1, 5))

    def test_cleared_contracts_drop_campaign_loot_into_the_armory(self):
        for objective in ("ace_rule", "multi_ace_trace", "ace_bug"):
            result = self.objective(objective)
        loot = result["loot"]
        self.assertIsNotNone(loot)
        self.assertTrue(loot["id"].startswith("bj-"))
        armory = self.read()["hunter"]["armory"]
        self.assertTrue(loot["id"] in armory["owned"] or armory["stack"].get(loot["id"]))

    def test_aid_buys_a_free_pyr_ask_and_a_ward_for_a_wrong_answer(self):
        self.give("aid-pyrs-favour", "aid-ward-shield")
        armed = self.service.apply("armory_use", {"item_id": "aid-pyrs-favour"}, "player")["result"]
        self.assertEqual(armed["armed"], {"free_asks": 1})
        self.service.apply("armory_use", {"item_id": "aid-ward-shield"}, "player")
        self.assertEqual(self.service.armory_projection(self.read())["charges"], {"free_asks": 1, "wards": 1})
        self.assertNotIn("aid-pyrs-favour", self.read()["hunter"]["armory"]["stack"])  # spent by arming it
        free = self.service.apply_internal("record_pyr_assist", {})["result"]
        self.assertTrue(free["free"])
        self.assertEqual((free["pyr_assists"], free["reward_scale"]), (0, 100))  # the fight still pays in full
        paid = self.service.apply_internal("record_pyr_assist", {})["result"]
        self.assertEqual((paid["free"], paid["pyr_assists"], paid["reward_scale"]), (False, 1, 80))
        hp = self.read()["player"]["hp"]
        warded = self.miss("ace_rule")
        self.assertTrue(warded["ward_used"])
        self.assertEqual((warded["damage"], warded["wards_left"]), (0, 0))
        self.assertEqual(self.read()["player"]["hp"], hp)
        hit = self.miss("ace_rule")
        self.assertFalse(hit["ward_used"])
        self.assertGreater(hit["damage"], 0)  # one ward, one wrong answer

    def test_aid_is_always_on_sale_and_cannot_be_armed_past_its_cap(self):
        market = self.service.armory_projection(self.read())["market"]
        aid = {lot["id"]: lot for lot in market if lot["campaign"] == "aid"}
        self.assertEqual(set(aid), {"aid-pyrs-favour", "aid-ward-shield", "aid-pyrs-blessing", "aid-aegis-of-patience"})
        self.assertTrue(all(lot["locked"] is None for lot in aid.values()))
        self.give(coins=500)
        self.service.apply("armory_buy", {"item_id": "aid-aegis-of-patience"}, "player")
        self.service.apply("armory_use", {"item_id": "aid-aegis-of-patience"}, "player")
        self.give("aid-aegis-of-patience")
        self.assertEqual(self.service.apply("armory_use", {"item_id": "aid-aegis-of-patience"}, "player")["result"]["armed"], {"wards": 1})  # capped at 3
        self.give("aid-ward-shield")
        with self.assertRaises(StateCommandError):
            self.service.apply("armory_use", {"item_id": "aid-ward-shield"}, "player")
        self.assertEqual(self.read()["hunter"]["armory"]["stack"].get("aid-ward-shield"), 1)  # a refused use keeps the item

    def test_the_merchant_gates_lots_by_campaign_progress(self):
        state = self.read()
        next(item for item in state["projects"] if item["branch"] == "05-dungeon-crawler").update(status="completed", completed=True)
        self.path.write_text(json.dumps(state), encoding="utf-8")
        market = self.service.armory_projection(self.read())["market"]
        crawler = [lot for lot in market if lot["campaign"] == "05-dungeon-crawler"]
        self.assertTrue(crawler and all(lot["locked"] is None for lot in crawler))  # a finished campaign sells everything up to rare
        casino = [lot for lot in market if lot["campaign"] == "04-casino-slots"]
        self.assertTrue(casino and all(lot["locked"] == "Start this campaign" for lot in casino))
        blackjack_rare = next(lot for lot in market if lot["campaign"] == "01-blackjack" and lot["tier"] == "rare" and lot["slot"] == "weapon")
        self.assertEqual(blackjack_rare["locked"], "Clear half of its contracts")  # 8 of 19 is under half
        self.give(coins=500)
        bought = self.service.apply("armory_buy", {"item_id": "bj-card-edge-dagger"}, "player")["result"]
        self.assertEqual(bought["coins"], 460)
        self.assertIn("bj-card-edge-dagger", self.read()["hunter"]["armory"]["owned"])
        with self.assertRaises(Exception):
            self.service.apply("armory_buy", {"item_id": "cas-coin-roll-club"}, "player")

    def test_armory_ownership_never_reaches_the_cloud(self):
        self.give("bj-the-house-cutter", "bj-the-high-roller-s-mail", "bj-counting-abacus", "bj-free-bar-peanuts", "bj-the-house-s-broken-shoe")
        for item in ("bj-the-house-cutter", "bj-the-high-roller-s-mail", "bj-counting-abacus"):
            self.service.apply("armory_equip", {"item_id": item}, "player")
        state = self.read()
        projection = LocalStateService._sync_projection(state)
        LocalStateService._validate_sync_projection(projection)
        text = json.dumps(projection)
        for item_id in armory_catalog():
            self.assertNotIn(f'"{item_id}"', text)
        self.assertEqual(projection["equipment"]["armor"], "The High Roller's Mail")

    def test_dungeon_floor_bosses_drop_gear_that_banks_into_the_armory(self):
        state = self.read()
        run = {"seed": "gear", "question_number": 3, "floor": 1, "pack": {}}
        gear = self.service._dungeon_gear_drop(run, "boss", state)
        self.assertIsNotNone(gear)
        item = armory_catalog()[gear]
        self.assertIn(item["slot"], ARMORY_GEAR_SLOTS)
        self.assertIn(item["tier"], {"rare", "epic"})
        run["pack"] = {gear: 1, "wraith-ash": 2}
        self.service._dungeon_bank_pack(run, state)
        self.assertIn(gear, state["hunter"]["armory"]["owned"])
        self.assertEqual(state["hunter"]["materials"].get("wraith-ash"), 2)


if __name__ == "__main__":
    unittest.main()


class DungeonFoeNameTests(unittest.TestCase):
    def test_multi_question_fight_keeps_its_first_foe_name(self):
        run = {
            "room_type": "boss",
            "floor": 1,
            "question": {"id": "q1", "question_type": "code_checkpoint", "difficulty": 4, "concept_id": "functions"},
            "fight": {"room_type": "boss", "questions_total": 5, "questions_cleared": 0, "resolve": 12, "max_resolve": 12, "guards": 0, "breaks": 0, "misses": 0, "mechanic": None},
        }
        first = LocalStateService._dungeon_pin_foe(run, LocalStateService._dungeon_mob_spec(run))
        run["question"] = {"id": "q2", "question_type": "bug_hunt", "difficulty": 4, "concept_id": "functions"}
        second = LocalStateService._dungeon_mob_spec(run)
        self.assertEqual(first["name"], second["name"])
        self.assertEqual(run["fight"]["foe"]["name"], first["name"])


class LegacyGearTests(unittest.TestCase):
    def test_merchant_trinkets_and_armours_have_real_effects(self):
        for trinket, key in (("Syntax Ward", "block_first_miss"), ("Loop Lens", "heal_on_objective"), ("Guard Bell", "start_guards"), ("Scimitar of Momentum", "coin_bonus"), ("Vision Scroll", "loot_luck")):
            effects = LocalStateService._gear_effects({"equipment": {"trinket": trinket}})
            self.assertTrue(effects[key], trinket)
        for armour, reduction in (("Debugger Plate", 15), ("Ledgerguard Coat", 25), ("Emberweave Mantle", 30)):
            effects = LocalStateService._gear_effects({"equipment": {"armor": armour}})
            self.assertEqual(effects["reduction"], reduction, armour)


class BossGateTests(unittest.TestCase):
    def test_an_older_save_resumes_at_the_new_coding_twist(self):
        project = {"branch": "01-blackjack", "name": "Blackjack", "boss": "The House", "boss_status": "available",
                   "boss_twist": "Turn your rules into data: a HouseRules dict.",
                   "boss_validation": {"verified": ["required_behavior", "explanation"], "history": []}}
        projection = LocalStateService._boss_validation_projection(project)
        self.assertEqual(projection["boss_phase"], "edge_cases")
        goal = projection["boss_current_requirement"]
        self.assertEqual(goal["question_type"], "code_checkpoint")
        self.assertIn("HouseRules", goal["quest"])

    def test_a_defeated_boss_stays_complete_and_phases_alternate_code_and_clicks(self):
        defeated = LocalStateService._boss_validation_projection({"boss_status": "defeated", "completed": True, "boss_validation": {"verified": ["required_behavior", "explanation", "interview"]}})
        self.assertEqual(defeated["boss_phase"], "complete")
        fresh = LocalStateService._boss_validation_projection({"branch": "09-ai-agent", "boss_status": "available", "boss_brief": "Bring a finished agent.py."})
        kinds = [item["question_type"] for item in fresh["boss_requirements_projection"]]
        self.assertEqual(kinds, ["code_checkpoint", "snippet_check", "code_checkpoint", "code_interview"])
        self.assertIn("agent.py", fresh["boss_requirements_projection"][0]["quest"])

    def test_every_shipped_boss_has_a_long_practical_twist(self):
        import json
        from pathlib import Path

        for path in sorted((Path(__file__).with_name("campaigns")).glob("*.json")):
            twist = json.loads(path.read_text(encoding="utf-8")).get("boss_twist", "")
            self.assertGreater(len(twist), 250, path.name)
            self.assertRegex(twist, r"[a-z_]+\(", path.name)

    def test_each_boss_runs_its_own_gauntlet(self):
        gauntlet = ["required_behavior", "edge_cases", "twist_2", "twist_3", "twist_4", "interview"]
        project = {"branch": "09-ai-agent", "boss": "The Rogue Familiar", "boss_status": "available", "boss_gauntlet": gauntlet,
                   "boss_phases": {"twist_2": {"label": "Phase 2: The Familiar forgets", "quest": "Cap memory and summarise the oldest entries."}},
                   "boss_validation": {"verified": ["required_behavior", "edge_cases"], "history": []}}
        projection = LocalStateService._boss_validation_projection(project)
        self.assertEqual([item["id"] for item in projection["boss_requirements_projection"]], gauntlet)
        self.assertEqual(projection["boss_phase"], "twist_2")
        self.assertEqual(projection["boss_current_requirement"]["label"], "Phase 2: The Familiar forgets")
        self.assertEqual(projection["boss_max_resolve"], 5 * 5 + 3)
        light = LocalStateService._boss_validation_projection({"boss_status": "available", "boss_gauntlet": ["required_behavior", "explanation", "interview"]})
        self.assertEqual(light["boss_max_resolve"], 5 + 2 + 3)
        broken = LocalStateService._boss_validation_projection({"boss_status": "available", "boss_gauntlet": ["interview", "nonsense"]})
        self.assertEqual(broken["remaining_boss_requirements"], ["required_behavior", "explanation", "edge_cases", "interview"])

    def test_a_phase_outside_this_gauntlet_is_refused_and_the_clear_records_this_gauntlet(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "progress.json"
            state = user_like_progress()
            for item in state["projects"]:
                item["status"] = "available"
            project = {"branch": "99-test-gauntlet", "name": "Test gauntlet", "status": "active", "boss": "The Pattern Warden", "boss_status": "available",
                       "progress": 100, "order": 0, "boss_gauntlet": ["required_behavior", "explanation", "interview"],
                       "mobs": [{"name": "The Mimic", "status": "defeated", "concept": "Input"}]}
            state["projects"] = [project] + [item for item in state["projects"] if item.get("branch") != "00-rps-tournament"]
            path.write_text(json.dumps(state), encoding="utf-8")
            service = LocalStateService(path, threading.RLock())
            with self.assertRaises(StateCommandError) as refused:
                service.apply_internal("record_boss_requirement", {"requirement_id": "edge_cases", "evidence_id": "x-1", "reason": "Not in this fight"})
            self.assertEqual(refused.exception.status_code, 409)
            for phase in ("required_behavior", "explanation", "interview"):
                service.apply_internal("record_boss_requirement", {"requirement_id": phase, "evidence_id": f"ev-{phase}", "reason": "Verified"})
            cleared = service.apply_internal("record_boss_clear", {"evidence_id": "ev-required_behavior", "explanation_evidence_id": "ev-explanation", "interview_evidence_id": "ev-interview", "reason": "Gauntlet done"})
            self.assertEqual(cleared["result"]["verified_boss_requirements"], ["required_behavior", "explanation", "interview"])
