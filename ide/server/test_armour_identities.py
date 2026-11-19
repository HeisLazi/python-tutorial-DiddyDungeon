"""Every armour has an identity of its own: a distinct effect, not just a different damage-reduction number."""
from __future__ import annotations

import json
import unittest

from ide.server import spar_sim
from ide.server.state import ARMORY_EFFECT_CAPS, LocalStateService, armory_catalog, armory_effect_text
from ide.server.test_campaign_content import use_real_content

# What an armour may do. Damage reduction and the first free mistake are the old pair; the rest are the roles
# armour gained when each piece was made unique.
ARMOUR_EFFECTS = {"reduction", "first_miss_free", "start_guards", "heal_on_objective", "impact", "on", "coin_bonus", "xp_bonus", "loot_luck", "revive"}


def armours():
    return [item for item in armory_catalog().values() if item["slot"] == "armor"]


def effects_for(armour):
    return LocalStateService.spar_loadout_effects(None, armour["name"], None)


class ArmourIdentityTests(unittest.TestCase):
    def setUp(self):
        use_real_content()

    def test_no_two_armours_share_an_effect(self):
        seen = {}
        for item in armours():
            key = json.dumps(item["effect"], sort_keys=True)
            self.assertNotIn(key, seen, f"{item['name']} repeats {seen.get(key)}")
            seen[key] = item["name"]
        self.assertEqual(len(seen), len(armours()))
        self.assertGreaterEqual(len(armours()), 33)

    def test_no_two_armours_read_the_same_in_words(self):
        texts = [armory_effect_text(item["effect"]) for item in armours()]
        self.assertEqual(len(set(texts)), len(texts))

    def test_every_effect_is_one_the_engine_reads_and_within_its_caps(self):
        for item in armours():
            with self.subTest(armour=item["name"]):
                self.assertTrue(item["effect"], "an armour must do something")
                self.assertTrue(set(item["effect"]) <= ARMOUR_EFFECTS, set(item["effect"]) - ARMOUR_EFFECTS)
                for key, value in item["effect"].items():
                    if key in ARMORY_EFFECT_CAPS:
                        self.assertTrue(0 < value <= ARMORY_EFFECT_CAPS[key], key)

    def test_every_effect_reaches_the_resolved_gear(self):
        """Wear each armour alone: whatever it promises must show up in what the fight reads."""
        for item in armours():
            effect, resolved = item["effect"], effects_for(item)
            with self.subTest(armour=item["name"]):
                if "reduction" in effect:
                    self.assertEqual(resolved["reduction"], min(80, effect["reduction"]))
                self.assertEqual(resolved["first_miss_free"], bool(effect.get("first_miss_free")))
                self.assertEqual(resolved["revive"], bool(effect.get("revive")))
                if effect.get("revive"):
                    self.assertEqual(resolved["revive_source"], item["name"])
                self.assertEqual(resolved["start_guards"], effect.get("start_guards", 0))
                self.assertEqual(resolved["heal_on_objective"], effect.get("heal_on_objective", 0))
                self.assertEqual(resolved["coin_bonus"], effect.get("coin_bonus", 0))
                self.assertEqual(resolved["xp_bonus"], effect.get("xp_bonus", 0))
                self.assertEqual(resolved["loot_luck"], effect.get("loot_luck", 0))
                self.assertEqual(resolved["armor_impact"], effect.get("impact", 0))
                self.assertEqual(resolved["armor_on"], effect.get("on"))

    def test_tiers_keep_their_power_order_on_average(self):
        """Uniqueness must not make a common coat out-class a legendary plate: count each armour's roles."""
        power = {tier: [] for tier in ("common", "uncommon", "rare", "epic", "legendary")}
        for item in armours():
            effect = item["effect"]
            points = effect.get("reduction", 0) / 10 + 2 * bool(effect.get("first_miss_free")) + 2 * bool(effect.get("revive")) + 2 * effect.get("start_guards", 0) + effect.get("heal_on_objective", 0) + 2 * effect.get("impact", 0) + effect.get("coin_bonus", 0) / 10 + effect.get("xp_bonus", 0) / 10 + effect.get("loot_luck", 0) / 10
            power[item["tier"]].append(points)
        means = [sum(values) / len(values) for values in power.values()]
        self.assertEqual(means, sorted(means), dict(zip(power, means)))
        self.assertGreater(means[-1], 2 * means[0])


class ArmourInTheRingTests(unittest.TestCase):
    def setUp(self):
        use_real_content()

    def rounds(self, *marks):
        kinds = ("choice", "code", "text", "choice", "code")
        return [{"correct": mark, "kind": kinds[i]} for i, mark in enumerate(marks)]

    def armour(self, name):
        return next(item for item in armours() if item["name"] == name)

    def test_armour_impact_only_fires_on_its_question_type(self):
        effects = effects_for(self.armour("Gilded Lapel Armour"))  # +1 impact on predictions
        result = spar_sim.simulate(effects, self.rounds(True, True))  # a choice answer, then a code answer
        self.assertEqual([item["impact"] for item in result["rounds"]], [spar_sim.SPAR_ROUND_IMPACT[0] + 1, spar_sim.SPAR_ROUND_IMPACT[1]])
        self.assertIn("Gilded Lapel Armour +1", result["rounds"][0]["fired"])

    def test_a_bug_hunt_effect_counts_for_a_spar_code_question(self):
        effects = effects_for(self.armour("Auditor's Waistcoat"))
        result = spar_sim.simulate(effects, self.rounds(True, True))
        self.assertEqual(result["rounds"][1]["impact"], spar_sim.SPAR_ROUND_IMPACT[1] + 1)

    def test_a_banked_guard_and_a_heal_come_from_armour_alone(self):
        guard = spar_sim.simulate(effects_for(self.armour("Vault Guard Plate")), self.rounds(False, False))
        self.assertEqual([item["damage"] for item in guard["rounds"]], [0, 3])  # the plate's guard, then 32% less of 4 rounds up
        self.assertEqual(guard["start"]["guards"], 1)
        mender = spar_sim.simulate(effects_for(self.armour("Patchwork Travel Coat")), self.rounds(False, True))
        self.assertEqual([item["healed"] for item in mender["rounds"]], [0, 1])

    def test_a_reviving_armour_saves_the_hunter_once(self):
        result = spar_sim.simulate(effects_for(self.armour("Gravebound Warden Plate")), self.rounds(*[False] * 5))
        self.assertEqual(result["rounds"][-1]["hp"], 1)
        self.assertEqual(result["rounds"][-1]["fired"][-1], "Revive")

    def test_the_effects_panel_lists_what_armour_does(self):
        lines = spar_sim.effect_lines(effects_for(self.armour("Lamp-Lit Lamellar")))
        self.assertTrue(any("impact from your armour on code questions" in text for text in lines["applied"]), lines)
        self.assertTrue(any("free mistake" in text for text in lines["applied"]), lines)


if __name__ == "__main__":
    unittest.main()
