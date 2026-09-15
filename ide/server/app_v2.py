from __future__ import annotations

import asyncio
import fcntl
import hashlib
import importlib.util
import json
import os
import pty
import secrets
import shutil
import signal
import struct
import subprocess
import sys
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
    MAX_DUNGEON_EDITOR_BYTES,
    MAX_IDENTIFIER_LENGTH,
    MAX_REASON_LENGTH,
    LocalStateService,
    StateApplyRequest,
    StateCommandError,
    StateSyncApplyRequest,
    legacy_state_report,
    opaque_device_id,
    state_authority_info,
)

REPO_ROOT = Path(os.getenv("QUESTLAB_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
WORKSPACE = Path(os.getenv("QUESTLAB_WORKSPACE", REPO_ROOT)).resolve()


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


PROGRESS_PATH = configured_progress_path()
TUTOR_PATH = WORKSPACE / "tutor.py"
DUNGEON_PATH = WORKSPACE / "dungeon.py"
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
PYR_CONTEXT_LOCK = threading.RLock()
PYR_CONTEXT_INPUT: dict[str, str | None] = {
    "active_path": None,
    "selection": "",
    "terminal_tail": "",
}
PYR_CONTEXT_CHALLENGE: dict[str, object] | None = None

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


class FormatRequest(BaseModel):
    path: str
    content: str


class HomesteadPurchase(BaseModel):
    item_id: str


class HomesteadEquip(BaseModel):
    item_id: str


class PyrContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active_path: str | None = Field(default=None, max_length=240)
    selection: str = Field(default="", max_length=64_000)
    terminal_tail: str = Field(default="", max_length=64_000)


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


class DungeonStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)
    seed: str | None = Field(default=None, max_length=MAX_IDENTIFIER_LENGTH)


class DungeonEditorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(min_length=1, max_length=MAX_IDENTIFIER_LENGTH)
    content: str = Field(max_length=MAX_DUNGEON_EDITOR_BYTES)


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


def state_path_kind(target: Path) -> str | None:
    canonical = PROGRESS_PATH.resolve()
    if target.resolve() == canonical:
        return "canonical"
    if target.resolve() == legacy_progress_path() and target.resolve() != canonical:
        return "legacy"
    if target.resolve() == DUNGEON_PATH.resolve():
        return "dungeon_projection"
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


def git_info() -> dict:
    def run(*args: str) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(WORKSPACE), *args],
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
    return {
        "branch": branch,
        "dirty_count": len(status_lines),
        "status": status_lines[:50],
        "last_commit": run("log", "-1", "--pretty=%h %s"),
    }


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
            if child.name in IGNORED_DIRS or child.name in {DUNGEON_PATH.name, TUTOR_PATH.name} or child.name.startswith(".DS_Store"):
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
    return {
        "shell": shell,
        "python": sys.executable,
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
    activity = read_json(REPO_ROOT / "activity.json", {})
    return {
        "progress": progress,
        "revision": metadata["revision"],
        "encounter": STATE_SERVICE.encounter_projection(progress),
        "dungeon": STATE_SERVICE.dungeon_projection(progress),
        "activity": activity,
        "git": git_info(),
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


@app.get("/api/state/revision")
def state_revision():
    try:
        metadata = STATE_SERVICE.metadata()
    except StateCommandError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return {**metadata, "state_authority": state_authority_info(PROGRESS_PATH, WORKSPACE)}


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


PYR_VERDICT_TTL_SECONDS = 300


def _attach_pyr_verdict_challenge(
    context: dict,
    *,
    revision: int,
    encounter: dict | None,
    rotate: bool,
) -> None:
    """Attach one short-lived challenge for a trusted PYR verdict call."""

    global PYR_CONTEXT_CHALLENGE
    mob_name = encounter.get("mob_name") if isinstance(encounter, dict) else None
    project_id = encounter.get("project_id") if isinstance(encounter, dict) else None
    if not mob_name or not project_id:
        with PYR_CONTEXT_LOCK:
            PYR_CONTEXT_CHALLENGE = None
        context["verdict"] = None
        return

    now = time.monotonic()
    with PYR_CONTEXT_LOCK:
        existing = PYR_CONTEXT_CHALLENGE
        valid_existing = (
            isinstance(existing, dict)
            and existing.get("revision") == revision
            and existing.get("project_id") == project_id
            and existing.get("mob_name") == mob_name
            and float(existing.get("expires_at", 0)) > now
        )
        # Keep an issued answer-bound challenge stable while the user submits
        # the prompt to the provider. A background/context refresh must not
        # invalidate the only pending Battle answer; a completed verdict still
        # clears the challenge before a fresh one can be issued.
        if rotate and valid_existing and existing.get("submission_id"):
            rotate = False
        if rotate or not valid_existing:
            existing = {
                "nonce": secrets.token_urlsafe(24),
                "revision": revision,
                "project_id": project_id,
                "mob_name": mob_name,
                "expires_at": now + PYR_VERDICT_TTL_SECONDS,
            }
            PYR_CONTEXT_CHALLENGE = existing
        context["verdict"] = {
            "nonce": existing["nonce"],
            "revision": existing["revision"],
            "project_id": existing["project_id"],
            "mob_name": existing["mob_name"],
            "expires_in": max(0, int(float(existing["expires_at"]) - now)),
        }
        for field in ("submission_id", "objective_id", "answer_digest", "evidence_id"):
            if field in existing:
                context["verdict"][field] = existing[field]


def _capture_pyr_context(payload: PyrContextRequest, *, rotate_challenge: bool = False) -> dict:
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
    with PYR_CONTEXT_LOCK:
        PYR_CONTEXT_INPUT.update(
            {
                "active_path": normalized_path,
                "selection": selection,
                "terminal_tail": terminal_tail,
            }
        )
    _attach_pyr_verdict_challenge(
        context,
        revision=metadata["revision"],
        encounter=encounter,
        rotate=rotate_challenge,
    )
    return context


def _stored_pyr_context_request() -> PyrContextRequest:
    with PYR_CONTEXT_LOCK:
        values = dict(PYR_CONTEXT_INPUT)
    return PyrContextRequest(**values)


@app.get("/api/pyr/context")
def read_pyr_context():
    """Return the latest bounded editor/terminal context and live campaign view."""

    return {"ok": True, "context": _capture_pyr_context(_stored_pyr_context_request())}


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
        challenge = PYR_CONTEXT_CHALLENGE
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce:
            raise HTTPException(status_code=409, detail="PYR challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            PYR_CONTEXT_CHALLENGE = None
            raise HTTPException(status_code=409, detail="PYR challenge expired; capture context again")
        if challenge.get("submission_id"):
            raise HTTPException(status_code=409, detail="This PYR challenge already has a Battle submission")

        with PROGRESS_LOCK:
            try:
                progress, metadata = STATE_SERVICE.snapshot_with_metadata()
                encounter = STATE_SERVICE.encounter_projection(progress)
                if metadata["revision"] != challenge.get("revision"):
                    PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Campaign changed; capture fresh PYR context")
                if (
                    not isinstance(encounter, dict)
                    or encounter.get("project_id") != challenge.get("project_id")
                    or encounter.get("mob_name") != challenge.get("mob_name")
                ):
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
        challenge = PYR_CONTEXT_CHALLENGE
        now = time.monotonic()
        if not isinstance(challenge, dict) or challenge.get("nonce") != nonce:
            raise HTTPException(status_code=409, detail="PYR verdict challenge is missing or already used")
        if float(challenge.get("expires_at", 0)) <= now:
            PYR_CONTEXT_CHALLENGE = None
            raise HTTPException(status_code=409, detail="PYR verdict challenge expired; capture context again")
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
                    PYR_CONTEXT_CHALLENGE = None
                    raise HTTPException(status_code=409, detail="Campaign changed; capture fresh PYR context")
                if (
                    not isinstance(encounter, dict)
                    or encounter.get("project_id") != challenge.get("project_id")
                    or encounter.get("mob_name") != challenge.get("mob_name")
                ):
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
    return {"path": "tutor.py", "content": content, "revision": tutor_revision(content)}


@app.put("/api/tutor")
def write_tutor(payload: TutorWrite):
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="Tutor notebook is too large")
    target = ensure_tutor_file()
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "path": "tutor.py", "bytes": len(encoded), "revision": tutor_revision(payload.content)}


@app.post("/api/format")
def format_file(payload: FormatRequest):
    target = safe_path(payload.path)
    reject_state_file_access(target)
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="File is too large for the learning editor")

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
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


@app.post("/api/homestead/purchase")
def purchase_homestead_item(payload: HomesteadPurchase):
    envelope = _apply_state_or_http("homestead_purchase", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


@app.post("/api/homestead/equip")
def equip_homestead_item(payload: HomesteadEquip):
    envelope = _apply_state_or_http("homestead_equip", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


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
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["QUESTLAB_WORKSPACE"] = str(WORKSPACE)
    env["QUESTLAB_TERMINAL_ROLE"] = role

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

            payload = message.get("data", "") if isinstance(message, dict) and message.get("type") == "input" else text
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
