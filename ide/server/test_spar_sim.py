from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from ide.server import spar_sim
from ide.server.state import LEGACY_ARMOR_REDUCTION, LocalStateService, StateCommandError, armory_catalog
from ide.server.test_campaign_content import use_real_content, user_like_progress

NO_GEAR = {"weapon": None, "reduction": 0, "set_bonus": {}}


def rounds(*marks):
    kinds = ("choice", "code", "text", "choice", "code")
    return [{"correct": mark, "kind": kinds[index]} for index, mark in enumerate(marks)]


class SparRulesTests(unittest.TestCase):
    def test_bare_hands_five_right_answers_finish_the_foe_and_five_misses_finish_the_hunter(self):
        won = spar_sim.simulate(NO_GEAR, rounds(*[True] * 5))
        self.assertEqual([item["resolve"] for item in won["rounds"]], [10, 8, 6, 4, 0])
        self.assertEqual(won["rounds"][-1]["hp"], spar_sim.SPAR_HP)
        lost = spar_sim.simulate(NO_GEAR, rounds(*[False] * 5))
        self.assertEqual([item["hp"] for item in lost["rounds"]], [16, 12, 8, 4, 0])
        self.assertEqual(lost["rounds"][-1]["resolve"], spar_sim.SPAR_RESOLVE)

    def test_start_state_and_empty_replay(self):
        empty = spar_sim.simulate({**NO_GEAR, "start_guards": 1}, [])
        self.assertEqual(empty["rounds"], [])
        self.assertEqual(empty["start"], {"hp": 20, "resolve": 12, "guards": 1})

    def test_armour_reduction_shrinks_each_wrong_answer_but_never_to_nothing(self):
        for reduction, expected in ((25, 3), (50, 2), (80, 1)):
            result = spar_sim.simulate({**NO_GEAR, "reduction": reduction}, rounds(False))
            self.assertEqual(result["rounds"][0]["damage"], expected, reduction)
            self.assertEqual(result["rounds"][0]["hp"], 20 - expected)

    def test_a_free_first_mistake_is_used_once_and_guards_go_first(self):
        result = spar_sim.simulate({**NO_GEAR, "first_miss_free": True, "first_miss_source": "Pilgrim Ward"}, rounds(False, False))
        self.assertEqual([item["damage"] for item in result["rounds"]], [0, 4])
        self.assertIn("Pilgrim Ward", result["rounds"][0]["fired"][0])
        guarded = spar_sim.simulate({**NO_GEAR, "start_guards": 1, "first_miss_free": True}, rounds(False, False, False))
        self.assertEqual([item["damage"] for item in guarded["rounds"]], [0, 0, 4])  # the guard, then the free mistake, then a real hit

    def test_revive_saves_the_hunter_once(self):
        result = spar_sim.simulate({**NO_GEAR, "revive": True}, rounds(*[False] * 5))
        self.assertEqual([item["hp"] for item in result["rounds"]], [16, 12, 8, 4, 1])  # 0 on the last hit becomes 1
        again = spar_sim.simulate({**NO_GEAR, "revive": True}, rounds(*([False] * 5)))
        self.assertEqual(again["rounds"][-1]["fired"][-1], "Revive")

    def test_heavy_impact_breaks_the_guard_instead_of_ending_the_fight_early(self):
        strong = {**NO_GEAR, "weapon": {"impact": 3, "on": "any", "break_guard": 1}}
        result = spar_sim.simulate(strong, rounds(True, True, True))
        # 12 Resolve, 5 per answer: it would reach 0 on the third hit, but two questions remain.
        self.assertTrue(result["rounds"][2]["guard_broken"])
        self.assertGreater(result["rounds"][2]["resolve"], 0)
        self.assertEqual(result["rounds"][2]["guards"], 2)  # one for the break plus the weapon's extra
        self.assertIn("Guard break", result["rounds"][2]["fired"])

    def test_healing_is_capped_at_full_health(self):
        healer = {**NO_GEAR, "heal_on_objective": 5}
        result = spar_sim.simulate(healer, rounds(False, True, True))
        self.assertEqual([item["hp"] for item in result["rounds"]], [16, 20, 20])
        self.assertEqual([item["healed"] for item in result["rounds"]], [0, 4, 0])

    def test_trinket_impact_only_applies_to_its_question_type(self):
        trinket = {**NO_GEAR, "trinket_impact": 2, "trinket_on": "code_checkpoint"}
        result = spar_sim.simulate(trinket, rounds(True, True))  # a choice answer, then a code answer
        self.assertEqual([item["impact"] for item in result["rounds"]], [2, 4])

    def test_effect_lines_split_what_applies_from_what_needs_rewards(self):
        lines = spar_sim.effect_lines({"reduction": 25, "coin_bonus": 20, "xp_bonus": 0, "weapon": {"impact": 1, "on": "any", "break_coins": 3, "chip_heavy": 2, "coin_clean": 1}})
        self.assertIn("25% less damage from wrong answers", lines["applied"])
        self.assertTrue(any("worth 4 or more" in text for text in lines["applied"]))
        self.assertEqual(sorted(lines["ignored"]), ["+1 coins on a clean objective", "+20% coins", "+3 coins on a Guard Break"])


class SparLoadoutTests(unittest.TestCase):
    def setUp(self):
        use_real_content()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "progress.json"
        self.path.write_text(json.dumps(user_like_progress()), encoding="utf-8")
        self.service = LocalStateService(self.path, threading.RLock())

    def test_a_real_weapon_uses_its_campaign_effects_without_being_owned(self):
        before = self.path.read_text(encoding="utf-8")
        effects = LocalStateService.spar_loadout_effects("cas-jackpot-hammer", None, None)
        self.assertEqual(effects["weapon"]["chip_heavy"], 2)
        result = self.service.spar_simulate("cas-jackpot-hammer", None, None, rounds(True, True, True, True, True))
        self.assertIn("Heavy blow +2", result["rounds"][-1]["fired"])  # only the 4-point final question is heavy
        self.assertIn("Weapon +2", result["rounds"][0]["fired"])  # its flat impact shows on every right answer
        self.assertTrue(all("Heavy blow" not in label for item in result["rounds"][:-1] for label in item["fired"]))
        self.assertEqual(self.path.read_text(encoding="utf-8"), before)  # a simulation never writes the save

    def test_armour_and_trinket_names_resolve_and_bare_hands_are_allowed(self):
        armour = next(item for item in armory_catalog().values() if item["slot"] == "armor" and item["effect"].get("reduction"))
        effects = LocalStateService.spar_loadout_effects(None, armour["name"], None)
        self.assertIsNone(effects["weapon"])
        self.assertEqual(effects["reduction"], min(80, armour["effect"]["reduction"]))
        trinket = next(item for item in armory_catalog().values() if item["slot"] == "trinket" and item["effect"].get("start_guards"))
        self.assertGreaterEqual(LocalStateService.spar_loadout_effects(None, None, trinket["name"])["start_guards"], 1)
        # The starting coat is not in the armory but still turns a little damage aside, as it does in a hunt.
        self.assertEqual(LocalStateService.spar_loadout_effects(None, "Apprentice Coat", "None")["reduction"], LEGACY_ARMOR_REDUCTION["Apprentice Coat"])
        self.assertEqual(LocalStateService.spar_loadout_effects(None, None, None)["reduction"], 0)

    def test_a_full_set_adds_its_bonus_in_the_ring(self):
        group = next(item for item in __import__("ide.server.state", fromlist=["HUNTER_SETS"]).HUNTER_SETS)
        catalog = armory_catalog()
        pieces = {catalog[piece]["slot"]: catalog[piece] for piece in group["pieces"]}
        effects = LocalStateService.spar_loadout_effects(pieces["weapon"]["id"], pieces["armor"]["name"], pieces["trinket"]["name"])
        self.assertEqual(effects["set_bonus"], group["bonus"])

    def test_wrong_kinds_of_item_are_refused(self):
        armour = next(item for item in armory_catalog().values() if item["slot"] == "armor")
        weapon = next(item for item in armory_catalog().values() if item["slot"] == "weapon")
        with self.assertRaises(StateCommandError):
            LocalStateService.spar_loadout_effects(armour["id"], None, None)  # an armour id is not a weapon
        with self.assertRaises(StateCommandError):
            LocalStateService.spar_loadout_effects("no-such-weapon", None, None)
        with self.assertRaises(StateCommandError):
            LocalStateService.spar_loadout_effects(None, weapon["name"], None)  # a weapon name is not armour

    def test_spar_looks_list_every_mastery_look_with_armour_first_and_nothing_owned_yet(self):
        looks = self.service.spar_looks(self.path and json.loads(self.path.read_text(encoding="utf-8")))
        self.assertEqual(len(looks), 24)
        self.assertEqual({item["appearance_type"] for item in looks}, {"armor", "weapon"})
        kinds = [item["appearance_type"] for item in looks]
        self.assertEqual(kinds, sorted(kinds, key=lambda kind: kind != "armor"))
        self.assertEqual({item["tier"] for item in looks}, {"rare", "legendary", "ethereal"})
        self.assertFalse(any(item["owned"] for item in looks))
        self.assertTrue(all(item["style"] for item in looks if item["appearance_type"] == "weapon"))


if __name__ == "__main__":
    unittest.main()
