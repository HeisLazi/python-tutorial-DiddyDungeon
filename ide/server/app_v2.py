from __future__ import annotations

import asyncio
import fcntl
import hashlib
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
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ide.server.context_bridge import (
    ContextValueError,
    bounded_file,
    bounded_text,
    build_context,
    is_sensitive_path,
)
from ide.server.security import allowed_hosts, allowed_origins, is_allowed_origin
from ide.server.state import (
    BOSS_REQUIREMENTS,
    MAX_CODEX_NOTE_BYTES,
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
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
    "dist",
    "build",
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
PROGRESS_LOCK = threading.RLock()
STATE_SERVICE = LocalStateService(lambda: PROGRESS_PATH, PROGRESS_LOCK)
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


class HomesteadEquip(BaseModel):
    item_id: str


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


class PyrBossSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    requirement_id: Literal["required_behavior", "explanation", "interview"]
    answer: str = Field(min_length=1, max_length=20_000)


class PyrBossVerdictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    nonce: str = Field(min_length=16, max_length=128)
    submission_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    answer_digest: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    verdict: Literal["correct", "incorrect"]
    requirement_id: Literal["required_behavior", "explanation", "interview"]
    evidence_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    reason: str = Field(min_length=1, max_length=MAX_REASON_LENGTH)


class DungeonStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)
    seed: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)


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


class DungeonMarketRequest(DungeonRunRequest):
    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonEquipRequest(DungeonRunRequest):
    item_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)


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
            if child.name in IGNORED_DIRS or child.name in {
                "progress.json",
                DUNGEON_PATH.name,
                f"{DUNGEON_PATH.name}.tmp",
                TUTOR_PATH.name,
                NOTES_DIR_NAME,
            } or child.name.startswith(".DS_Store"):
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
            "ruff": importlib.util.find_spec("ruff") is not None,
        },
    }


@app.get("/api/campaign")
def campaign():
    try:
        progress, metadata = STATE_SERVICE.snapshot_with_metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    dungeon_projection = safe_campaign_dungeon_projection(progress)
    activity = read_json(REPO_ROOT / "activity.json", {})
    return {
        "progress": progress,
        "revision": metadata["revision"],
        "sync_storage_namespace": checkout_storage_namespace(),
        "equipment_projection": STATE_SERVICE.equipment_projection(progress),
        "encounter": STATE_SERVICE.encounter_projection(progress),
        "codex_projection": STATE_SERVICE.codex_projection(progress),
        "practice_projection": STATE_SERVICE.practice_projection(progress),
        "dungeon": dungeon_projection,
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


@app.post("/api/dungeon/market")
def purchase_dungeon_market(payload: DungeonMarketRequest):
    return _dungeon_player_action("dungeon_market_purchase", payload.model_dump())


@app.post("/api/dungeon/equip")
def equip_dungeon_item(payload: DungeonEquipRequest):
    return _dungeon_player_action("dungeon_equip_item", payload.model_dump())


@app.post("/api/dungeon/leave")
def leave_dungeon_room(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_leave_room", payload.model_dump())


@app.post("/api/dungeon/finish")
def finish_dungeon_run(payload: DungeonRunRequest):
    return _dungeon_player_action("dungeon_finish_run", payload.model_dump())


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
            context["verdict"]["requirements"] = list(BOSS_REQUIREMENTS)
            context["verdict"]["verified_requirements"] = sorted(existing.get("boss_verified", {}).keys())
        for field in ("submission_id", "objective_id", "answer_digest", "evidence_id"):
            if field in existing:
                context["verdict"][field] = existing[field]


def _attach_pyr_dungeon_challenge(
    context: dict, *, revision: int, dungeon: dict | None, client_id: str, rotate: bool
) -> None:
    """Attach a short-lived answer-bound challenge for an active Dungeon room."""

    global PYR_DUNGEON_CHALLENGE
    client_key = _pyr_client_id(client_id)
    if not isinstance(dungeon, dict) or not dungeon.get("active") or dungeon.get("room_type") != "encounter":
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

                submission_id = f"battle-{secrets.token_hex(12)}"
                evidence_id = submission_id
                answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
                challenge.update(
                    {
                        "submission_id": submission_id,
                        "objective_id": objective_id,
                        "question_type": str(objective.get("question_type") or "verified"),
                        "impact": int(objective.get("impact") or 0),
                        "evidence_id": evidence_id,
                        "answer_digest": answer_digest,
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
                if metadata["revision"] != challenge.get("revision") or not projection.get("active") or projection.get("room_type") != "encounter":
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
                submission_id = f"boss-{secrets.token_hex(12)}"
                evidence_id = submission_id
                answer_digest = hashlib.sha256(answer.encode("utf-8")).hexdigest()
                submissions[requirement_id] = {
                    "submission_id": submission_id,
                    "evidence_id": evidence_id,
                    "answer_digest": answer_digest,
                    "requirement_id": requirement_id,
                    "question_type": "interview" if requirement_id == "interview" else "explanation",
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
            "expires_in": max(0, int(float(challenge["expires_at"]) - time.monotonic())),
        },
    }


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
                if all(requirement in verified for requirement in BOSS_REQUIREMENTS):
                    reason = "Boss requirements verified; " + "; ".join(
                        str(verified[requirement].get("reason") or "validated") for requirement in BOSS_REQUIREMENTS
                    )
                    mutation = STATE_SERVICE.apply_internal(
                        "record_boss_clear",
                        {
                            "evidence_id": verified["required_behavior"]["evidence_id"],
                            "explanation_evidence_id": verified["explanation"]["evidence_id"],
                            "interview_evidence_id": verified["interview"]["evidence_id"],
                            "reason": reason[:MAX_REASON_LENGTH],
                        },
                    )
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
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "path": target.relative_to(WORKSPACE).as_posix(), "bytes": len(encoded)}


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
    target.write_text(payload.content, encoding="utf-8")
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


@app.post("/api/homestead/equip")
def equip_homestead_item(payload: HomesteadEquip):
    envelope = _apply_state_or_http("homestead_equip", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


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
