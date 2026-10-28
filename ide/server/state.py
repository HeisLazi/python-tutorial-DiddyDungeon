"""Bounded local campaign-state mutation service.

The Forge backend is the only local writer for canonical progression state.
Callers submit named commands with an explicit trust level; arbitrary object
paths, JSON patches and direct snapshots are intentionally unsupported.
"""

from __future__ import annotations

import copy
import hashlib
import json
import os
import random
import re
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ide.server.beginner_codex import BEGINNER_CODEX
from ide.server.home_rooms import HOME_ROOM_LABELS, HOME_ROOM_LADDERS, effective_room_levels, validate_room_levels

MAX_EVENT_RECORDS = 100
MAX_REASON_LENGTH = 240
# An optional base layer of bounty boards keyed by project branch, under the
# story files. The shipped game has none; tests point it at the archived
# legacy boards (campaigns_archive/legacy_bounties.json) as fixture content.
CAMPAIGN_BOUNTIES_PATH: Path | None = None
# One authored story file per project (ide/server/campaigns/<branch>.json):
# its story, acts and contracts, each contract with its own objectives. A
# file here replaces that project's entry in the base layer.
CAMPAIGN_CONTENT_DIR = Path(__file__).with_name("campaigns")
# Campaigns taken out of the game (their files are in campaigns_archive/).
# An untouched save project on one of these is removed; one with any
# progress is kept as it is.
RETIRED_CAMPAIGNS = frozenset({
    "00-rps-tournament", "02-detective-game", "03-pokemon-battle", "06-gladiator-arena",
    "07-football-manager", "08-game-agent", "09-ai-agent",
})
# setup_check: a workshop step (make the folder, the file, run it) the game
# checks on disk by itself, with no PYR call.
CAMPAIGN_QUESTION_TYPES = frozenset({"code_checkpoint", "bug_diagnosis", "prediction", "explanation", "setup_check"})
_CAMPAIGN_CACHE: dict[str, Any] = {"key": None, "data": {}}


def boss_gauntlet(project: Mapping[str, Any]) -> tuple[str, ...]:
    """This boss's phases in fight order: the project's own list, else its
    campaign story file's boss_gauntlet, else the default four."""

    configured = project.get("boss_gauntlet")
    if not isinstance(configured, list):
        story = load_campaign_bounties().get(str(project.get("branch") or ""))
        configured = story.get("boss_gauntlet") if isinstance(story, Mapping) else None
    if isinstance(configured, list):
        phases = tuple(dict.fromkeys(item for item in configured if item in BOSS_REQUIREMENTS))
        if phases and phases[0] == "required_behavior":
            return phases
    return DEFAULT_BOSS_GAUNTLET


def load_campaign_bounties() -> dict[str, Any]:
    base = CAMPAIGN_BOUNTIES_PATH
    stories = sorted(CAMPAIGN_CONTENT_DIR.glob("*.json")) if CAMPAIGN_CONTENT_DIR.is_dir() else []
    paths = [*([base] if base is not None else []), *stories]
    try:
        key = tuple((str(path), path.stat().st_mtime_ns) for path in paths if path.exists())
    except OSError:
        key = None
    if key is not None and key == _CAMPAIGN_CACHE["key"]:
        return _CAMPAIGN_CACHE["data"]
    try:
        data = json.loads(base.read_text(encoding="utf-8")) if base is not None else {}
    except (OSError, ValueError):
        data = {}
    data = dict(data) if isinstance(data, dict) else {}
    for path in stories:
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(entry, dict) and isinstance(entry.get("branch"), str):
            data[entry["branch"]] = entry
    _CAMPAIGN_CACHE.update(key=key, data=data)
    return data


# A project file, at most one folder deep (crawler/world.py, tests/test_world.py).
PROJECT_FILE_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,40}(?:/[A-Za-z0-9_][A-Za-z0-9_.-]{0,80})?\.(?:py|md|json|txt|toml|cfg|ini)$")
# The kinds of bounty a campaign can author, shown on its poster.
CONTRACT_KINDS = frozenset({"workshop", "debug", "memory", "creative"})


PROJECT_DIR_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,40}$")


def project_dir_name(value: object) -> str:
    """A multi-file campaign's own folder in the workspace (never the root)."""

    return value if isinstance(value, str) and PROJECT_DIR_NAME.match(value) else ""


def project_file_name(value: object) -> str | None:
    """A plain project file name (no folders) a goal can be graded on."""

    return value if isinstance(value, str) and PROJECT_FILE_NAME.match(value) and value not in {"tutor.py", "dungeon.py"} else None


SETUP_FOLDER_NAME = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,40}$")


def setup_check_spec(value: object) -> dict[str, Any] | None:
    """A setup step's check, inside the campaign folder: {"dir": "."} or a
    subfolder, {"file": name}, or {"run": name.py, "expect": [text, ...]}."""

    if not isinstance(value, Mapping):
        return None
    if set(value) == {"dir"} and (value["dir"] == "." or (isinstance(value["dir"], str) and SETUP_FOLDER_NAME.match(value["dir"]))):
        return {"dir": value["dir"]}
    if set(value) == {"file"} and project_file_name(value["file"]):
        return {"file": value["file"]}
    if set(value) == {"run", "expect"} and project_file_name(value["run"]) and value["run"].endswith(".py"):
        expect = value["expect"]
        if isinstance(expect, list) and 0 < len(expect) <= 4 and all(isinstance(item, str) and 0 < len(item) <= 80 for item in expect):
            return {"run": value["run"], "expect": list(expect)}
    return None


def campaign_contract(branch: object, mob_name: object) -> dict[str, Any] | None:
    """The authored contract for one bounty, matched by name (never index)."""

    entry = load_campaign_bounties().get(str(branch or ""))
    mobs = entry.get("mobs") if isinstance(entry, Mapping) else None
    if not isinstance(mobs, list):
        return None
    return next((item for item in mobs if isinstance(item, dict) and item.get("name") == mob_name), None)
MAX_IDENTIFIER_LENGTH = 120
MAX_REWARD_XP = 100
# Asking PYR for help during a campaign fight costs that fight's rewards:
# each ask takes 20% off its XP and coins (never below 40%), and from the
# second ask on it drops no loot. The bounty also stops counting as clean.
PYR_ASSIST_REWARD_STEP = 20
PYR_ASSIST_REWARD_FLOOR = 40
PYR_ASSIST_LOOT_LIMIT = 2
MAX_REWARD_COINS = 100
MAX_HP_DELTA = 100
MAX_IMPACT = 8
MAX_CODEX_RECORDS = 100
MAX_CODEX_NOTE_BYTES = 2_000
MAX_CODEX_NOTES_PER_ENTRY = 20
MAX_CODEX_SNIPPET_BYTES = 1_600
MAX_PRACTICE_SESSIONS = 50
MAX_PRACTICE_ATTEMPTS_PER_SESSION = 20
PRACTICE_QUESTION_TYPES = frozenset({"true_false", "multiple_choice", "short_explanation", "code_trace", "bug_hunt"})
# Keep selector order and labels server-owned so Tutor and Practice cannot
# drift into a second, answer-bearing question catalogue in the browser.
PRACTICE_QUESTION_TYPE_ORDER: tuple[str, ...] = (
    "true_false",
    "multiple_choice",
    "short_explanation",
    "code_trace",
    "bug_hunt",
)
PRACTICE_QUESTION_TYPE_LABELS: dict[str, str] = {
    "true_false": "True or false",
    "multiple_choice": "Multiple choice",
    "short_explanation": "Short explanation",
    "code_trace": "Code trace",
    "bug_hunt": "Bug hunt",
}
PRACTICE_DIFFICULTY_MIN = 1
PRACTICE_DIFFICULTY_MAX = 5
CODEX_NOTES_DIRECTORY = "notes"
MAX_DUNGEON_LEADERBOARD = 50
MAX_DUNGEON_INVENTORY = 24
MAX_SYNC_LIST_ITEMS = 100
MAX_SYNC_TEXT_LENGTH = 120
MAX_SYNC_LEVEL = 1000
MAX_SYNC_COUNTER = 1_000_000_000
MAX_SYNC_CAMPAIGN_BYTES = 18_000
MAX_SYNC_PROJECTS = 20
MAX_SYNC_MOBS_PER_PROJECT = 20
MAX_SYNC_GOALS_PER_BUCKET = 20
MAX_SYNC_SKILLS = 50
MAX_SYNC_ACHIEVEMENTS = 100
MAX_SYNC_CODEX_RESULTS = 20
MAX_SYNC_DUNGEON_HISTORY = 50
BATTLE_RAW_DAMAGE_BY_MOB = (6, 10, 15, 18, 22, 24, 26, 28)
MAX_DUNGEON_EDITOR_BYTES = 120_000
MAX_DUNGEON_OPTIONS = 8
MAX_DUNGEON_FLOOR = 1_000_000
MAX_DUNGEON_ROOM = 1_000_000
MAX_DUNGEON_DIFFICULTY = 10
MAX_EQUIPMENT_ITEMS = 24
DUNGEON_SCORE_BY_DIFFICULTY = (0, 10, 15, 20, 30, 45, 60, 80, 105, 135, 170)
DUNGEON_COIN_BY_DIFFICULTY = (0, 5, 8, 11, 15, 20, 26, 33, 41, 50, 60)
DUNGEON_REST_HEAL = 30
CUSTODY_CONFIRMATION_TOKEN = "MIGRATE_LOCAL_STATE"
CUSTODY_MARKER_VERSION = 1
DUNGEON_MARKET_CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "dungeon-heal", "name": "Field Ration", "price": 12, "kind": "heal", "description": "Restore 20 run HP."},
    {"id": "dungeon-bandage", "name": "Field Bandage", "price": 18, "kind": "supply", "supply": "bandages", "description": "+22 HP at a campsite."},
    {"id": "dungeon-ration", "name": "Trail Ration", "price": 14, "kind": "supply", "supply": "rations", "description": "+10 maximum HP at a campsite."},
    {"id": "dungeon-vision-scroll", "name": "Vision Scroll", "price": 80, "kind": "supply", "supply": "vision_scrolls", "description": "Reveal one unknown risk room."},
    {"id": "dungeon-tonic", "name": "Ember Tonic", "price": 32, "kind": "supply", "supply": "tonics", "description": "+30 HP at a campsite."},
    {"id": "dungeon-ward", "name": "Ember Ward", "price": 24, "kind": "armor", "armor": "Ember Ward", "description": "Reduce the next counterattack."},
    {"id": "dungeon-lens", "name": "Scholar Lens", "price": 30, "kind": "trinket", "trinket": "Scholar Lens", "description": "A cosmetic run trophy for careful reasoning."},
    {"id": "dungeon-syntax-sabre", "name": "Syntax Sabre", "price": 70, "kind": "weapon", "weapon": "Syntax Sabre", "description": "+1 run Resolve damage when the objective is explained."},
    {"id": "dungeon-loopblade", "name": "Loopblade", "price": 78, "kind": "weapon", "weapon": "Loopblade", "description": "+1 run Resolve damage against elite challenges."},
    {"id": "dungeon-field-jacket", "name": "Field Jacket", "price": 72, "kind": "armor", "armor": "Field Jacket", "description": "Reduce failed-run damage by 6."},
    {"id": "dungeon-syntax-cuirass", "name": "Syntax Cuirass", "price": 88, "kind": "armor", "armor": "Syntax Cuirass", "description": "The first failed submission each floor costs less HP."},
)

# Campaign equipment is a separate, validated loadout from Homestead
# cosmetics.  The browser only receives items that are already present in the
# canonical owned lists (or the currently equipped legacy value), so this
# catalogue never reveals future loot by itself.
EQUIPMENT_CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "armor-apprentice-coat", "name": "Apprentice Coat", "kind": "armor", "effect": "10% Battle damage reduction", "description": "Starter armor for the campaign."},
    {"id": "armor-leather-guard", "name": "Leather Guard", "kind": "armor", "effect": "20% Battle damage reduction", "description": "A light guard earned through steady practice."},
    {"id": "armor-runic-mail", "name": "Runic Mail", "kind": "armor", "effect": "30% Battle damage reduction", "description": "Runes reinforce the answer under pressure."},
    {"id": "armor-emberplate", "name": "Emberplate", "kind": "armor", "effect": "40% Battle damage reduction", "description": "A warm plate for difficult encounters."},
    {"id": "armor-guardian-aegis", "name": "Guardian Aegis", "kind": "armor", "effect": "50% Battle damage reduction", "description": "A heavy ward against a hard lesson."},
    {"id": "armor-mythril-archive-plate", "name": "Mythril Archive Plate", "kind": "armor", "effect": "60% Battle damage reduction", "description": "Legendary protection for a well-kept archive."},
    {"id": "trinket-none", "name": "None", "kind": "trinket", "effect": "No special effect", "description": "Leave the trinket slot empty."},
    {"id": "trinket-ember-scythe", "name": "Ember Scythe", "kind": "trinket", "effect": "+1 Impact on the first verified objective", "description": "A weapon-shaped trinket; Impact remains evidence-backed."},
    {"id": "trinket-guardian-sigil", "name": "Guardian Sigil", "kind": "trinket", "effect": "Negates one counterattack", "description": "A single bounded ward for a risky submission."},
    {"id": "trinket-phoenix-ember", "name": "Phoenix Ember", "kind": "trinket", "effect": "Revives at 1 HP once per encounter", "description": "A last spark when an incorrect answer would down you."},
    {"id": "debugger-plate", "name": "Debugger Plate", "kind": "armor", "effect": "15% less damage from misses", "description": "A plated guard tuned for the next mechanic."},
    {"id": "ledgerguard-coat", "name": "Ledgerguard Coat", "kind": "armor", "effect": "25% less damage from misses", "description": "A careful coat for long, difficult lessons."},
    {"id": "emberweave-mantle", "name": "Emberweave Mantle", "kind": "armor", "effect": "30% less damage from misses", "description": "Warm woven plates catch one punishing mistake."},
    {"id": "syntax-ward", "name": "Syntax Ward", "kind": "trinket", "effect": "Blocks the first counterattack each battle", "description": "A compact ward against syntax-error damage."},
    {"id": "loop-lens", "name": "Loop Lens", "kind": "trinket", "effect": "Heal 2 HP per verified objective", "description": "A lens that rewards careful loop construction."},
    {"id": "guard-bell", "name": "Guard Bell", "kind": "trinket", "effect": "Start every battle with a free mistake", "description": "A small bell that makes danger easier to read."},
    {"id": "scimitar-of-momentum", "name": "Scimitar of Momentum", "kind": "trinket", "effect": "+15% bounty coins", "description": "A weapon-shaped trinket for pressing an opening."},
    {"id": "vision-scroll", "name": "Vision Scroll", "kind": "trinket", "effect": "+10% chance of rarer loot", "description": "A costly scroll that exposes one uncertain route."},
)
EQUIPMENT_BY_ID: dict[str, dict[str, Any]] = {item["id"]: item for item in EQUIPMENT_CATALOG}
# Paper-doll appearance, stored as equipment.avatar. Values are names the
# frontend maps to palette colours (avatarSprite.js); anything else is
# rejected so local and synced saves can only hold known options.
AVATAR_OPTIONS: dict[str, tuple[str, ...]] = {
    "skin": ("espresso", "deep", "umber", "brown", "caramel", "tan", "olive", "fair", "porcelain"),
    "hair_style": (
        "locs_taper", "freeform", "twists", "barrel_twists", "twist_out", "afro",
        "bantu_knots", "waves", "brush_cut", "taper", "hooded",
    ),
    "hair_color": (
        "black", "dark_brown", "brown", "auburn", "copper", "honey", "blonde", "platinum",
        "silver", "white", "burgundy", "crimson", "pink", "violet", "blue", "teal", "green",
    ),
    "facial_hair": ("none", "stubble", "mustache", "goatee", "circle_beard", "chin_strap", "full_beard"),
    # "match" follows hair_color; otherwise any hair colour.
    "beard_color": (
        "match", "black", "dark_brown", "brown", "auburn", "copper", "honey", "blonde", "platinum",
        "silver", "white", "burgundy", "crimson", "pink", "violet", "blue", "teal", "green",
    ),
    "eyes": ("brown", "blue", "green", "grey", "amber"),
    "outfit": ("indigo", "crimson", "forest", "charcoal", "plum", "teal", "gold", "sand"),
    "accent": ("gold", "silver", "crimson", "teal", "violet", "white"),
}
DEFAULT_AVATAR: dict[str, str] = {
    # Tate Buti: dark skin, hood up. Other skins and the hairstyles stay
    # valid so older saves still load.
    "skin": "deep",
    "hair_style": "hooded",
    "hair_color": "black",
    "facial_hair": "none",
    "beard_color": "match",
    "eyes": "brown",
    "outfit": "indigo",
    "accent": "gold",
}
EQUIPMENT_ID_BY_NAME: dict[str, str] = {item["name"]: item["id"] for item in EQUIPMENT_CATALOG}

# Campaign Market lots are canonical, single-copy offers.  The browser may
# render the prototype's presentation, but price, ownership and the resulting
# inventory mutation are decided here.
CAMPAIGN_MARKET_CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "field-bandage", "name": "Field bandage", "kind": "supply", "supply": "bandages", "price": 18, "description": "Recover during Home preparation."},
    {"id": "ember-tonic", "name": "Ember tonic", "kind": "supply", "supply": "tonics", "price": 32, "description": "A one-use buffer for the next encounter."},
    {"id": "camp-meal", "name": "Camp meal", "kind": "supply", "supply": "meals", "price": 26, "description": "Restore a small amount of HP from the encounter kit."},
    {"id": "debugger-plate", "name": "Debugger Plate", "kind": "armor", "price": 72, "description": "15% less damage from misses."},
    {"id": "ledgerguard-coat", "name": "Ledgerguard Coat", "kind": "armor", "price": 118, "description": "25% less damage from misses."},
    {"id": "emberweave-mantle", "name": "Emberweave Mantle", "kind": "armor", "price": 146, "description": "30% less damage from misses."},
    {"id": "syntax-ward", "name": "Syntax Ward", "kind": "trinket", "price": 48, "description": "Blocks the first counterattack each battle."},
    {"id": "loop-lens", "name": "Loop Lens", "kind": "trinket", "price": 64, "description": "Heal 2 HP per verified objective."},
    {"id": "guard-bell", "name": "Guard Bell", "kind": "trinket", "price": 78, "description": "Start every battle with a free mistake."},
    {"id": "scimitar-of-momentum", "name": "Scimitar of Momentum", "kind": "trinket", "price": 110, "description": "+15% bounty coins."},
    {"id": "vision-scroll", "name": "Vision Scroll", "kind": "trinket", "price": 125, "description": "+10% chance of rarer loot."},
)
CAMPAIGN_MARKET_BY_ID: dict[str, dict[str, Any]] = {item["id"]: item for item in CAMPAIGN_MARKET_CATALOG}

# Homestead room progression is intentionally a small authored catalogue.  The
# browser may render this copy, but ownership, costs and the resulting stat
# deltas are validated here so the port cannot turn the drawer into a client
# controlled reward path.
HOME_ROOM_UPGRADE_CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "reinforced-hearth", "name": "Reinforced Hearth", "kind": "STAT", "cost": 1, "effect": "MAX HP +10", "detail": "A stronger hearth gives you ten more maximum HP.", "max_hp_delta": 10},
    {"id": "warding-loom", "name": "Warding Loom", "kind": "TRINKET", "cost": 2, "effect": "RETALIATION −2", "detail": "Threaded syntax wards soften each failed submission by 2 HP.", "failure_damage_reduction": 2},
    {"id": "breaker-workbench", "name": "Breaker Workbench", "kind": "STAT", "cost": 2, "effect": "BREAK +1", "detail": "Tune your kit to break Guard one Resolve point faster.", "resolve_impact_delta": 1},
    {"id": "siphon-basin", "name": "Siphon Basin", "kind": "TRINKET", "cost": 3, "effect": "BREAK HEAL +4", "detail": "A clean Guard Break restores 4 HP before the final submit.", "guard_break_heal": 4},
    {"id": "field-kitchen", "name": "Field Kitchen", "kind": "STAT", "cost": 2, "effect": "MEALS +5", "detail": "Packed meals restore 5 extra HP when eaten at Home.", "meal_heal_delta": 5},
)
HOME_ROOM_UPGRADE_BY_ID: dict[str, dict[str, Any]] = {item["id"]: item for item in HOME_ROOM_UPGRADE_CATALOG}
# Route choices are intentionally answer-free.  The state service owns the
# route ids and room types; the browser may render these labels but cannot
# choose a question, reward, or answer key.
DUNGEON_ROUTE_CHOICES: tuple[dict[str, str], ...] = (
    {
        "id": "encounter",
        "kind": "encounter",
        "label": "Challenge room",
        "description": "Face one adaptive question and earn run score.",
    },
    {
        "id": "rest",
        "kind": "rest",
        "label": "Quiet rest",
        "description": "Recover at the ember when your run needs it.",
    },
    {
        "id": "market",
        "kind": "market",
        "label": "Wayfarer market",
        "description": "Spend run coins on a temporary aid.",
    },
)

# The Infinite Dungeon map is generated once by the state gateway when a run
# starts.  React receives room identities and the current lane, but never
# invents future nodes or route edges.  Questions, answers and reward payloads
# remain undisclosed until the player commits to a node.
DUNGEON_MAP_ROWS = 8
DUNGEON_MAP_NODE_COLUMNS = (1, 3, 5)
DUNGEON_MAP_ROOM_TYPES = ("encounter", "elite", "mystery", "rest", "market")
DUNGEON_MAP_FINAL_PREP_TYPES = ("rest", "market")
DUNGEON_MAP_ROOM_LABELS: dict[str, str] = {
    "encounter": "Challenge gate",
    "elite": "Elite gate",
    "mystery": "Fate / risk",
    "rest": "Campsite",
    "market": "Wayfarer market",
    "boss": "Floor boss",
}
DUNGEON_MAP_ROOM_NOTES: dict[str, str] = {
    "encounter": "fight",
    "elite": "trinket",
    "mystery": "risk",
    "rest": "recover",
    "market": "trade",
    "boss": "final destination",
}
DUNGEON_RISK_PROFILES: tuple[dict[str, str], ...] = (
    {"kind": "elite", "room_type": "elite", "title": "Elite ambush", "preview": "A harder fight. A clean clear drops a trinket and run coins."},
    {"kind": "quiz", "room_type": "encounter", "title": "Risk quiz", "preview": "A failed answer costs HP; a clean answer yields run coins."},
    {"kind": "reward", "room_type": "cache", "title": "Hidden cache", "preview": "Open the cache for a bounded coin and supply reward."},
    {"kind": "debuff", "room_type": "shrine", "title": "Hexed route", "preview": "The next failed submission costs extra HP, but the curse cannot end a run by itself."},
    {"kind": "buff", "room_type": "shrine", "title": "Ember blessing", "preview": "The next clean submission deals bonus Resolve damage."},
    {"kind": "teleport", "room_type": "corridor", "title": "Folding corridor", "preview": "Distance bends ahead; the route is committed when you enter."},
    {"kind": "discount", "room_type": "market", "title": "Discount stall", "preview": "Buy one rotating supply at a starting-value discount."},
    {"kind": "armory", "room_type": "market", "title": "Sealed armory", "preview": "Choose one weapon or armor piece from the bounded shelf."},
)

# Dungeon classes are part of the run contract rather than Campaign equipment.
# The browser may present these bounded choices, but the selected passive and
# starter loadout are recorded by the state service and restored with the run.
DUNGEON_CLASS_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "syntax-warden",
        "name": "Syntax Warden",
        "role": "The guarded opener",
        "passive": "The first syntax-error submission each floor deals no HP damage.",
        "starter_weapon": "Lint Lantern",
        "starter_weapon_id": "dungeon-lint-lantern",
        "starting_coins": 0,
        "extra_heals": 0,
        "resolve_bonus": 0,
        "syntax_guard": True,
    },
    {
        "id": "resolve-duelist",
        "name": "Resolve Duelist",
        "role": "The clean finisher",
        "passive": "Clean submissions deal +1 Resolve damage in this run.",
        "starter_weapon": "Loopblade",
        "starter_weapon_id": "dungeon-loopblade",
        "starting_coins": 0,
        "extra_heals": 0,
        "resolve_bonus": 1,
        "syntax_guard": False,
    },
    {
        "id": "route-merchant",
        "name": "Route Merchant",
        "role": "The prepared wayfarer",
        "passive": "Start with +20 run coins and one extra heal charge.",
        "starter_weapon": "Branch Compass",
        "starter_weapon_id": "dungeon-branch-compass",
        "starting_coins": 20,
        "extra_heals": 1,
        "resolve_bonus": 0,
        "syntax_guard": False,
    },
)
DUNGEON_CLASSES_BY_ID: dict[str, dict[str, Any]] = {item["id"]: item for item in DUNGEON_CLASS_CATALOG}

# A Dungeon room is a custom learning mob, not a second campaign enemy list.
# These names are server-owned presentation labels for the currently issued
# question type; the concept focus, phase and all score/reward values remain
# derived from the canonical run/question and are never guessed by React.
DUNGEON_MOB_ARCHETYPES: dict[str, dict[str, str]] = {
    "true_false": {"name": "The Verdict Wisp", "category": "signal check"},
    "multiple_choice": {"name": "The Forked Path", "category": "choice reasoning"},
    "short_explanation": {"name": "The Echo Scribe", "category": "explanation"},
    "code_trace": {"name": "The Trace Weaver", "category": "execution trace"},
    "bug_hunt": {"name": "The Boundary Hunter", "category": "bug hunt"},
    # Keep the first teaching gate aligned with the prototype's authored
    # encounter.  The question, concept and difficulty still come from the
    # current state-owned question; this is presentation metadata only.
    "code_checkpoint": {"name": "The Count Keeper", "category": "loops"},
    "output_prediction": {"name": "The Output Oracle", "category": "prediction"},
    "refactoring": {"name": "The Shape Shifter", "category": "refactoring"},
}
_DUNGEON_MOB_PHASES = ("I", "II", "III", "IV")

PUBLIC_ACTORS = frozenset({"player", "pyr"})
SYSTEM_ACTOR = "system"


class StateApplyRequest(BaseModel):
    """HTTP command envelope; system actions are never accepted over HTTP."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=80)
    actor: Literal["player", "pyr"]
    payload: dict[str, Any] = Field(default_factory=dict)


class StateSyncApplyRequest(BaseModel):
    """Validated cloud projection applied to the local cache.

    The browser never sends a full progress snapshot.  This envelope is a
    deliberately small allowlisted projection plus the local revision it read
    so a concurrent local mutation fails closed instead of being overwritten.
    """

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=0)
    cloud_revision: int = Field(ge=0)
    projection: dict[str, Any] = Field(default_factory=dict)


class StateCommandError(Exception):
    """A safe, user-facing validation or state error."""

    def __init__(self, detail: str, status_code: int = 422):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class Mutation:
    changed: bool
    result: dict[str, Any]
    event: dict[str, Any] | None = None


@dataclass(frozen=True)
class ActionDefinition:
    actors: frozenset[str]
    internal: bool = False


# Public actions are the minimum surface needed by the current single-player
# Forge. Internal actions are callable only by future trusted game code through
# ``apply_internal``; the HTTP route and CLI reject them.
ACTION_DEFINITIONS: dict[str, ActionDefinition] = {
    "homestead_purchase": ActionDefinition(frozenset({"player"})),
    "homestead_equip": ActionDefinition(frozenset({"player"})),
    "campaign_market_purchase": ActionDefinition(frozenset({"player"})),
    "homestead_room_upgrade": ActionDefinition(frozenset({"player"})),
    "home_room_purchase": ActionDefinition(frozenset({"player"})),
    "homestead_action": ActionDefinition(frozenset({"player"})),
    "boss_start": ActionDefinition(frozenset({"player"})),
    "boss_retreat": ActionDefinition(frozenset({"player"})),
    "equip_equipment": ActionDefinition(frozenset({"player"})),
    "set_avatar": ActionDefinition(frozenset({"player"})),
    "select_campaign": ActionDefinition(frozenset({"player"})),
    "hunter_spend_point": ActionDefinition(frozenset({"player"})),
    "record_learning_event": ActionDefinition(frozenset({"pyr"})),
    "record_reference_mode": ActionDefinition(frozenset({"pyr"})),
    "record_pyr_assist": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_code_activity": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "award_learning_reward": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "player_hp_change": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_achievement": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_battle_objective": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_equipment_unlock": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "complete_mob": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_boss_requirement": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_boss_clear": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_battle_miss": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "reconcile_legacy_progress": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_codex_note": ActionDefinition(frozenset({"player"})),
    "practice_session_started": ActionDefinition(frozenset({"player"})),
    "practice_record_attempt": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "dungeon_start_run": ActionDefinition(frozenset({"player"})),
    "dungeon_choose_room": ActionDefinition(frozenset({"player"})),
    "dungeon_save_editor": ActionDefinition(frozenset({"player"})),
    "dungeon_issue_question": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "dungeon_record_verdict": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "dungeon_record_death": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "dungeon_use_rest": ActionDefinition(frozenset({"player"})),
    "dungeon_camp_action": ActionDefinition(frozenset({"player"})),
    "dungeon_reveal_risk": ActionDefinition(frozenset({"player"})),
    "dungeon_enter_risk": ActionDefinition(frozenset({"player"})),
    "dungeon_market_purchase": ActionDefinition(frozenset({"player"})),
    "dungeon_equip_item": ActionDefinition(frozenset({"player"})),
    "dungeon_apply_oil": ActionDefinition(frozenset({"player"})),
    "dungeon_travel": ActionDefinition(frozenset({"player"})),
    "dungeon_reroll_question": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "hunter_craft_oil": ActionDefinition(frozenset({"player"})),
    "hunter_upgrade_kit": ActionDefinition(frozenset({"player"})),
    "armory_equip": ActionDefinition(frozenset({"player"})),
    "armory_unequip": ActionDefinition(frozenset({"player"})),
    "armory_use": ActionDefinition(frozenset({"player"})),
    "armory_buy": ActionDefinition(frozenset({"player"})),
    "campaign_extend": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "hunter_identify_start": ActionDefinition(frozenset({"player"})),
    "hunter_identify_answer": ActionDefinition(frozenset({"player"})),
    "dungeon_leave_room": ActionDefinition(frozenset({"player"})),
    "dungeon_finish_run": ActionDefinition(frozenset({"player"})),
    "dungeon_reset_run": ActionDefinition(frozenset({"player"})),
}

PUBLIC_ACTIONS = frozenset(action for action, definition in ACTION_DEFINITIONS.items() if not definition.internal)


# These are deliberately generic objective labels. Their values are the only
# Impact values the local game authority may apply; callers cannot supply an
# arbitrary reward or hidden question text.
ENCOUNTER_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "max_resolve": 4,
        "objectives": {
            "table_setup": {"impact": 2, "question_type": "prediction", "label": "Set up the table", "brief": "Identify the state the program must remember before the first turn."},
            "state_explanation": {"impact": 2, "question_type": "explanation", "label": "Explain the state", "brief": "Explain how the chosen state values change during a turn."},
        },
    },
    {
        "max_resolve": 6,
        "objectives": {
            "hand_model": {"impact": 3, "question_type": "code_checkpoint", "label": "Model the hand", "brief": "Show how a hand or deck can be represented without copying a project answer."},
            "deal_reasoning": {"impact": 3, "question_type": "explanation", "label": "Reason about a deal", "brief": "Explain why the next card selection belongs in the current state flow."},
        },
    },
    {
        "max_resolve": 9,
        "objectives": {
            "trace_total": {"impact": 3, "question_type": "prediction", "label": "Trace the total", "brief": "Predict how a running total changes across the next repeated values."},
            "running_total": {"impact": 3, "question_type": "code_checkpoint", "label": "Update the total", "brief": "Demonstrate the checkpoint that updates a running total safely."},
            "loop_explanation": {"impact": 3, "question_type": "explanation", "label": "Explain the loop", "brief": "Explain the loop state and when one iteration ends."},
        },
    },
    {
        "max_resolve": 8,
        "objectives": {
            "choice_flow": {"impact": 4, "question_type": "code_checkpoint", "label": "Build the choice flow", "brief": "Show the player-choice path while keeping the loop state explicit."},
            "stop_condition": {"impact": 4, "question_type": "bug_diagnosis", "label": "Find the stop condition", "brief": "Diagnose what should end the repeated choice flow and why."},
        },
    },
    {
        "max_resolve": 7,
        "objectives": {
            "outcome_classification": {"impact": 3, "question_type": "prediction", "label": "Classify an outcome", "brief": "Predict which outcome a changed total and condition should produce."},
            "branch_reasoning": {"impact": 4, "question_type": "explanation", "label": "Explain the branch", "brief": "Explain why the selected branch handles this outcome."},
        },
    },
    {
        "max_resolve": 8,
        "objectives": {
            "function_boundary": {"impact": 4, "question_type": "code_checkpoint", "label": "Choose a function boundary", "brief": "Show one focused function boundary and the data it should receive."},
            "return_reasoning": {"impact": 4, "question_type": "explanation", "label": "Explain the return", "brief": "Explain what the function returns and how the caller uses it."},
        },
    },
    {
        "max_resolve": 7,
        "objectives": {
            "compare_states": {"impact": 3, "question_type": "prediction", "label": "Compare states", "brief": "Predict which final state should win from the available values."},
            "winner_justification": {"impact": 4, "question_type": "explanation", "label": "Justify the winner", "brief": "Give a concise reason for the winner without relying on copied project logic."},
        },
    },
    {
        "max_resolve": 8,
        "objectives": {
            "reset_state": {"impact": 4, "question_type": "code_checkpoint", "label": "Reset the state", "brief": "Show how a finished round can reset without leaking the previous state."},
            "loop_explanation": {"impact": 4, "question_type": "explanation", "label": "Explain the reset loop", "brief": "Explain the order of operations when the next round begins."},
        },
    },
)


def canonical_battle_raw_damage(mob_index: int) -> int:
    """Return the server-owned counterattack damage for an encounter index."""

    try:
        index = max(0, int(mob_index))
    except (TypeError, ValueError):
        index = 0
    return BATTLE_RAW_DAMAGE_BY_MOB[min(index, len(BATTLE_RAW_DAMAGE_BY_MOB) - 1)]

MOB_REWARDS: tuple[tuple[int, int], ...] = (
    (25, 10),
    (25, 10),
    (30, 15),
    (30, 15),
    (35, 20),
    (40, 25),
    (45, 30),
    (50, 35),
)

# Bosses are fought mostly in code, and each campaign sets its own gauntlet
# (boss_gauntlet in its story file): an early boss might be one coding task
# and two questions, a late one five coding phases and an interview. These are
# every phase a gauntlet may use. The ids "explanation" and "interview" are
# kept so older saves stay valid.
BOSS_REQUIREMENTS: tuple[str, ...] = (
    "required_behavior",
    "explanation",
    "edge_cases",
    "twist_2",
    "twist_3",
    "twist_4",
    "read_2",
    "interview",
)
DEFAULT_BOSS_GAUNTLET: tuple[str, ...] = ("required_behavior", "explanation", "edge_cases", "interview")
# Boss goals answered by clicking an option about the player's own code.
BOSS_CHOICE_TYPES = frozenset({"snippet_check", "code_interview"})

# Boss validation is deliberately presentation-safe: the projection exposes
# only which bounded gate phases have been verified, never the provider's
# hidden interview prompt or answer key.
BOSS_PHASE_LABELS: dict[str, str] = {
    "required_behavior": "Required behaviour",
    "explanation": "Read your code",
    "edge_cases": "The boss twist",
    "twist_2": "The boss's second phase",
    "twist_3": "The boss's third phase",
    "twist_4": "The boss's final phase",
    "read_2": "Read your code again",
    "interview": "Code interview",
}

# State-owned encounter rules for the small mechanics panel in Forge.  These
# are descriptive outcomes, not a second provider answer key: the gateway
# still decides whether a submission is valid and how much canonical Impact it
# applies.  Only the current encounter receives this projection.
ENCOUNTER_MECHANICS: tuple[dict[str, str], ...] = (
    {
        "id": "execution_gate",
        "label": "Clean run",
        "detail": "A syntax or startup error blocks the objective from dealing Resolve damage.",
        "outcome": "No damage until the file runs.",
    },
    {
        "id": "bug_feedback",
        "label": "Bug feedback",
        "detail": "Runtime or test failures expose the broken path so PYR can coach the next attempt.",
        "outcome": "The verdict stays state-owned.",
    },
    {
        "id": "verified_goal",
        "label": "Verified goal",
        "detail": "A correct current quest applies the canonical Impact shown beside it.",
        "outcome": "Resolve drops; the next quest appears.",
    },
)


def campaign_special_mechanic(project: Mapping[str, Any], mob_name: str | None = None) -> dict[str, str] | None:
    """Look up the small, authored beginner combat reward, never client input."""
    if project.get("branch") != "00-lantern-vale":
        return None
    story = load_campaign_bounties().get("00-lantern-vale", {})
    source = (campaign_contract("00-lantern-vale", mob_name) or {}).get("mechanic") if mob_name else story.get("boss_mechanic")
    if not isinstance(source, Mapping) or source.get("reward") not in {"guard", "double_guard", "shelter", "focus", "heal"}:
        return None
    if not all(isinstance(source.get(key), str) and source[key] for key in ("label", "detail", "trigger")):
        return None
    return {key: str(source[key]) for key in ("label", "detail", "trigger", "reward")}


def apply_campaign_mechanic(progress: dict[str, Any], encounter: dict[str, Any] | None, mechanic: Mapping[str, str]) -> dict[str, int]:
    """Grant a bounded one-time reward when its verified objective is recorded."""
    result = {"guards": 0, "coins": 0, "healed": 0}
    reward = mechanic["reward"]
    player = progress.setdefault("player", {})
    if reward in {"guard", "double_guard"} and encounter is not None:
        before = max(0, int(encounter.get("guards", 0)))
        encounter["guards"] = min(3, before + (2 if reward == "double_guard" else 1))
        result["guards"] = encounter["guards"] - before
    if reward == "heal":
        hp, maximum = max(0, int(player.get("hp", 0))), max(0, int(player.get("max_hp", 0)))
        result["healed"] = max(0, min(8, maximum - hp))
        player["hp"] = hp + result["healed"]
    return result

# Boss metadata is a presentation-safe projection, not a second answer key.
# The current goal is always the first unverified requirement; each verified
# goal applies its canonical damage to the boss Resolve bar.  PYR may explain
# or adjudicate the goal, but it cannot choose the damage, reward, or a future
# prompt from the browser.
BOSS_REQUIREMENT_SPECS: dict[str, dict[str, Any]] = {
    "required_behavior": {
        "label": "Required behaviour",
        "question_type": "code_checkpoint",
        "impact": 5,
        "brief": "Show the finished program working in your active Forge file.",
    },
    "explanation": {
        "label": "Read your code",
        "question_type": "snippet_check",
        "impact": 2,
        "brief": "A quick question about a snippet from your own file. Click your answer.",
    },
    "edge_cases": {
        "label": "The boss twist",
        "question_type": "code_checkpoint",
        "impact": 5,
        "brief": "The boss changes the rules. Extend your program to handle the twist.",
    },
    "twist_2": {
        "label": "The boss's second phase",
        "question_type": "code_checkpoint",
        "impact": 5,
        "brief": "The boss changes again. Extend your program for its next phase.",
    },
    "twist_3": {
        "label": "The boss's third phase",
        "question_type": "code_checkpoint",
        "impact": 5,
        "brief": "The boss changes again. Extend your program for its next phase.",
    },
    "twist_4": {
        "label": "The boss's final phase",
        "question_type": "code_checkpoint",
        "impact": 5,
        "brief": "The boss's last form. Extend your program for its final phase.",
    },
    "read_2": {
        "label": "Read your code again",
        "question_type": "snippet_check",
        "impact": 2,
        "brief": "Another quick question about a different snippet of your own file. Click your answer.",
    },
    "interview": {
        "label": "Code interview",
        "question_type": "code_interview",
        "impact": 3,
        "brief": "Explain code you wrote: what a snippet from your file does, why, and what changes if an input does. Click your answers.",
    },
}
BOSS_REWARD_ENVELOPE: dict[str, Any] = {
    "xp": 100,
    "coins": 0,
    "authorized_items": [],
}

# The library is deliberately generic.  These pages teach transferable Python
# ideas without carrying a project answer key or a future encounter prompt.
# Encounter-specific observations remain in the canonical Codex records.
CODEX_CONCEPT_PAGES: tuple[dict[str, Any], ...] = (
    {
        "id": "variables",
        "title": "Variables & program state",
        "aliases": ("variable", "variables", "program state", "state"),
        "definition": "A variable gives a meaningful name to a value so a program can read or update its state.",
        "examples": ("score = 0\nscore = score + 1", "name = input('Name: ')\nprint(name)"),
        "when_to_use": "Use variables when a value needs a clear name so later lines can read it, update it or explain its current state.",
        "question_types": ("prediction", "explanation", "code_checkpoint"),
        "common_mistakes": ("Changing a different variable than the one the next line reads.", "Using a name before assigning its first value."),
        "mistake_examples": ("total = 0\ncount = count + 1  # changes a different name", "print(score)  # score has not been assigned yet"),
        "check_prompt": "Can you explain what value changes after each assignment?",
    },
    {
        "id": "input-output",
        "title": "Input and output",
        "aliases": ("input", "output", "input/output"),
        "definition": "Input brings data into a program; output communicates a result to a person or another system.",
        "examples": ("city = input('City: ')\nprint(f'You chose {city}')",),
        "when_to_use": "Use input and output when a program needs to receive a value, transform it, and make the result visible or usable elsewhere.",
        "question_types": ("prediction", "explanation"),
        "common_mistakes": ("Treating input text as a number without converting it.", "Printing a value before the program has received it."),
        "mistake_examples": ("age = input('Age: ')\nprint(age + 1)  # input returns text", "print(answer)\nanswer = input('Answer: ')  # read first"),
        "check_prompt": "What enters the program, and what leaves it?",
    },
    {
        "id": "lists",
        "title": "Lists & collections",
        "aliases": ("list", "lists", "collection", "random selection"),
        "definition": "A list keeps an ordered, changeable sequence of values that can be indexed or iterated.",
        "examples": ("colors = ['red', 'blue']\ncolors.append('gold')\nprint(colors[0])",),
        "when_to_use": "Use a list when order matters and you need to keep, inspect or iterate over a changeable collection of related values.",
        "question_types": ("code_checkpoint", "prediction", "explanation"),
        "common_mistakes": ("Forgetting that list indexes start at zero.", "Changing a list while assuming its length stayed the same."),
        "mistake_examples": ("colors = ['red', 'blue']\nprint(colors[1])  # the first item is index 0", "items = ['a', 'b']\nitems.append('c')\nprint(len(items))  # now 3"),
        "check_prompt": "Which value is at each index before and after the update?",
    },
    {
        "id": "loops",
        "title": "Loops & totals",
        "aliases": ("loop", "loops", "iteration", "totals", "running total"),
        "definition": "A loop repeats a block while walking through values or while a condition remains true.",
        "examples": ("total = 0\nfor value in [2, 4, 6]:\n    total += value",),
        "when_to_use": "Use a loop when the same rule must run for each value or until a clearly changing condition says the work is complete.",
        "question_types": ("prediction", "code_checkpoint", "explanation"),
        "common_mistakes": ("Putting the update outside the loop by accident.", "Using a condition that never changes in a while loop."),
        "mistake_examples": ("total = 0\nfor value in [2, 4, 6]:\n    pass\ntotal += value  # update happens once", "running = True\nwhile running:\n    print('again')  # running never changes"),
        "check_prompt": "What changes on every iteration, and what makes the loop stop?",
    },
    {
        "id": "conditionals",
        "title": "Conditionals & branches",
        "aliases": ("conditional", "conditionals", "branch", "branches"),
        "definition": "A conditional chooses which code path runs by evaluating a Boolean expression.",
        "examples": ("if temperature > 30:\n    label = 'hot'\nelse:\n    label = 'mild'",),
        "when_to_use": "Use a conditional when different inputs need different paths, especially at boundaries where the normal and fallback cases must both be explicit.",
        "question_types": ("prediction", "bug_diagnosis", "explanation"),
        "common_mistakes": ("Comparing a value with assignment syntax.", "Leaving an important branch without a defined result."),
        "mistake_examples": ("if score = 10:\n    print('ten')  # comparison needs ==", "if ready:\n    message = 'go'\nprint(message)  # no result when ready is false"),
        "check_prompt": "Which branch runs for one normal case and one boundary case?",
    },
    {
        "id": "functions",
        "title": "Functions & boundaries",
        "aliases": ("function", "functions", "return", "function boundary"),
        "definition": "A function packages a named operation with inputs and an explicit result or side effect.",
        "examples": ("def double(value):\n    return value * 2\n\nanswer = double(4)",),
        "when_to_use": "Use a function when a named piece of logic has a clear input/output boundary that you want to reuse or test separately.",
        "question_types": ("code_checkpoint", "explanation", "bug_diagnosis"),
        "common_mistakes": ("Defining parameters that the caller never supplies.", "Printing inside a function when the caller needs a returned value."),
        "mistake_examples": ("def add(a, b):\n    return a + b\nadd(2)  # b is missing", "def double(value):\n    print(value * 2)\nresult = double(4)  # result is None"),
        "check_prompt": "What goes in, what comes out, and where is the boundary?",
    },
    {
        "id": "dictionaries",
        "title": "Dictionaries & lookup",
        "aliases": ("dictionary", "dictionaries", "mapping", "lookup"),
        "definition": "A dictionary maps unique keys to values so related data can be looked up by name.",
        "examples": ("prices = {'tea': 3, 'cake': 5}\nprint(prices.get('tea', 0))",),
        "when_to_use": "Use a dictionary when each value is best found by a meaningful key rather than by a numeric position in a sequence.",
        "question_types": ("code_checkpoint", "prediction", "explanation"),
        "common_mistakes": ("Looking up a key that is not present without a fallback.", "Confusing a key with the value stored under it."),
        "mistake_examples": ("prices = {'tea': 3}\nprint(prices['cake'])  # key may be missing", "prices = {'tea': 3}\nprint(prices[3])  # 3 is a value, not the key"),
        "check_prompt": "Which key is being looked up, and what should happen if it is missing?",
    },
    {
        "id": "control-flow",
        "title": "Control flow & reset",
        "aliases": ("control flow", "input loops", "reset state", "program loops"),
        "definition": "Control flow combines sequence, branches, loops and state updates; reset logic returns state to a known boundary.",
        "examples": ("running = True\nwhile running:\n    running = False",),
        "when_to_use": "Use explicit control-flow boundaries when a program must move through steps, choose a branch, repeat work, and then return to a known state.",
        "question_types": ("code_checkpoint", "bug_diagnosis", "explanation"),
        "common_mistakes": ("Resetting state too early or in the wrong branch.", "Adding a loop without a reachable exit condition."),
        "mistake_examples": ("score = 0\nif reset:\n    score = 0\nscore += 1  # reset happened before the update", "while True:\n    print('stuck')  # no reachable break"),
        "check_prompt": "Where does the program start, branch, repeat, and return to a known state?",
    },
    {
        "id": "random-selection",
        "title": "Random selection",
        "aliases": ("random selection", "random"),
        "definition": "Random selection chooses a value from a collection; keeping the chosen value visible makes the result explainable and testable.",
        "examples": ("import random\nchoice = random.choice(['left', 'right'])",),
        "when_to_use": "Use random selection when the program should choose from several valid outcomes; keep the choice observable so behavior can still be explained and tested.",
        "question_types": ("prediction", "explanation", "code_checkpoint"),
        "common_mistakes": ("Expecting a random result to be repeatable without controlling the seed.", "Hiding the chosen value so the result cannot be explained or tested."),
        "mistake_examples": ("import random\n# tests expect the same result without random.seed(1)", "choice = random.choice(['left', 'right'])\n# no print or return means the choice is hidden"),
        "check_prompt": "What values are possible, and how could you make one result observable?",
    },
    {
        "id": "strings",
        "title": "Strings & text",
        "aliases": ("string handling", "strings", "text processing", "parsing user text", "string formatting"),
        "definition": "A string is text; methods like strip, lower, split and f-strings clean it, break it apart and build it back up.",
        "examples": ("raw = '  Rock '\nmove = raw.strip().lower()", "parts = '3 + 4'.split()\nprint(f'{parts[0]} plus {parts[2]}')"),
        "when_to_use": "Use string methods whenever text comes from a person or a file: clean it before you compare it, and split it before you read pieces of it.",
        "question_types": ("prediction", "code_checkpoint", "bug_diagnosis"),
        "common_mistakes": ("Comparing raw input that still has spaces or capitals.", "Checking 'hi' in text and matching words like 'this'."),
        "mistake_examples": ("move = input('Move: ')\nif move == 'rock':  # ' Rock' never matches", "if 'hi' in 'this one':\n    print('greeting')  # substring, not a word"),
        "check_prompt": "What exactly is in the string before and after each method?",
    },
    {
        "id": "exceptions",
        "title": "Errors & exceptions",
        "aliases": ("error handling", "exceptions", "exception", "try/except"),
        "definition": "An exception is Python reporting that something went wrong; try and except let the program recover instead of crashing.",
        "examples": ("try:\n    bet = int(text)\nexcept ValueError:\n    print('Numbers only')",),
        "when_to_use": "Use try/except around the one line that can fail for reasons outside your control, such as converting input or opening a file, and catch the specific error.",
        "question_types": ("bug_diagnosis", "prediction", "code_checkpoint"),
        "common_mistakes": ("Wrapping a whole program in a bare except that hides real bugs.", "Catching the error but carrying on with a value that was never set."),
        "mistake_examples": ("try:\n    play_game()\nexcept:\n    pass  # every bug disappears silently", "try:\n    bet = int(text)\nexcept ValueError:\n    print('bad')\nprint(bet * 2)  # bet may not exist"),
        "check_prompt": "Which line can fail, which error does it raise, and what happens next?",
    },
    {
        "id": "files-json",
        "title": "Files & JSON",
        "aliases": ("json", "saving and loading", "save and load", "files", "file i/o"),
        "definition": "Files keep data after the program ends; JSON turns dictionaries and lists into text that can be saved and read back.",
        "examples": ("import json\nwith open('save.json', 'w') as file:\n    json.dump({'gold': 10}, file)", "with open('save.json') as file:\n    data = json.load(file)"),
        "when_to_use": "Use files with JSON when something must survive a restart: a save game, settings, a record or a log.",
        "question_types": ("code_checkpoint", "bug_diagnosis", "explanation"),
        "common_mistakes": ("Assuming the file always exists or is never corrupted.", "Trying to save data JSON cannot store, such as sets or objects."),
        "mistake_examples": ("data = json.load(open('save.json'))  # crashes on the first run", "json.dumps({'seen': {1, 2}})  # a set is not JSON"),
        "check_prompt": "What is written, what is read back, and what if the file is missing?",
    },
    {
        "id": "sets",
        "title": "Sets & uniqueness",
        "aliases": ("sets", "unique values", "duplicates", "membership"),
        "definition": "A set holds unique values with no order, and checks whether something is inside it very quickly.",
        "examples": ("seen = set()\nseen.add((2, 3))\nprint((2, 3) in seen)",),
        "when_to_use": "Use a set when you only care whether something is present, such as visited rooms, or when duplicates must disappear.",
        "question_types": ("prediction", "code_checkpoint", "explanation"),
        "common_mistakes": ("Expecting a set to keep order or allow indexing.", "Writing {} for an empty set, which makes a dictionary."),
        "mistake_examples": ("tags = {'b', 'a'}\nprint(tags[0])  # sets have no index", "seen = {}\nseen.add(1)  # {} is an empty dict"),
        "check_prompt": "Which values are in the set, and which duplicates vanished?",
    },
    {
        "id": "grids",
        "title": "Grids & nested lists",
        "aliases": ("nested lists", "grid", "grids", "game board", "2d map"),
        "definition": "A grid is a list of rows, each row a list; grid[row][column] reaches one cell.",
        "examples": ("grid = [['.'] * 7 for _ in range(6)]\ngrid[5][3] = 'X'",),
        "when_to_use": "Use a grid for anything laid out in rows and columns: boards, maps, mazes and tables.",
        "question_types": ("code_checkpoint", "prediction", "bug_diagnosis"),
        "common_mistakes": ("Building rows with [[0] * 7] * 6, so every row is the same list.", "Swapping row and column, or walking off the edge."),
        "mistake_examples": ("grid = [[0] * 3] * 2\ngrid[0][0] = 9  # changes both rows", "print(grid[row][-1])  # -1 wraps to the last column"),
        "check_prompt": "Which row and which column does each index pick?",
    },
    {
        "id": "sorting",
        "title": "Sorting & ranking",
        "aliases": ("sorting", "sorted", "ranking", "league table", "best first"),
        "definition": "Sorting puts values in order; a key function decides what to compare, and a tuple key breaks ties.",
        "examples": ("table.sort(key=lambda club: (club['points'], club['gd']), reverse=True)",),
        "when_to_use": "Use sorted() or .sort() with a key whenever results must be ranked: tables, leaderboards, best moves.",
        "question_types": ("prediction", "code_checkpoint", "bug_diagnosis"),
        "common_mistakes": ("Storing the result of .sort(), which is None.", "Sorting by one key when ties need a second."),
        "mistake_examples": ("ranked = scores.sort()\nprint(ranked)  # None", "clubs.sort(key=lambda c: c['points'])  # ties left to chance"),
        "check_prompt": "What is compared, in which direction, and who wins a tie?",
    },
    {
        "id": "references",
        "title": "References & copies",
        "aliases": ("references", "copies", "aliasing", "copy of the board", "shallow copy"),
        "definition": "Assigning a list or dictionary to a new name does not copy it; both names point at the same object until you make a copy.",
        "examples": ("start = {'hp': 30}\nfighter = dict(start)  # a real copy",),
        "when_to_use": "Make a copy whenever you want to change something without touching the original: templates, trial moves, fresh rounds.",
        "question_types": ("bug_diagnosis", "prediction", "explanation"),
        "common_mistakes": ("Changing a 'copy' that is really the original.", "Copying the outer list while the inner lists are still shared."),
        "mistake_examples": ("enemy = TEMPLATE\nenemy['hp'] -= 5  # every future enemy is hurt", "trial = board.copy()\ntrial[0][0] = 'X'  # rows are still shared"),
        "check_prompt": "How many objects exist here, and how many names point at each?",
    },
    {
        "id": "classes",
        "title": "Classes & objects",
        "aliases": ("classes", "class", "objects", "methods"),
        "definition": "A class bundles data with the functions that act on it; each object made from it keeps its own data in self.",
        "examples": ("class Creature:\n    def __init__(self, name, hp):\n        self.name = name\n        self.hp = hp\n\n    def take_damage(self, amount):\n        self.hp = max(0, self.hp - amount)",),
        "when_to_use": "Use a class when the same kind of thing appears many times and its data and behaviour belong together.",
        "question_types": ("code_checkpoint", "explanation", "prediction"),
        "common_mistakes": ("Forgetting self, so a value is lost when the method ends.", "Putting a list at class level, so every object shares it."),
        "mistake_examples": ("def heal(self):\n    hp = self.max_hp  # sets a local, not self.hp", "class Team:\n    members = []  # shared by every Team"),
        "check_prompt": "Which object owns each value, and which method changes it?",
    },
    {
        "id": "testing",
        "title": "Testing & checks",
        "aliases": ("testing", "tests", "asserts", "assert checks", "evaluation"),
        "definition": "A test runs your code on a known case and checks the result, so a broken change is caught at once.",
        "examples": ("assert score_hand([11, 11, 9]) == 21\nassert score_hand([10, 7]) == 17",),
        "when_to_use": "Write a test for every rule you just made work, and for every bug you just fixed, so it can never come back unnoticed.",
        "question_types": ("code_checkpoint", "bug_diagnosis", "explanation"),
        "common_mistakes": ("Testing only the easy case.", "Tests that depend on randomness without fixing the seed."),
        "mistake_examples": ("def double(n):\n    return n + 2\nassert double(2) == 4  # passes by luck", "assert roll() == 4  # random, so it fails sometimes"),
        "check_prompt": "Which case would catch this bug, and does a test cover it?",
    },
    {
        "id": "callbacks",
        "title": "Functions as values",
        "aliases": ("callbacks", "functions as players", "strategy function", "function interface", "brain socket"),
        "definition": "A function is a value: you can store it, pass it to another function and call it later, so behaviour can be swapped like data.",
        "examples": ("def play(agent, board):\n    return agent(board)\n\nplay(random_agent, board)",),
        "when_to_use": "Pass a function in when the same loop should work with different behaviours: humans and bots, brains, sort keys.",
        "question_types": ("code_checkpoint", "explanation", "prediction"),
        "common_mistakes": ("Passing agent() instead of agent, which calls it too early.", "Giving swappable functions different inputs, so they cannot be swapped."),
        "mistake_examples": ("play_game(random_agent(), greedy_agent)  # passes a column, not a player", "def human(board): ...\ndef bot(board, piece): ...  # different shapes"),
        "check_prompt": "Is the function being passed, or called and its result passed?",
    },
    {
        "id": "agents",
        "title": "Agents & tools",
        "aliases": ("agents", "agent", "tools", "act-observe", "tool registry"),
        "definition": "An agent is a loop: a brain decides to answer or to use a tool, the program runs the tool, and the result goes back to the brain.",
        "examples": ("while steps < 5:\n    decision = brain(history)\n    if 'reply' in decision:\n        break\n    result = run_tool(decision['tool'], decision['args'])\n    history.append({'role': 'tool', 'content': result})\n    steps += 1",),
        "when_to_use": "Use an agent loop when a program must take several actions to reach a goal and decide each next step from what happened.",
        "question_types": ("code_checkpoint", "explanation", "bug_diagnosis"),
        "common_mistakes": ("A loop with no step limit, so a confused brain runs forever.", "Letting dangerous tools run without asking first."),
        "mistake_examples": ("while True:\n    act(brain(history))  # nothing stops it", "run_tool('delete_note', args)  # no confirmation"),
        "check_prompt": "What does the brain see, what can it do, and what stops it?",
    },
    {
        "id": "recursion",
        "title": "Recursion",
        "aliases": ("recursion", "recursive", "minimax", "base case"),
        "definition": "A recursive function solves a problem by calling itself on a smaller version of it, until a base case answers directly.",
        "examples": ("def total(n):\n    if n == 0:\n        return 0\n    return n + total(n - 1)",),
        "when_to_use": "Use recursion when a problem contains smaller copies of itself: game trees, nested data, mazes.",
        "question_types": ("prediction", "code_checkpoint", "bug_diagnosis"),
        "common_mistakes": ("No base case, or one that is never reached.", "Forgetting to return the recursive result."),
        "mistake_examples": ("def count(n):\n    return count(n - 1)  # never stops", "def total(n):\n    if n == 0:\n        return 0\n    n + total(n - 1)  # result thrown away"),
        "check_prompt": "What is the base case, and does every call move towards it?",
    },
    {
        "id": "search",
        "title": "Search & pathfinding",
        "aliases": ("search", "pathfinding", "breadth-first", "game tree", "alpha-beta"),
        "definition": "Search explores possibilities in an order: breadth-first finds the shortest path, and game-tree search looks ahead at moves and replies.",
        "examples": ("queue = [start]\nseen = {start}\nwhile queue:\n    node = queue.pop(0)\n    for nxt in neighbours(node):\n        if nxt not in seen:\n            seen.add(nxt)\n            queue.append(nxt)",),
        "when_to_use": "Use search when the answer is somewhere among many possibilities: a path through a maze, the best move, the right suspect.",
        "question_types": ("code_checkpoint", "prediction", "explanation"),
        "common_mistakes": ("Forgetting a seen set, so the search loops forever.", "Marking a node seen only when it is popped, so it is queued twice."),
        "mistake_examples": ("while queue:\n    node = queue.pop(0)\n    queue.extend(neighbours(node))  # revisits forever", "if node not in seen:\n    seen.add(node)  # too late, already queued twice"),
        "check_prompt": "In what order are possibilities explored, and what stops repeats?",
    },
    {
        "id": "simulation",
        "title": "Simulation & statistics",
        "aliases": ("simulation", "simulate", "statistics", "expected value", "monte carlo"),
        "definition": "A simulation runs a random process many times and counts what happens, turning chance into measurable rates.",
        "examples": ("wins = sum(1 for _ in range(10_000) if play_round() == 'win')\nprint(wins / 10_000)",),
        "when_to_use": "Simulate when the maths is hard or you want to check it: house edges, win rates, balance between classes.",
        "question_types": ("code_checkpoint", "explanation", "prediction"),
        "common_mistakes": ("Judging from a handful of runs.", "Leaving printing on inside a ten-thousand-run loop."),
        "mistake_examples": ("rate = sum(play() for _ in range(10)) / 10  # far too few", "for _ in range(10_000):\n    play_round(verbose=True)  # floods the screen"),
        "check_prompt": "How many runs, what is counted, and how much would a second run differ?",
    },
)

# Add approachable, transferable patterns to the existing Tutor pages.
CODEX_CONCEPT_PAGES = tuple(
    {**page, "definition": page["definition"] + " " + BEGINNER_CODEX[page["id"]][0],
     "examples": (*page["examples"], BEGINNER_CODEX[page["id"]][1])}
    if page["id"] in BEGINNER_CODEX else page
    for page in CODEX_CONCEPT_PAGES
)

SYNC_PLAYER_FIELDS = frozenset(
    {
        "name",
        "title",
        "rank",
        "level",
        "xp",
        "xp_next",
        "lifetime_xp",
        "hp",
        "max_hp",
        "coins",
        "potions",
    }
)
SYNC_EQUIPMENT_FIELDS = frozenset({"armor", "trinket", "title", "owned_armor", "owned_trinkets", "avatar"})
SYNC_EQUIPMENT_LIST_FIELDS = frozenset({"owned_armor", "owned_trinkets"})
SYNC_COMPANION_FIELDS = frozenset({"name", "form", "level", "bond", "next_form", "next_form_requirement", "energy", "max_energy", "fed_count", "training_count"})
SYNC_HOMESTEAD_FIELDS = frozenset({"name", "owned_cosmetics", "equipped", "room_upgrades", "room_levels", "upgrade_tokens", "upgrade_effects", "market_purchases"})
SYNC_HOMESTEAD_EQUIPPED_FIELDS = frozenset({"theme", "cursor", "hud", "terminal"})
SYNC_CAMPAIGN_FIELDS = frozenset(
    {
        "learning_state",
        "streak",
        "skills",
        "stats",
        "achievements",
        "goals",
        "projects",
        "current_quest",
        "codex",
        "dungeon_run",
        "dungeon_leaderboard",
        "practice_sessions",
    }
)


def _is_safe_device_id(value: object) -> bool:
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    return bool(candidate) and len(candidate) <= 80 and not any(
        character.isspace() or character in "/\\:\u0000" for character in candidate
    )


def opaque_device_id() -> str:
    """Return an opaque local label without exposing a filesystem path."""

    candidate = os.getenv("QUESTLAB_DEVICE_ID", "local-forge").strip()
    return candidate if _is_safe_device_id(candidate) else "local-forge"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Hunter progression: signs (concepts) and stats ──────────────────────
# Signs level by use: every verified correct answer gives its concept's sign
# XP (more for a clean first try). A rank also needs an achievement gate, so
# drills alone can't reach mastery. Stats grow from the kind of question
# answered. None of this ever skips or shortens a question (docs/
# GAME_DIRECTION.md, "the iron rule"). Local progression for now: it is not
# part of the cloud projection, which would need a Supabase migration.
HUNTER_SIGN_KEYWORDS: dict[str, tuple[str, ...]] = {
    "variables": ("variable", "variables", "assignment", "assign"),
    "input-output": ("input", "output", "print"),
    "conditionals": ("conditional", "conditionals", "if", "elif", "else", "branch", "branches", "boolean"),
    "lists": ("list", "lists", "collection", "collections", "index", "indexing"),
    "dictionaries": ("dictionary", "dictionaries", "dict", "dicts", "lookup", "key", "keys"),
    "random-selection": ("random", "randomness", "probability", "shuffle"),
    "loops": ("loop", "loops", "iteration", "iterate", "for", "while", "totals"),
    "functions": ("function", "functions", "return", "def", "parameter", "parameters"),
    "control-flow": ("control flow", "control", "reset", "break", "continue"),
    "strings": ("string", "strings", "text", "strip", "split", "parse", "parsing", "formatting"),
    "exceptions": ("exception", "exceptions", "error handling", "try", "except", "traceback"),
    "files-json": ("file", "files", "json", "save", "saving", "load", "loading"),
    "sets": ("sets", "unique", "duplicate", "duplicates", "membership"),
    "grids": ("grid", "grids", "board", "nested list", "nested lists", "maze", "matrix"),
    "sorting": ("sort", "sorting", "sorted", "ranking", "ranked"),
    "references": ("reference", "references", "copy", "copies", "alias", "aliasing", "mutable"),
    "classes": ("class", "classes", "object", "objects", "method", "methods", "self"),
    "testing": ("test", "tests", "testing", "assert", "asserts", "mock"),
    "callbacks": ("callback", "callbacks", "higher-order", "lambda", "first-class", "interface"),
    "agents": ("agent", "agents", "tool", "tools", "act-observe", "assistant"),
    "recursion": ("recursion", "recursive", "base case", "minimax"),
    "search": ("search", "searching", "bfs", "breadth-first", "pathfinding", "alpha-beta", "game tree"),
    "simulation": ("simulation", "simulate", "simulations", "statistics", "monte carlo", "expected value"),
}
HUNTER_SIGN_XP = {"clean": 3, "recovered": 1, "campaign_use": 5, "teachback": 2}
# Total sign XP needed to reach levels 1..10.
HUNTER_SIGN_LEVELS = (3, 8, 15, 24, 35, 48, 63, 80, 99, 120)
HUNTER_RANK_NAMES = ("Uninscribed", "Inscribed", "Honed", "Mastered")
HUNTER_HONED_CLEAN_CASTS = 10
HUNTER_DULL_DAYS = 7
HUNTER_STATS = ("strength", "insight", "focus", "vitality")
HUNTER_STAT_BY_TYPE = {
    # Writing and fixing code.
    "bug_hunt": "strength", "bug_diagnosis": "strength", "code_checkpoint": "strength", "refactoring": "strength",
    # Reading code.
    "code_trace": "insight", "prediction": "insight", "output_prediction": "insight",
    "multiple_choice": "insight", "true_false": "insight",
    # Explaining.
    "explanation": "focus", "short_explanation": "focus", "interview": "focus",
}
HUNTER_TEACHBACK_TYPES = frozenset({"explanation", "short_explanation", "interview"})
HUNTER_STAT_XP_PER_POINT = 10
HUNTER_SIGN_COUNTERS = ("xp", "clean_casts", "recovered", "tutor_passes", "dungeon_clean", "campaign_uses", "teachbacks")

# ── Dungeon fights (the iron rule) ───────────────────────────────────────
# A room with N questions always takes N correct answers. Resolve is the
# enemy's guard, separate from that progress: correct answers chip it and a
# break only helps (a free mistake, the mechanic interrupted, a few coins).
DUNGEON_FIGHT_QUESTIONS = {"encounter": 1, "elite": 3, "boss": 5}
DUNGEON_FIGHT_RESOLVE = {"encounter": 6, "elite": 8, "boss": 12}
DUNGEON_FIGHT_CHIP = {"encounter": 3, "elite": 4, "boss": 5}
DUNGEON_BREAK_COINS = 3
DUNGEON_SELF_DESTRUCT_BLAST = 15
DUNGEON_MECHANICS = {
    "elite": {
        "kind": "enrage",
        "label": "Enrage",
        "every": 2,
        "text": "Every 2 answers it works itself into a rage; while enraged its counterattacks hit twice as hard. A break calms it.",
    },
    "boss": {
        "kind": "self_destruct",
        "label": "Self-destruct",
        "every": 3,
        "text": f"It counts down to a self-destruct that blasts you for {DUNGEON_SELF_DESTRUCT_BLAST} HP, then starts again. A break interrupts the countdown.",
    },
}

# ── Delves and loot ──────────────────────────────────────────────────────
# A delve picks a Codex region; its fights draw from that region's signs,
# weighted to the weakest. Beasts drop parts into the run pack, which is
# banked at a camp or by ending the run, and lost on death. Loot never
# shortens a fight (the iron rule).
HUNTER_SIGN_CONCEPTS = {
    "variables": "variables",
    "input-output": "input and output",
    "conditionals": "conditionals",
    "lists": "lists",
    "dictionaries": "dictionaries",
    "random-selection": "random selection",
    "loops": "loops",
    "functions": "functions",
    "control-flow": "control flow",
    "strings": "strings",
    "exceptions": "exceptions",
    "files-json": "files and json",
    "sets": "sets",
    "grids": "grids",
    "sorting": "sorting",
    "references": "references and copies",
    "classes": "classes",
    "testing": "testing",
    "callbacks": "callbacks",
    "agents": "agents",
    "recursion": "recursion",
    "search": "search",
    "simulation": "simulation",
}
HUNTER_BEASTS = {
    "variables": {"beast": "The Nameless Wraith", "part": "wraith-ash", "part_name": "Wraith Ash"},
    "input-output": {"beast": "The String Mimic", "part": "mimic-scale", "part_name": "Mimic Scale"},
    "conditionals": {"beast": "The Forked Path", "part": "fork-splinter", "part_name": "Fork Splinter"},
    "lists": {"beast": "The IndexError Drowner", "part": "drowner-link", "part_name": "Drowner Link"},
    "dictionaries": {"beast": "The KeyError Ghoul", "part": "ghoul-page", "part_name": "Ghoul Page"},
    "random-selection": {"beast": "The Loaded Die", "part": "loaded-pip", "part_name": "Loaded Pip"},
    "loops": {"beast": "The Off-by-One Wraith", "part": "ouroboros-scale", "part_name": "Ouroboros Scale"},
    "functions": {"beast": "The Hollow Return", "part": "hollow-shard", "part_name": "Hollow Shard"},
    "control-flow": {"beast": "The Endless Leshen", "part": "leshen-root", "part_name": "Leshen Root"},
    "strings": {"beast": "The Whitespace Wisp", "part": "wisp-thread", "part_name": "Wisp Thread"},
    "exceptions": {"beast": "The Traceback Banshee", "part": "banshee-veil", "part_name": "Banshee Veil"},
    "files-json": {"beast": "The Lost Scroll", "part": "scroll-ash", "part_name": "Scroll Ash"},
    "sets": {"beast": "The Twin Doppel", "part": "doppel-scale", "part_name": "Doppel Scale"},
    "grids": {"beast": "The Row Mimic", "part": "lattice-shard", "part_name": "Lattice Shard"},
    "sorting": {"beast": "The Shuffled Herald", "part": "herald-pennant", "part_name": "Herald Pennant"},
    "references": {"beast": "The Alias Shade", "part": "shade-glass", "part_name": "Shade Glass"},
    "classes": {"beast": "The Selfless Golem", "part": "golem-clay", "part_name": "Golem Clay"},
    "testing": {"beast": "The Silent Saboteur", "part": "saboteur-pin", "part_name": "Saboteur Pin"},
    "callbacks": {"beast": "The Hasty Caller", "part": "caller-bell", "part_name": "Caller Bell"},
    "agents": {"beast": "The Unbound Servant", "part": "servant-collar", "part_name": "Servant Collar"},
    "recursion": {"beast": "The Bottomless Well", "part": "well-stone", "part_name": "Well Stone"},
    "search": {"beast": "The Wandering Lantern", "part": "lantern-wick", "part_name": "Lantern Wick"},
    "simulation": {"beast": "The Lucky Liar", "part": "liars-coin", "part_name": "Liar's Coin"},
}
DUNGEON_REGIONS = {
    "basics": {"id": "basics", "label": "Basics Village", "danger": 1, "signs": ("variables", "input-output", "conditionals"), "boss": "The Mimic Matriarch", "essence": "village-essence", "essence_name": "Village Essence"},
    "collections": {"id": "collections", "label": "Collection Caves", "danger": 2, "signs": ("lists", "dictionaries", "random-selection"), "boss": "The Drowned Hoard", "essence": "cave-essence", "essence_name": "Cave Essence"},
    "flow": {"id": "flow", "label": "Flow Keep", "danger": 3, "signs": ("loops", "functions", "control-flow"), "boss": "The Endless Warden", "essence": "keep-essence", "essence_name": "Keep Essence"},
    "archive": {"id": "archive", "label": "Sunken Archive", "danger": 2, "signs": ("strings", "exceptions", "files-json"), "boss": "The Archivist Lich", "essence": "archive-essence", "essence_name": "Archive Essence"},
    "labyrinth": {"id": "labyrinth", "label": "The Labyrinth", "danger": 3, "signs": ("grids", "sets", "sorting"), "boss": "The Minotaur of Rows", "essence": "labyrinth-essence", "essence_name": "Labyrinth Essence"},
    "workshop": {"id": "workshop", "label": "Clockwork Workshop", "danger": 3, "signs": ("classes", "references"), "boss": "The Brass Automaton", "essence": "workshop-essence", "essence_name": "Workshop Essence"},
    "spire": {"id": "spire", "label": "Seer's Spire", "danger": 4, "signs": ("recursion", "search", "simulation"), "boss": "The Recursive Oracle", "essence": "spire-essence", "essence_name": "Spire Essence"},
    "hollow": {"id": "hollow", "label": "Familiar's Hollow", "danger": 4, "signs": ("callbacks", "agents", "testing"), "boss": "The Hollow King", "essence": "hollow-essence", "essence_name": "Hollow Essence"},
}
DUNGEON_MATERIAL_NAMES = {
    **{beast["part"]: beast["part_name"] for beast in HUNTER_BEASTS.values()},
    **{region["essence"]: region["essence_name"] for region in DUNGEON_REGIONS.values()},
}
DUNGEON_LOOT_PARTS = {"encounter": 1, "elite": 2, "boss": 3}
# A fight cleared without a single miss (a guarded miss still counts) drops one more part.
DUNGEON_CLEAN_FIGHT_BONUS = 1
# Elites drop these in order; each one's effect is applied in Dungeon fights.
DUNGEON_TRINKETS = (
    {"id": "dungeon-warden-sigil", "name": "Warden Sigil", "kind": "trinket", "trinket": "Warden Sigil", "description": "Every fight starts with one free mistake banked."},
    {"id": "dungeon-hunting-bell", "name": "Hunting Bell", "kind": "trinket", "trinket": "Hunting Bell", "description": "Mechanic countdowns last one answer longer."},
    {"id": "dungeon-whetstone-charm", "name": "Whetstone Charm", "kind": "trinket", "trinket": "Whetstone Charm", "description": "Every correct answer chips 1 more Resolve."},
)
DUNGEON_TRINKET_FALLBACK_COINS = 10

# ── Beast oils (crafting) ────────────────────────────────────────────────
# Crafted at the Merchant from banked parts and coins, one sign each; a
# stronger oil needs a higher sign rank. Applied in a fight against that
# sign's beast (one per fight), an oil only helps: a free mistake, a slower
# mechanic or bigger Resolve chips. It never shortens a fight.
HUNTER_OIL_TIERS = (
    {"id": "ward", "name": "Ward Oil", "rank": 0, "parts": 2, "essence": 0, "coins": 10, "effect": "One free mistake banked for this fight."},
    {"id": "slowing", "name": "Slowing Oil", "rank": 1, "parts": 3, "essence": 1, "coins": 25, "effect": "Its mechanic countdown gets 2 more answers."},
    {"id": "bane", "name": "Bane Oil", "rank": 2, "parts": 5, "essence": 2, "coins": 50, "effect": "Every correct answer chips 3 more Resolve this fight."},
)
HUNTER_OIL_TIERS_BY_ID = {tier["id"]: tier for tier in HUNTER_OIL_TIERS}
HUNTER_OIL_SLOW_ANSWERS = 2
HUNTER_OIL_BANE_CHIP = 3


# ── Kit smithing and identify-by-reading ─────────────────────────────────
# Region essences (boss drops) upgrade a kit carried into every delve.
HUNTER_KIT = {
    "coat": {"name": "Hunter's Coat", "essence": "village-essence", "effect": "+8 max HP at the start of every delve per level"},
    "blade": {"name": "Hunter's Blade", "essence": "cave-essence", "effect": "+1 Resolve chip on every correct answer per level"},
    "satchel": {"name": "Hunter's Satchel", "essence": "keep-essence", "effect": "+1 field bandage at the start of every delve per level"},
}
HUNTER_KIT_MAX_LEVEL = 3
HUNTER_KIT_COINS_PER_LEVEL = 40
HUNTER_KIT_COAT_HP = 8
# Elites and bosses drop an unmarked vial; reading a code snippet right
# identifies it as an oil for the snippet's sign (Brogue-style).
DUNGEON_VIAL = "unmarked-vial"
DUNGEON_MATERIAL_NAMES[DUNGEON_VIAL] = "Unmarked Vial"
HUNTER_IDENTIFY_TIER_WEIGHTS = (("ward", 6), ("slowing", 3), ("bane", 1))


# ── Armory: campaign gear, food and relics ───────────────────────────────
# Every campaign story file carries an "armory" of themed items (weapons,
# armour, trinkets, food, tonics and a boss relic). Ownership lives in the
# local hunter save (not the cloud projection); equipping armour or a trinket
# writes only its name into the synced equipment fields. Effects come from a
# short list of capped keys and never change how many objectives a fight has.
ARMORY_SLOTS = ("weapon", "armor", "trinket", "food", "tonic", "relic", "aid")
ARMORY_GEAR_SLOTS = ("weapon", "armor", "trinket")
ARMORY_STACK_SLOTS = ("food", "tonic", "aid")
ARMORY_TIERS = ("common", "uncommon", "rare", "epic", "legendary")
ARMORY_EFFECT_CAPS = {
    "impact": 3, "break_coins": 10, "reduction": 60, "start_guards": 1, "heal_on_objective": 6,
    "coin_bonus": 25, "xp_bonus": 30, "loot_luck": 25, "heal": 100,
}
ARMORY_FLAG_EFFECTS = frozenset({"first_miss_free", "block_first_miss", "revive"})
ARMORY_ON_TYPES = frozenset({"any", *CAMPAIGN_QUESTION_TYPES})
ARMORY_BUFF_CAPS = {"guards": 1, "reduction": 30, "xp_bonus": 50, "coin_bonus": 50}
# Aid: one-time help that is armed by using it, then spent when it is needed.
# free_asks: an Ask PYR in a fight that costs nothing; wards: a wrong answer
# that deals no damage. Not tied to a campaign, so every board can drop them.
AID_CHARGE_CAPS = {"free_asks": 5, "wards": 3}
AID_CAMPAIGN = "aid"
AID_ITEMS = (
    {"id": "aid-pyrs-favour", "name": "PYR's Favour", "slot": "aid", "tier": "uncommon", "effect": {"free_asks": 1}, "price": 40,
     "flavour": "PYR owes you one. Ask once without it costing the fight."},
    {"id": "aid-ward-shield", "name": "Ward Shield", "slot": "aid", "tier": "uncommon", "effect": {"wards": 1}, "price": 45,
     "flavour": "A thin silver ward. It takes one wrong answer for you."},
    {"id": "aid-pyrs-blessing", "name": "PYR's Blessing", "slot": "aid", "tier": "rare", "effect": {"free_asks": 3}, "price": 100,
     "flavour": "Three questions, no strings, no lost rewards."},
    {"id": "aid-aegis-of-patience", "name": "Aegis of Patience", "slot": "aid", "tier": "rare", "effect": {"wards": 2}, "price": 110,
     "flavour": "For the bounties where you will need two more tries."},
)
AID_DROP_CHANCE = 30  # % per cleared bounty
# The local activity log behind the Settings activity graph: one entry per
# (local) day. Never synced; old days fall off after a bit over a year.
ACTIVITY_LOG_DAYS = 400
ACTIVITY_KINDS = ("lines", "answers", "mobs", "floors", "bosses")
MAX_CODE_LINES_PER_SAVE = 2_000
ARMORY_BONUS_CAP = 50
ARMORY_REDUCTION_CAP = 80
ARMORY_MAX_STACK = 99
CAMPAIGN_BREAK_COINS = 3
LEGACY_ARMOR_REDUCTION = {
    "Apprentice Coat": 10, "Leather Guard": 20, "Runic Mail": 30, "Emberplate": 40, "Guardian Aegis": 50, "Mythril Archive Plate": 60,
    "Debugger Plate": 15, "Ledgerguard Coat": 25, "Emberweave Mantle": 30,
}
# The Merchant's original trinkets, given real armory effects.
LEGACY_TRINKET_EFFECTS = {
    "Syntax Ward": {"block_first_miss": True},
    "Loop Lens": {"heal_on_objective": 2},
    "Guard Bell": {"start_guards": 1},
    "Scimitar of Momentum": {"coin_bonus": 15},
    "Vision Scroll": {"loot_luck": 10},
}
_ARMORY_CACHE: dict[str, Any] = {"source": None, "by_id": {}, "by_name": {}}
_OBJECTIVE_WORDS = {"code_checkpoint": "BUILD", "bug_diagnosis": "FIX", "prediction": "PREDICT", "explanation": "EXPLAIN"}


def armory_catalog() -> dict[str, dict[str, Any]]:
    """Every campaign's items by id, each tagged with its campaign branch."""

    data = load_campaign_bounties()
    if _ARMORY_CACHE["source"] is not data:
        by_id: dict[str, dict[str, Any]] = {}
        for branch, entry in data.items():
            for item in entry.get("armory", []) if isinstance(entry, Mapping) and isinstance(entry.get("armory"), list) else []:
                if isinstance(item, Mapping) and item.get("slot") in ARMORY_SLOTS and isinstance(item.get("id"), str) and isinstance(item.get("name"), str):
                    by_id[item["id"]] = {**item, "campaign": branch}
        for item in AID_ITEMS:
            by_id[item["id"]] = {**item, "campaign": AID_CAMPAIGN}
        _ARMORY_CACHE.update(source=data, by_id=by_id, by_name={item["name"]: item for item in by_id.values()})
    return _ARMORY_CACHE["by_id"]


def armory_by_name() -> dict[str, dict[str, Any]]:
    armory_catalog()
    return _ARMORY_CACHE["by_name"]


def armory_effect_text(effect: Mapping[str, Any]) -> str:
    """Plain words for an item's effect, built from the effect itself."""

    parts = []
    if effect.get("impact"):
        on = effect.get("on", "any")
        parts.append(f"+{effect['impact']} impact on {'every objective' if on == 'any' else _OBJECTIVE_WORDS.get(on, on) + ' objectives'}")
    if effect.get("break_coins"):
        parts.append(f"+{effect['break_coins']} coins on a Guard Break")
    if effect.get("reduction"):
        parts.append(f"{effect['reduction']}% less damage from misses")
    if effect.get("first_miss_free"):
        parts.append("your first miss each battle costs nothing")
    if effect.get("start_guards"):
        parts.append("start every battle with a free mistake")
    if effect.get("block_first_miss"):
        parts.append("blocks the first counterattack each battle")
    if effect.get("revive"):
        parts.append("revive at 1 HP once per battle")
    if effect.get("heal_on_objective"):
        parts.append(f"heal {effect['heal_on_objective']} HP per verified objective")
    if effect.get("coin_bonus"):
        parts.append(f"+{effect['coin_bonus']}% bounty coins")
    if effect.get("xp_bonus"):
        parts.append(f"+{effect['xp_bonus']}% bounty XP")
    if effect.get("loot_luck"):
        parts.append(f"+{effect['loot_luck']}% chance of rarer loot")
    if effect.get("heal"):
        parts.append(f"restores {effect['heal']} HP")
    if effect.get("free_asks"):
        count = effect["free_asks"]
        parts.append(f"your next {'Ask PYR' if count == 1 else f'{count} Ask PYRs'} in a fight cost{'s' if count == 1 else ''} no rewards")
    if effect.get("wards"):
        count = effect["wards"]
        parts.append(f"blocks the damage of your next {'wrong answer' if count == 1 else f'{count} wrong answers'}")
    buff = effect.get("next_battle") if isinstance(effect.get("next_battle"), Mapping) else {}
    if buff:
        words = []
        if buff.get("guards"):
            words.append("a free mistake")
        if buff.get("reduction"):
            words.append(f"{buff['reduction']}% less damage")
        if buff.get("xp_bonus"):
            words.append(f"+{buff['xp_bonus']}% XP")
        if buff.get("coin_bonus"):
            words.append(f"+{buff['coin_bonus']}% coins")
        parts.append("next battle: " + ", ".join(words))
    text = "; ".join(parts) or "a keepsake"
    return text[0].upper() + text[1:] + "."

# ── Floor grids and stairs ───────────────────────────────────────────────
# A floor is a small grid of rooms under fog: you see explored rooms and
# their doors (two rooms out with 4 Insight), and the boss lair is always
# felt. Explored rooms can be walked back through; doing so is inert (no
# camp, no banking). Beating the boss offers stairs to the next floor.
DUNGEON_GRID_COLUMNS = 5
DUNGEON_GRID_ROWS = 4
DUNGEON_GRID_ROOMS = 12
DUNGEON_GRID_LOOPS = 2
DUNGEON_GRID_FAR_SIGHT_INSIGHT = 4
DUNGEON_DEEP_EXTRA_PARTS = 1


def _identify_snippet(sign_id: str, seed: str) -> dict[str, Any]:
    """A short snippet for one sign with its printed result: the prompt,
    four options, the answer and why. Deterministic for a seed."""

    rng = random.Random(seed)
    words = ["sword", "shield", "potion", "torch", "rope", "map", "key", "lamp"]
    if sign_id == "lists":
        items = rng.sample(words, 4)
        index = rng.choice([0, 1, 2, -1])
        code = f"items = {items!r}\nprint(items[{index}])"
        answer = items[index]
        wrong = [word for word in items if word != answer][:2] + ["IndexError"]
        why = f"Indexes start at 0 and -1 is the last item, so items[{index}] is {answer!r}."
    elif sign_id == "loops":
        n = rng.randint(3, 6)
        code = f"total = 0\nfor i in range({n}):\n    total += i\nprint(total)"
        answer = str(sum(range(n)))
        wrong = [str(sum(range(n + 1))), str(n), str(sum(range(n)) + 1)]
        why = f"range({n}) gives 0 to {n - 1}, and those add up to {answer}."
    elif sign_id == "dictionaries":
        a, b, c = rng.sample(range(2, 20), 3)
        key = rng.choice(["gold", "gems", "ore"])
        stock = {"gold": a, "gems": b}
        code = f"stock = {stock!r}\nprint(stock.get({key!r}, {c}))"
        answer = str(stock.get(key, c))
        wrong = [str(value) for value in (a, b, c) if str(value) != answer][:2] + ["KeyError"]
        why = f".get returns the value when the key exists and the default ({c}) when it does not, so it prints {answer}."
    elif sign_id == "conditionals":
        hp = rng.choice([15, 35, 50, 51, 80])
        code = f"hp = {hp}\nif hp > 50:\n    print('steady')\nelif hp > 20:\n    print('wounded')\nelse:\n    print('fleeing')"
        answer = "steady" if hp > 50 else "wounded" if hp > 20 else "fleeing"
        wrong = [word for word in ("steady", "wounded", "fleeing") if word != answer] + ["nothing"]
        why = f"Checks run top to bottom and the first true one wins: hp is {hp}, so it prints {answer}."
    elif sign_id == "functions":
        k = rng.randint(2, 9)
        returns = rng.random() < 0.5
        body = f"    return n * 2" if returns else f"    n * 2"
        code = f"def double(n):\n{body}\n\nprint(double({k}))"
        answer = str(k * 2) if returns else "None"
        wrong = [value for value in (str(k * 2), "None", str(k), "TypeError") if value != answer][:3]
        why = "The function returns its result." if returns else "Without return, a function hands back None (the Hollow Return)."
    elif sign_id == "variables":
        x, y = rng.randint(2, 9), rng.randint(2, 9)
        code = f"a = {x}\nb = a\na = a + {y}\nprint(b)"
        answer = str(x)
        wrong = [str(x + y), str(y), "NameError"]
        why = f"b took a's value ({x}) when it was assigned; changing a afterwards does not change b."
    elif sign_id == "input-output":
        bet = rng.randint(2, 9)
        convert = rng.random() < 0.5
        line = f"print(int(bet) + {bet})" if convert else f"print(bet + '{bet}')"
        code = f"bet = '{bet}'   # what input() gives you\n{line}"
        answer = str(bet * 2) if convert else f"{bet}{bet}"
        wrong = [value for value in (str(bet * 2), f"{bet}{bet}", "TypeError", f"{bet} {bet}") if value != answer][:3]
        why = "int() turns the text into a number first." if convert else "Both are strings, so + joins them instead of adding."
    elif sign_id == "random-selection":
        low = rng.randint(0, 2)
        high = low + rng.randint(2, 3)
        use_randint = rng.random() < 0.5
        call = f"random.randint({low}, {high})" if use_randint else f"random.randrange({low}, {high})"
        code = f"import random\nroll = {call}\nprint(roll)"
        top = high if use_randint else high - 1
        answer = f"{low} to {top}"
        wrong = [value for value in (f"{low} to {high}", f"{low} to {high - 1}", f"{low + 1} to {high}", f"{low} to {high + 1}") if value != answer][:3]
        question = "Which values can this print?"
        why = "randint includes both ends." if use_randint else "randrange stops before the end, like range."
        return _identify_pack(rng, code, answer, wrong, why, question)
    elif sign_id == "strings":
        if rng.random() < 0.5:
            raw = rng.choice(["  Ada ", " Brook  ", "Cyr   ", "  Dax"])
            code = f"name = {raw!r}\nprint(len(name.strip()))"
            answer = str(len(raw.strip()))
            wrong = [str(len(raw)), str(len(raw.strip()) + 1), str(len(raw.lstrip()))]
            why = "strip() removes the spaces at both ends before len counts the letters."
        else:
            text = rng.choice(["a,b,,c", "red,,blue", "x,y,z,", ",one,two"])
            code = f"parts = {text!r}.split(',')\nprint(len(parts))"
            answer = str(len(text.split(",")))
            wrong = [str(len([part for part in text.split(",") if part])), str(len(text.split(",")) + 1), str(text.count(","))]
            why = "split(',') keeps an empty piece between two commas or at an end, so empty pieces still count."
    elif sign_id == "exceptions":
        text = rng.choice(["12", "1.5", "abc", "7", " 9 ", "4o"])
        code = f"try:\n    value = int({text!r})\n    print('number', value)\nexcept ValueError:\n    print('not a number')"
        try:
            answer = f"number {int(text)}"
        except ValueError:
            answer = "not a number"
        wrong = ["not a number", f"number {text.strip()}", "ValueError", "number 1"]
        why = "int() accepts whole-number text (spaces at the ends are fine) and raises ValueError for anything else, which except catches."
    elif sign_id == "files-json":
        name = rng.choice(["Ada", "Brook", "Cyr"])
        alive = rng.random() < 0.5
        hp = rng.randint(1, 9)
        record = {"name": name, "alive": alive, "hp": hp}
        code = f"import json\nprint(json.dumps({{'name': {name!r}, 'alive': {alive}, 'hp': {hp}}}))"
        answer = json.dumps(record)
        wrong = [str(record), answer.replace("true", "True").replace("false", "False"), "TypeError"]
        why = "json.dumps writes JSON text: double quotes around strings and lowercase true and false."
    elif sign_id == "sets":
        kinds = rng.sample(["ore", "gem", "bone", "salt", "ash"], 3)
        loot = kinds + rng.sample(kinds, 2)
        rng.shuffle(loot)
        code = f"loot = {loot!r}\nunique = set(loot)\nprint(len(unique))"
        answer = str(len(set(loot)))
        wrong = [str(len(loot)), str(len(loot) - 1), "0"]
        why = "A set keeps one copy of each value, so the duplicates disappear."
    elif sign_id == "grids":
        shared = rng.random() < 0.5
        rows, cols = rng.randint(2, 3), rng.randint(3, 4)
        row, col = rng.randint(1, rows - 1), rng.randint(0, cols - 1)
        build = f"[[0] * {cols}] * {rows}" if shared else f"[[0] * {cols} for _ in range({rows})]"
        code = f"grid = {build}\ngrid[0][{col}] = 5\nprint(grid[{row}][{col}])"
        answer = "5" if shared else "0"
        wrong = ["0" if shared else "5", "IndexError", "None"]
        why = "Multiplying a list of rows repeats the same row, so every row changes together." if shared else "The comprehension builds a separate row each time, so only row 0 changes."
    elif sign_id == "sorting":
        names = rng.sample(["ogre", "imp", "wyvern", "troll", "basilisk", "elf"], 4)
        if rng.random() < 0.5:
            code = f"names = {names!r}\nresult = names.sort()\nprint(result)"
            answer = "None"
            wrong = [str(sorted(names)), str(names), "[]"]
            why = "list.sort() sorts in place and returns None; sorted() is the one that returns a new list."
        else:
            code = f"names = {names!r}\nprint(sorted(names, key=len)[0])"
            answer = sorted(names, key=len)[0]
            wrong = [sorted(names)[0], names[0], max(names, key=len)]
            why = "key=len compares lengths; ties keep their original order, so the first shortest name wins."
    elif sign_id == "references":
        items = rng.sample(["torch", "rope", "map", "key"], 2)
        copied = rng.random() < 0.5
        code = f"a = {items!r}\nb = {'a.copy()' if copied else 'a'}\nb.append('lamp')\nprint(len(a))"
        answer = "2" if copied else "3"
        wrong = ["3" if copied else "2", "1", "4"]
        why = "a.copy() makes a new list, so a keeps its two items." if copied else "b = a gives the same list a second name, so appending through b changes a too."
    elif sign_id == "classes":
        start, step = rng.randint(0, 5), rng.randint(2, 4)
        code = (
            f"class Counter:\n    def __init__(self):\n        self.count = {start}\n\n    def add(self):\n        self.count += {step}\n\n\n"
            "c = Counter()\nc.add()\nc.add()\nprint(c.count)"
        )
        answer = str(start + 2 * step)
        wrong = [str(start + step), str(start), str(2 * step)]
        why = f"__init__ sets count to {start} once; each add() adds {step} to that object's own count."
    elif sign_id == "testing":
        k = rng.choice([2, 3, 4])
        code = f"def double(n):\n    return n + 2\n\nprint(double({k}) == {2 * k})"
        answer = str(k + 2 == 2 * k)
        wrong = ["False" if answer == "True" else "True", "AssertionError", str(k + 2)]
        why = "n + 2 equals n * 2 only when n is 2, so a test that only checks 2 passes on a broken function."
    elif sign_id == "callbacks":
        if rng.random() < 0.5:
            word = rng.choice(["hi", "run", "ok"])
            code = f"def shout(text):\n    return text.upper() + '!'\n\ndef apply(action, value):\n    return action(value)\n\nprint(apply(shout, {word!r}))"
            answer = word.upper() + "!"
            wrong = [word + "!", word.upper(), "TypeError"]
            why = "shout is passed without brackets, so apply receives the function itself and calls it."
        else:
            k = rng.randint(2, 6)
            name = rng.choice(["double", "square"])
            code = f"actions = {{'double': lambda n: n * 2, 'square': lambda n: n * n}}\nprint(actions[{name!r}]({k}))"
            answer = str(k * 2 if name == "double" else k * k)
            wrong = [str(k * k if name == "double" else k * 2), str(k), "KeyError"]
            why = "The dictionary stores functions as values; looking one up and adding brackets calls it."
    elif sign_id == "agents":
        x, y = rng.randint(2, 9), rng.randint(2, 9)
        tool = rng.choice(["add", "mul"])
        code = (
            "tools = {'add': lambda a, b: a + b, 'mul': lambda a, b: a * b}\n"
            f"action = {{'tool': {tool!r}, 'args': [{x}, {y}]}}\n"
            "result = tools[action['tool']](*action['args'])\nprint(result)"
        )
        answer = str(x + y if tool == "add" else x * y)
        wrong = [str(x * y if tool == "add" else x + y), f"{x}{y}", "KeyError"]
        why = "The agent looks the tool up by name in its registry and calls it with the arguments the brain chose."
    elif sign_id == "recursion":
        k = rng.randint(3, 6)
        if rng.random() < 0.5:
            code = f"def total(n):\n    if n == 0:\n        return 0\n    return n + total(n - 1)\n\nprint(total({k}))"
            answer = str(k * (k + 1) // 2)
            wrong = [str(k), str(k * (k - 1) // 2), "RecursionError"]
            why = "Each call adds n and asks for total(n - 1) until the base case returns 0."
        else:
            code = f"def depth(items):\n    if not items:\n        return 0\n    return 1 + depth(items[1:])\n\nprint(depth({list(range(k))!r}))"
            answer = str(k)
            wrong = [str(k - 1), str(k + 1), "RecursionError"]
            why = "Each call drops one item and adds 1, and the empty list is the base case."
    elif sign_id == "search":
        nodes = ["A", "B", "C", "D", "E"]
        graph: dict[str, list[str]] = {node: [] for node in nodes}
        for index, node in enumerate(nodes[1:], start=1):
            graph[nodes[rng.randint(0, index - 1)]].append(node)
        first, second = rng.sample(nodes[1:], 2)
        if second not in graph[first]:
            graph[first].append(second)

        def breadth_first() -> str:
            order, queue, seen = [], ["A"], {"A"}
            while queue:
                node = queue.pop(0)
                order.append(node)
                for nxt in graph[node]:
                    if nxt not in seen:
                        seen.add(nxt)
                        queue.append(nxt)
            return "".join(order)

        def depth_first(node: str, seen: list[str]) -> list[str]:
            seen.append(node)
            for nxt in graph[node]:
                if nxt not in seen:
                    depth_first(nxt, seen)
            return seen

        code = (
            f"graph = {graph!r}\norder = []\nqueue = ['A']\nseen = {{'A'}}\nwhile queue:\n    node = queue.pop(0)\n    order.append(node)\n"
            "    for nxt in graph[node]:\n        if nxt not in seen:\n            seen.add(nxt)\n            queue.append(nxt)\nprint(''.join(order))"
        )
        answer = breadth_first()
        wrong = ["".join(depth_first("A", [])), "".join(sorted(answer, reverse=True)), "ABCDE"]
        why = "Breadth-first search visits nodes in the order they were queued: A's neighbours first, then theirs."
    elif sign_id == "simulation":
        rolls = [rng.randint(1, 6) for _ in range(rng.choice([4, 5, 8, 10]))]
        target = rng.randint(4, 5)
        wins = sum(1 for roll in rolls if roll >= target)
        code = f"rolls = {rolls!r}\nwins = 0\nfor roll in rolls:\n    if roll >= {target}:\n        wins += 1\nprint(wins / len(rolls))"
        answer = str(wins / len(rolls))
        wrong = [str(wins), str((wins + 1) / len(rolls)), str(sum(1 for roll in rolls if roll > target) / len(rolls))]
        why = f"The loop counts rolls of {target} or more, then divides by the number of rolls to get a rate."
    else:  # control-flow
        k = rng.randint(5, 12)
        step = rng.randint(2, 4)
        n = 0
        while n < k:
            n += step
        code = f"n = 0\nwhile n < {k}:\n    n += {step}\nprint(n)"
        answer = str(n)
        wrong = [str(n - step), str(k), str(n + step)]
        why = f"The loop stops the first time n is no longer below {k}, which is {n}."
    return _identify_pack(rng, code, answer, wrong, why)


def _identify_pack(rng: random.Random, code: str, answer: str, wrong: list[str], why: str, question: str = "What does this print?") -> dict[str, Any]:
    options = [answer]
    for value in wrong:
        if value not in options:
            options.append(value)
    filler = ["Nothing", "SyntaxError", "0", "True"]
    while len(options) < 4:
        options.append(next(value for value in filler if value not in options))
    options = options[:4]
    rng.shuffle(options)
    return {"prompt": f"{question}\n```python\n{code}\n```", "options": options, "answer": options.index(answer), "answer_text": answer, "why": why}


def hunter_signs_for(concept: object) -> list[str]:
    """The signs a concept label (e.g. "Lists and random selection") feeds."""

    text = re.sub(r"[-_/]", " ", str(concept or "").lower())
    found = []
    for sign_id, words in HUNTER_SIGN_KEYWORDS.items():
        if re.search(rf"\b{re.escape(sign_id.replace('-', ' '))}\b", text) or any(re.search(rf"\b{re.escape(word)}\b", text) for word in words):
            found.append(sign_id)
    return found


def _read_state_file(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _custody_marker_path(destination: Path) -> Path:
    """Return the provenance marker paired with a derived local cache."""

    return destination.with_name(f".{destination.name}.custody.json")


def _read_custody_marker(path: Path) -> dict[str, Any] | None:
    """Read a regular, non-symlink custody marker if one is present."""

    if path.is_symlink() or not path.is_file():
        return None
    return _read_state_file(path)


def _custody_marker_allows_resume(
    marker: Mapping[str, Any] | None,
    *,
    source_digest: str | None,
    source_revision: object,
    destination_digest: str | None,
    destination_revision: object,
) -> bool:
    """Validate provenance for a previously approved, advanced local cache.

    A marker is evidence that the destination was copied through the gateway;
    it is not a newest-file heuristic.  The reviewed source bytes and
    revision must still be identical, and the destination may only have
    advanced through normal revisioned state-service writes.  An unchanged
    destination must still match its recorded digest, so a direct edit fails
    closed rather than becoming an implicit authority.
    """

    if not isinstance(marker, Mapping):
        return False
    if marker.get("schema_version") != CUSTODY_MARKER_VERSION:
        return False
    if not isinstance(source_digest, str) or marker.get("source_digest") != source_digest:
        return False
    if marker.get("source_revision") != source_revision:
        return False
    marker_destination_revision = marker.get("destination_revision")
    if isinstance(marker_destination_revision, bool) or not isinstance(marker_destination_revision, int):
        return False
    if marker_destination_revision < 0:
        return False
    marker_destination_digest = marker.get("destination_digest")
    if not isinstance(marker_destination_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", marker_destination_digest):
        return False
    if isinstance(destination_revision, bool) or not isinstance(destination_revision, int):
        return False
    if destination_revision < marker_destination_revision:
        return False
    if destination_revision == marker_destination_revision:
        return destination_digest == marker_destination_digest
    # A later revision is accepted only when the source identity remains the
    # one that the owner explicitly reviewed during migration.
    return True


def _active_project(value: Mapping[str, Any]) -> Mapping[str, Any]:
    projects = value.get("projects")
    if not isinstance(projects, list):
        return {}
    return next((item for item in projects if isinstance(item, dict) and item.get("status") == "active"), {})


def _state_summary(value: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if value is None:
        return None
    player = value.get("player") if isinstance(value.get("player"), dict) else {}
    stats = value.get("stats") if isinstance(value.get("stats"), dict) else {}
    streak = value.get("streak") if isinstance(value.get("streak"), dict) else {}
    project = _active_project(value)
    mobs = project.get("mobs") if isinstance(project.get("mobs"), list) else []
    mob_statuses = {
        str(item.get("name")): str(item.get("status"))
        for item in mobs
        if isinstance(item, dict) and item.get("name")
    }
    return {
        "schema_version": value.get("schema_version"),
        "rules_version": (value.get("rules") or {}).get("version") if isinstance(value.get("rules"), dict) else None,
        "revision": (value.get("meta") or {}).get("revision") if isinstance(value.get("meta"), dict) else None,
        "level": player.get("level"),
        "xp": player.get("xp"),
        "xp_next": player.get("xp_next"),
        "lifetime_xp": player.get("lifetime_xp"),
        "coins": player.get("coins"),
        "hp": player.get("hp"),
        "mobs_defeated": stats.get("mobs_defeated"),
        "sessions": stats.get("sessions"),
        "streak": streak.get("current"),
        "last_active": streak.get("last_active"),
        "project": project.get("name"),
        "project_progress": project.get("progress"),
        "mob_statuses": mob_statuses,
        "unlocked_achievements": [
            str(item.get("name"))
            for item in (value.get("achievements") or [])
            if isinstance(item, dict) and item.get("unlocked") is True
        ][:20],
    }


def legacy_state_report(canonical_path: Path, legacy_path: Path) -> dict[str, Any]:
    """Return a bounded, read-only comparison for an old workspace save.

    The report intentionally contains summaries rather than arbitrary state
    snapshots. A caller must review and approve any migration separately.
    """

    canonical = _read_state_file(canonical_path)
    same_path = canonical_path.resolve() == legacy_path.resolve()
    legacy = canonical if same_path else _read_state_file(legacy_path)
    canonical_summary = _state_summary(canonical)
    legacy_summary = _state_summary(legacy)
    differences: list[dict[str, Any]] = []
    if canonical_summary is not None and legacy_summary is not None and not same_path:
        for field in (
            "schema_version",
            "rules_version",
            "revision",
            "level",
            "xp",
            "xp_next",
            "lifetime_xp",
            "coins",
            "hp",
            "mobs_defeated",
            "sessions",
            "streak",
            "last_active",
            "project",
            "project_progress",
            "mob_statuses",
            "unlocked_achievements",
        ):
            if canonical_summary.get(field) != legacy_summary.get(field):
                differences.append(
                    {
                        "field": field,
                        "canonical": canonical_summary.get(field),
                        "legacy": legacy_summary.get(field),
                    }
                )
    return {
        "canonical_path": str(canonical_path.resolve()),
        "canonical_authoritative": True,
        "legacy_path": None if same_path else str(legacy_path.resolve()),
        "legacy_present": bool(legacy is not None and not same_path),
        "legacy_authoritative": False,
        "manual_approval_required": bool(legacy is not None and not same_path and differences),
        "migration_note": "No automatic merge: review validated reward/session evidence before selecting allowlisted fields.",
        "canonical": canonical_summary,
        "legacy": legacy_summary,
        "differences": differences[:40],
    }


def state_authority_info(canonical_path: Path, workspace_path: Path) -> dict[str, Any]:
    """Describe the one active state path and any non-authoritative legacy file."""

    canonical = canonical_path.resolve()
    legacy = (workspace_path / "progress.json").resolve()
    same_path = canonical == legacy
    return {
        "canonical_path": str(canonical),
        "canonical_authoritative": True,
        "legacy_path": None if same_path else str(legacy),
        "legacy_present": bool(not same_path and legacy.is_file()),
        "legacy_authoritative": False,
        "legacy_requires_approval": bool(not same_path and legacy.is_file()),
    }


def state_custody_report(canonical_path: Path, proposed_path: Path | None) -> dict[str, Any]:
    """Describe an opt-in per-device custody destination without migrating it.

    This is intentionally read-only.  It compares exact file digests when a
    destination already exists; revision numbers are reported for context, but
    are never used to choose a winner.  A previously approved destination may
    resume only when its gateway-written provenance marker still matches the
    reviewed source bytes and revision.  A caller must use the explicit gateway
    migration command for any unmarked or divergent destination.
    """

    canonical = canonical_path.resolve()
    proposed = proposed_path.resolve() if proposed_path is not None else None
    source = _read_state_file(canonical)
    destination = _read_state_file(proposed) if proposed is not None else None

    source_digest = None
    destination_digest = None
    try:
        source_digest = hashlib.sha256(canonical.read_bytes()).hexdigest()
    except (FileNotFoundError, OSError):
        pass
    if proposed is not None:
        try:
            destination_digest = hashlib.sha256(proposed.read_bytes()).hexdigest()
        except (FileNotFoundError, OSError):
            pass

    marker_path = _custody_marker_path(proposed) if proposed is not None else None
    marker = _read_custody_marker(marker_path) if marker_path is not None else None
    marker_verified = False
    resume_authorized = False

    if source is None:
        status = "no-source-found"
    elif proposed is None:
        status = "approval-required"
    elif canonical == proposed:
        status = "current"
    elif destination is None:
        status = "approval-required"
    elif source_digest == destination_digest:
        status = "already-local"
    elif _custody_marker_allows_resume(
        marker,
        source_digest=source_digest,
        source_revision=(source.get("meta") or {}).get("revision") if isinstance(source.get("meta"), dict) else None,
        destination_digest=destination_digest,
        destination_revision=(destination.get("meta") or {}).get("revision") if isinstance(destination.get("meta"), dict) else None,
    ):
        # The explicit --use-local-state choice has already established this
        # derived cache as the active device authority.  Do not copy, merge or
        # select by timestamp on a later launch; simply resume it.  A changed
        # source digest, malformed marker or unmarked destination remains a
        # conflict below.
        status = "already-local"
        marker_verified = True
        resume_authorized = True
    else:
        status = "conflict"

    revision = lambda value: (value.get("meta") or {}).get("revision") if isinstance(value, dict) else None
    return {
        "canonical_path": str(canonical),
        "proposed_path": str(proposed) if proposed is not None else None,
        "status": status,
        "approval_required": status in {"approval-required", "conflict"},
        "source_present": source is not None,
        "destination_present": destination is not None,
        "source_revision": revision(source),
        "destination_revision": revision(destination),
        "source_digest": source_digest,
        "destination_digest": destination_digest,
        "custody_marker_path": str(marker_path) if marker_path is not None else None,
        "custody_marker_verified": marker_verified,
        "custody_resume_authorized": resume_authorized,
        "migration_write_performed": False,
        "migration_note": "Read-only preview. No automatic copy, merge, newest-revision choice or source deletion is performed.",
    }


class LocalStateService:
    """Validate and apply named local state commands under one shared lock."""

    def __init__(
        self,
        progress_path: Path | Callable[[], Path],
        progress_lock: threading.RLock,
    ):
        self._progress_path = progress_path
        self._progress_lock = progress_lock

    @property
    def progress_path(self) -> Path:
        path = self._progress_path() if callable(self._progress_path) else self._progress_path
        return Path(path)

    def device_id(self) -> str:
        return opaque_device_id()

    def persist(self, progress: dict[str, Any]) -> dict[str, Any]:
        """Persist a canonical local mutation and return its new metadata."""

        if not isinstance(progress, dict):
            raise StateCommandError("Canonical state must be an object", status_code=500)
        with self._progress_lock:
            metadata, _ = self._persist_locked(progress)
            return metadata

    def snapshot(self) -> dict[str, Any]:
        """Load the latest canonical snapshot while holding the shared lock."""

        with self._progress_lock:
            return self._load_locked()

    def snapshot_with_metadata(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Read the snapshot and its revision from one locked view."""

        with self._progress_lock:
            progress = self._load_locked()
            return progress, self._metadata_from_progress(progress)

    def metadata(self) -> dict[str, Any]:
        """Return cheap revision metadata without exposing a second state path."""

        with self._progress_lock:
            return self._metadata_from_progress(self._load_locked())

    def sync_snapshot(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return only the bounded player-state projection used by cloud sync."""

        with self._progress_lock:
            progress = self._load_locked()
            return self._sync_projection(progress), self._metadata_from_progress(progress)

    def migrate_local_state(
        self,
        destination_path: Path,
        *,
        expected_source_revision: int,
        confirmation_token: str,
        forbidden_paths: tuple[Path, ...] = (),
    ) -> dict[str, Any]:
        """Copy the canonical snapshot to an explicit, derived local cache.

        This is deliberately not a normal progression mutation: the source
        JSON is copied byte-for-byte, its revision and events do not change,
        and the tracked source is never deleted. The caller must supply the
        fixed confirmation token and the revision it reviewed. A divergent or
        symlinked destination fails closed; no newest-file heuristic exists.
        """

        expected = self._integer(expected_source_revision, "expected_source_revision", minimum=0)
        if confirmation_token != CUSTODY_CONFIRMATION_TOKEN:
            raise StateCommandError("Explicit custody confirmation is required", status_code=403)

        source = self.progress_path.resolve()
        raw_destination = Path(destination_path).expanduser()
        if raw_destination.is_symlink():
            raise StateCommandError("Custody destination may not be a symlink", status_code=409)
        destination = raw_destination.resolve(strict=False)
        forbidden = {Path(path).expanduser().resolve(strict=False) for path in forbidden_paths}
        if destination == source or destination in forbidden:
            raise StateCommandError("Custody destination must be separate from canonical and legacy state", status_code=409)
        if self._path_has_symlink_component(raw_destination.parent):
            raise StateCommandError("Custody destination parent may not contain a symlink", status_code=409)

        marker = destination.with_name(f".{destination.name}.custody.json")
        if marker.is_symlink():
            raise StateCommandError("Custody marker may not be a symlink", status_code=409)

        with self._progress_lock:
            try:
                source_bytes = source.read_bytes()
                source_value = json.loads(source_bytes.decode("utf-8"))
            except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                raise StateCommandError("Canonical progress.json could not be loaded", status_code=500) from exc
            if not isinstance(source_value, dict) or not source_value:
                raise StateCommandError("Canonical progress.json must be a non-empty object", status_code=500)

            actual = self._revision(source_value)
            if actual != expected:
                raise StateCommandError(
                    f"Canonical state changed during custody review (expected revision {expected}, found {actual})",
                    status_code=409,
                )
            source_digest = hashlib.sha256(source_bytes).hexdigest()

            if raw_destination.exists():
                if not raw_destination.is_file():
                    raise StateCommandError("Custody destination must be a regular file", status_code=409)
                try:
                    destination_bytes = raw_destination.read_bytes()
                except OSError as exc:
                    raise StateCommandError("Custody destination could not be read", status_code=409) from exc
                destination_digest = hashlib.sha256(destination_bytes).hexdigest()
                if destination_digest != source_digest:
                    raise StateCommandError(
                        "Custody destination already contains a different snapshot; review it before retrying",
                        status_code=409,
                    )
                marker_written = self._ensure_custody_marker(
                    marker,
                    source_digest=source_digest,
                    source_revision=actual,
                    destination_digest=destination_digest,
                    destination_revision=actual,
                )
                return {
                    "ok": True,
                    "action": "migrate_local_state",
                    "status": "already-local",
                    "changed": False,
                    "revision": actual,
                    "source_revision": actual,
                    "destination_revision": actual,
                    "source_digest": source_digest,
                    "destination_digest": destination_digest,
                    "marker_path": str(marker),
                    "marker_written": marker_written,
                    "migration_write_performed": False,
                }

            if marker.exists():
                raise StateCommandError("Custody marker exists without its destination; review it before retrying", status_code=409)

            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.tmp")
            try:
                with temporary.open("xb") as handle:
                    handle.write(source_bytes)
                    handle.flush()
                    os.fsync(handle.fileno())
                temporary.replace(destination)
            except OSError as exc:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
                raise StateCommandError("Custody destination could not be written atomically", status_code=500) from exc

            destination_digest = hashlib.sha256(source_bytes).hexdigest()
            try:
                self._write_custody_marker(
                    marker,
                    source_digest=source_digest,
                    source_revision=actual,
                    destination_digest=destination_digest,
                    destination_revision=actual,
                )
            except StateCommandError:
                # Keep the exact copied snapshot recoverable; a subsequent
                # explicit retry sees it as already-local and can repair the
                # marker after review.
                raise
            return {
                "ok": True,
                "action": "migrate_local_state",
                "status": "migrated",
                "changed": True,
                "revision": actual,
                "source_revision": actual,
                "destination_revision": actual,
                "source_digest": source_digest,
                "destination_digest": destination_digest,
                "marker_path": str(marker),
                "marker_written": True,
                "migration_write_performed": True,
            }

    def apply_cloud_projection(
        self,
        projection: Mapping[str, Any],
        *,
        expected_revision: int,
        cloud_revision: int,
    ) -> dict[str, Any]:
        """Apply a validated cloud projection to the local cache.

        This is a cache import, not a general state write.  The expected local
        revision is checked while holding ``PROGRESS_LOCK`` so a cloud pull can
        never clobber a concurrent local mutation.  Conflict resolution stays
        explicit in the SyncEngine.
        """

        expected = self._integer(expected_revision, "expected_revision", minimum=0)
        cloud = self._integer(cloud_revision, "cloud_revision", minimum=0)
        with self._progress_lock:
            progress = self._load_locked()
            actual = self._revision(progress)
            if actual != expected:
                raise StateCommandError(
                    f"Local state changed during cloud sync (expected revision {expected}, found {actual})",
                    status_code=409,
                )
            validated = self._validate_sync_projection(projection)
            before = self._sync_projection(progress)
            changed_domains = self._merge_sync_projection(progress, validated)
            if not changed_domains:
                return {
                    "ok": True,
                    "action": "sync_apply_cloud",
                    "actor": "sync",
                    "changed": False,
                    "revision": actual,
                    "cloud_revision": cloud,
                    "projection": before,
                }
            metadata, event = self._persist_locked(
                progress,
                action="sync_apply_cloud",
                actor="sync",
                event_details={
                    "cloud_revision": cloud,
                    "domains": changed_domains,
                    "reason": "cloud_authoritative_cache_refresh",
                },
            )
            return {
                "ok": True,
                "action": "sync_apply_cloud",
                "actor": "sync",
                "changed": True,
                "revision": metadata["revision"],
                "cloud_revision": cloud,
                "projection": self._sync_projection(progress),
                "event": event,
            }

    @staticmethod
    def _sync_text(value: object, field: str) -> str:
        return LocalStateService._text(value, field, max_length=MAX_SYNC_TEXT_LENGTH)

    @staticmethod
    def _sync_list(value: object, field: str) -> list[str]:
        if not isinstance(value, list) or len(value) > MAX_SYNC_LIST_ITEMS:
            raise StateCommandError(f"{field} must be a bounded list")
        result: list[str] = []
        for item in value:
            normalized = LocalStateService._text(item, field, max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
            if normalized not in result:
                result.append(normalized)
        return result

    @staticmethod
    def _campaign_text(value: object, field: str, *, max_length: int = MAX_SYNC_TEXT_LENGTH) -> str:
        """Validate campaign evidence text without treating prose as a path.

        The player-state domains use ``_sync_text`` because those values are
        also used as identifiers in a few UI/storage paths.  Campaign notes,
        prompts, explanations and timestamps are evidence, not paths, so they
        only need bounded UTF-8-safe text validation here.
        """

        if not isinstance(value, str):
            raise StateCommandError(f"{field} must be text")
        normalized = value.strip()
        if not normalized or len(normalized) > max_length or any(ord(character) < 32 for character in normalized):
            raise StateCommandError(f"{field} must be bounded text without control characters")
        return normalized

    @staticmethod
    def _campaign_multiline(value: object, field: str, *, max_bytes: int) -> str:
        """Validate bounded learner-authored code while preserving line breaks."""

        if not isinstance(value, str):
            raise StateCommandError(f"{field} must be text")
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        if not normalized.strip() or any(ord(character) < 32 and character not in {"\n", "\t"} for character in normalized):
            raise StateCommandError(f"{field} must be bounded text without control characters")
        if len(normalized.encode("utf-8")) > max_bytes:
            raise StateCommandError(f"{field} exceeds the bounded size")
        return normalized

    @classmethod
    def _campaign_identifier(cls, value: object, field: str) -> str:
        return cls._text(value, field, max_length=MAX_IDENTIFIER_LENGTH, identifier=True)

    @classmethod
    def _campaign_int(cls, value: object, field: str, *, maximum: int = MAX_SYNC_COUNTER) -> int:
        return cls._integer(value, field, minimum=0, maximum=maximum)

    @classmethod
    def _campaign_bool(cls, value: object, field: str) -> bool:
        if not isinstance(value, bool):
            raise StateCommandError(f"{field} must be a boolean")
        return value

    @classmethod
    def _campaign_mapping(cls, value: object, field: str, allowed: set[str]) -> dict[str, Any]:
        if not isinstance(value, Mapping):
            raise StateCommandError(f"{field} must be an object")
        extra = set(value) - allowed
        if extra:
            raise StateCommandError(f"Unsupported cloud campaign field(s) in {field}: {', '.join(sorted(extra))}")
        return dict(value)

    @classmethod
    def _campaign_text_list(
        cls,
        value: object,
        field: str,
        *,
        maximum: int,
        identifiers: bool = False,
        max_length: int = MAX_SYNC_TEXT_LENGTH,
    ) -> list[str]:
        if not isinstance(value, list) or len(value) > maximum:
            raise StateCommandError(f"{field} must be a bounded list")
        result: list[str] = []
        for index, item in enumerate(value):
            item_field = f"{field}[{index}]"
            normalized = cls._campaign_identifier(item, item_field) if identifiers else cls._campaign_text(item, item_field, max_length=max_length)
            if normalized not in result:
                result.append(normalized)
        return result

    @classmethod
    def _validate_campaign_projection(cls, campaign: object) -> dict[str, Any]:
        """Validate the bounded campaign evidence carried by cloud sync.

        This is deliberately separate from the player/equipment projection.
        It carries enough validated history for another device to render the
        same campaign, Codex and Dungeon checkpoint, while excluding local
        event logs, catalogs, profiles, answer keys and arbitrary JSON paths.
        """

        if not isinstance(campaign, Mapping):
            raise StateCommandError("Cloud campaign projection must be an object")
        extra = set(campaign) - SYNC_CAMPAIGN_FIELDS
        if extra:
            raise StateCommandError(f"Unsupported cloud campaign domain(s): {', '.join(sorted(extra))}")
        clean: dict[str, Any] = {}

        learning = campaign.get("learning_state")
        if learning is not None:
            raw = cls._campaign_mapping(learning, "campaign.learning_state", {"project", "concept", "phase", "reference_mode", "clean_clear_eligible"})
            item: dict[str, Any] = {}
            for field in ("project", "concept", "phase"):
                if field in raw:
                    item[field] = cls._campaign_text(raw[field], f"campaign.learning_state.{field}")
            for field in ("reference_mode", "clean_clear_eligible"):
                if field in raw:
                    item[field] = cls._campaign_bool(raw[field], f"campaign.learning_state.{field}")
            clean["learning_state"] = item

        streak = campaign.get("streak")
        if streak is not None:
            raw = cls._campaign_mapping(streak, "campaign.streak", {"current", "longest", "last_active", "freeze_tokens", "days_logged"})
            item = {}
            for field in ("current", "longest", "freeze_tokens"):
                if field in raw:
                    item[field] = cls._campaign_int(raw[field], f"campaign.streak.{field}")
            if "last_active" in raw and raw["last_active"] is not None:
                item["last_active"] = cls._campaign_text(raw["last_active"], "campaign.streak.last_active", max_length=40)
            if "days_logged" in raw:
                item["days_logged"] = cls._campaign_text_list(raw["days_logged"], "campaign.streak.days_logged", maximum=MAX_SYNC_LIST_ITEMS, max_length=40)
            clean["streak"] = item

        skills = campaign.get("skills")
        if skills is not None:
            if not isinstance(skills, list) or len(skills) > MAX_SYNC_SKILLS:
                raise StateCommandError("campaign.skills must be a bounded list")
            clean_skills: list[dict[str, Any]] = []
            for index, skill in enumerate(skills):
                raw = cls._campaign_mapping(skill, f"campaign.skills[{index}]", {"name", "concept", "status", "evidence", "interview_passes", "shield"})
                item = {}
                for field in ("name", "concept", "status"):
                    if field in raw:
                        item[field] = cls._campaign_text(raw[field], f"campaign.skills[{index}].{field}")
                for field in ("evidence", "interview_passes"):
                    if field in raw:
                        item[field] = cls._campaign_int(raw[field], f"campaign.skills[{index}].{field}")
                if "shield" in raw and raw["shield"] is not None:
                    shield = cls._campaign_mapping(raw["shield"], f"campaign.skills[{index}].shield", {"tier", "charges", "max_charges"})
                    clean_shield: dict[str, Any] = {}
                    if "tier" in shield:
                        clean_shield["tier"] = cls._campaign_text(shield["tier"], f"campaign.skills[{index}].shield.tier", max_length=40)
                    for field in ("charges", "max_charges"):
                        if field in shield:
                            clean_shield[field] = cls._campaign_int(shield[field], f"campaign.skills[{index}].shield.{field}")
                    item["shield"] = clean_shield
                clean_skills.append(item)
            clean["skills"] = clean_skills

        stats = campaign.get("stats")
        if stats is not None:
            allowed_stats = {
                "sessions", "projects_cleared", "bosses_defeated", "mobs_defeated", "interviews_passed",
                "interviews_failed", "mastery_shields_earned", "bugs_fixed", "explanations", "clean_clears",
                "commits_logged", "reference_mode_uses", "guided_milestones", "recovery_trials_passed", "guard_breaks",
                "creative_bonuses", "discoveries_unlocked",
            }
            raw = cls._campaign_mapping(stats, "campaign.stats", allowed_stats)
            clean["stats"] = {field: cls._campaign_int(raw[field], f"campaign.stats.{field}") for field in allowed_stats if field in raw}

        achievements = campaign.get("achievements")
        if achievements is not None:
            if not isinstance(achievements, list) or len(achievements) > MAX_SYNC_ACHIEVEMENTS:
                raise StateCommandError("campaign.achievements must be a bounded list")
            clean_achievements: list[dict[str, Any]] = []
            for index, achievement in enumerate(achievements):
                raw = cls._campaign_mapping(achievement, f"campaign.achievements[{index}]", {"name", "description", "unlocked"})
                item = {}
                for field in ("name", "description"):
                    if field in raw:
                        item[field] = cls._campaign_text(raw[field], f"campaign.achievements[{index}].{field}")
                if "unlocked" in raw:
                    item["unlocked"] = cls._campaign_bool(raw["unlocked"], f"campaign.achievements[{index}].unlocked")
                clean_achievements.append(item)
            clean["achievements"] = clean_achievements

        goals = campaign.get("goals")
        if goals is not None:
            raw_goals = cls._campaign_mapping(goals, "campaign.goals", {"daily", "weekly", "long_term"})
            clean_goals: dict[str, list[dict[str, Any]]] = {}
            for bucket in ("daily", "weekly", "long_term"):
                values = raw_goals.get(bucket)
                if values is None:
                    continue
                if not isinstance(values, list) or len(values) > MAX_SYNC_GOALS_PER_BUCKET:
                    raise StateCommandError(f"campaign.goals.{bucket} must be a bounded list")
                clean_bucket: list[dict[str, Any]] = []
                for index, goal in enumerate(values):
                    raw_goal = cls._campaign_mapping(goal, f"campaign.goals.{bucket}[{index}]", {"id", "text", "target", "progress", "reward_xp", "reward_coins", "done"})
                    item = {}
                    if "id" in raw_goal:
                        item["id"] = cls._campaign_identifier(raw_goal["id"], f"campaign.goals.{bucket}[{index}].id")
                    if "text" in raw_goal:
                        item["text"] = cls._campaign_text(raw_goal["text"], f"campaign.goals.{bucket}[{index}].text", max_length=400)
                    for field in ("target", "progress", "reward_xp", "reward_coins"):
                        if field in raw_goal:
                            item[field] = cls._campaign_int(raw_goal[field], f"campaign.goals.{bucket}[{index}].{field}")
                    if "done" in raw_goal:
                        item["done"] = cls._campaign_bool(raw_goal["done"], f"campaign.goals.{bucket}[{index}].done")
                    clean_bucket.append(item)
                clean_goals[bucket] = clean_bucket
            clean["goals"] = clean_goals

        projects = campaign.get("projects")
        if projects is not None:
            if not isinstance(projects, list) or len(projects) > MAX_SYNC_PROJECTS:
                raise StateCommandError("campaign.projects must be a bounded list")
            project_fields = {
                "order", "branch", "name", "status", "progress", "boss", "boss_status", "clean_clear_eligible",
                "completed", "completed_at", "clean_clear", "mob_sequence_complete", "creative_discoveries", "mobs", "boss_validation",
            }
            mob_fields = {"name", "status", "assist", "concept", "encounter", "max_resolve", "resolve", "impact_applied", "objective_attempts"}
            clean_projects: list[dict[str, Any]] = []
            for index, project in enumerate(projects):
                raw = cls._campaign_mapping(project, f"campaign.projects[{index}]", project_fields)
                item = {}
                for field in ("branch", "name", "status", "boss", "boss_status"):
                    if field in raw:
                        item[field] = cls._campaign_text(raw[field], f"campaign.projects[{index}].{field}")
                if "order" in raw:
                    item["order"] = cls._campaign_int(raw["order"], f"campaign.projects[{index}].order")
                if "progress" in raw:
                    item["progress"] = cls._campaign_int(raw["progress"], f"campaign.projects[{index}].progress", maximum=100)
                for field in ("clean_clear_eligible", "completed", "clean_clear", "mob_sequence_complete"):
                    if field in raw:
                        item[field] = cls._campaign_bool(raw[field], f"campaign.projects[{index}].{field}")
                if "completed_at" in raw and raw["completed_at"] is not None:
                    item["completed_at"] = cls._campaign_text(raw["completed_at"], f"campaign.projects[{index}].completed_at", max_length=80)
                if "creative_discoveries" in raw:
                    item["creative_discoveries"] = cls._campaign_text_list(raw["creative_discoveries"], f"campaign.projects[{index}].creative_discoveries", maximum=MAX_SYNC_LIST_ITEMS, max_length=240)
                if "boss_validation" in raw and raw["boss_validation"] is not None:
                    raw_validation = cls._campaign_mapping(raw["boss_validation"], f"campaign.projects[{index}].boss_validation", {"verified", "history", "completed_at"})
                    clean_validation: dict[str, Any] = {}
                    if "verified" in raw_validation:
                        clean_validation["verified"] = cls._campaign_text_list(
                            raw_validation["verified"],
                            f"campaign.projects[{index}].boss_validation.verified",
                            maximum=len(BOSS_REQUIREMENTS),
                            identifiers=True,
                        )
                        if any(item not in BOSS_REQUIREMENTS for item in clean_validation["verified"]):
                            raise StateCommandError(f"campaign.projects[{index}].boss_validation.verified contains an unknown phase")
                    if "completed_at" in raw_validation and raw_validation["completed_at"] is not None:
                        clean_validation["completed_at"] = cls._campaign_text(
                            raw_validation["completed_at"],
                            f"campaign.projects[{index}].boss_validation.completed_at",
                            max_length=80,
                        )
                    if "history" in raw_validation:
                        raw_history = raw_validation["history"]
                        if not isinstance(raw_history, list) or len(raw_history) > 20:
                            raise StateCommandError(f"campaign.projects[{index}].boss_validation.history must be bounded")
                        clean_history: list[dict[str, Any]] = []
                        for history_index, history_item in enumerate(raw_history):
                            raw_entry = cls._campaign_mapping(
                                history_item,
                                f"campaign.projects[{index}].boss_validation.history[{history_index}]",
                                {"requirement_id", "evidence_id", "reason", "recorded_at"},
                            )
                            clean_entry: dict[str, Any] = {}
                            for field in ("requirement_id", "evidence_id"):
                                if field in raw_entry:
                                    clean_entry[field] = cls._campaign_identifier(
                                        raw_entry[field],
                                        f"campaign.projects[{index}].boss_validation.history[{history_index}].{field}",
                                    )
                            for field in ("reason", "recorded_at"):
                                if field in raw_entry:
                                    clean_entry[field] = cls._campaign_text(
                                        raw_entry[field],
                                        f"campaign.projects[{index}].boss_validation.history[{history_index}].{field}",
                                        max_length=500,
                                    )
                            clean_history.append(clean_entry)
                        clean_validation["history"] = clean_history
                    item["boss_validation"] = clean_validation
                if "mobs" in raw:
                    values = raw["mobs"]
                    if not isinstance(values, list) or len(values) > MAX_SYNC_MOBS_PER_PROJECT:
                        raise StateCommandError(f"campaign.projects[{index}].mobs must be a bounded list")
                    clean_mobs: list[dict[str, Any]] = []
                    for mob_index, mob in enumerate(values):
                        raw_mob = cls._campaign_mapping(mob, f"campaign.projects[{index}].mobs[{mob_index}]", mob_fields)
                        clean_mob: dict[str, Any] = {}
                        for field in ("name", "status", "assist", "concept", "encounter"):
                            if field in raw_mob:
                                clean_mob[field] = cls._campaign_text(raw_mob[field], f"campaign.projects[{index}].mobs[{mob_index}].{field}", max_length=500)
                        for field in ("max_resolve", "resolve", "impact_applied", "objective_attempts"):
                            if field in raw_mob:
                                clean_mob[field] = cls._campaign_int(raw_mob[field], f"campaign.projects[{index}].mobs[{mob_index}].{field}")
                        clean_mobs.append(clean_mob)
                    item["mobs"] = clean_mobs
                clean_projects.append(item)
            clean["projects"] = clean_projects

        if "current_quest" in campaign and campaign["current_quest"] is not None:
            clean["current_quest"] = cls._campaign_text(campaign["current_quest"], "campaign.current_quest", max_length=400)

        codex = campaign.get("codex")
        if codex is not None:
            raw_codex = cls._campaign_mapping(codex, "campaign.codex", {"encounters"})
            encounters = raw_codex.get("encounters", [])
            if not isinstance(encounters, list) or len(encounters) > MAX_CODEX_RECORDS:
                raise StateCommandError("campaign.codex.encounters must be a bounded list")
            entry_fields = {"id", "project_id", "mob_name", "concept", "status", "question_types", "weaknesses", "notes", "player_notes", "code_snippet", "attempts", "results", "interview_history", "mastery"}
            clean_entries: list[dict[str, Any]] = []
            for index, entry in enumerate(encounters):
                raw = cls._campaign_mapping(entry, f"campaign.codex.encounters[{index}]", entry_fields)
                item = {}
                for field in ("id", "project_id"):
                    if field in raw:
                        item[field] = cls._campaign_identifier(raw[field], f"campaign.codex.encounters[{index}].{field}")
                for field in ("mob_name", "concept", "status"):
                    if field in raw:
                        item[field] = cls._campaign_text(raw[field], f"campaign.codex.encounters[{index}].{field}", max_length=300)
                for field in ("question_types", "weaknesses"):
                    if field in raw:
                        item[field] = cls._campaign_text_list(raw[field], f"campaign.codex.encounters[{index}].{field}", maximum=MAX_SYNC_CODEX_RESULTS, max_length=240)
                if "notes" in raw:
                    item["notes"] = cls._campaign_text_list(raw["notes"], f"campaign.codex.encounters[{index}].notes", maximum=MAX_CODEX_NOTES_PER_ENTRY, max_length=MAX_CODEX_NOTE_BYTES)
                if "player_notes" in raw:
                    item["player_notes"] = cls._campaign_text_list(raw["player_notes"], f"campaign.codex.encounters[{index}].player_notes", maximum=MAX_CODEX_NOTES_PER_ENTRY, max_length=MAX_CODEX_NOTE_BYTES)
                if "code_snippet" in raw and raw["code_snippet"] is not None:
                    item["code_snippet"] = cls._campaign_multiline(raw["code_snippet"], f"campaign.codex.encounters[{index}].code_snippet", max_bytes=MAX_CODEX_SNIPPET_BYTES)
                if "attempts" in raw:
                    item["attempts"] = cls._campaign_int(raw["attempts"], f"campaign.codex.encounters[{index}].attempts")
                for history_field in ("results", "interview_history"):
                    if history_field not in raw:
                        continue
                    values = raw[history_field]
                    if not isinstance(values, list) or len(values) > MAX_SYNC_CODEX_RESULTS:
                        raise StateCommandError(f"campaign.codex.encounters[{index}].{history_field} must be a bounded list")
                    clean_history: list[dict[str, Any]] = []
                    for result_index, result in enumerate(values):
                        raw_result = cls._campaign_mapping(result, f"campaign.codex.encounters[{index}].{history_field}[{result_index}]", {"outcome", "evidence_id", "reason", "recorded_at"})
                        clean_result: dict[str, Any] = {}
                        if "outcome" in raw_result:
                            clean_result["outcome"] = cls._campaign_identifier(raw_result["outcome"], f"campaign.codex.encounters[{index}].{history_field}[{result_index}].outcome")
                        if "evidence_id" in raw_result:
                            clean_result["evidence_id"] = cls._campaign_identifier(raw_result["evidence_id"], f"campaign.codex.encounters[{index}].{history_field}[{result_index}].evidence_id")
                        for field in ("reason", "recorded_at"):
                            if field in raw_result:
                                clean_result[field] = cls._campaign_text(raw_result[field], f"campaign.codex.encounters[{index}].{history_field}[{result_index}].{field}", max_length=500)
                        clean_history.append(clean_result)
                    item[history_field] = clean_history
                if "mastery" in raw and raw["mastery"] is not None:
                    mastery = cls._campaign_mapping(raw["mastery"], f"campaign.codex.encounters[{index}].mastery", {"evidence", "interview_passes", "shield", "tier", "charges", "max_charges"})
                    clean_mastery: dict[str, Any] = {}
                    for field in ("evidence", "interview_passes", "charges", "max_charges"):
                        if field in mastery:
                            clean_mastery[field] = cls._campaign_int(mastery[field], f"campaign.codex.encounters[{index}].mastery.{field}")
                    for field in ("shield", "tier"):
                        if field in mastery:
                            clean_mastery[field] = cls._campaign_text(mastery[field], f"campaign.codex.encounters[{index}].mastery.{field}", max_length=80)
                    item["mastery"] = clean_mastery
                clean_entries.append(item)
            clean["codex"] = {"encounters": clean_entries}

        dungeon = campaign.get("dungeon_run")
        if dungeon is not None:
            raw = cls._campaign_mapping(dungeon, "campaign.dungeon_run", {"status", "run_id", "seed", "class_id", "concept_id", "floor", "room", "room_type", "score", "run_coins", "started_at", "updated_at", "ended_at", "loadout", "inventory", "question", "question_number", "room_choices", "map", "risk_profile", "risk_status", "editor_content", "last_result", "history", "attempts"})
            item: dict[str, Any] = {}
            for field in ("status", "run_id", "seed", "class_id", "concept_id", "room_type"):
                if field in raw:
                    item[field] = cls._campaign_text(raw[field], f"campaign.dungeon_run.{field}", max_length=MAX_IDENTIFIER_LENGTH)
            for field in ("started_at", "updated_at", "ended_at"):
                if field in raw and raw[field] is not None:
                    item[field] = cls._campaign_text(raw[field], f"campaign.dungeon_run.{field}", max_length=80)
            for field in ("floor", "room", "score", "run_coins", "question_number", "attempts"):
                if field in raw:
                    item[field] = cls._campaign_int(raw[field], f"campaign.dungeon_run.{field}", maximum=MAX_DUNGEON_FLOOR if field in {"floor", "room"} else MAX_SYNC_COUNTER)
            if "loadout" in raw and raw["loadout"] is not None:
                loadout = cls._campaign_mapping(raw["loadout"], "campaign.dungeon_run.loadout", {"weapon", "armor", "trinket", "hp", "max_hp", "heals", "coins", "bandages", "rations", "vision_scrolls", "tonics", "edge_charges", "armor_guard"})
                clean_loadout: dict[str, Any] = {}
                for field in ("weapon", "armor", "trinket"):
                    if field in loadout and loadout[field] is not None:
                        clean_loadout[field] = cls._campaign_text(loadout[field], f"campaign.dungeon_run.loadout.{field}", max_length=MAX_IDENTIFIER_LENGTH)
                    elif field in loadout:
                        clean_loadout[field] = None
                for field in ("hp", "max_hp", "heals", "coins", "bandages", "rations", "vision_scrolls", "tonics", "edge_charges", "armor_guard"):
                    if field in loadout:
                        clean_loadout[field] = cls._campaign_int(loadout[field], f"campaign.dungeon_run.loadout.{field}")
                item["loadout"] = clean_loadout
            if "inventory" in raw and raw["inventory"] is not None:
                raw_inventory = raw["inventory"]
                if not isinstance(raw_inventory, list) or len(raw_inventory) > MAX_DUNGEON_INVENTORY:
                    raise StateCommandError("campaign.dungeon_run.inventory must be a bounded list")
                clean_inventory: list[dict[str, Any]] = []
                for index, entry in enumerate(raw_inventory):
                    raw_entry = cls._campaign_mapping(entry, f"campaign.dungeon_run.inventory[{index}]", {"id", "name", "kind", "weapon", "armor", "trinket", "description"})
                    clean_entry: dict[str, Any] = {}
                    for field in ("id", "kind"):
                        if field in raw_entry:
                            clean_entry[field] = cls._campaign_identifier(raw_entry[field], f"campaign.dungeon_run.inventory[{index}].{field}")
                    for field in ("name", "weapon", "armor", "trinket", "description"):
                        if field in raw_entry and raw_entry[field] is not None:
                            clean_entry[field] = cls._campaign_text(raw_entry[field], f"campaign.dungeon_run.inventory[{index}].{field}", max_length=300)
                    clean_inventory.append(clean_entry)
                item["inventory"] = clean_inventory
            if "question" in raw and raw["question"] is not None:
                question = cls._campaign_mapping(raw["question"], "campaign.dungeon_run.question", {"id", "question_type", "concept_id", "difficulty", "prompt", "options"})
                clean_question: dict[str, Any] = {}
                for field in ("id", "question_type", "concept_id"):
                    if field in question:
                        clean_question[field] = cls._campaign_text(question[field], f"campaign.dungeon_run.question.{field}", max_length=MAX_IDENTIFIER_LENGTH)
                if "difficulty" in question:
                    clean_question["difficulty"] = cls._campaign_int(question["difficulty"], "campaign.dungeon_run.question.difficulty", maximum=MAX_DUNGEON_DIFFICULTY)
                if "prompt" in question:
                    # Same rule as dungeon_issue_question: AI-written questions
                    # carry line breaks and fenced code snippets.
                    prompt = cls._multiline_text(question["prompt"], "campaign.dungeon_run.question.prompt", max_bytes=8_000).strip()
                    if not prompt:
                        raise StateCommandError("campaign.dungeon_run.question.prompt must not be empty")
                    clean_question["prompt"] = prompt
                if "options" in question:
                    clean_question["options"] = cls._campaign_text_list(question["options"], "campaign.dungeon_run.question.options", maximum=MAX_DUNGEON_OPTIONS, max_length=500)
                item["question"] = clean_question
            if "room_choices" in raw:
                choices = raw["room_choices"]
                if not isinstance(choices, list) or len(choices) > len(DUNGEON_ROUTE_CHOICES):
                    raise StateCommandError("campaign.dungeon_run.room_choices must be bounded")
                clean_choices: list[dict[str, Any]] = []
                for index, choice in enumerate(choices):
                    raw_choice = cls._campaign_mapping(choice, f"campaign.dungeon_run.room_choices[{index}]", {"id", "kind", "label", "description"})
                    clean_choice: dict[str, Any] = {}
                    for field in ("id", "kind"):
                        if field in raw_choice:
                            clean_choice[field] = cls._campaign_identifier(raw_choice[field], f"campaign.dungeon_run.room_choices[{index}].{field}")
                    for field in ("label", "description"):
                        if field in raw_choice:
                            clean_choice[field] = cls._campaign_text(raw_choice[field], f"campaign.dungeon_run.room_choices[{index}].{field}", max_length=300)
                    clean_choices.append(clean_choice)
                item["room_choices"] = clean_choices
            if "map" in raw and raw["map"] is not None:
                raw_map = cls._campaign_mapping(raw["map"], "campaign.dungeon_run.map", {"floor", "nodes", "edges", "current_node_id", "visited_node_ids"})
                clean_map: dict[str, Any] = {}
                if "floor" in raw_map:
                    clean_map["floor"] = cls._campaign_int(raw_map["floor"], "campaign.dungeon_run.map.floor", maximum=MAX_DUNGEON_FLOOR)
                for field in ("current_node_id",):
                    if field in raw_map and raw_map[field] is not None:
                        clean_map[field] = cls._campaign_identifier(raw_map[field], f"campaign.dungeon_run.map.{field}")
                if "visited_node_ids" in raw_map:
                    visited = raw_map["visited_node_ids"]
                    if not isinstance(visited, list) or len(visited) > 64:
                        raise StateCommandError("campaign.dungeon_run.map.visited_node_ids must be bounded")
                    clean_map["visited_node_ids"] = [cls._campaign_identifier(value, f"campaign.dungeon_run.map.visited_node_ids[{index}]") for index, value in enumerate(visited)]
                if "nodes" in raw_map:
                    nodes = raw_map["nodes"]
                    if not isinstance(nodes, list) or len(nodes) > 64:
                        raise StateCommandError("campaign.dungeon_run.map.nodes must be bounded")
                    clean_nodes: list[dict[str, Any]] = []
                    for index, node in enumerate(nodes):
                        raw_node = cls._campaign_mapping(node, f"campaign.dungeon_run.map.nodes[{index}]", {"id", "type", "row", "column", "label", "note"})
                        clean_node: dict[str, Any] = {}
                        for field in ("id", "type"):
                            if field in raw_node:
                                clean_node[field] = cls._campaign_identifier(raw_node[field], f"campaign.dungeon_run.map.nodes[{index}].{field}")
                        for field in ("row", "column"):
                            if field in raw_node:
                                clean_node[field] = cls._campaign_int(raw_node[field], f"campaign.dungeon_run.map.nodes[{index}].{field}", maximum=16)
                        for field in ("label", "note"):
                            if field in raw_node:
                                clean_node[field] = cls._campaign_text(raw_node[field], f"campaign.dungeon_run.map.nodes[{index}].{field}", max_length=120)
                        clean_nodes.append(clean_node)
                    clean_map["nodes"] = clean_nodes
                if "edges" in raw_map:
                    edges = raw_map["edges"]
                    if not isinstance(edges, Mapping) or len(edges) > 64:
                        raise StateCommandError("campaign.dungeon_run.map.edges must be bounded")
                    clean_map["edges"] = {
                        cls._campaign_identifier(key, f"campaign.dungeon_run.map.edges[{key}]"): [
                            cls._campaign_identifier(value, f"campaign.dungeon_run.map.edges[{key}][]")
                            for value in values
                        ]
                        for key, values in edges.items()
                        if isinstance(values, list) and len(values) <= 8
                    }
                item["map"] = clean_map
            if "risk_profile" in raw and raw["risk_profile"] is not None:
                profile = cls._campaign_mapping(raw["risk_profile"], "campaign.dungeon_run.risk_profile", {"kind", "room_type", "title", "preview"})
                item["risk_profile"] = {field: cls._campaign_text(profile[field], f"campaign.dungeon_run.risk_profile.{field}", max_length=300) for field in ("kind", "room_type", "title", "preview") if field in profile}
            if "risk_status" in raw and raw["risk_status"] is not None:
                item["risk_status"] = cls._campaign_identifier(raw["risk_status"], "campaign.dungeon_run.risk_status")
            if "editor_content" in raw:
                # Learner code: keep its line breaks, bounded like the editor save.
                item["editor_content"] = cls._campaign_multiline(raw["editor_content"], "campaign.dungeon_run.editor_content", max_bytes=MAX_DUNGEON_EDITOR_BYTES) if raw["editor_content"] else ""
            for field in ("last_result",):
                if field in raw and raw[field] is not None:
                    result = cls._campaign_mapping(raw[field], "campaign.dungeon_run.last_result", {"outcome", "question_id", "mob_name", "score_delta", "coins_delta", "damage", "evidence_id", "reason"})
                    clean_result: dict[str, Any] = {}
                    for text_field in ("outcome", "question_id", "mob_name", "evidence_id", "reason"):
                        if text_field in result:
                            clean_result[text_field] = cls._campaign_text(result[text_field], f"campaign.dungeon_run.last_result.{text_field}", max_length=500)
                    for number_field in ("score_delta", "coins_delta", "damage"):
                        if number_field in result:
                            clean_result[number_field] = cls._campaign_int(result[number_field], f"campaign.dungeon_run.last_result.{number_field}")
                    item[field] = clean_result
            if "history" in raw:
                history = raw["history"]
                if not isinstance(history, list) or len(history) > MAX_SYNC_DUNGEON_HISTORY:
                    raise StateCommandError("campaign.dungeon_run.history must be bounded")
                clean_history: list[dict[str, Any]] = []
                for index, entry in enumerate(history):
                    raw_entry = cls._campaign_mapping(entry, f"campaign.dungeon_run.history[{index}]", {"room", "floor", "question_id", "mob_name", "outcome", "evidence_id", "score_delta", "coins_delta", "damage"})
                    clean_entry: dict[str, Any] = {}
                    for number_field in ("room", "floor", "score_delta", "coins_delta", "damage"):
                        if number_field in raw_entry:
                            clean_entry[number_field] = cls._campaign_int(raw_entry[number_field], f"campaign.dungeon_run.history[{index}].{number_field}")
                    for text_field in ("question_id", "mob_name", "outcome", "evidence_id"):
                        if text_field in raw_entry:
                            clean_entry[text_field] = cls._campaign_text(raw_entry[text_field], f"campaign.dungeon_run.history[{index}].{text_field}", max_length=500)
                    clean_history.append(clean_entry)
                item["history"] = clean_history
            clean["dungeon_run"] = item
        elif "dungeon_run" in campaign:
            clean["dungeon_run"] = None

        leaderboard = campaign.get("dungeon_leaderboard")
        if leaderboard is not None:
            if not isinstance(leaderboard, list) or len(leaderboard) > MAX_DUNGEON_LEADERBOARD:
                raise StateCommandError("campaign.dungeon_leaderboard must be a bounded list")
            clean_board: list[dict[str, Any]] = []
            for index, entry in enumerate(leaderboard):
                raw = cls._campaign_mapping(entry, f"campaign.dungeon_leaderboard[{index}]", {"run_id", "score", "floor", "room", "status", "concept_id", "ended_at"})
                item = {}
                for field in ("run_id", "status", "concept_id", "ended_at"):
                    if field in raw:
                        item[field] = cls._campaign_text(raw[field], f"campaign.dungeon_leaderboard[{index}].{field}", max_length=MAX_IDENTIFIER_LENGTH)
                for field in ("score", "floor", "room"):
                    if field in raw:
                        item[field] = cls._campaign_int(raw[field], f"campaign.dungeon_leaderboard[{index}].{field}")
                clean_board.append(item)
            clean["dungeon_leaderboard"] = clean_board

        practice = campaign.get("practice_sessions")
        if practice is not None:
            if not isinstance(practice, list) or len(practice) > MAX_PRACTICE_SESSIONS:
                raise StateCommandError("campaign.practice_sessions must be a bounded list")
            clean_practice: list[dict[str, Any]] = []
            for index, session in enumerate(practice):
                raw = cls._campaign_mapping(session, f"campaign.practice_sessions[{index}]", {"session_id", "concept", "question_type", "difficulty", "status", "attempts", "correct", "started_at", "updated_at", "history"})
                item = {}
                for field in ("session_id", "question_type"):
                    if field in raw:
                        item[field] = cls._campaign_identifier(raw[field], f"campaign.practice_sessions[{index}].{field}")
                for field in ("concept", "status"):
                    if field in raw:
                        item[field] = cls._campaign_text(raw[field], f"campaign.practice_sessions[{index}].{field}")
                if "difficulty" in raw:
                    item["difficulty"] = cls._integer(raw["difficulty"], f"campaign.practice_sessions[{index}].difficulty", minimum=PRACTICE_DIFFICULTY_MIN, maximum=PRACTICE_DIFFICULTY_MAX)
                for field in ("attempts", "correct"):
                    if field in raw:
                        item[field] = cls._campaign_int(raw[field], f"campaign.practice_sessions[{index}].{field}")
                for field in ("started_at", "updated_at"):
                    if field in raw and raw[field] is not None:
                        item[field] = cls._campaign_text(raw[field], f"campaign.practice_sessions[{index}].{field}", max_length=80)
                if "history" in raw:
                    history = raw["history"]
                    if not isinstance(history, list) or len(history) > MAX_PRACTICE_ATTEMPTS_PER_SESSION:
                        raise StateCommandError(f"campaign.practice_sessions[{index}].history must be bounded")
                    clean_history: list[dict[str, Any]] = []
                    for attempt_index, attempt in enumerate(history):
                        raw_attempt = cls._campaign_mapping(attempt, f"campaign.practice_sessions[{index}].history[{attempt_index}]", {"outcome", "evidence_id", "reason", "recorded_at"})
                        clean_attempt: dict[str, Any] = {}
                        for field in ("outcome", "evidence_id"):
                            if field in raw_attempt:
                                clean_attempt[field] = cls._campaign_identifier(raw_attempt[field], f"campaign.practice_sessions[{index}].history[{attempt_index}].{field}")
                        for field in ("reason", "recorded_at"):
                            if field in raw_attempt:
                                clean_attempt[field] = cls._campaign_text(raw_attempt[field], f"campaign.practice_sessions[{index}].history[{attempt_index}].{field}", max_length=500)
                        clean_history.append(clean_attempt)
                    item["history"] = clean_history
                clean_practice.append(item)
            clean["practice_sessions"] = clean_practice

        try:
            size = len(json.dumps(clean, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        except (TypeError, ValueError) as exc:
            raise StateCommandError("Cloud campaign projection is not JSON serializable") from exc
        if size > MAX_SYNC_CAMPAIGN_BYTES:
            raise StateCommandError("Cloud campaign projection is too large")
        return clean

    @classmethod
    def _campaign_source_projection(cls, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Strip local-only keys before validating an existing save for sync."""

        def pick(value: object, fields: set[str]) -> dict[str, Any]:
            return {field: value[field] for field in fields if isinstance(value, Mapping) and field in value}

        campaign: dict[str, Any] = {}
        if isinstance(progress.get("learning_state"), Mapping):
            campaign["learning_state"] = pick(progress["learning_state"], {"project", "concept", "phase", "reference_mode", "clean_clear_eligible"})
        if isinstance(progress.get("streak"), Mapping):
            campaign["streak"] = pick(progress["streak"], {"current", "longest", "last_active", "freeze_tokens", "days_logged"})
        if isinstance(progress.get("skills"), list):
            campaign["skills"] = []
            for skill in progress["skills"]:
                if not isinstance(skill, Mapping):
                    continue
                item = pick(skill, {"name", "concept", "status", "evidence", "interview_passes"})
                if isinstance(skill.get("shield"), Mapping):
                    item["shield"] = pick(skill["shield"], {"tier", "charges", "max_charges"})
                campaign["skills"].append(item)
        if isinstance(progress.get("stats"), Mapping):
            campaign["stats"] = pick(
                progress["stats"],
                {
                    "sessions", "projects_cleared", "bosses_defeated", "mobs_defeated", "interviews_passed",
                    "interviews_failed", "mastery_shields_earned", "bugs_fixed", "explanations", "clean_clears",
                    "commits_logged", "reference_mode_uses", "guided_milestones", "recovery_trials_passed",
                    "creative_bonuses", "discoveries_unlocked", "guard_breaks",
                },
            )
        if isinstance(progress.get("achievements"), list):
            campaign["achievements"] = [pick(item, {"name", "description", "unlocked"}) for item in progress["achievements"] if isinstance(item, Mapping)]
        if isinstance(progress.get("goals"), Mapping):
            campaign["goals"] = {
                bucket: [
                    pick(item, {"id", "text", "target", "progress", "reward_xp", "reward_coins", "done"})
                    for item in progress["goals"].get(bucket, [])
                    if isinstance(item, Mapping)
                ]
                for bucket in ("daily", "weekly", "long_term")
                if isinstance(progress["goals"].get(bucket), list)
            }
        if isinstance(progress.get("projects"), list):
            project_fields = {
                "order", "branch", "name", "status", "progress", "boss", "boss_status", "clean_clear_eligible",
                "completed", "completed_at", "clean_clear", "mob_sequence_complete", "creative_discoveries", "boss_validation",
            }
            mob_fields = {"name", "status", "assist", "concept", "encounter", "max_resolve", "resolve", "impact_applied", "objective_attempts"}
            campaign["projects"] = []
            for project in progress["projects"]:
                if not isinstance(project, Mapping):
                    continue
                item = pick(project, project_fields)
                if isinstance(project.get("boss_validation"), Mapping):
                    validation = project["boss_validation"]
                    item["boss_validation"] = pick(validation, {"verified", "completed_at"})
                    if isinstance(validation.get("history"), list):
                        item["boss_validation"]["history"] = [
                            pick(entry, {"requirement_id", "evidence_id", "reason", "recorded_at"})
                            for entry in validation["history"]
                            if isinstance(entry, Mapping)
                        ][-20:]
                if isinstance(project.get("mobs"), list):
                    item["mobs"] = cls._compact_sync_mobs(project, [pick(mob, mob_fields) for mob in project["mobs"] if isinstance(mob, Mapping)])
                campaign["projects"].append(item)
        if "current_quest" in progress:
            campaign["current_quest"] = progress.get("current_quest")
        if isinstance(progress.get("codex"), Mapping):
            codex = {"encounters": []}
            for entry in progress["codex"].get("encounters", []):
                if not isinstance(entry, Mapping):
                    continue
                item = pick(entry, {"id", "project_id", "mob_name", "concept", "status", "question_types", "weaknesses", "notes", "player_notes", "code_snippet", "attempts"})
                for history_field in ("results", "interview_history"):
                    if isinstance(entry.get(history_field), list):
                        item[history_field] = [pick(result, {"outcome", "evidence_id", "reason", "recorded_at"}) for result in entry[history_field] if isinstance(result, Mapping)]
                if isinstance(entry.get("mastery"), Mapping):
                    item["mastery"] = pick(entry["mastery"], {"evidence", "interview_passes", "shield", "tier", "charges", "max_charges"})
                codex["encounters"].append(item)
            campaign["codex"] = codex
        if "dungeon_run" in progress:
            raw_run = progress.get("dungeon_run")
            if raw_run is None:
                campaign["dungeon_run"] = None
            elif isinstance(raw_run, Mapping):
                run_fields = {"status", "run_id", "seed", "class_id", "concept_id", "floor", "room", "room_type", "score", "run_coins", "started_at", "updated_at", "ended_at", "question_number", "editor_content", "attempts", "risk_profile", "risk_status"}
                item = pick(raw_run, run_fields)
                if isinstance(raw_run.get("loadout"), Mapping):
                    item["loadout"] = pick(raw_run["loadout"], {"weapon", "armor", "trinket", "hp", "max_hp", "heals", "coins", "bandages", "rations", "vision_scrolls", "tonics", "edge_charges", "armor_guard"})
                if isinstance(raw_run.get("inventory"), list):
                    item["inventory"] = [pick(entry, {"id", "name", "kind", "armor", "trinket", "description"}) for entry in raw_run["inventory"] if isinstance(entry, Mapping)]
                if isinstance(raw_run.get("question"), Mapping):
                    item["question"] = pick(raw_run["question"], {"id", "question_type", "concept_id", "difficulty", "prompt", "options"})
                elif "question" in raw_run:
                    item["question"] = None
                if isinstance(raw_run.get("room_choices"), list):
                    item["room_choices"] = [pick(choice, {"id", "kind", "label", "description"}) for choice in raw_run["room_choices"] if isinstance(choice, Mapping)]
                if isinstance(raw_run.get("map"), Mapping):
                    raw_map = raw_run["map"]
                    item["map"] = {
                        "floor": raw_map.get("floor"),
                        "current_node_id": raw_map.get("current_node_id"),
                        "visited_node_ids": list(raw_map.get("visited_node_ids") or []),
                        "nodes": [pick(node, {"id", "type", "row", "column", "label", "note"}) for node in raw_map.get("nodes", []) if isinstance(node, Mapping)],
                        "edges": {str(key): [str(value) for value in values] for key, values in (raw_map.get("edges") or {}).items() if isinstance(values, list)},
                    }
                if "editor_content" not in item:
                    item["editor_content"] = ""
                if isinstance(raw_run.get("last_result"), Mapping):
                    item["last_result"] = pick(raw_run["last_result"], {"outcome", "question_id", "mob_name", "score_delta", "coins_delta", "damage", "evidence_id", "reason"})
                if isinstance(raw_run.get("history"), list):
                    item["history"] = [pick(entry, {"room", "floor", "question_id", "mob_name", "outcome", "evidence_id", "score_delta", "coins_delta", "damage"}) for entry in raw_run["history"] if isinstance(entry, Mapping)]
                campaign["dungeon_run"] = item
        if isinstance(progress.get("dungeon_leaderboard"), list):
            campaign["dungeon_leaderboard"] = [
                pick(item, {"run_id", "score", "floor", "room", "status", "concept_id", "ended_at"})
                for item in progress["dungeon_leaderboard"]
                if isinstance(item, Mapping)
            ]
        if "practice_sessions" in progress:
            campaign["practice_sessions"] = cls.practice_projection(progress).get("sessions", [])
        return campaign

    @classmethod
    def _validate_sync_projection(cls, projection: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(projection, Mapping):
            raise StateCommandError("Cloud state projection must be an object")
        unknown = set(projection) - {"player", "equipment", "companion", "homestead", "campaign"}
        if unknown:
            raise StateCommandError(f"Unsupported cloud state domain(s): {', '.join(sorted(unknown))}")

        validated: dict[str, Any] = {}
        player = projection.get("player")
        if player is not None:
            if not isinstance(player, Mapping):
                raise StateCommandError("Cloud player projection must be an object")
            extra = set(player) - SYNC_PLAYER_FIELDS
            if extra:
                raise StateCommandError(f"Unsupported cloud player field(s): {', '.join(sorted(extra))}")
            clean_player: dict[str, Any] = {}
            text_fields = {"name", "title", "rank"}
            integer_limits = {
                "level": (1, MAX_SYNC_LEVEL),
                "xp": (0, MAX_SYNC_COUNTER),
                "xp_next": (1, MAX_SYNC_COUNTER),
                "lifetime_xp": (0, MAX_SYNC_COUNTER),
                "hp": (0, MAX_SYNC_COUNTER),
                "max_hp": (1, MAX_SYNC_COUNTER),
                "coins": (0, MAX_SYNC_COUNTER),
                "potions": (0, MAX_SYNC_COUNTER),
            }
            for field in text_fields:
                if field in player:
                    clean_player[field] = cls._sync_text(player[field], f"player.{field}")
            for field, (minimum, maximum) in integer_limits.items():
                if field in player:
                    clean_player[field] = cls._integer(player[field], f"player.{field}", minimum=minimum, maximum=maximum)
            if "xp" in clean_player and "xp_next" in clean_player and clean_player["xp"] >= clean_player["xp_next"]:
                raise StateCommandError("player.xp must be below player.xp_next")
            if "hp" in clean_player and "max_hp" in clean_player and clean_player["hp"] > clean_player["max_hp"]:
                raise StateCommandError("player.hp must not exceed player.max_hp")
            validated["player"] = clean_player

        equipment = projection.get("equipment")
        if equipment is not None:
            if not isinstance(equipment, Mapping):
                raise StateCommandError("Cloud equipment projection must be an object")
            extra = set(equipment) - SYNC_EQUIPMENT_FIELDS
            if extra:
                raise StateCommandError(f"Unsupported cloud equipment field(s): {', '.join(sorted(extra))}")
            clean_equipment: dict[str, Any] = {}
            for field in ("armor", "trinket", "title"):
                if field in equipment:
                    clean_equipment[field] = cls._sync_text(equipment[field], f"equipment.{field}")
            for field in SYNC_EQUIPMENT_LIST_FIELDS:
                if field in equipment:
                    values = cls._sync_list(equipment[field], f"equipment.{field}")
                    if any(item_id not in EQUIPMENT_BY_ID for item_id in values):
                        raise StateCommandError(f"equipment.{field} contains an unknown item")
                    clean_equipment[field] = values[:MAX_EQUIPMENT_ITEMS]
            if "avatar" in equipment:
                clean_equipment["avatar"] = cls._avatar_value(equipment["avatar"], "equipment.avatar")
            validated["equipment"] = clean_equipment

        companion = projection.get("companion")
        if companion is not None:
            if not isinstance(companion, Mapping):
                raise StateCommandError("Cloud companion projection must be an object")
            extra = set(companion) - SYNC_COMPANION_FIELDS
            if extra:
                raise StateCommandError(f"Unsupported cloud companion field(s): {', '.join(sorted(extra))}")
            clean_companion: dict[str, Any] = {}
            for field in ("name", "form", "next_form", "next_form_requirement"):
                if field in companion:
                    clean_companion[field] = cls._sync_text(companion[field], f"companion.{field}")
            for field in ("level", "bond", "energy", "max_energy", "fed_count", "training_count"):
                if field in companion:
                    clean_companion[field] = cls._integer(companion[field], f"companion.{field}", minimum=0, maximum=MAX_SYNC_COUNTER)
            if "energy" in clean_companion and "max_energy" in clean_companion and clean_companion["energy"] > clean_companion["max_energy"]:
                raise StateCommandError("companion.energy must not exceed companion.max_energy")
            validated["companion"] = clean_companion

        homestead = projection.get("homestead")
        if homestead is not None:
            if not isinstance(homestead, Mapping):
                raise StateCommandError("Cloud Homestead projection must be an object")
            extra = set(homestead) - SYNC_HOMESTEAD_FIELDS
            if extra:
                raise StateCommandError(f"Unsupported cloud Homestead field(s): {', '.join(sorted(extra))}")
            clean_homestead: dict[str, Any] = {}
            if "room_levels" in homestead:
                try:
                    clean_homestead["room_levels"] = validate_room_levels(homestead["room_levels"])
                except ValueError as exc:
                    raise StateCommandError(str(exc)) from exc
            if "name" in homestead:
                clean_homestead["name"] = cls._sync_text(homestead["name"], "homestead.name")
            owned = cls._sync_list(homestead["owned_cosmetics"], "homestead.owned_cosmetics") if "owned_cosmetics" in homestead else None
            if owned is not None:
                clean_homestead["owned_cosmetics"] = owned
            room_upgrades = cls._sync_list(homestead["room_upgrades"], "homestead.room_upgrades") if "room_upgrades" in homestead else None
            if room_upgrades is not None:
                invalid_upgrades = [item for item in room_upgrades if item not in HOME_ROOM_UPGRADE_BY_ID]
                if invalid_upgrades:
                    raise StateCommandError("homestead.room_upgrades contains an unknown upgrade")
                clean_homestead["room_upgrades"] = room_upgrades[:len(HOME_ROOM_UPGRADE_CATALOG)]
            market_purchases = cls._sync_list(homestead["market_purchases"], "homestead.market_purchases") if "market_purchases" in homestead else None
            if market_purchases is not None:
                unknown_market_items = [item for item in market_purchases if item not in CAMPAIGN_MARKET_BY_ID]
                if unknown_market_items:
                    raise StateCommandError("homestead.market_purchases contains an unknown market lot")
                clean_homestead["market_purchases"] = market_purchases[:len(CAMPAIGN_MARKET_CATALOG)]
            if "upgrade_tokens" in homestead:
                clean_homestead["upgrade_tokens"] = cls._campaign_int(homestead["upgrade_tokens"], "homestead.upgrade_tokens")
            if "upgrade_effects" in homestead:
                effects = cls._campaign_mapping(homestead["upgrade_effects"], "homestead.upgrade_effects", {"max_hp_delta", "failure_damage_reduction", "resolve_impact_delta", "guard_break_heal", "meal_heal_delta"})
                clean_homestead["upgrade_effects"] = {
                    field: cls._campaign_int(effects[field], f"homestead.upgrade_effects.{field}")
                    for field in ("max_hp_delta", "failure_damage_reduction", "resolve_impact_delta", "guard_break_heal", "meal_heal_delta")
                    if field in effects
                }
            equipped = homestead.get("equipped")
            if equipped is not None:
                if not isinstance(equipped, Mapping):
                    raise StateCommandError("homestead.equipped must be an object")
                extra_equipped = set(equipped) - SYNC_HOMESTEAD_EQUIPPED_FIELDS
                if extra_equipped:
                    raise StateCommandError(
                        f"Unsupported cloud equipped field(s): {', '.join(sorted(extra_equipped))}"
                    )
                clean_equipped = {
                    field: cls._text(equipped[field], f"homestead.equipped.{field}", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
                    for field in SYNC_HOMESTEAD_EQUIPPED_FIELDS
                    if field in equipped
                }
                clean_homestead["equipped"] = clean_equipped
                if owned is not None and any(item_id not in owned for item_id in clean_equipped.values()):
                    raise StateCommandError("Every equipped cosmetic must be owned")
            validated["homestead"] = clean_homestead

        if "campaign" in projection:
            validated["campaign"] = cls._validate_campaign_projection(projection.get("campaign"))

        return validated

    @classmethod
    def _sync_projection(cls, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Build a JSON-safe allowlisted projection; static catalogs stay local."""

        def copy_fields(container: object, fields: frozenset[str]) -> dict[str, Any]:
            if not isinstance(container, Mapping):
                return {}
            return {field: container[field] for field in fields if field in container}

        player = copy_fields(progress.get("player"), SYNC_PLAYER_FIELDS)
        equipment = copy_fields(progress.get("equipment"), SYNC_EQUIPMENT_FIELDS)
        for field in SYNC_EQUIPMENT_LIST_FIELDS:
            if isinstance(equipment.get(field), list):
                equipment[field] = [
                    item for item in equipment[field]
                    if isinstance(item, str) and item in EQUIPMENT_BY_ID
                ][:MAX_EQUIPMENT_ITEMS]
            else:
                equipment.pop(field, None)
        companion = copy_fields(progress.get("companion"), SYNC_COMPANION_FIELDS)
        homestead_source = progress.get("homestead")
        homestead = copy_fields(homestead_source, frozenset({"name", "owned_cosmetics", "equipped", "room_upgrades", "upgrade_tokens", "upgrade_effects", "market_purchases"}))
        try:
            homestead["room_levels"] = effective_room_levels(progress)
        except ValueError as exc:
            raise StateCommandError(str(exc), status_code=500) from exc
        if isinstance(homestead.get("owned_cosmetics"), list):
            homestead["owned_cosmetics"] = [
                item for item in homestead["owned_cosmetics"] if isinstance(item, str)
            ][:MAX_SYNC_LIST_ITEMS]
        else:
            homestead.pop("owned_cosmetics", None)
        if isinstance(homestead.get("equipped"), Mapping):
            homestead["equipped"] = {
                field: value
                for field, value in homestead["equipped"].items()
                if field in SYNC_HOMESTEAD_EQUIPPED_FIELDS and isinstance(value, str)
            }
        else:
            homestead.pop("equipped", None)
        if isinstance(homestead.get("room_upgrades"), list):
            homestead["room_upgrades"] = [item for item in homestead["room_upgrades"] if isinstance(item, str) and item in HOME_ROOM_UPGRADE_BY_ID][:len(HOME_ROOM_UPGRADE_CATALOG)]
        else:
            homestead.pop("room_upgrades", None)
        if isinstance(homestead.get("market_purchases"), list):
            homestead["market_purchases"] = [item for item in homestead["market_purchases"] if isinstance(item, str) and item in CAMPAIGN_MARKET_BY_ID][:len(CAMPAIGN_MARKET_CATALOG)]
        else:
            homestead.pop("market_purchases", None)
        if "upgrade_tokens" in homestead:
            try:
                homestead["upgrade_tokens"] = max(0, min(MAX_SYNC_COUNTER, int(homestead["upgrade_tokens"])))
            except (TypeError, ValueError):
                homestead.pop("upgrade_tokens", None)
        if isinstance(homestead.get("upgrade_effects"), Mapping):
            homestead["upgrade_effects"] = {
                field: max(0, min(MAX_SYNC_COUNTER, int(value)))
                for field, value in homestead["upgrade_effects"].items()
                if field in {"max_hp_delta", "failure_damage_reduction", "resolve_impact_delta", "guard_break_heal", "meal_heal_delta"}
                and isinstance(value, int)
            }
        else:
            homestead.pop("upgrade_effects", None)
        campaign_source = cls._campaign_source_projection(progress)
        campaign = cls._validate_campaign_projection(campaign_source)
        return {"player": player, "equipment": equipment, "companion": companion, "homestead": homestead, "campaign": campaign}

    @classmethod
    def _merge_sync_projection(cls, progress: dict[str, Any], projection: Mapping[str, Any]) -> list[str]:
        validated = cls._validate_sync_projection(projection)
        changed_domains: list[str] = []
        for domain, fields in (
            ("player", SYNC_PLAYER_FIELDS),
            ("equipment", SYNC_EQUIPMENT_FIELDS),
            ("companion", SYNC_COMPANION_FIELDS),
        ):
            incoming = validated.get(domain)
            if not isinstance(incoming, Mapping):
                continue
            target = cls._dict(progress, domain)
            if domain == "player":
                merged_xp = incoming.get("xp", target.get("xp"))
                merged_xp_next = incoming.get("xp_next", target.get("xp_next"))
                if isinstance(merged_xp, int) and isinstance(merged_xp_next, int) and merged_xp >= merged_xp_next:
                    raise StateCommandError("player.xp must be below player.xp_next")
                merged_hp = incoming.get("hp", target.get("hp"))
                merged_max_hp = incoming.get("max_hp", target.get("max_hp"))
                if isinstance(merged_hp, int) and isinstance(merged_max_hp, int) and merged_hp > merged_max_hp:
                    raise StateCommandError("player.hp must not exceed player.max_hp")
            changed = False
            for field in fields:
                if field in incoming and target.get(field) != incoming[field]:
                    target[field] = incoming[field]
                    changed = True
            if changed:
                changed_domains.append(domain)

        incoming_home = validated.get("homestead")
        if isinstance(incoming_home, Mapping):
            target_home = cls._dict(progress, "homestead")
            owned_source = incoming_home.get("owned_cosmetics", target_home.get("owned_cosmetics", []))
            owned = {item for item in owned_source if isinstance(item, str)} if isinstance(owned_source, list) else set()
            incoming_equipped = incoming_home.get("equipped", target_home.get("equipped", {}))
            if isinstance(incoming_equipped, Mapping) and any(item_id not in owned for item_id in incoming_equipped.values()):
                raise StateCommandError("Every equipped cosmetic must be owned")
            changed = False
            for field in ("name", "owned_cosmetics", "equipped", "room_upgrades", "room_levels", "upgrade_tokens", "upgrade_effects", "market_purchases"):
                if field in incoming_home and target_home.get(field) != incoming_home[field]:
                    target_home[field] = incoming_home[field]
                    changed = True
            if changed:
                changed_domains.append("homestead")

        incoming_campaign = validated.get("campaign")
        if isinstance(incoming_campaign, Mapping):
            changed = False
            for field in SYNC_CAMPAIGN_FIELDS:
                if field not in incoming_campaign:
                    continue
                incoming_value = incoming_campaign[field]
                if field in {"learning_state", "streak", "stats"} and isinstance(incoming_value, Mapping):
                    existing_value = progress.get(field)
                    merged_value = dict(existing_value) if isinstance(existing_value, Mapping) else {}
                    merged_value.update(incoming_value)
                    if merged_value != existing_value:
                        progress[field] = merged_value
                        changed = True
                elif progress.get(field) != incoming_value:
                    progress[field] = incoming_value
                    changed = True
            if changed:
                changed_domains.append("campaign")
        return changed_domains

    @staticmethod
    def _boss_validation_projection(project: Mapping[str, Any]) -> dict[str, Any]:
        """Return safe boss phases without projecting provider prompts."""

        gauntlet = boss_gauntlet(project)
        raw = project.get("boss_validation")
        verified = raw.get("verified") if isinstance(raw, Mapping) else []
        if not isinstance(verified, list):
            verified = []
        # Preserve this boss's gauntlet order even if an older local
        # checkpoint recorded them in a different order.
        verified_ids = [item for item in gauntlet if item in verified]
        remaining = [item for item in gauntlet if item not in verified_ids]
        status = str(project.get("boss_status") or "locked")
        if status == "defeated" or project.get("completed") is True:
            phase = "complete"
        elif remaining:
            phase = remaining[0]
        else:
            phase = "ready_to_clear"
        boss_name = str(project.get("boss") or "Campaign boss")[:MAX_IDENTIFIER_LENGTH]
        project_name = str(project.get("name") or project.get("branch") or "this chapter")[:MAX_REASON_LENGTH]
        story_entry = load_campaign_bounties().get(str(project.get("branch") or ""))
        story_entry = story_entry if isinstance(story_entry, Mapping) else {}
        configured_lore = project.get("boss_lore") or story_entry.get("boss_lore")
        configured_brief = project.get("boss_brief") or story_entry.get("boss_brief")
        boss_lore = (
            str(configured_lore).strip()[:MAX_REASON_LENGTH]
            if isinstance(configured_lore, str) and configured_lore.strip()
            else f"{boss_name} guards the final boundary of {project_name}."
        )
        boss_brief = (
            str(configured_brief).strip()[:MAX_REASON_LENGTH]
            if isinstance(configured_brief, str) and configured_brief.strip()
            else "Break the gate one verified goal at a time. The next goal appears only after the current one is validated."
        )
        configured_twist = project.get("boss_twist") or story_entry.get("boss_twist")
        authored_quests = {
            "required_behavior": str(configured_brief).strip() if isinstance(configured_brief, str) and configured_brief.strip() else "",
            "edge_cases": str(configured_twist).strip() if isinstance(configured_twist, str) and configured_twist.strip() else "",
        }
        authored_phases = project.get("boss_phases") or story_entry.get("boss_phases")
        authored_phases = authored_phases if isinstance(authored_phases, Mapping) else {}
        requirement_projection: list[dict[str, Any]] = []
        max_resolve = 0
        resolved_damage = 0
        for requirement_id in gauntlet:
            spec = dict(BOSS_REQUIREMENT_SPECS.get(requirement_id, {}))
            if authored_quests.get(requirement_id):
                spec["quest"] = authored_quests[requirement_id]
            authored = authored_phases.get(requirement_id)
            if isinstance(authored, Mapping):
                for field in ("label", "quest"):
                    if isinstance(authored.get(field), str) and authored[field].strip():
                        spec[field] = authored[field].strip()
            try:
                impact = max(1, min(MAX_IMPACT, int(spec.get("impact", 1))))
            except (TypeError, ValueError):
                impact = 1
            max_resolve += impact
            is_verified = requirement_id in verified_ids
            if is_verified:
                resolved_damage += impact
            requirement_projection.append(
                {
                    "id": requirement_id,
                    "label": str(spec.get("label") or BOSS_PHASE_LABELS.get(requirement_id) or requirement_id.replace("_", " ").title()),
                    "question_type": str(spec.get("question_type") or "verified"),
                    "impact": impact,
                    "damage": impact,
                    "brief": str(spec.get("brief") or "Submit evidence for the current boss goal.")[:MAX_REASON_LENGTH],
                    "quest": str(spec.get("quest") or spec.get("brief") or "Complete the current boss goal.")[:1_000],
                    "status": "verified" if is_verified else ("current" if requirement_id == phase else "locked"),
                }
            )
        current_requirement = next(
            (item for item in requirement_projection if item["id"] == phase),
            None,
        )
        boss_max_resolve = max(1, max_resolve)
        boss_resolve = 0 if phase in {"ready_to_clear", "complete"} else max(0, boss_max_resolve - resolved_damage)
        reward_envelope = dict(BOSS_REWARD_ENVELOPE)
        special = campaign_special_mechanic(project)
        return {
            "boss_active": LocalStateService._boss_is_active({"projects": [{**project, "status": "active"}]}),
            "boss_attempt_id": next((entry.get("evidence_id") for entry in reversed(raw.get("history", [])) if isinstance(entry, Mapping) and entry.get("requirement_id") == "boss_begin"), None) if isinstance(raw, Mapping) and isinstance(raw.get("history"), list) else None,
            "verified_boss_requirements": verified_ids,
            "remaining_boss_requirements": remaining,
            "boss_phase": phase,
            "boss_phase_label": BOSS_PHASE_LABELS.get(phase, "Boss validation complete" if phase == "ready_to_clear" else "Boss clear"),
            "boss_lore": boss_lore,
            "boss_brief": boss_brief,
            "boss_max_resolve": boss_max_resolve,
            "boss_resolve": boss_resolve,
            "boss_current_requirement": current_requirement if phase in gauntlet else None,
            "current_quest": current_requirement if phase in gauntlet else None,
            "boss_requirements_projection": requirement_projection,
            "mechanics": [dict(item) for item in ENCOUNTER_MECHANICS],
            "special_mechanic": {**special, "triggered": special["trigger"] in verified_ids} if special else None,
            "reward_envelope": reward_envelope,
        }

    def encounter_projection(self, progress: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return the validated, non-secret projection for the active encounter.

        The frontend receives this alongside the campaign snapshot instead of
        re-deriving Impact or Resolve from a duplicated rules table.  Only the
        current allowed objective identifiers/types are exposed; future locked
        encounter prompts and answers never leave the state service.
        """

        projects = progress.get("projects")
        if not isinstance(projects, list):
            return None
        project = next((item for item in projects if isinstance(item, dict) and item.get("status") == "active"), None)
        if project is None:
            # Every project is cleared: report the most recent clear as the
            # finished campaign instead of no encounter at all.
            finished = [item for item in projects if isinstance(item, dict) and item.get("completed") is True]
            project = max(finished, key=lambda item: str(item.get("completed_at") or ""), default=None)
        if project is None:
            return None
        mobs = project.get("mobs")
        if not isinstance(mobs, list) or not all(isinstance(item, dict) for item in mobs):
            return None
        index = next((i for i, item in enumerate(mobs) if item.get("status") == "available"), None)
        if index is None:
            index = next((i for i, item in enumerate(mobs) if item.get("status") not in {"defeated", "cleared"}), None)
        if index is None:
            project_completed = project.get("completed") is True or project.get("boss_status") == "defeated"
            boss_status = str(project.get("boss_status") or ("available" if not project_completed else "defeated"))
            boss_validation = self._boss_validation_projection(project)
            return {
                "project_id": self._project_id(project),
                "project_name": str(project.get("name") or project.get("branch") or ""),
                "project_progress": project.get("progress", 100),
                "project_status": str(project.get("status") or "active"),
                "project_complete": project_completed,
                "mob_sequence_complete": True,
                "boss": str(project.get("boss") or ""),
                "boss_status": boss_status,
                "boss_requirements": list(boss_gauntlet(project)),
                **boss_validation,
                "mob_name": None,
                "mob_index": None,
                "status": "complete" if project_completed else "boss_available",
                "resolve": boss_validation["boss_resolve"],
                "max_resolve": boss_validation["boss_max_resolve"],
                "completed_objectives": [],
                "available_objectives": [],
                "attempts": 0,
                "question_types": [],
                "mob": None,
                "mechanics": [dict(item) for item in ENCOUNTER_MECHANICS],
                "current_quest": boss_validation.get("current_quest"),
                # The envelope is the only reward preview exposed to the UI;
                # the clear mutation remains the authority for the actual
                # reward and any unlocks.
                "reward_envelope": boss_validation["reward_envelope"],
            }

        mob = mobs[index]
        profile = self._encounter_profile(index, project, mob)
        try:
            project_id = self._project_id(project)
            mob_name = self._text(mob.get("name", ""), "mob_name", max_length=MAX_IDENTIFIER_LENGTH)
        except StateCommandError:
            return None
        existing = progress.get("encounter_state")
        matching = (
            existing
            if isinstance(existing, dict)
            and existing.get("project_id") == project_id
            and existing.get("mob_name") == mob_name
            else {}
        )
        try:
            max_resolve = max(1, int(matching.get("max_resolve", mob.get("max_resolve", profile["max_resolve"]))))
            resolve = max(0, min(max_resolve, int(matching.get("resolve", mob.get("resolve", max_resolve)))))
        except (TypeError, ValueError):
            max_resolve = int(profile["max_resolve"])
            resolve = max_resolve
        completed = matching.get("completed_objectives")
        completed_ids = [item for item in completed if isinstance(item, str)][:20] if isinstance(completed, list) else []
        concept = str(mob.get("concept") or "Current campaign concept")
        encounter_brief = str(
            mob.get("encounter")
            or f"Reason about {concept.lower()} using your own project evidence."
        )
        contract = campaign_contract(project.get("branch"), mob.get("name")) or {}
        special = campaign_special_mechanic(project, mob_name)
        encounter_lore = str(
            mob.get("lore")
            or mob.get("background")
            or contract.get("contract")
            or f"A bounded field encounter testing {concept.lower()}."
        )
        contract_sign = contract.get("sign") if isinstance(contract.get("sign"), str) else None
        available = [
            {
                "id": objective_id,
                "label": str(definition.get("label") or objective_id.replace("_", " ").title()),
                "brief": str(definition.get("brief") or "Submit your own evidence for this objective."),
                "impact": int(definition["impact"]),
                "question_type": str(definition["question_type"]),
                **({"file": definition["file"]} if definition.get("file") else {}),
                **({"see": list(definition["see"])} if definition.get("see") else {}),
                **({"check": dict(definition["check"])} if definition.get("check") else {}),
            }
            for objective_id, definition in profile["objectives"].items()
            if objective_id not in completed_ids
        ]
        question_types = matching.get("question_types")
        observed_types = [item for item in question_types if isinstance(item, str)][:20] if isinstance(question_types, list) else []
        try:
            attempts = max(0, int(matching.get("attempts", mob.get("objective_attempts", 0)) or 0))
        except (TypeError, ValueError):
            attempts = 0
        reward_xp, reward_coins = MOB_REWARDS[min(index, len(MOB_REWARDS) - 1)]
        return {
            "project_id": project_id,
            "project_name": str(project.get("name") or project.get("branch") or ""),
            "project_progress": project.get("progress", 0),
            "project_status": str(project.get("status") or "active"),
            "project_complete": False,
            "mob_sequence_complete": False,
            "boss": str(project.get("boss") or ""),
            "boss_status": str(project.get("boss_status") or "locked"),
            "mob_name": mob_name,
            "mob_index": index,
            "status": str(mob.get("status") or "locked"),
            "resolve": resolve,
            "max_resolve": max_resolve,
            "completed_objectives": completed_ids,
            "available_objectives": available,
            "attempts": attempts,
            "pyr_assists": max(0, int(matching.get("pyr_assists", 0) or 0)),
            "reward_scale": self.pyr_reward_scale(int(matching.get("pyr_assists", 0) or 0)),
            "guards": max(0, int(matching.get("guards", 0) or 0)) if isinstance(matching, Mapping) else 0,
            "question_types": observed_types,
            "current_quest": available[0] if available else None,
            "mechanics": [dict(item) for item in ENCOUNTER_MECHANICS],
            "special_mechanic": {**special, "triggered": special["trigger"] in completed_ids} if special else None,
            "mob": {
                "name": mob_name,
                "index": index,
                "concept": concept,
                "lore": encounter_lore,
                "brief": encounter_brief,
                "contract": contract.get("contract") if isinstance(contract.get("contract"), str) else None,
                "act": contract.get("act") if isinstance(contract.get("act"), int) else None,
                "sign_id": contract_sign,
                "beast": HUNTER_BEASTS[contract_sign]["beast"] if contract_sign in HUNTER_BEASTS else None,
            },
            # This is a preview for the currently available mob only.  The
            # mutation event remains the authority for rewards and unlocks.
            "reward_envelope": {
                "xp": reward_xp,
                "coins": reward_coins,
                "authorized_items": [],
            },
        }

    @staticmethod
    def _multiline_text(value: object, field: str, *, max_bytes: int) -> str:
        """Normalize bounded editor/prompt text while preserving line breaks."""

        if not isinstance(value, str):
            raise StateCommandError(f"{field} must be text")
        normalized = value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
        if any(ord(character) < 32 and character not in {"\n", "\t"} for character in normalized):
            raise StateCommandError(f"{field} contains unsupported control characters")
        if len(normalized.encode("utf-8")) > max_bytes:
            raise StateCommandError(f"{field} is too large")
        return normalized

    @classmethod
    def _dungeon_question_spec(cls, value: Mapping[str, Any]) -> dict[str, Any]:
        """Validate the public portion of one current Dungeon question."""

        if not isinstance(value, Mapping):
            raise StateCommandError("Dungeon question must be an object")
        allowed = {"id", "question_type", "concept_id", "difficulty", "prompt", "options"}
        unknown = set(value) - allowed
        if unknown:
            raise StateCommandError(f"Unsupported Dungeon question field(s): {', '.join(sorted(unknown))}")
        required = {"id", "question_type", "concept_id", "difficulty", "prompt"}
        missing = sorted(required - set(value))
        if missing:
            raise StateCommandError(f"Missing Dungeon question field(s): {', '.join(missing)}")
        question_id = cls._text(value["id"], "question.id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        question_type = cls._text(
            value["question_type"],
            "question.question_type",
            max_length=MAX_IDENTIFIER_LENGTH,
            identifier=True,
        )
        concept_id = cls._text(value["concept_id"], "question.concept_id", max_length=MAX_IDENTIFIER_LENGTH)
        difficulty = cls._integer(
            value["difficulty"],
            "question.difficulty",
            minimum=1,
            maximum=MAX_DUNGEON_DIFFICULTY,
        )
        prompt = cls._multiline_text(value["prompt"], "question.prompt", max_bytes=8_000).strip()
        if not prompt:
            raise StateCommandError("question.prompt must not be empty")
        raw_options = value.get("options", [])
        if not isinstance(raw_options, list) or len(raw_options) > MAX_DUNGEON_OPTIONS:
            raise StateCommandError("question.options must be a bounded list")
        options = [
            cls._text(option, "question.options", max_length=MAX_SYNC_TEXT_LENGTH)
            for option in raw_options
        ]
        return {
            "id": question_id,
            "question_type": question_type,
            "concept_id": concept_id,
            "difficulty": difficulty,
            "prompt": prompt,
            "options": options,
        }

    @staticmethod
    def _dungeon_market_catalog() -> list[dict[str, Any]]:
        return [dict(item) for item in DUNGEON_MARKET_CATALOG]

    @classmethod
    def _dungeon_inventory_entries(cls, run: dict[str, Any], *, mutate: bool = False) -> list[dict[str, Any]]:
        """Return the bounded item inventory for a run.

        Older checkpoints only stored the currently equipped loadout. They
        receive a deterministic starter entry on projection; the first
        state-changing Dungeon action persists that migration through the
        normal revision/event path.
        """

        raw = run.get("inventory")
        if raw is None:
            loadout = run.get("loadout") if isinstance(run.get("loadout"), Mapping) else {}
            starter = {
                "id": "dungeon-starter-armor",
                "name": str(loadout.get("armor") or "Apprentice Coat"),
                "kind": "armor",
                "armor": str(loadout.get("armor") or "Apprentice Coat"),
                "description": "Starter armor for this Dungeon run.",
            }
            items = [starter]
            if loadout.get("weapon"):
                items.append({
                    "id": "dungeon-starter-weapon",
                    "name": str(loadout.get("weapon")),
                    "kind": "weapon",
                    "weapon": str(loadout.get("weapon")),
                    "description": "Starter weapon for this Dungeon run.",
                })
            if mutate:
                run["inventory"] = items
            return items
        if not isinstance(raw, list) or len(raw) > MAX_DUNGEON_INVENTORY:
            raise StateCommandError("Existing Dungeon inventory is invalid", status_code=500)
        items: list[dict[str, Any]] = []
        for index, item in enumerate(raw):
            if not isinstance(item, Mapping):
                raise StateCommandError(f"Existing Dungeon inventory item {index} is invalid", status_code=500)
            item_id = item.get("id")
            name = item.get("name")
            kind = item.get("kind")
            if not isinstance(item_id, str) or not item_id.strip() or not isinstance(name, str) or not name.strip() or kind not in {"weapon", "armor", "trinket"}:
                raise StateCommandError(f"Existing Dungeon inventory item {index} is invalid", status_code=500)
            clean = {
                "id": item_id[:MAX_IDENTIFIER_LENGTH],
                "name": name[:MAX_IDENTIFIER_LENGTH],
                "kind": kind,
                "description": str(item.get("description") or "")[:300],
            }
            if kind == "weapon":
                clean["weapon"] = str(item.get("weapon") or name)[:MAX_IDENTIFIER_LENGTH]
            elif kind == "armor":
                clean["armor"] = str(item.get("armor") or name)[:MAX_IDENTIFIER_LENGTH]
            else:
                clean["trinket"] = str(item.get("trinket") or name)[:MAX_IDENTIFIER_LENGTH]
            items.append(clean)
        if mutate:
            run["inventory"] = items
        return items

    def _dungeon_next_concept(self, run: Mapping[str, Any], progress: Mapping[str, Any]) -> str:
        """The concept for the next fight: a delve draws from its region's
        signs, weighted to the weakest; an open run follows Codex misses."""

        region = DUNGEON_REGIONS.get(str(run.get("region_id") or ""))
        if region is None:
            return self._dungeon_adaptive_concept(progress, str(run.get("concept_id") or "python-basics"))
        levels = {sign["id"]: sign["level"] for sign in self.hunter_projection(progress)["signs"]}
        weights = [(sign_id, (11 - levels.get(sign_id, 0)) ** 2) for sign_id in region["signs"]]
        digest = hashlib.sha256(f"{run.get('seed')}:{run.get('question_number', 0)}:delve".encode("utf-8")).digest()
        roll = int.from_bytes(digest[:4], "big") % sum(weight for _, weight in weights)
        for sign_id, weight in weights:
            if roll < weight:
                return HUNTER_SIGN_CONCEPTS[sign_id]
            roll -= weight
        return HUNTER_SIGN_CONCEPTS[region["signs"][0]]

    @staticmethod
    def _dungeon_pack_items(pack: object) -> list[dict[str, Any]]:
        if not isinstance(pack, Mapping):
            return []
        catalog = armory_catalog()
        items = [
            {"id": key, "name": DUNGEON_MATERIAL_NAMES.get(key) or catalog.get(key, {}).get("name", key), "count": value, **({"tier": catalog[key]["tier"], "slot": catalog[key]["slot"]} if key in catalog else {})}
            for key, value in pack.items()
            if isinstance(key, str) and isinstance(value, int) and not isinstance(value, bool) and value > 0
        ]
        return sorted(items, key=lambda item: item["name"])

    def _dungeon_bank_pack(self, run: dict[str, Any], progress: dict[str, Any]) -> list[dict[str, Any]]:
        """Move the run pack into the hunter's bank (at a camp or a safe exit)."""

        banked = self._dungeon_pack_items(run.get("pack"))
        if banked:
            hunter = self._hunter_state(progress)
            catalog = armory_catalog()
            for item in banked:
                if item["id"] in catalog:
                    self._armory_add(hunter, item["id"], item["count"])
                else:
                    hunter["materials"][item["id"]] = self._counter(hunter["materials"], item["id"]) + item["count"]
        run["pack"] = {}
        run["last_banked"] = banked
        return banked

    def _dungeon_forfeit_pack(self, run: dict[str, Any]) -> list[dict[str, Any]]:
        """Death keeps nothing unbanked; the dead run remembers what was lost."""

        lost = self._dungeon_pack_items(run.get("pack"))
        run["pack_lost"] = {item["id"]: item["count"] for item in lost}
        run["pack"] = {}
        return lost

    def _dungeon_award_loot(self, run: dict[str, Any], fight: Mapping[str, Any], concept: object, progress: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Drops for a cleared fight: beast parts, a boss essence, an elite trinket."""

        room_type = str(fight.get("room_type") or "encounter")
        clean = not int(fight.get("misses", 0) or 0)
        drops: dict[str, int] = {}
        sign_id = next((sign for sign in hunter_signs_for(concept) if sign in HUNTER_BEASTS), None)
        if sign_id:
            drops[HUNTER_BEASTS[sign_id]["part"]] = (
                DUNGEON_LOOT_PARTS.get(room_type, 1)
                + (DUNGEON_CLEAN_FIGHT_BONUS if clean else 0)
                + (DUNGEON_DEEP_EXTRA_PARTS if run.get("floor_modifier") == "deep" else 0)
            )
        region = DUNGEON_REGIONS.get(str(run.get("region_id") or ""))
        if room_type == "boss" and region:
            drops[region["essence"]] = 1
        if room_type in {"elite", "boss"}:
            drops[DUNGEON_VIAL] = 1
        pack = run.get("pack") if isinstance(run.get("pack"), dict) else {}
        for key, count in drops.items():
            pack[key] = self._counter(pack, key) + count
        run["pack"] = pack
        gear = self._dungeon_gear_drop(run, room_type, progress)
        if gear:
            pack[gear] = self._counter(pack, gear) + 1
            drops[gear] = 1
        loot: dict[str, Any] = {"items": self._dungeon_pack_items(drops), "clean": clean, "trinket": None, "coins": 0}
        if room_type == "elite":
            inventory = self._dungeon_inventory_entries(run, mutate=True)
            owned = {item.get("id") for item in inventory}
            trinket = next((dict(item) for item in DUNGEON_TRINKETS if item["id"] not in owned), None)
            if trinket and len(inventory) < MAX_DUNGEON_INVENTORY:
                inventory.append(trinket)
                loadout = self._dungeon_ensure_loadout_defaults(run)
                equipped = not loadout.get("trinket")
                if equipped:
                    loadout["trinket"] = trinket["trinket"]
                loot["trinket"] = {"id": trinket["id"], "name": trinket["name"], "description": trinket["description"], "equipped": equipped}
            else:
                run["run_coins"] = self._counter(run, "run_coins") + DUNGEON_TRINKET_FALLBACK_COINS
                loot["coins"] = DUNGEON_TRINKET_FALLBACK_COINS
        return loot

    @classmethod
    def _dungeon_adaptive_concept(cls, progress: Mapping[str, Any] | None, fallback: str) -> str:
        """Choose a recorded weak concept for the next room when available.

        The Dungeon may adapt to evidence already in the Codex, but it never
        invents a weakness from raw browser text.  Incorrect encounter results
        or an explicit recorded weakness are the only signals considered.
        """

        if not isinstance(progress, Mapping):
            return fallback
        codex = progress.get("codex")
        entries = codex.get("encounters") if isinstance(codex, Mapping) else None
        if not isinstance(entries, list):
            return fallback
        candidates: list[tuple[int, str]] = []
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            concept = entry.get("concept")
            if not isinstance(concept, str) or not concept.strip():
                continue
            results = entry.get("results") if isinstance(entry.get("results"), list) else []
            incorrect = sum(1 for result in results if isinstance(result, Mapping) and result.get("outcome") == "incorrect")
            weaknesses = entry.get("weaknesses") if isinstance(entry.get("weaknesses"), list) else []
            signal = incorrect + (1 if weaknesses else 0)
            if signal:
                candidates.append((signal, concept.strip()))
        if not candidates:
            return fallback
        candidates.sort(key=lambda item: (-item[0], item[1].casefold()))
        return candidates[0][1][:MAX_IDENTIFIER_LENGTH]

    @classmethod
    def _dungeon_question_for_room(cls, run: Mapping[str, Any], *, room: int, floor: int) -> dict[str, Any]:
        """Create a safe deterministic prompt for a newly reached room.

        A trusted provider may replace this public prompt through
        ``dungeon_issue_question``; this fallback keeps the local vertical
        slice playable without exposing an answer key.
        """

        concept = str(run.get("concept_id") or "python-basics")
        room_type = str(run.get("room_type") or "encounter")
        difficulty = min(
            MAX_DUNGEON_DIFFICULTY,
            max(1, 1 + (floor - 1) // 2 + (2 if room_type == "elite" else 3 if room_type == "boss" else 0) + (1 if run.get("floor_modifier") == "deep" else 0)),
        )
        # Harder rooms ask for more code: encounters mix quick clickable
        # questions with short code, elites lean on code, bosses are all code.
        # Theory belongs in the Tutor notebook.
        types = {
            "boss": ("code_checkpoint", "bug_hunt", "code_checkpoint"),
            "elite": ("code_checkpoint", "multiple_choice", "bug_hunt"),
        }.get(room_type, ("multiple_choice", "code_checkpoint", "true_false", "bug_hunt"))
        question_type = types[int(run.get("question_number", room) or room) % len(types)]
        prompt_by_type = {
            "true_false": f"True or false: a {concept} loop should make its stopping condition observable.",
            "multiple_choice": f"Which small change would make a {concept} example easier to test?",
            "code_checkpoint": f"Write a small Python example that demonstrates {concept}.",
            "bug_hunt": f"Find one likely boundary bug in a short {concept} example and explain the fix.",
            "short_explanation": f"Explain how you would check a {concept} result before changing state.",
        }
        options = ["Make the state explicit", "Hide the state", "Skip the check"] if question_type == "multiple_choice" else ["True", "False"] if question_type == "true_false" else []
        return cls._dungeon_question_spec(
            {
                "id": f"{run['run_id']}-q{int(run.get('question_number', 1))}",
                "question_type": question_type,
                "concept_id": concept,
                "difficulty": difficulty,
                "prompt": prompt_by_type[question_type],
                "options": options,
            }
        )

    def _dungeon_start_fight(self, run: dict[str, Any], progress: Mapping[str, Any]) -> dict[str, Any]:
        """Open the fight for the current combat room: its fixed question
        count, a full Resolve bar and the room's mechanic. Insight buys one
        more answer on every mechanic countdown per 3 points."""

        room_type = str(run.get("room_type") or "encounter")
        insight = self.hunter_projection(progress)["stats"]["insight"]["value"]
        loadout = run.get("loadout") if isinstance(run.get("loadout"), Mapping) else {}
        trinket = loadout.get("trinket")
        mechanic = None
        definition = DUNGEON_MECHANICS.get(room_type)
        if definition:
            span = definition["every"] + max(0, insight - 1) // 3 + (1 if trinket == "Hunting Bell" else 0)
            mechanic = {
                "kind": definition["kind"],
                "label": definition["label"],
                "text": definition["text"],
                "every": span,
                "countdown": span,
                "enraged": False,
                "fired": 0,
            }
        resolve = DUNGEON_FIGHT_RESOLVE.get(room_type, 6)
        fight = {
            "room_type": room_type,
            "questions_total": DUNGEON_FIGHT_QUESTIONS.get(room_type, 1),
            "questions_cleared": 0,
            "resolve": resolve,
            "max_resolve": resolve,
            "guards": 1 if trinket == "Warden Sigil" else 0,
            "breaks": 0,
            "misses": 0,
            "mechanic": mechanic,
        }
        run["fight"] = fight
        return fight

    @staticmethod
    def _dungeon_pin_foe(run: dict[str, Any], mob: dict[str, Any] | None) -> dict[str, Any] | None:
        """Remember who this fight is against, so later questions keep the name."""

        fight = run.get("fight")
        if mob and isinstance(fight, dict) and not isinstance(fight.get("foe"), Mapping):
            fight["foe"] = {"name": mob["name"], "category": mob["category"]}
        return mob

    def _dungeon_fight(self, run: dict[str, Any], progress: Mapping[str, Any]) -> dict[str, Any]:
        fight = run.get("fight")
        if not isinstance(fight, dict) or fight.get("room_type") != run.get("room_type"):
            fight = self._dungeon_start_fight(run, progress)
        return fight

    @classmethod
    def _dungeon_mob_spec(cls, run: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return the safe identity for the currently issued learning mob.

        A mob exists only for the current encounter question.  Selector rooms
        deliberately return ``None`` so the browser cannot discover future
        enemies, prompts or answer keys before it commits a route.
        """

        if run.get("room_type") not in {"encounter", "elite", "boss"}:
            return None
        question = run.get("question")
        if not isinstance(question, Mapping):
            return None
        question_type = str(question.get("question_type") or "question")
        archetype = DUNGEON_MOB_ARCHETYPES.get(
            question_type,
            {"name": "The Unwritten Trial", "category": "adaptive challenge"},
        )
        try:
            difficulty = max(1, min(MAX_DUNGEON_DIFFICULTY, int(question.get("difficulty", 1))))
        except (TypeError, ValueError):
            difficulty = 1
        phase_index = min(len(_DUNGEON_MOB_PHASES) - 1, (difficulty - 1) // 3)
        room_type = str(run.get("room_type") or "encounter")
        fight = run.get("fight") if isinstance(run.get("fight"), Mapping) and run["fight"].get("room_type") == room_type else None
        max_resolve = int(fight["max_resolve"]) if fight else DUNGEON_FIGHT_RESOLVE.get(room_type, 6)
        resolve = int(fight["resolve"]) if fight else max_resolve
        score_index = min(difficulty, len(DUNGEON_SCORE_BY_DIFFICULTY) - 1)
        class_data = DUNGEON_CLASSES_BY_ID.get(str(run.get("class_id") or ""), {})
        loadout = run.get("loadout") if isinstance(run.get("loadout"), Mapping) else {}
        clean_impact = DUNGEON_SCORE_BY_DIFFICULTY[score_index] + max(0, int(class_data.get("resolve_bonus", 0) or 0))
        if int(loadout.get("edge_charges", 0) or 0) > 0:
            clean_impact += 1
        guide_steps = [
            {"id": "setup", "label": "Name the result or state you need to track", "resolve_damage": 1, "inference_signals": ["assignment", "result"]},
            {"id": "iterate", "label": "Build the loop or repeated check", "resolve_damage": 2, "inference_signals": ["for", "while", "iteration"]},
            {"id": "filter", "label": "Apply the condition that selects the right values", "resolve_damage": 2, "inference_signals": ["if", "condition", "comparison"]},
            {"id": "finish", "label": "Return, print, or otherwise expose the result", "resolve_damage": 1, "inference_signals": ["return", "print", "output"]},
        ]
        floor = max(1, int(run.get("floor", 1) or 1))
        guide_tier = "full" if floor <= 2 else "partial" if floor <= 4 else "question"
        profile_by_room = {
            "encounter": {
                "label": "Submission Gate",
                "weapon": "Bounded verifier",
                "passive": "Only a validated submission changes this room.",
                "telegraph": "Run is a safe local preview; Submit is the combat turn.",
                "on_run": "No HP or Resolve is spent while you work.",
                "on_failure": "An incorrect verdict costs bounded run HP and returns a text hint.",
            },
            "elite": {
                "label": "Trinket Warden",
                "weapon": "Counter-check gauntlet",
                "passive": "The elite keeps its trinket until the answer is verified.",
                "telegraph": "A clean file clears the gate; errors trigger the normal failure cost.",
                "on_run": "Run previews locally and cannot claim the trinket.",
                "on_failure": "The run takes bounded damage; no loot is invented or granted early.",
            },
            "boss": {
                "label": "Floor Boss",
                "weapon": "Final objective check",
                "passive": "The converged route stays locked until the current file is verified.",
                "telegraph": "The next floor is revealed only after the state service accepts the answer.",
                "on_run": "Local self-checks never bypass the boss verdict.",
                "on_failure": "An incorrect verdict costs bounded HP and keeps the floor locked.",
            },
        }
        profile = profile_by_room.get(room_type, profile_by_room["encounter"])
        beast_sign = next((sign for sign in hunter_signs_for(question.get("concept_id") or run.get("concept_id")) if sign in HUNTER_BEASTS), None)
        name = archetype["name"]
        category = archetype["category"]
        region = DUNGEON_REGIONS.get(str(run.get("region_id") or ""))
        if region and room_type == "boss":
            name = region["boss"]
        elif region:
            sign_id = next((sign for sign in hunter_signs_for(question.get("concept_id") or run.get("concept_id")) if sign in HUNTER_BEASTS), None)
            if sign_id:
                beast = HUNTER_BEASTS[sign_id]["beast"]
                name = beast if room_type == "encounter" else f"Elder {beast.removeprefix('The ')}"
        # One fight, one foe: a multi-question fight keeps the name it started with.
        foe = fight.get("foe") if fight and isinstance(fight.get("foe"), Mapping) else None
        if foe and isinstance(foe.get("name"), str) and foe["name"]:
            name = foe["name"]
            category = str(foe.get("category") or category)
        return {
            "id": f"{question.get('id', 'dungeon-question')}-mob",
            "name": name,
            "category": category,
            "concept_id": str(question.get("concept_id") or run.get("concept_id") or "python-basics")[:MAX_IDENTIFIER_LENGTH],
            "sign_id": beast_sign,
            "question_type": question_type,
            "difficulty": difficulty,
            "phase": _DUNGEON_MOB_PHASES[phase_index],
            "room_type": room_type,
            "max_resolve": max_resolve,
            "resolve": resolve,
            "resolve_damage": clean_impact,
            "fight": {
                "questions_total": int(fight["questions_total"]) if fight else DUNGEON_FIGHT_QUESTIONS.get(room_type, 1),
                "questions_cleared": int(fight["questions_cleared"]) if fight else 0,
                "guards": int(fight["guards"]) if fight else 0,
                "breaks": int(fight["breaks"]) if fight else 0,
                "oil": dict(fight["oil"]) if fight and isinstance(fight.get("oil"), Mapping) else None,
                "mechanic": dict(fight["mechanic"]) if fight and isinstance(fight.get("mechanic"), Mapping) else (
                    {**DUNGEON_MECHANICS[room_type], "countdown": DUNGEON_MECHANICS[room_type]["every"], "enraged": False, "fired": 0}
                    if room_type in DUNGEON_MECHANICS else None
                ),
            },
            "guide": {"tier": guide_tier, "steps": guide_steps},
            "mechanic": profile,
            "reward_envelope": {
                "score": DUNGEON_SCORE_BY_DIFFICULTY[score_index],
                "coins": DUNGEON_COIN_BY_DIFFICULTY[score_index],
                "authorized_items": ["trinket"] if room_type == "elite" else [],
            },
            "lore": (
                "A harder gate guarding a temporary trinket drop."
                if run.get("room_type") == "elite"
                else "The final keeper of this floor waits at the converging paths."
                if run.get("room_type") == "boss"
                else "A bounded learning mob shaped around the current concept."
            ),
        }

    @classmethod
    def _dungeon_map_node_id(cls, floor: int, row: int, column: int) -> str:
        return f"f{floor}-r{row}-c{column}"

    @classmethod
    def _dungeon_map_seed_byte(cls, seed: str, floor: int, row: int, column: int) -> int:
        digest = hashlib.sha256(f"{seed}:{floor}:{row}:{column}".encode("utf-8")).digest()
        return digest[0]

    @classmethod
    def _dungeon_generate_grid(cls, seed: str, floor: int, *, modifier: str | None = None, region_id: object = None) -> dict[str, Any]:
        """One floor as a connected room grid: a camp on the west edge, the
        boss in the farthest room, a camp beside the boss, and a seeded mix
        of gates, elites, fates and a market in between."""

        floor = max(1, min(MAX_DUNGEON_FLOOR, int(floor)))
        rng = random.Random(f"{seed}:{floor}:grid")

        def neighbours(cell: tuple[int, int]) -> list[tuple[int, int]]:
            row, column = cell
            return [
                (r, c) for r, c in ((row - 1, column), (row + 1, column), (row, column - 1), (row, column + 1))
                if 1 <= r <= DUNGEON_GRID_ROWS and 1 <= c <= DUNGEON_GRID_COLUMNS
            ]

        start = (rng.randint(1, DUNGEON_GRID_ROWS), 1)
        cells = {start}
        links: set[frozenset[tuple[int, int]]] = set()
        while len(cells) < DUNGEON_GRID_ROOMS:
            frontier = sorted((cell, other) for cell in cells for other in neighbours(cell) if other not in cells)
            cell, other = rng.choice(frontier)
            cells.add(other)
            links.add(frozenset((cell, other)))
        extra = sorted(
            {frozenset((cell, other)) for cell in cells for other in neighbours(cell) if other in cells} - links,
            key=lambda pair: sorted(pair),
        )
        links.update(rng.sample(extra, min(DUNGEON_GRID_LOOPS, len(extra))))
        adjacent: dict[tuple[int, int], list[tuple[int, int]]] = {cell: [] for cell in cells}
        for pair in links:
            a, b = sorted(pair)
            adjacent[a].append(b)
            adjacent[b].append(a)
        distance = {start: 0}
        queue = [start]
        while queue:
            cell = queue.pop(0)
            for other in sorted(adjacent[cell]):
                if other not in distance:
                    distance[other] = distance[cell] + 1
                    queue.append(other)
        farthest = max(distance.values())
        boss = rng.choice(sorted(cell for cell, value in distance.items() if value == farthest))
        kinds: dict[tuple[int, int], str] = {start: "rest", boss: "boss"}
        prep = rng.choice(sorted(cell for cell in adjacent[boss] if distance[cell] == farthest - 1))
        kinds[prep] = "rest"
        rest = [cell for cell in sorted(cells) if cell not in kinds]
        rng.shuffle(rest)
        elites = 1 + (1 if floor >= 3 else 0) + (1 if modifier == "deep" else 0)
        far = [cell for cell in rest if distance[cell] >= 2]
        for cell in far[:elites]:
            kinds[cell] = "elite"
        rest = [cell for cell in rest if cell not in kinds]
        plan = ["market", "mystery", "mystery"] + (["rest"] if modifier == "quiet" else [])
        for cell, kind in zip(rest, plan):
            kinds[cell] = kind
        for cell in rest:
            kinds.setdefault(cell, "encounter")
        # The first door out of camp always leads to a fight.
        doors = [cell for cell in sorted(adjacent[start]) if kinds[cell] != "boss"]
        if doors and not any(kinds[cell] in {"encounter", "elite"} for cell in doors):
            door = next((cell for cell in doors if kinds[cell] in {"market", "mystery"}), doors[0])
            gate = next(cell for cell in sorted(cells) if kinds[cell] == "encounter")
            kinds[door], kinds[gate] = "encounter", kinds[door]
        region = DUNGEON_REGIONS.get(str(region_id or ""))
        names = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII")
        order = sorted(cells, key=lambda cell: (distance[cell], cell))
        nodes = []
        for index, cell in enumerate(order):
            kind = kinds[cell]
            numeral = names[min(index, len(names) - 1)]
            label = (
                (region["boss"] if region else "The Count Keeper") if kind == "boss" else
                f"Gate {numeral}" if kind == "encounter" else
                f"Camp {numeral}" if kind == "rest" else
                "Elite" if kind == "elite" else
                "Market" if kind == "market" else
                "Fate"
            )
            nodes.append({
                "id": cls._dungeon_map_node_id(floor, cell[0], cell[1]),
                "type": kind,
                "row": cell[0],
                "column": cell[1],
                "label": label,
                "note": "start" if cell == start else DUNGEON_MAP_ROOM_NOTES.get(kind, "room"),
            })
        edges = {
            cls._dungeon_map_node_id(floor, cell[0], cell[1]): [cls._dungeon_map_node_id(floor, other[0], other[1]) for other in sorted(adjacent[cell])]
            for cell in sorted(cells)
        }
        start_id = cls._dungeon_map_node_id(floor, start[0], start[1])
        return {"floor": floor, "nodes": nodes, "edges": edges, "current_node_id": start_id, "visited_node_ids": [start_id]}

    @staticmethod
    def _dungeon_grid_visible(route: Mapping[str, Any], *, far_sight: bool = False) -> set[str]:
        """Explored rooms, their doors, and the boss lair (always felt)."""

        edges = route.get("edges") if isinstance(route.get("edges"), Mapping) else {}
        visible = {str(item) for item in route.get("visited_node_ids", []) if isinstance(item, str)}
        for _ in range(2 if far_sight else 1):
            visible |= {str(other) for node_id in list(visible) for other in edges.get(node_id, []) if isinstance(other, str)}
        visible |= {str(node.get("id")) for node in route.get("nodes", []) if isinstance(node, Mapping) and node.get("type") == "boss"}
        return visible

    @classmethod
    def _dungeon_stairs_choices(cls, run: Mapping[str, Any]) -> list[dict[str, str]]:
        floor = max(1, int(run.get("floor", 1) or 1))
        region = DUNGEON_REGIONS.get(str(run.get("region_id") or ""))
        where = region["label"] if region else "the dungeon"
        choices = [
            {"id": f"stairs-descend-{floor}", "kind": "stairs", "label": "Descend", "description": f"Floor {floor + 1} of {where}. A camp waits at the bottom."},
            {"id": f"stairs-deep-{floor}", "kind": "stairs", "label": "Deep stair", "description": "Harder questions and one more elite; every cleared fight drops one more part."},
        ]
        if region:
            ids = list(DUNGEON_REGIONS)
            target = DUNGEON_REGIONS[ids[(ids.index(region["id"]) + 1) % len(ids)]]
            choices.append({"id": f"stairs-region-{target['id']}-{floor}", "kind": "stairs", "label": f"Path to {target['label']}", "description": f"Change the delve: {target['label']} beasts, {target['boss']} and {target['essence_name']}."})
        else:
            choices.append({"id": f"stairs-quiet-{floor}", "kind": "stairs", "label": "Quiet stair", "description": "A gentler floor with one more camp."})
        return choices

    def _dungeon_live_choices(self, run: Mapping[str, Any]) -> list[dict[str, Any]] | Any:
        """Stored choices, or stairs for a save left at a cleared boss with
        none (older runs had no route past the first boss)."""

        stored = run.get("room_choices")
        if isinstance(stored, list) and stored:
            return stored
        if run.get("room_type") == "selector":
            node = self._dungeon_current_map_node(run)
            if isinstance(node, Mapping) and node.get("type") == "boss":
                return self._dungeon_stairs_choices(run)
        return stored if stored is not None else []

    def _dungeon_take_stairs(self, run: dict[str, Any], progress: dict[str, Any], choice_id: str) -> Mutation:
        """Go down: a new grid floor, starting at a camp (which banks)."""

        parts = choice_id.split("-")
        mode = parts[1] if len(parts) > 2 else "descend"
        if mode == "region":
            target = parts[2] if len(parts) > 3 else ""
            if target not in DUNGEON_REGIONS:
                raise StateCommandError("Unknown delve region", status_code=422)
            run["region_id"] = target
        modifier = mode if mode in {"deep", "quiet"} else None
        next_floor = min(MAX_DUNGEON_FLOOR, max(1, self._counter(run, "floor")) + 1)
        self._log_activity(progress, "floors")
        self._bump_record(progress, "dungeon_floors_descended")
        self._bump_record(progress, "dungeon_best_floor", next_floor, best=True)
        seed = str(run.get("seed") or run.get("run_id"))
        run["map"] = self._dungeon_generate_grid(seed, next_floor, modifier=modifier, region_id=run.get("region_id"))
        run["floor_layout"] = "grid"
        run["floor_modifier"] = modifier
        run["floor"] = next_floor
        run["room"] = min(MAX_DUNGEON_ROOM, max(1, self._counter(run, "room")) + 1)
        run.pop("fight", None)
        run.update({
            "room_type": "rest", "room_choices": [], "question": None, "camp_action_used": False,
            "risk_profile": None, "risk_status": None, "editor_content": "", "updated_at": _utc_now(),
        })
        banked = self._dungeon_bank_pack(run, progress)
        run["last_result"] = {"outcome": "floor_descended", "score_delta": 0, "coins_delta": 0, "damage": 0, "reason": mode}
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "floor": next_floor, "banked": banked},
            {"run_id": run["run_id"], "floor": next_floor, "stairs": mode, "region_id": run.get("region_id"), "banked": banked, "editor_reset": True, "reason": "dungeon_floor_descended"},
        )

    def _dungeon_travel(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Walk back through explored rooms. Inert: no camp, no banking."""

        data = self._payload(payload, {"run_id", "node_id"}, {"run_id", "node_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        node_id = self._text(data["node_id"], "node_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") != "selector":
            raise StateCommandError("Finish this room before walking the map", status_code=409)
        route = self._dungeon_map_for_run(run)
        if not route or run.get("floor_layout") != "grid":
            raise StateCommandError("This floor has no explored rooms to walk back to", status_code=409)
        if node_id not in route.get("visited_node_ids", []):
            raise StateCommandError("You can only walk back through explored rooms", status_code=409)
        if node_id == route.get("current_node_id"):
            return Mutation(False, {"run": self.dungeon_projection(progress)})
        route["current_node_id"] = node_id
        run["map"] = route
        run["room_choices"] = self._dungeon_route_choices(run)
        run["updated_at"] = _utc_now()
        return Mutation(True, {"run": self.dungeon_projection(progress)}, {"run_id": run_id, "node_id": node_id, "reason": "dungeon_travelled"})

    @classmethod
    def _dungeon_generate_map(cls, seed: str, *, floor: int = 1) -> dict[str, Any]:
        """Create one deterministic, state-owned branching map.

        The prototype's authored shape is retained: three lanes, a shared
        boss destination, and a preparation-only row before the boss.  Room
        types are randomised from the run seed, with only the safety rules the
        prototype established (a recovery row after an unusually dangerous
        row and at least one combat room before the boss).
        """

        try:
            safe_floor = max(1, min(MAX_DUNGEON_FLOOR, int(floor)))
        except (TypeError, ValueError):
            safe_floor = 1
        nodes: list[dict[str, Any]] = []
        row_names = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII")
        start = {
            "id": cls._dungeon_map_node_id(safe_floor, 1, 3),
            "type": "rest",
            "row": 1,
            "column": 3,
            "label": "Camp I",
            "note": "start",
        }
        nodes.append(start)
        combat_seen = False
        for row in range(2, DUNGEON_MAP_ROWS):
            row_nodes: list[dict[str, Any]] = []
            for column in DUNGEON_MAP_NODE_COLUMNS:
                if row == DUNGEON_MAP_ROWS - 1:
                    kind = DUNGEON_MAP_FINAL_PREP_TYPES[
                        cls._dungeon_map_seed_byte(seed, safe_floor, row, column) % len(DUNGEON_MAP_FINAL_PREP_TYPES)
                    ]
                else:
                    kind = DUNGEON_MAP_ROOM_TYPES[
                        cls._dungeon_map_seed_byte(seed, safe_floor, row, column) % len(DUNGEON_MAP_ROOM_TYPES)
                    ]
                if kind in {"encounter", "elite"}:
                    combat_seen = True
                label = (
                    f"Gate {row_names[row - 1]}" if kind == "encounter" else
                    f"Camp {row_names[row - 1]}" if kind == "rest" else
                    "Elite" if kind == "elite" else
                    "Market" if kind == "market" else
                    "Fate"
                )
                row_nodes.append({
                    "id": cls._dungeon_map_node_id(safe_floor, row, column),
                    "type": kind,
                    "row": row,
                    "column": column,
                    "label": label,
                    "note": DUNGEON_MAP_ROOM_NOTES[kind],
                })
            elite_count = sum(1 for item in row_nodes if item["type"] == "elite")
            gate_count = sum(1 for item in row_nodes if item["type"] == "encounter")
            has_camp = any(item["type"] == "rest" for item in row_nodes)
            has_market = any(item["type"] == "market" for item in row_nodes)
            nodes.extend(row_nodes)
            # Preserve the prototype's recovery safeguards without imposing a
            # quota on ordinary rows.
            if row < DUNGEON_MAP_ROWS - 1 and (elite_count >= 2 or gate_count == 3):
                next_row = [item for item in nodes if item["row"] == row + 1]
                for item in next_row:
                    if item["column"] == 1:
                        item.update(type="rest", label=f"Camp {row_names[row]}", note="recover")
                    elif item["column"] == 5:
                        item.update(type="market", label="Market", note="trade")
            elif not has_camp:
                end_type = "rest" if has_market else "market"
                for item in row_nodes:
                    if item["column"] == 5:
                        item.update(type=end_type, label=f"Camp {row_names[row - 1]}" if end_type == "rest" else "Market", note=DUNGEON_MAP_ROOM_NOTES[end_type])
        # Apply row safeguards after all rows exist so the recovery row is
        # actually present in the generated map.
        by_row = {row: [item for item in nodes if item["row"] == row] for row in range(2, DUNGEON_MAP_ROWS)}
        for row in range(2, DUNGEON_MAP_ROWS - 1):
            row_nodes = by_row[row]
            elite_count = sum(1 for item in row_nodes if item["type"] == "elite")
            gate_count = sum(1 for item in row_nodes if item["type"] == "encounter")
            has_camp = any(item["type"] == "rest" for item in row_nodes)
            has_market = any(item["type"] == "market" for item in row_nodes)
            if elite_count >= 2 or gate_count == 3:
                for item in by_row.get(row + 1, []):
                    if item["column"] == 1:
                        item.update(type="rest", label=f"Camp {row_names[row]}", note="recover")
                    elif item["column"] == 5:
                        item.update(type="market", label="Market", note="trade")
            elif not has_camp:
                end_type = "rest" if has_market else "market"
                for item in row_nodes:
                    if item["column"] == 5:
                        item.update(type=end_type, label=f"Camp {row_names[row - 1]}" if end_type == "rest" else "Market", note=DUNGEON_MAP_ROOM_NOTES[end_type])

        if not combat_seen:
            candidates = [item for item in nodes if 2 <= item["row"] < DUNGEON_MAP_ROWS]
            if candidates:
                forced = candidates[0]
                forced.update(type="encounter", label=f"Gate {row_names[forced['row'] - 1]}", note="fight")
        boss = {
            "id": cls._dungeon_map_node_id(safe_floor, DUNGEON_MAP_ROWS, 3),
            "type": "boss",
            "row": DUNGEON_MAP_ROWS,
            "column": 3,
            "label": "The Count Keeper",
            "note": DUNGEON_MAP_ROOM_NOTES["boss"],
        }
        nodes.append(boss)
        edges: dict[str, list[str]] = {}
        by_row_column = {(item["row"], item["column"]): item for item in nodes}
        edges[start["id"]] = [by_row_column[(2, column)]["id"] for column in DUNGEON_MAP_NODE_COLUMNS]
        for row in range(2, DUNGEON_MAP_ROWS - 1):
            for column in DUNGEON_MAP_NODE_COLUMNS:
                node = by_row_column[(row, column)]
                edges[node["id"]] = [by_row_column[(row + 1, column)]["id"]]
        for column in DUNGEON_MAP_NODE_COLUMNS:
            edges[by_row_column[(DUNGEON_MAP_ROWS - 1, column)]["id"]] = [boss["id"]]
        edges[boss["id"]] = []
        return {
            "floor": safe_floor,
            "nodes": nodes,
            "edges": edges,
            "current_node_id": start["id"],
            "visited_node_ids": [start["id"]],
        }

    @classmethod
    def _dungeon_map_for_run(cls, run: Mapping[str, Any]) -> dict[str, Any] | None:
        raw = run.get("map")
        if not isinstance(raw, Mapping):
            # Older checkpoints predate the prototype map.  Project a
            # deterministic compatibility map without silently changing the
            # saved run; the first route selection will persist it through the
            # normal state mutation path.
            seed = run.get("seed")
            if not isinstance(seed, str) or not seed.strip():
                return None
            route = cls._dungeon_generate_map(seed, floor=run.get("floor", 1))
            room_type = str(run.get("room_type") or "selector")
            if room_type != "selector":
                current = next((node for node in route["nodes"] if node.get("type") == room_type and node.get("row", 0) < DUNGEON_MAP_ROWS), None)
                if current is None:
                    current = next((node for node in route["nodes"] if node.get("row", 0) == 2), route["nodes"][0])
                    # Keep a legacy checkpoint's visible room coherent with
                    # its persisted room_type.  This is an ephemeral
                    # projection-only adjustment; the save is not rewritten
                    # until the player takes a normal gateway action.
                    current["type"] = room_type
                    current["label"] = DUNGEON_MAP_ROOM_LABELS.get(room_type, "Current room")
                    current["note"] = DUNGEON_MAP_ROOM_NOTES.get(room_type, "current")
                route["current_node_id"] = current.get("id")
                route["visited_node_ids"] = [route["nodes"][0].get("id"), current.get("id")]
            return route
        nodes = raw.get("nodes")
        edges = raw.get("edges")
        if not isinstance(nodes, list) or not isinstance(edges, Mapping):
            return None
        return {
            "floor": raw.get("floor", run.get("floor", 1)),
            "nodes": [dict(item) for item in nodes if isinstance(item, Mapping)],
            "edges": {str(key): list(value) for key, value in edges.items() if isinstance(value, list)},
            "current_node_id": raw.get("current_node_id"),
            "visited_node_ids": [str(item) for item in raw.get("visited_node_ids", []) if isinstance(item, str)],
        }

    @classmethod
    def _dungeon_current_map_node(cls, run: Mapping[str, Any]) -> dict[str, Any] | None:
        route = cls._dungeon_map_for_run(run)
        if not route:
            return None
        current_id = route.get("current_node_id")
        return next((item for item in route["nodes"] if item.get("id") == current_id), None)

    @classmethod
    def _dungeon_route_choices(cls, run: Mapping[str, Any]) -> list[dict[str, str]]:
        """Build the answer-free route selector for the current map node."""

        route = cls._dungeon_map_for_run(run)
        if route:
            current_id = route.get("current_node_id")
            current = next((item for item in route.get("nodes", []) if item.get("id") == current_id), None)
            if isinstance(current, Mapping) and current.get("type") == "boss":
                # Back at the selector on the boss node means the boss fell.
                return cls._dungeon_stairs_choices(run)
            next_ids = route.get("edges", {}).get(current_id, []) if isinstance(route.get("edges"), Mapping) else []
            visited = set(route.get("visited_node_ids", []))
            choices: list[dict[str, str]] = []
            for node_id in next_ids:
                node = next((item for item in route.get("nodes", []) if item.get("id") == node_id), None)
                if not isinstance(node, Mapping) or node_id in visited:
                    continue
                kind = str(node.get("type") or "encounter")
                choices.append(
                    {
                        "id": str(node_id),
                        "kind": kind,
                        "label": str(node.get("label") or DUNGEON_MAP_ROOM_LABELS.get(kind, "Next room")),
                        "description": str(node.get("note") or DUNGEON_MAP_ROOM_NOTES.get(kind, "Choose this route.")),
                    }
                )
            return choices

        room = cls._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM)
        # Keep the visible route variety deterministic for a checkpoint while
        # allowing the UI to render a real selector instead of predicting the
        # next room from a client-side modulo rule.
        choices: list[dict[str, str]] = []
        for choice in DUNGEON_ROUTE_CHOICES:
            choices.append(
                {
                    "id": f"r{room}-{choice['id']}",
                    "kind": choice["kind"],
                    "label": choice["label"],
                    "description": choice["description"],
                }
            )
        return choices

    @classmethod
    def _dungeon_prepare_room_choices(
        cls,
        run: dict[str, Any],
        progress: Mapping[str, Any] | None = None,
        *,
        advance: bool = True,
    ) -> dict[str, Any]:
        """Return an active run to the map selector after a room resolves."""

        current_room = cls._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM)
        next_room = min(MAX_DUNGEON_ROOM, current_room + 1) if advance else current_room
        floor = max(1, cls._integer(run.get("floor", 1), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR))
        floor = max(floor, 1 + (next_room - 1) // 10)
        route = cls._dungeon_map_for_run(run)
        if route:
            # The map node is advanced by dungeon_choose_room.  Resolving a
            # room returns to the selector without inventing another node.
            run["room"] = current_room
            run["floor"] = max(1, cls._integer(route.get("floor", floor), "map.floor", minimum=1, maximum=MAX_DUNGEON_FLOOR))
        else:
            run["room"] = next_room
            run["floor"] = floor
        run["room_type"] = "selector"
        run["room_choices"] = cls._dungeon_route_choices(run)
        run["question"] = None
        run["camp_action_used"] = False
        run.setdefault("next_failure_multiplier", 1)
        run["risk_profile"] = None
        run["risk_status"] = None
        run["editor_content"] = ""
        run["updated_at"] = _utc_now()
        return run

    @classmethod
    def _dungeon_set_next_room(cls, run: dict[str, Any], progress: Mapping[str, Any] | None = None) -> dict[str, Any]:
        return cls._dungeon_prepare_room_choices(run, progress)

    def _dungeon_choose_room(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Select one state-service-issued route before a question is shown."""

        data = self._payload(payload, {"run_id", "choice_id"}, {"run_id", "choice_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        choice_id = self._text(data["choice_id"], "choice_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") != "selector":
            raise StateCommandError("Choose a route from the current Dungeon map first", status_code=409)
        raw_choices = self._dungeon_live_choices(run)
        if not isinstance(raw_choices, list):
            raise StateCommandError("The current Dungeon map has no route choices", status_code=409)
        choice = next((item for item in raw_choices if isinstance(item, Mapping) and item.get("id") == choice_id), None)
        if choice is None:
            raise StateCommandError("That Dungeon route is no longer available", status_code=409)
        kind = self._text(choice.get("kind"), "choice.kind", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if kind not in {"encounter", "elite", "mystery", "rest", "market", "boss", "stairs"}:
            raise StateCommandError("Unsupported Dungeon route", status_code=500)
        if kind == "stairs":
            return self._dungeon_take_stairs(run, progress, choice_id)
        route = self._dungeon_map_for_run(run)
        if route:
            node = next((item for item in route["nodes"] if item.get("id") == choice_id), None)
            if not isinstance(node, Mapping):
                raise StateCommandError("That Dungeon route is no longer available", status_code=409)
            route["current_node_id"] = choice_id
            visited = list(route.get("visited_node_ids", []))
            if choice_id not in visited:
                visited.append(choice_id)
            route["visited_node_ids"] = visited[-MAX_SYNC_DUNGEON_HISTORY:]
            run["map"] = route
            # Rooms entered so far: the display and the leaderboard depth.
            run["room"] = min(MAX_DUNGEON_ROOM, max(1, self._counter(run, "room")) + 1)
            run["floor"] = max(1, self._integer(route.get("floor", run.get("floor", 1)), "map.floor", minimum=1, maximum=MAX_DUNGEON_FLOOR))
        run["room_choices"] = []
        run["room_type"] = kind
        run["editor_content"] = ""
        run["updated_at"] = _utc_now()
        question_id = None
        mob = None
        if kind in {"encounter", "elite", "boss"}:
            run["concept_id"] = self._dungeon_next_concept(run, progress)
            run["question_number"] = self._counter(run, "question_number") + 1
            question = self._dungeon_question_for_room(
                run,
                room=self._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM),
                floor=self._integer(run.get("floor", 1), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR),
            )
            run["question"] = question
            question_id = question["id"]
            self._dungeon_start_fight(run, progress)
            mob = self._dungeon_pin_foe(run, self._dungeon_mob_spec(run))
        elif kind == "mystery":
            seed = str(run.get("seed") or run.get("run_id") or "dungeon")
            node_id = str(choice_id)
            digest = hashlib.sha256(f"{seed}:{node_id}:risk".encode("utf-8")).digest()
            run["risk_profile"] = dict(DUNGEON_RISK_PROFILES[digest[0] % len(DUNGEON_RISK_PROFILES)])
            run["risk_status"] = "unrevealed"
        else:
            run["question"] = None
        # Reaching a camp banks the pack; it costs no camp action.
        banked = self._dungeon_bank_pack(run, progress) if kind == "rest" else []
        if kind != "rest":
            run["last_banked"] = []
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "choice": dict(choice), "banked": banked},
            {
                "run_id": run_id,
                "floor": run.get("floor", 1),
                "room": run.get("room", 1),
                "choice_id": choice_id,
                "room_type": kind,
                "question_id": question_id,
                "mob_name": mob["name"] if mob else None,
                "mob_category": mob["category"] if mob else None,
                "mob_phase": mob["phase"] if mob else None,
                "banked": banked,
                "editor_reset": True,
                "reason": "dungeon_route_selected",
            },
        )

    @classmethod
    def _dungeon_append_history(cls, run: dict[str, Any], item: Mapping[str, Any]) -> None:
        history = run.setdefault("history", [])
        if not isinstance(history, list):
            raise StateCommandError("Existing Dungeon history is invalid", status_code=500)
        safe = {key: item[key] for key in ("room", "floor", "question_id", "outcome", "evidence_id", "score_delta", "coins_delta", "damage") if key in item}
        history.append(safe)
        run["history"] = history[-50:]

    @staticmethod
    def _dungeon_run(progress: Mapping[str, Any]) -> dict[str, Any] | None:
        raw = progress.get("dungeon_run")
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise StateCommandError("Existing state field dungeon_run is invalid", status_code=500)
        return raw

    def _active_dungeon_run(self, progress: Mapping[str, Any]) -> dict[str, Any]:
        run = self._dungeon_run(progress)
        if run is None or run.get("status") != "active":
            raise StateCommandError("No active Dungeon run is available", status_code=409)
        if not isinstance(run.get("run_id"), str) or not run["run_id"].strip():
            raise StateCommandError("Existing Dungeon run ID is invalid", status_code=500)
        return run

    def dungeon_projection(self, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Return the restart-safe public Dungeon projection.

        Internal generation fields (including any future answer key) are never
        copied into this projection. The editor buffer is canonical state and
        is only exposed for the current active run.
        """

        run = self._dungeon_run(progress)
        if run is None:
            return {"active": False, "status": "idle", "editor_content": ""}
        status = run.get("status", "idle")
        if status not in {"active", "dead", "complete"}:
            raise StateCommandError("Existing Dungeon run status is invalid", status_code=500)
        projection: dict[str, Any] = {
            "active": status == "active",
            "status": status,
            "run_id": run.get("run_id"),
            "seed": run.get("seed"),
            "class_id": run.get("class_id") or "syntax-warden",
            "class": None,
            "concept_id": run.get("concept_id"),
            "floor": run.get("floor", 0),
            "room": run.get("room", 0),
            "room_type": run.get("room_type", ""),
            "score": run.get("score", 0),
            "run_coins": run.get("run_coins", 0),
            "started_at": run.get("started_at"),
            "updated_at": run.get("updated_at"),
            "ended_at": run.get("ended_at"),
            "loadout": {},
            "question": None,
            "encounter": None,
            "room_choices": [],
            "map": None,
            "current_node": None,
            "visited_node_ids": [],
            "risk_profile": None,
            "risk_status": None,
            "camp_action_used": bool(run.get("camp_action_used", False)),
            "next_failure_multiplier": max(1, self._counter(run, "next_failure_multiplier") or 1),
            "editor_content": "",
            "last_result": None,
            "history": [],
            "inventory": [],
            "market_catalog": [],
            "leaderboard": [],
        }
        for field in ("floor", "room", "score", "run_coins"):
            try:
                projection[field] = max(0, int(projection[field] or 0))
            except (TypeError, ValueError) as exc:
                raise StateCommandError(f"Existing Dungeon field {field} is invalid", status_code=500) from exc
        if status == "active" and run.get("room_type") == "market":
            discount = min(90, self._counter(run, "market_discount"))
            projection["market_catalog"] = [
                {**item, "price": max(0, (int(item["price"]) * (100 - discount) + 99) // 100) if discount else item["price"]}
                for item in self._dungeon_market_catalog()
            ]
        loadout = run.get("loadout")
        if not isinstance(loadout, Mapping):
            raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
        starter_defaults = DUNGEON_CLASSES_BY_ID.get(str(projection["class_id"]), DUNGEON_CLASSES_BY_ID["syntax-warden"])
        loadout_defaults = {
            "weapon": starter_defaults.get("starter_weapon", "Lint Lantern"),
            "armor": "Apprentice Coat",
            "trinket": None,
            "hp": 100,
            "max_hp": 100,
            "heals": 1,
            "coins": 0,
            "bandages": 1,
            "rations": 1,
            "vision_scrolls": 0,
            "tonics": 0,
            "edge_charges": 0,
            "armor_guard": 0,
        }
        projection["loadout"] = {
            field: loadout.get(field, loadout_defaults[field])
            for field in ("weapon", "armor", "trinket", "hp", "max_hp", "heals", "coins", "bandages", "rations", "vision_scrolls", "tonics", "edge_charges", "armor_guard")
        }
        selected_class = DUNGEON_CLASSES_BY_ID.get(str(projection["class_id"]))
        if selected_class is not None:
            projection["class"] = {
                field: selected_class[field]
                for field in ("id", "name", "role", "passive", "starter_weapon", "resolve_bonus", "syntax_guard")
                if field in selected_class
            }
        inventory = self._dungeon_inventory_entries(run)
        inventory = [dict(item) for item in inventory]
        if not any(item.get("kind") == "weapon" for item in inventory):
            inventory.append({
                "id": starter_defaults.get("starter_weapon_id", "dungeon-lint-lantern"),
                "name": starter_defaults.get("starter_weapon", "Lint Lantern"),
                "kind": "weapon",
                "weapon": starter_defaults.get("starter_weapon", "Lint Lantern"),
                "description": "Starter weapon for this Dungeon run.",
            })
        equipped_weapon = projection["loadout"].get("weapon")
        equipped_armor = projection["loadout"].get("armor")
        equipped_trinket = projection["loadout"].get("trinket")
        projection["inventory"] = [
            {
                **item,
                "equipped": (
                    item.get("kind") == "weapon" and item.get("weapon") == equipped_weapon
                ) or (
                    item.get("kind") == "armor" and item.get("armor") == equipped_armor
                ) or (
                    item.get("kind") == "trinket" and item.get("trinket") == equipped_trinket
                ),
            }
            for item in inventory
        ]
        region = DUNGEON_REGIONS.get(str(run.get("region_id") or ""))
        projection["region"] = {
            "id": region["id"], "label": region["label"], "danger": region["danger"], "signs": list(region["signs"]), "boss": region["boss"],
        } if region else None
        projection["pack"] = self._dungeon_pack_items(run.get("pack"))
        projection["pack_lost"] = self._dungeon_pack_items(run.get("pack_lost"))
        last_banked = run.get("last_banked")
        projection["last_banked"] = [dict(item) for item in last_banked if isinstance(item, Mapping)] if isinstance(last_banked, list) else []
        question = run.get("question")
        if isinstance(question, Mapping):
            projection["question"] = {
                field: question[field]
                for field in ("id", "question_type", "concept_id", "difficulty", "prompt", "options")
                if field in question
            }
            projection["encounter"] = self._dungeon_mob_spec(run)
        elif status == "active" and run.get("room_type") not in {"rest", "market", "selector", "mystery", "cache", "shrine", "corridor"}:
            raise StateCommandError("Active Dungeon run has no current question", status_code=500)
        raw_choices = self._dungeon_live_choices(run) if status == "active" else run.get("room_choices", [])
        if raw_choices is None:
            raw_choices = []
        if not isinstance(raw_choices, list) or len(raw_choices) > len(DUNGEON_ROUTE_CHOICES):
            raise StateCommandError("Existing Dungeon route choices are invalid", status_code=500)
        projection["room_choices"] = [
            {
                field: item[field]
                for field in ("id", "kind", "label", "description")
                if field in item
            }
            for item in raw_choices
            if isinstance(item, Mapping)
        ]
        route = self._dungeon_map_for_run(run)
        if route:
            layout = "grid" if run.get("floor_layout") == "grid" else "lanes"
            visible = None
            if layout == "grid":
                insight = self.hunter_projection(progress)["stats"]["insight"]["value"]
                visible = self._dungeon_grid_visible(route, far_sight=insight >= DUNGEON_GRID_FAR_SIGHT_INSIGHT)
            projection["map"] = {
                "floor": route.get("floor", projection.get("floor", 1)),
                "layout": layout,
                "columns": DUNGEON_GRID_COLUMNS if layout == "grid" else 5,
                "rows": DUNGEON_GRID_ROWS if layout == "grid" else DUNGEON_MAP_ROWS,
                "modifier": run.get("floor_modifier"),
                "nodes": [
                    {
                        key: item[key]
                        for key in ("id", "type", "row", "column", "label", "note")
                        if key in item
                    }
                    for item in route.get("nodes", [])
                    if isinstance(item, Mapping) and (visible is None or item.get("id") in visible)
                ],
                "edges": {
                    str(key): [str(value) for value in values if isinstance(value, str) and (visible is None or value in visible)]
                    for key, values in route.get("edges", {}).items()
                    if isinstance(values, list) and (visible is None or key in visible)
                },
                "current_node_id": route.get("current_node_id"),
            }
            projection["visited_node_ids"] = list(route.get("visited_node_ids", []))
            current_node = self._dungeon_current_map_node(run)
            if current_node:
                projection["current_node"] = {
                    key: current_node[key]
                    for key in ("id", "type", "row", "column", "label", "note")
                    if key in current_node
                }
        risk_profile = run.get("risk_profile")
        # A risk scroll is the only authority allowed to reveal the authored
        # profile.  Never leak a hidden room's title/preview in the public
        # projection; React can still render the generic risk shell.
        risk_visible = str(run.get("risk_status") or "") in {"revealed", "entered"}
        if isinstance(risk_profile, Mapping) and risk_visible:
            projection["risk_profile"] = {
                key: risk_profile[key]
                for key in ("kind", "room_type", "title", "preview")
                if key in risk_profile
            }
            projection["risk_status"] = str(run.get("risk_status") or "unrevealed")
        editor_content = run.get("editor_content", "")
        if not isinstance(editor_content, str):
            raise StateCommandError("Existing Dungeon editor content is invalid", status_code=500)
        projection["editor_content"] = editor_content if status == "active" else ""
        current_question = run.get("question") if isinstance(run.get("question"), Mapping) else {}
        projection["pyr_written"] = bool(current_question.get("id")) and run.get("pyr_question_id") == current_question.get("id")
        last_result = run.get("last_result")
        if isinstance(last_result, Mapping):
            projection["last_result"] = {
                key: last_result[key]
                for key in ("outcome", "question_id", "mob_name", "score_delta", "coins_delta", "damage", "evidence_id", "reason", "hunter_gain", "fight", "loot")
                if key in last_result
            }
        history = run.get("history")
        if isinstance(history, list):
            projection["history"] = [
                {
                    key: item[key]
                    for key in ("room", "floor", "question_id", "mob_name", "outcome", "evidence_id", "score_delta", "coins_delta", "damage")
                    if key in item
                }
                for item in history[-50:]
                if isinstance(item, Mapping)
            ]
        leaderboard = progress.get("dungeon_leaderboard") if isinstance(progress, Mapping) else None
        if isinstance(leaderboard, list):
            projection["leaderboard"] = [
                {
                    key: item[key]
                    for key in ("run_id", "score", "floor", "room", "status", "concept_id", "ended_at")
                    if key in item
                }
                for item in leaderboard[:20]
                if isinstance(item, Mapping)
            ]
        return projection

    @classmethod
    def _dungeon_record_leaderboard(cls, progress: dict[str, Any], run: Mapping[str, Any], status: str) -> None:
        board = progress.setdefault("dungeon_leaderboard", [])
        if not isinstance(board, list):
            raise StateCommandError("Existing Dungeon leaderboard is invalid", status_code=500)
        run_id = str(run.get("run_id") or "")
        if not run_id or any(isinstance(item, Mapping) and item.get("run_id") == run_id for item in board):
            return
        cls._bump_record(progress, "dungeon_runs_ended")
        cls._bump_record(progress, "dungeon_deaths" if status == "dead" else "dungeon_runs_survived")
        cls._bump_record(progress, "dungeon_best_floor", max(1, int(run.get("floor", 1) or 1)), best=True)
        cls._bump_record(progress, "dungeon_best_score", max(0, int(run.get("score", 0) or 0)), best=True)
        board.append(
            {
                "run_id": run_id,
                "score": max(0, int(run.get("score", 0) or 0)),
                "floor": max(1, int(run.get("floor", 1) or 1)),
                "room": max(1, int(run.get("room", 1) or 1)),
                "status": status,
                "concept_id": str(run.get("concept_id") or "python-basics")[:MAX_IDENTIFIER_LENGTH],
                "ended_at": run.get("ended_at") or _utc_now(),
            }
        )
        board.sort(key=lambda item: (-int(item.get("score", 0) or 0), -int(item.get("floor", 0) or 0), str(item.get("ended_at") or "")))
        progress["dungeon_leaderboard"] = board[:MAX_DUNGEON_LEADERBOARD]

    def _dungeon_start_run(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"concept_id", "seed", "class_id", "region_id"}, set())
        existing = self._dungeon_run(progress)
        if isinstance(existing, dict) and existing.get("status") == "active":
            raise StateCommandError("An active Dungeon run already exists", status_code=409)
        self._bump_record(progress, "dungeon_runs_started")

        region_id = None
        if data.get("region_id"):
            region_id = self._text(data["region_id"], "region_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
            if region_id not in DUNGEON_REGIONS:
                raise StateCommandError("Unknown delve region", status_code=422)
        learning = progress.get("learning_state")
        fallback_concept = learning.get("concept") if isinstance(learning, Mapping) else None
        concept_id = data.get("concept_id") or (
            HUNTER_SIGN_CONCEPTS[DUNGEON_REGIONS[region_id]["signs"][0]] if region_id
            else self._dungeon_adaptive_concept(progress, str(fallback_concept or "python-basics"))
        )
        concept_id = self._text(concept_id, "concept_id", max_length=MAX_IDENTIFIER_LENGTH)
        seed = data.get("seed") or uuid.uuid4().hex
        seed = self._text(seed, "seed", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        class_id = self._text(data.get("class_id") or "syntax-warden", "class_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        starter_class = DUNGEON_CLASSES_BY_ID.get(class_id)
        if starter_class is None:
            raise StateCommandError("Unknown Dungeon class", status_code=422)
        run_id = f"dungeon-{uuid.uuid4().hex}"
        player = self._dict(progress, "player")
        vitality = self.hunter_projection(progress)["stats"]["vitality"]["value"]
        kit = self._hunter_kit_levels(progress)
        maximum = (self._counter(player, "max_hp") or 100) + 5 * max(0, vitality - 1) + HUNTER_KIT_COAT_HP * kit["coat"]
        now = _utc_now()
        run = {
            "status": "active",
            "run_id": run_id,
            "seed": seed,
            "class_id": class_id,
            "concept_id": concept_id,
            "region_id": region_id,
            "pack": {},
            "floor": 1,
            "room": 1,
            "room_type": "selector",
            "score": 0,
            "run_coins": int(starter_class.get("starting_coins", 0) or 0),
            "started_at": now,
            "updated_at": now,
            "ended_at": None,
            "loadout": {
                "weapon": starter_class["starter_weapon"],
                "armor": "Apprentice Coat",
                "trinket": None,
                "hp": maximum,
                "max_hp": maximum,
                "heals": 1 + int(starter_class.get("extra_heals", 0) or 0),
                "coins": int(starter_class.get("starting_coins", 0) or 0),
                "bandages": 1 + kit["satchel"],
                "rations": 1,
                "vision_scrolls": 0,
                "tonics": 0,
                "edge_charges": 0,
                "armor_guard": 0,
            },
            "inventory": [
                {
                    "id": "dungeon-starter-armor",
                    "name": "Apprentice Coat",
                    "kind": "armor",
                    "armor": "Apprentice Coat",
                    "description": "Starter armor for this Dungeon run.",
                },
                {
                    "id": starter_class["starter_weapon_id"],
                    "name": starter_class["starter_weapon"],
                    "kind": "weapon",
                    "weapon": starter_class["starter_weapon"],
                    "description": f"Starter weapon for the {starter_class['name']} class.",
                },
            ],
            "question": None,
            "question_number": 0,
            "room_choices": [],
            "map": self._dungeon_generate_grid(seed, 1, region_id=region_id),
            "floor_layout": "grid",
            "floor_modifier": None,
            "risk_profile": None,
            "risk_status": None,
            "camp_action_used": False,
            "next_failure_multiplier": 1,
            "editor_content": "",
            "last_result": None,
            "history": [],
        }
        progress["dungeon_run"] = run
        self._dungeon_prepare_room_choices(run, progress, advance=False)
        projection = self.dungeon_projection(progress)
        return Mutation(
            True,
            {"run": projection},
            {
                "run_id": run_id,
                "floor": 1,
                "room": 1,
                "room_type": "selector",
                "class_id": class_id,
                "class_name": starter_class["name"],
                "question_id": None,
                "question_type": None,
                "room_choices": [choice["id"] for choice in run.get("room_choices", [])],
                "concept_id": concept_id,
                "region_id": region_id,
                "editor_reset": True,
                "reason": "dungeon_run_started",
            },
        )

    def _dungeon_save_editor(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id", "question_id", "content"}, {"run_id", "question_id", "content"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        question_id = self._text(data["question_id"], "question_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        question = run.get("question") if isinstance(run.get("question"), Mapping) else {}
        current_question_id = question.get("id")
        if not isinstance(current_question_id, str) or not current_question_id.strip():
            raise StateCommandError("Active Dungeon run has no current question", status_code=500)
        if question_id != current_question_id:
            raise StateCommandError("Dungeon question changed; reload the current question", status_code=409)
        content = self._multiline_text(data["content"], "content", max_bytes=MAX_DUNGEON_EDITOR_BYTES)
        previous = run.get("editor_content", "")
        if previous == content:
            return Mutation(False, {"run": self.dungeon_projection(progress), "saved": False})
        run["editor_content"] = content
        run["updated_at"] = _utc_now()
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "saved": True},
            {
                "run_id": run_id,
                "floor": run.get("floor", 1),
                "room": run.get("room", 1),
                "question_id": question_id,
                "bytes": len(content.encode("utf-8")),
                "reason": "dungeon_checkpoint_saved",
            },
        )

    def _dungeon_issue_question(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id", "question", "floor", "room", "room_type"}, {"run_id", "question"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        question = self._dungeon_question_spec(data["question"])
        floor = self._integer(data.get("floor", run.get("floor", 1)), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR)
        room = self._integer(data.get("room", run.get("room", 1)), "room", minimum=1, maximum=MAX_DUNGEON_ROOM)
        room_type = self._text(data.get("room_type", run.get("room_type", "encounter")), "room_type", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        previous_question = run.get("question") if isinstance(run.get("question"), Mapping) else {}
        run.update(
            {
                "floor": floor,
                "room": room,
                "room_type": room_type,
                "concept_id": question["concept_id"],
                "question": question,
                "room_choices": [],
                "editor_content": "",
                # Local-only: PYR already wrote this room, so a restart never rewrites it.
                "pyr_question_id": question["id"],
                "updated_at": _utc_now(),
            }
        )
        mob = self._dungeon_mob_spec(run)
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress)},
            {
                "run_id": run_id,
                "floor": floor,
                "room": room,
                "room_type": room_type,
                "question_id": question["id"],
                "question_type": question["question_type"],
                "concept_id": question["concept_id"],
                "mob_name": mob["name"] if mob else None,
                "mob_category": mob["category"] if mob else None,
                "mob_phase": mob["phase"] if mob else None,
                "previous_question_id": previous_question.get("id"),
                "editor_reset": True,
                "reason": "dungeon_question_rotated",
            },
        )

    def _dungeon_record_verdict(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Apply one provider-validated Dungeon answer without Campaign rewards."""

        data = self._payload(
            payload,
            {"run_id", "question_id", "verdict", "evidence_id", "reason"},
            {"run_id", "question_id", "verdict", "evidence_id", "reason"},
        )
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        question_id = self._text(data["question_id"], "question_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        verdict = self._text(data["verdict"], "verdict", max_length=20, identifier=True)
        if verdict not in {"correct", "incorrect"}:
            raise StateCommandError("Dungeon verdict must be correct or incorrect")
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        question = run.get("question") if isinstance(run.get("question"), Mapping) else None
        if question is None or question.get("id") != question_id or run.get("room_type") not in {"encounter", "elite", "boss"}:
            raise StateCommandError("Dungeon question changed; reload the current room", status_code=409)
        fight = self._dungeon_fight(run, progress)
        mob = self._dungeon_pin_foe(run, self._dungeon_mob_spec(run))
        difficulty = self._integer(question.get("difficulty", 1), "question.difficulty", minimum=1, maximum=MAX_DUNGEON_DIFFICULTY)
        run["attempts"] = self._counter(run, "attempts") + 1
        score_delta = 0
        coins_delta = 0
        damage = 0
        hunter_gain = None
        hunter = self.hunter_projection(progress)
        mechanic = fight.get("mechanic") if isinstance(fight.get("mechanic"), dict) else None
        resolve_before = int(fight["resolve"])
        chip = 0
        broke = False
        guard_used = False
        mechanic_fired = None
        blast = 0
        fight_done = False
        loot = None
        pack_lost: list[dict[str, Any]] = []
        if verdict == "correct":
            clean_cast = not any(
                isinstance(item, Mapping) and item.get("question_id") == question_id and item.get("outcome") == "incorrect"
                for item in (run.get("history") if isinstance(run.get("history"), list) else [])
            )
            hunter_gain = self._hunter_record(progress, concept=question.get("concept_id") or run.get("concept_id"), question_type=question.get("question_type"), source="dungeon", clean=clean_cast)
            score_delta = DUNGEON_SCORE_BY_DIFFICULTY[min(difficulty, len(DUNGEON_SCORE_BY_DIFFICULTY) - 1)]
            coins_delta = DUNGEON_COIN_BY_DIFFICULTY[min(difficulty, len(DUNGEON_COIN_BY_DIFFICULTY) - 1)]
            loadout = self._dungeon_ensure_loadout_defaults(run)
            class_data = DUNGEON_CLASSES_BY_ID.get(str(run.get("class_id") or ""), {})
            score_delta += max(0, int(class_data.get("resolve_bonus", 0) or 0))
            if self._counter(loadout, "edge_charges") > 0:
                score_delta += 1
                loadout["edge_charges"] = self._counter(loadout, "edge_charges") - 1
            run["score"] = self._counter(run, "score") + score_delta
            # Progress: exactly one question per correct answer; coins on the clear.
            fight["questions_cleared"] = int(fight["questions_cleared"]) + 1
            fight_done = fight["questions_cleared"] >= int(fight["questions_total"])
            if fight_done:
                run["run_coins"] = self._counter(run, "run_coins") + coins_delta
                loot = self._dungeon_award_loot(run, fight, question.get("concept_id") or run.get("concept_id"), progress)
                coins_delta += loot["coins"]
            else:
                coins_delta = 0
            # Resolve: Strength and the sign's level make each chip bigger;
            # every 3 Focus makes the sign's share hit harder.
            concept_signs = set(hunter_signs_for(question.get("concept_id") or run.get("concept_id")))
            sign_level = max((sign["level"] for sign in hunter["signs"] if sign["id"] in concept_signs), default=0)
            focus_multiplier = 1 + max(0, hunter["stats"]["focus"]["value"] - 1) // 3
            base_chip = DUNGEON_FIGHT_CHIP.get(str(run.get("room_type")), 3)
            chip = (base_chip if clean_cast else max(1, base_chip // 2)) + (hunter["stats"]["strength"]["value"] - 1) + (sign_level // 3) * focus_multiplier
            if loadout.get("trinket") == "Whetstone Charm":
                chip += 1
            chip += int(fight.get("bane", 0) or 0) + self._hunter_kit_levels(progress)["blade"]
            fight["resolve"] = max(0, resolve_before - chip)
            if fight["resolve"] == 0 and not fight_done:
                # A break only helps: a free mistake, the mechanic stops, a few coins.
                broke = True
                fight["breaks"] = int(fight["breaks"]) + 1
                fight["guards"] = int(fight["guards"]) + 1
                fight["resolve"] = int(fight["max_resolve"])
                run["run_coins"] = self._counter(run, "run_coins") + DUNGEON_BREAK_COINS
                coins_delta += DUNGEON_BREAK_COINS
                if mechanic:
                    mechanic["countdown"] = int(mechanic["every"])
                    mechanic["enraged"] = False
        else:
            raw_damage = min(28, 4 + difficulty * 2)
            loadout = self._dungeon_ensure_loadout_defaults(run)
            fight["misses"] = int(fight.get("misses", 0) or 0) + 1
            if int(fight["guards"]) > 0:
                # A banked free mistake absorbs this miss entirely.
                fight["guards"] = int(fight["guards"]) - 1
                guard_used = True
                damage = 0
            else:
                multiplier = max(1, self._counter(run, "next_failure_multiplier") or 1)
                if mechanic and mechanic.get("enraged"):
                    multiplier *= 2
                armor_reduction = 25 if loadout.get("armor") == "Ember Ward" else 0
                if self._counter(loadout, "armor_guard") > 0:
                    loadout["armor_guard"] = 0
                    damage = 0
                else:
                    damage = max(1, (raw_damage * multiplier * (100 - armor_reduction) + 99) // 100)
                if loadout["armor"] == "Ember Ward":
                    loadout["armor"] = "Apprentice Coat"
                run["next_failure_multiplier"] = 1
            current_hp = self._counter(loadout, "hp")
            loadout["hp"] = max(0, current_hp - damage)
        # The mechanic ticks on every answer, unless this answer broke it or
        # ended the fight.
        if mechanic and not broke and not fight_done:
            mechanic["countdown"] = int(mechanic["countdown"]) - 1
            if mechanic["countdown"] <= 0:
                mechanic["countdown"] = int(mechanic["every"])
                mechanic["fired"] = int(mechanic.get("fired", 0)) + 1
                mechanic_fired = mechanic["kind"]
                if mechanic["kind"] == "enrage":
                    mechanic["enraged"] = True
                elif mechanic["kind"] == "self_destruct":
                    blast = DUNGEON_SELF_DESTRUCT_BLAST
                    loadout = self._dungeon_ensure_loadout_defaults(run)
                    loadout["hp"] = max(0, self._counter(loadout, "hp") - blast)

        result_record = {
            "outcome": verdict,
            "question_id": question_id,
            "mob_name": mob["name"] if mob else None,
            "score_delta": score_delta,
            "coins_delta": coins_delta,
            "damage": damage,
            "evidence_id": evidence_id,
            "reason": reason,
        }
        fight_record = {
            "room_type": str(run.get("room_type") or "encounter"),
            "chip": chip,
            "resolve_before": resolve_before,
            "resolve_after": max(0, resolve_before - chip) if verdict == "correct" else resolve_before,
            "max_resolve": int(fight["max_resolve"]),
            "broke": broke,
            "guard_used": guard_used,
            "guards": int(fight["guards"]),
            "mechanic": mechanic["kind"] if mechanic else None,
            "mechanic_label": mechanic["label"] if mechanic else None,
            "mechanic_fired": mechanic_fired,
            "mechanic_countdown": int(mechanic["countdown"]) if mechanic else None,
            "enraged": bool(mechanic and mechanic.get("enraged")),
            "blast": blast,
            "questions_cleared": int(fight["questions_cleared"]),
            "questions_total": int(fight["questions_total"]),
            "fight_done": fight_done,
        }
        run["last_result"] = {**result_record, "fight": fight_record, **({"hunter_gain": hunter_gain} if hunter_gain else {}), **({"loot": loot} if loot else {})}
        self._dungeon_append_history(run, {"room": run.get("room", 1), "floor": run.get("floor", 1), **result_record})
        # A self-destruct blast can end a run on a correct answer too.
        died = self._counter(run.get("loadout") or {}, "hp") <= 0
        # A miss keeps the attempt in dungeon.py so the player can fix it; the
        # next question, a clear or a death starts from a blank buffer.
        editor_reset = verdict == "correct" or died
        if editor_reset:
            run["editor_content"] = ""
        if died:
            ended = _utc_now()
            run.update({"status": "dead", "ended_at": ended, "updated_at": ended, "question": None})
            pack_lost = self._dungeon_forfeit_pack(run)
            self._dungeon_record_leaderboard(progress, run, "dead")
        else:
            if verdict == "correct" and fight_done:
                run.pop("fight", None)
                self._dungeon_set_next_room(run, progress)
            elif verdict == "correct":
                # Same room, next question: the fight (Resolve, free mistakes,
                # mechanic) carries on.
                run["question_number"] = self._counter(run, "question_number") + 1
                run["question"] = self._dungeon_question_for_room(
                    run,
                    room=self._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM),
                    floor=self._integer(run.get("floor", 1), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR),
                )
                run["updated_at"] = _utc_now()
            else:
                run["updated_at"] = _utc_now()
        projection = self.dungeon_projection(progress)
        event = {
            "run_id": run_id,
            "floor": run.get("floor", 1),
            "room": run.get("room", 1),
            "question_id": question_id,
            "mob_name": mob["name"] if mob else None,
            "mob_category": mob["category"] if mob else None,
            "mob_phase": mob["phase"] if mob else None,
            "outcome": verdict,
            "score_delta": score_delta,
            "coins_delta": coins_delta,
            "damage": damage,
            "evidence_id": evidence_id,
            "editor_reset": editor_reset,
            "reason": reason,
        }
        if died:
            event.update({"run_died": True, "score": run.get("score", 0), "pack_lost": pack_lost})
        elif verdict == "correct":
            event.update({"next_room": run.get("room"), "next_room_type": run.get("room_type"), "question_type": (run.get("question") or {}).get("question_type") if isinstance(run.get("question"), Mapping) else None, "concept_id": (run.get("question") or {}).get("concept_id") if isinstance(run.get("question"), Mapping) else run.get("concept_id")})
        event["fight"] = fight_record
        if loot:
            event["loot"] = loot
        return Mutation(True, {"run": projection, **result_record, "fight": fight_record, "run_died": died, "hunter_gain": hunter_gain, "loot": loot, "pack_lost": pack_lost}, event)

    def _dungeon_ensure_loadout_defaults(self, run: dict[str, Any]) -> dict[str, Any]:
        loadout = run.get("loadout")
        if not isinstance(loadout, dict):
            raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
        starter = DUNGEON_CLASSES_BY_ID.get(str(run.get("class_id") or ""), DUNGEON_CLASSES_BY_ID["syntax-warden"])
        defaults = {
            "weapon": starter.get("starter_weapon", "Lint Lantern"),
            "armor": "Apprentice Coat",
            "trinket": None,
            "hp": 100,
            "max_hp": 100,
            "heals": 1,
            "coins": 0,
            "bandages": 1,
            "rations": 1,
            "vision_scrolls": 0,
            "tonics": 0,
            "edge_charges": 0,
            "armor_guard": 0,
        }
        for key, value in defaults.items():
            loadout.setdefault(key, value)
        return loadout

    def _dungeon_camp_action(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id", "action"}, {"run_id", "action"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        action = self._text(data["action"], "action", max_length=32, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") != "rest":
            raise StateCommandError("A campsite is not currently available", status_code=409)
        if run.get("camp_action_used"):
            raise StateCommandError("Only one campsite action is allowed per visit", status_code=409)
        if action not in {"rest", "bandage", "cook", "sharpen", "fortify", "tonic"}:
            raise StateCommandError("Unsupported campsite action", status_code=422)
        loadout = self._dungeon_ensure_loadout_defaults(run)
        current_hp = self._counter(loadout, "hp")
        maximum = self._counter(loadout, "max_hp")
        healed = 0
        if action == "rest":
            charges = self._counter(loadout, "heals")
            if charges <= 0:
                raise StateCommandError("No rest charges remain in this run", status_code=409)
            if current_hp >= maximum:
                raise StateCommandError("HP is already full", status_code=409)
            healed = min(DUNGEON_REST_HEAL, maximum - current_hp)
            loadout["hp"] = current_hp + healed
            loadout["heals"] = charges - 1
        elif action == "bandage":
            charges = self._counter(loadout, "bandages")
            if charges <= 0:
                raise StateCommandError("No field bandages remain", status_code=409)
            if current_hp >= maximum:
                raise StateCommandError("HP is already full", status_code=409)
            healed = min(22, maximum - current_hp)
            loadout["hp"] = current_hp + healed
            loadout["bandages"] = charges - 1
        elif action == "tonic":
            charges = self._counter(loadout, "tonics")
            if charges <= 0:
                raise StateCommandError("No ember tonics remain", status_code=409)
            if current_hp >= maximum:
                raise StateCommandError("HP is already full", status_code=409)
            healed = min(30, maximum - current_hp)
            loadout["hp"] = current_hp + healed
            loadout["tonics"] = charges - 1
        elif action == "cook":
            charges = self._counter(loadout, "rations")
            if charges <= 0:
                raise StateCommandError("No trail rations remain", status_code=409)
            loadout["rations"] = charges - 1
            loadout["max_hp"] = min(300, maximum + 10)
            loadout["hp"] = min(loadout["max_hp"], current_hp + 10)
        elif action == "sharpen":
            if self._counter(loadout, "edge_charges") > 0:
                raise StateCommandError("Your edge is already sharpened", status_code=409)
            loadout["edge_charges"] = 1
        elif action == "fortify":
            if self._counter(loadout, "armor_guard") > 0:
                raise StateCommandError("Your armor is already fortified", status_code=409)
            loadout["armor_guard"] = 1
        run["camp_action_used"] = True
        run["last_result"] = {"outcome": "camp_action", "score_delta": 0, "coins_delta": 0, "damage": 0, "reason": action, "healed": healed}
        self._dungeon_append_history(run, {"room": run.get("room", 1), "floor": run.get("floor", 1), "outcome": "camp_action", "score_delta": 0, "coins_delta": 0, "damage": 0})
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "action": action, "healed": healed},
            {"run_id": run_id, "action": action, "healed": healed, "next_room": run.get("room"), "next_room_type": run.get("room_type"), "reason": "dungeon_camp_action"},
        )

    def _dungeon_use_rest(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Compatibility wrapper for the original rest endpoint."""

        data = self._payload(payload, {"run_id"}, {"run_id"})
        # The original endpoint historically advanced past the campsite.  Keep
        # that contract for older clients/tests while the new camp-action
        # endpoint leaves the player at the campsite so they can see the
        # one-action result before choosing the next route.
        mutation = self._dungeon_camp_action({"run_id": data["run_id"], "action": "rest"}, progress)
        run = self._active_dungeon_run(progress)
        self._dungeon_set_next_room(run, progress)
        result = dict(mutation.result or {})
        result["run"] = self.dungeon_projection(progress)
        event = dict(mutation.event or {})
        event.update({
            "next_room": run.get("room"),
            "next_room_type": run.get("room_type"),
            "editor_reset": True,
            "reason": "dungeon_rest_used",
        })
        return Mutation(True, result, event)

    def _dungeon_reveal_risk(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id"}, {"run_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") != "mystery" or not isinstance(run.get("risk_profile"), Mapping):
            raise StateCommandError("An unrevealed risk room is not currently available", status_code=409)
        if run.get("risk_status") in {"revealed", "entered"}:
            return Mutation(False, {"run": self.dungeon_projection(progress), "revealed": False})
        loadout = self._dungeon_ensure_loadout_defaults(run)
        scrolls = self._counter(loadout, "vision_scrolls")
        if scrolls <= 0:
            raise StateCommandError("You need a vision scroll to scout this risk", status_code=409)
        loadout["vision_scrolls"] = scrolls - 1
        run["risk_status"] = "revealed"
        run["last_result"] = {"outcome": "risk_revealed", "score_delta": 0, "coins_delta": 0, "damage": 0, "reason": "vision_scroll"}
        return Mutation(True, {"run": self.dungeon_projection(progress), "revealed": True}, {"run_id": run_id, "reason": "dungeon_risk_revealed"})

    def _dungeon_enter_risk(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id"}, {"run_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        profile = run.get("risk_profile")
        if run.get("room_type") != "mystery" or not isinstance(profile, Mapping):
            raise StateCommandError("A risk room is not currently available", status_code=409)
        kind = self._text(profile.get("kind"), "risk_profile.kind", max_length=32, identifier=True)
        run["risk_status"] = "entered"
        run["last_result"] = {"outcome": "risk_entered", "score_delta": 0, "coins_delta": 0, "damage": 0, "reason": kind}
        event: dict[str, Any] = {"run_id": run_id, "risk_kind": kind, "reason": "dungeon_risk_entered"}
        if kind in {"elite", "quiz"}:
            room_type = "elite" if kind == "elite" else "encounter"
            run["room_type"] = room_type
            run["room_choices"] = []
            run["concept_id"] = self._dungeon_next_concept(run, progress)
            run["question_number"] = self._counter(run, "question_number") + 1
            question = self._dungeon_question_for_room(run, room=self._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM), floor=self._integer(run.get("floor", 1), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR))
            run["question"] = question
            run["editor_content"] = ""
            self._dungeon_start_fight(run, progress)
            event.update({"room_type": room_type, "question_id": question["id"], "editor_reset": True})
        elif kind in {"discount", "armory"}:
            run["room_type"] = "market"
            run["room_choices"] = []
            run["market_discount"] = 20 if kind == "discount" else 0
            run["question"] = None
            event.update({"room_type": "market"})
        elif kind == "reward":
            loadout = run.get("loadout")
            if isinstance(loadout, dict):
                loadout["bandages"] = min(9, self._counter(loadout, "bandages") + 1)
            run["run_coins"] = self._counter(run, "run_coins") + 20
            self._dungeon_set_next_room(run, progress)
            event.update({"coins_delta": 20, "supply": "bandages", "next_room_type": "selector"})
        elif kind == "debuff":
            run["next_failure_multiplier"] = 2
            self._dungeon_set_next_room(run, progress)
            event.update({"next_failure_multiplier": 2, "next_room_type": "selector"})
        elif kind == "buff":
            loadout = run.get("loadout")
            if isinstance(loadout, dict):
                loadout["edge_charges"] = min(3, self._counter(loadout, "edge_charges") + 1)
            self._dungeon_set_next_room(run, progress)
            event.update({"edge_charge": True, "next_room_type": "selector"})
        else:
            self._dungeon_set_next_room(run, progress)
            event.update({"next_room_type": "selector"})
        run["updated_at"] = _utc_now()
        return Mutation(True, {"run": self.dungeon_projection(progress), "risk_kind": kind}, event)

    def _dungeon_market_purchase(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id", "item_id"}, {"run_id", "item_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") != "market":
            raise StateCommandError("A market room is not currently available", status_code=409)
        item = next((candidate for candidate in DUNGEON_MARKET_CATALOG if candidate["id"] == item_id), None)
        if item is None:
            raise StateCommandError("Unknown Dungeon market item", status_code=404)
        coins = self._counter(run, "run_coins")
        base_price = self._integer(item["price"], "market.price", minimum=0, maximum=MAX_SYNC_COUNTER)
        discount = min(90, self._counter(run, "market_discount"))
        price = max(0, (base_price * (100 - discount) + 99) // 100)
        if coins < price:
            raise StateCommandError(f"Not enough run coins for {item['name']}", status_code=409)
        loadout = self._dungeon_ensure_loadout_defaults(run)
        run["run_coins"] = coins - price
        if item["kind"] == "heal":
            loadout["hp"] = min(self._counter(loadout, "max_hp"), self._counter(loadout, "hp") + 20)
        elif item["kind"] == "supply":
            supply = item.get("supply")
            if not isinstance(supply, str) or supply not in {"bandages", "rations", "vision_scrolls", "tonics"}:
                raise StateCommandError("Unknown Dungeon supply", status_code=500)
            loadout[supply] = min(9, self._counter(loadout, supply) + 1)
        elif item["kind"] in {"weapon", "armor", "trinket"}:
            inventory = self._dungeon_inventory_entries(run, mutate=True)
            if not any(candidate.get("id") == item["id"] for candidate in inventory):
                inventory.append(
                    {
                        key: item[key]
                        for key in ("id", "name", "kind", "weapon", "armor", "trinket", "description")
                        if key in item
                    }
                )
                run["inventory"] = inventory[-MAX_DUNGEON_INVENTORY:]
            # Preserve the previous market behavior while making the choice
            # reversible from the run inventory menu.
            slot = "weapon" if item["kind"] == "weapon" else item["kind"]
            loadout[slot] = item[slot]
        run["last_result"] = {"outcome": "market_purchase", "coins_delta": -price, "score_delta": 0, "damage": 0, "reason": item["name"]}
        if discount:
            run["market_discount"] = 0
        self._dungeon_append_history(run, {"room": run.get("room", 1), "floor": run.get("floor", 1), "outcome": "market_purchase", "coins_delta": -price, "score_delta": 0, "damage": 0})
        return Mutation(True, {"run": self.dungeon_projection(progress), "item": item, "run_coins": run["run_coins"]}, {"run_id": run_id, "item_id": item_id, "item_name": item["name"], "coins_delta": -price, "reason": "dungeon_market_purchase"})

    def _dungeon_equip_item(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id", "item_id"}, {"run_id", "item_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        inventory = self._dungeon_inventory_entries(run, mutate=True)
        item = next((candidate for candidate in inventory if candidate.get("id") == item_id), None)
        if item is None:
            raise StateCommandError("That item is not in this Dungeon run inventory", status_code=404)
        loadout = self._dungeon_ensure_loadout_defaults(run)
        field = "weapon" if item.get("kind") == "weapon" else "armor" if item.get("kind") == "armor" else "trinket"
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            raise StateCommandError("That Dungeon item cannot be equipped", status_code=422)
        if loadout.get(field) == value:
            return Mutation(False, {"run": self.dungeon_projection(progress), "equipped": value, "slot": field})
        loadout[field] = value
        run["updated_at"] = _utc_now()
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "equipped": value, "slot": field},
            {"run_id": run_id, "item_id": item_id, "item_name": item.get("name"), "slot": field, "reason": "dungeon_item_equipped"},
        )

    def _dungeon_reroll_question(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """After a wrong click on a choice question, deal a fresh question in
        the same fight so the options cannot simply be tried one by one."""

        data = self._payload(payload, {"run_id", "question_id"}, {"run_id", "question_id"})
        run = self._active_dungeon_run(progress)
        if run.get("run_id") != data["run_id"]:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        question = run.get("question")
        if run.get("room_type") not in {"encounter", "elite", "boss"} or not isinstance(question, Mapping) or question.get("id") != data["question_id"]:
            raise StateCommandError("That Dungeon question is no longer current", status_code=409)
        run["question_number"] = self._counter(run, "question_number") + 1
        run["question"] = self._dungeon_question_for_room(
            run,
            room=self._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM),
            floor=self._integer(run.get("floor", 1), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR),
        )
        run["editor_content"] = ""
        run["updated_at"] = _utc_now()
        return Mutation(True, {"run": self.dungeon_projection(progress)}, {"run_id": run["run_id"], "question_id": run["question"]["id"], "editor_reset": True, "reason": "dungeon_question_rerolled"})

    def _dungeon_apply_oil(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Coat your blade for the current fight with an oil for its beast."""

        data = self._payload(payload, {"run_id", "oil_id"}, {"run_id", "oil_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        oil_id = self._text(data["oil_id"], "oil_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        question = run.get("question")
        if run.get("room_type") not in {"encounter", "elite", "boss"} or not isinstance(question, Mapping):
            raise StateCommandError("Oils are applied during a fight", status_code=409)
        sign_id, _, tier_id = oil_id.rpartition("-")
        tier = HUNTER_OIL_TIERS_BY_ID.get(tier_id)
        if tier is None or sign_id not in HUNTER_BEASTS:
            raise StateCommandError("Unknown oil", status_code=422)
        hunter = self._hunter_state(progress)
        if self._counter(hunter["oils"], oil_id) <= 0:
            raise StateCommandError("You have none of that oil; craft it at the Merchant", status_code=409)
        if sign_id not in hunter_signs_for(question.get("concept_id") or run.get("concept_id")):
            raise StateCommandError("That oil is made for a different beast", status_code=409)
        fight = self._dungeon_fight(run, progress)
        if isinstance(fight.get("oil"), Mapping):
            raise StateCommandError("This fight already has an oil applied", status_code=409)
        mechanic = fight.get("mechanic")
        if tier_id == "slowing" and not isinstance(mechanic, dict):
            raise StateCommandError("This fight has no mechanic to slow", status_code=409)
        if tier_id == "ward":
            fight["guards"] = int(fight.get("guards", 0) or 0) + 1
        elif tier_id == "slowing":
            mechanic["countdown"] = int(mechanic["countdown"]) + HUNTER_OIL_SLOW_ANSWERS
        else:
            fight["bane"] = HUNTER_OIL_BANE_CHIP
        name = f"{HUNTER_BEASTS[sign_id]['beast'].removeprefix('The ')} {tier['name']}"
        fight["oil"] = {"id": oil_id, "tier": tier_id, "name": name, "effect": tier["effect"]}
        left = self._counter(hunter["oils"], oil_id) - 1
        if left > 0:
            hunter["oils"][oil_id] = left
        else:
            hunter["oils"].pop(oil_id, None)
        run["updated_at"] = _utc_now()
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "hunter": self.hunter_projection(progress), "oil": dict(fight["oil"])},
            {"run_id": run_id, "oil_id": oil_id, "reason": "dungeon_oil_applied"},
        )

    def _dungeon_leave_room(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id"}, {"run_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") not in {"rest", "market"}:
            raise StateCommandError("The current encounter must be resolved first", status_code=409)
        self._dungeon_set_next_room(run, progress)
        return Mutation(True, {"run": self.dungeon_projection(progress)}, {"run_id": run_id, "next_room": run.get("room"), "next_room_type": run.get("room_type"), "editor_reset": True, "reason": "dungeon_room_left"})

    def _dungeon_finish_run(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id"}, {"run_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        ended = _utc_now()
        score = self._counter(run, "score")
        run.update({"status": "complete", "ended_at": ended, "updated_at": ended, "question": None, "editor_content": ""})
        run["last_result"] = {"outcome": "complete", "score_delta": 0, "coins_delta": 0, "damage": 0, "reason": "dungeon_run_finished"}
        banked = self._dungeon_bank_pack(run, progress)
        self._dungeon_record_leaderboard(progress, run, "complete")
        return Mutation(True, {"run": self.dungeon_projection(progress), "score": score, "banked": banked}, {"run_id": run_id, "score": score, "banked": banked, "run_finished": True, "editor_reset": True, "reason": "dungeon_run_finished"})

    def _dungeon_reset_run(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Discard only the active Dungeon checkpoint.

        This is deliberately separate from ``dungeon_finish_run``: reset is a
        local run-management operation for restarting the prototype/run setup,
        while finish banks a score on the local Dungeon leaderboard.  Campaign
        progress, equipment, Codex evidence and the canonical player save are
        never changed by this action.
        """

        data = self._payload(payload, {"run_id"}, {"run_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        progress["dungeon_run"] = None
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "reset": True, "run_id": run_id},
            {"run_id": run_id, "editor_reset": True, "reason": "dungeon_run_reset", "campaign_untouched": True},
        )

    def _dungeon_record_death(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id", "reason"}, {"run_id", "reason"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        reason = self._text(data["reason"], "reason")
        ended = _utc_now()
        score = self._counter(run, "score")
        floor = self._counter(run, "floor")
        run.update({"status": "dead", "ended_at": ended, "updated_at": ended, "editor_content": "", "question": None})
        pack_lost = self._dungeon_forfeit_pack(run)
        self._dungeon_record_leaderboard(progress, run, "dead")
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "pack_lost": pack_lost},
            {"run_id": run_id, "floor": floor, "score": score, "pack_lost": pack_lost, "editor_reset": True, "reason": reason},
        )

    def _metadata_from_progress(self, progress: Mapping[str, Any]) -> dict[str, Any]:
        raw = progress.get("meta") if isinstance(progress.get("meta"), dict) else {}
        device_id = raw.get("device_id") if _is_safe_device_id(raw.get("device_id")) else self.device_id()
        updated_at = raw.get("updated_at") if isinstance(raw.get("updated_at"), str) else None
        return {"revision": self._revision(progress), "updated_at": updated_at, "device_id": device_id}

    def apply_internal(self, action: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """Apply a system/game command from trusted in-process code only."""

        return self.apply(action, payload, SYSTEM_ACTOR, internal=True)

    def apply(
        self,
        action: str,
        payload: Mapping[str, Any],
        actor: str,
        *,
        internal: bool = False,
    ) -> dict[str, Any]:
        normalized_action = self._normalize_action(action)
        definition = ACTION_DEFINITIONS.get(normalized_action)
        if definition is None:
            raise StateCommandError(f"Unknown state action: {normalized_action}")
        if definition.internal and not internal:
            raise StateCommandError("This state action is reserved for trusted game code", status_code=403)
        if internal and actor != SYSTEM_ACTOR:
            raise StateCommandError("Internal state actions require the system actor", status_code=403)
        if actor not in definition.actors:
            raise StateCommandError(
                f"Actor '{actor}' is not permitted to perform {normalized_action}",
                status_code=403,
            )

        with self._progress_lock:
            progress = self._load_locked()
            if normalized_action != "campaign_extend":
                # Every action sees the authored campaign; campaign_extend
                # itself does (and persists) the same work.
                self._extend_campaign(progress)
            if self._boss_is_active(progress) and (normalized_action.startswith("dungeon_") or normalized_action in {
                "homestead_action", "home_room_purchase", "homestead_room_upgrade", "homestead_purchase", "homestead_equip",
                "campaign_market_purchase", "equip_equipment", "set_avatar", "select_campaign", "hunter_spend_point",
                "hunter_craft_oil", "hunter_upgrade_kit", "hunter_identify_start", "hunter_identify_answer",
                "practice_session_started", "practice_record_attempt", "armory_equip", "armory_unequip", "armory_use", "armory_buy",
            }):
                raise StateCommandError("Leave the boss fight first; retreat resets its progress", status_code=409)
            mutation = self._dispatch(normalized_action, payload, progress)
            if mutation.changed:
                # A cloud pull can bring back a shorter board; re-extend it.
                self._extend_campaign(progress)
            if not mutation.changed:
                return {
                    "ok": True,
                    "action": normalized_action,
                    "actor": actor,
                    "changed": False,
                    "revision": self._revision(progress),
                    "result": mutation.result,
                }

            metadata, event = self._persist_locked(
                progress,
                action=normalized_action,
                actor=actor,
                event_details=mutation.event,
            )
            return {
                "ok": True,
                "action": normalized_action,
                "actor": actor,
                "changed": True,
                "revision": metadata["revision"],
                "result": mutation.result,
                "event": event,
            }

    def _load_locked(self) -> dict[str, Any]:
        try:
            value = json.loads(self.progress_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise StateCommandError("progress.json could not be loaded", status_code=500) from exc
        if not isinstance(value, dict) or not value:
            raise StateCommandError("progress.json could not be loaded", status_code=500)
        return value

    def _write_atomic_locked(self, progress: dict[str, Any]) -> None:
        path = self.progress_path
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(path.suffix + ".tmp")
        temp.write_text(json.dumps(progress, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        temp.replace(path)

    @staticmethod
    def _path_has_symlink_component(path: Path) -> bool:
        current = path
        while True:
            if current.is_symlink():
                return True
            parent = current.parent
            if parent == current:
                return False
            current = parent

    @staticmethod
    def _custody_marker_payload(
        *,
        source_digest: str,
        source_revision: int,
        destination_digest: str,
        destination_revision: int,
    ) -> dict[str, Any]:
        return {
            "schema_version": CUSTODY_MARKER_VERSION,
            "source_digest": source_digest,
            "source_revision": source_revision,
            "destination_digest": destination_digest,
            "destination_revision": destination_revision,
            "recorded_at": _utc_now(),
        }

    @classmethod
    def _write_custody_marker(
        cls,
        marker: Path,
        *,
        source_digest: str,
        source_revision: int,
        destination_digest: str,
        destination_revision: int,
    ) -> None:
        if marker.is_symlink() or marker.exists():
            raise StateCommandError("Custody marker already exists; review it before retrying", status_code=409)
        marker.parent.mkdir(parents=True, exist_ok=True)
        temporary = marker.with_name(f".{marker.name}.{uuid.uuid4().hex}.tmp")
        payload = cls._custody_marker_payload(
            source_digest=source_digest,
            source_revision=source_revision,
            destination_digest=destination_digest,
            destination_revision=destination_revision,
        )
        try:
            with temporary.open("x", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2, ensure_ascii=False)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(marker)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise StateCommandError("Custody marker could not be written atomically", status_code=500) from exc

    @classmethod
    def _ensure_custody_marker(
        cls,
        marker: Path,
        *,
        source_digest: str,
        source_revision: int,
        destination_digest: str,
        destination_revision: int,
    ) -> bool:
        if marker.is_symlink():
            raise StateCommandError("Custody marker may not be a symlink", status_code=409)
        if marker.exists():
            existing = _read_state_file(marker)
            expected = {
                "schema_version": CUSTODY_MARKER_VERSION,
                "source_digest": source_digest,
                "source_revision": source_revision,
                "destination_digest": destination_digest,
                "destination_revision": destination_revision,
            }
            if not isinstance(existing, dict) or any(existing.get(key) != value for key, value in expected.items()):
                raise StateCommandError("Custody marker disagrees with the snapshot; review it before retrying", status_code=409)
            return False
        cls._write_custody_marker(
            marker,
            source_digest=source_digest,
            source_revision=source_revision,
            destination_digest=destination_digest,
            destination_revision=destination_revision,
        )
        return True

    def _persist_locked(
        self,
        progress: dict[str, Any],
        *,
        action: str | None = None,
        actor: str | None = None,
        event_details: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        existing = progress.get("meta") if isinstance(progress.get("meta"), dict) else {}
        revision = self._revision(progress)
        existing_device = existing.get("device_id")
        device_id = existing_device if _is_safe_device_id(existing_device) else self.device_id()
        metadata = {"revision": revision + 1, "updated_at": _utc_now(), "device_id": device_id}
        progress["meta"] = metadata

        event = None
        if event_details is not None:
            event = {
                "id": uuid.uuid4().hex,
                "action": action,
                "actor": actor,
                "revision": metadata["revision"],
                "recorded_at": metadata["updated_at"],
                **event_details,
            }
            events = progress.get("state_events")
            if not isinstance(events, list):
                events = []
            progress["state_events"] = (events + [event])[-MAX_EVENT_RECORDS:]

        self._write_atomic_locked(progress)
        return metadata, event

    @staticmethod
    def _normalize_action(action: object) -> str:
        if not isinstance(action, str):
            raise StateCommandError("action must be a string")
        normalized = action.strip()
        if not normalized or len(normalized) > 80 or not re.fullmatch(r"[a-z][a-z0-9_]*", normalized):
            raise StateCommandError("action must be a lowercase named command")
        return normalized

    @staticmethod
    def _revision(progress: Mapping[str, Any]) -> int:
        metadata = progress.get("meta")
        raw = metadata.get("revision", 0) if isinstance(metadata, dict) else 0
        if isinstance(raw, bool):
            return 0
        try:
            return max(0, int(raw))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _payload(payload: Mapping[str, Any], allowed: set[str], required: set[str]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise StateCommandError("payload must be an object")
        keys = set(payload)
        unknown = sorted(keys - allowed)
        if unknown:
            raise StateCommandError(f"Unsupported payload field(s): {', '.join(unknown)}")
        missing = sorted(required - keys)
        if missing:
            raise StateCommandError(f"Missing payload field(s): {', '.join(missing)}")
        return dict(payload)

    @staticmethod
    def _text(value: object, field: str, *, max_length: int = MAX_REASON_LENGTH, identifier: bool = False) -> str:
        if not isinstance(value, str):
            raise StateCommandError(f"{field} must be text")
        normalized = value.strip()
        if not normalized or len(normalized) > max_length or any(ord(character) < 32 for character in normalized):
            raise StateCommandError(f"{field} must be bounded text without control characters")
        if identifier:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", normalized):
                raise StateCommandError(f"{field} must be a safe identifier")
        elif any(character in normalized for character in "/\\:\u0000"):
            raise StateCommandError(f"{field} cannot contain path-like characters")
        return normalized

    @staticmethod
    def _integer(value: object, field: str, *, minimum: int | None = None, maximum: int | None = None) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise StateCommandError(f"{field} must be an integer")
        if minimum is not None and value < minimum:
            raise StateCommandError(f"{field} must be at least {minimum}")
        if maximum is not None and value > maximum:
            raise StateCommandError(f"{field} must be at most {maximum}")
        return value

    @staticmethod
    def _counter(container: dict[str, Any], field: str) -> int:
        raw = container.get(field, 0)
        if isinstance(raw, bool):
            raise StateCommandError(f"Existing state field {field} is invalid", status_code=500)
        try:
            value = int(raw)
        except (TypeError, ValueError) as exc:
            raise StateCommandError(f"Existing state field {field} is invalid", status_code=500) from exc
        return max(0, value)

    @staticmethod
    def _dict(container: dict[str, Any], field: str) -> dict[str, Any]:
        value = container.get(field)
        if value is None:
            value = {}
            container[field] = value
        if not isinstance(value, dict):
            raise StateCommandError(f"Existing state field {field} is invalid", status_code=500)
        return value

    @staticmethod
    def _catalog(progress: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
        homestead = progress.get("homestead")
        if not isinstance(homestead, dict):
            return {}
        catalog = homestead.get("catalog")
        if not isinstance(catalog, list):
            return {}
        return {
            str(item.get("id")): item
            for item in catalog
            if isinstance(item, dict) and item.get("id")
        }

    @classmethod
    def equipment_projection(cls, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Return only campaign gear already owned by the canonical save.

        The static catalogue is used for descriptions/effects, but it is never
        returned wholesale.  A legacy save without owned lists exposes only
        its currently equipped values, so the UI cannot turn future loot into
        an apparent inventory.
        """

        raw_equipment = progress.get("equipment")
        equipment = raw_equipment if isinstance(raw_equipment, Mapping) else {}
        slots: list[dict[str, Any]] = []
        for kind, owned_field, equipped_field, label in (
            ("armor", "owned_armor", "armor", "ARMOR"),
            ("trinket", "owned_trinkets", "trinket", "TRINKET"),
        ):
            current_name = str(equipment.get(equipped_field) or ("Apprentice Coat" if kind == "armor" else "None"))
            raw_owned = equipment.get(owned_field)
            raw_owned_values = raw_owned if isinstance(raw_owned, list) else []
            owned_ids = [
                item_id for item_id in raw_owned_values
                if isinstance(item_id, str) and item_id in EQUIPMENT_BY_ID
            ]
            current_id = EQUIPMENT_ID_BY_NAME.get(current_name)
            if current_id and current_id not in owned_ids:
                owned_ids.insert(0, current_id)
            items: list[dict[str, Any]] = []
            for item_id in owned_ids[:MAX_EQUIPMENT_ITEMS]:
                item = EQUIPMENT_BY_ID[item_id]
                if item.get("kind") != kind:
                    continue
                items.append(
                    {
                        "id": item_id,
                        "name": item["name"],
                        "kind": kind,
                        "effect": item["effect"],
                        "description": item["description"],
                        "equipped": item["name"] == current_name,
                    }
                )
            if not items and current_name:
                # Preserve an older validated value without fabricating an
                # unlock record or silently rewriting the save.
                items.append(
                    {
                        "id": f"legacy-{kind}",
                        "name": current_name,
                        "kind": kind,
                        "effect": "Existing campaign loadout",
                        "description": "Recorded in the canonical save; no new reward was inferred.",
                        "equipped": True,
                    }
                )
            slots.append(
                {
                    "id": kind,
                    "label": label,
                    "equipped": current_name,
                    "items": items,
                }
            )
        try:
            avatar = cls._avatar_value(equipment.get("avatar", {}), "equipment.avatar")
        except StateCommandError:
            avatar = dict(DEFAULT_AVATAR)
        return {"slots": slots, "avatar": avatar, "avatar_options": {key: list(values) for key, values in AVATAR_OPTIONS.items()}}

    def _dispatch(self, action: str, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        handlers = {
            "homestead_purchase": self._homestead_purchase,
            "homestead_equip": self._homestead_equip,
            "campaign_market_purchase": self._campaign_market_purchase,
            "homestead_room_upgrade": self._homestead_room_upgrade,
            "home_room_purchase": self._home_room_purchase,
            "homestead_action": self._homestead_action,
            "boss_start": self._boss_start,
            "boss_retreat": self._boss_retreat,
            "equip_equipment": self._equip_equipment,
            "set_avatar": self._set_avatar,
            "select_campaign": self._select_campaign,
            "hunter_spend_point": self._hunter_spend_point,
            "record_learning_event": self._record_learning_event,
            "record_reference_mode": self._record_reference_mode,
            "record_pyr_assist": self._record_pyr_assist,
            "record_code_activity": self._record_code_activity,
            "award_learning_reward": self._award_learning_reward,
            "player_hp_change": self._player_hp_change,
            "record_achievement": self._record_achievement,
            "record_battle_objective": self._record_battle_objective,
            "record_equipment_unlock": self._record_equipment_unlock,
            "complete_mob": self._complete_mob,
            "record_boss_requirement": self._record_boss_requirement,
            "record_boss_clear": self._record_boss_clear,
            "record_battle_miss": self._record_battle_miss,
            "reconcile_legacy_progress": self._reconcile_legacy_progress,
            "record_codex_note": self._record_codex_note,
            "practice_session_started": self._practice_session_started,
            "practice_record_attempt": self._practice_record_attempt,
            "dungeon_start_run": self._dungeon_start_run,
            "dungeon_choose_room": self._dungeon_choose_room,
            "dungeon_save_editor": self._dungeon_save_editor,
            "dungeon_issue_question": self._dungeon_issue_question,
            "dungeon_record_verdict": self._dungeon_record_verdict,
            "dungeon_record_death": self._dungeon_record_death,
            "dungeon_use_rest": self._dungeon_use_rest,
            "dungeon_camp_action": self._dungeon_camp_action,
            "dungeon_reveal_risk": self._dungeon_reveal_risk,
            "dungeon_enter_risk": self._dungeon_enter_risk,
            "dungeon_market_purchase": self._dungeon_market_purchase,
            "dungeon_equip_item": self._dungeon_equip_item,
            "dungeon_apply_oil": self._dungeon_apply_oil,
            "dungeon_travel": self._dungeon_travel,
            "dungeon_reroll_question": self._dungeon_reroll_question,
            "hunter_craft_oil": self._hunter_craft_oil,
            "hunter_upgrade_kit": self._hunter_upgrade_kit,
            "armory_equip": self._armory_equip,
            "armory_unequip": self._armory_unequip,
            "armory_use": self._armory_use,
            "armory_buy": self._armory_buy,
            "campaign_extend": self._campaign_extend,
            "hunter_identify_start": self._hunter_identify_start,
            "hunter_identify_answer": self._hunter_identify_answer,
            "dungeon_leave_room": self._dungeon_leave_room,
            "dungeon_finish_run": self._dungeon_finish_run,
            "dungeon_reset_run": self._dungeon_reset_run,
        }
        return handlers[action](payload, progress)

    @staticmethod
    def _avatar_value(value: object, field: str) -> dict[str, str]:
        """Validate a (partial) avatar appearance; missing keys use defaults."""

        if not isinstance(value, Mapping):
            raise StateCommandError(f"{field} must be an object")
        unknown = sorted(set(value) - set(AVATAR_OPTIONS))
        if unknown:
            raise StateCommandError(f"Unsupported {field} field(s): {', '.join(unknown)}")
        clean = dict(DEFAULT_AVATAR)
        for key, choice in value.items():
            if choice not in AVATAR_OPTIONS[key]:
                raise StateCommandError(f"{field}.{key} is not an available option")
            clean[key] = choice
        return clean

    @staticmethod
    def _hunter_seed(progress: Mapping[str, Any]) -> dict[str, Any]:
        """Starting hunter progress for a save that predates signs, built only
        from evidence it already holds: each defeated campaign bounty counts as
        using its sign in a real project, each correct practice answer as a
        clean Tutor cast."""

        signs: dict[str, dict[str, Any]] = {}

        def bump(concept: object, **counters: int) -> None:
            for sign_id in hunter_signs_for(concept):
                sign = signs.setdefault(sign_id, {})
                for key, amount in counters.items():
                    sign[key] = sign.get(key, 0) + amount

        for project in progress.get("projects", []) if isinstance(progress.get("projects"), list) else []:
            if not isinstance(project, Mapping):
                continue
            for mob in project.get("mobs", []) if isinstance(project.get("mobs"), list) else []:
                if isinstance(mob, Mapping) and mob.get("status") in {"defeated", "cleared"}:
                    bump(mob.get("concept"), campaign_uses=1, xp=HUNTER_SIGN_XP["campaign_use"])
        for session in progress.get("practice_sessions", []) if isinstance(progress.get("practice_sessions"), list) else []:
            correct = session.get("correct", 0) if isinstance(session, Mapping) else 0
            if isinstance(correct, int) and correct > 0:
                bump(session.get("concept"), clean_casts=correct, tutor_passes=correct, xp=HUNTER_SIGN_XP["clean"] * correct)
        return {"signs": signs, "stats_xp": {}, "spent": {}, "seeded_from_history": True}

    @classmethod
    def _hunter_state(cls, progress: dict[str, Any]) -> dict[str, Any]:
        hunter = progress.get("hunter")
        if not isinstance(hunter, dict):
            hunter = cls._hunter_seed(progress)
            progress["hunter"] = hunter
        for key in ("signs", "stats_xp", "spent", "materials", "oils", "kit", "armory"):
            if not isinstance(hunter.get(key), dict):
                hunter[key] = {}
        armory = hunter["armory"]
        if not isinstance(armory.get("owned"), list):
            armory["owned"] = []
        for key in ("stack", "buffs"):
            if not isinstance(armory.get(key), dict):
                armory[key] = {}
        return hunter

    def _hunter_record(
        self,
        progress: dict[str, Any],
        *,
        concept: object,
        question_type: object,
        source: str,
        clean: bool,
        campaign_use: bool = False,
    ) -> dict[str, Any]:
        """Grow signs and stats for one verified correct answer, or for a
        cleared campaign bounty (campaign_use). Returns what was gained."""

        if not campaign_use:
            self._log_activity(progress, "answers")
            self._bump_record(progress, "answers_verified")

        hunter = self._hunter_state(progress)
        now = _utc_now()
        qtype = str(question_type or "")
        gain: dict[str, Any] = {"signs": [], "stats": {}}
        for sign_id in hunter_signs_for(concept):
            sign = hunter["signs"].setdefault(sign_id, {})
            xp = 0
            if campaign_use:
                sign["campaign_uses"] = self._counter(sign, "campaign_uses") + 1
                xp += HUNTER_SIGN_XP["campaign_use"]
            else:
                if clean:
                    sign["clean_casts"] = self._counter(sign, "clean_casts") + 1
                    xp += HUNTER_SIGN_XP["clean"]
                else:
                    sign["recovered"] = self._counter(sign, "recovered") + 1
                    xp += HUNTER_SIGN_XP["recovered"]
                if source == "tutor":
                    sign["tutor_passes"] = self._counter(sign, "tutor_passes") + 1
                if source == "dungeon" and clean:
                    sign["dungeon_clean"] = self._counter(sign, "dungeon_clean") + 1
                if qtype in HUNTER_TEACHBACK_TYPES:
                    sign["teachbacks"] = self._counter(sign, "teachbacks") + 1
                    xp += HUNTER_SIGN_XP["teachback"]
            sign["xp"] = min(9999, self._counter(sign, "xp") + xp)
            sign["last_used_at"] = now
            gain["signs"].append({"id": sign_id, "xp": xp})
        if not campaign_use:
            stats_xp = hunter["stats_xp"]
            stat = HUNTER_STAT_BY_TYPE.get(qtype)
            if stat:
                amount = 2 if clean else 1
                stats_xp[stat] = self._counter(stats_xp, stat) + amount
                gain["stats"][stat] = amount
            today = now[:10]
            if hunter.get("last_active_day") != today:
                # Vitality grows from showing up: the first correct answer each day.
                hunter["last_active_day"] = today
                stats_xp["vitality"] = self._counter(stats_xp, "vitality") + 2
                gain["stats"]["vitality"] = gain["stats"].get("vitality", 0) + 2
        return gain

    @classmethod
    def hunter_projection(cls, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Signs (level, rank, gates, dulling) and stats for the hunter sheet."""

        hunter = progress.get("hunter") if isinstance(progress.get("hunter"), Mapping) else cls._hunter_seed(progress)
        raw_signs = hunter.get("signs") if isinstance(hunter.get("signs"), Mapping) else {}
        now = datetime.now(timezone.utc)

        def count(source: Mapping[str, Any], key: str) -> int:
            value = source.get(key, 0)
            return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0

        signs = []
        for sign_id in HUNTER_SIGN_KEYWORDS:
            raw = raw_signs.get(sign_id) if isinstance(raw_signs.get(sign_id), Mapping) else {}
            counters = {key: count(raw, key) for key in HUNTER_SIGN_COUNTERS}
            xp = counters["xp"]
            xp_level = sum(1 for need in HUNTER_SIGN_LEVELS if xp >= need)
            gates = {
                "inscribed": counters["tutor_passes"] >= 1,
                "honed": counters["clean_casts"] >= HUNTER_HONED_CLEAN_CASTS,
                "mastered": counters["campaign_uses"] >= 1 and counters["teachbacks"] >= 1,
            }
            cap = 2 if not gates["inscribed"] else 5 if not gates["honed"] else 9 if not gates["mastered"] else 10
            level = min(xp_level, cap)
            rank = 3 if level >= 10 else 2 if level >= 6 else 1 if level >= 3 else 0
            days_unused = None
            last_used = raw.get("last_used_at")
            if isinstance(last_used, str):
                try:
                    days_unused = (now - datetime.fromisoformat(last_used)).days
                except ValueError:
                    days_unused = None
            dull = bool(level and days_unused is not None and days_unused >= HUNTER_DULL_DAYS)
            effective = max(level - 1, 3 if rank >= 1 else 0) if dull else level
            if not gates["inscribed"]:
                next_gate = "Pass a Tutor drill with this sign"
            elif not gates["honed"]:
                next_gate = f"{counters['clean_casts']} / {HUNTER_HONED_CLEAN_CASTS} clean casts"
            elif not gates["mastered"]:
                missing = []
                if counters["campaign_uses"] < 1:
                    missing.append("use it in a campaign bounty")
                if counters["teachbacks"] < 1:
                    missing.append("explain it back to PYR")
                next_gate = "Then " + " and ".join(missing)
            else:
                next_gate = None
            signs.append({
                "id": sign_id,
                "xp": xp,
                "level": effective,
                "earned_level": level,
                "rank": rank,
                "rank_name": HUNTER_RANK_NAMES[rank],
                "next_level_xp": HUNTER_SIGN_LEVELS[xp_level] if xp_level < len(HUNTER_SIGN_LEVELS) else None,
                "held_by_gate": xp_level > level,
                "gates": gates,
                "next_gate": next_gate,
                "dull": dull,
                "days_unused": days_unused,
                **{key: counters[key] for key in HUNTER_SIGN_COUNTERS if key != "xp"},
            })

        stats_xp = hunter.get("stats_xp") if isinstance(hunter.get("stats_xp"), Mapping) else {}
        spent = hunter.get("spent") if isinstance(hunter.get("spent"), Mapping) else {}
        player = progress.get("player") if isinstance(progress.get("player"), Mapping) else {}
        player_level = max(1, count(player, "level") or 1)
        stats = {}
        for name in HUNTER_STATS:
            xp = count(stats_xp, name)
            trained = xp // HUNTER_STAT_XP_PER_POINT
            stats[name] = {
                "value": 1 + trained + count(spent, name),
                "xp": xp,
                "trained": trained,
                "spent": count(spent, name),
                "next_at": (trained + 1) * HUNTER_STAT_XP_PER_POINT,
            }
        points = max(0, player_level - 1)
        spent_total = sum(count(spent, name) for name in HUNTER_STATS)
        materials = cls._dungeon_pack_items(hunter.get("materials"))
        bank = hunter.get("materials") if isinstance(hunter.get("materials"), Mapping) else {}
        owned_oils = hunter.get("oils") if isinstance(hunter.get("oils"), Mapping) else {}
        coins = count(player, "coins")
        ranks = {sign["id"]: sign["rank"] for sign in signs}
        recipes = []
        oils = []
        for sign_id, beast in HUNTER_BEASTS.items():
            essence = next(region["essence"] for region in DUNGEON_REGIONS.values() if sign_id in region["signs"])
            for tier in HUNTER_OIL_TIERS:
                oil_id = f"{sign_id}-{tier['id']}"
                needs = {beast["part"]: tier["parts"], **({essence: tier["essence"]} if tier["essence"] else {})}
                inputs = [{"id": key, "name": DUNGEON_MATERIAL_NAMES[key], "count": need, "have": count(bank, key)} for key, need in needs.items()]
                recipe = {
                    "id": oil_id,
                    "sign": sign_id,
                    "tier": tier["id"],
                    "name": f"{beast['beast'].removeprefix('The ')} {tier['name']}",
                    "effect": tier["effect"],
                    "rank_needed": tier["rank"],
                    "unlocked": ranks.get(sign_id, 0) >= tier["rank"],
                    "coins": tier["coins"],
                    "materials": inputs,
                    "affordable": coins >= tier["coins"] and all(item["have"] >= item["count"] for item in inputs),
                    "owned": count(owned_oils, oil_id),
                }
                recipes.append(recipe)
                if recipe["owned"]:
                    oils.append({key: recipe[key] for key in ("id", "sign", "tier", "name", "effect")} | {"count": recipe["owned"]})
        raw_kit = hunter.get("kit") if isinstance(hunter.get("kit"), Mapping) else {}
        kit = []
        for track, info in HUNTER_KIT.items():
            level = min(HUNTER_KIT_MAX_LEVEL, count(raw_kit, track))
            entry = {"id": track, "name": info["name"], "effect": info["effect"], "level": level, "max_level": HUNTER_KIT_MAX_LEVEL, "next": None}
            if level < HUNTER_KIT_MAX_LEVEL:
                need = level + 1
                entry["next"] = {
                    "essence": info["essence"],
                    "essence_name": DUNGEON_MATERIAL_NAMES[info["essence"]],
                    "count": need,
                    "have": count(bank, info["essence"]),
                    "coins": HUNTER_KIT_COINS_PER_LEVEL * need,
                    "affordable": count(bank, info["essence"]) >= need and coins >= HUNTER_KIT_COINS_PER_LEVEL * need,
                }
            kit.append(entry)
        puzzle = hunter.get("identify") if isinstance(hunter.get("identify"), Mapping) else None
        identify = {key: puzzle[key] for key in ("id", "sign", "prompt", "options") if key in puzzle} if puzzle else None
        return {
            "signs": signs, "stats": stats, "level": player_level, "free_points": max(0, points - spent_total),
            "materials": materials, "oil_recipes": recipes, "oils": oils, "kit": kit,
            "vials": count(bank, DUNGEON_VIAL), "identify": identify,
        }

    @staticmethod
    def _armory_add(hunter: dict[str, Any], item_id: str, count: int = 1) -> None:
        item = armory_catalog().get(item_id)
        if item is None:
            return
        armory = hunter.setdefault("armory", {})
        armory.setdefault("owned", [])
        armory.setdefault("stack", {})
        if item["slot"] in ARMORY_STACK_SLOTS:
            armory["stack"][item_id] = min(ARMORY_MAX_STACK, int(armory["stack"].get(item_id, 0) or 0) + max(1, count))
        elif item_id not in armory["owned"]:
            armory["owned"].append(item_id)

    @classmethod
    def _gear_effects(cls, progress: Mapping[str, Any]) -> dict[str, Any]:
        """What the equipped weapon, armour and trinket and every relic do."""

        catalog = armory_catalog()
        by_name = armory_by_name()
        equipment = progress.get("equipment") if isinstance(progress.get("equipment"), Mapping) else {}
        hunter = progress.get("hunter") if isinstance(progress.get("hunter"), Mapping) else {}
        armory = hunter.get("armory") if isinstance(hunter.get("armory"), Mapping) else {}
        owned = [item for item in armory.get("owned", []) if isinstance(item, str)] if isinstance(armory.get("owned"), list) else []
        weapon = catalog.get(armory.get("weapon")) if isinstance(armory.get("weapon"), str) and armory.get("weapon") in owned else None
        armor_name = str(equipment.get("armor") or "")
        armor = by_name.get(armor_name) if by_name.get(armor_name, {}).get("slot") == "armor" else None
        trinket_name = str(equipment.get("trinket") or "")
        trinket = by_name.get(trinket_name)
        trinket = trinket if trinket and trinket["slot"] == "trinket" else None
        if trinket is None and trinket_name in LEGACY_TRINKET_EFFECTS:
            trinket = {"name": trinket_name, "slot": "trinket", "effect": LEGACY_TRINKET_EFFECTS[trinket_name]}
        relics = [catalog[item] for item in owned if item in catalog and catalog[item]["slot"] == "relic"]
        trinket_effect = trinket["effect"] if trinket else {}
        armor_effect = armor["effect"] if armor else {}

        def capped(key: str, value: object) -> int:
            return max(0, min(ARMORY_EFFECT_CAPS[key], int(value or 0)))

        return {
            "weapon": {key: (capped(key, value) if key in ARMORY_EFFECT_CAPS else value) for key, value in weapon["effect"].items()} if weapon else None,
            "reduction": min(ARMORY_REDUCTION_CAP, capped("reduction", armor_effect.get("reduction")) if armor else LEGACY_ARMOR_REDUCTION.get(armor_name, 0)),
            "first_miss_free": bool(armor_effect.get("first_miss_free")),
            "block_first_miss": bool(trinket_effect.get("block_first_miss")),
            "first_miss_source": armor["name"] if armor_effect.get("first_miss_free") else trinket["name"] if trinket else None,
            "revive": bool(trinket_effect.get("revive")),
            "start_guards": capped("start_guards", trinket_effect.get("start_guards")),
            "heal_on_objective": capped("heal_on_objective", trinket_effect.get("heal_on_objective")),
            "loot_luck": capped("loot_luck", trinket_effect.get("loot_luck")),
            "coin_bonus": min(ARMORY_BONUS_CAP, capped("coin_bonus", trinket_effect.get("coin_bonus")) + sum(capped("coin_bonus", relic["effect"].get("coin_bonus")) for relic in relics)),
            "xp_bonus": min(ARMORY_BONUS_CAP, capped("xp_bonus", trinket_effect.get("xp_bonus")) + sum(capped("xp_bonus", relic["effect"].get("xp_bonus")) for relic in relics)),
        }

    def _armory_take_buffs(self, progress: dict[str, Any]) -> dict[str, int]:
        """Hand over (and clear) the food buffs waiting for the next battle."""

        hunter = progress.get("hunter")
        armory = hunter.get("armory") if isinstance(hunter, dict) and isinstance(hunter.get("armory"), dict) else None
        if not armory or not isinstance(armory.get("buffs"), dict) or not armory["buffs"]:
            return {}
        buffs = {key: max(0, min(ARMORY_BUFF_CAPS[key], int(value or 0))) for key, value in armory["buffs"].items() if key in ARMORY_BUFF_CAPS}
        armory["buffs"] = {}
        return buffs

    def _armory_roll(self, rng: random.Random, pool: list[dict[str, Any]], weights: dict[str, int], owned: set[str]) -> dict[str, Any] | None:
        """A weighted pick by tier, skipping gear the hunter already owns."""

        available = [item for item in pool if item["slot"] in ARMORY_STACK_SLOTS or item["id"] not in owned]
        candidates = [(item, weights.get(item["tier"], 0)) for item in available if weights.get(item["tier"], 0) > 0]
        if not candidates:
            return None
        return rng.choices([item for item, _ in candidates], weights=[weight for _, weight in candidates])[0]

    def _armory_contract_drop(self, progress: dict[str, Any], project: Mapping[str, Any], mobs: list[Mapping[str, Any]], index: int, mob: Mapping[str, Any], evidence_id: str) -> dict[str, Any] | None:
        """Every cleared contract drops something from its campaign's armory,
        rarer the further into the campaign it is."""

        pool = [item for item in armory_catalog().values() if item["campaign"] == project.get("branch") and item["slot"] not in {"relic"} and item["tier"] != "legendary"]
        if not pool:
            return None
        hunter = self._hunter_state(progress)
        owned = set(hunter["armory"]["owned"])
        depth = index / max(1, len(mobs) - 1)
        luck = self._gear_effects(progress)["loot_luck"]
        weights = {
            "common": max(5, round(45 - 35 * depth)),
            "uncommon": 30,
            "rare": round(12 + 25 * depth + luck / 2),
            "epic": round((18 * depth if depth >= 0.5 else 0) + (luck / 3 if depth >= 0.5 else 0)),
        }
        rng = random.Random(f"{self.device_id()}:{project.get('branch')}:{mob.get('name')}:{evidence_id}")
        item = self._armory_roll(rng, pool, weights, owned)
        if item is None:
            return None
        self._armory_add(hunter, item["id"])
        return {"id": item["id"], "name": item["name"], "slot": item["slot"], "tier": item["tier"], "effect": armory_effect_text(item["effect"])}

    def _armory_boss_loot(self, progress: dict[str, Any], project: Mapping[str, Any]) -> list[dict[str, Any]]:
        """A campaign boss drops its relic and one legendary piece."""

        catalog = armory_catalog()
        hunter = self._hunter_state(progress)
        owned = set(hunter["armory"]["owned"])
        branch = project.get("branch")
        loot = []
        relic = next((item for item in catalog.values() if item["campaign"] == branch and item["slot"] == "relic"), None)
        legendaries = [item for item in catalog.values() if item["campaign"] == branch and item["tier"] == "legendary" and item["slot"] in ARMORY_GEAR_SLOTS and item["id"] not in owned]
        rng = random.Random(f"{self.device_id()}:{branch}:boss")
        for item in ([relic] if relic and relic["id"] not in owned else []) + ([rng.choice(legendaries)] if legendaries else []):
            self._armory_add(hunter, item["id"])
            loot.append({"id": item["id"], "name": item["name"], "slot": item["slot"], "tier": item["tier"], "effect": armory_effect_text(item["effect"])})
        # And a PYR's Blessing for the next campaign.
        blessing = catalog.get("aid-pyrs-blessing")
        if blessing:
            self._armory_add(hunter, blessing["id"])
            loot.append({"id": blessing["id"], "name": blessing["name"], "slot": "aid", "tier": blessing["tier"], "effect": armory_effect_text(blessing["effect"])})
        return loot

    def _dungeon_gear_drop(self, run: Mapping[str, Any], room_type: str, progress: Mapping[str, Any] | None) -> str | None:
        """Floor bosses drop campaign gear (legendaries deep down, once that
        campaign's boss is beaten); elites sometimes drop food."""

        if room_type not in {"boss", "elite"}:
            return None
        if not isinstance(progress, Mapping):
            return None
        projects = [item for item in progress.get("projects", []) if isinstance(item, Mapping)] if isinstance(progress.get("projects"), list) else []
        started = [item for item in projects if item.get("status") == "active" or any(isinstance(mob, Mapping) and mob.get("status") == "defeated" for mob in item.get("mobs", []) or [])]
        if not started:
            return None
        hunter = progress.get("hunter") if isinstance(progress.get("hunter"), Mapping) else {}
        armory = hunter.get("armory") if isinstance(hunter.get("armory"), Mapping) else {}
        owned = set(armory.get("owned", []) if isinstance(armory.get("owned"), list) else [])
        rng = random.Random(f"{run.get('seed')}:{run.get('question_number')}:{room_type}:gear")
        project = rng.choice(started)
        pool = [item for item in armory_catalog().values() if item["campaign"] == project.get("branch") and item["slot"] != "relic"]
        if room_type == "elite":
            if rng.random() >= 0.5:
                return None
            item = self._armory_roll(rng, [item for item in pool if item["slot"] in ARMORY_STACK_SLOTS], {tier: 1 for tier in ARMORY_TIERS}, owned)
        else:
            deep = max(1, int(run.get("floor", 1) or 1)) >= 3 and project.get("completed") is True
            weights = {"rare": 50, "epic": 40, "legendary": 10 if deep else 0}
            item = self._armory_roll(rng, [item for item in pool if item["slot"] in ARMORY_GEAR_SLOTS], weights, owned)
        return item["id"] if item else None

    def armory_projection(self, progress: Mapping[str, Any]) -> dict[str, Any]:
        """The hunter's gear, food, relics, collection and Merchant lots."""

        catalog = armory_catalog()
        hunter = progress.get("hunter") if isinstance(progress.get("hunter"), Mapping) else {}
        armory = hunter.get("armory") if isinstance(hunter.get("armory"), Mapping) else {}
        owned = [item for item in armory.get("owned", []) if isinstance(item, str) and item in catalog] if isinstance(armory.get("owned"), list) else []
        stack = armory.get("stack") if isinstance(armory.get("stack"), Mapping) else {}
        equipment = progress.get("equipment") if isinstance(progress.get("equipment"), Mapping) else {}
        equipped = {"weapon": armory.get("weapon"), "armor": str(equipment.get("armor") or "Apprentice Coat"), "trinket": str(equipment.get("trinket") or "None")}

        def view(item: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
            return {key: item[key] for key in ("id", "name", "slot", "tier", "flavour", "campaign") if key in item} | {"effect": armory_effect_text(item["effect"])} | extra

        items = [view(catalog[item], equipped=(catalog[item]["slot"] == "weapon" and equipped["weapon"] == item) or catalog[item]["name"] in {equipped["armor"], equipped["trinket"]}) for item in owned]
        items += [view(catalog[item], count=int(count)) for item, count in stack.items() if item in catalog and isinstance(count, int) and count > 0]
        projects = {item.get("branch"): item for item in progress.get("projects", []) if isinstance(item, Mapping)} if isinstance(progress.get("projects"), list) else {}
        collection = []
        market = []
        coins = int(((progress.get("player") or {}) if isinstance(progress.get("player"), Mapping) else {}).get("coins", 0) or 0)
        for branch, project in projects.items():
            pool = [item for item in catalog.values() if item["campaign"] == branch]
            if not pool:
                continue
            found = sum(1 for item in pool if item["id"] in owned or int(stack.get(item["id"], 0) or 0) > 0)
            collection.append({"branch": branch, "name": project.get("name"), "found": found, "total": len(pool)})
            mobs = [mob for mob in project.get("mobs", []) or [] if isinstance(mob, Mapping)]
            cleared = sum(1 for mob in mobs if mob.get("status") in {"defeated", "cleared"})
            share = cleared / max(1, len(mobs))
            started = project.get("status") == "active" or cleared > 0 or project.get("completed") is True
            for item in pool:
                if not isinstance(item.get("price"), int):
                    continue
                if item["slot"] in ARMORY_GEAR_SLOTS and item["id"] in owned:
                    continue
                need = "Start this campaign" if not started else ("Clear half of its contracts" if item["tier"] == "rare" and share < 0.5 and project.get("completed") is not True else None)
                market.append(view(item, price=item["price"], locked=need, affordable=need is None and coins >= item["price"]))
        for item in AID_ITEMS:
            market.append(view(catalog[item["id"]], price=item["price"], locked=None, affordable=coins >= item["price"]))
        tier_rank = {tier: index for index, tier in enumerate(ARMORY_TIERS)}
        market.sort(key=lambda item: (item["locked"] is not None, item["campaign"], ARMORY_SLOTS.index(item["slot"]), tier_rank[item["tier"]]))
        effects = self._gear_effects(progress)
        return {
            "items": items,
            "equipped": equipped,
            "weapon": view(catalog[equipped["weapon"]]) if equipped["weapon"] in catalog else None,
            "buffs": {key: value for key, value in (armory.get("buffs") or {}).items() if isinstance(value, int) and value > 0} if isinstance(armory.get("buffs"), Mapping) else {},
            "charges": self.aid_charges(progress),
            "collection": collection,
            "market": market,
            "summary": {key: effects[key] for key in ("reduction", "start_guards", "heal_on_objective", "coin_bonus", "xp_bonus", "loot_luck")},
        }

    def _armory_equip(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Equip an owned weapon, armour or trinket from the armory."""

        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        item = armory_catalog().get(item_id)
        if item is None or item["slot"] not in ARMORY_GEAR_SLOTS:
            raise StateCommandError("That is not gear you can equip", status_code=404)
        hunter = self._hunter_state(progress)
        if item_id not in hunter["armory"]["owned"]:
            raise StateCommandError("You do not own that item yet", status_code=409)
        if item["slot"] == "weapon":
            hunter["armory"]["weapon"] = item_id
        else:
            # Only the name reaches the synced equipment; ownership stays local.
            self._dict(progress, "equipment")[item["slot"]] = item["name"]
        return Mutation(True, {"armory": self.armory_projection(progress)}, {"item_id": item_id, "slot": item["slot"], "reason": "armory_equipped"})

    def _armory_unequip(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"slot"}, {"slot"})
        slot = self._text(data["slot"], "slot", max_length=20, identifier=True)
        if slot not in ARMORY_GEAR_SLOTS:
            raise StateCommandError("Unknown gear slot", status_code=422)
        if slot == "weapon":
            self._hunter_state(progress)["armory"]["weapon"] = None
        else:
            self._dict(progress, "equipment")[slot] = "Apprentice Coat" if slot == "armor" else "None"
        return Mutation(True, {"armory": self.armory_projection(progress)}, {"slot": slot, "reason": "armory_unequipped"})

    def _armory_use(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Eat or drink something: heal now, and buff the next battle."""

        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        item = armory_catalog().get(item_id)
        if item is None or item["slot"] not in ARMORY_STACK_SLOTS:
            raise StateCommandError("That cannot be eaten or drunk", status_code=404)
        hunter = self._hunter_state(progress)
        stack = hunter["armory"]["stack"]
        if self._counter(stack, item_id) <= 0:
            raise StateCommandError("You have none of that left", status_code=409)
        effect = item["effect"]
        if item["slot"] == "aid":
            charges = hunter["armory"].setdefault("charges", {})
            armed = {}
            for key, cap in AID_CHARGE_CAPS.items():
                if effect.get(key):
                    before = self._counter(charges, key)
                    charges[key] = min(cap, before + int(effect[key]))
                    armed[key] = charges[key] - before
            if not any(armed.values()):
                raise StateCommandError("You already carry as much of that help as you can", status_code=409)
            left = self._counter(stack, item_id) - 1
            if left > 0:
                stack[item_id] = left
            else:
                stack.pop(item_id, None)
            records = self._dict(progress, "records")
            records["aid_used"] = self._counter(records, "aid_used") + 1
            return Mutation(True, {"armory": self.armory_projection(progress), "armed": armed, "charges": self.aid_charges(progress)}, {"item_id": item_id, "armed": armed, "reason": "aid_armed"})
        player = self._dict(progress, "player")
        healed = 0
        if effect.get("heal"):
            current = self._counter(player, "hp")
            healed = max(0, min(ARMORY_EFFECT_CAPS["heal"], int(effect["heal"]), self._counter(player, "max_hp") - current))
            player["hp"] = current + healed
        buff = effect.get("next_battle") if isinstance(effect.get("next_battle"), Mapping) else {}
        buffs = hunter["armory"]["buffs"]
        for key, value in buff.items():
            if key in ARMORY_BUFF_CAPS:
                buffs[key] = min(ARMORY_BUFF_CAPS[key], self._counter(buffs, key) + int(value))
        if not healed and not buff:
            raise StateCommandError("You are already at full HP", status_code=409)
        left = self._counter(stack, item_id) - 1
        if left > 0:
            stack[item_id] = left
        else:
            stack.pop(item_id, None)
        return Mutation(True, {"armory": self.armory_projection(progress), "healed": healed, "hp": player.get("hp")}, {"item_id": item_id, "healed": healed, "reason": "armory_used"})

    @staticmethod
    def aid_charges(progress: Mapping[str, Any]) -> dict[str, int]:
        """Armed Aid: free PYR asks and wards waiting to be spent."""

        hunter = progress.get("hunter") if isinstance(progress.get("hunter"), Mapping) else {}
        armory = hunter.get("armory") if isinstance(hunter.get("armory"), Mapping) else {}
        charges = armory.get("charges") if isinstance(armory.get("charges"), Mapping) else {}
        return {key: max(0, int(charges.get(key, 0) or 0)) if isinstance(charges.get(key, 0), int) else 0 for key in AID_CHARGE_CAPS}

    def _spend_aid(self, progress: dict[str, Any], key: str) -> bool:
        """Spend one armed charge if there is one."""

        if self.aid_charges(progress).get(key, 0) <= 0:
            return False
        charges = self._hunter_state(progress)["armory"].setdefault("charges", {})
        charges[key] = self._counter(charges, key) - 1
        return True

    def _aid_drop(self, progress: dict[str, Any], project: Mapping[str, Any], mobs: list[Mapping[str, Any]], index: int, mob: Mapping[str, Any], evidence_id: str) -> dict[str, Any] | None:
        """A cleared bounty sometimes drops one-time help, rarer help deeper in."""

        rng = random.Random(f"aid:{self.device_id()}:{project.get('branch')}:{mob.get('name')}:{evidence_id}")
        if rng.randrange(100) >= AID_DROP_CHANCE:
            return None
        depth = index / max(1, len(mobs) - 1)
        weights = {item["id"]: (40 if item["tier"] == "uncommon" else round(8 + 22 * depth)) for item in AID_ITEMS}
        roll = rng.randrange(sum(weights.values()))
        for item in AID_ITEMS:
            roll -= weights[item["id"]]
            if roll < 0:
                self._armory_add(self._hunter_state(progress), item["id"])
                return {"id": item["id"], "name": item["name"], "slot": "aid", "tier": item["tier"], "effect": armory_effect_text(item["effect"])}
        return None

    def _armory_buy(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        lot = next((item for item in self.armory_projection(progress)["market"] if item["id"] == item_id), None)
        if lot is None:
            raise StateCommandError("The Merchant does not sell that", status_code=404)
        if lot["locked"]:
            raise StateCommandError(lot["locked"] + " to unlock this lot", status_code=409)
        player = self._dict(progress, "player")
        if self._counter(player, "coins") < lot["price"]:
            raise StateCommandError(f"Needs {lot['price']} coins", status_code=409)
        player["coins"] = self._counter(player, "coins") - lot["price"]
        self._armory_add(self._hunter_state(progress), item_id)
        return Mutation(True, {"armory": self.armory_projection(progress), "coins": player["coins"]}, {"item_id": item_id, "coins_spent": lot["price"], "reason": "armory_bought"})

    @classmethod
    def _hunter_kit_levels(cls, progress: Mapping[str, Any]) -> dict[str, int]:
        hunter = progress.get("hunter") if isinstance(progress.get("hunter"), Mapping) else {}
        raw = hunter.get("kit") if isinstance(hunter.get("kit"), Mapping) else {}
        levels = {}
        for track in HUNTER_KIT:
            value = raw.get(track, 0)
            levels[track] = min(HUNTER_KIT_MAX_LEVEL, value) if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0
        return levels

    def _hunter_upgrade_kit(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Spend region essences and coins on one level of a kit track."""

        data = self._payload(payload, {"track"}, {"track"})
        track = self._text(data["track"], "track", max_length=20, identifier=True)
        entry = next((item for item in self.hunter_projection(progress)["kit"] if item["id"] == track), None)
        if entry is None:
            raise StateCommandError("Unknown kit piece", status_code=404)
        cost = entry["next"]
        if cost is None:
            raise StateCommandError(f"{entry['name']} is already at its best", status_code=409)
        if not cost["affordable"]:
            raise StateCommandError(f"Needs {cost['count']} {cost['essence_name']} and {cost['coins']} coins", status_code=409)
        hunter = self._hunter_state(progress)
        left = self._counter(hunter["materials"], cost["essence"]) - cost["count"]
        if left > 0:
            hunter["materials"][cost["essence"]] = left
        else:
            hunter["materials"].pop(cost["essence"], None)
        player = self._dict(progress, "player")
        player["coins"] = self._counter(player, "coins") - cost["coins"]
        hunter["kit"][track] = entry["level"] + 1
        return Mutation(
            True,
            {"hunter": self.hunter_projection(progress), "track": track, "level": entry["level"] + 1, "coins": player["coins"]},
            {"track": track, "level": entry["level"] + 1, "coins_spent": cost["coins"], "reason": "hunter_kit_upgraded"},
        )

    def _hunter_new_identify(self, hunter: dict[str, Any], progress: Mapping[str, Any]) -> dict[str, Any]:
        """Deal a snippet for the next vial: weak signs come up more often."""

        attempt = self._counter(hunter, "identify_count") + 1
        hunter["identify_count"] = attempt
        seed = f"{self.device_id()}:{attempt}"
        levels = {sign["id"]: sign["level"] for sign in self.hunter_projection(progress)["signs"]}
        rng = random.Random(seed)
        signs = list(HUNTER_BEASTS)
        sign_id = rng.choices(signs, weights=[(11 - levels.get(sign, 0)) ** 2 for sign in signs])[0]
        tier = rng.choices([name for name, _ in HUNTER_IDENTIFY_TIER_WEIGHTS], weights=[weight for _, weight in HUNTER_IDENTIFY_TIER_WEIGHTS])[0]
        snippet = _identify_snippet(sign_id, seed)
        puzzle = {"id": f"vial-{attempt}", "sign": sign_id, "tier": tier, **snippet}
        hunter["identify"] = puzzle
        return puzzle

    def _hunter_identify_start(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Hold an unmarked vial to the light: deal its reading puzzle."""

        self._payload(payload, set(), set())
        hunter = self._hunter_state(progress)
        if self._counter(hunter["materials"], DUNGEON_VIAL) <= 0:
            raise StateCommandError("No unmarked vials banked; elites and bosses drop them", status_code=409)
        if isinstance(hunter.get("identify"), Mapping):
            return Mutation(False, {"hunter": self.hunter_projection(progress)})
        self._hunter_new_identify(hunter, progress)
        return Mutation(True, {"hunter": self.hunter_projection(progress)}, {"reason": "hunter_identify_started"})

    def _hunter_identify_answer(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Check a reading. Right: the vial becomes an oil for that sign.
        Wrong: nothing is lost; the answer is explained and a new snippet dealt."""

        data = self._payload(payload, {"puzzle_id", "choice"}, {"puzzle_id", "choice"})
        puzzle_id = self._text(data["puzzle_id"], "puzzle_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        choice = self._integer(data["choice"], "choice", minimum=0, maximum=3)
        hunter = self._hunter_state(progress)
        puzzle = hunter.get("identify")
        if not isinstance(puzzle, Mapping) or puzzle.get("id") != puzzle_id:
            raise StateCommandError("That vial reading changed; reload the bench", status_code=409)
        reveal = {"answer": puzzle["answer_text"], "why": puzzle["why"], "prompt": puzzle["prompt"]}
        if choice != puzzle["answer"]:
            hunter["identify_misses"] = self._counter(hunter, "identify_misses") + 1
            self._hunter_new_identify(hunter, progress)
            return Mutation(
                True,
                {"hunter": self.hunter_projection(progress), "correct": False, **reveal},
                {"correct": False, "sign": puzzle["sign"], "reason": "hunter_identify_missed"},
            )
        clean = not self._counter(hunter, "identify_misses")
        hunter["identify_misses"] = 0
        left = self._counter(hunter["materials"], DUNGEON_VIAL) - 1
        if left > 0:
            hunter["materials"][DUNGEON_VIAL] = left
        else:
            hunter["materials"].pop(DUNGEON_VIAL, None)
        oil_id = f"{puzzle['sign']}-{puzzle['tier']}"
        hunter["oils"][oil_id] = self._counter(hunter["oils"], oil_id) + 1
        hunter.pop("identify", None)
        gain = self._hunter_record(progress, concept=HUNTER_SIGN_CONCEPTS[puzzle["sign"]], question_type="code_trace", source="identify", clean=clean)
        tier = HUNTER_OIL_TIERS_BY_ID[puzzle["tier"]]
        oil = {"id": oil_id, "name": f"{HUNTER_BEASTS[puzzle['sign']]['beast'].removeprefix('The ')} {tier['name']}", "effect": tier["effect"]}
        return Mutation(
            True,
            {"hunter": self.hunter_projection(progress), "correct": True, "oil": oil, "hunter_gain": gain, **reveal},
            {"correct": True, "oil_id": oil_id, "reason": "hunter_vial_identified"},
        )

    def _hunter_craft_oil(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Craft one beast oil at the Merchant from banked parts and coins."""

        data = self._payload(payload, {"oil_id"}, {"oil_id"})
        oil_id = self._text(data["oil_id"], "oil_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        recipe = next((item for item in self.hunter_projection(progress)["oil_recipes"] if item["id"] == oil_id), None)
        if recipe is None:
            raise StateCommandError("Unknown oil recipe", status_code=404)
        if not recipe["unlocked"]:
            raise StateCommandError(f"This oil needs its sign at rank {recipe['rank_needed']}", status_code=409)
        if not recipe["affordable"]:
            raise StateCommandError("Not enough banked materials or coins for this oil", status_code=409)
        hunter = self._hunter_state(progress)
        for item in recipe["materials"]:
            left = self._counter(hunter["materials"], item["id"]) - item["count"]
            if left > 0:
                hunter["materials"][item["id"]] = left
            else:
                hunter["materials"].pop(item["id"], None)
        player = self._dict(progress, "player")
        player["coins"] = self._counter(player, "coins") - recipe["coins"]
        hunter["oils"][oil_id] = self._counter(hunter["oils"], oil_id) + 1
        return Mutation(
            True,
            {"hunter": self.hunter_projection(progress), "oil_id": oil_id, "coins": player["coins"]},
            {"oil_id": oil_id, "coins_spent": recipe["coins"], "reason": "hunter_oil_crafted"},
        )

    def _hunter_spend_point(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Spend one free stat point (one is earned per hunter level)."""

        data = self._payload(payload, {"stat"}, {"stat"})
        stat = self._text(data["stat"], "stat", max_length=20, identifier=True)
        if stat not in HUNTER_STATS:
            raise StateCommandError("That stat does not exist")
        if self.hunter_projection(progress)["free_points"] <= 0:
            raise StateCommandError("No free stat points yet; one comes with every hunter level", status_code=409)
        hunter = self._hunter_state(progress)
        hunter["spent"][stat] = self._counter(hunter["spent"], stat) + 1
        return Mutation(True, {"hunter": self.hunter_projection(progress)}, {"stat": stat, "reason": "hunter_stat_point"})

    def _set_avatar(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Change the player's paper-doll appearance (cosmetic only)."""

        data = self._payload(payload, set(AVATAR_OPTIONS), set())
        equipment = self._dict(progress, "equipment")
        current = equipment.get("avatar") if isinstance(equipment.get("avatar"), Mapping) else {}
        try:
            current = self._avatar_value(current, "equipment.avatar")
        except StateCommandError:
            current = dict(DEFAULT_AVATAR)
        avatar = self._avatar_value({**current, **data}, "avatar")
        changed = avatar != equipment.get("avatar")
        equipment["avatar"] = avatar
        return Mutation(changed, {"avatar": avatar})

    def _equip_equipment(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Equip an already-owned campaign armor or trinket item."""

        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        item = EQUIPMENT_BY_ID.get(item_id)
        if item is None:
            raise StateCommandError("Unknown campaign equipment", status_code=404)
        equipment = self._dict(progress, "equipment")
        slot = "armor" if item["kind"] == "armor" else "trinket"
        owned_field = "owned_armor" if slot == "armor" else "owned_trinkets"
        raw_owned = equipment.get(owned_field)
        if raw_owned is not None and not isinstance(raw_owned, list):
            raise StateCommandError(f"Existing state field equipment.{owned_field} is invalid", status_code=500)
        owned = [
            value for value in (raw_owned or [])
            if isinstance(value, str) and value in EQUIPMENT_BY_ID and EQUIPMENT_BY_ID[value]["kind"] == item["kind"]
        ]
        current_name = str(equipment.get(slot) or ("Apprentice Coat" if slot == "armor" else "None"))
        current_id = EQUIPMENT_ID_BY_NAME.get(current_name)
        if current_id and current_id not in owned:
            owned.append(current_id)
        if item_id not in owned:
            raise StateCommandError("Unlock this campaign item before equipping it", status_code=409)
        if equipment.get(slot) == item["name"]:
            return Mutation(False, {"item": item, "equipment": self.equipment_projection(progress)})
        equipment[slot] = item["name"]
        if raw_owned is not None:
            equipment[owned_field] = owned[:MAX_EQUIPMENT_ITEMS]
        return Mutation(
            True,
            {"item": item, "equipment": self.equipment_projection(progress)},
            {
                "item_id": item_id,
                "item_name": item["name"],
                "slot": slot,
                "reason": "campaign_equipment_equipped",
            },
        )

    def _record_equipment_unlock(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Record a validated equipment unlock from trusted game code."""

        data = self._payload(payload, {"item_id", "evidence_id", "reason"}, {"item_id", "evidence_id", "reason"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        item = EQUIPMENT_BY_ID.get(item_id)
        if item is None:
            raise StateCommandError("Unknown campaign equipment")
        equipment = self._dict(progress, "equipment")
        owned_field = "owned_armor" if item["kind"] == "armor" else "owned_trinkets"
        raw_owned = equipment.get(owned_field)
        if raw_owned is None:
            raw_owned = []
            equipment[owned_field] = raw_owned
        if not isinstance(raw_owned, list):
            raise StateCommandError(f"Existing state field equipment.{owned_field} is invalid", status_code=500)
        owned = [
            value for value in raw_owned
            if isinstance(value, str) and value in EQUIPMENT_BY_ID and EQUIPMENT_BY_ID[value]["kind"] == item["kind"]
        ]
        if item_id in owned:
            return Mutation(False, {"item": item, "equipment": self.equipment_projection(progress)})
        if len(owned) >= MAX_EQUIPMENT_ITEMS:
            raise StateCommandError("Campaign equipment inventory is full", status_code=409)
        owned.append(item_id)
        equipment[owned_field] = owned
        return Mutation(
            True,
            {"item": item, "equipment": self.equipment_projection(progress)},
            {
                "item_id": item_id,
                "item_name": item["name"],
                "slot": item["kind"],
                "evidence_id": evidence_id,
                "reason": reason,
            },
        )

    def _campaign_market_purchase(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Buy one displayed Campaign Market lot into the real Home state."""

        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        item = CAMPAIGN_MARKET_BY_ID.get(item_id)
        if item is None:
            raise StateCommandError("Unknown Campaign Market lot", status_code=404)
        homestead = progress.get("homestead")
        if not isinstance(homestead, dict):
            raise StateCommandError("Homestead state is not initialized", status_code=409)
        purchases = homestead.get("market_purchases")
        if purchases is None:
            purchases = []
            homestead["market_purchases"] = purchases
        if not isinstance(purchases, list) or any(not isinstance(value, str) for value in purchases):
            raise StateCommandError("Existing homestead market purchases are invalid", status_code=500)
        if item_id in purchases:
            return Mutation(
                False,
                {"already_owned": True, "item": item, "coins": self._counter(self._dict(progress, "player"), "coins")},
            )

        player = self._dict(progress, "player")
        coins = self._counter(player, "coins")
        price = self._counter(item, "price")
        if coins < price:
            raise StateCommandError(
                f"Not enough coins. {item['name']} costs {price}c and you have {coins}c.",
                status_code=409,
            )

        kind = str(item.get("kind") or "")
        supplies = None
        equipment = None
        if kind in {"armor", "trinket"}:
            equipment = self._dict(progress, "equipment")
            owned_field = "owned_armor" if kind == "armor" else "owned_trinkets"
            owned = equipment.get(owned_field)
            if owned is None:
                owned = []
                equipment[owned_field] = owned
            if not isinstance(owned, list):
                raise StateCommandError(f"Existing state field equipment.{owned_field} is invalid", status_code=500)
            if len(owned) >= MAX_EQUIPMENT_ITEMS:
                raise StateCommandError("Campaign equipment inventory is full", status_code=409)
            owned.append(item_id)
        elif kind == "supply":
            supply = item.get("supply")
            if not isinstance(supply, str) or supply not in {"bandages", "tonics", "meals", "vision_scrolls"}:
                raise StateCommandError("Unknown Campaign Market supply", status_code=500)
            supplies = self._homestead_supplies(progress)
            supplies[supply] = min(MAX_SYNC_COUNTER, self._counter(supplies, supply) + 1)
        else:
            raise StateCommandError("Campaign Market lot has an invalid kind", status_code=500)

        player["coins"] = coins - price
        purchases.append(item_id)
        history = homestead.get("purchase_history")
        if not isinstance(history, list):
            raise StateCommandError("Existing state field purchase_history is invalid", status_code=500)
        history.append(
            {
                "item_id": item_id,
                "name": item["name"],
                "price": price,
                "source": "campaign_market",
                "purchased_at": _utc_now(),
            }
        )
        result: dict[str, Any] = {
            "item": item,
            "coins": player["coins"],
            "market_purchases": purchases,
        }
        if equipment is not None:
            result["equipment"] = self.equipment_projection(progress)
        if supplies is not None:
            result["supplies"] = supplies
        return Mutation(
            True,
            result,
            {
                "item_id": item_id,
                "item_name": item["name"],
                "coins_delta": -price,
                "reason": "campaign_market_purchase",
            },
        )

    def _homestead_purchase(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        homestead = progress.get("homestead")
        if not isinstance(homestead, dict):
            raise StateCommandError("Homestead state is not initialized", status_code=409)
        item = self._catalog(progress).get(item_id)
        if not item:
            raise StateCommandError("Unknown Homestead item", status_code=404)
        owned = homestead.get("owned_cosmetics")
        if not isinstance(owned, list):
            raise StateCommandError("Existing state field owned_cosmetics is invalid", status_code=500)
        player = self._dict(progress, "player")
        coins = self._counter(player, "coins")
        if item_id in owned:
            return Mutation(False, {"already_owned": True, "item": item, "coins": coins})
        try:
            price = max(0, int(item.get("price", 0) or 0))
        except (TypeError, ValueError) as exc:
            raise StateCommandError("Invalid Homestead item price", status_code=500) from exc
        if coins < price:
            raise StateCommandError(
                f"Not enough coins. {item.get('name', item_id)} costs {price}c and you have {coins}c.",
                status_code=409,
            )
        purchase_history = homestead.get("purchase_history")
        if not isinstance(purchase_history, list):
            raise StateCommandError("Existing state field purchase_history is invalid", status_code=500)
        player["coins"] = coins - price
        owned.append(item_id)
        purchase_history.append(
            {
                "item_id": item_id,
                "name": item.get("name", item_id),
                "price": price,
                "purchased_at": _utc_now(),
            }
        )
        return Mutation(
            True,
            {"item": item, "coins": player["coins"], "owned_cosmetics": owned},
            {"item_id": item_id, "item_name": str(item.get("name", item_id)), "coins_delta": -price, "reason": "homestead_purchase"},
        )

    def _homestead_equip(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"item_id"}, {"item_id"})
        item_id = self._text(data["item_id"], "item_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        homestead = progress.get("homestead")
        if not isinstance(homestead, dict):
            raise StateCommandError("Homestead state is not initialized", status_code=409)
        item = self._catalog(progress).get(item_id)
        if not item:
            raise StateCommandError("Unknown Homestead item", status_code=404)
        owned = homestead.get("owned_cosmetics")
        if not isinstance(owned, list) or item_id not in owned:
            raise StateCommandError("Buy or unlock this cosmetic before equipping it", status_code=409)
        kind = str(item.get("kind", ""))
        if kind not in {"theme", "cursor", "hud", "terminal"}:
            raise StateCommandError("This Homestead item cannot be equipped", status_code=409)
        equipped = homestead.get("equipped")
        if not isinstance(equipped, dict):
            raise StateCommandError("Existing state field equipped is invalid", status_code=500)
        if equipped.get(kind) == item_id:
            return Mutation(False, {"item": item, "equipped": equipped})
        equipped[kind] = item_id
        return Mutation(
            True,
            {"item": item, "equipped": equipped},
            {"item_id": item_id, "kind": kind, "reason": "homestead_equip"},
        )

    @staticmethod
    def home_room_projection(progress: Mapping[str, Any]) -> dict[str, Any]:
        try:
            levels = effective_room_levels(progress)
        except ValueError as exc:
            raise StateCommandError(str(exc), status_code=500) from exc
        return {"levels": levels, "ladders": HOME_ROOM_LADDERS, "labels": HOME_ROOM_LABELS}

    def _home_room_purchase(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"room_id", "expected_level"}, {"room_id", "expected_level"})
        room = self._text(data["room_id"], "room_id", max_length=40, identifier=True)
        if room not in HOME_ROOM_LADDERS:
            raise StateCommandError("Unknown Home room", status_code=404)
        expected = self._integer(data["expected_level"], "expected_level", minimum=0, maximum=len(HOME_ROOM_LADDERS[room]))
        home = progress.get("homestead")
        if not isinstance(home, dict):
            raise StateCommandError("Homestead state is not initialized", status_code=409)
        try:
            levels = effective_room_levels(progress)
        except ValueError as exc:
            raise StateCommandError(str(exc), status_code=500) from exc
        level = levels[room]
        if expected != level:
            raise StateCommandError("Room level changed; refresh before buying", status_code=409)
        if level >= len(HOME_ROOM_LADDERS[room]):
            raise StateCommandError("This room is already fully upgraded", status_code=409)
        tokens = home.get("upgrade_tokens", 0)
        if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
            raise StateCommandError("Existing upgrade_tokens is invalid", status_code=500)
        step = HOME_ROOM_LADDERS[room][level]
        if tokens < step["cost"]:
            raise StateCommandError(f"{step['name']} needs {step['cost']} Embers", status_code=409)
        levels[room] = level + 1
        home["room_levels"] = levels
        home["upgrade_tokens"] = tokens - step["cost"]
        return Mutation(True, {"room_id": room, "level": levels[room], "levels": levels, "step": step, "upgrade_tokens": home["upgrade_tokens"]},
                        {"room_id": room, "level": levels[room], "tokens_delta": -step["cost"], "reason": "home_room_purchase"})

    def _homestead_room_upgrade(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Build one authored Home room upgrade through the state gateway."""

        data = self._payload(payload, {"upgrade_id"}, {"upgrade_id"})
        upgrade_id = self._text(data["upgrade_id"], "upgrade_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        upgrade = HOME_ROOM_UPGRADE_BY_ID.get(upgrade_id)
        if not upgrade:
            raise StateCommandError("Unknown Homestead room upgrade", status_code=404)
        homestead = progress.get("homestead")
        if not isinstance(homestead, dict):
            raise StateCommandError("Homestead state is not initialized", status_code=409)
        owned = homestead.get("room_upgrades")
        if owned is None:
            owned = []
            homestead["room_upgrades"] = owned
        if not isinstance(owned, list):
            raise StateCommandError("Existing room_upgrades is invalid", status_code=500)
        if upgrade_id in owned:
            return Mutation(False, {"already_built": True, "upgrade": upgrade, "room_upgrades": owned, "upgrade_tokens": self._counter(homestead, "upgrade_tokens")})

        # Existing saves predate the Home room layer. The prototype starts with
        # one authored token, so migrate the missing field lazily on first use.
        tokens = homestead.get("upgrade_tokens", 1)
        if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
            raise StateCommandError("Existing upgrade_tokens is invalid", status_code=500)
        cost = self._integer(upgrade.get("cost", 0), "upgrade.cost", minimum=1, maximum=10)
        if tokens < cost:
            raise StateCommandError(f"{upgrade['name']} needs {cost} upgrade token{'s' if cost != 1 else ''}.", status_code=409)

        effects = homestead.get("upgrade_effects")
        if effects is None:
            effects = {}
            homestead["upgrade_effects"] = effects
        if not isinstance(effects, dict):
            raise StateCommandError("Existing upgrade_effects is invalid", status_code=500)
        player = self._dict(progress, "player")
        max_hp_delta = self._integer(upgrade.get("max_hp_delta", 0), "upgrade.max_hp_delta", minimum=0, maximum=MAX_HP_DELTA)
        if max_hp_delta:
            player["max_hp"] = self._counter(player, "max_hp") + max_hp_delta
            player["hp"] = min(self._counter(player, "max_hp"), self._counter(player, "hp") + max_hp_delta)
        effect_fields = ("failure_damage_reduction", "resolve_impact_delta", "guard_break_heal", "meal_heal_delta")
        for field in effect_fields:
            value = self._integer(upgrade.get(field, 0), f"upgrade.{field}", minimum=0, maximum=MAX_HP_DELTA)
            if value:
                effects[field] = self._counter(effects, field) + value
        owned.append(upgrade_id)
        homestead["upgrade_tokens"] = tokens - cost
        return Mutation(
            True,
            {
                "upgrade": upgrade,
                "room_upgrades": owned,
                "upgrade_tokens": homestead["upgrade_tokens"],
                "upgrade_effects": effects,
                "player": {"hp": player.get("hp"), "max_hp": player.get("max_hp")},
            },
            {
                "upgrade_id": upgrade_id,
                "upgrade_name": str(upgrade.get("name", upgrade_id)),
                "tokens_delta": -cost,
                "reason": "homestead_room_upgrade",
            },
        )

    @staticmethod
    def _homestead_pyr_stage(bond: int) -> dict[str, str | int]:
        """Return the authored Pyr stage used by the Home prototype."""

        stages = (
            {"id": "spark", "label": "Tiny Code-Flame", "threshold": 0, "next": "Emberling"},
            {"id": "ember", "label": "Emberling", "threshold": 3, "next": "Flarekin"},
            {"id": "flare", "label": "Flarekin", "threshold": 6, "next": "Runic Familiar"},
        )
        return next((stage for stage in reversed(stages) if bond >= int(stage["threshold"])), stages[0])

    def _homestead_supplies(self, progress: dict[str, Any]) -> dict[str, Any]:
        """Load the Home supply pouch, migrating legacy potion counts once."""

        supplies = progress.get("supplies")
        if supplies is None:
            player = self._dict(progress, "player")
            supplies = {
                "bandages": self._counter(player, "potions"),
                "tonics": 0,
                "meals": 0,
                "vision_scrolls": 0,
            }
            progress["supplies"] = supplies
        if not isinstance(supplies, dict):
            raise StateCommandError("Existing state field supplies is invalid", status_code=500)
        for field in ("bandages", "tonics", "meals", "vision_scrolls"):
            if field not in supplies:
                supplies[field] = 0
            self._counter(supplies, field)
        return supplies

    def _homestead_action(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Apply one bounded Home interaction from the prototype contract."""

        data = self._payload(payload, {"action"}, {"action"})
        action = self._text(data["action"], "action", max_length=32, identifier=True)
        if action not in {"recover", "bandage", "meal", "feed_pyr", "train_pyr", "spend_token"}:
            raise StateCommandError("Unsupported Home action", status_code=422)
        player = self._dict(progress, "player")
        homestead = progress.get("homestead")
        if not isinstance(homestead, dict):
            raise StateCommandError("Homestead state is not initialized", status_code=409)
        supplies = self._homestead_supplies(progress)
        hp = self._counter(player, "hp")
        max_hp = max(1, self._counter(player, "max_hp"))
        effects = homestead.get("upgrade_effects")
        if effects is None:
            effects = {}
            homestead["upgrade_effects"] = effects
        if not isinstance(effects, dict):
            raise StateCommandError("Existing upgrade_effects is invalid", status_code=500)

        if action == "recover":
            if hp >= max_hp:
                return Mutation(False, {"action": action, "already_full": True, "hp": hp, "max_hp": max_hp})
            missing = max_hp - hp
            cost = (missing + 9) // 10
            coins = self._counter(player, "coins")
            if coins >= cost:
                player["coins"] = coins - cost
                target = max_hp
                paid = cost
            else:
                target = max(1, (max_hp * 30 + 99) // 100)
                paid = 0
                if hp >= target:
                    raise StateCommandError(f"Full rest costs {cost} coins; free emergency rest is only available below {target} HP", status_code=409)
            player["hp"] = target
            healed = target - hp
            return Mutation(True, {"action": action, "healed": healed, "hp": target, "max_hp": max_hp, "coins_spent": paid, "emergency": paid == 0}, {"home_action": action, "healed": healed, "coins_spent": paid, "emergency": paid == 0, "reason": "homestead_recover"})

        if action == "bandage":
            count = self._counter(supplies, "bandages")
            if count <= 0:
                raise StateCommandError("No bandages are packed", status_code=409)
            if hp >= max_hp:
                raise StateCommandError("Your HP is already full", status_code=409)
            healed = min(max_hp, hp + 20) - hp
            supplies["bandages"] = count - 1
            player["potions"] = supplies["bandages"]
            player["hp"] = hp + healed
            return Mutation(True, {"action": action, "healed": healed, "hp": player["hp"], "max_hp": max_hp, "supplies": supplies}, {"home_action": action, "healed": healed, "reason": "homestead_bandage"})

        if action == "meal":
            count = self._counter(supplies, "meals")
            if count <= 0:
                raise StateCommandError("No meals are packed", status_code=409)
            if hp >= max_hp:
                raise StateCommandError("Your HP is already full", status_code=409)
            bonus = self._counter(effects, "meal_heal_delta")
            healed = min(max_hp, hp + 10 + bonus) - hp
            supplies["meals"] = count - 1
            player["hp"] = hp + healed
            return Mutation(True, {"action": action, "healed": healed, "hp": player["hp"], "max_hp": max_hp, "supplies": supplies}, {"home_action": action, "healed": healed, "reason": "homestead_meal"})

        if action == "spend_token":
            tokens = homestead.get("upgrade_tokens", 1)
            if not isinstance(tokens, int) or isinstance(tokens, bool) or tokens < 0:
                raise StateCommandError("Existing upgrade_tokens is invalid", status_code=500)
            if tokens < 1:
                raise StateCommandError("No upgrade tokens available", status_code=409)
            player["max_hp"] = max_hp + 5
            player["hp"] = min(player["max_hp"], hp + 5)
            homestead["upgrade_tokens"] = tokens - 1
            return Mutation(True, {"action": action, "upgrade_tokens": homestead["upgrade_tokens"], "player": {"hp": player["hp"], "max_hp": player["max_hp"]}}, {"home_action": action, "tokens_delta": -1, "reason": "homestead_legacy_token"})

        companion = self._dict(progress, "companion")
        bond = self._counter(companion, "bond")
        max_energy = companion.get("max_energy", 2)
        if not isinstance(max_energy, int) or isinstance(max_energy, bool) or max_energy < 1:
            max_energy = 2
        energy = companion.get("energy", max_energy)
        if not isinstance(energy, int) or isinstance(energy, bool) or energy < 0:
            energy = max_energy
        energy = min(max_energy, energy)
        if action == "feed_pyr":
            meals = self._counter(supplies, "meals")
            if meals <= 0:
                raise StateCommandError("Pyr needs a packed meal first", status_code=409)
            supplies["meals"] = meals - 1
            companion["fed_count"] = self._counter(companion, "fed_count") + 1
            companion["bond"] = bond + 1
            companion["energy"] = min(max_energy, energy + 1)
        else:
            if energy <= 0:
                raise StateCommandError("Pyr needs a little rest before training", status_code=409)
            companion["training_count"] = self._counter(companion, "training_count") + 1
            companion["bond"] = bond + 1
            companion["energy"] = energy - 1
        companion["max_energy"] = max_energy
        stage = self._homestead_pyr_stage(self._counter(companion, "bond"))
        previous_form = str(companion.get("form") or "Tiny Code-Flame")
        companion["form"] = str(stage["label"])
        companion["next_form"] = str(stage["next"])
        companion["next_form_requirement"] = f"Reach bond {int(stage['threshold']) + 3}" if int(stage["threshold"]) < 6 else "Earn 3 Mastery Shields"
        return Mutation(
            True,
            {"action": action, "companion": companion, "supplies": supplies, "stage_changed": previous_form != companion["form"]},
            {"home_action": action, "pyr_form_before": previous_form, "pyr_form_after": companion["form"], "pyr_bond": companion["bond"], "reason": f"homestead_{action}"},
        )

    def _record_learning_event(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"kind", "evidence_id", "reason"}, {"kind", "evidence_id", "reason"})
        kind = self._text(data["kind"], "kind", max_length=40, identifier=True)
        if kind not in {"teachback", "practice", "forge", "review", "interview", "mob", "bugfix", "session"}:
            raise StateCommandError("kind is not a supported learning event")
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        learning_state = self._dict(progress, "learning_state")
        learning_state["last_event_kind"] = kind
        learning_state["last_evidence_id"] = evidence_id
        return Mutation(True, {"kind": kind, "evidence_id": evidence_id}, {"kind": kind, "evidence_id": evidence_id, "reason": reason})

    def _record_reference_mode(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(
            payload,
            {"milestone_id", "evidence_id", "reason", "xp_forfeited"},
            {"milestone_id", "evidence_id", "reason"},
        )
        milestone_id = self._text(data["milestone_id"], "milestone_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        xp_forfeited = self._integer(data.get("xp_forfeited", 0), "xp_forfeited", minimum=0, maximum=1000)
        assist = self._dict(progress, "assist")
        stats = self._dict(progress, "stats")
        learning_state = self._dict(progress, "learning_state")
        assist["mode"] = "reference"
        assist["reference_mode_uses"] = self._counter(assist, "reference_mode_uses") + 1
        assist["guided_milestones"] = self._counter(assist, "guided_milestones") + 1
        assist["xp_forfeited"] = self._counter(assist, "xp_forfeited") + xp_forfeited
        stats["reference_mode_uses"] = self._counter(stats, "reference_mode_uses") + 1
        stats["guided_milestones"] = self._counter(stats, "guided_milestones") + 1
        learning_state["reference_mode"] = True
        return Mutation(
            True,
            {"milestone_id": milestone_id, "reference_mode_uses": assist["reference_mode_uses"]},
            {"milestone_id": milestone_id, "evidence_id": evidence_id, "xp_forfeited": xp_forfeited, "reason": reason},
        )

    @staticmethod
    def _log_activity(progress: dict[str, Any], kind: str, amount: int = 1) -> None:
        """Count today's work for the activity graph (local day, local only)."""

        if kind not in ACTIVITY_KINDS or amount <= 0:
            return
        log = progress.get("activity_log")
        if not isinstance(log, dict) or not isinstance(log.get("days"), dict):
            log = {"days": {}}
            progress["activity_log"] = log
        days = log["days"]
        today = time.strftime("%Y-%m-%d")
        day = days.get(today) if isinstance(days.get(today), dict) else {}
        day[kind] = int(day.get(kind, 0) or 0) + int(amount)
        days[today] = day
        if len(days) > ACTIVITY_LOG_DAYS:
            for stale in sorted(days)[: len(days) - ACTIVITY_LOG_DAYS]:
                days.pop(stale, None)

    @staticmethod
    def _bump_record(progress: dict[str, Any], key: str, amount: int = 1, *, best: bool = False) -> None:
        """Lifetime records for the Settings stats (local only)."""

        records = progress.get("records")
        if not isinstance(records, dict):
            records = {}
            progress["records"] = records
        current = records.get(key, 0)
        current = current if isinstance(current, int) and not isinstance(current, bool) else 0
        records[key] = max(current, amount) if best else current + amount

    def _record_code_activity(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Lines of code the learner added in a save, for the activity graph."""

        data = self._payload(payload, {"lines"}, {"lines"})
        lines = self._integer(data["lines"], "lines", minimum=1, maximum=MAX_CODE_LINES_PER_SAVE)
        self._log_activity(progress, "lines", lines)
        self._bump_record(progress, "lines_written", lines)
        return Mutation(True, {"lines": lines}, {"lines": lines, "reason": "code_saved"})

    @staticmethod
    def pyr_reward_scale(assists: object) -> int:
        """The share (in %) of a fight's XP and coins left after PYR asks."""

        count = assists if isinstance(assists, int) and assists > 0 else 0
        return max(PYR_ASSIST_REWARD_FLOOR, 100 - PYR_ASSIST_REWARD_STEP * count)

    def _record_pyr_assist(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """PYR helped during the current campaign fight: it now pays less."""

        data = self._payload(payload, {"reason"}, set())
        reason = self._text(data.get("reason") or "Asked PYR for help", "reason")
        project, _mobs, index, mob = self._active_project_and_mob(progress)
        encounter = self._ensure_encounter_state(progress, project, mob, index)
        records = self._dict(progress, "records")
        records["pyr_asks"] = self._counter(records, "pyr_asks") + 1
        if self._spend_aid(progress, "free_asks"):
            # PYR's Favour: this ask is on the house.
            scale = self.pyr_reward_scale(self._counter(encounter, "pyr_assists"))
            result = {"mob_name": str(mob.get("name") or ""), "pyr_assists": self._counter(encounter, "pyr_assists"), "reward_scale": scale,
                      "loot_lost": self._counter(encounter, "pyr_assists") >= PYR_ASSIST_LOOT_LIMIT, "free": True, "free_asks_left": self.aid_charges(progress)["free_asks"]}
            return Mutation(True, result, {**result, "reason": reason})
        encounter["pyr_assists"] = self._counter(encounter, "pyr_assists") + 1
        mob["assist"] = "assisted"
        assist = self._dict(progress, "assist")
        assist["pyr_asks"] = self._counter(assist, "pyr_asks") + 1
        scale = self.pyr_reward_scale(encounter["pyr_assists"])
        result = {
            "mob_name": str(mob.get("name") or ""),
            "pyr_assists": encounter["pyr_assists"],
            "reward_scale": scale,
            "loot_lost": encounter["pyr_assists"] >= PYR_ASSIST_LOOT_LIMIT,
            "free": False,
        }
        return Mutation(True, result, {**result, "reason": reason})

    def _award_learning_reward(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"xp", "coins", "reason", "evidence_id"}, {"xp", "coins", "reason", "evidence_id"})
        xp = self._integer(data["xp"], "xp", minimum=0, maximum=MAX_REWARD_XP)
        coins = self._integer(data["coins"], "coins", minimum=0, maximum=MAX_REWARD_COINS)
        if xp == 0 and coins == 0:
            raise StateCommandError("A learning reward must contain XP or coins")
        reason = self._text(data["reason"], "reason")
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        player = self._dict(progress, "player")
        reward = self._grant_reward(player, xp, coins)
        return Mutation(
            True,
            reward,
            {
                "xp": xp,
                "coins": coins,
                "reward_xp": xp,
                "reward_coins": coins,
                "level_before": reward["level_before"],
                "level_after": reward["level_after"],
                "reason": reason,
                "evidence_id": evidence_id,
            },
        )

    @classmethod
    def _grant_reward(cls, player: dict[str, Any], xp: int, coins: int) -> dict[str, int]:
        level_before = max(1, cls._counter(player, "level"))
        current_xp = cls._counter(player, "xp")
        raw_next = player.get("xp_next", 100)
        try:
            xp_next = max(1, int(raw_next))
        except (TypeError, ValueError) as exc:
            raise StateCommandError("Existing state field xp_next is invalid", status_code=500) from exc
        updated_xp = current_xp + xp
        level_after = level_before
        while updated_xp >= xp_next:
            updated_xp -= xp_next
            level_after += 1
        player["level"] = level_after
        player["xp"] = updated_xp
        player["xp_next"] = xp_next
        player["lifetime_xp"] = cls._counter(player, "lifetime_xp") + xp
        player["coins"] = cls._counter(player, "coins") + coins
        return {
            "xp": player["xp"],
            "coins": player["coins"],
            "level": player["level"],
            "lifetime_xp": player["lifetime_xp"],
            "level_before": level_before,
            "level_after": level_after,
        }

    @staticmethod
    def _active_project_and_mob(progress: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]], int, dict[str, Any]]:
        projects = progress.get("projects")
        if not isinstance(projects, list):
            raise StateCommandError("Existing state field projects is invalid", status_code=500)
        project = next((item for item in projects if isinstance(item, dict) and item.get("status") == "active"), None)
        if project is None:
            raise StateCommandError("No active project is available", status_code=409)
        mobs = project.get("mobs")
        if not isinstance(mobs, list) or not all(isinstance(item, dict) for item in mobs):
            raise StateCommandError("Existing active project mobs are invalid", status_code=500)
        index = next((i for i, item in enumerate(mobs) if item.get("status") == "available"), None)
        if index is None:
            index = next((i for i, item in enumerate(mobs) if item.get("status") not in {"defeated", "cleared"}), None)
        if index is None:
            raise StateCommandError("All encounters in the active project are complete", status_code=409)
        return project, mobs, index, mobs[index]

    @staticmethod
    def _project_id(project: Mapping[str, Any]) -> str:
        value = project.get("branch") or project.get("id") or project.get("name")
        if not isinstance(value, str) or not value.strip():
            raise StateCommandError("Active project has no safe identifier", status_code=500)
        return re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())[:MAX_IDENTIFIER_LENGTH]

    @staticmethod
    def _encounter_profile(index: int, project: Mapping[str, Any] | None = None, mob: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """A contract's own objectives when it has authored ones (Resolve is
        their total impact, so the last objective is what fells it), else the
        generic profile for its position."""

        contract = campaign_contract(project.get("branch"), mob.get("name")) if project and mob else None
        authored = contract.get("objectives") if isinstance(contract, Mapping) else None
        if isinstance(authored, list):
            objectives = {
                str(item["id"]): {
                    "impact": max(1, min(MAX_IMPACT, int(item["impact"]))),
                    "question_type": str(item["question_type"]),
                    "label": str(item["label"]),
                    "brief": str(item["brief"]),
                    **({"file": project_file_name(item.get("file"))} if project_file_name(item.get("file")) else {}),
                    **({"see": [name for name in item["see"] if project_file_name(name)][:4]} if isinstance(item.get("see"), list) else {}),
                    **({"check": setup_check_spec(item.get("check"))} if item.get("question_type") == "setup_check" else {}),
                }
                for item in authored
                if isinstance(item, Mapping) and item.get("question_type") in CAMPAIGN_QUESTION_TYPES
                and (item.get("question_type") != "setup_check" or setup_check_spec(item.get("check")))
                and all(isinstance(item.get(key), str) for key in ("id", "label", "brief")) and isinstance(item.get("impact"), int)
            }
            if objectives:
                return {"max_resolve": sum(item["impact"] for item in objectives.values()), "objectives": objectives}
        return ENCOUNTER_PROFILES[min(max(index, 0), len(ENCOUNTER_PROFILES) - 1)]

    @staticmethod
    def _mob_sign_concept(project: Mapping[str, Any] | None, mob: Mapping[str, Any]) -> object:
        """The concept text a bounty feeds signs with: its contract's sign when authored."""

        contract = campaign_contract(project.get("branch"), mob.get("name")) if project else None
        sign = contract.get("sign") if isinstance(contract, Mapping) else None
        return HUNTER_SIGN_CONCEPTS.get(sign, mob.get("concept")) if isinstance(sign, str) else mob.get("concept")

    @staticmethod
    def _compact_sync_mobs(project: Mapping[str, Any], mobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Keep the synced board small: anything the story file can restore is
        left out (a finished board, trailing locked contracts, contract text,
        zero counters). _extend_campaign puts it back after a pull."""

        branch = project.get("branch")
        if not any(campaign_contract(branch, mob.get("name")) for mob in mobs):
            return mobs
        if project.get("completed") is True:
            return []
        while mobs and mobs[-1].get("status") == "locked" and campaign_contract(branch, mobs[-1].get("name")):
            mobs.pop()
        compact = []
        for mob in mobs:
            item = dict(mob)
            if campaign_contract(branch, item.get("name")):
                item.pop("concept", None)
                item.pop("encounter", None)
            for field in ("resolve", "impact_applied", "objective_attempts"):
                if item.get(field) == 0:
                    item.pop(field)
            compact.append(item)
        return compact

    def _extend_campaign(self, progress: dict[str, Any]) -> bool:
        """Bring the save up to the authored campaign: add catalog projects
        that are missing and append new contracts to unfinished boards
        (matched by name). Idempotent; finished projects are never touched."""

        projects = progress.get("projects")
        if not isinstance(projects, list):
            return False
        content = load_campaign_bounties()
        changed = False
        kept = [item for item in projects if not self._retired_and_untouched(progress, item)]
        if len(kept) != len(projects):
            projects[:] = kept
            changed = True
        known = {item.get("branch") for item in projects if isinstance(item, dict)}
        for branch, entry in sorted(content.items(), key=lambda pair: int(pair[1].get("order", 99)) if isinstance(pair[1], Mapping) and isinstance(pair[1].get("order"), int) else 99):
            if not isinstance(entry, Mapping) or not entry.get("catalog") or branch in known or len(projects) >= MAX_SYNC_PROJECTS:
                continue
            if not all(isinstance(entry.get(key), str) for key in ("name", "boss")):
                continue
            projects.append({
                "branch": branch,
                "name": entry["name"],
                "status": "available",
                "boss": entry["boss"],
                "order": int(entry.get("order", len(projects))),
                "progress": 0,
                "mobs": [],
            })
            changed = True
        for project in projects:
            if not isinstance(project, dict):
                continue
            entry = content.get(str(project.get("branch") or ""))
            if not isinstance(entry, Mapping):
                continue
            authored = [
                item for item in entry.get("mobs", [])
                if isinstance(item, Mapping) and all(isinstance(item.get(key), str) for key in ("name", "concept", "encounter"))
            ][:MAX_SYNC_MOBS_PER_PROJECT]
            by_name = {item["name"]: item for item in authored}
            mobs = project.get("mobs")
            finished = project.get("completed") is True or project.get("status") == "completed"
            if finished:
                # A finished board syncs empty; show it as fully cleared again.
                if (not isinstance(mobs, list) or not mobs) and authored:
                    project["mobs"] = [{"name": item["name"], "concept": item["concept"], "encounter": item["encounter"], "status": "defeated", "resolve": 0} for item in authored]
                    changed = True
                continue
            if isinstance(entry.get("order"), int) and project.get("order") != entry["order"]:
                # The campaign order is authored; the next boss clear follows it.
                project["order"] = entry["order"]
                changed = True
            if isinstance(entry.get("boss"), str) and entry["boss"] and project.get("boss") != entry["boss"]:
                # The boss is authored content: an unfinished campaign follows a renamed boss.
                project["boss"] = entry["boss"]
                changed = True
            if entry.get("multi_file") is True and project.get("multi_file") is not True:
                project["multi_file"] = True
                changed = True
            if self._reseed_untouched_board(progress, project, authored):
                mobs = project.get("mobs")
                if isinstance(entry.get("entry_file"), str):
                    # A rewritten campaign may move into its own project folder.
                    project["entry_file"] = entry["entry_file"]
                if isinstance(entry.get("name"), str) and entry["name"]:
                    project["name"] = entry["name"]
                changed = True
            if isinstance(mobs, list):
                for mob in mobs:
                    contract = by_name.get(mob.get("name")) if isinstance(mob, dict) else None
                    if contract:
                        for key in ("concept", "encounter"):
                            if not isinstance(mob.get(key), str):
                                mob[key] = contract[key]
                                changed = True
            if (not isinstance(mobs, list) or not mobs) and authored and project.get("status") in {"active", "available"}:
                # An untouched board syncs empty; seed it like opening it would.
                project["mobs"] = [{"name": item["name"], "concept": item["concept"], "encounter": item["encounter"], "status": "locked"} for item in authored]
                project["mobs"][0]["status"] = "available"
                changed = True
            if isinstance(entry.get("entry_file"), str) and not project.get("entry_file"):
                project["entry_file"] = entry["entry_file"]
                changed = True
            mobs = project.get("mobs")
            if not isinstance(mobs, list) or not mobs or not all(isinstance(item, dict) for item in mobs):
                continue  # an empty board is seeded when the project opens
            names = {item.get("name") for item in mobs}
            additions = [
                {"name": item["name"], "concept": item["concept"], "encounter": item["encounter"], "status": "locked"}
                for item in entry.get("mobs", [])
                if isinstance(item, Mapping) and all(isinstance(item.get(key), str) for key in ("name", "concept", "encounter")) and item["name"] not in names
            ][: max(0, MAX_SYNC_MOBS_PER_PROJECT - len(mobs))]
            if not additions:
                continue
            mobs.extend(additions)
            if not any(item.get("status") == "available" for item in mobs):
                upcoming = next((item for item in mobs if item.get("status") == "locked"), None)
                if upcoming is not None:
                    upcoming["status"] = "available"
            if project.get("boss_status") == "available":
                # New contracts stand between the hunter and the boss again.
                project.pop("boss_status", None)
            if project.get("status") == "active":
                progress["current_quest"] = (
                    f"{project.get('name') or project.get('branch')}: clear the bounty board, "
                    f"then face {project.get('boss') or 'the boss'}."
                )
            if project.get("mob_sequence_complete"):
                project["mob_sequence_complete"] = False
            cleared = sum(1 for item in mobs if item.get("status") in {"defeated", "cleared"})
            project["progress"] = round(cleared / max(1, len(mobs)) * 100)
            changed = True
        return changed

    @staticmethod
    def _retired_and_untouched(progress: Mapping[str, Any], project: object) -> bool:
        """A retired campaign nobody has played: safe to drop from the save."""

        if not isinstance(project, Mapping) or project.get("branch") not in RETIRED_CAMPAIGNS:
            return False
        if project.get("status") in {"active", "completed"} or project.get("completed") is True or project.get("boss_validation"):
            return False
        mobs = project.get("mobs")
        names = {item.get("name") for item in mobs if isinstance(item, Mapping)} if isinstance(mobs, list) else set()
        if any(isinstance(item, Mapping) and item.get("status") in {"defeated", "cleared"} for item in mobs or []):
            return False
        encounter = progress.get("encounter_state")
        return not (isinstance(encounter, Mapping) and encounter.get("mob_name") in names)

    @staticmethod
    def _reseed_untouched_board(progress: Mapping[str, Any], project: dict[str, Any], authored: list[Mapping[str, Any]]) -> bool:
        """Replace a board nobody has played when its campaign was rewritten.

        Only a board that is not the active one, has nothing cleared and is not
        the current fight is replaced, so no progress can ever be lost; it is
        replaced whole (never appended to) and doing it twice changes nothing.
        """

        mobs = project.get("mobs")
        if not authored or not isinstance(mobs, list) or not mobs or project.get("status") == "active":
            return False
        names = [item.get("name") for item in mobs if isinstance(item, Mapping)]
        if names == [item["name"] for item in authored]:
            return False
        if any(isinstance(item, Mapping) and item.get("status") in {"defeated", "cleared"} for item in mobs):
            return False
        encounter = progress.get("encounter_state")
        if isinstance(encounter, Mapping) and encounter.get("mob_name") in names:
            return False
        project["mobs"] = [{"name": item["name"], "concept": item["concept"], "encounter": item["encounter"], "status": "locked"} for item in authored]
        project["mobs"][0]["status"] = "available"
        project["progress"] = 0
        project.pop("boss_status", None)
        project.pop("boss_validation", None)
        project["mob_sequence_complete"] = False
        return True

    def _campaign_extend(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        self._payload(payload, set(), set())
        changed = self._extend_campaign(progress)
        return Mutation(changed, {"extended": changed}, {"reason": "campaign_extended"} if changed else None)

    def spar_roster(self, progress: Mapping[str, Any]) -> list[dict[str, Any]]:
        """Foes the hunter has already met, for simulated Tutor fights:
        campaign contracts cleared (or being fought) and beasts whose sign the
        hunter has used."""

        roster: list[dict[str, Any]] = []
        encounter = progress.get("encounter_state") if isinstance(progress.get("encounter_state"), Mapping) else {}
        projects = progress.get("projects") if isinstance(progress.get("projects"), list) else []
        for project_index, project in enumerate(projects):
            if not isinstance(project, Mapping):
                continue
            for mob_index, mob in enumerate(project.get("mobs", []) if isinstance(project.get("mobs"), list) else []):
                if not isinstance(mob, Mapping) or not isinstance(mob.get("name"), str):
                    continue
                fighting = encounter.get("mob_name") == mob["name"] and (encounter.get("completed_objectives") or self._counter(encounter, "attempts"))
                if mob.get("status") not in {"defeated", "cleared"} and not fighting:
                    continue
                contract = campaign_contract(project.get("branch"), mob["name"]) or {}
                sign = contract.get("sign") if isinstance(contract.get("sign"), str) else None
                roster.append({
                    "id": f"c-{project_index}-{mob_index}",
                    "name": mob["name"],
                    "kind": "contract",
                    "campaign": project.get("name"),
                    "concept": str(mob.get("concept") or contract.get("concept") or ""),
                    "sign": sign,
                })
        for sign in self.hunter_projection(progress)["signs"]:
            if sign["xp"] > 0 and sign["id"] in HUNTER_BEASTS:
                roster.append({
                    "id": f"b-{sign['id']}",
                    "name": HUNTER_BEASTS[sign["id"]]["beast"],
                    "kind": "beast",
                    "campaign": None,
                    "concept": HUNTER_SIGN_CONCEPTS[sign["id"]],
                    "sign": sign["id"],
                })
        return roster[:80]

    def campaign_view(self, progress: Mapping[str, Any]) -> dict[str, Any]:
        """A copy of the save brought up to the authored campaign, for reads."""

        view = copy.deepcopy(dict(progress))
        self._extend_campaign(view)
        return view

    def campaign_board(self, progress: Mapping[str, Any]) -> dict[str, Any] | None:
        """The active project's story: acts and contracts with beasts and signs."""

        projects = [item for item in progress.get("projects", []) if isinstance(item, Mapping)] if isinstance(progress.get("projects"), list) else []
        project = next((item for item in projects if item.get("status") == "active"), None)
        if project is None:
            return None
        entry = load_campaign_bounties().get(str(project.get("branch") or ""))
        entry = entry if isinstance(entry, Mapping) else {}
        story = entry.get("story") if isinstance(entry.get("story"), Mapping) else {}
        acts = [dict(item) for item in entry.get("acts", []) if isinstance(item, Mapping)] if isinstance(entry.get("acts"), list) else []
        contracts = []
        for index, mob in enumerate(project.get("mobs", []) if isinstance(project.get("mobs"), list) else []):
            if not isinstance(mob, Mapping):
                continue
            contract = campaign_contract(project.get("branch"), mob.get("name")) or {}
            sign = contract.get("sign") if isinstance(contract.get("sign"), str) else None
            profile = self._encounter_profile(index, project, mob)
            contracts.append({
                "name": mob.get("name"),
                "status": mob.get("status"),
                "concept": mob.get("concept"),
                "encounter": mob.get("encounter"),
                "act": contract.get("act", 1) if isinstance(contract.get("act"), int) else 1,
                "contract": contract.get("contract") if isinstance(contract.get("contract"), str) else None,
                "sign": sign,
                "beast": HUNTER_BEASTS[sign]["beast"] if sign in HUNTER_BEASTS else None,
                # light (one code task, two questions), quick (two goals) or elite (four or five).
                "tier": contract.get("tier") if contract.get("tier") in {"light", "quick", "elite"} else None,
                "kind": contract.get("kind") if contract.get("kind") in CONTRACT_KINDS else None,
                "objectives": [{"id": key, "label": value["label"], "question_type": value["question_type"], **({"file": value["file"]} if value.get("file") else {})} for key, value in profile["objectives"].items()],
            })
        return {
            "branch": project.get("branch"),
            "name": project.get("name"),
            "boss": project.get("boss"),
            "entry_file": project.get("entry_file") or entry.get("entry_file"),
            "project_dir": project_dir_name(entry.get("project_dir")),
            "story": {key: story[key] for key in ("title", "client", "hook") if isinstance(story.get(key), str)},
            "acts": acts,
            "boss_brief": entry.get("boss_brief") if isinstance(entry.get("boss_brief"), str) else None,
            "contracts": contracts,
        }

    def _ensure_encounter_state(
        self,
        progress: dict[str, Any],
        project: Mapping[str, Any],
        mob: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        profile = self._encounter_profile(index, project, mob)
        project_id = self._project_id(project)
        mob_name = self._text(mob.get("name", ""), "mob_name", max_length=MAX_IDENTIFIER_LENGTH)
        existing = progress.get("encounter_state")
        if (
            not isinstance(existing, dict)
            or existing.get("project_id") != project_id
            or existing.get("mob_name") != mob_name
            or existing.get("status") == "defeated"
        ):
            existing = {
                "project_id": project_id,
                "mob_name": mob_name,
                "status": "active",
                "resolve": int(profile["max_resolve"]),
                "max_resolve": int(profile["max_resolve"]),
                "completed_objectives": [],
                "attempts": 0,
                "question_types": [],
                "trinket_triggers": [],
            }
            # Gear and food that act at the start of a battle (a new one only).
            effects = self._gear_effects(progress)
            buffs = self._armory_take_buffs(progress)
            existing["guards"] = min(2, effects["start_guards"] + int(buffs.get("guards", 0)))
            existing["buffs"] = {key: buffs[key] for key in ("reduction", "xp_bonus", "coin_bonus") if buffs.get(key)}
            progress["encounter_state"] = existing
        else:
            try:
                existing.setdefault("max_resolve", int(profile["max_resolve"]))
                existing["max_resolve"] = max(1, int(existing["max_resolve"]))
                existing.setdefault("resolve", int(existing["max_resolve"]))
                existing["resolve"] = max(0, min(existing["max_resolve"], int(existing["resolve"])))
            except (TypeError, ValueError) as exc:
                raise StateCommandError("Existing encounter Resolve state is invalid", status_code=500) from exc
            existing.setdefault("completed_objectives", [])
            existing.setdefault("attempts", 0)
            existing.setdefault("question_types", [])
            existing.setdefault("trinket_triggers", [])
        mob.setdefault("max_resolve", int(existing["max_resolve"]))
        mob.setdefault("resolve", int(existing["resolve"]))
        mob.setdefault("impact_applied", 0)
        mob.setdefault("objective_attempts", 0)
        return existing

    @staticmethod
    def _codex_container(progress: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        codex = progress.get("codex")
        if codex is None:
            codex = {}
            progress["codex"] = codex
        if not isinstance(codex, dict):
            raise StateCommandError("Existing state field codex is invalid", status_code=500)
        entries = codex.get("encounters")
        if entries is None:
            entries = []
            codex["encounters"] = entries
        if not isinstance(entries, list) or not all(isinstance(item, dict) for item in entries):
            raise StateCommandError("Existing state field codex.encounters is invalid", status_code=500)
        return codex, entries

    @staticmethod
    def _codex_page_id(concept: object) -> str | None:
        """Map a recorded concept label to a generic library page."""

        if not isinstance(concept, str):
            return None
        normalized = concept.casefold()
        for page in CODEX_CONCEPT_PAGES:
            aliases = page.get("aliases", ())
            if any(isinstance(alias, str) and alias.casefold() in normalized for alias in aliases):
                return str(page["id"])
        return None

    def codex_projection(self, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Return the safe book/page projection used by the live Codex UI.

        Only canonical encounter observations are copied.  Unknown fields on
        a legacy or provider-created record are intentionally omitted, which
        keeps answer keys and arbitrary provider payloads out of the browser.
        """

        mutable_progress = progress if isinstance(progress, dict) else dict(progress)
        _, entries = self._codex_container(mutable_progress)
        projected_entries: list[dict[str, Any]] = []
        page_entry_ids: dict[str, list[str]] = {str(page["id"]): [] for page in CODEX_CONCEPT_PAGES}
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            entry_id = entry.get("id")
            mob_name = entry.get("mob_name")
            if not isinstance(entry_id, str) or not entry_id.strip() or not isinstance(mob_name, str):
                continue
            page_id = self._codex_page_id(entry.get("concept"))
            safe: dict[str, Any] = {
                "id": entry_id,
                "project_id": str(entry.get("project_id") or ""),
                "mob_name": mob_name[:MAX_IDENTIFIER_LENGTH],
                "concept": str(entry.get("concept") or "Unknown concept")[:MAX_REASON_LENGTH],
                "page_id": page_id,
                # Notes are workspace artifacts, not player-state fields. The
                # path is a safe, deterministic link for the Codex UI; note
                # contents are fetched through the dedicated notes endpoint.
                "notes_path": f"{CODEX_NOTES_DIRECTORY}/{page_id}.md" if page_id else None,
                "status": str(entry.get("status") or "observed"),
                "attempts": max(0, int(entry.get("attempts", 0) or 0)),
                "question_types": [item for item in entry.get("question_types", []) if isinstance(item, str)][-20:],
                "weaknesses": [item for item in entry.get("weaknesses", []) if isinstance(item, str)][-20:],
                "notes": [item for item in entry.get("notes", []) if isinstance(item, str)][-20:],
                "player_notes": [item for item in entry.get("player_notes", []) if isinstance(item, str)][-MAX_CODEX_NOTES_PER_ENTRY:],
                "code_snippet": str(entry.get("code_snippet") or "")[:MAX_CODEX_SNIPPET_BYTES],
                "results": [
                    {
                        "outcome": str(item.get("outcome") or "recorded"),
                        "evidence_id": str(item.get("evidence_id") or ""),
                    }
                    for item in entry.get("results", [])
                    if isinstance(item, Mapping)
                ][-20:],
                "interview_history": [
                    {
                        "outcome": str(item.get("outcome") or "recorded"),
                        "evidence_id": str(item.get("evidence_id") or ""),
                    }
                    for item in entry.get("interview_history", [])
                    if isinstance(item, Mapping)
                ][-20:],
            }
            mastery = entry.get("mastery")
            if isinstance(mastery, Mapping):
                safe["mastery"] = {
                    "evidence": max(0, int(mastery.get("evidence", 0) or 0)),
                    "interview_passes": max(0, int(mastery.get("interview_passes", 0) or 0)),
                    "shield": str(mastery.get("shield") or "none"),
                }
            projected_entries.append(safe)
            if page_id in page_entry_ids:
                page_entry_ids[page_id].append(entry_id)

        pages = [
            {
                "id": str(page["id"]),
                "title": str(page["title"]),
                "definition": str(page["definition"]),
                "examples": list(page.get("examples", ())),
                "when_to_use": str(page.get("when_to_use") or page.get("check_prompt") or "Use this idea when it helps you make program state explicit."),
                "question_types": list(page.get("question_types", ())),
                "common_mistakes": [item for item in page.get("common_mistakes", ()) if isinstance(item, str)][-8:],
                "mistake_examples": [item for item in page.get("mistake_examples", ()) if isinstance(item, str)][-8:],
                "check_prompt": str(page.get("check_prompt") or "Can you explain this idea in your own words?")[:MAX_REASON_LENGTH],
                "notes_path": f"{CODEX_NOTES_DIRECTORY}/{page['id']}.md",
                "encounter_ids": page_entry_ids[str(page["id"])],
            }
            for page in CODEX_CONCEPT_PAGES
        ]
        return {"pages": pages, "entries": projected_entries}

    def _upsert_codex_entry(
        self,
        progress: dict[str, Any],
        project: Mapping[str, Any],
        mob: Mapping[str, Any],
        *,
        question_type: str,
        outcome: str,
        evidence_id: str,
        note: str,
        code_snippet: str | None = None,
    ) -> dict[str, Any]:
        project_id = self._project_id(project)
        mob_name = self._text(mob.get("name", ""), "mob_name", max_length=MAX_IDENTIFIER_LENGTH)
        _, entries = self._codex_container(progress)
        entry = next(
            (item for item in entries if item.get("project_id") == project_id and item.get("mob_name") == mob_name),
            None,
        )
        if entry is None:
            entry = {
                "id": f"{project_id}-{re.sub(r'[^A-Za-z0-9._-]+', '-', mob_name)[:80]}",
                "project_id": project_id,
                "mob_name": mob_name,
                "concept": str(mob.get("concept") or "Unknown concept")[:MAX_REASON_LENGTH],
                "status": "observed",
                "question_types": [],
                "weaknesses": [],
                "notes": [],
                "attempts": 0,
                "results": [],
                "interview_history": [],
                "mastery": {"evidence": 0, "interview_passes": 0, "shield": "none"},
            }
            entries.append(entry)
            if len(entries) > MAX_CODEX_RECORDS:
                del entries[:-MAX_CODEX_RECORDS]
        entry["attempts"] = self._counter(entry, "attempts") + 1
        question_types = entry.setdefault("question_types", [])
        if not isinstance(question_types, list):
            raise StateCommandError("Existing Codex question type history is invalid", status_code=500)
        if question_type not in question_types:
            question_types.append(question_type)
        results = entry.setdefault("results", [])
        if not isinstance(results, list):
            raise StateCommandError("Existing Codex result history is invalid", status_code=500)
        results.append({"outcome": outcome, "evidence_id": evidence_id})
        entry["results"] = results[-20:]
        notes = entry.setdefault("notes", [])
        if not isinstance(notes, list):
            raise StateCommandError("Existing Codex notes are invalid", status_code=500)
        if note not in notes:
            notes.append(note)
        entry["notes"] = notes[-20:]
        if code_snippet:
            entry["code_snippet"] = self._multiline_text(
                code_snippet,
                "code_snippet",
                max_bytes=MAX_CODEX_SNIPPET_BYTES,
            ).strip()
        weaknesses = entry.setdefault("weaknesses", [])
        if not isinstance(weaknesses, list):
            raise StateCommandError("Existing Codex weakness history is invalid", status_code=500)
        entry["weaknesses"] = weaknesses[-20:]
        interview_history = entry.setdefault("interview_history", [])
        if not isinstance(interview_history, list):
            raise StateCommandError("Existing Codex interview history is invalid", status_code=500)
        entry["interview_history"] = interview_history[-20:]
        mastery = entry.setdefault("mastery", {"evidence": 0, "interview_passes": 0, "shield": "none"})
        if not isinstance(mastery, dict):
            raise StateCommandError("Existing Codex mastery state is invalid", status_code=500)
        if outcome in {"verified", "defeated"}:
            mastery["evidence"] = self._counter(mastery, "evidence") + 1
        return entry

    def _update_skill_evidence(self, progress: dict[str, Any], concept: object) -> None:
        if not isinstance(concept, str) or not concept:
            return
        normalized_concept = concept.casefold()
        skills = progress.get("skills")
        if not isinstance(skills, list):
            return
        for skill in skills:
            if not isinstance(skill, dict) or not isinstance(skill.get("concept"), str):
                continue
            skill_concept = skill["concept"].casefold()
            # Mob concepts are often richer than the canonical skill label
            # (for example, "Program loops and reset state"), so evidence is
            # attributed only when one complete concept label contains the
            # other.  This keeps the gateway authoritative without guessing
            # from arbitrary words or caller-supplied labels.
            if skill_concept == normalized_concept or skill_concept in normalized_concept or normalized_concept in skill_concept:
                skill["evidence"] = self._counter(skill, "evidence") + 1
                skill["battle_attempts"] = self._counter(skill, "battle_attempts") + 1
                return

    def _finish_mob(
        self,
        progress: dict[str, Any],
        project: dict[str, Any],
        mobs: list[dict[str, Any]],
        index: int,
        mob: dict[str, Any],
        encounter: dict[str, Any],
        *,
        evidence_id: str,
        reason: str,
    ) -> dict[str, Any]:
        # Seed hunter progress before this bounty counts as defeated history.
        self._hunter_state(progress)
        mob["status"] = "defeated"
        mob["resolve"] = 0
        encounter["status"] = "defeated"
        encounter["resolve"] = 0
        next_mob = None
        for candidate in mobs[index + 1 :]:
            if candidate.get("status") in {"locked", "available"}:
                candidate["status"] = "available"
                next_mob = str(candidate.get("name") or "")
                break

        stats = self._dict(progress, "stats")
        stats["mobs_defeated"] = self._counter(stats, "mobs_defeated") + 1
        self._log_activity(progress, "mobs")
        self._hunter_record(progress, concept=self._mob_sign_concept(project, mob), question_type=None, source="campaign", clean=True, campaign_use=True)
        cleared_count = sum(1 for candidate in mobs if candidate.get("status") in {"defeated", "cleared"})
        project["progress"] = round(cleared_count / max(1, len(mobs)) * 100)
        boss_unlocked = next_mob is None
        if boss_unlocked:
            # A mob sequence ending is a gate, not a boss victory.  The
            # integrated boss still needs its own verified behaviour,
            # explanation and interview evidence before it can award boss XP.
            project["progress"] = 100
            project["mob_sequence_complete"] = True
            project["boss_status"] = "available"
        for goal in (progress.get("goals") or {}).get("weekly", []):
            if isinstance(goal, dict) and goal.get("id") == "two-mobs":
                target = max(1, self._counter(goal, "target"))
                goal["progress"] = min(target, self._counter(goal, "progress") + 1)
                goal["done"] = goal["progress"] >= target

        player = self._dict(progress, "player")
        reward_xp, reward_coins = MOB_REWARDS[min(max(index, 0), len(MOB_REWARDS) - 1)]
        effects = self._gear_effects(progress)
        buffs = encounter.get("buffs") if isinstance(encounter.get("buffs"), Mapping) else {}
        reward_xp = min(MAX_REWARD_XP, reward_xp * (100 + min(ARMORY_BONUS_CAP, effects["xp_bonus"] + int(buffs.get("xp_bonus", 0)))) // 100)
        reward_coins = min(MAX_REWARD_COINS, reward_coins * (100 + min(ARMORY_BONUS_CAP, effects["coin_bonus"] + int(buffs.get("coin_bonus", 0)))) // 100)
        pyr_assists = self._counter(encounter, "pyr_assists")
        reward_scale = self.pyr_reward_scale(pyr_assists)
        reward_xp = reward_xp * reward_scale // 100
        reward_coins = reward_coins * reward_scale // 100
        reward = self._grant_reward(player, reward_xp, reward_coins)
        loot = None if pyr_assists >= PYR_ASSIST_LOOT_LIMIT else self._armory_contract_drop(progress, project, mobs, index, mob, evidence_id)
        aid_loot = None if pyr_assists >= PYR_ASSIST_LOOT_LIMIT else self._aid_drop(progress, project, mobs, index, mob, evidence_id)
        achievement_unlocked = None
        achievements = progress.get("achievements")
        if isinstance(achievements, list):
            first_blood = next((item for item in achievements if isinstance(item, dict) and item.get("name") == "First Blood"), None)
            if first_blood is not None and first_blood.get("unlocked") is not True:
                first_blood["unlocked"] = True
                achievement_unlocked = "First Blood"
        companion = progress.get("companion")
        if isinstance(companion, dict):
            companion["bond"] = self._counter(companion, "bond") + 1
        return {
            "mob_defeated": True,
            "mob_name": str(mob.get("name") or ""),
            "next_mob": next_mob,
            "boss_unlocked": boss_unlocked,
            "boss_name": str(project.get("boss") or "") if boss_unlocked else None,
            "project_name": str(project.get("name") or "") if boss_unlocked else None,
            "project_progress": project.get("progress", 0),
            "boss_status": project.get("boss_status") if boss_unlocked else None,
            "reward_xp": reward_xp,
            "reward_coins": reward_coins,
            "loot": loot,
            "aid_loot": aid_loot,
            "pyr_assists": pyr_assists,
            "reward_scale": reward_scale,
            "level_before": reward["level_before"],
            "level_after": reward["level_after"],
            "achievement_unlocked": achievement_unlocked,
            "evidence_id": evidence_id,
            "reason": reason,
        }

    def _record_battle_objective(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"objective_id", "evidence_id", "reason", "code_snippet"}, {"objective_id", "evidence_id", "reason"})
        objective_id = self._text(data["objective_id"], "objective_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        code_snippet = None
        if data.get("code_snippet"):
            code_snippet = self._multiline_text(data["code_snippet"], "code_snippet", max_bytes=MAX_CODEX_SNIPPET_BYTES).strip()
        project, mobs, index, mob = self._active_project_and_mob(progress)
        profile = self._encounter_profile(index, project, mob)
        objective = profile["objectives"].get(objective_id)
        if objective is None:
            raise StateCommandError("This verified objective is not defined for the active encounter")
        encounter = self._ensure_encounter_state(progress, project, mob, index)
        completed = encounter.get("completed_objectives")
        if not isinstance(completed, list):
            raise StateCommandError("Existing encounter objective history is invalid", status_code=500)
        if objective_id in completed:
            raise StateCommandError("This encounter objective has already been verified", status_code=409)
        before = max(0, min(int(encounter.get("max_resolve", profile["max_resolve"])), int(encounter.get("resolve", profile["max_resolve"]))))
        base_impact = self._integer(objective["impact"], "impact", minimum=1, maximum=MAX_IMPACT)
        impact = base_impact
        bonus_impact = 0
        trinket_trigger = None
        trinket_name = str((progress.get("equipment") or {}).get("trinket") or "")
        trinket_triggers = encounter.setdefault("trinket_triggers", [])
        if not isinstance(trinket_triggers, list):
            raise StateCommandError("Existing encounter trinket history is invalid", status_code=500)
        if trinket_name == "Ember Scythe" and "ember-scythe:first-objective" not in trinket_triggers:
            bonus_impact = min(1, max(0, before - base_impact))
            if bonus_impact:
                impact = min(MAX_IMPACT, base_impact + bonus_impact)
                trinket_triggers.append("ember-scythe:first-objective")
                trinket_trigger = "Ember Scythe"
        effects = self._gear_effects(progress)
        weapon = effects["weapon"]
        if weapon and weapon.get("on") in {"any", objective["question_type"]}:
            impact = min(MAX_IMPACT + ARMORY_EFFECT_CAPS["impact"], impact + int(weapon.get("impact", 0)))
        special = campaign_special_mechanic(project, str(mob.get("name") or ""))
        if special and special["reward"] == "focus" and special["trigger"] in completed:
            impact = min(MAX_IMPACT + ARMORY_EFFECT_CAPS["impact"], impact + 1)
        after = max(0, before - impact)
        remaining = [key for key in profile["objectives"] if key not in completed and key != objective_id]
        guard_break = None
        if after == 0 and remaining:
            # The iron rule: impact never ends a battle before its last
            # objective. Breaking the guard early only helps: a free mistake
            # and coins, then Resolve is what the remaining objectives remove.
            break_coins = CAMPAIGN_BREAK_COINS + (int(weapon.get("break_coins", 0)) if weapon else 0)
            encounter["guards"] = min(3, self._counter(encounter, "guards") + 1)
            break_player = self._dict(progress, "player")
            break_player["coins"] = self._counter(break_player, "coins") + break_coins
            break_stats = self._dict(progress, "stats")
            break_stats["guard_breaks"] = self._counter(break_stats, "guard_breaks") + 1
            after = max(1, sum(int(profile["objectives"][key]["impact"]) for key in remaining))
            guard_break = {"coins": break_coins, "guards": encounter["guards"]}
        healed = 0
        if effects["heal_on_objective"]:
            heal_player = self._dict(progress, "player")
            current_hp = self._counter(heal_player, "hp")
            healed = max(0, min(effects["heal_on_objective"], self._counter(heal_player, "max_hp") - current_hp))
            heal_player["hp"] = current_hp + healed
        completed.append(objective_id)
        mechanic_reward = apply_campaign_mechanic(progress, encounter, special) if special and special["trigger"] == objective_id else None
        encounter["completed_objectives"] = completed[-20:]
        encounter["resolve"] = after
        encounter["attempts"] = self._counter(encounter, "attempts") + 1
        encounter["last_objective_id"] = objective_id
        encounter["last_question_type"] = objective["question_type"]
        question_types = encounter.setdefault("question_types", [])
        if objective["question_type"] not in question_types:
            question_types.append(objective["question_type"])
        mob["resolve"] = after
        mob["max_resolve"] = int(encounter["max_resolve"])
        mob["impact_applied"] = self._counter(mob, "impact_applied") + impact
        mob["objective_attempts"] = self._counter(mob, "objective_attempts") + 1
        self._update_skill_evidence(progress, mob.get("concept"))
        missed = encounter.get("missed_objectives") if isinstance(encounter.get("missed_objectives"), list) else []
        hunter_gain = self._hunter_record(progress, concept=self._mob_sign_concept(project, mob), question_type=objective["question_type"], source="campaign", clean=objective_id not in missed)
        entry = self._upsert_codex_entry(
            progress,
            project,
            mob,
            question_type=str(objective["question_type"]),
            outcome="verified",
            evidence_id=evidence_id,
            note=reason,
            code_snippet=code_snippet,
        )
        finish = None
        if after == 0:
            finish = self._finish_mob(progress, project, mobs, index, mob, encounter, evidence_id=evidence_id, reason=reason)
            entry["status"] = "defeated"
        else:
            entry["status"] = "observed"
        return Mutation(
            True,
            {
                "guard_break": guard_break,
                "mechanic_reward": mechanic_reward,
                "healed": healed,
                "guards": self._counter(encounter, "guards"),
                "mob_name": str(mob.get("name") or ""),
                "objective_id": objective_id,
                "impact": impact,
                "base_impact": base_impact,
                "bonus_impact": bonus_impact,
                "trinket_trigger": trinket_trigger,
                "resolve_before": before,
                "resolve_after": after,
                "mob_defeated": bool(finish),
                "codex_entry_id": entry["id"],
                "hunter_gain": hunter_gain,
                **(finish or {"reward_xp": 0, "reward_coins": 0, "next_mob": None}),
            },
            {
                "project_id": self._project_id(project),
                "mob_name": str(mob.get("name") or ""),
                "objective_id": objective_id,
                "question_type": str(objective["question_type"]),
                "base_impact": base_impact,
                "bonus_impact": bonus_impact,
                "trinket_trigger": trinket_trigger,
                "evidence_id": evidence_id,
                "reason": reason,
                "impact": impact,
                "resolve_before": before,
                "resolve_after": after,
                "mob_defeated": bool(finish),
                "codex_entry_id": entry["id"],
                "guard_break": guard_break,
                "mechanic_reward": mechanic_reward,
                **(finish or {"reward_xp": 0, "reward_coins": 0, "level_before": self._counter(progress.get("player") or {}, "level"), "level_after": self._counter(progress.get("player") or {}, "level"), "next_mob": None, "achievement_unlocked": None}),
            },
        )

    def _complete_mob(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"evidence_id", "reason"}, {"evidence_id", "reason"})
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        existing = progress.get("encounter_state")
        if isinstance(existing, dict) and existing.get("status") == "defeated":
            return Mutation(False, {"already_defeated": True, "mob_name": existing.get("mob_name")})
        project, mobs, index, mob = self._active_project_and_mob(progress)
        encounter = self._ensure_encounter_state(progress, project, mob, index)
        if int(encounter.get("resolve", 0)) > 0:
            raise StateCommandError("The encounter still has Resolve remaining", status_code=409)
        finish = self._finish_mob(progress, project, mobs, index, mob, encounter, evidence_id=evidence_id, reason=reason)
        entry = self._upsert_codex_entry(progress, project, mob, question_type="completion", outcome="defeated", evidence_id=evidence_id, note=reason)
        entry["status"] = "defeated"
        return Mutation(True, finish, {"project_id": self._project_id(project), **finish, "codex_entry_id": entry["id"]})

    def _record_codex_note(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Append one bounded player-authored note to an existing entry."""

        data = self._payload(payload, {"entry_id", "note"}, {"entry_id", "note"})
        entry_id = self._text(data["entry_id"], "entry_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if not isinstance(data["note"], str) or "\x00" in data["note"]:
            raise StateCommandError("note contains unsupported control characters")
        note = self._multiline_text(data["note"], "note", max_bytes=MAX_CODEX_NOTE_BYTES).strip()
        if not note:
            raise StateCommandError("note must not be empty")
        _, entries = self._codex_container(progress)
        entry = next((item for item in entries if item.get("id") == entry_id), None)
        if entry is None:
            raise StateCommandError("Codex entry was not found", status_code=404)
        notes = entry.setdefault("player_notes", [])
        if not isinstance(notes, list) or not all(isinstance(item, str) for item in notes):
            raise StateCommandError("Existing Codex player notes are invalid", status_code=500)
        if note in notes:
            return Mutation(
                False,
                {"entry_id": entry_id, "note_count": len(notes), "already_saved": True},
            )
        notes.append(note)
        entry["player_notes"] = notes[-MAX_CODEX_NOTES_PER_ENTRY:]
        return Mutation(
            True,
            {"entry_id": entry_id, "note_count": len(entry["player_notes"]), "saved": True},
            {
                "entry_id": entry_id,
                "note_count": len(entry["player_notes"]),
                "reason": "player_codex_note",
            },
        )

    @classmethod
    def practice_options(cls) -> dict[str, Any]:
        """Return safe Tutor/Practice selectors without question content.

        The unified Tutor surface uses the same selectors as Practice. This
        catalogue contains only generic concept labels and question-type
        labels; prompts, answer keys, and provider challenge material are
        intentionally absent.
        """

        return {
            "concepts": [
                {"id": str(page["id"]), "title": str(page["title"])}
                for page in CODEX_CONCEPT_PAGES
            ],
            "question_types": [
                {
                    "id": question_type,
                    "label": PRACTICE_QUESTION_TYPE_LABELS[question_type],
                }
                for question_type in PRACTICE_QUESTION_TYPE_ORDER
                if question_type in PRACTICE_QUESTION_TYPES
            ],
            "difficulty": {
                "min": PRACTICE_DIFFICULTY_MIN,
                "max": PRACTICE_DIFFICULTY_MAX,
            },
            "notes_directory": CODEX_NOTES_DIRECTORY,
            "tutor_file": "tutor.py",
        }

    @classmethod
    def practice_projection(cls, progress: Mapping[str, Any]) -> dict[str, Any]:
        """Return the bounded, answer-free Practice history projection.

        Practice is intentionally independent from Campaign and Dungeon.  The
        history records only the selected drill metadata and provider-validated
        outcomes; raw answers, prompts and answer keys never enter canonical
        state or this projection.
        """

        raw = progress.get("practice_sessions") if isinstance(progress, Mapping) else None
        if raw is None:
            raw = []
        if not isinstance(raw, list):
            raise StateCommandError("Existing Practice history is invalid", status_code=500)
        sessions: list[dict[str, Any]] = []
        for item in raw[-MAX_PRACTICE_SESSIONS:]:
            if not isinstance(item, Mapping):
                continue
            session_id = item.get("session_id")
            concept = item.get("concept")
            question_type = item.get("question_type")
            if not all(isinstance(value, str) and value.strip() for value in (session_id, concept, question_type)):
                continue
            history = item.get("history") if isinstance(item.get("history"), list) else []
            safe_history = []
            for attempt in history[-MAX_PRACTICE_ATTEMPTS_PER_SESSION:]:
                if not isinstance(attempt, Mapping):
                    continue
                safe_attempt = {
                    key: attempt[key]
                    for key in ("outcome", "evidence_id", "reason", "recorded_at")
                    if key in attempt
                }
                safe_history.append(safe_attempt)
            try:
                difficulty = max(
                    PRACTICE_DIFFICULTY_MIN,
                    min(PRACTICE_DIFFICULTY_MAX, int(item.get("difficulty", PRACTICE_DIFFICULTY_MIN) or PRACTICE_DIFFICULTY_MIN)),
                )
                attempts = max(0, int(item.get("attempts", 0) or 0))
                correct = max(0, int(item.get("correct", 0) or 0))
            except (TypeError, ValueError) as exc:
                raise StateCommandError("Existing Practice counters are invalid", status_code=500) from exc
            sessions.append(
                {
                    "session_id": session_id,
                    "concept": concept,
                    "question_type": question_type,
                    "difficulty": difficulty,
                    "status": str(item.get("status") or "requested"),
                    "attempts": attempts,
                    "correct": correct,
                    "started_at": item.get("started_at"),
                    "updated_at": item.get("updated_at"),
                    "history": safe_history,
                }
            )
        # Keep selectors next to history so a single revision-aware campaign
        # fetch can hydrate both Tutor and Practice without another catalogue
        # invented by React.
        options = cls.practice_options()
        return {
            "sessions": sessions,
            "count": len(sessions),
            "selectors": options,
            # Top-level aliases make the small /api/practice response easy to
            # consume while retaining the nested selector contract.
            "concepts": options["concepts"],
            "question_types": options["question_types"],
            "difficulty": options["difficulty"],
            "notes_directory": options["notes_directory"],
            "tutor_file": options["tutor_file"],
        }

    def _practice_session_started(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Open one independent Practice drill without touching game state."""

        data = self._payload(payload, {"concept", "question_type", "difficulty"}, {"concept", "question_type", "difficulty"})
        concept = self._text(data["concept"], "concept", max_length=MAX_IDENTIFIER_LENGTH)
        question_type = self._text(data["question_type"], "question_type", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if question_type not in PRACTICE_QUESTION_TYPES:
            raise StateCommandError("Unsupported Practice question type")
        difficulty = self._integer(
            data["difficulty"],
            "difficulty",
            minimum=PRACTICE_DIFFICULTY_MIN,
            maximum=PRACTICE_DIFFICULTY_MAX,
        )
        sessions = progress.setdefault("practice_sessions", [])
        if not isinstance(sessions, list):
            raise StateCommandError("Existing Practice history is invalid", status_code=500)
        session_id = f"practice-{uuid.uuid4().hex}"
        now = _utc_now()
        session = {
            "session_id": session_id,
            "concept": concept,
            "question_type": question_type,
            "difficulty": difficulty,
            "status": "requested",
            "attempts": 0,
            "correct": 0,
            "started_at": now,
            "updated_at": now,
            "history": [],
        }
        sessions.append(session)
        progress["practice_sessions"] = sessions[-MAX_PRACTICE_SESSIONS:]
        return Mutation(
            True,
            {"session": self.practice_projection(progress)["sessions"][-1]},
            {
                "session_id": session_id,
                "concept": concept,
                "question_type": question_type,
                "difficulty": difficulty,
                "reason": "practice_session_started",
            },
        )

    def _practice_record_attempt(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Record a provider-validated Practice result, with no rewards."""

        data = self._payload(
            payload,
            {"session_id", "outcome", "evidence_id", "reason"},
            {"session_id", "outcome", "evidence_id", "reason"},
        )
        session_id = self._text(data["session_id"], "session_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        outcome = self._text(data["outcome"], "outcome", max_length=20, identifier=True)
        if outcome not in {"correct", "incorrect", "reviewed"}:
            raise StateCommandError("Practice outcome must be correct, incorrect or reviewed")
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        sessions = progress.get("practice_sessions")
        if not isinstance(sessions, list):
            raise StateCommandError("Existing Practice history is invalid", status_code=500)
        session = next((item for item in sessions if isinstance(item, dict) and item.get("session_id") == session_id), None)
        if session is None:
            raise StateCommandError("Practice session was not found", status_code=404)
        history = session.setdefault("history", [])
        if not isinstance(history, list):
            raise StateCommandError("Existing Practice attempt history is invalid", status_code=500)
        if any(isinstance(item, Mapping) and item.get("evidence_id") == evidence_id for item in history):
            return Mutation(False, {"session": self.practice_projection(progress)["sessions"][-1], "already_recorded": True})
        attempts = self._counter(session, "attempts")
        if attempts >= MAX_PRACTICE_ATTEMPTS_PER_SESSION:
            raise StateCommandError("Practice session attempt limit reached", status_code=409)
        # Seed hunter progress from history before this answer becomes history.
        self._hunter_state(progress)
        session["attempts"] = attempts + 1
        hunter_gain = None
        if outcome == "correct":
            session["correct"] = self._counter(session, "correct") + 1
            clean = not any(isinstance(item, Mapping) and item.get("outcome") == "incorrect" for item in history)
            hunter_gain = self._hunter_record(progress, concept=session.get("concept"), question_type=session.get("question_type"), source="tutor", clean=clean)
        session["status"] = "reviewed"
        session["updated_at"] = _utc_now()
        history.append({"outcome": outcome, "evidence_id": evidence_id, "reason": reason, "recorded_at": session["updated_at"]})
        session["history"] = history[-MAX_PRACTICE_ATTEMPTS_PER_SESSION:]
        projected = self.practice_projection(progress)
        safe_session = next(item for item in projected["sessions"] if item["session_id"] == session_id)
        return Mutation(
            True,
            {"session": safe_session, "outcome": outcome, "reward_xp": 0, "reward_coins": 0, "hunter_gain": hunter_gain},
            {
                "session_id": session_id,
                "outcome": outcome,
                "concept": str(session.get("concept") or "")[:120],
                "evidence_id": evidence_id,
                "reason": reason,
                "reward_xp": 0,
                "reward_coins": 0,
            },
        )

    def _advance_campaign(self, progress: dict[str, Any], cleared: dict[str, Any]) -> dict[str, Any] | None:
        """Close a cleared project and open the next one.

        The next project is the first unfinished one after the cleared
        project's order, wrapping back to any earlier project that was
        skipped. A project with no bounty board gets one seeded from
        campaign_bounties.json (first bounty open, the rest locked) so its
        boss can never unlock on an empty board.
        """

        cleared["status"] = "completed"
        projects = [item for item in progress.get("projects", []) if isinstance(item, dict)]

        def order(item: Mapping[str, Any]) -> int:
            value = item.get("order")
            return value if isinstance(value, int) else 0

        current_order = order(cleared)
        remaining = [
            item for item in projects
            if item is not cleared and item.get("completed") is not True and item.get("status") != "completed"
        ]
        remaining.sort(key=lambda item: (order(item) <= current_order, order(item)))
        upcoming = remaining[0] if remaining else None
        if upcoming is None:
            progress["current_quest"] = "Campaign complete: every project boss is defeated."
            return None

        upcoming.pop("boss_status", None)
        self._open_project(progress, upcoming)
        return upcoming

    @staticmethod
    def _open_project(progress: dict[str, Any], project: dict[str, Any]) -> None:
        """Make `project` the active one, seeding its bounty board from
        campaign_bounties.json if it has none (first bounty open, the rest
        locked). Existing mobs and progress are kept as they are."""

        bounties = load_campaign_bounties().get(str(project.get("branch") or ""), {})
        mobs = project.get("mobs")
        if not isinstance(mobs, list) or not mobs:
            seeded = [
                {"name": item["name"], "concept": item["concept"], "encounter": item["encounter"], "status": "locked"}
                for item in bounties.get("mobs", [])
                if isinstance(item, Mapping) and all(isinstance(item.get(key), str) for key in ("name", "concept", "encounter"))
            ]
            if seeded:
                seeded[0]["status"] = "available"
            project["mobs"] = seeded
        if isinstance(bounties.get("entry_file"), str):
            project.setdefault("entry_file", bounties["entry_file"])
        project["status"] = "active"
        project.setdefault("progress", 0)
        project.setdefault("clean_clear_eligible", True)
        project.setdefault("creative_discoveries", [])
        progress["current_quest"] = (
            f"{project.get('name') or project.get('branch')}: clear the bounty board, "
            f"then face {project.get('boss') or 'the boss'}."
        )

    def _select_campaign(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Switch the active campaign project. The project being left keeps
        its board, progress and boss state and can be picked up again later;
        cleared and locked projects cannot be selected."""

        data = self._payload(payload, {"branch"}, {"branch"})
        branch = self._text(data["branch"], "branch", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        projects = [item for item in progress.get("projects", []) if isinstance(item, dict)]
        target = next((item for item in projects if item.get("branch") == branch), None)
        if target is None:
            raise StateCommandError("That campaign does not exist", status_code=404)
        if target.get("status") == "completed" or target.get("completed") is True:
            raise StateCommandError("That campaign is already cleared", status_code=409)
        if target.get("status") == "locked":
            raise StateCommandError("That campaign is still locked", status_code=409)
        summary = {"project_id": self._project_id(target), "name": target.get("name"), "boss": target.get("boss"), "entry_file": target.get("entry_file")}
        if target.get("status") == "active":
            return Mutation(False, {"project": summary})
        previous = next((item for item in projects if item.get("status") == "active"), None)
        if previous is not None:
            previous["status"] = "available"
        self._open_project(progress, target)
        summary["entry_file"] = target.get("entry_file")
        event = {"reason": "campaign_selected", **summary}
        if previous is not None:
            event["previous_project_id"] = self._project_id(previous)
        return Mutation(True, {"project": summary}, event)

    @staticmethod
    def _boss_is_active(progress: Mapping[str, Any]) -> bool:
        projects = progress.get("projects")
        if not isinstance(projects, list):
            return False
        project = next((p for p in projects if isinstance(p, Mapping) and p.get("status") == "active"), None)
        if not project or project.get("completed") is True or project.get("boss_status") == "defeated":
            return False
        validation = project.get("boss_validation")
        history = validation.get("history", []) if isinstance(validation, Mapping) else []
        if not isinstance(history, list):
            return False
        marker = next((entry.get("requirement_id") for entry in reversed(history) if isinstance(entry, Mapping) and entry.get("requirement_id") in {"boss_begin", "boss_retreat"}), None)
        return marker == "boss_begin"

    @staticmethod
    def _boss_history(project: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        validation = project.get("boss_validation")
        if not isinstance(validation, dict):
            validation = {"verified": [], "history": []}
            project["boss_validation"] = validation
        history = validation.setdefault("history", [])
        validation.setdefault("verified", [])
        if not isinstance(history, list) or not isinstance(validation.get("verified"), list):
            raise StateCommandError("Existing boss validation state is invalid", status_code=500)
        return validation, history

    def _boss_start(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        self._payload(payload, set(), set())
        project = next((p for p in progress.get("projects", []) if isinstance(p, dict) and p.get("status") == "active"), None)
        if not project or project.get("completed") is True or project.get("boss_status") == "defeated":
            raise StateCommandError("No boss is available", status_code=409)
        mobs = project.get("mobs")
        if not isinstance(mobs, list) or not mobs or any(not isinstance(m, dict) or m.get("status") not in {"defeated", "cleared"} for m in mobs):
            raise StateCommandError("Clear the bounties before fighting the boss", status_code=409)
        self._unlock_boss_if_cleared(project)
        if project.get("boss_status") != "available":
            raise StateCommandError("The boss is not available", status_code=409)
        if self._boss_is_active(progress):
            return Mutation(False, {"boss_active": True})
        validation, history = self._boss_history(project)
        history.append({"requirement_id": "boss_begin", "evidence_id": uuid.uuid4().hex, "recorded_at": _utc_now()})
        self._trim_boss_history(project, validation, history)
        return Mutation(True, {"boss_active": True}, {"project_id": self._project_id(project), "boss_name": str(project.get("boss") or "")})

    @staticmethod
    def _trim_boss_history(project: Mapping[str, Any], validation: dict[str, Any], history: list[dict[str, Any]]) -> None:
        # Keep the first special-mechanic award across retreats so it cannot be farmed.
        special = campaign_special_mechanic(project)
        first_award = next((entry for entry in history if isinstance(entry, dict) and special and entry.get("requirement_id") == special["trigger"]), None)
        tail = history[-19:] if first_award and first_award not in history[-20:] else history[-20:]
        validation["history"] = ([first_award] + tail) if first_award and first_award not in tail else tail

    def _boss_retreat(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        self._payload(payload, set(), set())
        if not self._boss_is_active(progress):
            return Mutation(False, {"boss_active": False, "reset": False})
        project = next(p for p in progress["projects"] if isinstance(p, dict) and p.get("status") == "active")
        validation, history = self._boss_history(project)
        validation["verified"] = []
        history.append({"requirement_id": "boss_retreat", "recorded_at": _utc_now()})
        self._trim_boss_history(project, validation, history)
        return Mutation(True, {"boss_active": False, "reset": True}, {"project_id": self._project_id(project), "boss_name": str(project.get("boss") or "")})

    @staticmethod
    def _unlock_boss_if_cleared(project: dict[str, Any]) -> None:
        """Match the encounter projection: a cleared board with no stored boss
        status (for example after a cloud sync dropped it) means the boss is
        available. Callers have already checked every mob is resolved."""

        if not project.get("boss_status") and project.get("completed") is not True:
            project["boss_status"] = "available"

    def _record_boss_requirement(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Persist one provider-validated boss phase before the final clear."""

        data = self._payload(payload, {"requirement_id", "evidence_id", "reason"}, {"requirement_id", "evidence_id", "reason"})
        requirement_id = self._text(data["requirement_id"], "requirement_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if requirement_id not in BOSS_REQUIREMENTS:
            raise StateCommandError("Unsupported boss requirement")
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")

        projects = progress.get("projects")
        if not isinstance(projects, list):
            raise StateCommandError("Existing state field projects is invalid", status_code=500)
        project = next((item for item in projects if isinstance(item, dict) and item.get("status") == "active"), None)
        if project is None:
            raise StateCommandError("No active project is available", status_code=409)
        mobs = project.get("mobs")
        if not isinstance(mobs, list) or not all(isinstance(item, dict) for item in mobs):
            raise StateCommandError("Existing active project mobs are invalid", status_code=500)
        if any(item.get("status") not in {"defeated", "cleared"} for item in mobs):
            raise StateCommandError("The active project still has unresolved mobs", status_code=409)
        self._unlock_boss_if_cleared(project)
        if project.get("boss_status") not in {"available", "defeated"}:
            raise StateCommandError("The project boss is not unlocked yet", status_code=409)

        validation = project.get("boss_validation")
        if not isinstance(validation, dict):
            validation = {"verified": [], "history": []}
            project["boss_validation"] = validation
        verified = validation.get("verified")
        history = validation.get("history")
        if not isinstance(verified, list) or not isinstance(history, list):
            raise StateCommandError("Existing boss validation state is invalid", status_code=500)
        gauntlet = boss_gauntlet(project)
        if requirement_id not in gauntlet:
            raise StateCommandError("That goal is not part of this boss fight", status_code=409)
        verified = [item for item in verified if item in gauntlet]
        validation["verified"] = verified
        if requirement_id in verified:
            projection = self._boss_validation_projection(project)
            return Mutation(
                False,
                {
                    "already_verified": True,
                    "requirement_id": requirement_id,
                    **projection,
                },
            )

        before_projection = self._boss_validation_projection(project)
        current_goal = before_projection.get("boss_phase")
        if current_goal in gauntlet and requirement_id != current_goal:
            raise StateCommandError(
                f"The current boss goal is {current_goal}; verify goals in order",
                status_code=409,
            )

        verified.append(requirement_id)
        special = campaign_special_mechanic(project)
        already_awarded = any(isinstance(entry, dict) and entry.get("requirement_id") == requirement_id for entry in history)
        mechanic_reward = apply_campaign_mechanic(progress, None, special) if special and special["trigger"] == requirement_id and not already_awarded else None
        validation["verified"] = [item for item in gauntlet if item in verified]
        history.append(
            {
                "requirement_id": requirement_id,
                "evidence_id": evidence_id,
                "reason": reason,
                "recorded_at": _utc_now(),
            }
        )
        self._trim_boss_history(project, validation, history)
        projection = self._boss_validation_projection(project)
        current_spec = BOSS_REQUIREMENT_SPECS.get(requirement_id, {})
        try:
            boss_damage = max(1, min(MAX_IMPACT, int(current_spec.get("impact", 1))))
        except (TypeError, ValueError):
            boss_damage = 1
        result = {
            "boss_requirement_verified": True,
            "mechanic_reward": mechanic_reward,
            "requirement_id": requirement_id,
            "evidence_id": evidence_id,
            "reason": reason,
            "boss_damage": boss_damage,
            "boss_resolve_before": before_projection.get("boss_resolve", 0),
            "boss_resolve_after": projection.get("boss_resolve", 0),
            **projection,
        }
        return Mutation(
            True,
            result,
            {
                "project_id": self._project_id(project),
                "boss_name": str(project.get("boss") or ""),
                **result,
            },
        )

    def _record_boss_clear(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Record a boss victory after trusted, evidence-backed validation.

        The local provider bridge is still a trusted workstation boundary, so
        this command is deliberately internal-only.  It accepts evidence IDs
        and a bounded explanation, never caller-selected rewards, Impact or
        level values.  A final mob clear only opens the boss gate; this command
        is the sole path that can award the canonical boss reward.
        """

        data = self._payload(
            payload,
            {"evidence_id", "explanation_evidence_id", "interview_evidence_id", "reason"},
            {"evidence_id", "explanation_evidence_id", "interview_evidence_id", "reason"},
        )
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        explanation_evidence_id = self._text(
            data["explanation_evidence_id"],
            "explanation_evidence_id",
            max_length=MAX_IDENTIFIER_LENGTH,
            identifier=True,
        )
        interview_evidence_id = self._text(
            data["interview_evidence_id"],
            "interview_evidence_id",
            max_length=MAX_IDENTIFIER_LENGTH,
            identifier=True,
        )
        reason = self._text(data["reason"], "reason")

        projects = progress.get("projects")
        if not isinstance(projects, list):
            raise StateCommandError("Existing state field projects is invalid", status_code=500)
        project = next((item for item in projects if isinstance(item, dict) and item.get("status") == "active"), None)
        if project is None:
            raise StateCommandError("No active project is available", status_code=409)
        mobs = project.get("mobs")
        if not isinstance(mobs, list) or not all(isinstance(item, dict) for item in mobs):
            raise StateCommandError("Existing active project mobs are invalid", status_code=500)
        if any(item.get("status") not in {"defeated", "cleared"} for item in mobs):
            raise StateCommandError("The active project still has unresolved mobs", status_code=409)
        boss_name = self._text(project.get("boss") or "", "boss_name", max_length=MAX_IDENTIFIER_LENGTH)
        # Display text, not a path: real names include "Guess Who / Detective Game".
        project_name = self._campaign_text(project.get("name") or project.get("branch") or "project", "project_name")
        if project.get("boss_status") == "defeated" or project.get("completed") is True:
            return Mutation(
                False,
                {
                    "already_cleared": True,
                    "boss_name": boss_name,
                    "project_name": project_name,
                },
            )
        self._unlock_boss_if_cleared(project)
        if project.get("boss_status") != "available":
            raise StateCommandError("The project boss is not unlocked yet", status_code=409)

        player = self._dict(progress, "player")
        reward = self._grant_reward(player, 100, 0)
        stats = self._dict(progress, "stats")
        stats["projects_cleared"] = self._counter(stats, "projects_cleared") + 1
        self._log_activity(progress, "bosses")
        stats["bosses_defeated"] = self._counter(stats, "bosses_defeated") + 1
        project["progress"] = 100
        project["completed"] = True
        project["boss_status"] = "defeated"
        completed_at = _utc_now()
        project["completed_at"] = completed_at
        project["boss_clear"] = {
            "evidence_id": evidence_id,
            "explanation_evidence_id": explanation_evidence_id,
            "interview_evidence_id": interview_evidence_id,
            "recorded_at": completed_at,
        }
        validation = project.get("boss_validation")
        if not isinstance(validation, dict):
            validation = {"verified": [], "history": []}
            project["boss_validation"] = validation
        validation["verified"] = list(boss_gauntlet(project))
        validation["completed_at"] = completed_at
        boss_loot = self._armory_boss_loot(progress, project)

        clean_clear = bool(project.get("clean_clear_eligible"))
        assist = progress.get("assist")
        if isinstance(assist, dict) and str(assist.get("mode") or "").casefold() in {"reference", "guided", "assisted"}:
            clean_clear = False
        if any(str(item.get("assist") or "clean").casefold() in {"reference", "guided", "assisted"} for item in mobs):
            clean_clear = False
        if clean_clear:
            project["clean_clear"] = True
            stats["clean_clears"] = self._counter(stats, "clean_clears") + 1

        unlocked_achievements: list[str] = []
        achievements = progress.get("achievements")
        if isinstance(achievements, list):
            for achievement_name in ("Housebreaker", "Clean Clear") if clean_clear else ("Housebreaker",):
                match = next(
                    (
                        item
                        for item in achievements
                        if isinstance(item, dict) and item.get("name") == achievement_name
                    ),
                    None,
                )
                if match is not None and match.get("unlocked") is not True:
                    match["unlocked"] = True
                    unlocked_achievements.append(achievement_name)

        goals = progress.get("goals")
        if isinstance(goals, dict):
            for goal in goals.get("long_term", []):
                if isinstance(goal, dict) and goal.get("id") == "first-boss":
                    goal["done"] = True

        companion = progress.get("companion")
        companion_form_before = None
        companion_form_after = None
        companion_level_before = None
        companion_level_after = None
        if isinstance(companion, dict):
            companion_form_before = str(companion.get("form") or "")
            companion_level_before = self._counter(companion, "level")
            companion["bond"] = self._counter(companion, "bond") + 1
            if companion_form_before == "Tiny Code-Flame":
                companion["form"] = "Ember Sprite"
                companion["level"] = max(2, companion_level_before)
                companion["next_form"] = "Runic Familiar"
                companion["next_form_requirement"] = "Earn 3 Mastery Shields"
            companion_form_after = str(companion.get("form") or companion_form_before)
            companion_level_after = self._counter(companion, "level")

        upcoming = self._advance_campaign(progress, project)
        next_project = (
            {"project_id": self._project_id(upcoming), "name": upcoming.get("name"), "boss": upcoming.get("boss"), "entry_file": upcoming.get("entry_file")}
            if upcoming
            else None
        )

        return Mutation(
            True,
            {
                "boss_defeated": True,
                "project_completed": True,
                "loot": boss_loot,
                "boss_name": boss_name,
                "project_name": project_name,
                "reward_xp": 100,
                "reward_coins": 0,
                "boss_reward_xp": 100,
                "boss_reward_coins": 0,
                "level_before": reward["level_before"],
                "level_after": reward["level_after"],
                "achievement_unlocked": unlocked_achievements[0] if unlocked_achievements else None,
                "achievements_unlocked": unlocked_achievements,
                "clean_clear": clean_clear,
                "companion_form_before": companion_form_before,
                "companion_form_after": companion_form_after,
                "companion_level_before": companion_level_before,
                "companion_level_after": companion_level_after,
                "evidence_id": evidence_id,
                "explanation_evidence_id": explanation_evidence_id,
                "interview_evidence_id": interview_evidence_id,
                "reason": reason,
                "boss_phase": "complete",
                "boss_phase_label": "Boss clear",
                "verified_boss_requirements": list(validation["verified"]),
                "next_project": next_project,
                "campaign_complete": next_project is None,
            },
            {
                "project_id": self._project_id(project),
                "project_name": project_name,
                "boss_name": boss_name,
                "boss_defeated": True,
                "project_completed": True,
                "loot": boss_loot,
                "next_project_name": next_project["name"] if next_project else None,
                "reward_xp": 100,
                "reward_coins": 0,
                "boss_reward_xp": 100,
                "boss_reward_coins": 0,
                "level_before": reward["level_before"],
                "level_after": reward["level_after"],
                "achievement_unlocked": unlocked_achievements[0] if unlocked_achievements else None,
                "achievements_unlocked": unlocked_achievements,
                "clean_clear": clean_clear,
                "companion_form_before": companion_form_before,
                "companion_form_after": companion_form_after,
                "companion_level_before": companion_level_before,
                "companion_level_after": companion_level_after,
                "evidence_id": evidence_id,
                "explanation_evidence_id": explanation_evidence_id,
                "interview_evidence_id": interview_evidence_id,
                "reason": reason,
                "boss_phase": "complete",
                "boss_phase_label": "Boss clear",
                "verified_boss_requirements": list(validation["verified"]),
            },
        )

    def _record_battle_miss(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(
            payload,
            {"raw_damage", "mob_index", "reason", "encounter_id", "objective_id", "evidence_id"},
            {"reason", "encounter_id"},
        )
        reason = self._text(data["reason"], "reason")
        encounter_id = self._text(data["encounter_id"], "encounter_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        evidence_id = self._text(data.get("evidence_id", encounter_id), "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        objective_id = None
        question_type = None
        mob_name = None
        raw_damage = None
        encounter = None
        if data.get("objective_id") is not None:
            objective_id = self._text(data["objective_id"], "objective_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
            project, mobs, index, mob = self._active_project_and_mob(progress)
            raw_damage = canonical_battle_raw_damage(index)
            profile = self._encounter_profile(index, project, mob)
            objective = profile["objectives"].get(objective_id)
            if objective is None:
                raise StateCommandError("This Battle objective is not defined for the active encounter")
            encounter = self._ensure_encounter_state(progress, project, mob, index)
            completed = encounter.get("completed_objectives")
            if not isinstance(completed, list):
                raise StateCommandError("Existing encounter objective history is invalid", status_code=500)
            if objective_id in completed:
                raise StateCommandError("This encounter objective has already been verified", status_code=409)
            question_type = str(objective["question_type"])
            encounter["attempts"] = self._counter(encounter, "attempts") + 1
            encounter["last_objective_id"] = objective_id
            encounter["last_question_type"] = question_type
            encounter["last_outcome"] = "incorrect"
            # Remembered so a later correct answer counts as recovered, not clean.
            missed = encounter.setdefault("missed_objectives", [])
            if isinstance(missed, list) and objective_id not in missed:
                missed.append(objective_id)
                encounter["missed_objectives"] = missed[-20:]
            question_types = encounter.setdefault("question_types", [])
            if question_type not in question_types:
                question_types.append(question_type)
            mob["objective_attempts"] = self._counter(mob, "objective_attempts") + 1
            mob_name = str(mob.get("name") or "")
            entry = self._upsert_codex_entry(
                progress,
                project,
                mob,
                question_type=question_type,
                outcome="incorrect",
                evidence_id=evidence_id,
                note=reason,
            )
            entry["status"] = "observed"
        elif data.get("raw_damage") is not None:
            raw_damage = self._integer(data["raw_damage"], "raw_damage", minimum=1, maximum=28)
        elif data.get("mob_index") is not None:
            raw_damage = canonical_battle_raw_damage(self._integer(data["mob_index"], "mob_index", minimum=0, maximum=1000))
        else:
            raise StateCommandError("raw_damage or mob_index is required")
        player = self._dict(progress, "player")
        effects = self._gear_effects(progress)
        buff_reduction = int(((encounter or {}).get("buffs") or {}).get("reduction", 0)) if isinstance(encounter, dict) else 0
        armor_reduction = min(ARMORY_REDUCTION_CAP, effects["reduction"] + buff_reduction)
        damage = max(1, (raw_damage * (100 - armor_reduction) + 99) // 100)
        if objective_id and isinstance(encounter, dict):
            special = campaign_special_mechanic(project, mob_name)
            if special and special["reward"] == "shelter" and special["trigger"] in encounter.get("completed_objectives", []):
                damage = max(1, damage - 3)
        prevented_damage = 0
        trinket_trigger = None
        revived = False
        guard_used = False
        ward_used = False
        trinket_name = str((progress.get("equipment") or {}).get("trinket") or "")
        trinket_triggers = encounter.setdefault("trinket_triggers", []) if isinstance(encounter, dict) else []
        if not isinstance(trinket_triggers, list):
            raise StateCommandError("Existing encounter trinket history is invalid", status_code=500)
        if isinstance(encounter, dict) and self._counter(encounter, "guards") > 0:
            # A banked free mistake (Guard Break, trinket or food) takes the hit.
            encounter["guards"] = self._counter(encounter, "guards") - 1
            prevented_damage, damage, guard_used = damage, 0, True
        elif self._spend_aid(progress, "wards"):
            # A Ward Shield the hunter armed takes this wrong answer.
            prevented_damage, damage, ward_used = damage, 0, True
        elif trinket_name == "Guardian Sigil" and "guardian-sigil:counterattack" not in trinket_triggers:
            prevented_damage = damage
            damage = 0
            trinket_triggers.append("guardian-sigil:counterattack")
            trinket_trigger = "Guardian Sigil"
        elif (effects["first_miss_free"] or effects["block_first_miss"]) and "armory:first-miss" not in trinket_triggers:
            prevented_damage = damage
            damage = 0
            trinket_triggers.append("armory:first-miss")
            trinket_trigger = effects["first_miss_source"]
        maximum = self._counter(player, "max_hp")
        current = self._counter(player, "hp")
        updated = max(0, current - damage)
        if updated == 0 and trinket_name == "Phoenix Ember" and "phoenix-ember:revive" not in trinket_triggers:
            updated = 1
            trinket_triggers.append("phoenix-ember:revive")
            revived = True
            trinket_trigger = "Phoenix Ember"
        elif updated == 0 and effects["revive"] and "armory:revive" not in trinket_triggers:
            updated = 1
            trinket_triggers.append("armory:revive")
            revived = True
            trinket_trigger = trinket_name
        player["hp"] = updated
        return Mutation(
            True,
            {
                "hp": updated,
                "max_hp": maximum,
                "damage": damage,
                "prevented_damage": prevented_damage,
                "trinket_trigger": trinket_trigger,
                "revived": revived,
                "guard_used": guard_used,
                "ward_used": ward_used,
                "wards_left": self.aid_charges(progress)["wards"],
                "guards": self._counter(encounter, "guards") if isinstance(encounter, dict) else 0,
                "mob_name": mob_name,
                "objective_id": objective_id,
                "question_type": question_type,
            },
            {
                "raw_damage": raw_damage,
                "damage": damage,
                "prevented_damage": prevented_damage,
                "trinket_trigger": trinket_trigger,
                "ward_used": ward_used,
                "revived": revived,
                "hp_before": current,
                "hp_after": updated,
                "encounter_id": encounter_id,
                "evidence_id": evidence_id,
                "mob_name": mob_name,
                "objective_id": objective_id,
                "question_type": question_type,
                "reason": reason,
            },
        )

    def _player_hp_change(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"amount", "reason", "encounter_id"}, {"amount", "reason", "encounter_id"})
        amount = self._integer(data["amount"], "amount", minimum=-MAX_HP_DELTA, maximum=MAX_HP_DELTA)
        if amount == 0:
            raise StateCommandError("amount must not be zero")
        reason = self._text(data["reason"], "reason")
        encounter_id = self._text(data["encounter_id"], "encounter_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        player = self._dict(progress, "player")
        maximum = self._counter(player, "max_hp")
        current = self._counter(player, "hp")
        updated = max(0, min(maximum, current + amount))
        if updated == current:
            return Mutation(False, {"hp": current, "max_hp": maximum})
        player["hp"] = updated
        return Mutation(
            True,
            {"hp": updated, "max_hp": maximum},
            {"amount": updated - current, "requested_amount": amount, "encounter_id": encounter_id, "reason": reason},
        )

    def _record_achievement(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"achievement_id", "reason", "evidence_id"}, {"achievement_id", "reason", "evidence_id"})
        achievement_id = self._text(data["achievement_id"], "achievement_id", max_length=MAX_IDENTIFIER_LENGTH)
        reason = self._text(data["reason"], "reason")
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        achievements = progress.get("achievements")
        if not isinstance(achievements, list):
            raise StateCommandError("Existing state field achievements is invalid", status_code=500)
        match = next(
            (item for item in achievements if isinstance(item, dict) and (item.get("id") == achievement_id or item.get("name") == achievement_id)),
            None,
        )
        if match is None:
            raise StateCommandError("Unknown achievement", status_code=404)
        if match.get("unlocked") is True:
            return Mutation(False, {"achievement_id": achievement_id, "already_unlocked": True})
        match["unlocked"] = True
        return Mutation(
            True,
            {"achievement_id": achievement_id, "unlocked": True},
            {"achievement_id": achievement_id, "evidence_id": evidence_id, "reason": reason},
        )

    @staticmethod
    def _legacy_text(value: object, field: str, *, max_length: int = MAX_REASON_LENGTH) -> str:
        """Validate human-readable migration evidence without treating punctuation as a path."""

        if not isinstance(value, str):
            raise StateCommandError(f"{field} must be text")
        normalized = value.strip()
        if not normalized or len(normalized) > max_length or any(ord(character) < 32 for character in normalized):
            raise StateCommandError(f"{field} must be bounded text without control characters")
        return normalized

    def _reconcile_codex_entry(
        self,
        progress: dict[str, Any],
        project: Mapping[str, Any],
        mob: Mapping[str, Any],
        *,
        evidence_id: str,
    ) -> tuple[dict[str, Any], bool]:
        """Record only that an evidence-backed encounter was reached and cleared.

        Legacy saves did not retain question/attempt histories.  This helper
        therefore never fabricates those fields or a mastery shield; it only
        creates the bounded encounter identity/concept and an auditable clear
        result tied to the supplied evidence id.
        """

        project_id = self._project_id(project)
        mob_name = self._text(mob.get("name", ""), "mob_name", max_length=MAX_IDENTIFIER_LENGTH)
        concept = self._legacy_text(mob.get("concept") or "Unknown concept", "concept")
        _, entries = self._codex_container(progress)
        entry = next(
            (item for item in entries if item.get("project_id") == project_id and item.get("mob_name") == mob_name),
            None,
        )
        changed = False
        if entry is None:
            entry = {
                "id": f"{project_id}-{re.sub(r'[^A-Za-z0-9._-]+', '-', mob_name)[:80]}",
                "project_id": project_id,
                "mob_name": mob_name,
                "concept": concept,
                "status": "defeated",
                "question_types": [],
                "weaknesses": [],
                "notes": [],
                "attempts": 0,
                "results": [],
                "interview_history": [],
                "mastery": {"evidence": 0, "interview_passes": 0, "shield": "none"},
            }
            entries.append(entry)
            if len(entries) > MAX_CODEX_RECORDS:
                del entries[:-MAX_CODEX_RECORDS]
            changed = True
        if entry.get("concept") != concept:
            entry["concept"] = concept
            changed = True
        if entry.get("status") != "defeated":
            entry["status"] = "defeated"
            changed = True

        results = entry.setdefault("results", [])
        if not isinstance(results, list):
            raise StateCommandError("Existing Codex result history is invalid", status_code=500)
        if not any(isinstance(item, dict) and item.get("evidence_id") == evidence_id for item in results):
            results.append({"outcome": "defeated", "evidence_id": evidence_id})
            entry["results"] = results[-20:]
            changed = True

        note = "Encounter clear confirmed by approved legacy session evidence; attempts and exact rewards were not inferred."
        notes = entry.setdefault("notes", [])
        if not isinstance(notes, list):
            raise StateCommandError("Existing Codex notes are invalid", status_code=500)
        if note not in notes:
            notes.append(note)
            entry["notes"] = notes[-20:]
            changed = True
        entry.setdefault("question_types", [])
        entry.setdefault("weaknesses", [])
        entry.setdefault("interview_history", [])
        entry.setdefault("mastery", {"evidence": 0, "interview_passes": 0, "shield": "none"})
        return entry, changed

    def _reconcile_legacy_progress(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        """Apply an explicitly approved, evidence-bounded legacy save migration.

        This is intentionally an internal-only command.  It accepts selected
        facts that a human reviewed from the legacy report/session evidence,
        never a legacy snapshot.  Player counters may move only from the
        untouched defaults to the reviewed values (or remain idempotent), so a
        later legitimate local save cannot be silently overwritten.
        """

        allowed = {
            "evidence_id",
            "source",
            "reason",
            "level",
            "xp",
            "xp_next",
            "lifetime_xp",
            "coins",
            "defeated_mobs",
            "project_progress",
            "sessions",
            "explanations",
            "streak_current",
            "streak_longest",
            "streak_last_active",
            "streak_days_logged",
            "daily_goal_ids",
            "weekly_goal_progress",
            "current_quest",
            "last_session",
        }
        required = {
            "evidence_id",
            "source",
            "reason",
            "level",
            "xp",
            "lifetime_xp",
            "coins",
            "defeated_mobs",
            "project_progress",
        }
        data = self._payload(payload, allowed, required)
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        source = self._text(data["source"], "source", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        level = self._integer(data["level"], "level", minimum=1, maximum=MAX_SYNC_LEVEL)
        xp = self._integer(data["xp"], "xp", minimum=0, maximum=MAX_SYNC_COUNTER)
        lifetime_xp = self._integer(data["lifetime_xp"], "lifetime_xp", minimum=0, maximum=MAX_SYNC_COUNTER)
        coins = self._integer(data["coins"], "coins", minimum=0, maximum=MAX_SYNC_COUNTER)
        xp_next = self._integer(data.get("xp_next", 100), "xp_next", minimum=1, maximum=MAX_SYNC_COUNTER)
        if xp >= xp_next:
            raise StateCommandError("xp must be below xp_next for a reconciled level")
        project_progress = self._integer(data["project_progress"], "project_progress", minimum=0, maximum=100)

        raw_defeated = data["defeated_mobs"]
        if not isinstance(raw_defeated, list) or not raw_defeated:
            raise StateCommandError("defeated_mobs must contain at least one reviewed encounter")
        if len(raw_defeated) > MAX_SYNC_LIST_ITEMS:
            raise StateCommandError("defeated_mobs contains too many entries")
        defeated_names = [
            self._text(item, "defeated_mob", max_length=MAX_IDENTIFIER_LENGTH)
            for item in raw_defeated
        ]
        if len(set(defeated_names)) != len(defeated_names):
            raise StateCommandError("defeated_mobs must not contain duplicates")

        project, mobs, _next_index, next_mob = self._active_project_and_mob(progress)
        project_id = self._project_id(project)
        mob_names = [self._text(item.get("name", ""), "mob_name", max_length=MAX_IDENTIFIER_LENGTH) for item in mobs]
        expected_prefix = mob_names[: len(defeated_names)]
        if defeated_names != expected_prefix:
            raise StateCommandError("defeated_mobs must be the contiguous active-quest prefix")

        # A player counter with any non-default, non-target value represents a
        # possible newer local session.  Refuse the migration instead of
        # choosing a timestamp or silently replacing it.
        player = self._dict(progress, "player")
        defaults = {"level": 1, "xp": 0, "xp_next": 100, "lifetime_xp": 0, "coins": 0}
        targets = {"level": level, "xp": xp, "xp_next": xp_next, "lifetime_xp": lifetime_xp, "coins": coins}
        player_conflicts = []
        for field, target in targets.items():
            current = self._counter(player, field)
            if current not in {defaults[field], target}:
                player_conflicts.append(field)
        if player_conflicts:
            raise StateCommandError(
                "Canonical player progress differs from the reviewed legacy target: "
                + ", ".join(player_conflicts),
                status_code=409,
            )

        changed = False
        restored_fields: list[str] = []
        player_level_changed = False
        for field, target in targets.items():
            if self._counter(player, field) != target:
                player[field] = target
                changed = True
                restored_fields.append(f"player.{field}")
                player_level_changed = player_level_changed or field == "level"

        stats = self._dict(progress, "stats")
        stat_targets = {
            "sessions": data.get("sessions"),
            "explanations": data.get("explanations"),
            "mobs_defeated": len(defeated_names),
        }
        for field, raw_target in stat_targets.items():
            if raw_target is None:
                continue
            target = self._integer(raw_target, field, minimum=0, maximum=MAX_SYNC_COUNTER)
            current = self._counter(stats, field)
            if current < target:
                stats[field] = target
                changed = True
                restored_fields.append(f"stats.{field}")

        # Preserve any later clear that is already in canonical state, but
        # never allow this migration to unlock a non-prefix encounter.
        later_conflicts = []
        for index, mob in enumerate(mobs):
            status = str(mob.get("status") or "locked")
            if index >= len(defeated_names) and status in {"defeated", "cleared"}:
                later_conflicts.append(str(mob.get("name") or index))
        if later_conflicts:
            raise StateCommandError(
                "Canonical encounter history is ahead of the reviewed legacy evidence: "
                + ", ".join(later_conflicts),
                status_code=409,
            )
        for index, mob in enumerate(mobs[: len(defeated_names)]):
            if mob.get("status") != "defeated":
                mob["status"] = "defeated"
                changed = True
                restored_fields.append(f"projects.{project_id}.mobs.{index}.status")
            if mob.get("resolve") != 0:
                mob["resolve"] = 0
                changed = True
                restored_fields.append(f"projects.{project_id}.mobs.{index}.resolve")

        current_project_progress = self._integer(project.get("progress", 0), "project.progress", minimum=0, maximum=100)
        if current_project_progress < project_progress:
            project["progress"] = project_progress
            changed = True
            restored_fields.append(f"projects.{project_id}.progress")

        next_name: str | None = None
        encounter_projection: dict[str, Any] | None = None
        if len(defeated_names) < len(mobs):
            next_mob = mobs[len(defeated_names)]
            next_name = str(next_mob.get("name") or "")
            if next_mob.get("status") == "locked":
                next_mob["status"] = "available"
                changed = True
                restored_fields.append(f"projects.{project_id}.mobs.{len(defeated_names)}.status")
            elif next_mob.get("status") not in {"available"}:
                raise StateCommandError("Canonical next encounter conflicts with the reviewed legacy state", status_code=409)
            existing_encounter = progress.get("encounter_state")
            if (
                isinstance(existing_encounter, dict)
                and existing_encounter.get("status") != "defeated"
                and existing_encounter.get("mob_name") not in {None, next_name}
            ):
                raise StateCommandError("Canonical active encounter conflicts with the reviewed legacy state", status_code=409)
            self._ensure_encounter_state(progress, project, next_mob, len(defeated_names))
            encounter_projection = self.encounter_projection(progress)
            if not isinstance(existing_encounter, dict) or existing_encounter.get("mob_name") != next_name:
                changed = True
                restored_fields.append("encounter_state")

        codex_ids: list[str] = []
        for mob in mobs[: len(defeated_names)]:
            entry, entry_changed = self._reconcile_codex_entry(progress, project, mob, evidence_id=evidence_id)
            codex_ids.append(str(entry["id"]))
            changed = changed or entry_changed
            if entry_changed:
                restored_fields.append(f"codex.{entry['id']}")

        achievement_unlocked = None
        achievements = progress.get("achievements")
        if not isinstance(achievements, list):
            raise StateCommandError("Existing state field achievements is invalid", status_code=500)
        first_blood = next((item for item in achievements if isinstance(item, dict) and item.get("name") == "First Blood"), None)
        if first_blood is not None and first_blood.get("unlocked") is not True:
            first_blood["unlocked"] = True
            achievement_unlocked = "First Blood"
            changed = True
            restored_fields.append("achievements.First Blood")

        streak_fields = {"streak_current", "streak_longest", "streak_last_active", "streak_days_logged"}
        if any(field in data for field in streak_fields):
            streak = self._dict(progress, "streak")
            for field in ("streak_current", "streak_longest"):
                if field not in data:
                    continue
                target = self._integer(data[field], field, minimum=0, maximum=MAX_SYNC_COUNTER)
                current = self._counter(streak, "current" if field == "streak_current" else "longest")
                if current < target:
                    streak["current" if field == "streak_current" else "longest"] = target
                    changed = True
                    restored_fields.append(f"streak.{field.removeprefix('streak_')}")
            if "streak_last_active" in data:
                last_active = self._legacy_text(data["streak_last_active"], "streak_last_active", max_length=10)
                if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_active):
                    raise StateCommandError("streak_last_active must use YYYY-MM-DD")
                if not streak.get("last_active"):
                    streak["last_active"] = last_active
                    changed = True
                    restored_fields.append("streak.last_active")
            if "streak_days_logged" in data:
                raw_days = data["streak_days_logged"]
                if not isinstance(raw_days, list) or len(raw_days) > MAX_SYNC_LIST_ITEMS:
                    raise StateCommandError("streak_days_logged must be a bounded list")
                days = []
                for day in raw_days:
                    value = self._legacy_text(day, "streak_day", max_length=10)
                    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                        raise StateCommandError("streak_days_logged must use YYYY-MM-DD")
                    if value not in days:
                        days.append(value)
                existing_days = streak.get("days_logged")
                if not isinstance(existing_days, list):
                    existing_days = []
                merged_days = list(dict.fromkeys([str(day) for day in existing_days] + days))[-MAX_SYNC_LIST_ITEMS:]
                if merged_days != existing_days:
                    streak["days_logged"] = merged_days
                    changed = True
                    restored_fields.append("streak.days_logged")

        if "daily_goal_ids" in data:
            raw_goal_ids = data["daily_goal_ids"]
            if not isinstance(raw_goal_ids, list) or len(raw_goal_ids) > MAX_SYNC_LIST_ITEMS:
                raise StateCommandError("daily_goal_ids must be a bounded list")
            goals = self._dict(progress, "goals")
            daily = goals.get("daily")
            if not isinstance(daily, list):
                raise StateCommandError("Existing daily goals are invalid", status_code=500)
            daily_by_id = {str(item.get("id")): item for item in daily if isinstance(item, dict) and item.get("id")}
            for raw_id in raw_goal_ids:
                goal_id = self._text(raw_id, "daily_goal_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
                goal = daily_by_id.get(goal_id)
                if goal is None:
                    raise StateCommandError(f"Unknown daily goal: {goal_id}", status_code=404)
                if goal.get("done") is not True:
                    goal["done"] = True
                    changed = True
                    restored_fields.append(f"goals.daily.{goal_id}")

        if "weekly_goal_progress" in data:
            raw_updates = data["weekly_goal_progress"]
            if not isinstance(raw_updates, list) or len(raw_updates) > MAX_SYNC_LIST_ITEMS:
                raise StateCommandError("weekly_goal_progress must be a bounded list")
            goals = self._dict(progress, "goals")
            weekly = goals.get("weekly")
            if not isinstance(weekly, list):
                raise StateCommandError("Existing weekly goals are invalid", status_code=500)
            weekly_by_id = {str(item.get("id")): item for item in weekly if isinstance(item, dict) and item.get("id")}
            for update in raw_updates:
                if not isinstance(update, Mapping) or set(update) != {"id", "progress"}:
                    raise StateCommandError("weekly_goal_progress entries must contain only id and progress")
                goal_id = self._text(update["id"], "weekly_goal_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
                goal = weekly_by_id.get(goal_id)
                if goal is None:
                    raise StateCommandError(f"Unknown weekly goal: {goal_id}", status_code=404)
                target = self._integer(update["progress"], "weekly_goal_progress", minimum=0, maximum=MAX_SYNC_COUNTER)
                current = self._counter(goal, "progress")
                if current < target:
                    goal["progress"] = target
                    target_goal = self._counter(goal, "target")
                    goal["done"] = target >= target_goal
                    changed = True
                    restored_fields.append(f"goals.weekly.{goal_id}")

        text_targets = {"current_quest": data.get("current_quest"), "last_session": data.get("last_session")}
        text_defaults = {
            "current_quest": "Blackjack — PYR teaches the next needed concept, then you enter Forge phase and implement it from scratch.",
            "last_session": "Forge RPG Shell and Homestead were approved as the next IDE evolution. No learning rewards or purchases were claimed.",
        }
        for field, target in text_targets.items():
            if target is None:
                continue
            target_text = self._legacy_text(target, field)
            current_text = progress.get(field)
            if current_text not in {None, "", text_defaults[field], target_text}:
                raise StateCommandError(f"Canonical {field} differs from the reviewed legacy evidence", status_code=409)
            if current_text != target_text:
                progress[field] = target_text
                changed = True
                restored_fields.append(field)

        # Session notes establish that the player reached Forge for the next
        # encounter.  The concept is taken from canonical mob metadata rather
        # than from an arbitrary legacy string.
        learning_state = self._dict(progress, "learning_state")
        if next_name:
            next_concept = self._legacy_text(next_mob.get("concept") or "", "next_mob_concept")
            if learning_state.get("phase") not in {None, "teach", "forge"}:
                raise StateCommandError("Canonical learning phase conflicts with the reviewed legacy evidence", status_code=409)
            if learning_state.get("project") not in {None, project_id}:
                raise StateCommandError("Canonical learning project conflicts with the reviewed legacy evidence", status_code=409)
            if learning_state.get("phase") != "forge":
                learning_state["phase"] = "forge"
                changed = True
                restored_fields.append("learning_state.phase")
            if learning_state.get("project") != project_id:
                learning_state["project"] = project_id
                changed = True
                restored_fields.append("learning_state.project")
            if learning_state.get("concept") != next_concept:
                learning_state["concept"] = next_concept
                changed = True
                restored_fields.append("learning_state.concept")

        if not changed:
            return Mutation(
                False,
                {
                    "already_reconciled": True,
                    "project_id": project_id,
                    "restored_mobs": defeated_names,
                    "next_mob": next_name,
                    "codex_entries": codex_ids,
                    "encounter": encounter_projection,
                },
            )

        actual_project_progress = self._integer(project.get("progress", 0), "project.progress", minimum=0, maximum=100)
        level_event = {"level_before": defaults["level"], "level_after": level} if player_level_changed else {}
        return Mutation(
            True,
            {
                "project_id": project_id,
                "restored_level": level,
                "restored_xp": xp,
                "restored_lifetime_xp": lifetime_xp,
                "restored_coins": coins,
                "restored_mobs": defeated_names,
                "project_progress": actual_project_progress,
                "next_mob": next_name,
                "encounter": encounter_projection,
                "codex_entries": codex_ids,
                "achievement_unlocked": achievement_unlocked,
                "restored_fields": list(dict.fromkeys(restored_fields)),
                "reward_history_inferred": False,
            },
            {
                "project_id": project_id,
                "source": source,
                "evidence_id": evidence_id,
                "reason": reason,
                "reconciliation": "approved_legacy_evidence",
                "restored_level": level,
                "restored_xp": xp,
                "restored_lifetime_xp": lifetime_xp,
                "restored_coins": coins,
                "restored_mobs": defeated_names,
                "project_progress": actual_project_progress,
                "next_mob": next_name,
                "codex_entries": codex_ids,
                "achievement_unlocked": achievement_unlocked,
                "reward_history_inferred": False,
                "restored_fields": list(dict.fromkeys(restored_fields)),
                **level_event,
            },
        )
