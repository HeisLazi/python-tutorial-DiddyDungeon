"""Every trinket has an identity of its own: a distinct effect, not one of four shared ones."""
from __future__ import annotations

import json
import unittest

from ide.server import spar_sim
from ide.server.state import ARMORY_EFFECT_CAPS, GEAR_TRIGGER_KEYS, LocalStateService, armory_catalog, armory_effect_text
from ide.server.test_campaign_content import use_real_content

TRINKET_EFFECTS = {"impact", "on", "start_guards", "block_first_miss", "revive", "heal_on_objective", "coin_bonus", "xp_bonus", "loot_luck", "reduction", *GEAR_TRIGGER_KEYS}
TIERS = ("common", "uncommon", "rare", "epic", "legendary", "ethereal")


def trinkets():
    return [item for item in armory_catalog().values() if item["slot"] == "trinket"]


def power(effect):
    flags = 2 * bool(effect.get("block_first_miss")) + 3 * bool(effect.get("revive")) + 2 * effect.get("start_guards", 0)
    triggers = sum(2 * effect.get(key, 0) for key in GEAR_TRIGGER_KEYS if key.startswith("chip_") or key in {"heal_clean", "coin_clean"})
    return (flags + triggers + 2 * effect.get("impact", 0) + effect.get("heal_on_objective", 0) + 1.5 * (effect.get("opening_impact", 0) + effect.get("retry_impact", 0))
            + (effect.get("coin_bonus", 0) + effect.get("xp_bonus", 0) + effect.get("loot_luck", 0) + effect.get("reduction", 0)) / 8
            + effect.get("break_coins", 0) / 5 + effect.get("heal_on_break", 0) / 3)


def resolved(item):
    return LocalStateService.spar_loadout_effects(None, None, item["name"])


class TrinketIdentityTests(unittest.TestCase):
    def setUp(self):
        use_real_content()

    def test_there_are_sixty_four_trinkets_and_no_two_share_an_effect(self):
        seen = {}
        for item in trinkets():
            key = json.dumps(item["effect"], sort_keys=True)
            self.assertNotIn(key, seen, f"{item['name']} repeats {seen.get(key)}")
            seen[key] = item["name"]
        self.assertEqual(len(seen), len(trinkets()))
        self.assertGreaterEqual(len(trinkets()), 64)

    def test_no_two_trinkets_read_the_same_in_words(self):
        texts = [armory_effect_text(item["effect"]) for item in trinkets()]
        self.assertEqual(len(set(texts)), len(texts))

    def test_every_effect_is_one_the_engine_reads_and_within_its_caps(self):
        for item in trinkets():
            with self.subTest(trinket=item["name"]):
                self.assertTrue(item["effect"], "a trinket must do something")
                self.assertTrue(set(item["effect"]) <= TRINKET_EFFECTS, set(item["effect"]) - TRINKET_EFFECTS)
                for key, value in item["effect"].items():
                    if key in ARMORY_EFFECT_CAPS:
                        self.assertTrue(0 < value <= ARMORY_EFFECT_CAPS[key], key)

    def test_every_trinket_has_its_own_flavour(self):
        flavours = [item.get("flavour") or item.get("description") for item in trinkets()]
        self.assertTrue(all(flavours))
        # Elite keepsakes share one sentence per elite by design; every other trinket reads differently.
        others = [text for item, text in zip(trinkets(), flavours) if item["campaign"] != "elite"]
        self.assertEqual(len(set(others)), len(others), "two trinkets share flavour text")

    def test_every_effect_reaches_the_resolved_gear(self):
        """Wear each trinket alone: whatever it promises must show up in what the fight reads."""
        for item in trinkets():
            effect, fight = item["effect"], resolved(item)
            with self.subTest(trinket=item["name"]):
                self.assertEqual(fight["start_guards"], effect.get("start_guards", 0))
                self.assertEqual(fight["block_first_miss"], bool(effect.get("block_first_miss")))
                self.assertEqual(fight["revive"], bool(effect.get("revive")))
                self.assertEqual(fight["heal_on_objective"], effect.get("heal_on_objective", 0))
                self.assertEqual(fight["coin_bonus"], effect.get("coin_bonus", 0))
                self.assertEqual(fight["xp_bonus"], effect.get("xp_bonus", 0))
                self.assertEqual(fight["loot_luck"], effect.get("loot_luck", 0))
                self.assertEqual(fight["trinket_impact"], effect.get("impact", 0))
                self.assertEqual(fight["trinket_on"], effect.get("on"))
                for key in GEAR_TRIGGER_KEYS:
                    self.assertEqual((fight["triggers"] or {}).get(key, 0), effect.get(key, 0), key)

    def test_tiers_keep_their_power_order_on_average(self):
        by_tier = {tier: [power(item["effect"]) for item in trinkets() if item["tier"] == tier] for tier in TIERS}
        means = [sum(values) / len(values) for values in by_tier.values() if values]
        self.assertEqual(means, sorted(means), {tier: round(sum(v) / len(v), 2) for tier, v in by_tier.items() if v})
        self.assertGreater(means[-1], 2 * means[0])


class TrinketInTheRingTests(unittest.TestCase):
    def setUp(self):
        use_real_content()

    def rounds(self, *marks):
        kinds = ("choice", "code", "text", "choice", "code")
        return [{"correct": mark, "kind": kinds[i]} for i, mark in enumerate(marks)]

    def effects(self, name):
        return LocalStateService.spar_loadout_effects(None, None, name)

    def test_opening_impact_only_helps_the_first_right_answer(self):
        result = spar_sim.simulate(self.effects("Delver's Keeper’s Ring"), self.rounds(True, True))
        base = spar_sim.SPAR_ROUND_IMPACT
        self.assertEqual([item["impact"] for item in result["rounds"]], [base[0] + 2, base[1]])
        self.assertIn("Opening +2", result["rounds"][0]["fired"])

    def test_a_signature_trigger_on_a_trinket_fires_without_a_weapon(self):
        result = spar_sim.simulate(self.effects("Weighted Die"), self.rounds(True, True))  # Variety: the question type changes
        self.assertEqual(result["rounds"][0]["fired"], [])
        self.assertIn("Variety +1", result["rounds"][1]["fired"])

    def test_a_low_hp_trinket_wakes_when_the_hunter_is_hurt(self):
        effects = self.effects("Delver's Bull Ring")  # +2 impact at half HP or less
        hurt = spar_sim.simulate(effects, self.rounds(False, False, False, False, True))
        self.assertTrue(any("Last stand" in label for label in hurt["rounds"][-1]["fired"]), hurt["rounds"][-1])
        fresh = spar_sim.simulate(effects, self.rounds(True))
        self.assertFalse(any("Last stand" in label for label in fresh["rounds"][0]["fired"]))

    def test_healing_a_guard_break_and_a_revive_come_from_trinkets_alone(self):
        mender = spar_sim.simulate(self.effects("Canary Feather"), self.rounds(False, True))
        self.assertEqual([item["healed"] for item in mender["rounds"]], [0, 1])
        revived = spar_sim.simulate(self.effects("Delver's Last Spark"), self.rounds(*[False] * 5))
        self.assertEqual(revived["rounds"][-1]["hp"], 1)

    def test_trinket_reduction_adds_to_the_armour_in_the_ring(self):
        both = LocalStateService.spar_loadout_effects(None, "Riveted Leather", "Delver's Brass Gear")
        self.assertEqual(both["reduction"], 16 + 6)


if __name__ == "__main__":
    unittest.main()
