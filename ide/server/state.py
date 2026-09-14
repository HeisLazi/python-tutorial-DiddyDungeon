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
}

PUBLIC_ACTIONS = frozenset(action for action, definition in ACTION_DEFINITIONS.items() if not definition.internal)


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
        player["xp"] = self._counter(player, "xp") + xp
        player["lifetime_xp"] = self._counter(player, "lifetime_xp") + xp
        player["coins"] = self._counter(player, "coins") + coins
        return Mutation(
            True,
            {"xp": player["xp"], "coins": player["coins"]},
            {"xp": xp, "coins": coins, "reason": reason, "evidence_id": evidence_id},
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
