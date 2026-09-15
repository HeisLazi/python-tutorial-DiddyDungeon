from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import os
import pty
import signal
import struct
import subprocess
import sys
import termios
import threading
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from starlette.middleware.trustedhost import TrustedHostMiddleware

from ide.server.security import allowed_hosts, allowed_origins, is_allowed_origin
from ide.server.state import (
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

app = FastAPI(title="Python Quest Lab Local Server", version="0.3.0")
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
    return None


def reject_state_file_access(target: Path) -> None:
    kind = state_path_kind(target)
    if kind:
        if kind == "legacy":
            raise HTTPException(
                status_code=403,
                detail="workspace progress.json is legacy data; use the local state service and canonical repo state",
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
    last_commit = run("log", "-1", "--pretty=%h %s")
    return {
        "branch": branch,
        "dirty_count": len(status_lines),
        "status": status_lines[:50],
        "last_commit": last_commit,
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
            if child.name in IGNORED_DIRS or child.name.startswith(".DS_Store"):
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


@app.get("/api/health")
def health():
    return {"ok": True, "workspace": str(WORKSPACE), "repo_root": str(REPO_ROOT)}


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
        "activity": activity,
        "git": git_info(),
        "workspace": str(WORKSPACE),
        "repo_root": str(REPO_ROOT),
        "state_authority": state_authority_info(PROGRESS_PATH, WORKSPACE),
    }


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


@app.get("/api/tutor")
def read_tutor_notebook():
    target = ensure_tutor_file()
    if target.stat().st_size > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="Tutor notebook is too large")
    content = target.read_text(encoding="utf-8")
    return {"path": "tutor.py", "content": content, "revision": tutor_revision(content)}


@app.put("/api/tutor")
def write_tutor_notebook(payload: TutorWrite):
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="Tutor notebook is too large")
    target = ensure_tutor_file()
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "path": "tutor.py", "bytes": len(encoded), "revision": tutor_revision(payload.content)}


@app.post("/api/homestead/purchase")
def purchase_homestead_item(payload: HomesteadPurchase):
    envelope = _apply_state_or_http("homestead_purchase", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


@app.post("/api/homestead/equip")
def equip_homestead_item(payload: HomesteadEquip):
    envelope = _apply_state_or_http("homestead_equip", payload.model_dump(), "player")
    return _flatten_state_result(envelope)


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

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=415, detail="Formatted file is not valid UTF-8") from exc

    return {
        "ok": True,
        "path": target.relative_to(WORKSPACE).as_posix(),
        "content": content,
        "formatter": formatter,
    }


@app.websocket("/ws/terminal")
async def terminal(websocket: WebSocket):
    if not is_allowed_origin(websocket.headers.get("origin")):
        await websocket.close(code=1008, reason="Origin not allowed")
        return
    await websocket.accept()
    shell = os.getenv("SHELL", "/bin/bash")
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["COLORTERM"] = "truecolor"
    env["QUESTLAB_WORKSPACE"] = str(WORKSPACE)

    try:
        pid, master_fd = pty.fork()
    except OSError as exc:
        await websocket.send_text(f"\r\nFailed to create terminal PTY: {exc}\r\n")
        await websocket.close(code=1011)
        return

    if pid == 0:
        try:
            os.chdir(WORKSPACE)
            os.execvpe(shell, [shell, "-l"], env)
        except Exception as exc:
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
            text = await websocket.receive_text()
            message = None
            json_object = False
            if text.startswith("{"):
                try:
                    candidate = json.loads(text)
                    if isinstance(candidate, dict):
                        json_object = True
                        if candidate.get("type") in {"input", "resize"}:
                            message = candidate
                except json.JSONDecodeError:
                    pass

            # JSON control envelopes are an internal protocol.  Never echo an
            # unknown envelope into the user's shell as literal input.
            if json_object and message is None:
                continue

            if message and message.get("type") == "resize":
                try:
                    set_pty_size(master_fd, message.get("cols", 120), message.get("rows", 30))
                except (OSError, TypeError, ValueError):
                    pass
                continue

            if message:
                if message.get("type") != "input":
                    continue
                payload = message.get("data", "")
            else:
                payload = text
            if payload:
                await asyncio.to_thread(os.write, master_fd, payload.encode("utf-8"))

    output_task = asyncio.create_task(pump_output())
    input_task = asyncio.create_task(pump_input())

    try:
        done, pending = await asyncio.wait(
            {output_task, input_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
        for task in done:
            try:
                await task
            except (WebSocketDisconnect, asyncio.CancelledError):
                pass
    except WebSocketDisconnect:
        pass
    finally:
        for task in (output_task, input_task):
            if not task.done():
                task.cancel()

        if not child_exited(pid):
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            try:
                await asyncio.to_thread(os.waitpid, pid, 0)
            except ChildProcessError:
                pass
        try:
            os.close(master_fd)
        except OSError:
            pass
