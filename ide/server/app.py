from __future__ import annotations

import asyncio
import fcntl
import json
import os
import pty
import signal
import struct
import subprocess
import sys
import termios
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

REPO_ROOT = Path(os.getenv("QUESTLAB_REPO_ROOT", Path(__file__).resolve().parents[2])).resolve()
WORKSPACE = Path(os.getenv("QUESTLAB_WORKSPACE", REPO_ROOT)).resolve()
PROGRESS_PATH = REPO_ROOT / "progress.json"
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

app = FastAPI(title="Python Quest Lab Local Server", version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FileWrite(BaseModel):
    path: str
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


def write_json_atomic(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def load_progress() -> dict:
    progress = read_json(PROGRESS_PATH, {})
    if not progress:
        raise HTTPException(status_code=500, detail="progress.json could not be loaded")
    return progress


def homestead_catalog(progress: dict) -> dict[str, dict]:
    homestead = progress.get("homestead") or {}
    return {
        str(item.get("id")): item
        for item in homestead.get("catalog", [])
        if isinstance(item, dict) and item.get("id")
    }


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
    progress = read_json(PROGRESS_PATH, {})
    activity = read_json(REPO_ROOT / "activity.json", {})
    return {
        "progress": progress,
        "activity": activity,
        "git": git_info(),
        "workspace": str(WORKSPACE),
        "repo_root": str(REPO_ROOT),
    }


@app.post("/api/homestead/purchase")
def purchase_homestead_item(payload: HomesteadPurchase):
    progress = load_progress()
    homestead = progress.get("homestead")
    if not isinstance(homestead, dict):
        raise HTTPException(status_code=409, detail="Homestead state is not initialized")

    catalog = homestead_catalog(progress)
    item = catalog.get(payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown Homestead item")

    owned = homestead.setdefault("owned_cosmetics", [])
    if payload.item_id in owned:
        return {
            "ok": True,
            "already_owned": True,
            "item": item,
            "coins": int((progress.get("player") or {}).get("coins", 0)),
        }

    try:
        price = max(0, int(item.get("price", 0)))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=500, detail="Invalid Homestead item price") from exc

    player = progress.setdefault("player", {})
    try:
        coins = int(player.get("coins", 0))
    except (TypeError, ValueError):
        coins = 0

    if coins < price:
        raise HTTPException(
            status_code=409,
            detail=f"Not enough coins. {item.get('name', 'This item')} costs {price}c and you have {coins}c.",
        )

    player["coins"] = coins - price
    owned.append(payload.item_id)
    homestead.setdefault("purchase_history", []).append(
        {
            "item_id": payload.item_id,
            "name": item.get("name", payload.item_id),
            "price": price,
            "purchased_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    write_json_atomic(PROGRESS_PATH, progress)

    return {
        "ok": True,
        "item": item,
        "coins": player["coins"],
        "owned_cosmetics": owned,
    }


@app.post("/api/homestead/equip")
def equip_homestead_item(payload: HomesteadEquip):
    progress = load_progress()
    homestead = progress.get("homestead")
    if not isinstance(homestead, dict):
        raise HTTPException(status_code=409, detail="Homestead state is not initialized")

    catalog = homestead_catalog(progress)
    item = catalog.get(payload.item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Unknown Homestead item")

    owned = homestead.setdefault("owned_cosmetics", [])
    if payload.item_id not in owned:
        raise HTTPException(status_code=409, detail="Buy or unlock this cosmetic before equipping it")

    kind = str(item.get("kind", ""))
    if kind not in {"theme", "cursor", "hud", "terminal"}:
        raise HTTPException(status_code=409, detail="This Homestead item cannot be equipped")

    equipped = homestead.setdefault("equipped", {})
    equipped[kind] = payload.item_id
    write_json_atomic(PROGRESS_PATH, progress)

    return {"ok": True, "item": item, "equipped": equipped}


@app.get("/api/tree")
def tree():
    return {"workspace": str(WORKSPACE), "items": build_tree()}


@app.get("/api/file")
def read_file(path: str):
    target = safe_path(path)
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
    encoded = payload.content.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        raise HTTPException(status_code=413, detail="File is too large for the learning editor")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"ok": True, "path": target.relative_to(WORKSPACE).as_posix(), "bytes": len(encoded)}


@app.post("/api/format")
def format_file(payload: FormatRequest):
    target = safe_path(payload.path)
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
            if text.startswith("{"):
                try:
                    candidate = json.loads(text)
                    if isinstance(candidate, dict) and candidate.get("type") in {"input", "resize"}:
                        message = candidate
                except json.JSONDecodeError:
                    pass

            if message and message.get("type") == "resize":
                try:
                    set_pty_size(master_fd, message.get("cols", 120), message.get("rows", 30))
                except (OSError, TypeError, ValueError):
                    pass
                continue

            payload = message.get("data", "") if message and message.get("type") == "input" else text
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
                await asyncio.to_thread(os.waitpid, pid, 0)
            except ChildProcessError:
                pass
