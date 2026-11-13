"""Every weapon has its own signature, a combat style, and the campaign loop honours the triggers."""
import json
import tempfile
import threading
import unittest
from pathlib import Path

from ide.server.state import ARMORY_COMBAT_STYLES, ARMORY_EFFECT_CAPS, LocalStateService, armory_catalog, armory_effect_text
from ide.server.test_campaign_content import use_real_content, user_like_progress
from ide.server.weapon_signatures import IMPACT_KEYS, SIGNATURE_TEXT, WEAPON_SIGNATURES, signature_bonus

QUIET = dict(first=False, clean=False, streak=0, low_hp=False, heavy=False, last_type=None, this_type="prediction", enemy_low=False, verified=0)


def bonus(effect, **kwargs):
    return signature_bonus(effect, **{**QUIET, **kwargs})


class WeaponCatalogTests(unittest.TestCase):
    def setUp(self):
        use_real_content()
        self.weapons = {item_id: item for item_id, item in armory_catalog().items() if item["slot"] == "weapon"}

    def test_every_weapon_has_a_signature_and_a_combat_style(self):
        self.assertEqual(set(self.weapons), set(WEAPON_SIGNATURES))
        for item_id, item in self.weapons.items():
            with self.subTest(item=item_id):
                self.assertIn(item["combat_style"], ARMORY_COMBAT_STYLES)
                self.assertTrue(item.get("shape"))
                self.assertTrue(set(item["effect"]) & set(SIGNATURE_TEXT), "a weapon needs at least one signature trigger")

    def test_no_two_weapons_share_the_same_effect(self):
        seen = {}
        for item_id, item in self.weapons.items():
            key = json.dumps(item["effect"], sort_keys=True)
            self.assertNotIn(key, seen, f"{item_id} duplicates {seen.get(key)}")
            seen[key] = item_id

    def test_signature_values_stay_inside_their_caps_and_read_in_plain_words(self):
        for item_id, item in self.weapons.items():
            for key, value in item["effect"].items():
                if key in SIGNATURE_TEXT:
                    self.assertTrue(0 < value <= ARMORY_EFFECT_CAPS[key], (item_id, key))
            text = armory_effect_text(item["effect"])
            for key in item["effect"]:
                if key in SIGNATURE_TEXT:
                    self.assertIn(SIGNATURE_TEXT[key].format(n=item["effect"][key]).split(" ", 1)[1][:12], text)

    def test_each_combat_style_has_more_than_one_kind_of_weapon(self):
        for style in ("sword", "greatsword", "staff", "scythe", "whip", "handmagic"):
            kinds = {frozenset(set(item["effect"]) & set(SIGNATURE_TEXT)) for item in self.weapons.values() if item["combat_style"] == style}
            self.assertGreaterEqual(len(kinds), 2, style)


class SignatureTriggerTests(unittest.TestCase):
    def test_combo_needs_a_third_clean_objective_in_a_row(self):
        self.assertEqual(bonus({"chip_streak": 2}, clean=True, streak=2), (0, []))
        self.assertEqual(bonus({"chip_streak": 2}, clean=True, streak=3), (2, ["Combo +2"]))
        self.assertEqual(bonus({"chip_streak": 2}, clean=False, streak=0), (0, []))

    def test_variety_and_chain_are_opposites(self):
        self.assertEqual(bonus({"chip_switch": 1, "chip_chain": 1}, last_type="explanation", this_type="prediction")[0], 1)
        self.assertEqual(bonus({"chip_switch": 1, "chip_chain": 1}, last_type="prediction", this_type="prediction")[0], 1)
        self.assertEqual(bonus({"chip_switch": 1}, last_type=None)[0], 0)  # nothing to switch from on the opening objective

    def test_heavy_finish_ramp_low_and_follow(self):
        self.assertEqual(bonus({"chip_heavy": 2}, heavy=True)[0], 2)
        self.assertEqual(bonus({"chip_heavy": 2}, heavy=False)[0], 0)
        self.assertEqual(bonus({"chip_finish": 1}, enemy_low=True)[0], 1)
        self.assertEqual(bonus({"chip_ramp": 1}, verified=5)[0], 2)
        self.assertEqual(bonus({"chip_ramp": 3}, verified=9)[0], 3)  # capped at +3
        self.assertEqual(bonus({"chip_low": 2}, low_hp=True)[0], 2)
        self.assertEqual(bonus({"chip_follow": 1}, clean=True, first=True)[0], 0)
        self.assertEqual(bonus({"chip_follow": 1}, clean=True, first=False)[0], 1)

    def test_a_weapon_with_no_signature_adds_nothing(self):
        self.assertEqual(bonus({"impact": 2, "on": "any"}, clean=True, streak=5, heavy=True, enemy_low=True), (0, []))
        self.assertEqual(bonus(None), (0, []))

    def test_every_impact_key_can_fire(self):
        for key in IMPACT_KEYS:
            fired = [bonus({key: 1}, first=False, clean=True, streak=3, low_hp=True, heavy=True, last_type=last, this_type="prediction", enemy_low=True, verified=4)[0] for last in ("prediction", "explanation")]
            self.assertTrue(any(fired), key)


class CampaignSignatureTests(unittest.TestCase):
    def setUp(self):
        use_real_content()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "progress.json"
        self.path.write_text(json.dumps(user_like_progress()), encoding="utf-8")
        self.service = LocalStateService(self.path, threading.RLock())
        self.service.apply_internal("campaign_extend", {})

    def equip(self, item_id):
        state = json.loads(self.path.read_text())
        state.setdefault("hunter", {"signs": {}, "stats_xp": {}, "spent": {}}).setdefault("armory", {"owned": [], "stack": {}, "buffs": {}})["owned"].append(item_id)
        self.path.write_text(json.dumps(state), encoding="utf-8")
        self.service.apply("armory_equip", {"item_id": item_id}, "player")

    def objective(self, objective_id):
        return self.service.apply_internal("record_battle_objective", {"objective_id": objective_id, "evidence_id": f"ev-{objective_id}", "reason": "Verified"})["result"]

    def test_a_clean_mend_heals_and_a_payout_pays(self):
        self.equip("cas-lady-luck-s-sceptre")  # +2 coins and +1 HP on every clean objective
        state = json.loads(self.path.read_text())
        state["player"]["hp"] = max(1, state["player"]["max_hp"] - 20)
        coins = state["player"]["coins"]
        self.path.write_text(json.dumps(state), encoding="utf-8")
        result = self.objective("ace_rule")
        self.assertIn("Pay-out +2 coins", result["weapon_triggers"])
        self.assertGreaterEqual(json.loads(self.path.read_text())["player"]["coins"], coins + 2)
        self.assertTrue(any(trigger.startswith("Mend") for trigger in result["weapon_triggers"]))
        self.assertEqual(result["healed"], 1)

    def test_a_heavy_blow_only_lands_on_big_objectives(self):
        self.equip("dc-deepvein-warhammer")  # +2 on objectives worth 4 or more (base 3 here, so no blow)
        result = self.objective("ace_rule")
        self.assertFalse(any(trigger.startswith("Heavy") for trigger in result["weapon_triggers"]))
        self.assertEqual(result["resolve_before"] - result["resolve_after"], result["impact"])

    def test_the_guard_ring_gives_an_extra_free_mistake_on_a_break(self):
        self.equip("lv-05")  # Dawnbringer: break_guard
        result = self.objective("ace_bug")
        if result["guard_break"]:
            self.assertEqual(result["guards"], 2)
