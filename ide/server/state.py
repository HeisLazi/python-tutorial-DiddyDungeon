"""Bounded local campaign-state mutation service.

The Forge backend is the only local writer for canonical progression state.
Callers submit named commands with an explicit trust level; arbitrary object
paths, JSON patches and direct snapshots are intentionally unsupported.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MAX_EVENT_RECORDS = 100
MAX_REASON_LENGTH = 240
MAX_IDENTIFIER_LENGTH = 120
MAX_REWARD_XP = 100
MAX_REWARD_COINS = 100
MAX_HP_DELTA = 100
MAX_IMPACT = 8
MAX_CODEX_RECORDS = 100
MAX_CODEX_NOTE_BYTES = 2_000
MAX_CODEX_NOTES_PER_ENTRY = 20
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
DUNGEON_SCORE_BY_DIFFICULTY = (0, 10, 15, 20, 30, 45, 60, 80, 105, 135, 170)
DUNGEON_COIN_BY_DIFFICULTY = (0, 5, 8, 11, 15, 20, 26, 33, 41, 50, 60)
DUNGEON_REST_HEAL = 30
CUSTODY_CONFIRMATION_TOKEN = "MIGRATE_LOCAL_STATE"
CUSTODY_MARKER_VERSION = 1
DUNGEON_MARKET_CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "dungeon-heal", "name": "Field Ration", "price": 12, "kind": "heal", "description": "Restore 20 run HP."},
    {"id": "dungeon-ward", "name": "Ember Ward", "price": 24, "kind": "armor", "armor": "Ember Ward", "description": "Reduce the next counterattack."},
    {"id": "dungeon-lens", "name": "Scholar Lens", "price": 30, "kind": "trinket", "trinket": "Scholar Lens", "description": "A cosmetic run trophy for careful reasoning."},
)
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
    "code_checkpoint": {"name": "The Checkpoint Golem", "category": "code craft"},
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
    "record_learning_event": ActionDefinition(frozenset({"pyr"})),
    "record_reference_mode": ActionDefinition(frozenset({"pyr"})),
    "award_learning_reward": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "player_hp_change": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_achievement": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
    "record_battle_objective": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
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
    "dungeon_market_purchase": ActionDefinition(frozenset({"player"})),
    "dungeon_equip_item": ActionDefinition(frozenset({"player"})),
    "dungeon_leave_room": ActionDefinition(frozenset({"player"})),
    "dungeon_finish_run": ActionDefinition(frozenset({"player"})),
}

PUBLIC_ACTIONS = frozenset(action for action, definition in ACTION_DEFINITIONS.items() if not definition.internal)


# These are deliberately generic objective labels. Their values are the only
# Impact values the local game authority may apply; callers cannot supply an
# arbitrary reward or hidden question text.
ENCOUNTER_PROFILES: tuple[dict[str, Any], ...] = (
    {
        "max_resolve": 4,
        "objectives": {
            "table_setup": {"impact": 2, "question_type": "prediction"},
            "state_explanation": {"impact": 2, "question_type": "explanation"},
        },
    },
    {
        "max_resolve": 6,
        "objectives": {
            "hand_model": {"impact": 3, "question_type": "code_checkpoint"},
            "deal_reasoning": {"impact": 3, "question_type": "explanation"},
        },
    },
    {
        "max_resolve": 9,
        "objectives": {
            "trace_total": {"impact": 3, "question_type": "prediction"},
            "running_total": {"impact": 3, "question_type": "code_checkpoint"},
            "loop_explanation": {"impact": 3, "question_type": "explanation"},
        },
    },
    {
        "max_resolve": 8,
        "objectives": {
            "choice_flow": {"impact": 4, "question_type": "code_checkpoint"},
            "stop_condition": {"impact": 4, "question_type": "bug_diagnosis"},
        },
    },
    {
        "max_resolve": 7,
        "objectives": {
            "outcome_classification": {"impact": 3, "question_type": "prediction"},
            "branch_reasoning": {"impact": 4, "question_type": "explanation"},
        },
    },
    {
        "max_resolve": 8,
        "objectives": {
            "function_boundary": {"impact": 4, "question_type": "code_checkpoint"},
            "return_reasoning": {"impact": 4, "question_type": "explanation"},
        },
    },
    {
        "max_resolve": 7,
        "objectives": {
            "compare_states": {"impact": 3, "question_type": "prediction"},
            "winner_justification": {"impact": 4, "question_type": "explanation"},
        },
    },
    {
        "max_resolve": 8,
        "objectives": {
            "reset_state": {"impact": 4, "question_type": "code_checkpoint"},
            "loop_explanation": {"impact": 4, "question_type": "explanation"},
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

BOSS_REQUIREMENTS: tuple[str, ...] = (
    "required_behavior",
    "explanation",
    "interview",
)

# Boss validation is deliberately presentation-safe: the projection exposes
# only which bounded gate phases have been verified, never the provider's
# hidden interview prompt or answer key.
BOSS_PHASE_LABELS: dict[str, str] = {
    "required_behavior": "Required behaviour",
    "explanation": "Explanation",
    "interview": "Interview",
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
        "question_types": ("prediction", "explanation", "code_checkpoint"),
    },
    {
        "id": "input-output",
        "title": "Input and output",
        "aliases": ("input", "output", "input/output"),
        "definition": "Input brings data into a program; output communicates a result to a person or another system.",
        "examples": ("city = input('City: ')\nprint(f'You chose {city}')",),
        "question_types": ("prediction", "explanation"),
    },
    {
        "id": "lists",
        "title": "Lists & collections",
        "aliases": ("list", "lists", "collection", "random selection"),
        "definition": "A list keeps an ordered, changeable sequence of values that can be indexed or iterated.",
        "examples": ("colors = ['red', 'blue']\ncolors.append('gold')\nprint(colors[0])",),
        "question_types": ("code_checkpoint", "prediction", "explanation"),
    },
    {
        "id": "loops",
        "title": "Loops & totals",
        "aliases": ("loop", "loops", "iteration", "totals", "running total"),
        "definition": "A loop repeats a block while walking through values or while a condition remains true.",
        "examples": ("total = 0\nfor value in [2, 4, 6]:\n    total += value",),
        "question_types": ("prediction", "code_checkpoint", "explanation"),
    },
    {
        "id": "conditionals",
        "title": "Conditionals & branches",
        "aliases": ("conditional", "conditionals", "branch", "branches"),
        "definition": "A conditional chooses which code path runs by evaluating a Boolean expression.",
        "examples": ("if temperature > 30:\n    label = 'hot'\nelse:\n    label = 'mild'",),
        "question_types": ("prediction", "bug_diagnosis", "explanation"),
    },
    {
        "id": "functions",
        "title": "Functions & boundaries",
        "aliases": ("function", "functions", "return", "function boundary"),
        "definition": "A function packages a named operation with inputs and an explicit result or side effect.",
        "examples": ("def double(value):\n    return value * 2\n\nanswer = double(4)",),
        "question_types": ("code_checkpoint", "explanation", "bug_diagnosis"),
    },
    {
        "id": "dictionaries",
        "title": "Dictionaries & lookup",
        "aliases": ("dictionary", "dictionaries", "mapping", "lookup"),
        "definition": "A dictionary maps unique keys to values so related data can be looked up by name.",
        "examples": ("prices = {'tea': 3, 'cake': 5}\nprint(prices.get('tea', 0))",),
        "question_types": ("code_checkpoint", "prediction", "explanation"),
    },
    {
        "id": "control-flow",
        "title": "Control flow & reset",
        "aliases": ("control flow", "input loops", "reset state", "program loops"),
        "definition": "Control flow combines sequence, branches, loops and state updates; reset logic returns state to a known boundary.",
        "examples": ("running = True\nwhile running:\n    running = False",),
        "question_types": ("code_checkpoint", "bug_diagnosis", "explanation"),
    },
    {
        "id": "random-selection",
        "title": "Random selection",
        "aliases": ("random selection", "random"),
        "definition": "Random selection chooses a value from a collection; keeping the chosen value visible makes the result explainable and testable.",
        "examples": ("import random\nchoice = random.choice(['left', 'right'])",),
        "question_types": ("prediction", "explanation", "code_checkpoint"),
    },
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
SYNC_EQUIPMENT_FIELDS = frozenset({"armor", "trinket", "title"})
SYNC_COMPANION_FIELDS = frozenset({"name", "form", "level", "bond", "next_form", "next_form_requirement"})
SYNC_HOMESTEAD_FIELDS = frozenset({"name", "owned_cosmetics", "equipped"})
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
                "commits_logged", "reference_mode_uses", "guided_milestones", "recovery_trials_passed",
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
            entry_fields = {"id", "project_id", "mob_name", "concept", "status", "question_types", "weaknesses", "notes", "player_notes", "attempts", "results", "interview_history", "mastery"}
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
            raw = cls._campaign_mapping(dungeon, "campaign.dungeon_run", {"status", "run_id", "seed", "concept_id", "floor", "room", "room_type", "score", "run_coins", "started_at", "updated_at", "ended_at", "loadout", "inventory", "question", "question_number", "room_choices", "editor_content", "last_result", "history", "attempts"})
            item: dict[str, Any] = {}
            for field in ("status", "run_id", "seed", "concept_id", "room_type"):
                if field in raw:
                    item[field] = cls._campaign_text(raw[field], f"campaign.dungeon_run.{field}", max_length=MAX_IDENTIFIER_LENGTH)
            for field in ("started_at", "updated_at", "ended_at"):
                if field in raw and raw[field] is not None:
                    item[field] = cls._campaign_text(raw[field], f"campaign.dungeon_run.{field}", max_length=80)
            for field in ("floor", "room", "score", "run_coins", "question_number", "attempts"):
                if field in raw:
                    item[field] = cls._campaign_int(raw[field], f"campaign.dungeon_run.{field}", maximum=MAX_DUNGEON_FLOOR if field in {"floor", "room"} else MAX_SYNC_COUNTER)
            if "loadout" in raw and raw["loadout"] is not None:
                loadout = cls._campaign_mapping(raw["loadout"], "campaign.dungeon_run.loadout", {"armor", "trinket", "hp", "max_hp", "heals", "coins"})
                clean_loadout: dict[str, Any] = {}
                for field in ("armor", "trinket"):
                    if field in loadout and loadout[field] is not None:
                        clean_loadout[field] = cls._campaign_text(loadout[field], f"campaign.dungeon_run.loadout.{field}", max_length=MAX_IDENTIFIER_LENGTH)
                    elif field in loadout:
                        clean_loadout[field] = None
                for field in ("hp", "max_hp", "heals", "coins"):
                    if field in loadout:
                        clean_loadout[field] = cls._campaign_int(loadout[field], f"campaign.dungeon_run.loadout.{field}")
                item["loadout"] = clean_loadout
            if "inventory" in raw and raw["inventory"] is not None:
                raw_inventory = raw["inventory"]
                if not isinstance(raw_inventory, list) or len(raw_inventory) > MAX_DUNGEON_INVENTORY:
                    raise StateCommandError("campaign.dungeon_run.inventory must be a bounded list")
                clean_inventory: list[dict[str, Any]] = []
                for index, entry in enumerate(raw_inventory):
                    raw_entry = cls._campaign_mapping(entry, f"campaign.dungeon_run.inventory[{index}]", {"id", "name", "kind", "armor", "trinket", "description"})
                    clean_entry: dict[str, Any] = {}
                    for field in ("id", "kind"):
                        if field in raw_entry:
                            clean_entry[field] = cls._campaign_identifier(raw_entry[field], f"campaign.dungeon_run.inventory[{index}].{field}")
                    for field in ("name", "armor", "trinket", "description"):
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
                    clean_question["prompt"] = cls._campaign_text(question["prompt"], "campaign.dungeon_run.question.prompt", max_length=2_000)
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
            if "editor_content" in raw:
                item["editor_content"] = cls._campaign_text(raw["editor_content"], "campaign.dungeon_run.editor_content", max_length=8_000) if raw["editor_content"] else ""
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
                    "creative_bonuses", "discoveries_unlocked",
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
                    item["mobs"] = [pick(mob, mob_fields) for mob in project["mobs"] if isinstance(mob, Mapping)]
                campaign["projects"].append(item)
        if "current_quest" in progress:
            campaign["current_quest"] = progress.get("current_quest")
        if isinstance(progress.get("codex"), Mapping):
            codex = {"encounters": []}
            for entry in progress["codex"].get("encounters", []):
                if not isinstance(entry, Mapping):
                    continue
                item = pick(entry, {"id", "project_id", "mob_name", "concept", "status", "question_types", "weaknesses", "notes", "player_notes", "attempts"})
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
                run_fields = {"status", "run_id", "seed", "concept_id", "floor", "room", "room_type", "score", "run_coins", "started_at", "updated_at", "ended_at", "question_number", "editor_content", "attempts"}
                item = pick(raw_run, run_fields)
                if isinstance(raw_run.get("loadout"), Mapping):
                    item["loadout"] = pick(raw_run["loadout"], {"armor", "trinket", "hp", "max_hp", "heals", "coins"})
                if isinstance(raw_run.get("inventory"), list):
                    item["inventory"] = [pick(entry, {"id", "name", "kind", "armor", "trinket", "description"}) for entry in raw_run["inventory"] if isinstance(entry, Mapping)]
                if isinstance(raw_run.get("question"), Mapping):
                    item["question"] = pick(raw_run["question"], {"id", "question_type", "concept_id", "difficulty", "prompt", "options"})
                elif "question" in raw_run:
                    item["question"] = None
                if isinstance(raw_run.get("room_choices"), list):
                    item["room_choices"] = [pick(choice, {"id", "kind", "label", "description"}) for choice in raw_run["room_choices"] if isinstance(choice, Mapping)]
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
            validated["equipment"] = {
                field: cls._sync_text(equipment[field], f"equipment.{field}")
                for field in SYNC_EQUIPMENT_FIELDS
                if field in equipment
            }

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
            for field in ("level", "bond"):
                if field in companion:
                    clean_companion[field] = cls._integer(companion[field], f"companion.{field}", minimum=0, maximum=MAX_SYNC_LEVEL)
            validated["companion"] = clean_companion

        homestead = projection.get("homestead")
        if homestead is not None:
            if not isinstance(homestead, Mapping):
                raise StateCommandError("Cloud Homestead projection must be an object")
            extra = set(homestead) - SYNC_HOMESTEAD_FIELDS
            if extra:
                raise StateCommandError(f"Unsupported cloud Homestead field(s): {', '.join(sorted(extra))}")
            clean_homestead: dict[str, Any] = {}
            if "name" in homestead:
                clean_homestead["name"] = cls._sync_text(homestead["name"], "homestead.name")
            owned = cls._sync_list(homestead["owned_cosmetics"], "homestead.owned_cosmetics") if "owned_cosmetics" in homestead else None
            if owned is not None:
                clean_homestead["owned_cosmetics"] = owned
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
        companion = copy_fields(progress.get("companion"), SYNC_COMPANION_FIELDS)
        homestead_source = progress.get("homestead")
        homestead = copy_fields(homestead_source, frozenset({"name", "owned_cosmetics", "equipped"}))
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
            for field in ("name", "owned_cosmetics", "equipped"):
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

        raw = project.get("boss_validation")
        verified = raw.get("verified") if isinstance(raw, Mapping) else []
        if not isinstance(verified, list):
            verified = []
        verified_ids = [item for item in verified if item in BOSS_REQUIREMENTS]
        # Preserve the canonical requirement order even if an older local
        # checkpoint recorded them in a different order.
        verified_ids = [item for item in BOSS_REQUIREMENTS if item in verified_ids]
        remaining = [item for item in BOSS_REQUIREMENTS if item not in verified_ids]
        status = str(project.get("boss_status") or "locked")
        if status == "defeated" or project.get("completed") is True:
            phase = "complete"
        elif remaining:
            phase = remaining[0]
        else:
            phase = "ready_to_clear"
        return {
            "verified_boss_requirements": verified_ids,
            "remaining_boss_requirements": remaining,
            "boss_phase": phase,
            "boss_phase_label": BOSS_PHASE_LABELS.get(phase, "Boss validation complete" if phase == "ready_to_clear" else "Boss clear"),
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
                "boss_requirements": list(BOSS_REQUIREMENTS),
                **boss_validation,
                "mob_name": None,
                "mob_index": None,
                "status": "complete" if project_completed else "boss_available",
                "resolve": 0,
                "max_resolve": 0,
                "completed_objectives": [],
                "available_objectives": [],
                "attempts": 0,
                "question_types": [],
            }

        mob = mobs[index]
        profile = self._encounter_profile(index)
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
        available = [
            {"id": objective_id, "impact": int(definition["impact"]), "question_type": str(definition["question_type"])}
            for objective_id, definition in profile["objectives"].items()
            if objective_id not in completed_ids
        ]
        question_types = matching.get("question_types")
        observed_types = [item for item in question_types if isinstance(item, str)][:20] if isinstance(question_types, list) else []
        try:
            attempts = max(0, int(matching.get("attempts", mob.get("objective_attempts", 0)) or 0))
        except (TypeError, ValueError):
            attempts = 0
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
            "question_types": observed_types,
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
            if not isinstance(item_id, str) or not item_id.strip() or not isinstance(name, str) or not name.strip() or kind not in {"armor", "trinket"}:
                raise StateCommandError(f"Existing Dungeon inventory item {index} is invalid", status_code=500)
            clean = {
                "id": item_id[:MAX_IDENTIFIER_LENGTH],
                "name": name[:MAX_IDENTIFIER_LENGTH],
                "kind": kind,
                "description": str(item.get("description") or "")[:300],
            }
            if kind == "armor":
                clean["armor"] = str(item.get("armor") or name)[:MAX_IDENTIFIER_LENGTH]
            else:
                clean["trinket"] = str(item.get("trinket") or name)[:MAX_IDENTIFIER_LENGTH]
            items.append(clean)
        if mutate:
            run["inventory"] = items
        return items

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
        difficulty = min(MAX_DUNGEON_DIFFICULTY, max(1, 1 + (floor - 1) // 2))
        types = ("true_false", "multiple_choice", "code_checkpoint", "bug_hunt", "short_explanation")
        question_type = types[(room - 1) % len(types)]
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

    @classmethod
    def _dungeon_mob_spec(cls, run: Mapping[str, Any]) -> dict[str, Any] | None:
        """Return the safe identity for the currently issued learning mob.

        A mob exists only for the current encounter question.  Selector rooms
        deliberately return ``None`` so the browser cannot discover future
        enemies, prompts or answer keys before it commits a route.
        """

        if run.get("room_type") != "encounter":
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
        return {
            "id": f"{question.get('id', 'dungeon-question')}-mob",
            "name": archetype["name"],
            "category": archetype["category"],
            "concept_id": str(question.get("concept_id") or run.get("concept_id") or "python-basics")[:MAX_IDENTIFIER_LENGTH],
            "question_type": question_type,
            "difficulty": difficulty,
            "phase": _DUNGEON_MOB_PHASES[phase_index],
        }

    @classmethod
    def _dungeon_route_choices(cls, run: Mapping[str, Any]) -> list[dict[str, str]]:
        """Build the answer-free route selector for the current map node."""

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
        run["room"] = next_room
        run["floor"] = floor
        run["room_type"] = "selector"
        run["room_choices"] = cls._dungeon_route_choices(run)
        run["question"] = None
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
        raw_choices = run.get("room_choices")
        if not isinstance(raw_choices, list):
            raise StateCommandError("The current Dungeon map has no route choices", status_code=409)
        choice = next((item for item in raw_choices if isinstance(item, Mapping) and item.get("id") == choice_id), None)
        if choice is None:
            raise StateCommandError("That Dungeon route is no longer available", status_code=409)
        kind = self._text(choice.get("kind"), "choice.kind", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if kind not in {"encounter", "rest", "market"}:
            raise StateCommandError("Unsupported Dungeon route", status_code=500)
        run["room_choices"] = []
        run["room_type"] = kind
        run["editor_content"] = ""
        run["updated_at"] = _utc_now()
        question_id = None
        mob = None
        if kind == "encounter":
            run["concept_id"] = self._dungeon_adaptive_concept(progress, str(run.get("concept_id") or "python-basics"))
            run["question_number"] = self._counter(run, "question_number") + 1
            question = self._dungeon_question_for_room(
                run,
                room=self._integer(run.get("room", 1), "room", minimum=1, maximum=MAX_DUNGEON_ROOM),
                floor=self._integer(run.get("floor", 1), "floor", minimum=1, maximum=MAX_DUNGEON_FLOOR),
            )
            run["question"] = question
            question_id = question["id"]
            mob = self._dungeon_mob_spec(run)
        else:
            run["question"] = None
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress), "choice": dict(choice)},
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
            "editor_content": "",
            "last_result": None,
            "history": [],
            "inventory": [],
            "market_catalog": self._dungeon_market_catalog() if status == "active" and run.get("room_type") == "market" else [],
            "leaderboard": [],
        }
        for field in ("floor", "room", "score", "run_coins"):
            try:
                projection[field] = max(0, int(projection[field] or 0))
            except (TypeError, ValueError) as exc:
                raise StateCommandError(f"Existing Dungeon field {field} is invalid", status_code=500) from exc
        loadout = run.get("loadout")
        if not isinstance(loadout, Mapping):
            raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
        projection["loadout"] = {
            field: loadout[field]
            for field in ("armor", "trinket", "hp", "max_hp", "heals", "coins")
            if field in loadout
        }
        inventory = self._dungeon_inventory_entries(run)
        equipped_armor = projection["loadout"].get("armor")
        equipped_trinket = projection["loadout"].get("trinket")
        projection["inventory"] = [
            {
                **item,
                "equipped": (
                    item.get("kind") == "armor" and item.get("armor") == equipped_armor
                ) or (
                    item.get("kind") == "trinket" and item.get("trinket") == equipped_trinket
                ),
            }
            for item in inventory
        ]
        question = run.get("question")
        if isinstance(question, Mapping):
            projection["question"] = {
                field: question[field]
                for field in ("id", "question_type", "concept_id", "difficulty", "prompt", "options")
                if field in question
            }
            projection["encounter"] = self._dungeon_mob_spec(run)
        elif status == "active" and run.get("room_type") not in {"rest", "market", "selector"}:
            raise StateCommandError("Active Dungeon run has no current question", status_code=500)
        raw_choices = run.get("room_choices", [])
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
        editor_content = run.get("editor_content", "")
        if not isinstance(editor_content, str):
            raise StateCommandError("Existing Dungeon editor content is invalid", status_code=500)
        projection["editor_content"] = editor_content if status == "active" else ""
        last_result = run.get("last_result")
        if isinstance(last_result, Mapping):
            projection["last_result"] = {
                key: last_result[key]
                for key in ("outcome", "question_id", "mob_name", "score_delta", "coins_delta", "damage", "evidence_id", "reason")
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
        data = self._payload(payload, {"concept_id", "seed"}, set())
        existing = self._dungeon_run(progress)
        if isinstance(existing, dict) and existing.get("status") == "active":
            raise StateCommandError("An active Dungeon run already exists", status_code=409)

        learning = progress.get("learning_state")
        fallback_concept = learning.get("concept") if isinstance(learning, Mapping) else None
        concept_id = data.get("concept_id") or self._dungeon_adaptive_concept(progress, str(fallback_concept or "python-basics"))
        concept_id = self._text(concept_id, "concept_id", max_length=MAX_IDENTIFIER_LENGTH)
        seed = data.get("seed") or uuid.uuid4().hex
        seed = self._text(seed, "seed", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        run_id = f"dungeon-{uuid.uuid4().hex}"
        player = self._dict(progress, "player")
        maximum = self._counter(player, "max_hp") or 100
        now = _utc_now()
        run = {
            "status": "active",
            "run_id": run_id,
            "seed": seed,
            "concept_id": concept_id,
            "floor": 1,
            "room": 1,
            "room_type": "selector",
            "score": 0,
            "run_coins": 0,
            "started_at": now,
            "updated_at": now,
            "ended_at": None,
            "loadout": {
                "armor": "Apprentice Coat",
                "trinket": None,
                "hp": maximum,
                "max_hp": maximum,
                "heals": 1,
                "coins": 0,
            },
            "inventory": [
                {
                    "id": "dungeon-starter-armor",
                    "name": "Apprentice Coat",
                    "kind": "armor",
                    "armor": "Apprentice Coat",
                    "description": "Starter armor for this Dungeon run.",
                },
            ],
            "question": None,
            "question_number": 0,
            "room_choices": [],
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
                "question_id": None,
                "question_type": None,
                "room_choices": [choice["id"] for choice in run.get("room_choices", [])],
                "concept_id": concept_id,
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
        if question is None or question.get("id") != question_id or run.get("room_type") != "encounter":
            raise StateCommandError("Dungeon question changed; reload the current room", status_code=409)
        mob = self._dungeon_mob_spec(run)
        difficulty = self._integer(question.get("difficulty", 1), "question.difficulty", minimum=1, maximum=MAX_DUNGEON_DIFFICULTY)
        run["attempts"] = self._counter(run, "attempts") + 1
        score_delta = 0
        coins_delta = 0
        damage = 0
        if verdict == "correct":
            score_delta = DUNGEON_SCORE_BY_DIFFICULTY[min(difficulty, len(DUNGEON_SCORE_BY_DIFFICULTY) - 1)]
            coins_delta = DUNGEON_COIN_BY_DIFFICULTY[min(difficulty, len(DUNGEON_COIN_BY_DIFFICULTY) - 1)]
            run["score"] = self._counter(run, "score") + score_delta
            run["run_coins"] = self._counter(run, "run_coins") + coins_delta
        else:
            raw_damage = min(28, 4 + difficulty * 2)
            loadout = run.get("loadout")
            if not isinstance(loadout, dict):
                raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
            armor_reduction = 25 if loadout.get("armor") == "Ember Ward" else 0
            damage = max(1, (raw_damage * (100 - armor_reduction) + 99) // 100)
            current_hp = self._counter(loadout, "hp")
            loadout["hp"] = max(0, current_hp - damage)
            if loadout["armor"] == "Ember Ward":
                loadout["armor"] = "Apprentice Coat"

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
        run["last_result"] = result_record
        self._dungeon_append_history(run, {"room": run.get("room", 1), "floor": run.get("floor", 1), **result_record})
        run["editor_content"] = ""
        died = verdict == "incorrect" and self._counter(run.get("loadout") or {}, "hp") <= 0
        if died:
            ended = _utc_now()
            run.update({"status": "dead", "ended_at": ended, "updated_at": ended, "question": None})
            self._dungeon_record_leaderboard(progress, run, "dead")
        else:
            if verdict == "correct":
                self._dungeon_set_next_room(run, progress)
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
            "editor_reset": True,
            "reason": reason,
        }
        if died:
            event.update({"run_died": True, "score": run.get("score", 0)})
        elif verdict == "correct":
            event.update({"next_room": run.get("room"), "next_room_type": run.get("room_type"), "question_type": (run.get("question") or {}).get("question_type") if isinstance(run.get("question"), Mapping) else None, "concept_id": (run.get("question") or {}).get("concept_id") if isinstance(run.get("question"), Mapping) else run.get("concept_id")})
        return Mutation(True, {"run": projection, **result_record, "run_died": died}, event)

    def _dungeon_use_rest(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"run_id"}, {"run_id"})
        run = self._active_dungeon_run(progress)
        run_id = self._text(data["run_id"], "run_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        if run.get("run_id") != run_id:
            raise StateCommandError("Dungeon run changed; reload the current run", status_code=409)
        if run.get("room_type") != "rest":
            raise StateCommandError("A rest room is not currently available", status_code=409)
        loadout = run.get("loadout")
        if not isinstance(loadout, dict):
            raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
        heals = self._counter(loadout, "heals")
        current_hp = self._counter(loadout, "hp")
        maximum = self._counter(loadout, "max_hp")
        if heals <= 0:
            raise StateCommandError("No rest charges remain in this run", status_code=409)
        if current_hp >= maximum:
            raise StateCommandError("HP is already full", status_code=409)
        healed = min(DUNGEON_REST_HEAL, maximum - current_hp)
        loadout["hp"] = current_hp + healed
        loadout["heals"] = heals - 1
        run["last_result"] = {"outcome": "rest", "score_delta": 0, "coins_delta": 0, "damage": 0, "reason": "dungeon_rest_used"}
        self._dungeon_append_history(run, {"room": run.get("room", 1), "floor": run.get("floor", 1), "outcome": "rest", "score_delta": 0, "coins_delta": 0, "damage": 0})
        self._dungeon_set_next_room(run, progress)
        return Mutation(True, {"run": self.dungeon_projection(progress), "healed": healed}, {"run_id": run_id, "healed": healed, "next_room": run.get("room"), "next_room_type": run.get("room_type"), "editor_reset": True, "reason": "dungeon_rest_used"})

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
        price = self._integer(item["price"], "market.price", minimum=0, maximum=MAX_SYNC_COUNTER)
        if coins < price:
            raise StateCommandError(f"Not enough run coins for {item['name']}", status_code=409)
        loadout = run.get("loadout")
        if not isinstance(loadout, dict):
            raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
        run["run_coins"] = coins - price
        if item["kind"] == "heal":
            loadout["hp"] = min(self._counter(loadout, "max_hp"), self._counter(loadout, "hp") + 20)
        elif item["kind"] in {"armor", "trinket"}:
            inventory = self._dungeon_inventory_entries(run, mutate=True)
            if not any(candidate.get("id") == item["id"] for candidate in inventory):
                inventory.append(
                    {
                        key: item[key]
                        for key in ("id", "name", "kind", "armor", "trinket", "description")
                        if key in item
                    }
                )
                run["inventory"] = inventory[-MAX_DUNGEON_INVENTORY:]
            # Preserve the previous market behavior while making the choice
            # reversible from the run inventory menu.
            loadout[item["kind"]] = item["armor"] if item["kind"] == "armor" else item["trinket"]
        run["last_result"] = {"outcome": "market_purchase", "coins_delta": -price, "score_delta": 0, "damage": 0, "reason": item["name"]}
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
        loadout = run.get("loadout")
        if not isinstance(loadout, dict):
            raise StateCommandError("Existing Dungeon loadout is invalid", status_code=500)
        field = "armor" if item.get("kind") == "armor" else "trinket"
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
        self._dungeon_record_leaderboard(progress, run, "complete")
        return Mutation(True, {"run": self.dungeon_projection(progress), "score": score}, {"run_id": run_id, "score": score, "run_finished": True, "editor_reset": True, "reason": "dungeon_run_finished"})

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
        self._dungeon_record_leaderboard(progress, run, "dead")
        return Mutation(
            True,
            {"run": self.dungeon_projection(progress)},
            {"run_id": run_id, "floor": floor, "score": score, "editor_reset": True, "reason": reason},
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
            mutation = self._dispatch(normalized_action, payload, progress)
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

    def _dispatch(self, action: str, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        handlers = {
            "homestead_purchase": self._homestead_purchase,
            "homestead_equip": self._homestead_equip,
            "record_learning_event": self._record_learning_event,
            "record_reference_mode": self._record_reference_mode,
            "award_learning_reward": self._award_learning_reward,
            "player_hp_change": self._player_hp_change,
            "record_achievement": self._record_achievement,
            "record_battle_objective": self._record_battle_objective,
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
            "dungeon_market_purchase": self._dungeon_market_purchase,
            "dungeon_equip_item": self._dungeon_equip_item,
            "dungeon_leave_room": self._dungeon_leave_room,
            "dungeon_finish_run": self._dungeon_finish_run,
        }
        return handlers[action](payload, progress)

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
    def _encounter_profile(index: int) -> dict[str, Any]:
        return ENCOUNTER_PROFILES[min(max(index, 0), len(ENCOUNTER_PROFILES) - 1)]

    def _ensure_encounter_state(
        self,
        progress: dict[str, Any],
        project: Mapping[str, Any],
        mob: dict[str, Any],
        index: int,
    ) -> dict[str, Any]:
        profile = self._encounter_profile(index)
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
                "question_types": list(page.get("question_types", ())),
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
        reward = self._grant_reward(player, reward_xp, reward_coins)
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
            "level_before": reward["level_before"],
            "level_after": reward["level_after"],
            "achievement_unlocked": achievement_unlocked,
            "evidence_id": evidence_id,
            "reason": reason,
        }

    def _record_battle_objective(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"objective_id", "evidence_id", "reason"}, {"objective_id", "evidence_id", "reason"})
        objective_id = self._text(data["objective_id"], "objective_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        evidence_id = self._text(data["evidence_id"], "evidence_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        reason = self._text(data["reason"], "reason")
        project, mobs, index, mob = self._active_project_and_mob(progress)
        profile = self._encounter_profile(index)
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
        after = max(0, before - impact)
        completed.append(objective_id)
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
        entry = self._upsert_codex_entry(
            progress,
            project,
            mob,
            question_type=str(objective["question_type"]),
            outcome="verified",
            evidence_id=evidence_id,
            note=reason,
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
        session["attempts"] = attempts + 1
        if outcome == "correct":
            session["correct"] = self._counter(session, "correct") + 1
        session["status"] = "reviewed"
        session["updated_at"] = _utc_now()
        history.append({"outcome": outcome, "evidence_id": evidence_id, "reason": reason, "recorded_at": session["updated_at"]})
        session["history"] = history[-MAX_PRACTICE_ATTEMPTS_PER_SESSION:]
        projected = self.practice_projection(progress)
        safe_session = next(item for item in projected["sessions"] if item["session_id"] == session_id)
        return Mutation(
            True,
            {"session": safe_session, "outcome": outcome, "reward_xp": 0, "reward_coins": 0},
            {
                "session_id": session_id,
                "outcome": outcome,
                "evidence_id": evidence_id,
                "reason": reason,
                "reward_xp": 0,
                "reward_coins": 0,
            },
        )

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
        verified = [item for item in verified if item in BOSS_REQUIREMENTS]
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

        verified.append(requirement_id)
        validation["verified"] = [item for item in BOSS_REQUIREMENTS if item in verified]
        history.append(
            {
                "requirement_id": requirement_id,
                "evidence_id": evidence_id,
                "reason": reason,
                "recorded_at": _utc_now(),
            }
        )
        validation["history"] = history[-20:]
        projection = self._boss_validation_projection(project)
        result = {
            "boss_requirement_verified": True,
            "requirement_id": requirement_id,
            "evidence_id": evidence_id,
            "reason": reason,
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
        project_name = self._text(project.get("name") or project.get("branch") or "", "project_name")
        if project.get("boss_status") == "defeated" or project.get("completed") is True:
            return Mutation(
                False,
                {
                    "already_cleared": True,
                    "boss_name": boss_name,
                    "project_name": project_name,
                },
            )
        if project.get("boss_status") != "available":
            raise StateCommandError("The project boss is not unlocked yet", status_code=409)

        player = self._dict(progress, "player")
        reward = self._grant_reward(player, 100, 0)
        stats = self._dict(progress, "stats")
        stats["projects_cleared"] = self._counter(stats, "projects_cleared") + 1
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
        validation["verified"] = list(BOSS_REQUIREMENTS)
        validation["completed_at"] = completed_at

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

        return Mutation(
            True,
            {
                "boss_defeated": True,
                "project_completed": True,
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
                "verified_boss_requirements": list(BOSS_REQUIREMENTS),
            },
            {
                "project_id": self._project_id(project),
                "project_name": project_name,
                "boss_name": boss_name,
                "boss_defeated": True,
                "project_completed": True,
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
                "verified_boss_requirements": list(BOSS_REQUIREMENTS),
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
            profile = self._encounter_profile(index)
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
        armor_name = str((progress.get("equipment") or {}).get("armor") or "")
        armor_reduction = {"Apprentice Coat": 10, "Leather Guard": 20, "Runic Mail": 30, "Emberplate": 40, "Guardian Aegis": 50, "Mythril Archive Plate": 60}.get(armor_name, 0)
        damage = max(1, (raw_damage * (100 - armor_reduction) + 99) // 100)
        prevented_damage = 0
        trinket_trigger = None
        revived = False
        trinket_name = str((progress.get("equipment") or {}).get("trinket") or "")
        trinket_triggers = encounter.setdefault("trinket_triggers", []) if isinstance(encounter, dict) else []
        if not isinstance(trinket_triggers, list):
            raise StateCommandError("Existing encounter trinket history is invalid", status_code=500)
        if trinket_name == "Guardian Sigil" and "guardian-sigil:counterattack" not in trinket_triggers:
            prevented_damage = damage
            damage = 0
            trinket_triggers.append("guardian-sigil:counterattack")
            trinket_trigger = "Guardian Sigil"
        maximum = self._counter(player, "max_hp")
        current = self._counter(player, "hp")
        updated = max(0, current - damage)
        if updated == 0 and trinket_name == "Phoenix Ember" and "phoenix-ember:revive" not in trinket_triggers:
            updated = 1
            trinket_triggers.append("phoenix-ember:revive")
            revived = True
            trinket_trigger = "Phoenix Ember"
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
                "mob_name": mob_name,
                "objective_id": objective_id,
                "question_type": question_type,
            },
            {
                "raw_damage": raw_damage,
                "damage": damage,
                "prevented_damage": prevented_damage,
                "trinket_trigger": trinket_trigger,
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
