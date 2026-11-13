#!/usr/bin/env python3
"""Create a throwaway "everything unlocked" Quest Lab save for testing.

Usage: tools/make_test_save.py /absolute/path/progress.json [--force]

This only ever writes the path you give it, never the real progress.json, and refuses to replace an
existing file unless --force is passed. Pair it with QUESTLAB_TEST_UNLOCKS=1 (see
tools/questlab-test.sh), which also stocks every Dungeon run.

Unlocks: every armory item (weapons, armour, trinkets, aids, supplies, forged and online gear), every
Legacy Journal echo and all eight bosses (so every run perk applies), all hunter signs at a high
level, a full stock of Dungeon materials, every online mastery appearance, a high player level and a
large purse, and every campaign opened with its bounty board seeded.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ide.server.new_game import fresh_progress  # noqa: E402
from ide.server.state import (  # noqa: E402
    ARMORY_STACK_SLOTS,
    CAMPAIGN_DELVE_GEAR,
    DUNGEON_MATERIAL_NAMES,
    DUNGEON_REGIONS,
    HUNTER_SIGN_COUNTERS,
    HUNTER_SIGN_KEYWORDS,
    ONLINE_MASTERY_BY_ID,
    LocalStateService,
    armory_catalog,
)

BIG_PURSE = 999_999
SIGN_XP = 1_000_000
MATERIAL_COUNT = 99


def everything_unlocked() -> dict:
    progress = fresh_progress()
    for project in progress["projects"]:
        LocalStateService._open_project(progress, project)
    progress["player"].update(level=30, xp=0, xp_next=10_000, lifetime_xp=500_000, coins=BIG_PURSE, hp=130, max_hp=130)

    hunter = LocalStateService._hunter_state(progress)
    for item_id, item in armory_catalog().items():
        LocalStateService._armory_add(hunter, item_id, 9 if item.get("slot") in ARMORY_STACK_SLOTS else 1)
    hunter["armory"]["owned_appearances"] = sorted(ONLINE_MASTERY_BY_ID)
    # A sign's level is capped until its gates are met (a Tutor pass, enough clean casts, a campaign
    # use and a teachback), so fill every counter, not just the XP.
    for sign_id in HUNTER_SIGN_KEYWORDS:
        hunter["signs"][sign_id] = {**{counter: 50 for counter in HUNTER_SIGN_COUNTERS}, "xp": SIGN_XP}
    for material in DUNGEON_MATERIAL_NAMES:
        hunter["materials"][material] = MATERIAL_COUNT

    progress["dungeon_journal"] = {
        "unlocks": [item["id"] for item in CAMPAIGN_DELVE_GEAR],
        "cleared_bosses": list(DUNGEON_REGIONS),
    }
    progress["test_save"] = {"purpose": "everything unlocked for testing; not a real save"}
    return progress


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="absolute path of the test save to create")
    parser.add_argument("--force", action="store_true", help="replace an existing test save")
    args = parser.parse_args()
    path = args.path
    if not path.is_absolute():
        parser.error("the test save path must be absolute")
    if path.name == "progress.json" and path.resolve() == (ROOT / "progress.json").resolve():
        parser.error("refusing to touch the real progress.json")
    if path.exists() and not args.force:
        print(f"Test save already exists, left as it is: {path}")
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(everything_unlocked(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote everything-unlocked test save: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
