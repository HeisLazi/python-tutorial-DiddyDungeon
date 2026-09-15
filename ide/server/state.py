"""Bounded local campaign-state mutation service.

The Forge backend is the only local writer for canonical progression state.
Callers submit named commands with an explicit trust level; arbitrary object
paths, JSON patches and direct snapshots are intentionally unsupported.
"""

from __future__ import annotations

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

PUBLIC_ACTORS = frozenset({"player", "pyr"})
SYSTEM_ACTOR = "system"


class StateApplyRequest(BaseModel):
    """HTTP command envelope; system actions are never accepted over HTTP."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(min_length=1, max_length=80)
    actor: Literal["player", "pyr"]
    payload: dict[str, Any] = Field(default_factory=dict)


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
    "record_battle_miss": ActionDefinition(frozenset({SYSTEM_ACTOR}), internal=True),
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
            return {
                "project_id": self._project_id(project),
                "mob_name": None,
                "mob_index": None,
                "status": "complete",
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
            "record_battle_miss": self._record_battle_miss,
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
        impact = self._integer(objective["impact"], "impact", minimum=1, maximum=MAX_IMPACT)
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

    def _record_battle_miss(self, payload: Mapping[str, Any], progress: dict[str, Any]) -> Mutation:
        data = self._payload(payload, {"raw_damage", "reason", "encounter_id"}, {"raw_damage", "reason", "encounter_id"})
        raw_damage = self._integer(data["raw_damage"], "raw_damage", minimum=1, maximum=28)
        reason = self._text(data["reason"], "reason")
        encounter_id = self._text(data["encounter_id"], "encounter_id", max_length=MAX_IDENTIFIER_LENGTH, identifier=True)
        player = self._dict(progress, "player")
        armor_name = str((progress.get("equipment") or {}).get("armor") or "")
        armor_reduction = {"Apprentice Coat": 10, "Leather Guard": 20, "Runic Mail": 30, "Emberplate": 40, "Guardian Aegis": 50, "Mythril Archive Plate": 60}.get(armor_name, 0)
        damage = max(1, (raw_damage * (100 - armor_reduction) + 99) // 100)
        maximum = self._counter(player, "max_hp")
        current = self._counter(player, "hp")
        updated = max(0, current - damage)
        player["hp"] = updated
        return Mutation(
            True,
            {"hp": updated, "max_hp": maximum, "damage": damage},
            {"raw_damage": raw_damage, "damage": damage, "hp_before": current, "hp_after": updated, "encounter_id": encounter_id, "reason": reason},
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
