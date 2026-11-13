"""The "everything unlocked" Quest Lab save used for testing.

Lives in the server package (not tools/) so the installed desktop app can build it too. It never
touches a real save: callers pass the path, and ``initialize_test_save`` only creates a missing file.
"""
from __future__ import annotations

import json
from pathlib import Path

from ide.server.new_game import fresh_progress
from ide.server.state import (
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


def initialize_test_save(path: Path) -> bool:
    """Create the test save only when absent; keep any test progress already made."""
    if not path.is_absolute():
        raise ValueError("The test save path must be absolute")
    if path.exists():
        return False
    content = json.dumps(everything_unlocked(), indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as target:
            target.write(content)
    except FileExistsError:
        return False
    return True
