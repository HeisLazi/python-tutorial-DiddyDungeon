from __future__ import annotations

import asyncio
import fcntl
import hashlib
import uuid
import difflib
import importlib.util
import json
import os
import pty
import re
import secrets
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ide.server import ai_tutor, learnharness
from ide.server.context_bridge import (
    ContextValueError,
    bounded_file,
    bounded_text,
    build_context,
    is_sensitive_path,
)
from ide.server.security import allowed_hosts, allowed_origins, is_allowed_origin
from ide.server.state import (
    BOSS_CHOICE_TYPES,
    load_campaign_bounties,
    project_dir_name,
    project_file_name,
    BOSS_REQUIREMENTS,
    CAMPAIGN_MARKET_CATALOG,
    HUNTER_SIGN_CONCEPTS,
    MAX_CODEX_NOTE_BYTES,
    MAX_CODEX_SNIPPET_BYTES,
    MAX_DUNGEON_EDITOR_BYTES,
    MAX_IDENTIFIER_LENGTH,
    MAX_REASON_LENGTH,
    LocalStateService,
    StateApplyRequest,
    StateCommandError,
    StateSyncApplyRequest,
    legacy_state_report,
    opaque_device_id,
    state_custody_report,
    state_authority_info,
)
from ide import workspace_transfer

REPO_ROOT = Path(os.getenv("QUESTLAB_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
WORKSPACE = Path(os.getenv("QUESTLAB_WORKSPACE", REPO_ROOT)).resolve()


def checkout_storage_namespace(repo_root: Path | None = None, workspace: Path | None = None) -> str:
    """Return an opaque, stable local-storage partition for this checkout.

    The browser needs to distinguish two local Forge checkouts that share an
    origin, but an absolute repository/workspace path must never become a
    cloud/device identifier.  Hashing both roots keeps the partition stable
    for a checkout while exposing no filesystem path to the frontend.
    """

    material = "\n".join(
        str(path.resolve())
        for path in (repo_root or REPO_ROOT, workspace or WORKSPACE)
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]
    return f"checkout-{digest}"


def configured_progress_path() -> Path:
    """Resolve the one canonical state path from server configuration.

    Relative overrides are anchored to ``REPO_ROOT`` rather than the process
    cwd, so a CLI launched from the quest workspace cannot silently create a
    second live save.  The normal launcher leaves this unset and uses the
    platform repository's ``progress.json``.
    """

    raw = os.getenv("QUESTLAB_STATE_PATH", "").strip()
    if not raw:
        return (REPO_ROOT / "progress.json").resolve()
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    return candidate.resolve()


def proposed_local_state_path() -> Path:
    """Return the opt-in per-device destination without making it canonical."""

    override = os.getenv("QUESTLAB_LOCAL_STATE_ROOT", "").strip()
    if override:
        root = Path(override).expanduser()
    elif os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "QuestLab"
    else:
        root = Path(os.getenv("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "QuestLab"
    return (root / checkout_storage_namespace() / "progress.json").resolve()


def local_state_custody_report() -> dict[str, object]:
    return state_custody_report(PROGRESS_PATH, proposed_local_state_path())


PROGRESS_PATH = configured_progress_path()
TUTOR_PATH = WORKSPACE / "tutor.py"
DUNGEON_PATH = WORKSPACE / "dungeon.py"
NOTES_DIR_NAME = "notes"
MAX_WORKSPACE_NOTE_BYTES = 20_000
MAX_WORKSPACE_NOTES = 100
NOTE_IDENTIFIER_PATTERN = r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}"
MAX_TEXT_BYTES = 2_000_000
IGNORED_DIRS = {
    ".git",
    ".questlab-trash",
    "node_modules",
    ".venv",
    "venv",
    ".ruff_cache",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
    # A malformed transfer once created a literal ``\\`` directory under the
    # checkout. It mirrors a filesystem root and must never appear as a
    # second workspace root in the editor tree.
    "\\",
}

TUTOR_TEMPLATE = '''"""Quest Lab Tutor Notebook.

PYR and the player may edit this file together for examples, drills, and tiny
experiments. Required project source stays player-authored. Examples here
should teach the concept without becoming a paste-ready solution for the
current project.
"""

# PYR can place unrelated teaching examples below this line.
# You can freely change, run, break, and rebuild them.

'''

ALLOWED_ORIGINS = allowed_origins()
# Rooms whose question is answered and adjudicated; must match the state
# service's dungeon_record_verdict room check.
DUNGEON_COMBAT_ROOM_TYPES = frozenset({"encounter", "elite", "boss"})
PROGRESS_LOCK = threading.RLock()
STATE_SERVICE = LocalStateService(lambda: PROGRESS_PATH, PROGRESS_LOCK)


def extend_campaign_on_startup() -> None:
    """Save new authored contracts and projects into the save once at launch."""

    try:
        STATE_SERVICE.apply_internal("campaign_extend", {})
    except Exception:  # a missing or unreadable save is handled by the first real action
        pass
WORKSPACE_NOTES_LOCK = threading.RLock()
PYR_CONTEXT_LOCK = threading.RLock()
PYR_CONTEXT_INPUT: dict[str, str | None] = {
    "active_path": None,
    "selection": "",
    "terminal_tail": "",
    "client_id": "default",
}
# Context payloads are partitioned by the same opaque client id as verdict
# challenges.  Keep the singular snapshot above for default-client and
# in-process compatibility, but never use it to answer a named client's GET.
PYR_CONTEXT_INPUTS: dict[str, dict[str, str | None]] = {}
# Challenge state is partitioned by an opaque browser-tab id. Verdict calls
# still locate the entry by their nonce, so a provider does not need to know
# the tab id. The legacy singular names remain as compatibility snapshots for
# older tests/in-process callers; they are never the authority for lookup.
PYR_CONTEXT_CHALLENGES: dict[str, dict[str, object]] = {}
PYR_DUNGEON_CHALLENGES: dict[str, dict[str, object]] = {}
PYR_CONTEXT_CHALLENGE: dict[str, object] | None = None
PYR_DUNGEON_CHALLENGE: dict[str, object] | None = None
PYR_PRACTICE_CHALLENGES: dict[str, dict[str, object]] = {}

app = FastAPI(title="Python Quest Lab Local Server", version="0.4.0")


@app.on_event("startup")
def _startup_extend_campaign() -> None:
    extend_campaign_on_startup()


app.add_middleware(TrustedHostMiddleware, allowed_hosts=list(allowed_hosts()))
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(ALLOWED_ORIGINS),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FileWrite(BaseModel):
    path: str
    content: str


class TutorWrite(BaseModel):
    content: str


class StateCustodyMigrationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_source_revision: int = Field(ge=0)
    confirmation_token: str = Field(min_length=1, max_length=64)


class FormatRequest(BaseModel):
    path: str
    content: str


class HomesteadPurchase(BaseModel):
    item_id: str


class CampaignMarketPurchase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class HomesteadEquip(BaseModel):
    item_id: str


class HomesteadRoomUpgrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    upgrade_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class HomeRoomPurchase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    room_id: Literal["great_hall", "library", "armory", "pantry", "gallery", "war_room", "den"]
    expected_level: int = Field(ge=0, le=9, strict=True)


class HomesteadAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["recover", "bandage", "meal", "feed_pyr", "train_pyr", "spend_token"]


class EquipmentEquip(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class CodexNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entry_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    note: str = Field(min_length=1, max_length=MAX_CODEX_NOTE_BYTES)


class WorkspaceNoteWrite(BaseModel):
    """A bounded Markdown note stored in the workspace notes directory.

    Workspace notes are deliberately separate from ``progress.json``. They
    are user-authored learning artifacts that can be transferred with the
    project, while progression and rewards continue to flow through the
    canonical state gateway.
    """

    model_config = ConfigDict(extra="forbid")

    content: str = Field(default="", max_length=MAX_WORKSPACE_NOTE_BYTES)


class WorkspaceTransferRequest(BaseModel):
    """Explicit UI control for the separate source-file transfer channel."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["push", "pull_preview", "pull_apply"]
    confirmation: str | None = Field(default=None, max_length=64)
    allow_overwrite: bool = False


class PyrContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_path: str | None = Field(default=None, max_length=240)
    selection: str = Field(default="", max_length=64_000)
    terminal_tail: str = Field(default="", max_length=64_000)
    client_id: str = Field(default="default", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class PyrVerdictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    submission_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    verdict: Literal["correct", "incorrect"]
    objective_id: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)
    evidence_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)


class PyrBattleSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    objective_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer: str = Field(min_length=1, max_length=20_000)
    answer_source: Literal["manual", "forge_active_file"] = "manual"
    source_path: str | None = Field(default=None, max_length=240)
    file_digest: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class PyrBossSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    requirement_id: Literal["required_behavior", "explanation", "edge_cases", "twist_2", "twist_3", "twist_4", "read_2", "interview"]
    answer: str = Field(min_length=1, max_length=20_000)
    answer_source: Literal["manual", "forge_active_file"] = "manual"
    source_path: str | None = Field(default=None, max_length=240)
    file_digest: str | None = Field(default=None, min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")


class PyrBossVerdictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    submission_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    verdict: Literal["correct", "incorrect"]
    requirement_id: Literal["required_behavior", "explanation", "edge_cases", "twist_2", "twist_3", "twist_4", "read_2", "interview"]
    evidence_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)


class DungeonStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)
    seed: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)
    class_id: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)
    region_id: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonChooseRoomRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    choice_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonEditorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    question_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    content: str = Field(max_length=MAX_DUNGEON_EDITOR_BYTES)


class DungeonRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonCampActionRequest(DungeonRunRequest):
    action: Literal["rest", "bandage", "cook", "sharpen", "fortify", "tonic"]


class DungeonMarketRequest(DungeonRunRequest):
    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonEquipRequest(DungeonRunRequest):
    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonOilRequest(DungeonRunRequest):
    oil_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonTravelRequest(DungeonRunRequest):
    node_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class PyrDungeonSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    question_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer: str = Field(min_length=1, max_length=MAX_DUNGEON_EDITOR_BYTES)


class PyrDungeonVerdictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    submission_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    verdict: Literal["correct", "incorrect"]
    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    question_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    evidence_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)


class PracticeStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    question_type: Literal["true_false", "multiple_choice", "short_explanation", "code_trace", "bug_hunt"]
    difficulty: int = Field(ge=1, le=5)


class PyrPracticeSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer: str = Field(min_length=1, max_length=20_000)


class PyrPracticeVerdictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    submission_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    verdict: Literal["correct", "incorrect", "reviewed"]
    session_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    evidence_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)


def safe_path(relative: str) -> Path:
    relative = relative.strip().lstrip("/\\")
    if not relative:
        raise HTTPException(status_code=400, detail="A relative path is required")
    candidate = (WORKSPACE / relative).resolve()
    try:
        candidate.relative_to(WORKSPACE)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Path escapes the quest workspace") from exc
    return candidate


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
        return fallback


def legacy_progress_path() -> Path:
    return (WORKSPACE / "progress.json").resolve()


def workspace_notes_root(*, create: bool = False) -> Path:
    """Resolve the one controlled workspace directory for Codex Markdown.

    The directory is intentionally derived from ``WORKSPACE`` at request time
    because tests and embedded launchers may swap the configured workspace.
    A symlinked directory is rejected so a note cannot escape the workspace.
    """

    workspace = WORKSPACE.resolve()
    raw_root = WORKSPACE / NOTES_DIR_NAME
    if raw_root.exists() and raw_root.is_symlink():
        raise HTTPException(status_code=409, detail="The workspace notes directory may not be a symlink")
    root = raw_root.resolve()
    try:
        root.relative_to(workspace)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="The workspace notes directory escaped the quest workspace") from exc
    if root.exists() and not root.is_dir():
        raise HTTPException(status_code=409, detail="The workspace notes path is not a directory")
    if create:
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="The workspace notes directory could not be created") from exc
    return root


def workspace_note_identifier(value: str) -> str:
    """Normalize one flat, safe concept slug used as ``notes/<slug>.md``."""

    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail="concept_id must be text")
    candidate = value.strip().casefold()
    if not candidate or len(candidate) > MAX_IDENTIFIER_LENGTH or not re.fullmatch(NOTE_IDENTIFIER_PATTERN, candidate):
        raise HTTPException(status_code=422, detail="concept_id must be a flat safe identifier")
    return candidate


def workspace_note_path(concept_id: str, *, create: bool = False) -> tuple[str, Path]:
    """Return a safe relative path and resolved path for one concept note."""

    identifier = workspace_note_identifier(concept_id)
    root = workspace_notes_root(create=create)
    raw_target = root / f"{identifier}.md"
    if raw_target.exists() and raw_target.is_symlink():
        raise HTTPException(status_code=409, detail="A workspace note may not be a symlink")
    target = raw_target.resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="The workspace note escaped the notes directory") from exc
    return f"{NOTES_DIR_NAME}/{identifier}.md", target


def workspace_note_revision(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def normalize_workspace_note(content: str) -> str:
    if not isinstance(content, str) or "\x00" in content:
        raise HTTPException(status_code=422, detail="Workspace notes must be valid text without NUL characters")
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    if any(ord(character) < 32 and character not in {"\n", "\t"} for character in normalized):
        raise HTTPException(status_code=422, detail="Workspace notes contain unsupported control characters")
    try:
        encoded = normalized.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise HTTPException(status_code=422, detail="Workspace note is not valid UTF-8") from exc
    if len(encoded) > MAX_WORKSPACE_NOTE_BYTES:
        raise HTTPException(status_code=413, detail="Workspace note is too large")
    return normalized


def read_workspace_note(concept_id: str) -> dict[str, object]:
    relative, target = workspace_note_path(concept_id)
    identifier = workspace_note_identifier(concept_id)
    if not target.exists():
        return {
            "concept_id": identifier,
            "path": relative,
            "content": "",
            "bytes": 0,
            "revision": workspace_note_revision(""),
            "exists": False,
        }
    if not target.is_file():
        raise HTTPException(status_code=409, detail="Workspace note is not a regular file")
    try:
        if target.stat().st_size > MAX_WORKSPACE_NOTE_BYTES:
            raise HTTPException(status_code=413, detail="Workspace note is too large")
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="Workspace notes must be UTF-8 Markdown") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="Workspace note could not be read") from exc
    content = normalize_workspace_note(content)
    return {
        "concept_id": identifier,
        "path": relative,
        "content": content,
        "bytes": len(content.encode("utf-8")),
        "revision": workspace_note_revision(content),
        "exists": True,
    }


def write_workspace_note(concept_id: str, content: str) -> dict[str, object]:
    normalized = normalize_workspace_note(content)
    relative, target = workspace_note_path(concept_id, create=True)
    identifier = workspace_note_identifier(concept_id)
    try:
        # Write beside the destination and replace atomically so a browser
        # refresh never sees a partially-written Markdown note. ``delete`` is
        # intentionally false because Windows cannot replace an open handle.
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=str(target.parent),
            prefix=f".{identifier}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(normalized)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
    except OSError as exc:
        try:
            temporary.unlink(missing_ok=True)
        except (UnboundLocalError, OSError):
            pass
        raise HTTPException(status_code=500, detail="Workspace note could not be written") from exc
    return {
        "concept_id": identifier,
        "path": relative,
        "content": normalized,
        "bytes": len(normalized.encode("utf-8")),
        "revision": workspace_note_revision(normalized),
        "exists": True,
    }


def state_path_kind(target: Path) -> str | None:
    canonical = PROGRESS_PATH.resolve()
    if target.resolve() == canonical:
        return "canonical"
    if target.resolve() == legacy_progress_path() and target.resolve() != canonical:
        return "legacy"
    if target.resolve() == DUNGEON_PATH.resolve():
        return "dungeon_projection"
    if target.resolve() == (WORKSPACE / TUTOR_PATH.name).resolve():
        return "tutor_legacy"
    try:
        target.resolve().relative_to(workspace_notes_root())
    except (HTTPException, ValueError):
        pass
    else:
        return "workspace_note"
    return None


def reject_state_file_access(target: Path, *, allow_dungeon_projection: bool = False) -> None:
    kind = state_path_kind(target)
    if kind:
        if kind == "legacy":
            raise HTTPException(
                status_code=403,
                detail="workspace progress.json is legacy data; use the local state service and canonical repo state",
            )
        if kind == "dungeon_projection":
            if allow_dungeon_projection:
                return
            raise HTTPException(
                status_code=403,
                detail="dungeon.py is a state-service projection; use the Dungeon checkpoint endpoint",
            )
        if kind == "tutor_legacy":
            raise HTTPException(
                status_code=403,
                detail="tutor.py is managed by the Campaign Tutor Notebook; use its dedicated endpoint",
            )
        if kind == "workspace_note":
            raise HTTPException(
                status_code=403,
                detail="Codex notes are managed by the dedicated workspace notes endpoint",
            )
        raise HTTPException(status_code=403, detail="progress.json is managed by the local state service")


def local_device_id() -> str:
    return opaque_device_id()


def tutor_revision(content: str) -> str:
    """Return a deterministic local revision for external tutor-file polling."""

    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def write_progress_atomic(progress: dict) -> dict:
    return STATE_SERVICE.persist(progress)


def load_progress() -> dict:
    progress = read_json(PROGRESS_PATH, {})
    if not progress:
        raise HTTPException(status_code=500, detail="progress.json could not be loaded")
    return progress


def ensure_tutor_file() -> Path:
    try:
        TUTOR_PATH.relative_to(WORKSPACE)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Tutor notebook path escaped the workspace") from exc
    if not TUTOR_PATH.exists():
        TUTOR_PATH.write_text(TUTOR_TEMPLATE, encoding="utf-8")
    return TUTOR_PATH


def write_dungeon_projection(content: str) -> None:
    """Materialize the canonical current-run buffer as a controlled cache."""

    try:
        DUNGEON_PATH.relative_to(WORKSPACE)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail="Dungeon projection path escaped the workspace") from exc
    DUNGEON_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = DUNGEON_PATH.with_suffix(DUNGEON_PATH.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(DUNGEON_PATH)


def sync_dungeon_projection(progress: dict) -> dict:
    """Write only the current canonical run buffer and return its projection."""

    projection = STATE_SERVICE.dungeon_projection(progress)
    write_dungeon_projection(projection.get("editor_content", "") if projection.get("active") else "")
    return projection


def safe_campaign_dungeon_projection(progress: dict) -> dict:
    """Keep a Dungeon-only corruption from taking down the campaign HUD."""

    try:
        return sync_dungeon_projection(progress)
    except StateCommandError as exc:
        return {
            "active": False,
            "status": "invalid",
            "editor_content": "",
            "error": exc.detail,
        }
    except HTTPException:
        # A test or a legacy launcher can temporarily point DUNGEON_PATH at a
        # path outside its current WORKSPACE. Keep the campaign projection
        # available; the next correctly configured Dungeon request will
        # materialize the controlled cache.
        try:
            return STATE_SERVICE.dungeon_projection(progress)
        except StateCommandError as exc:
            return {
                "active": False,
                "status": "invalid",
                "editor_content": "",
                "error": exc.detail,
            }


def git_info(root: Path | None = None, *, include_upstream: bool = False) -> dict:
    git_root = (root or WORKSPACE).resolve()

    def run(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(git_root), *args],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ""

    branch = run("branch", "--show-current") or "detached"
    status_lines = [line for line in run("status", "--short").splitlines() if line.strip()]
    info = {
        "root": str(git_root),
        "branch": branch,
        "dirty_count": len(status_lines),
        "status": status_lines[:50],
        "last_commit": run("log", "-1", "--pretty=%h %s"),
    }
    if include_upstream:
        head_sha = run("rev-parse", "HEAD")
        upstream_ref = run("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        upstream_sha = run("rev-parse", "@{u}") if upstream_ref else ""
        ahead = behind = 0
        counts = run("rev-list", "--left-right", "--count", "HEAD...@{u}") if upstream_ref else ""
        if counts:
            try:
                ahead, behind = (int(value) for value in counts.split())
            except (TypeError, ValueError):
                ahead = behind = 0
        info.update(
            {
                "head_sha": head_sha,
                "upstream_ref": upstream_ref or None,
                "upstream_sha": upstream_sha or None,
                "upstream_available": bool(upstream_ref and upstream_sha),
                "ahead_upstream": ahead,
                "behind_upstream": behind,
            }
        )
    return info


def build_tree() -> list[dict]:
    items: list[dict] = []
    max_depth = 5

    def walk(folder: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            children = sorted(folder.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
        except OSError:
            return

        for child in children:
            # A workspace progress.json is legacy evidence, never a file the
            # learner should open or mistake for the canonical state save.
            # Keep it out of the tree as well as rejecting direct file access.
            # This prevents a stray edit from looking like a second live save.
            if child.name in IGNORED_DIRS or child.name == "progress.json" or child.name.startswith(".DS_Store"):
                continue
            # The platform's own files sit at the workspace root; the same
            # names inside a project (silver_reels/notes/) are the learner's.
            if depth == 0 and child.name in {DUNGEON_PATH.name, f"{DUNGEON_PATH.name}.tmp", TUTOR_PATH.name, NOTES_DIR_NAME}:
                continue
            # Do not follow symlinks while projecting the workspace. A linked
            # directory can escape the checkout and flood the tree with host
            # files; the file API still enforces the same safe workspace root.
            if child.is_symlink():
                continue
            try:
                relative = child.relative_to(WORKSPACE).as_posix()
            except ValueError:
                continue
            if child.is_dir():
                items.append({"name": child.name, "path": relative, "type": "dir", "depth": depth})
                walk(child, depth + 1)
            elif child.is_file():
                items.append({"name": child.name, "path": relative, "type": "file", "depth": depth})

    walk(WORKSPACE, 0)
    return items


def resolve_shell() -> str:
    requested = os.getenv("SHELL", "").strip()
    if requested and Path(requested).exists():
        return requested
    for name in ("bash", "fish", "zsh", "sh"):
        found = shutil.which(name)
        if found:
            return found
    return "/bin/sh"


def set_pty_size(fd: int, cols: int, rows: int) -> None:
    cols = max(20, min(int(cols), 500))
    rows = max(5, min(int(rows), 200))
    packed = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, packed)


def child_exited(pid: int) -> bool:
    try:
        finished, _ = os.waitpid(pid, os.WNOHANG)
        return finished == pid
    except ChildProcessError:
        return True


def shell_argv(shell: str) -> list[str]:
    name = Path(shell).name
    if name in {"bash", "zsh", "fish"}:
        return [shell, "-l"]
    return [shell]


def terminal_environment(role: str) -> dict[str, str]:
    """Build a PTY environment that can reach the same state authority.

    Terminals intentionally run in the player quest workspace so normal code
    and Git commands stay local.  That cwd must not determine where state
    commands import from or where they save: expose the platform package,
    backend port and canonical/legacy diagnostics explicitly instead.
    """

    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["QUESTLAB_WORKSPACE"] = str(WORKSPACE)
    env["QUESTLAB_REPO_ROOT"] = str(REPO_ROOT)
    env["QUESTLAB_STATE_PATH"] = str(PROGRESS_PATH)
    env["QUESTLAB_CANONICAL_STATE_PATH"] = str(PROGRESS_PATH)
    env["QUESTLAB_LEGACY_STATE_PATH"] = str(legacy_progress_path())
    env["QUESTLAB_BACKEND_PORT"] = os.getenv("QUESTLAB_BACKEND_PORT", "7331")
    env["QUESTLAB_FRONTEND_PORT"] = os.getenv("QUESTLAB_FRONTEND_PORT", "5173")
    env["QUESTLAB_TERMINAL_ROLE"] = role
    env["QUESTLAB_PYTHON"] = sys.executable
    env["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(REPO_ROOT), env.get("PYTHONPATH", "")) if item
    )
    # Keep inherited tools ahead of repository files.  Appending REPO_ROOT
    # keeps an editable workspace from shadowing `python`, `git`, or another
    # command with an accidental file; the Quest Lab wrapper remains
    # discoverable at the end of PATH without changing normal resolution.
    env["PATH"] = os.pathsep.join(
        item for item in (env.get("PATH", ""), str(REPO_ROOT)) if item
    )
    return env


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "version": app.version,
        "workspace": str(WORKSPACE),
        "repo_root": str(REPO_ROOT),
    }


@app.get("/api/runtime")
def runtime():
    shell = resolve_shell()
    workspace_git = git_info(WORKSPACE)
    repo_git = git_info(REPO_ROOT, include_upstream=True)
    return {
        "shell": shell,
        "python": sys.executable,
        "workspace": str(WORKSPACE),
        "repo_root": str(REPO_ROOT),
        "sync_storage_namespace": checkout_storage_namespace(),
        "canonical_state_path": str(PROGRESS_PATH),
        "legacy_state_path": str(legacy_progress_path()),
        "expected_branch": os.getenv("QUESTLAB_EXPECTED_BRANCH", "feature/cloud-sync-desktop"),
        "workspace_git": workspace_git,
        "repo_git": repo_git,
        "state_authority": state_authority_info(PROGRESS_PATH, WORKSPACE),
        "state_custody": local_state_custody_report(),
        "commands": {
            "python3": command_available("python3"),
            "git": command_available("git"),
            "codex": command_available("codex"),
            "claude": command_available("claude"),
            "agy": command_available("agy"),
            "copilot": command_available("copilot"),
            "ruff": importlib.util.find_spec("ruff") is not None,
        },
    }


def _without_identify_answer(progress: dict) -> dict:
    """The browser never sees a vial reading's answer key."""

    hunter = progress.get("hunter")
    if not isinstance(hunter, dict) or not isinstance(hunter.get("identify"), dict):
        return progress
    puzzle = {key: value for key, value in hunter["identify"].items() if key not in {"answer", "answer_text", "why"}}
    return {**progress, "hunter": {**hunter, "identify": puzzle}}


@app.get("/api/campaign")
def campaign():
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    # Reads see the save brought up to the authored campaign (new contracts
    # and projects); the next state action persists the same extension.
    progress = STATE_SERVICE.campaign_view(progress)
    try:
        home_rooms = STATE_SERVICE.home_room_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    progress.setdefault("homestead", {})["room_levels"] = home_rooms["levels"]
    dungeon_projection = safe_campaign_dungeon_projection(progress)
    activity = read_json(REPO_ROOT / "activity.json", {})
    return {
        "home_rooms": home_rooms,
        "campaign_board": STATE_SERVICE.campaign_board(progress),
        "armory": STATE_SERVICE.armory_projection(progress),
        "spar_roster": STATE_SERVICE.spar_roster(progress),
        "progress": _without_identify_answer(progress),
        "revision": metadata["revision"],
        "sync_storage_namespace": checkout_storage_namespace(),
        "equipment_projection": STATE_SERVICE.equipment_projection(progress),
        "campaign_market": [dict(item) for item in CAMPAIGN_MARKET_CATALOG],
        "encounter": STATE_SERVICE.encounter_projection(progress),
        "codex_projection": STATE_SERVICE.codex_projection(progress),
        "practice_projection": STATE_SERVICE.practice_projection(progress),
        "dungeon": dungeon_projection,
        "hunter_projection": STATE_SERVICE.hunter_projection(progress),
        "activity": activity,
        "git": git_info(),
        "repo_git": git_info(REPO_ROOT),
        "workspace": str(WORKSPACE),
        "repo_root": str(REPO_ROOT),
        "state_authority": state_authority_info(PROGRESS_PATH, WORKSPACE),
    }


@app.get("/api/dungeon")
def dungeon():
    """Return the restart-safe Dungeon run and materialize its editor cache."""

    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = sync_dungeon_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {
        "ok": True,
        "revision": metadata["revision"],
        "dungeon": projection,
        "file": {"path": "dungeon.py", "content": projection.get("editor_content", "")},
    }


@app.post("/api/dungeon/start")
def start_dungeon(payload: DungeonStartRequest):
    envelope = _apply_state_or_http("dungeon_start_run", payload.model_dump(exclude_none=True), "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = sync_dungeon_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"dungeon": projection, "file": {"path": "dungeon.py", "content": projection.get("editor_content", "")}})
    result["revision"] = metadata["revision"]
    return result


@app.post("/api/dungeon/choose")
def choose_dungeon_room(payload: DungeonChooseRoomRequest):
    return _dungeon_player_action("dungeon_choose_room", payload.model_dump())


@app.put("/api/dungeon/editor")
def save_dungeon_editor(payload: DungeonEditorRequest):
    envelope = _apply_state_or_http("dungeon_save_editor", payload.model_dump(), "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = sync_dungeon_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"dungeon": projection, "file": {"path": "dungeon.py", "content": projection.get("editor_content", "")}})
    result["revision"] = metadata["revision"]
    return result


def _dungeon_player_action(action: str, payload: dict) -> dict:
    envelope = _apply_state_or_http(action, payload, "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = sync_dungeon_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"dungeon": projection, "revision": metadata["revision"]})
    return result


@app.post("/api/dungeon/rest")
def use_dungeon_rest(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_use_rest", payload.model_dump())


@app.post("/api/dungeon/camp")
def use_dungeon_camp_action(payload: DungeonCampActionRequest):
    return _dungeon_player_action("dungeon_camp_action", payload.model_dump())


@app.post("/api/dungeon/risk/reveal")
def reveal_dungeon_risk(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_reveal_risk", payload.model_dump())


@app.post("/api/dungeon/risk/enter")
def enter_dungeon_risk(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_enter_risk", payload.model_dump())


@app.post("/api/dungeon/market")
def purchase_dungeon_market(payload: DungeonMarketRequest):
    return _dungeon_player_action("dungeon_market_purchase", payload.model_dump())


@app.post("/api/dungeon/equip")
def equip_dungeon_item(payload: DungeonEquipRequest):
    return _dungeon_player_action("dungeon_equip_item", payload.model_dump())


@app.post("/api/dungeon/oil")
def apply_dungeon_oil(payload: DungeonOilRequest):
    return _dungeon_player_action("dungeon_apply_oil", payload.model_dump())


@app.post("/api/dungeon/travel")
def travel_dungeon_map(payload: DungeonTravelRequest):
    return _dungeon_player_action("dungeon_travel", payload.model_dump())


@app.post("/api/dungeon/leave")
def leave_dungeon_room(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_leave_room", payload.model_dump())


@app.post("/api/dungeon/finish")
def finish_dungeon_run(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_finish_run", payload.model_dump())


@app.post("/api/dungeon/reset")
def reset_dungeon_run(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_reset_run", payload.model_dump())


@app.get("/api/practice")
def practice():
    """Return the answer-free Tutor/Practice projection and selectors."""

    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = STATE_SERVICE.practice_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {
        "ok": True,
        "revision": metadata["revision"],
        "practice": projection,
        "tutor": {
            "file": "tutor.py",
            "notes_directory": projection["notes_directory"],
        },
    }


@app.post("/api/practice/session")
def start_practice_session(payload: PracticeStartRequest):
    envelope = _apply_state_or_http(
        "practice_session_started",
        payload.model_dump(),
        "player",
    )
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = STATE_SERVICE.practice_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"practice": projection, "revision": metadata["revision"]})
    return result


@app.get("/api/state/revision")
def state_revision():
    try:
        metadata = STATE_SERVICE.metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {
        **metadata,
        "sync_storage_namespace": checkout_storage_namespace(),
        "state_authority": state_authority_info(PROGRESS_PATH, WORKSPACE),
    }


@app.get("/api/state/custody")
def state_custody():
    """Return a read-only preview of the opt-in local custody destination."""

    return local_state_custody_report()


@app.post("/api/state/custody/migrate")
def migrate_state_custody(payload: StateCustodyMigrationRequest):
    """Copy the reviewed canonical snapshot to the derived local cache."""

    destination = proposed_local_state_path()
    forbidden_paths = (PROGRESS_PATH, legacy_progress_path())
    try:
        return STATE_SERVICE.migrate_local_state(
            destination,
            expected_source_revision=payload.expected_source_revision,
            confirmation_token=payload.confirmation_token,
            forbidden_paths=forbidden_paths,
        )
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/api/state/sync")
def state_sync_snapshot():
    try:
        projection, metadata = STATE_SERVICE.sync_snapshot()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"projection": projection, "revision": metadata["revision"], "metadata": metadata}


@app.post("/api/state/sync/apply")
def apply_cloud_state(payload: StateSyncApplyRequest):
    try:
        return STATE_SERVICE.apply_cloud_projection(
            payload.projection,
            expected_revision=payload.expected_revision,
            cloud_revision=payload.cloud_revision,
        )
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@app.get("/api/state/legacy")
def state_legacy_report():
    return legacy_state_report(PROGRESS_PATH, legacy_progress_path())


def workspace_transfer_branch() -> str:
    """Return the explicit project namespace used by the source-transfer ref."""

    return os.getenv("QUESTLAB_PROJECT_BRANCH", workspace_transfer.DEFAULT_REMOTE_BRANCH).strip() or workspace_transfer.DEFAULT_REMOTE_BRANCH


def workspace_transfer_response(result: dict[str, object]) -> dict[str, object]:
    """Keep transfer responses useful without exposing local absolute paths."""

    response = dict(result)
    response.pop("workspace", None)
    backup_directory = response.pop("backup_directory", None)
    if backup_directory is not None:
        response["backup_created"] = True
    return response


def workspace_transfer_error(exc: workspace_transfer.TransferError) -> HTTPException:
    return HTTPException(status_code=409, detail=str(exc))


@app.get("/api/workspace-transfer")
def workspace_transfer_status():
    """Preview allowlisted source/notes transfer state without writing files."""

    try:
        result = workspace_transfer.status(
            WORKSPACE,
            remote=os.getenv("QUESTLAB_TRANSFER_REMOTE", workspace_transfer.DEFAULT_REMOTE),
            remote_branch=workspace_transfer_branch(),
        )
    except workspace_transfer.TransferError as exc:
        raise workspace_transfer_error(exc) from exc
    return workspace_transfer_response(result)


@app.post("/api/workspace-transfer")
def apply_workspace_transfer(payload: WorkspaceTransferRequest):
    """Push or pull only the explicit source-transfer allowlist.

    Progression state, session logs and PTY data are never part of this
    channel. Pull writes remain confirmation-token gated and conflicts require
    a second explicit overwrite opt-in in the UI/CLI.
    """

    remote = os.getenv("QUESTLAB_TRANSFER_REMOTE", workspace_transfer.DEFAULT_REMOTE)
    branch = workspace_transfer_branch()
    try:
        if payload.action == "push":
            if payload.confirmation != workspace_transfer.CONFIRM_PUSH:
                raise HTTPException(status_code=400, detail=f"Push requires {workspace_transfer.CONFIRM_PUSH}")
            result = workspace_transfer.push(
                WORKSPACE,
                remote=remote,
                remote_branch=branch,
                confirmation=payload.confirmation,
            )
        elif payload.action == "pull_preview":
            result = workspace_transfer.pull(
                WORKSPACE,
                remote=remote,
                remote_branch=branch,
            )
        else:
            if payload.confirmation != workspace_transfer.CONFIRM_PULL:
                raise HTTPException(status_code=400, detail=f"Pull requires {workspace_transfer.CONFIRM_PULL}")
            result = workspace_transfer.pull(
                WORKSPACE,
                remote=remote,
                remote_branch=branch,
                confirmation=payload.confirmation,
                allow_overwrite=payload.allow_overwrite,
            )
    except workspace_transfer.TransferError as exc:
        raise workspace_transfer_error(exc) from exc
    return workspace_transfer_response(result)


@app.get("/api/codex")
def codex():
    """Return the generic concept library and validated encounter records."""

    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = STATE_SERVICE.codex_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {
        "ok": True,
        "revision": metadata["revision"],
        "codex": projection,
        "notes": {
            "directory": NOTES_DIR_NAME,
            "extension": ".md",
            "max_bytes": MAX_WORKSPACE_NOTE_BYTES,
        },
    }


PYR_VERDICT_TTL_SECONDS = 300


def _pyr_client_id(value: str | None) -> str:
    """Normalize the opaque per-tab challenge partition key."""

    candidate = (value or "default").strip()
    if not candidate or len(candidate) > 128 or any(
        character not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._:-"
        for character in candidate
    ):
        return "default"
    return candidate


def _prune_pyr_challenges(now: float | None = None) -> None:
    """Drop expired tab challenges without touching another tab's state."""

    current = time.monotonic() if now is None else now
    for store in (PYR_CONTEXT_CHALLENGES, PYR_DUNGEON_CHALLENGES):
        for client_id, challenge in list(store.items()):
            if not isinstance(challenge, dict) or float(challenge.get("expires_at", 0)) <= current:
                store.pop(client_id, None)


def _challenge_by_nonce(
    store: dict[str, dict[str, object]], nonce: str, *, legacy: dict[str, object] | None = None
) -> tuple[str | None, dict[str, object] | None]:
    """Find a challenge by its provider-facing nonce under the lock."""

    _prune_pyr_challenges()
    for client_id, challenge in store.items():
        if isinstance(challenge, dict) and challenge.get("nonce") == nonce:
            return client_id, challenge
    # Preserve compatibility for old in-process callers that set the singular
    # snapshot directly while the new partitioned map is empty.
    if isinstance(legacy, dict) and legacy.get("nonce") == nonce:
        return "default", legacy
    return None, None


def _clear_challenge(store: dict[str, dict[str, object]], client_id: str | None) -> None:
    if client_id is not None:
        store.pop(client_id, None)


def _attach_pyr_verdict_challenge(
    context: dict,
    *,
    revision: int,
    encounter: dict | None,
    client_id: str,
    rotate: bool,
) -> None:
    """Attach one short-lived challenge for a trusted PYR verdict call."""

    global PYR_CONTEXT_CHALLENGE
    client_key = _pyr_client_id(client_id)
    if not isinstance(encounter, dict):
        with PYR_CONTEXT_LOCK:
            _clear_challenge(PYR_CONTEXT_CHALLENGES, client_key)
            if client_key == "default":
                PYR_CONTEXT_CHALLENGE = None
        context["verdict"] = None
        return

    project_id = encounter.get("project_id")
    mob_name = encounter.get("mob_name")
    active_file = context.get("active_file")
    active_path = active_file.get("path") if isinstance(active_file, dict) else None
    active_file_digest = active_file.get("digest") if isinstance(active_file, dict) else None
    boss_mode = encounter.get("status") == "boss_available" or encounter.get("boss_status") == "available"
    boss_name = encounter.get("boss") if boss_mode else None
    if not project_id or (not mob_name and not boss_mode):
        with PYR_CONTEXT_LOCK:
            _clear_challenge(PYR_CONTEXT_CHALLENGES, client_key)
            if client_key == "default":
                PYR_CONTEXT_CHALLENGE = None
        context["verdict"] = None
        return

    now = time.monotonic()
    with PYR_CONTEXT_LOCK:
        _prune_pyr_challenges(now)
        if client_key == "default" and PYR_CONTEXT_CHALLENGE is None:
            PYR_CONTEXT_CHALLENGES.pop(client_key, None)
        existing = PYR_CONTEXT_CHALLENGES.get(client_key)
        if existing is None and client_key == "default" and isinstance(PYR_CONTEXT_CHALLENGE, dict):
            existing = PYR_CONTEXT_CHALLENGE
        valid_existing = (
            isinstance(existing, dict)
            and existing.get("revision") == revision
            and existing.get("project_id") == project_id
            and existing.get("challenge_type") == ("boss" if boss_mode else "battle")
            and (existing.get("boss_name") == boss_name if boss_mode else existing.get("mob_name") == mob_name)
            and existing.get("active_path") == active_path
            and existing.get("active_file_digest") == active_file_digest
            and float(existing.get("expires_at", 0)) > now
        )
        # Keep an issued answer-bound challenge stable while the user submits
        # the prompt to the provider. A background/context refresh must not
        # invalidate the only pending Battle answer; a completed verdict still
        # clears the challenge before a fresh one can be issued.
        if rotate and valid_existing and (existing.get("submission_id") or existing.get("boss_submissions") or existing.get("boss_verified")):
            rotate = False
        if rotate or not valid_existing:
            existing = {
                "nonce": secrets.token_urlsafe(24),
                "client_id": client_key,
                "revision": revision,
                "project_id": project_id,
                "challenge_type": "boss" if boss_mode else "battle",
                "active_path": active_path,
                "active_file_digest": active_file_digest,
                "expires_at": now + PYR_VERDICT_TTL_SECONDS,
            }
            if boss_mode:
                verified_requirements = encounter.get("verified_boss_requirements", [])
                existing.update({"boss_name": boss_name, "boss_submissions": {}, "boss_verified": {}})
                if isinstance(verified_requirements, list):
                    existing["boss_verified"] = {
                        requirement: {"state": "recorded"}
                        for requirement in verified_requirements
                        if requirement in BOSS_REQUIREMENTS
                    }
            else:
                existing["mob_name"] = mob_name
            PYR_CONTEXT_CHALLENGES[client_key] = existing
            PYR_CONTEXT_CHALLENGE = existing
        elif isinstance(existing, dict):
            PYR_CONTEXT_CHALLENGES[client_key] = existing
            if client_key == "default":
                PYR_CONTEXT_CHALLENGE = existing
        context["verdict"] = {
            "nonce": existing["nonce"],
            "revision": existing["revision"],
            "project_id": existing["project_id"],
            "challenge_type": existing["challenge_type"],
            "expires_in": max(0, int(float(existing["expires_at"]) - now)),
        }
        if existing.get("mob_name"):
            context["verdict"]["mob_name"] = existing["mob_name"]
        if existing.get("boss_name"):
            context["verdict"]["boss_name"] = existing["boss_name"]
            context["verdict"]["requirements"] = list(encounter.get("boss_requirements") or BOSS_REQUIREMENTS)
            context["verdict"]["verified_requirements"] = sorted(existing.get("boss_verified", {}).keys())
            current_requirement = encounter.get("boss_current_requirement")
            if isinstance(current_requirement, dict):
                context["verdict"]["current_requirement"] = current_requirement.get("id")
        if existing.get("active_path"):
            context["verdict"]["active_path"] = existing["active_path"]
        if existing.get("active_file_digest"):
            context["verdict"]["file_digest"] = existing["active_file_digest"]
        for field in ("submission_id", "objective_id", "answer_digest", "evidence_id"):
            if field in existing:
                context["verdict"][field] = existing[field]


def _attach_pyr_dungeon_challenge(
    context: dict, *, revision: int, dungeon: dict | None, client_id: str, rotate: bool
) -> None:
    """Attach a short-lived answer-bound challenge for an active Dungeon room."""

    global PYR_DUNGEON_CHALLENGE
    client_key = _pyr_client_id(client_id)
    if not isinstance(dungeon, dict) or not dungeon.get("active") or dungeon.get("room_type") not in DUNGEON_COMBAT_ROOM_TYPES:
        with PYR_CONTEXT_LOCK:
            _clear_challenge(PYR_DUNGEON_CHALLENGES, client_key)
            if client_key == "default":
                PYR_DUNGEON_CHALLENGE = None
        context["dungeon_verdict"] = None
        return
    run_id = dungeon.get("run_id")
    question = dungeon.get("question") if isinstance(dungeon.get("question"), dict) else {}
    question_id = question.get("id")
    if not isinstance(run_id, str) or not run_id.strip() or not isinstance(question_id, str) or not question_id.strip():
        with PYR_CONTEXT_LOCK:
            _clear_challenge(PYR_DUNGEON_CHALLENGES, client_key)
            if client_key == "default":
                PYR_DUNGEON_CHALLENGE = None
        context["dungeon_verdict"] = None
        return
    now = time.monotonic()
    with PYR_CONTEXT_LOCK:
        _prune_pyr_challenges(now)
        if client_key == "default" and PYR_DUNGEON_CHALLENGE is None:
            PYR_DUNGEON_CHALLENGES.pop(client_key, None)
        existing = PYR_DUNGEON_CHALLENGES.get(client_key)
        if existing is None and client_key == "default" and isinstance(PYR_DUNGEON_CHALLENGE, dict):
            existing = PYR_DUNGEON_CHALLENGE
        valid_existing = (
            isinstance(existing, dict)
            and existing.get("revision") == revision
            and existing.get("run_id") == run_id
            and existing.get("question_id") == question_id
            and float(existing.get("expires_at", 0)) > now
        )
        if rotate and valid_existing and existing.get("submission_id"):
            rotate = False
        if rotate or not valid_existing:
            existing = {
                "nonce": secrets.token_urlsafe(24),
                "client_id": client_key,
                "revision": revision,
                "run_id": run_id,
                "question_id": question_id,
                "question_type": str(question.get("question_type") or "question"),
                "concept_id": str(question.get("concept_id") or "python-basics"),
                "expires_at": now + PYR_VERDICT_TTL_SECONDS,
            }
            PYR_DUNGEON_CHALLENGES[client_key] = existing
            PYR_DUNGEON_CHALLENGE = existing
        elif isinstance(existing, dict):
            PYR_DUNGEON_CHALLENGES[client_key] = existing
            if client_key == "default":
                PYR_DUNGEON_CHALLENGE = existing
        context["dungeon_verdict"] = {
            "nonce": existing["nonce"],
            "revision": existing["revision"],
            "run_id": existing["run_id"],
            "question_id": existing["question_id"],
            "question_type": existing["question_type"],
            "concept_id": existing["concept_id"],
            "expires_in": max(0, int(float(existing["expires_at"]) - now)),
        }
        for field in ("submission_id", "answer_digest", "evidence_id"):
            if field in existing:
                context["dungeon_verdict"][field] = existing[field]


def _capture_pyr_context(payload: PyrContextRequest, *, rotate_challenge: bool = False) -> dict:
    client_id = _pyr_client_id(payload.client_id)
    active_path = payload.active_path.strip() if payload.active_path else ""
    if len(active_path) > 240 or any(ord(character) < 32 for character in active_path):
        raise HTTPException(status_code=422, detail="active_path must be a bounded relative path")

    normalized_path: str | None = None
    active_file = None
    if active_path:
        if is_sensitive_path(active_path):
            raise HTTPException(status_code=403, detail="Secret-looking files cannot be sent to the PYR context bridge")
        target = safe_path(active_path)
        if target.resolve() == DUNGEON_PATH.resolve():
            try:
                sync_dungeon_projection(STATE_SERVICE.snapshot())
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        elif target.resolve() == (WORKSPACE / TUTOR_PATH.name).resolve():
            # Tutor/Practice deliberately shares tutor.py.  The context
            # bridge may read this managed notebook for a bounded prompt;
            # generic file routes still reject it and all writes use /api/tutor.
            # Do not call ensure_tutor_file here: tests and disposable
            # workspaces may replace WORKSPACE while the module-level path is
            # still bound to the original checkout. The bounded read below
            # will fail closed if this managed file is absent.
            pass
        else:
            reject_state_file_access(target)
        if not target.exists() or not target.is_file():
            raise HTTPException(status_code=404, detail="Active file not found")
        try:
            active_file = bounded_file(target)
        except ContextValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        normalized_path = target.relative_to(WORKSPACE).as_posix()

    try:
        selection, selection_truncated = bounded_text(payload.selection, "selection")
        terminal_tail, terminal_truncated = bounded_text(payload.terminal_tail, "terminal_tail")
    except ContextValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    encounter = STATE_SERVICE.encounter_projection(progress)
    try:
        dungeon = STATE_SERVICE.dungeon_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    context = build_context(
        progress=progress,
        revision=metadata["revision"],
        encounter=encounter,
        workspace=WORKSPACE,
        active_path=normalized_path,
        active_file=active_file,
        selection=selection,
        selection_truncated=selection_truncated,
        terminal_tail=terminal_tail,
        terminal_truncated=terminal_truncated,
    )
    stored_input = {
        "active_path": normalized_path,
        "selection": selection,
        "terminal_tail": terminal_tail,
        "client_id": client_id,
    }
    with PYR_CONTEXT_LOCK:
        if client_id == "default":
            # Preserve the legacy default slot for older in-process callers.
            PYR_CONTEXT_INPUT.update(stored_input)
        else:
            # Named tabs must retain their own context; another tab's POST may
            # not replace what a later GET returns for this client.
            PYR_CONTEXT_INPUTS[client_id] = stored_input
    _attach_pyr_verdict_challenge(
        context,
        revision=metadata["revision"],
        encounter=encounter,
        client_id=client_id,
        rotate=rotate_challenge,
    )
    context["dungeon"] = dungeon
    _attach_pyr_dungeon_challenge(
        context,
        revision=metadata["revision"],
        dungeon=dungeon,
        client_id=client_id,
        rotate=rotate_challenge,
    )
    return context


def _stored_pyr_context_request(client_id: str = "default") -> PyrContextRequest:
    client_key = _pyr_client_id(client_id)
    with PYR_CONTEXT_LOCK:
        if client_key == "default":
            # The singular slot remains the compatibility source for the
            # default client because existing callers/tests update it
            # directly.  Named clients never fall back to this value.
            values = dict(PYR_CONTEXT_INPUT)
        else:
            values = dict(PYR_CONTEXT_INPUTS.get(client_key, {}))
    if not values:
        values = {
            "active_path": None,
            "selection": "",
            "terminal_tail": "",
        }
    values["client_id"] = client_key
    return PyrContextRequest(**values)


@app.get("/api/pyr/context")
def read_pyr_context(client_id: str = "default"):
    """Return the latest bounded editor/terminal context and live campaign view."""

    return {
        "ok": True,
        "context": _capture_pyr_context(_stored_pyr_context_request(client_id)),
    }


@app.post("/api/pyr/context")
def write_pyr_context(payload: PyrContextRequest):
    """Capture explicit UI context for a local PYR client without mutating state."""

    return {"ok": True, "context": _capture_pyr_context(payload, rotate_challenge=True)}


def _validate_forge_submission_source(
    *, answer_source: str, source_path: str | None, file_digest: str | None, answer: str, challenge: dict[str, object]
) -> None:
    """Bind Forge submissions to the file that issued the current challenge.

    The provider still decides the verdict, but the gateway prevents a stale
    editor tab (or a different file) from being presented as the active Forge
    answer.  Manual callers remain compatible for tests and older clients.
    """

    if answer_source != "forge_active_file":
        return
    normalized = (source_path or "").strip().replace("\\", "/")
    expected = str(challenge.get("active_path") or "")
    expected_digest = str(challenge.get("active_file_digest") or "")
    filename = Path(normalized).name.lower()
    if not normalized or normalized != expected:
        raise HTTPException(status_code=409, detail="Forge file changed; capture the active Forge context again")
    if not expected_digest or (file_digest or "").lower() != expected_digest:
        raise HTTPException(status_code=409, detail="Forge file digest changed; capture the active Forge context again")
    if not normalized.lower().endswith((".py", ".md")) or filename in {"tutor.py", "dungeon.py"}:
        raise HTTPException(status_code=422, detail="Forge submissions must use an active campaign .py or .md file")
    if not answer.strip():
        raise HTTPException(status_code=422, detail="Active Forge file is empty")
    if hashlib.sha256(answer.encode("utf-8")).hexdigest() != expected_digest:
        raise HTTPException(status_code=409, detail="Forge file contents do not match the captured digest")
    try:
        current_file = bounded_file(safe_path(normalized))
    except (ContextValueError, HTTPException) as exc:
        raise HTTPException(status_code=409, detail="Forge file changed; capture the active Forge context again") from exc
    if current_file.get("digest") != expected_digest:
        raise HTTPException(status_code=409, detail="Forge file changed; capture the active Forge context again")


def _codex_code_snippet(answer: str, answer_source: str) -> str | None:
    """Return only a small learner-authored Forge excerpt for valid Codex evidence.

    Raw answers remain ephemeral until a provider verdict.  If the submitted
    answer came from the active campaign file, the state service may retain a
    bounded, control-character-clean excerpt after a correct verdict so the
    encounter record feels personal without becoming an answer archive.
    """

    if answer_source != "forge_active_file":
        return None
    snippet, _ = bounded_text(answer, "code_snippet", max_bytes=MAX_CODEX_SNIPPET_BYTES)
    return snippet.strip() or None


@app.post("/api/pyr/battle-submission")
def create_pyr_battle_submission(payload: PyrBattleSubmissionRequest):
    """Bind one bounded player answer to the current PYR challenge.

    The answer is intentionally ephemeral: it is hashed for the verdict
    boundary and is never written to canonical progress. The selected local
    provider receives the answer from the Forge UI and must return a verdict
    using the issued submission/evidence tokens.
    """

    nonce = payload.nonce.strip()
    objective_id = payload.objective_id.strip()
    try:
        answer, answer_truncated = bounded_text(payload.answer, "answer")
    except ContextValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if answer_truncated:
        raise HTTPException(status_code=413, detail="Battle answer is too large")
    if not answer.strip():
        raise HTTPException(status_code=422, detail="Battle answer must not be empty")

    global PYR_CONTEXT_CHALLENGE
    with PYR_CONTEXT_LOCK:
        client_id, challenge = _challenge_by_nonce(
            PYR_CONTEXT_CHALLENGES, nonce, legacy=PYR_CONTEXT_CHALLENGE
        )
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce:
            raise HTTPException(status_code=409, detail="PYR challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
            if client_id == "default":
                PYR_CONTEXT_CHALLENGE = None
            raise HTTPException(status_code=409, detail="PYR challenge expired; capture context again")
        if client_id is not None:
            PYR_CONTEXT_CHALLENGES[client_id] = challenge
        if challenge.get("submission_id"):
            raise HTTPException(status_code=409, detail="This PYR challenge already has a Battle submission")
        _validate_forge_submission_source(
            answer_source=payload.answer_source,
            source_path=payload.source_path,
            file_digest=payload.file_digest,
            answer=answer,
            challenge=challenge,
        )

        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                encounter = STATE_SERVICE.encounter_projection(progress)
                if metadata["revision"] != challenge.get("revision"):
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Campaign changed; capture fresh PYR context")
                if (
                    not isinstance(encounter, dict)
                    or encounter.get("project_id") != challenge.get("project_id")
                    or encounter.get("mob_name") != challenge.get("mob_name")
                ):
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Active encounter changed; capture fresh PYR context")
                objective = next(
                    (item for item in encounter.get("available_objectives", []) if isinstance(item, dict) and item.get("id") == objective_id),
                    None,
                )
                if objective is None:
                    raise HTTPException(status_code=422, detail="objective_id is not available for the active encounter")
                project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
                story = load_campaign_bounties().get(str(project.get("branch") or ""))
                folder = project_dir_name(story.get("project_dir")) if isinstance(story, dict) else ""
                graded_file = f"{folder}/{objective['file']}" if folder and objective.get("file") else objective.get("file")
                if not graded_file and project.get("multi_file") is True:
                    # In a multi-file project an unnamed goal is graded on the entry file.
                    graded_file = project.get("entry_file")
                submitted = str(payload.source_path or "").strip().replace("\\", "/")
                if graded_file and payload.answer_source == "forge_active_file" and submitted != graded_file:
                    raise HTTPException(status_code=409, detail=f"'{objective.get('label')}' is graded on {graded_file}; open it in the Forge and submit again")

                submission_id = f"battle-{secrets.token_hex(12)}"
                evidence_id = submission_id
                answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
                answer_snippet = _codex_code_snippet(answer, payload.answer_source)
                challenge.update(
                    {
                        "submission_id": submission_id,
                        "objective_id": objective_id,
                        "question_type": str(objective.get("question_type") or "verified"),
                        "impact": int(objective.get("impact") or 0),
                        "evidence_id": evidence_id,
                        "answer_digest": answer_digest,
                        "answer_snippet": answer_snippet,
                        "answer_source": payload.answer_source,
                        "source_path": payload.source_path.strip().replace("\\", "/") if payload.source_path else None,
                        "file_digest": payload.file_digest,
                    }
                )
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return {
        "ok": True,
        "submission": {
            "submission_id": submission_id,
            "nonce": nonce,
            "revision": challenge["revision"],
            "project_id": challenge["project_id"],
            "mob_name": challenge["mob_name"],
            "objective_id": objective_id,
            "question_type": challenge["question_type"],
            "impact": challenge["impact"],
            "evidence_id": evidence_id,
            "answer_digest": answer_digest,
            "answer_source": challenge.get("answer_source", "manual"),
            "source_path": challenge.get("source_path"),
            "file_digest": challenge.get("file_digest"),
            "expires_in": max(0, int(float(challenge["expires_at"]) - time.monotonic())),
        },
    }


@app.post("/api/pyr/dungeon-submission")
def create_pyr_dungeon_submission(payload: PyrDungeonSubmissionRequest):
    """Bind the current Dungeon answer before provider adjudication."""

    nonce = payload.nonce.strip()
    run_id = payload.run_id.strip()
    question_id = payload.question_id.strip()
    try:
        answer, answer_truncated = bounded_text(payload.answer, "answer", max_bytes=MAX_DUNGEON_EDITOR_BYTES)
    except ContextValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if answer_truncated:
        raise HTTPException(status_code=413, detail="Dungeon answer is too large")
    if not answer.strip():
        raise HTTPException(status_code=422, detail="Dungeon answer must not be empty")

    global PYR_DUNGEON_CHALLENGE
    with PYR_CONTEXT_LOCK:
        client_id, challenge = _challenge_by_nonce(
            PYR_DUNGEON_CHALLENGES, nonce, legacy=PYR_DUNGEON_CHALLENGE
        )
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce:
            raise HTTPException(status_code=409, detail="Dungeon challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            _clear_challenge(PYR_DUNGEON_CHALLENGES, client_id)
            if client_id == "default":
                PYR_DUNGEON_CHALLENGE = None
            raise HTTPException(status_code=409, detail="Dungeon challenge expired; capture context again")
        if client_id is not None:
            PYR_DUNGEON_CHALLENGES[client_id] = challenge
        if challenge.get("submission_id"):
            raise HTTPException(status_code=409, detail="This Dungeon challenge already has a submission")
        if challenge.get("run_id") != run_id or challenge.get("question_id") != question_id:
            raise HTTPException(status_code=409, detail="Dungeon question changed; capture current context again")
        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                projection = STATE_SERVICE.dungeon_projection(progress)
                question = projection.get("question") if isinstance(projection.get("question"), dict) else {}
                if metadata["revision"] != challenge.get("revision") or not projection.get("active") or projection.get("room_type") not in DUNGEON_COMBAT_ROOM_TYPES:
                    _clear_challenge(PYR_DUNGEON_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_DUNGEON_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Dungeon run changed; capture fresh context")
                if projection.get("run_id") != run_id or question.get("id") != question_id:
                    _clear_challenge(PYR_DUNGEON_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_DUNGEON_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Dungeon question changed; capture fresh context")
                submission_id = f"dungeon-{secrets.token_hex(12)}"
                evidence_id = submission_id
                answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
                challenge.update({"submission_id": submission_id, "evidence_id": evidence_id, "answer_digest": answer_digest})
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return {
        "ok": True,
        "submission": {
            "submission_id": submission_id,
            "nonce": nonce,
            "revision": challenge["revision"],
            "run_id": run_id,
            "question_id": question_id,
            "question_type": challenge["question_type"],
            "concept_id": challenge["concept_id"],
            "evidence_id": evidence_id,
            "answer_digest": answer_digest,
            "expires_in": max(0, int(float(challenge["expires_at"]) - time.monotonic())),
        },
    }


@app.post("/api/pyr/dungeon-verdict")
def apply_pyr_dungeon_verdict(payload: PyrDungeonVerdictRequest):
    """Apply one provider-validated Dungeon result through the gateway."""

    nonce = payload.nonce.strip()
    global PYR_DUNGEON_CHALLENGE
    with PYR_CONTEXT_LOCK:
        client_id, challenge = _challenge_by_nonce(
            PYR_DUNGEON_CHALLENGES, nonce, legacy=PYR_DUNGEON_CHALLENGE
        )
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce:
            raise HTTPException(status_code=409, detail="Dungeon verdict challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            _clear_challenge(PYR_DUNGEON_CHALLENGES, client_id)
            if client_id == "default":
                PYR_DUNGEON_CHALLENGE = None
            raise HTTPException(status_code=409, detail="Dungeon challenge expired; capture context again")
        if (
            challenge.get("submission_id") != payload.submission_id
            or challenge.get("answer_digest") != payload.answer_digest
            or challenge.get("run_id") != payload.run_id
            or challenge.get("question_id") != payload.question_id
            or challenge.get("evidence_id") != payload.evidence_id
        ):
            raise HTTPException(status_code=409, detail="Dungeon verdict does not match the pending submission")
        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                if metadata["revision"] != challenge.get("revision"):
                    _clear_challenge(PYR_DUNGEON_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_DUNGEON_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Dungeon run changed; capture fresh context")
                mutation = STATE_SERVICE.apply_internal(
                    "dungeon_record_verdict",
                    {
                        "run_id": payload.run_id,
                        "question_id": payload.question_id,
                        "verdict": payload.verdict,
                        "evidence_id": payload.evidence_id,
                        "reason": payload.reason,
                    },
                )
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        _clear_challenge(PYR_DUNGEON_CHALLENGES, client_id)
        if client_id == "default":
            PYR_DUNGEON_CHALLENGE = None
    return {"ok": True, "verdict": payload.verdict, "mutation": mutation, "revision": mutation.get("revision"), "event": mutation.get("event")}


@app.post("/api/pyr/practice-submission")
def create_pyr_practice_submission(payload: PyrPracticeSubmissionRequest):
    """Bind an optional Practice answer without storing its raw text."""

    session_id = payload.session_id.strip()
    try:
        answer, answer_truncated = bounded_text(payload.answer, "answer")
    except ContextValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if answer_truncated:
        raise HTTPException(status_code=413, detail="Practice answer is too large")
    if not answer.strip():
        raise HTTPException(status_code=422, detail="Practice answer must not be empty")

    global PYR_PRACTICE_CHALLENGES
    with PYR_CONTEXT_LOCK:
        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                history = STATE_SERVICE.practice_projection(progress)["sessions"]
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        session = next((item for item in history if item.get("session_id") == session_id), None)
        if session is None:
            raise HTTPException(status_code=404, detail="Practice session was not found")
        now = time.monotonic()
        existing = PYR_PRACTICE_CHALLENGES.get(session_id)
        if isinstance(existing, dict) and float(existing.get("expires_at", 0)) > now and existing.get("submission_id"):
            raise HTTPException(status_code=409, detail="This Practice session already has a pending submission")
        nonce = secrets.token_urlsafe(24)
        submission_id = f"practice-{secrets.token_hex(12)}"
        evidence_id = submission_id
        answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
        challenge = {
            "nonce": nonce,
            "submission_id": submission_id,
            "session_id": session_id,
            "answer_digest": answer_digest,
            "evidence_id": evidence_id,
            "revision": metadata["revision"],
            "expires_at": now + PYR_VERDICT_TTL_SECONDS,
        }
        PYR_PRACTICE_CHALLENGES[session_id] = challenge
    return {
        "ok": True,
        "submission": {
            "nonce": nonce,
            "submission_id": submission_id,
            "session_id": session_id,
            "revision": metadata["revision"],
            "evidence_id": evidence_id,
            "answer_digest": answer_digest,
            "expires_in": PYR_VERDICT_TTL_SECONDS,
        },
    }


@app.post("/api/pyr/practice-verdict")
def apply_pyr_practice_verdict(payload: PyrPracticeVerdictRequest):
    """Record a provider-validated Practice outcome with no game reward."""

    global PYR_PRACTICE_CHALLENGES
    with PYR_CONTEXT_LOCK:
        challenge = PYR_PRACTICE_CHALLENGES.get(payload.session_id)
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != payload.nonce:
            raise HTTPException(status_code=409, detail="Practice verdict challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            PYR_PRACTICE_CHALLENGES.pop(payload.session_id, None)
            raise HTTPException(status_code=409, detail="Practice challenge expired; request a fresh answer")
        if (
            challenge.get("submission_id") != payload.submission_id
            or challenge.get("answer_digest") != payload.answer_digest
            or challenge.get("evidence_id") != payload.evidence_id
        ):
            raise HTTPException(status_code=409, detail="Practice verdict does not match the pending submission")
        with PROGRESS_LOCK:
            try:
                mutation = STATE_SERVICE.apply_internal(
                    "practice_record_attempt",
                    {
                        "session_id": payload.session_id,
                        "outcome": payload.verdict,
                        "evidence_id": payload.evidence_id,
                        "reason": payload.reason,
                    },
                )
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        PYR_PRACTICE_CHALLENGES.pop(payload.session_id, None)
    return {"ok": True, "verdict": payload.verdict, "mutation": mutation, "revision": mutation.get("revision"), "event": mutation.get("event")}


@app.post("/api/pyr/boss-submission")
def create_pyr_boss_submission(payload: PyrBossSubmissionRequest):
    """Bind one answer to one of the three current boss requirements."""

    nonce = payload.nonce.strip()
    requirement_id = payload.requirement_id
    try:
        answer, answer_truncated = bounded_text(payload.answer, "answer")
    except ContextValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if answer_truncated:
        raise HTTPException(status_code=413, detail="Boss answer is too large")
    if not answer.strip():
        raise HTTPException(status_code=422, detail="Boss answer must not be empty")

    global PYR_CONTEXT_CHALLENGE
    with PYR_CONTEXT_LOCK:
        client_id, challenge = _challenge_by_nonce(
            PYR_CONTEXT_CHALLENGES, nonce, legacy=PYR_CONTEXT_CHALLENGE
        )
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce or challenge.get("challenge_type") != "boss":
            raise HTTPException(status_code=409, detail="Boss challenge is missing; capture current context again")
        if float(challenge.get("expires_at", 0)) <= now:
            _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
            if client_id == "default":
                PYR_CONTEXT_CHALLENGE = None
            raise HTTPException(status_code=409, detail="Boss challenge expired; capture context again")
        if client_id is not None:
            PYR_CONTEXT_CHALLENGES[client_id] = challenge
        submissions = challenge.setdefault("boss_submissions", {})
        verified = challenge.setdefault("boss_verified", {})
        if requirement_id in verified:
            raise HTTPException(status_code=409, detail="This boss requirement is already verified")
        if requirement_id in submissions:
            raise HTTPException(status_code=409, detail="This boss requirement already has a pending submission")
        _validate_forge_submission_source(
            answer_source=payload.answer_source,
            source_path=payload.source_path,
            file_digest=payload.file_digest,
            answer=answer,
            challenge=challenge,
        )

        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                encounter = STATE_SERVICE.encounter_projection(progress)
                if metadata["revision"] != challenge.get("revision") or not isinstance(encounter, dict):
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Campaign changed; capture fresh boss context")
                if encounter.get("status") != "boss_available" or encounter.get("project_id") != challenge.get("project_id"):
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="The boss gate is no longer available")
                if requirement_id not in BOSS_REQUIREMENTS:
                    raise HTTPException(status_code=422, detail="Unsupported boss requirement")
                current_requirement = encounter.get("boss_current_requirement")
                current_requirement_id = current_requirement.get("id") if isinstance(current_requirement, dict) else None
                if current_requirement_id and requirement_id != current_requirement_id:
                    raise HTTPException(status_code=409, detail="Submit the current boss goal before a later goal")
                if isinstance(current_requirement, dict) and current_requirement.get("question_type") in BOSS_CHOICE_TYPES:
                    raise HTTPException(status_code=409, detail="This boss goal is answered by clicking an option in the sidebar")
                submission_id = f"boss-{secrets.token_hex(12)}"
                evidence_id = submission_id
                answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
                question_type = (
                    str(current_requirement.get("question_type") or "explanation")
                    if isinstance(current_requirement, dict)
                    else "explanation"
                )
                submissions[requirement_id] = {
                    "submission_id": submission_id,
                    "evidence_id": evidence_id,
                    "answer_digest": answer_digest,
                    "requirement_id": requirement_id,
                    "question_type": question_type,
                    "answer_source": payload.answer_source,
                    "source_path": payload.source_path.strip().replace("\\", "/") if payload.source_path else None,
                    "file_digest": payload.file_digest,
                }
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return {
        "ok": True,
        "submission": {
            "submission_id": submission_id,
            "nonce": nonce,
            "challenge_type": "boss",
            "revision": challenge["revision"],
            "project_id": challenge["project_id"],
            "boss_name": challenge.get("boss_name"),
            "requirement_id": requirement_id,
            "question_type": submissions[requirement_id]["question_type"],
            "evidence_id": evidence_id,
            "answer_digest": answer_digest,
            "answer_source": submissions[requirement_id].get("answer_source", "manual"),
            "source_path": submissions[requirement_id].get("source_path"),
            "file_digest": submissions[requirement_id].get("file_digest"),
            "expires_in": max(0, int(float(challenge["expires_at"]) - time.monotonic())),
        },
    }


def _clear_boss_if_ready() -> dict | None:
    """Clear the boss once every goal is verified in the saved state. Call
    with PROGRESS_LOCK held, right after recording a boss requirement."""

    progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
    encounter = STATE_SERVICE.encounter_projection(progress)
    if not isinstance(encounter, dict) or encounter.get("boss_phase") != "ready_to_clear":
        return None
    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    validation = project.get("boss_validation") if isinstance(project.get("boss_validation"), dict) else {}
    gauntlet = list(encounter.get("boss_requirements") or BOSS_REQUIREMENTS)
    evidence: dict[str, dict] = {}
    for entry in validation.get("history") or []:
        if isinstance(entry, dict) and entry.get("requirement_id") in gauntlet:
            evidence[entry["requirement_id"]] = entry
    fallback = next(iter(evidence.values()), {}).get("evidence_id") or f"boss-{secrets.token_hex(12)}"
    reason = "Boss requirements verified; " + "; ".join(
        str(evidence.get(requirement, {}).get("reason") or "validated") for requirement in gauntlet
    )
    return STATE_SERVICE.apply_internal(
        "record_boss_clear",
        {
            "evidence_id": evidence.get("required_behavior", {}).get("evidence_id") or fallback,
            "explanation_evidence_id": evidence.get("explanation", {}).get("evidence_id") or fallback,
            "interview_evidence_id": evidence.get("interview", {}).get("evidence_id") or fallback,
            "reason": reason[:MAX_REASON_LENGTH],
        },
    )


@app.post("/api/pyr/boss-verdict")
def apply_pyr_boss_verdict(payload: PyrBossVerdictRequest):
    """Record a validated boss requirement and clear the gate when complete."""

    nonce = payload.nonce.strip()
    requirement_id = payload.requirement_id
    global PYR_CONTEXT_CHALLENGE
    with PYR_CONTEXT_LOCK:
        client_id, challenge = _challenge_by_nonce(
            PYR_CONTEXT_CHALLENGES, nonce, legacy=PYR_CONTEXT_CHALLENGE
        )
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce or challenge.get("challenge_type") != "boss":
            raise HTTPException(status_code=409, detail="Boss verdict challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
            if client_id == "default":
                PYR_CONTEXT_CHALLENGE = None
            raise HTTPException(status_code=409, detail="Boss challenge expired; capture context again")
        submissions = challenge.get("boss_submissions")
        verified = challenge.get("boss_verified")
        pending = submissions.get(requirement_id) if isinstance(submissions, dict) else None
        if not isinstance(verified, dict) or not isinstance(pending, dict):
            raise HTTPException(status_code=409, detail="No pending submission exists for this boss requirement")
        if (
            pending.get("submission_id") != payload.submission_id
            or pending.get("answer_digest") != payload.answer_digest
            or pending.get("evidence_id") != payload.evidence_id
        ):
            raise HTTPException(status_code=409, detail="Boss verdict does not match the pending submission")

        if payload.verdict == "incorrect":
            del submissions[requirement_id]
            return {
                "ok": True,
                "verdict": "incorrect",
                "requirement_id": requirement_id,
                "complete": False,
                "retry_allowed": True,
                "reason": payload.reason,
            }

        verified[requirement_id] = {
            "evidence_id": pending["evidence_id"],
            "submission_id": pending["submission_id"],
            "reason": payload.reason,
        }
        del submissions[requirement_id]
        mutation = None
        requirement_mutation = None
        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                encounter = STATE_SERVICE.encounter_projection(progress)
                if metadata["revision"] != challenge.get("revision") or not isinstance(encounter, dict) or encounter.get("status") != "boss_available":
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Campaign changed; capture fresh boss context")
                requirement_mutation = STATE_SERVICE.apply_internal(
                    "record_boss_requirement",
                    {
                        "requirement_id": requirement_id,
                        "evidence_id": pending["evidence_id"],
                        "reason": payload.reason,
                    },
                )
                if requirement_mutation.get("changed"):
                    # Keep this bounded boss challenge usable for the next
                    # phase while binding it to the newly committed revision.
                    challenge["revision"] = requirement_mutation["revision"]
                mutation = _clear_boss_if_ready()
                if mutation is not None:
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

        response_mutation = mutation or requirement_mutation
        return {
            "ok": True,
            "verdict": "correct",
            "requirement_id": requirement_id,
            "complete": mutation is not None,
            "verified_requirements": sorted(verified),
            "mutation": mutation,
            "phase_mutation": requirement_mutation,
            "revision": response_mutation.get("revision") if response_mutation else challenge.get("revision"),
            "event": response_mutation.get("event") if response_mutation else None,
        }


@app.post("/api/pyr/verdict")
def apply_pyr_verdict(payload: PyrVerdictRequest):
    """Apply one challenged PYR Battle verdict through the state service.

    The challenge binds the verdict to the campaign revision and active mob
    that the context bridge returned. The caller can choose only correct or
    incorrect; Impact, rewards and counterattack damage remain canonical
    server/state-service values.
    """

    nonce = payload.nonce.strip()
    if len(nonce) < 16 or len(nonce) > 128 or any(ord(character) < 33 for character in nonce):
        raise HTTPException(status_code=422, detail="nonce must be a bounded challenge token")
    objective_id = payload.objective_id.strip() if payload.objective_id else None
    evidence_id = payload.evidence_id.strip()
    if payload.verdict == "correct" and not objective_id:
        raise HTTPException(status_code=422, detail="A correct verdict requires objective_id")
    if payload.verdict == "incorrect" and not objective_id:
        raise HTTPException(status_code=422, detail="An incorrect verdict requires objective_id")

    global PYR_CONTEXT_CHALLENGE
    with PYR_CONTEXT_LOCK:
        client_id, challenge = _challenge_by_nonce(
            PYR_CONTEXT_CHALLENGES, nonce, legacy=PYR_CONTEXT_CHALLENGE
        )
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce:
            raise HTTPException(status_code=409, detail="PYR verdict challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
            if client_id == "default":
                PYR_CONTEXT_CHALLENGE = None
            raise HTTPException(status_code=409, detail="PYR verdict challenge expired; capture context again")
        if client_id is not None:
            PYR_CONTEXT_CHALLENGES[client_id] = challenge
        if (
            challenge.get("submission_id") != payload.submission_id
            or challenge.get("answer_digest") != payload.answer_digest
            or challenge.get("objective_id") != objective_id
            or challenge.get("evidence_id") != evidence_id
        ):
            raise HTTPException(status_code=409, detail="Verdict does not match the pending Battle submission")

        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                encounter = STATE_SERVICE.encounter_projection(progress)
                if metadata["revision"] != challenge.get("revision"):
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Campaign changed; capture fresh PYR context")
                if (
                    not isinstance(encounter, dict)
                    or encounter.get("project_id") != challenge.get("project_id")
                    or encounter.get("mob_name") != challenge.get("mob_name")
                ):
                    _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
                    if client_id == "default":
                        PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Active encounter changed; capture fresh PYR context")
                available_ids = {
                    item.get("id")
                    for item in encounter.get("available_objectives", [])
                    if isinstance(item, dict) and item.get("id")
                }
                if objective_id not in available_ids:
                    raise HTTPException(status_code=422, detail="objective_id is not available for the active encounter")

                if payload.verdict == "correct":
                    action = "record_battle_objective"
                    state_payload = {
                        "objective_id": objective_id,
                        "evidence_id": evidence_id,
                        "reason": payload.reason,
                        "code_snippet": challenge.get("answer_snippet"),
                    }
                else:
                    action = "record_battle_miss"
                    try:
                        mob_index = max(0, int(encounter.get("mob_index", 0)))
                    except (TypeError, ValueError):
                        mob_index = 0
                    state_payload = {
                        "mob_index": mob_index,
                        "reason": payload.reason,
                        "encounter_id": f"{encounter['project_id']}-{mob_index}",
                        "objective_id": objective_id,
                        "evidence_id": evidence_id,
                    }
                mutation = STATE_SERVICE.apply_internal(action, state_payload)
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        _clear_challenge(PYR_CONTEXT_CHALLENGES, client_id)
        if client_id == "default":
            PYR_CONTEXT_CHALLENGE = None

    return {
        "ok": True,
        "verdict": payload.verdict,
        "mutation": mutation,
        "revision": mutation.get("revision"),
        "event": mutation.get("event"),
    }


@app.get("/api/tree")
def tree():
    return {"workspace": str(WORKSPACE), "items": build_tree()}


@app.get("/api/file")
def read_file(path: str):
    target = safe_path(path)
    reject_state_file_access(target)
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if target.stat().st_size > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="File is too large for the learning editor")
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="Only UTF-8 text files are supported") from exc
    return {"path": target.relative_to(WORKSPACE).as_posix(), "content": content}


@app.put("/api/file")
def write_file(payload: FileWrite):
    target = safe_path(payload.path)
    reject_state_file_access(target)
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="File is too large for the learning editor")
    target.parent.mkdir(parents=True, exist_ok=True)
    before = _read_text_or_empty(target)
    target.write_text(payload.content, encoding="utf-8")
    _record_code_lines(before, payload.content)
    return {"ok": True, "path": target.relative_to(WORKSPACE).as_posix(), "bytes": len(encoded)}


CODE_LINE_SUFFIXES = {".py", ".md", ".txt", ".json", ".toml", ".cfg", ".ini", ".html", ".css", ".js", ".sql"}


def _read_text_or_empty(target: Path) -> str:
    try:
        return target.read_text(encoding="utf-8") if target.is_file() else ""
    except (OSError, UnicodeDecodeError):
        return ""


def added_code_lines(before: str, after: str) -> int:
    """Non-blank lines a save adds or rewrites (moved or deleted lines don't count)."""

    old = [line.rstrip() for line in before.splitlines()]
    new = [line.rstrip() for line in after.splitlines()]
    matcher = difflib.SequenceMatcher(a=old, b=new, autojunk=False)
    return sum(
        sum(1 for line in new[b0:b1] if line.strip())
        for tag, _a0, _a1, b0, b1 in matcher.get_opcodes()
        if tag in {"insert", "replace"}
    )


def _record_code_lines(before: str, after: str) -> None:
    """Feed the Settings activity graph; a save never fails because of it."""

    lines = min(added_code_lines(before, after), 2_000)
    if lines <= 0:
        return
    try:
        with PROGRESS_LOCK:
            STATE_SERVICE.apply_internal("record_code_activity", {"lines": lines})
    except StateCommandError:
        pass


class WorkspaceEntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)
    type: Literal["file", "dir"]


@app.post("/api/workspace/new")
def create_workspace_entry(payload: WorkspaceEntryCreate):
    """Create an empty file or a folder from the Forge explorer. Never
    overwrites: an existing name is refused, so New File cannot wipe work."""

    parts = [part for part in payload.path.replace("\\", "/").split("/") if part]
    if not parts or any(part in {".", ".."} or part.startswith(".") or part in IGNORED_DIRS for part in parts):
        raise HTTPException(status_code=422, detail="Use plain names: no hidden (dot) or tool folders")
    target = safe_path("/".join(parts))
    reject_state_file_access(target)
    relative = target.relative_to(WORKSPACE).as_posix()
    if target.exists():
        raise HTTPException(status_code=409, detail=f"{relative} already exists")
    try:
        if payload.type == "dir":
            target.mkdir(parents=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.touch(exist_ok=False)
    except OSError as exc:  # a file where a folder should be, or a race
        raise HTTPException(status_code=409, detail=f"Could not create {relative}: a file is in the way") from exc
    return {"ok": True, "path": relative, "type": payload.type}


# Explorer deletes go here, never straight to oblivion: a learner can get a
# file back from <workspace>/.questlab-trash/<time>/.
TRASH_DIR_NAME = ".questlab-trash"
PLATFORM_ROOT_FILES = {"tutor.py", "dungeon.py"}


class WorkspaceEntryDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, max_length=240)


def _deletable_game_path(target: Path) -> bool:
    """Only game files can be deleted from the explorer: anything inside a
    campaign's project folder, or a root-level .py file that is not part of
    the platform. The workspace, tool folders and state stay untouchable."""

    relative = target.relative_to(WORKSPACE)
    parts = relative.parts
    if not parts or any(part.startswith(".") or part in IGNORED_DIRS for part in parts):
        return False
    folders = {
        project_dir_name(entry.get("project_dir"))
        for entry in load_campaign_bounties().values()
        if isinstance(entry, dict)
    } - {""}
    if parts[0] in folders:
        return len(parts) > 1
    return len(parts) == 1 and target.suffix == ".py" and parts[0] not in PLATFORM_ROOT_FILES


@app.post("/api/workspace/delete")
def delete_workspace_entry(payload: WorkspaceEntryDelete):
    """Move a game file or folder to the workspace trash (recoverable)."""

    target = safe_path(payload.path.replace("\\", "/"))
    reject_state_file_access(target)
    if not target.exists() or target.is_symlink():
        raise HTTPException(status_code=404, detail="Nothing to delete there")
    if not _deletable_game_path(target):
        raise HTTPException(status_code=403, detail="Only your project's own files can be deleted here")
    relative = target.relative_to(WORKSPACE)
    stamp = f"{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    destination = WORKSPACE / TRASH_DIR_NAME / stamp / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(target), str(destination))
    return {"ok": True, "path": relative.as_posix(), "trash": destination.relative_to(WORKSPACE).as_posix()}


def _apply_state_or_http(action: str, payload: dict, actor: str, *, internal: bool = False) -> dict:
    try:
        return STATE_SERVICE.apply(action, payload, actor, internal=internal)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _flatten_state_result(envelope: dict) -> dict:
    result = dict(envelope.get("result") or {})
    result.update(
        {
            "ok": envelope.get("ok", True),
            "action": envelope.get("action"),
            "changed": envelope.get("changed", False),
            "revision": envelope.get("revision"),
        }
    )
    if envelope.get("event") is not None:
        result["event"] = envelope["event"]
    return result


@app.post("/api/state/apply")
def apply_state_command(payload: StateApplyRequest):
    return _apply_state_or_http(payload.action, payload.payload, payload.actor)


@app.get("/api/tutor")
def read_tutor():
    target = ensure_tutor_file()
    content = target.read_text(encoding="utf-8")
    return {
        "path": "tutor.py",
        "content": content,
        "revision": tutor_revision(content),
        "practice_options": LocalStateService.practice_options(),
        "notes": {
            "directory": NOTES_DIR_NAME,
            "extension": ".md",
            "max_bytes": MAX_WORKSPACE_NOTE_BYTES,
        },
    }


@app.put("/api/tutor")
def write_tutor(payload: TutorWrite):
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="Tutor notebook is too large")
    target = ensure_tutor_file()
    before = _read_text_or_empty(target)
    target.write_text(payload.content, encoding="utf-8")
    _record_code_lines(before, payload.content)
    return {
        "ok": True,
        "path": "tutor.py",
        "bytes": len(encoded),
        "revision": tutor_revision(payload.content),
        "practice_options": LocalStateService.practice_options(),
        "notes": {
            "directory": NOTES_DIR_NAME,
            "extension": ".md",
            "max_bytes": MAX_WORKSPACE_NOTE_BYTES,
        },
    }


def _format_file(target: Path, content: str, *, allow_tutor: bool = False) -> dict:
    if allow_tutor:
        if target.resolve() != TUTOR_PATH.resolve():
            raise HTTPException(status_code=403, detail="Only the Campaign Tutor Notebook may use this endpoint")
    else:
        reject_state_file_access(target)
    encoded = content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="File is too large for the learning editor")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    suffix = target.suffix.lower()

    if suffix == ".py":
        command = [sys.executable, "-m", "ruff", "format", str(target)]
        formatter = "Ruff"
    elif suffix in {".js", ".jsx", ".ts", ".tsx", ".json", ".css", ".scss", ".html", ".md", ".yaml", ".yml"}:
        prettier = REPO_ROOT / "ide" / "frontend" / "node_modules" / ".bin" / "prettier"
        if not prettier.exists():
            raise HTTPException(status_code=503, detail="Prettier is not installed. Run npm install in ide/frontend.")
        command = [str(prettier), "--write", str(target)]
        formatter = "Prettier"
    else:
        raise HTTPException(status_code=415, detail=f"No formatter configured for {suffix or 'this file type'}")

    try:
        result = subprocess.run(
            command,
            cwd=str(WORKSPACE),
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(status_code=500, detail=f"Formatter failed to start: {exc}") from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "Formatter failed").strip()
        raise HTTPException(status_code=422, detail=detail[:4000])

    return {
        "ok": True,
        "path": target.relative_to(WORKSPACE).as_posix(),
        "content": target.read_text(encoding="utf-8"),
        "formatter": formatter,
    }


@app.post("/api/tutor/format")
def format_tutor(payload: TutorWrite):
    return _format_file(ensure_tutor_file(), payload.content, allow_tutor=True)


@app.post("/api/format")
def format_file(payload: FormatRequest):
    return _format_file(safe_path(payload.path), payload.content)


@app.get("/api/notes")
def list_workspace_notes():
    """List bounded per-concept Markdown artifacts without reading progress.

    Notes are intentionally not part of the generic file API. This endpoint
    exposes only flat ``notes/<concept_id>.md`` files so a malformed or
    legacy file cannot become a second state authority.
    """

    with WORKSPACE_NOTES_LOCK:
        root = workspace_notes_root()
        notes: list[dict[str, object]] = []
        if root.exists():
            try:
                children = sorted(root.iterdir(), key=lambda item: item.name.casefold())
            except OSError as exc:
                raise HTTPException(status_code=500, detail="Workspace notes could not be listed") from exc
            for child in children:
                if len(notes) >= MAX_WORKSPACE_NOTES:
                    break
                if child.suffix.casefold() != ".md" or child.is_symlink() or not child.is_file():
                    continue
                try:
                    identifier = workspace_note_identifier(child.stem)
                    relative, resolved = workspace_note_path(identifier)
                    if resolved != child.resolve():
                        continue
                    if child.stat().st_size > MAX_WORKSPACE_NOTE_BYTES:
                        notes.append(
                            {
                                "concept_id": identifier,
                                "path": relative,
                                "bytes": child.stat().st_size,
                                "revision": None,
                                "exists": True,
                                "too_large": True,
                            }
                        )
                        continue
                    content = child.read_text(encoding="utf-8")
                    content = normalize_workspace_note(content)
                except (HTTPException, UnicodeDecodeError, OSError):
                    # Invalid legacy notes are not promoted into the active
                    # note catalogue. The dedicated GET gives a precise error
                    # once a user explicitly selects a valid identifier.
                    continue
                notes.append(
                    {
                        "concept_id": identifier,
                        "path": relative,
                        "bytes": len(content.encode("utf-8")),
                        "revision": workspace_note_revision(content),
                        "exists": True,
                        "too_large": False,
                    }
                )
        return {
            "ok": True,
            "directory": NOTES_DIR_NAME,
            "extension": ".md",
            "max_bytes": MAX_WORKSPACE_NOTE_BYTES,
            "notes": notes,
        }


@app.get("/api/notes/{concept_id}")
def get_workspace_note(concept_id: str):
    """Read one concept note; an absent note is an empty editable document."""

    with WORKSPACE_NOTES_LOCK:
        return {
            "ok": True,
            "directory": NOTES_DIR_NAME,
            "max_bytes": MAX_WORKSPACE_NOTE_BYTES,
            "note": read_workspace_note(concept_id),
        }


@app.put("/api/notes/{concept_id}")
def put_workspace_note(concept_id: str, payload: WorkspaceNoteWrite):
    """Atomically save one concept note without mutating canonical state."""

    with WORKSPACE_NOTES_LOCK:
        note = write_workspace_note(concept_id, payload.content)
    return {
        "ok": True,
        "directory": NOTES_DIR_NAME,
        "max_bytes": MAX_WORKSPACE_NOTE_BYTES,
        "note": note,
    }


@app.post("/api/homestead/purchase")
def purchase_homestead_item(payload: HomesteadPurchase):
    envelope = _apply_state_or_http("homestead_purchase", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


@app.post("/api/campaign/market/purchase")
def purchase_campaign_market_item(payload: CampaignMarketPurchase):
    envelope = _apply_state_or_http("campaign_market_purchase", payload.model_dump(), "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({
        "equipment_projection": STATE_SERVICE.equipment_projection(progress),
        "revision": metadata["revision"],
        "coins": progress.get("player", {}).get("coins", 0),
        "supplies": progress.get("supplies", {}),
        "market_purchases": progress.get("homestead", {}).get("market_purchases", []),
    })
    return result


@app.post("/api/homestead/equip")
def equip_homestead_item(payload: HomesteadEquip):
    envelope = _apply_state_or_http("homestead_equip", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


@app.post("/api/home/rooms/purchase")
def purchase_home_room(payload: HomeRoomPurchase):
    envelope = _apply_state_or_http("home_room_purchase", payload.model_dump(), "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        home_rooms = STATE_SERVICE.home_room_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"progress": _without_identify_answer(progress), "home_rooms": home_rooms, "revision": metadata["revision"]})
    return result


@app.post("/api/homestead/room-upgrade")
def build_homestead_room_upgrade(payload: HomesteadRoomUpgrade):
    envelope = _apply_state_or_http("homestead_room_upgrade", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


@app.post("/api/homestead/action")
def perform_homestead_action(payload: HomesteadAction):
    envelope = _apply_state_or_http("homestead_action", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


class AvatarUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skin: str | None = Field(default=None, max_length=40)
    hair_style: str | None = Field(default=None, max_length=40)
    hair_color: str | None = Field(default=None, max_length=40)
    facial_hair: str | None = Field(default=None, max_length=40)
    beard_color: str | None = Field(default=None, max_length=40)
    eyes: str | None = Field(default=None, max_length=40)
    outfit: str | None = Field(default=None, max_length=40)
    accent: str | None = Field(default=None, max_length=40)


class CampaignSelect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    branch: str = Field(min_length=1, max_length=120)


class HunterStatPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stat: str = Field(min_length=1, max_length=20)


class HunterCraftOil(BaseModel):
    model_config = ConfigDict(extra="forbid")

    oil_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


@app.post("/api/hunter/craft")
def craft_hunter_oil(payload: HunterCraftOil):
    """Craft a beast oil from banked materials (validated by the state service)."""

    envelope = _apply_state_or_http("hunter_craft_oil", {"oil_id": payload.oil_id}, "player")
    try:
        _progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result["revision"] = metadata["revision"]
    return result


class HunterKitUpgrade(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track: str = Field(min_length=1, max_length=20)


class HunterIdentifyAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    puzzle_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    choice: int = Field(ge=0, le=3)


def _hunter_action(action: str, payload: dict) -> dict:
    envelope = _apply_state_or_http(action, payload, "player")
    try:
        _progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result["revision"] = metadata["revision"]
    return result


class ArmoryItemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class ArmorySlotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slot: str = Field(min_length=1, max_length=20)


@app.post("/api/armory/equip")
def equip_armory_item(payload: ArmoryItemRequest):
    return _hunter_action("armory_equip", payload.model_dump())


@app.post("/api/armory/unequip")
def unequip_armory_slot(payload: ArmorySlotRequest):
    return _hunter_action("armory_unequip", payload.model_dump())


@app.post("/api/armory/use")
def use_armory_item(payload: ArmoryItemRequest):
    return _hunter_action("armory_use", payload.model_dump())


@app.post("/api/armory/buy")
def buy_armory_item(payload: ArmoryItemRequest):
    return _hunter_action("armory_buy", payload.model_dump())


@app.post("/api/hunter/kit")
def upgrade_hunter_kit(payload: HunterKitUpgrade):
    return _hunter_action("hunter_upgrade_kit", {"track": payload.track})


@app.post("/api/hunter/identify/start")
def start_hunter_identify():
    return _hunter_action("hunter_identify_start", {})


@app.post("/api/hunter/identify/answer")
def answer_hunter_identify(payload: HunterIdentifyAnswer):
    return _hunter_action("hunter_identify_answer", payload.model_dump())


@app.post("/api/hunter/stat")
def spend_hunter_point(payload: HunterStatPoint):
    """Spend one free stat point (validated by the state service)."""

    envelope = _apply_state_or_http("hunter_spend_point", {"stat": payload.stat}, "player")
    try:
        _progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result["revision"] = metadata["revision"]
    return result


@app.post("/api/campaign/select")
def select_campaign(payload: CampaignSelect):
    """Switch the active campaign project (validated by the state service)."""

    envelope = _apply_state_or_http("select_campaign", {"branch": payload.branch}, "player")
    try:
        _progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result["revision"] = metadata["revision"]
    return result


@app.post("/api/avatar")
def set_avatar(payload: AvatarUpdate):
    """Update the player's paper-doll appearance (validated by the state service)."""

    envelope = _apply_state_or_http("set_avatar", payload.model_dump(exclude_none=True), "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"equipment_projection": STATE_SERVICE.equipment_projection(progress), "revision": metadata["revision"]})
    return result


@app.post("/api/equipment/equip")
def equip_campaign_equipment(payload: EquipmentEquip):
    envelope = _apply_state_or_http("equip_equipment", payload.model_dump(), "player")
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"equipment_projection": STATE_SERVICE.equipment_projection(progress), "revision": metadata["revision"]})
    return result


@app.post("/api/codex/note")
def save_codex_note(payload: CodexNoteRequest):
    """Store a player-authored note through the canonical state gateway."""

    try:
        note = payload.note.replace("\r\n", "\n").replace("\r", "\n")
        if len(note.encode("utf-8")) > MAX_CODEX_NOTE_BYTES:
            raise HTTPException(status_code=413, detail="Codex note is too large")
    except UnicodeEncodeError as exc:
        raise HTTPException(status_code=422, detail="Codex note is not valid UTF-8") from exc
    envelope = _apply_state_or_http(
        "record_codex_note",
        {"entry_id": payload.entry_id, "note": note},
        "player",
    )
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = STATE_SERVICE.codex_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    result = _flatten_state_result(envelope)
    result.update({"revision": metadata["revision"], "codex": projection})
    return result


@app.websocket("/ws/terminal/{role}")
async def terminal(websocket: WebSocket, role: str):
    if role not in {"shell", "ai"}:
        await websocket.close(code=1008)
        return
    if not is_allowed_origin(websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="Origin not allowed")
        return

    await websocket.accept()
    shell = resolve_shell()
    env = terminal_environment(role)

    try:
        pid, master_fd = pty.fork()
    except OSError as exc:
        await websocket.send_text(f"\r\n[Quest Lab] Failed to create PTY: {exc}\r\n")
        await websocket.close(code=1011)
        return

    if pid == 0:
        try:
            os.chdir(WORKSPACE)
            os.execvpe(shell, shell_argv(shell), env)
        except BaseException as exc:
            message = f"Quest Lab could not start shell {shell}: {exc}\n"
            os.write(2, message.encode("utf-8", errors="replace"))
            os._exit(127)

    try:
        set_pty_size(master_fd, 120, 30)
    except OSError:
        pass

    async def pump_output():
        while True:
            try:
                data = await asyncio.to_thread(os.read, master_fd, 4096)
            except OSError:
                break
            if not data:
                break
            try:
                await websocket.send_text(data.decode("utf-8", errors="replace"))
            except (WebSocketDisconnect, RuntimeError):
                break

    async def pump_input():
        while True:
            try:
                text = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            try:
                message = json.loads(text) if text.startswith("{") else None
            except json.JSONDecodeError:
                message = None

            if isinstance(message, dict) and message.get("type") == "resize":
                try:
                    set_pty_size(master_fd, message.get("cols", 120), message.get("rows", 30))
                except (OSError, TypeError, ValueError):
                    pass
                continue

            if isinstance(message, dict) and message.get("type") == "ping":
                continue

            if isinstance(message, dict):
                if message.get("type") != "input":
                    continue
                payload = message.get("data", "")
            else:
                payload = text
            if payload:
                try:
                    await asyncio.to_thread(os.write, master_fd, payload.encode("utf-8"))
                except OSError:
                    break

    output_task = asyncio.create_task(pump_output())
    input_task = asyncio.create_task(pump_input())

    try:
        done, pending = await asyncio.wait(
            {output_task, input_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        await asyncio.gather(*pending, return_exceptions=True)
        for task in done:
            try:
                await task
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
    finally:
        for task in (output_task, input_task):
            if not task.done():
                task.cancel()
        # Closing the master before waiting on the child unblocks any
        # ``os.read`` already running in the output worker. This matters for
        # browser/test clients that close immediately after the websocket
        # handshake and prevents the PTY route from hanging its shutdown.
        try:
            os.close(master_fd)
        except OSError:
            pass
        if not child_exited(pid):
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            try:
                await asyncio.wait_for(asyncio.to_thread(os.waitpid, pid, 0), timeout=1.5)
            except (asyncio.TimeoutError, ChildProcessError):
                try:
                    os.kill(pid, signal.SIGKILL)
                except OSError:
                    pass
                try:
                    await asyncio.wait_for(asyncio.to_thread(os.waitpid, pid, 0), timeout=1.5)
                except (asyncio.TimeoutError, ChildProcessError):
                    pass


# ── OpenCode-backed PYR (ide/server/ai_tutor.py) ─────────────────────────
# These routes call the player's OpenCode install. They never hold the state
# or context locks while a model is thinking; a grade is applied afterwards
# through the same verdict functions an external provider would call, so the
# state service still owns rewards, damage, HP and replay protection.


class AiSettingsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, max_length=200)
    mode: Literal["opencode", "classic"] | None = None
    auto_grade: bool | None = None
    generate_dungeon_questions: bool | None = None
    choose_practice_lens: bool | None = None


class AiTestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str | None = Field(default=None, max_length=200)


class AiJudgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["battle", "boss", "dungeon", "practice"]
    submission: dict
    answer: str = Field(min_length=1, max_length=MAX_DUNGEON_EDITOR_BYTES)
    question: str = Field(default="", max_length=8_000)
    client_id: str = Field(default="default", min_length=1, max_length=128, pattern=r"^[A-Za-z0-9._:-]+$")


class AiDungeonQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class AiPracticeLensRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept: str = Field(min_length=1, max_length=200)
    lenses: list[dict[str, str]] = Field(min_length=1, max_length=12)


class AiAskRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2_000)
    concept: str = Field(default="", max_length=200)
    code: str = Field(default="", max_length=20_000)
    # Asked from the Forge during a campaign fight: the fight pays less.
    battle: bool = False


def _ai_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except ai_tutor.AiTutorError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"message": str(exc), "kind": exc.kind}) from exc


GRADING_FILE_CHARS = 2_500
GRADING_FILES_TOTAL = 9_000


def _grading_files(kind: str, submission: dict) -> dict | None:
    """For a multi-file campaign, the project's files (which exist, and their
    size) and the bounded contents of the files this goal names, so a goal
    like "split the reels into reels.py" is graded on the real project."""

    if kind not in {"battle", "boss"}:
        return None
    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
        encounter = STATE_SERVICE.encounter_projection(progress) or {}
    except StateCommandError:
        return None
    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    entry = load_campaign_bounties().get(str(project.get("branch") or ""))
    if not isinstance(entry, dict) or entry.get("multi_file") is not True:
        return None
    names = [name for name in entry.get("project_files", []) if project_file_name(name)][:20]
    folder = WORKSPACE / project_dir_name(entry.get("project_dir"))
    listing = []
    for name in names:
        path = folder / name
        listing.append({"file": name, "exists": path.is_file(), "bytes": path.stat().st_size if path.is_file() else 0})
    if kind == "battle":
        objective = next((item for item in encounter.get("available_objectives") or [] if item.get("id") == submission.get("objective_id")), {})
        wanted = [*(objective.get("see") or []), *([objective["file"]] if objective.get("file") else [])]
    else:
        wanted = names
    related, budget = {}, GRADING_FILES_TOTAL
    submitted = str(submission.get("source_path") or "").replace("\\", "/")
    for name in dict.fromkeys(wanted):
        path = folder / name
        if budget <= 0 or not project_file_name(name) or not path.is_file() or path.resolve() == (WORKSPACE / submitted).resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")[: min(GRADING_FILE_CHARS, budget)]
        related[name] = text
        budget -= len(text)
    return {"project_files": listing, "related_files": related}


def _grading_context(kind: str, context: dict) -> dict:
    """Keep only what a grader needs. The full bounded context runs to ~20k
    characters, which made real grades take minutes; the submitted answer
    already carries the active file for battle and boss grades."""

    if kind == "dungeon":
        dungeon = context.get("dungeon") if isinstance(context.get("dungeon"), dict) else {}
        return {"dungeon": {key: dungeon[key] for key in ("room_type", "floor", "room", "question", "mob") if key in dungeon}}
    encounter = context.get("encounter") if isinstance(context.get("encounter"), dict) else {}
    encounter_keys = ("mob_name", "mob", "boss", "status", "concept", "current_quest", "boss_current_requirement", "available_objectives")
    terminal = context.get("terminal") if isinstance(context.get("terminal"), dict) else {}
    active = context.get("active_file") if isinstance(context.get("active_file"), dict) else {}
    return {
        "quest": context.get("quest"),
        "encounter": {key: encounter[key] for key in encounter_keys if key in encounter},
        "submitted_file": active.get("path"),
        "recent_terminal_output": str(terminal.get("tail") or "")[-2_000:],
    }


# Question ids PYR has already rewritten this session, so a re-render or a
# second tab cannot rotate the same room's question (and wipe the editor) twice.
AI_ISSUED_DUNGEON_QUESTIONS: set[str] = set()
# Hidden answer keys for clickable questions, by '<mode>:<question id>'; server memory only.
CHOICE_ANSWER_KEYS: dict[str, dict[str, object]] = {}


@app.get("/api/ai/status")
def ai_status():
    return {"ok": True, "settings": ai_tutor.load_settings(), "opencode": ai_tutor.status()}


@app.get("/api/ai/models")
def ai_models():
    return {"ok": True, "models": ai_tutor.list_models()}


@app.post("/api/ai/settings")
def ai_save_settings(payload: AiSettingsRequest):
    return {"ok": True, "settings": _ai_call(ai_tutor.save_settings, payload.model_dump(exclude_none=True))}


@app.post("/api/ai/test")
def ai_test(payload: AiTestRequest):
    return _ai_call(ai_tutor.test_connection, payload.model)


@app.post("/api/ai/judge")
def ai_judge(payload: AiJudgeRequest):
    """Grade a submission that was already bound by a PYR submission endpoint,
    then apply the verdict through the matching verdict gateway."""

    submission = payload.submission
    if hashlib.sha256(payload.answer.encode("utf-8")).hexdigest() != submission.get("answer_digest"):
        raise HTTPException(status_code=409, detail="The answer does not match the bound submission")
    context = None if payload.kind == "practice" else _grading_context(payload.kind, read_pyr_context(payload.client_id)["context"])
    files = _grading_files(payload.kind, submission)
    if context is not None and files:
        context.update(files)
    graded = _ai_call(ai_tutor.judge, payload.kind, context=context, answer=payload.answer, question=payload.question)
    common = {
        "nonce": submission.get("nonce"),
        "submission_id": submission.get("submission_id"),
        "answer_digest": submission.get("answer_digest"),
        "evidence_id": submission.get("evidence_id"),
        "verdict": graded["verdict"],
        "reason": graded["reason"],
    }
    try:
        if payload.kind == "battle":
            applied = apply_pyr_verdict(PyrVerdictRequest(**common, objective_id=submission.get("objective_id")))
        elif payload.kind == "boss":
            applied = apply_pyr_boss_verdict(PyrBossVerdictRequest(**common, requirement_id=submission.get("requirement_id")))
        elif payload.kind == "dungeon":
            applied = apply_pyr_dungeon_verdict(
                PyrDungeonVerdictRequest(**common, run_id=submission.get("run_id"), question_id=submission.get("question_id"))
            )
        else:
            applied = apply_pyr_practice_verdict(PyrPracticeVerdictRequest(**common, session_id=submission.get("session_id")))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail="The bound submission is missing fields for this verdict") from exc
    return {"ok": True, "verdict": graded["verdict"], "reason": graded["reason"], "applied": applied}


@app.post("/api/ai/dungeon-question")
def ai_dungeon_question(payload: AiDungeonQuestionRequest):
    """Have PYR write the current room's question (same id, type and concept)."""

    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
        projection = STATE_SERVICE.dungeon_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    question = projection.get("question") if isinstance(projection.get("question"), dict) else None
    if not projection.get("active") or projection.get("run_id") != payload.run_id or not question:
        raise HTTPException(status_code=409, detail="No current Dungeon question for this run")
    if projection.get("room_type") not in DUNGEON_COMBAT_ROOM_TYPES:
        raise HTTPException(status_code=409, detail="This room has no question")
    run_state = progress.get("dungeon_run") if isinstance(progress.get("dungeon_run"), dict) else {}
    # Issuing a question resets dungeon.py, so never rewrite a room the player
    # has already started answering (e.g. after an app restart).
    if (
        question["id"] in AI_ISSUED_DUNGEON_QUESTIONS
        or run_state.get("pyr_question_id") == question["id"]
        or str(run_state.get("editor_content") or "").strip()
    ):
        return {"ok": True, "changed": False, "dungeon": projection}
    fight = run_state.get("fight") if isinstance(run_state.get("fight"), dict) else {}
    written = _ai_call(
        ai_tutor.write_dungeon_question,
        concept=str(question.get("concept_id") or "python-basics"),
        question_type=str(question.get("question_type") or "short_explanation"),
        difficulty=int(question.get("difficulty") or 1),
        room_type=str(projection.get("room_type")),
        floor=int(projection.get("floor") or 1),
        fight_step=int(fight.get("questions_cleared", 0) or 0) + 1,
        fight_total=int(fight.get("questions_total", 1) or 1),
    )
    # The answer key stays in server memory: never in the save or the browser.
    key = {"answer": written.pop("answer"), "why": written.pop("why", "")} if "answer" in written else None
    written.pop("why", None)
    replacement = {key_name: question[key_name] for key_name in ("id", "question_type", "concept_id", "difficulty")}
    replacement.update(written)
    with PROGRESS_LOCK:
        try:
            mutation = STATE_SERVICE.apply_internal("dungeon_issue_question", {"run_id": payload.run_id, "question": replacement})
            progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
            projection = STATE_SERVICE.dungeon_projection(progress)
        except StateCommandError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    AI_ISSUED_DUNGEON_QUESTIONS.add(question["id"])
    if key is not None:
        CHOICE_ANSWER_KEYS[f"dungeon:{question['id']}"] = {**key, "options": list(written.get("options") or [])}
    return {"ok": True, "changed": True, "revision": mutation.get("revision"), "dungeon": projection}


# Clickable boss goals PYR wrote, by 'boss:<project>:<requirement>'.
BOSS_QUESTIONS: dict[str, dict[str, object]] = {}
BOSS_QUESTION_STYLES = {
    "snippet_check": (
        "Read your code",
        "Quote a short snippet (3-8 lines) from the learner's own file and ask what it does or what it prints for a given input.",
    ),
    "code_interview": (
        "Code interview",
        "Pick a function or block the learner wrote in this file. Quote it, then ask why it is written that way or what changes if an input or line changes. Harder than a plain read.",
    ),
}


class BossOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_id: Literal["required_behavior", "explanation", "edge_cases", "twist_2", "twist_3", "twist_4", "read_2", "interview"]
    option_index: int = Field(ge=0, le=7)


def _boss_choice_goal() -> tuple[dict, dict, dict, str]:
    """The active project, boss encounter, its current click goal and cache key."""

    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
        encounter = STATE_SERVICE.encounter_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not isinstance(encounter, dict) or encounter.get("status") != "boss_available":
        raise HTTPException(status_code=409, detail="There is no boss fight right now")
    goal = encounter.get("boss_current_requirement")
    if not isinstance(goal, dict) or goal.get("question_type") not in BOSS_CHOICE_TYPES:
        raise HTTPException(status_code=409, detail="The current boss goal is not a clickable question")
    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    return project, encounter, goal, f"boss:{encounter.get('project_id')}:{goal['id']}"


@app.post("/api/ai/boss-question")
def ai_boss_question():
    """PYR writes the clickable question for the current boss goal, about the
    player's own project file. Cached until answered."""

    project, encounter, goal, key = _boss_choice_goal()
    cached = BOSS_QUESTIONS.get(key)
    if cached:
        return {"ok": True, "question": {"requirement_id": goal["id"], **cached}}
    code = ""
    entry = project.get("entry_file")
    if isinstance(entry, str) and entry.endswith(".py"):
        path = (WORKSPACE / entry).resolve()
        if path.is_file() and WORKSPACE.resolve() in path.parents:
            code = path.read_text(encoding="utf-8", errors="replace")[:6000]
    label, style = BOSS_QUESTION_STYLES[goal["question_type"]]
    written = _ai_call(
        ai_tutor.write_battle_question,
        concept=str(project.get("name") or ""),
        project=str(encounter.get("project_name") or ""),
        contract=f"Boss fight: {encounter.get('boss') or 'the boss'}",
        objective=label,
        brief=style,
        code=code,
        studied=_studied_ideas(f"{project.get('name') or ''} {encounter.get('boss') or ''} {goal.get('label') or ''}"),
    )
    BOSS_QUESTIONS[key] = {"prompt": written["prompt"], "options": written["options"]}
    CHOICE_ANSWER_KEYS[key] = {"answer": written["answer"], "why": written.get("why", ""), "options": written["options"]}
    return {"ok": True, "question": {"requirement_id": goal["id"], **BOSS_QUESTIONS[key]}}


@app.post("/api/boss/answer-option")
def answer_boss_option(payload: BossOptionRequest):
    """Grade a clicked boss answer. Right verifies the goal (and clears the
    boss when it was the last one); wrong costs nothing, exactly like a wrong
    code submission, and the next question for the goal is a fresh one."""

    with PROGRESS_LOCK:
        _project, _encounter, goal, key = _boss_choice_goal()
        if payload.requirement_id != goal["id"]:
            raise HTTPException(status_code=409, detail="Answer the current boss goal")
        question = BOSS_QUESTIONS.get(key)
        answer = CHOICE_ANSWER_KEYS.get(key)
        if not question or not answer:
            raise HTTPException(status_code=409, detail="That question is no longer open; ask PYR for it again")
        options = list(question.get("options") or [])
        if payload.option_index >= len(options):
            raise HTTPException(status_code=422, detail="That question has no such option")
        BOSS_QUESTIONS.pop(key, None)
        CHOICE_ANSWER_KEYS.pop(key, None)
        correct_text = options[int(answer["answer"])]
        verdict = "correct" if payload.option_index == int(answer["answer"]) else "incorrect"
        why = str(answer.get("why") or "")
        reason = ((why or f"Right: {correct_text}.") if verdict == "correct" else f"The answer was {correct_text}. {why}".strip())[:400]
        cleared = None
        if verdict == "correct":
            try:
                STATE_SERVICE.apply_internal(
                    "record_boss_requirement",
                    {"requirement_id": goal["id"], "evidence_id": f"bs-click-{uuid.uuid4().hex[:16]}", "reason": reason[:MAX_REASON_LENGTH]},
                )
                cleared = _clear_boss_if_ready()
            except StateCommandError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"ok": True, "verdict": verdict, "reason": reason, "correct_index": int(answer["answer"]), "complete": cleared is not None}


def _studied_ideas(text: str, limit: int = 5) -> list[str]:
    """Statements from the learner's LearnHarness graph related to ``text``."""

    return [f"{node['name']}: {node['statement']}" for node in learnharness.related(learnharness.read_propositions(), text, limit)]


class LearnHarnessStudyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1, max_length=200)
    context: str = Field(default="", max_length=300)


@app.get("/api/learnharness/status")
def learnharness_status():
    """Is LearnHarness here, open, and how much has been studied at home."""

    url = learnharness.api_url()
    return {
        "ok": True,
        "installed": learnharness.installed(),
        "running": learnharness.is_running(),
        "mode": "direct" if url else "handoff",
        "ideas": len(learnharness.read_propositions()),
        "notes_dir": str(learnharness.notes_dir()),
    }


@app.get("/api/learnharness/lore")
def learnharness_lore(concept: str = ""):
    """Ideas studied at home that relate to a concept (read-only)."""

    if len(concept) > 300:
        raise HTTPException(status_code=422, detail="concept is too long")
    ideas = learnharness.related(learnharness.read_propositions(), concept, 8)
    return {"ok": True, "ideas": [{"name": node["name"], "statement": node["statement"]} for node in ideas]}


@app.post("/api/learnharness/study")
def learnharness_study(payload: LearnHarnessStudyRequest):
    """Send a concept home to study: a new LearnHarness session when its API
    is open to the game, otherwise open LearnHarness with a study brief."""

    ideas = learnharness.related(learnharness.read_propositions(), f"{payload.topic} {payload.context}", 6)
    context = payload.context.strip() or "working on my current campaign"
    url = learnharness.api_url()
    if url:
        title = f"{payload.topic} — {context}"[:120]
        try:
            created = learnharness.create_session(url, title, ideas)
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"LearnHarness did not create the session: {exc}") from exc
        return {"ok": True, "mode": "direct", "title": created.get("title") or title}
    if not learnharness.installed():
        raise HTTPException(status_code=404, detail="LearnHarness is not installed on this machine")
    return {"ok": True, "mode": "handoff", "launched": learnharness.launch(), "brief": learnharness.study_brief(payload.topic, context, ideas)}


@app.post("/api/learnharness/notes")
def learnharness_notes():
    """Hand the learner's campaign notes to LearnHarness: imported directly
    when its API is open to the game, else written as a Markdown file to import."""

    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    story = load_campaign_bounties().get(str(project.get("branch") or ""))
    contracts = {item["name"]: item for item in (story or {}).get("mobs", []) if isinstance(item, dict) and isinstance(item.get("name"), str)}
    filename, text = learnharness.notes_markdown(progress, contracts)
    url = learnharness.api_url()
    if url:
        try:
            result = learnharness.import_notes(url, filename, text)
        except (OSError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=f"LearnHarness did not import the notes: {exc}") from exc
        return {"ok": True, "mode": "direct", "result": result}
    folder = learnharness.notes_dir()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    target.write_text(text, encoding="utf-8")
    return {"ok": True, "mode": "handoff", "path": str(target), "launched": learnharness.launch()}


# Campaign choice questions PYR wrote, by 'battle:<project>:<mob>:<objective>'.
BATTLE_QUESTIONS: dict[str, dict[str, object]] = {}
BATTLE_CHOICE_TYPES = frozenset({"prediction", "explanation"})


class BattleQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    objective_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class BattleOptionRequest(BattleQuestionRequest):
    option_index: int = Field(ge=0, le=7)


def _battle_choice_objective(objective_id: str) -> tuple[dict, dict, dict, str]:
    """The live encounter, its open choice objective and the cache key."""

    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
        encounter = STATE_SERVICE.encounter_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not isinstance(encounter, dict) or not encounter.get("mob_name"):
        raise HTTPException(status_code=409, detail="There is no campaign battle right now")
    objective = next((item for item in encounter.get("available_objectives") or [] if item.get("id") == objective_id), None)
    if objective is None or objective.get("question_type") not in BATTLE_CHOICE_TYPES:
        raise HTTPException(status_code=409, detail="That objective is not an open question")
    key = f"battle:{encounter.get('project_id')}:{encounter.get('mob_name')}:{objective_id}"
    return progress, encounter, objective, key


@app.post("/api/ai/battle-question")
def ai_battle_question(payload: BattleQuestionRequest):
    """PYR writes the clickable question for a campaign PREDICT/EXPLAIN
    objective, about the learner's own project file. Cached until answered."""

    progress, encounter, objective, key = _battle_choice_objective(payload.objective_id)
    cached = BATTLE_QUESTIONS.get(key)
    if cached:
        return {"ok": True, "question": {"objective_id": payload.objective_id, **cached}}
    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    code = ""
    entry = project.get("entry_file")
    story = load_campaign_bounties().get(str(project.get("branch") or ""))
    folder = project_dir_name(story.get("project_dir")) if isinstance(story, dict) else ""
    target = project_file_name(objective.get("file"))
    if folder and target:
        entry = f"{folder}/{target}"
    if isinstance(entry, str) and entry.endswith(".py"):
        path = (WORKSPACE / entry).resolve()
        if path.is_file() and WORKSPACE.resolve() in path.parents:
            code = path.read_text(encoding="utf-8", errors="replace")[:6000]
    mob = encounter.get("mob") or {}
    written = _ai_call(
        ai_tutor.write_battle_question,
        concept=str(mob.get("concept") or ""),
        project=str(encounter.get("project_name") or ""),
        contract=str(mob.get("contract") or mob.get("brief") or ""),
        objective=str(objective.get("label") or payload.objective_id),
        brief=str(objective.get("brief") or ""),
        code=code,
        studied=_studied_ideas(f"{mob.get('concept') or ''} {objective.get('label') or ''} {objective.get('brief') or ''}"),
    )
    BATTLE_QUESTIONS[key] = {"prompt": written["prompt"], "options": written["options"]}
    CHOICE_ANSWER_KEYS[key] = {"answer": written["answer"], "why": written.get("why", ""), "options": written["options"]}
    return {"ok": True, "question": {"objective_id": payload.objective_id, **BATTLE_QUESTIONS[key]}}


@app.post("/api/battle/answer-option")
def answer_battle_option(payload: BattleOptionRequest):
    """Grade a clicked campaign answer. Right verifies the objective; wrong is
    a normal miss, and the next question for it is a fresh one."""

    with PROGRESS_LOCK:
        _progress, encounter, _objective, key = _battle_choice_objective(payload.objective_id)
        question = BATTLE_QUESTIONS.get(key)
        answer = CHOICE_ANSWER_KEYS.get(key)
        if not question or not answer:
            raise HTTPException(status_code=409, detail="That question is no longer open; ask PYR for it again")
        options = list(question.get("options") or [])
        if payload.option_index >= len(options):
            raise HTTPException(status_code=422, detail="That question has no such option")
        BATTLE_QUESTIONS.pop(key, None)
        CHOICE_ANSWER_KEYS.pop(key, None)
        correct_text = options[int(answer["answer"])]
        verdict = "correct" if payload.option_index == int(answer["answer"]) else "incorrect"
        why = str(answer.get("why") or "")
        reason = ((why or f"Right: {correct_text}.") if verdict == "correct" else f"The answer was {correct_text}. {why}".strip())[:400]
        evidence_id = f"bt-click-{uuid.uuid4().hex[:16]}"
        try:
            if verdict == "correct":
                applied = STATE_SERVICE.apply_internal("record_battle_objective", {"objective_id": payload.objective_id, "evidence_id": evidence_id, "reason": reason})
            else:
                applied = STATE_SERVICE.apply_internal(
                    "record_battle_miss",
                    {"objective_id": payload.objective_id, "encounter_id": f"battle-{uuid.uuid4().hex[:12]}", "evidence_id": evidence_id, "reason": reason},
                )
        except StateCommandError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"ok": True, "verdict": verdict, "reason": reason, "correct_index": int(answer["answer"]), "result": applied.get("result")}


SETUP_RUN_TIMEOUT_SECONDS = 10
SETUP_RUN_OUTPUT_CHARS = 1200


def _setup_check(project_dir: Path, check: dict) -> tuple[bool, str, str]:
    """Look at the learner's own folder for one setup step: (passed, reason, output)."""

    if "dir" in check:
        folder = project_dir if check["dir"] == "." else project_dir / check["dir"]
        shown = folder.relative_to(WORKSPACE).as_posix()
        if folder.is_dir():
            return True, f"{shown}/ is there.", ""
        return False, f"There is no {shown}/ folder yet. Make it in the terminal, then check again.", ""
    if "file" in check:
        target = project_dir / check["file"]
        shown = target.relative_to(WORKSPACE).as_posix()
        if target.is_file():
            return True, f"{shown} exists.", ""
        return False, f"There is no {shown} yet. Create it, then check again.", ""
    target = project_dir / check["run"]
    shown = target.relative_to(WORKSPACE).as_posix()
    if not target.is_file():
        return False, f"There is no {shown} to run yet.", ""
    try:
        # Run it the way the brief says: from inside the project folder.
        done = subprocess.run(
            [sys.executable, check["run"]], cwd=project_dir, stdin=subprocess.DEVNULL, capture_output=True,
            text=True, timeout=SETUP_RUN_TIMEOUT_SECONDS, env=terminal_environment("shell"),
        )
    except subprocess.TimeoutExpired:
        return False, f"{check['run']} was still running after {SETUP_RUN_TIMEOUT_SECONDS} seconds. Does it wait for input or loop forever?", ""
    output = (done.stdout + done.stderr)[-SETUP_RUN_OUTPUT_CHARS:]
    if done.returncode != 0:
        return False, f"{check['run']} stopped with an error. Read the last line of the traceback, fix it, run it again.", output
    missing = [text for text in check["expect"] if text not in done.stdout]
    if missing:
        return False, f"{check['run']} runs, but its output does not show {', '.join(repr(text) for text in missing)} yet.", output
    return True, f"{check['run']} runs and prints what it should.", output


@app.post("/api/battle/setup-check")
def check_setup_step(payload: BattleQuestionRequest):
    """Verify a workshop setup step (folder, file, first run) on disk. Free:
    no PYR call. Not done yet is not a miss; the learner just tries again."""

    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
        encounter = STATE_SERVICE.encounter_projection(progress)
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not isinstance(encounter, dict) or not encounter.get("mob_name"):
        raise HTTPException(status_code=409, detail="There is no campaign battle right now")
    objective = next((item for item in encounter.get("available_objectives") or [] if item.get("id") == payload.objective_id), None)
    if objective is None or objective.get("question_type") != "setup_check" or not isinstance(objective.get("check"), dict):
        raise HTTPException(status_code=409, detail="That objective is not an open setup step")
    project = next((item for item in progress.get("projects", []) if isinstance(item, dict) and item.get("status") == "active"), {})
    story = load_campaign_bounties().get(str(project.get("branch") or ""))
    folder = project_dir_name(story.get("project_dir")) if isinstance(story, dict) else ""
    if not folder:
        raise HTTPException(status_code=409, detail="This campaign has no project folder")
    # The check (it may run the learner's file) happens outside the state lock;
    # recording it re-checks that the objective is still open.
    passed, reason, output = _setup_check(safe_path(folder), objective["check"])
    if not passed:
        return {"ok": True, "verdict": "not_yet", "reason": reason, "output": output}
    try:
        with PROGRESS_LOCK:
            applied = STATE_SERVICE.apply_internal(
                "record_battle_objective",
                {"objective_id": payload.objective_id, "evidence_id": f"setup-{uuid.uuid4().hex[:16]}", "reason": "Setup step checked on disk"},
            )
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"ok": True, "verdict": "correct", "reason": reason, "output": output, "result": applied.get("result")}


# Tutor sparring: one live question per foe, by foe id.
SPAR_QUESTIONS: dict[str, dict[str, object]] = {}
SPAR_ROUNDS = 5


class SparQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    round: int = Field(default=1, ge=1, le=SPAR_ROUNDS)


class SparOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    option_index: int = Field(ge=0, le=7)


def _spar_foe(target_id: str) -> dict:
    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    foe = next((item for item in STATE_SERVICE.spar_roster(progress) if item["id"] == target_id), None)
    if foe is None:
        raise HTTPException(status_code=404, detail="You can only spar with foes you have already met")
    return foe


@app.post("/api/ai/spar-question")
def ai_spar_question(payload: SparQuestionRequest):
    """PYR writes the next sparring question (a simulated fight: no damage)."""

    foe = _spar_foe(payload.target_id)
    question_type = "true_false" if payload.round % 3 == 0 else "multiple_choice"
    written = _ai_call(
        ai_tutor.write_spar_question,
        concept=foe["concept"] or foe["name"],
        foe=foe["name"],
        question_type=question_type,
        round_number=payload.round,
        rounds=SPAR_ROUNDS,
        studied=_studied_ideas(f"{foe['concept']} {foe['name']}"),
    )
    key = f"spar:{payload.target_id}"
    SPAR_QUESTIONS[key] = {"prompt": written["prompt"], "options": written["options"], "question_type": question_type}
    CHOICE_ANSWER_KEYS[key] = {"answer": written["answer"], "why": written.get("why", ""), "options": written["options"]}
    return {"ok": True, "question": {"target_id": payload.target_id, "round": payload.round, **SPAR_QUESTIONS[key]}}


@app.post("/api/spar/answer-option")
def answer_spar_option(payload: SparOptionRequest):
    """Grade a sparring click. Each question is its own practice drill, so a
    right first click earns sign XP exactly like Tutor practice; nothing hurts."""

    foe = _spar_foe(payload.target_id)
    key = f"spar:{payload.target_id}"
    with PROGRESS_LOCK:
        question = SPAR_QUESTIONS.pop(key, None)
        answer = CHOICE_ANSWER_KEYS.pop(key, None)
        if not question or not answer:
            raise HTTPException(status_code=409, detail="That sparring question is no longer open")
        options = list(question.get("options") or [])
        if payload.option_index >= len(options):
            raise HTTPException(status_code=422, detail="That question has no such option")
        correct_text = options[int(answer["answer"])]
        verdict = "correct" if payload.option_index == int(answer["answer"]) else "incorrect"
        why = str(answer.get("why") or "")
        reason = ((why or f"Right: {correct_text}.") if verdict == "correct" else f"The answer was {correct_text}. {why}".strip())[:400]
        concept = HUNTER_SIGN_CONCEPTS.get(foe.get("sign") or "", foe["concept"] or foe["name"])
        try:
            started = STATE_SERVICE.apply("practice_session_started", {"concept": concept[:120], "question_type": str(question["question_type"]), "difficulty": 2}, "player")
            session_id = started["result"]["session"]["session_id"]
            recorded = STATE_SERVICE.apply_internal(
                "practice_record_attempt",
                {"session_id": session_id, "outcome": verdict, "evidence_id": f"sp-click-{uuid.uuid4().hex[:16]}", "reason": reason},
            )
        except StateCommandError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"ok": True, "verdict": verdict, "reason": reason, "correct_index": int(answer["answer"]), "hunter_gain": recorded["result"].get("hunter_gain")}


class DungeonOptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    question_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    option_index: int = Field(ge=0, le=7)


@app.post("/api/dungeon/answer-option")
def answer_dungeon_option(payload: DungeonOptionRequest):
    """Grade a clicked option instantly against the hidden key. Without a key
    (a built-in question, or after a restart) the browser falls back to PYR.
    A wrong click shows the answer and deals a fresh question."""

    key_name = f"dungeon:{payload.question_id}"
    with PROGRESS_LOCK:
        try:
            progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
            projection = STATE_SERVICE.dungeon_projection(progress)
        except StateCommandError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        question = projection.get("question") if isinstance(projection.get("question"), dict) else None
        if not projection.get("active") or projection.get("run_id") != payload.run_id or not question or question.get("id") != payload.question_id:
            raise HTTPException(status_code=409, detail="That Dungeon question is no longer current")
        options = list(question.get("options") or [])
        if not options or payload.option_index >= len(options):
            raise HTTPException(status_code=422, detail="That question has no such option")
        key = CHOICE_ANSWER_KEYS.get(key_name)
        if key is None or key.get("options") != options:
            return {"ok": True, "graded": False}
        CHOICE_ANSWER_KEYS.pop(key_name, None)
        correct_text = options[int(key["answer"])]
        verdict = "correct" if payload.option_index == int(key["answer"]) else "incorrect"
        why = str(key.get("why") or "")
        reason = (why or f"Right: {correct_text}.") if verdict == "correct" else f"The answer was {correct_text}. {why}".strip()
        try:
            STATE_SERVICE.apply_internal(
                "dungeon_record_verdict",
                {"run_id": payload.run_id, "question_id": payload.question_id, "verdict": verdict, "evidence_id": f"dg-click-{uuid.uuid4().hex[:16]}", "reason": reason[:400]},
            )
            progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
            after = STATE_SERVICE.dungeon_projection(progress)
            if verdict == "incorrect" and after.get("active") and (after.get("question") or {}).get("id") == payload.question_id:
                STATE_SERVICE.apply_internal("dungeon_reroll_question", {"run_id": payload.run_id, "question_id": payload.question_id})
                progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
                after = STATE_SERVICE.dungeon_projection(progress)
        except StateCommandError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {"ok": True, "graded": True, "verdict": verdict, "reason": reason, "correct_index": int(key["answer"]), "dungeon": after}


@app.post("/api/ai/practice-lens")
def ai_practice_lens(payload: AiPracticeLensRequest):
    lenses = [
        {"id": str(item.get("id", ""))[:40], "label": str(item.get("label", ""))[:80], "prompt": str(item.get("prompt", ""))[:300]}
        for item in payload.lenses
        if item.get("id")
    ]
    try:
        progress, _metadata = STATE_SERVICE.snapshot_with_metadata()
        learner = {
            "practice": STATE_SERVICE.practice_projection(progress),
            "skills": progress.get("skills", [])[:20],
            "learning_state": progress.get("learning_state"),
        }
    except StateCommandError:
        learner = {}
    return {"ok": True, **_ai_call(ai_tutor.choose_practice_lens, concept=payload.concept, lenses=lenses, learner=learner)}


@app.post("/api/ai/ask")
def ai_ask(payload: AiAskRequest):
    reply = _ai_call(ai_tutor.ask, question=payload.question, concept=payload.concept, code=payload.code)
    assist = None
    if payload.battle:
        # Only a reply that arrived counts; with no fight on, help is free.
        try:
            with PROGRESS_LOCK:
                assist = STATE_SERVICE.apply_internal("record_pyr_assist", {"reason": "Asked PYR during a fight"}).get("result")
        except StateCommandError:
            assist = None
    return {"ok": True, "reply": reply, "assist": assist}


# App mode (`ide/quest.py --app`, used by the desktop shell) serves the built
# frontend from this same origin. Mounted last so every /api and /ws route
# above keeps priority over the static catch-all.
_SERVE_DIST = os.getenv("QUESTLAB_SERVE_DIST", "").strip()
if _SERVE_DIST and (Path(_SERVE_DIST) / "index.html").is_file():
    from starlette.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=_SERVE_DIST, html=True), name="frontend")
