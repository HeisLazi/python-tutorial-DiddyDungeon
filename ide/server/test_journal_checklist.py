"""The Legacy Journal projection lists every echo and boss, not only the ones already earned."""
import json
import unittest

from ide.server.state import CAMPAIGN_DELVE_GEAR, DUNGEON_REGIONS, LocalStateService


def projection(unlocks=(), bosses=()):
    return LocalStateService._dungeon_journal_projection(
        {"dungeon_journal": {"unlocks": list(unlocks), "cleared_bosses": list(bosses)}}
    )


class JournalChecklistTests(unittest.TestCase):
    def test_an_empty_journal_still_lists_everything_that_can_be_earned(self):
        journal = projection()
        self.assertEqual(journal["unlocks"], [])
        self.assertEqual(len(journal["checklist"]), len(CAMPAIGN_DELVE_GEAR))
        self.assertEqual(len(journal["regions"]), len(DUNGEON_REGIONS))
        self.assertEqual(journal["totals"], {"bosses": 0, "bosses_total": len(DUNGEON_REGIONS), "echoes": 0, "echoes_total": len(CAMPAIGN_DELVE_GEAR)})
        self.assertFalse(any(row["earned"] for row in journal["checklist"]))

    def test_earned_echoes_and_cleared_bosses_are_marked_per_region(self):
        region = "basics"
        in_region = [item["id"] for item in CAMPAIGN_DELVE_GEAR if item.get("region") == region]
        journal = projection(unlocks=in_region[:2], bosses=[region])
        row = next(item for item in journal["regions"] if item["id"] == region)
        self.assertTrue(row["cleared"])
        self.assertEqual((row["echoes_earned"], row["echoes_total"]), (2, len(in_region)))
        self.assertEqual(journal["totals"]["echoes"], 2)
        self.assertEqual(journal["totals"]["bosses"], 1)
        self.assertEqual({item["id"] for item in journal["checklist"] if item["earned"]}, set(in_region[:2]))
        other = next(item for item in journal["regions"] if item["id"] != region)
        self.assertFalse(other["cleared"])

    def test_every_echo_says_how_it_is_earned_and_where_it_can_be_used(self):
        journal = projection()
        for row in journal["checklist"]:
            self.assertTrue(row["how"], row["id"])
            self.assertTrue(set(row["modes"]) <= {"campaign", "sparring", "pvp"}, row["id"])
            self.assertTrue(row["modes"], row["id"])
        hows = {row["how"].split(" · ")[0] for row in journal["checklist"]}
        self.assertTrue({"Elite drop", "Boss drop"} <= hows)

    def test_shop_gear_echoes_say_to_win_a_boss_in_the_gear(self):
        journal = projection()
        hows = {row["name"]: row["how"] for row in journal["checklist"]}
        self.assertEqual(hows["Lanternkeeper’s Coat"], "Prove it · win The Mimic Matriarch wearing Lantern Coat")
        self.assertEqual(hows["Oathkeeper Sabre"], "Prove it · win any boss wielding Syntax Sabre")
        self.assertFalse([row for row in journal["checklist"] if row["how"] == "Legacy reward"])
        armour = [row for row in journal["checklist"] if row["slot"] == "armor"]
        self.assertEqual({row["region"] for row in armour}, {"basics"})

    def test_basics_checklist_has_each_regional_reward_and_its_source(self):
        journal = projection()
        rows = {row["id"]: row for row in journal["checklist"] if row["region"] == "basics"}
        expected = {
            "campaign-dungeon-dawn-lantern": "Boss drop · The Mimic Matriarch",
            "campaign-dungeon-village-lantern": "Elite drop · Basics Village",
            "campaign-dungeon-pilgrim-knot": "Elite drop · Basics Village",
            "campaign-dungeon-warm-ember": "Elite drop · Basics Village",
            "campaign-dungeon-lantern-coat": "Prove it · win The Mimic Matriarch wearing Lantern Coat",
            "campaign-dungeon-pilgrim-ward": "Prove it · win The Mimic Matriarch wearing Pilgrim Ward",
        }
        self.assertEqual(set(rows), set(expected))
        self.assertEqual({item_id: row["how"] for item_id, row in rows.items()}, expected)
        region = next(row for row in journal["regions"] if row["id"] == "basics")
        self.assertEqual((region["echoes_earned"], region["echoes_total"]), (0, 6))

    def test_the_milestone_no_longer_claims_everything_is_unlocked_after_three_bosses(self):
        few = projection(bosses=["basics"])["next_milestone"]
        many = projection(bosses=["basics", "collections", "flow"])["next_milestone"]
        self.assertIn("+5 starting HP", few)
        self.assertNotIn("fully unlocked", many)
        self.assertIn("remaining", many)

    def test_unknown_or_duplicate_entries_are_ignored_and_the_payload_stays_small(self):
        known = CAMPAIGN_DELVE_GEAR[0]["id"]
        journal = projection(unlocks=[known, known, "not-a-real-item"], bosses=["basics", "basics", "nowhere"])
        self.assertEqual(journal["totals"]["echoes"], 1)
        self.assertEqual(journal["totals"]["bosses"], 1)
        self.assertLess(len(json.dumps(journal)), 24000)

    def test_existing_fields_are_unchanged_for_current_consumers(self):
        journal = projection(unlocks=[CAMPAIGN_DELVE_GEAR[0]["id"]], bosses=["basics", "collections"])
        # Existing keys keep their meaning; perks for bosses four to eight start at zero.
        self.assertEqual({key: journal["bonuses"][key] for key in ("starting_hp", "starting_bandages")}, {"starting_hp": 10, "starting_bandages": 0})
        self.assertEqual(sum(value for key, value in journal["bonuses"].items() if key not in ("starting_hp", "starting_bandages")), 0)
        self.assertEqual([boss["id"] for boss in journal["cleared_bosses"]], ["basics", "collections"])
        self.assertEqual(journal["unlocks"][0]["id"], CAMPAIGN_DELVE_GEAR[0]["id"])


if __name__ == "__main__":
    unittest.main()
