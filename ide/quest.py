#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND = REPO_ROOT / "ide" / "frontend"


def parse_args():
    parser = argparse.ArgumentParser(description="Launch the local Python Quest Lab IDE")
    parser.add_argument(
        "--workspace",
        default=str(REPO_ROOT),
        help="Folder the editor/terminal may access. A git worktree for the active quest is recommended.",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically open the browser")
    parser.add_argument(
        "--use-local-state",
        action="store_true",
        help="review and explicitly migrate to this checkout's per-device local state before launching",
    )
    parser.add_argument(
        "--confirm-local-state",
        action="store_true",
        help="accept the reviewed custody migration without an interactive token prompt",
    )
    parser.add_argument("--backend-port", type=int, default=7331, help="Preferred backend port (auto-falls forward if busy)")
    parser.add_argument("--frontend-port", type=int, default=5173, help="Preferred frontend port (auto-falls forward if busy)")
    parser.add_argument(
        "--reload-backend",
        action="store_true",
        help="Development only: enable uvicorn reload. This intentionally restarts PTY terminals when backend files change.",
    )
    return parser.parse_args()


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def checkout_head_sha(root: Path) -> str:
    """Return the exact checkout revision used to launch both child processes."""

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def choose_port(preferred: int, *, avoid: set[int] | None = None) -> int:
    avoid = avoid or set()
    for port in range(preferred, preferred + 100):
        if port not in avoid and port_available(port):
            return port
    raise SystemExit(f"Could not find a free localhost port near {preferred}")


def wait_for_port(port: int, timeout: float = 8.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def running_under_wsl() -> bool:
    if os.getenv("WSL_DISTRO_NAME") or os.getenv("WSL_INTEROP"):
        return True
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def linux_rollup_optional_dependency_ready(frontend: Path) -> bool:
    """Return whether a WSL frontend has a native Rollup optional package."""

    if not running_under_wsl():
        return True
    rollup_root = frontend / "node_modules" / "@rollup"
    return any(
        (rollup_root / package).is_dir()
        for package in (
            "rollup-linux-arm-gnueabihf",
            "rollup-linux-arm-musleabihf",
            "rollup-linux-x64-gnu",
            "rollup-linux-x64-musl",
            "rollup-linux-arm64-gnu",
            "rollup-linux-arm64-musl",
            "rollup-linux-loong64-gnu",
            "rollup-linux-loong64-musl",
            "rollup-linux-ppc64-gnu",
            "rollup-linux-ppc64-musl",
            "rollup-linux-riscv64-gnu",
            "rollup-linux-riscv64-musl",
            "rollup-linux-s390x-gnu",
        )
    )


def prepare_local_state(workspace: Path, *, use_local_state: bool, confirm_local_state: bool) -> Path:
    """Review and, only when explicitly requested, switch to local custody."""

    canonical = REPO_ROOT / "progress.json"
    if not use_local_state:
        return canonical

    # Importing the server here keeps the normal launcher path lightweight and
    # lets this preflight use exactly the same destination derivation and state
    # service as the running backend, without starting a second server.
    from ide.server import app_v2
    from ide.server.state import CUSTODY_CONFIRMATION_TOKEN, StateCommandError

    original_root = app_v2.REPO_ROOT
    original_workspace = app_v2.WORKSPACE
    original_progress = app_v2.PROGRESS_PATH
    app_v2.REPO_ROOT = REPO_ROOT
    app_v2.WORKSPACE = workspace
    app_v2.PROGRESS_PATH = canonical
    try:
        report = app_v2.local_state_custody_report()
        print("\nLocal state custody preview:")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        status = report.get("status")
        if status in {"no-source-found", "conflict"}:
            raise SystemExit(f"Local custody cannot proceed while preview status is '{status}'.")
        if status == "current":
            return canonical
        if status != "already-local":
            approved = confirm_local_state
            if not approved and sys.stdin.isatty():
                response = input(f"Type {CUSTODY_CONFIRMATION_TOKEN} to copy this snapshot: ").strip()
                approved = response == CUSTODY_CONFIRMATION_TOKEN
            if not approved:
                raise SystemExit(
                    "Custody migration was not confirmed. Review the preview and rerun with "
                    "--confirm-local-state or an interactive token prompt."
                )
            expected_revision = report.get("source_revision")
            if not isinstance(expected_revision, int) or expected_revision < 0:
                raise SystemExit("Custody preview did not contain a valid source revision.")
            try:
                result = app_v2.STATE_SERVICE.migrate_local_state(
                    app_v2.proposed_local_state_path(),
                    expected_source_revision=expected_revision,
                    confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
                    forbidden_paths=(app_v2.PROGRESS_PATH, app_v2.legacy_progress_path()),
                )
            except StateCommandError as exc:
                raise SystemExit(f"Custody migration rejected: {exc.detail}") from exc
            print("Local state custody result:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        return app_v2.proposed_local_state_path()
    finally:
        app_v2.REPO_ROOT = original_root
        app_v2.WORKSPACE = original_workspace
        app_v2.PROGRESS_PATH = original_progress


def open_local_browser(url: str) -> bool:
    """Open the Windows browser when launched from WSL, else use Python's browser helper."""
    if running_under_wsl():
        wslview = shutil.which("wslview")
        if wslview:
            subprocess.Popen([wslview, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True

        powershell = shutil.which("powershell.exe")
        if powershell:
            subprocess.Popen(
                [powershell, "-NoProfile", "-Command", "Start-Process", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

        cmd = shutil.which("cmd.exe")
        if cmd:
            subprocess.Popen(
                [cmd, "/c", "start", "", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True

    try:
        return bool(webbrowser.open(url))
    except Exception:
        return False


def main():
    args = parse_args()
    if args.confirm_local_state and not args.use_local_state:
        raise SystemExit("--confirm-local-state requires --use-local-state")
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist: {workspace}")
    if not (FRONTEND / "node_modules").exists():
        raise SystemExit("Frontend dependencies are missing. Run: cd ide/frontend && npm install")
    if not linux_rollup_optional_dependency_ready(FRONTEND):
        raise SystemExit(
            "WSL frontend dependencies are a Windows node_modules tree without a Linux Rollup optional package. "
            "Run npm ci inside this WSL checkout (or use a clean Linux filesystem) before launching Forge."
        )
    if not shutil.which("npm"):
        raise SystemExit("npm is not on PATH")

    backend_port = choose_port(args.backend_port)
    frontend_port = choose_port(args.frontend_port, avoid={backend_port})

    env = os.environ.copy()
    env["QUESTLAB_REPO_ROOT"] = str(REPO_ROOT)
    # State is always anchored to the platform checkout; PYR/CLI processes do
    # not infer a save path from their terminal cwd.
    env["QUESTLAB_STATE_PATH"] = str(REPO_ROOT / "progress.json")
    env["QUESTLAB_WORKSPACE"] = str(workspace)
    env["QUESTLAB_BACKEND_PORT"] = str(backend_port)
    env["QUESTLAB_FRONTEND_PORT"] = str(frontend_port)
    env["QUESTLAB_EXPECTED_BRANCH"] = "feature/cloud-sync-desktop"
    # Vite embeds this marker into the frontend bundle so a stale frontend
    # paired with a newer backend can identify itself instead of silently
    # presenting an older UI. Manual `npm run dev` remains supported but has
    # no authoritative marker and falls back to the branch/runtime checks.
    env["QUESTLAB_BUILD_SHA"] = checkout_head_sha(REPO_ROOT)
    if args.use_local_state:
        local_state_path = prepare_local_state(
            workspace,
            use_local_state=True,
            confirm_local_state=args.confirm_local_state,
        )
        env["QUESTLAB_STATE_PATH"] = str(local_state_path)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "ide.server.app_v2:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(backend_port),
    ]
    if args.reload_backend:
        backend_cmd.append("--reload")

    frontend_cmd = [
        "npm",
        "run",
        "dev",
        "--",
        "--host",
        "127.0.0.1",
        "--port",
        str(frontend_port),
        "--strictPort",
    ]

    url = f"http://127.0.0.1:{frontend_port}"

    print("\n🔥 Python Quest Lab — Forge v2")
    print(f"   platform:  {REPO_ROOT}")
    print(f"   workspace: {workspace}")
    print(f"   backend:   http://127.0.0.1:{backend_port}")
    print(f"   web:       {url}")
    if backend_port != args.backend_port:
        print(f"   note:      port {args.backend_port} was busy, so Forge moved the backend to {backend_port}")
    if frontend_port != args.frontend_port:
        print(f"   note:      port {args.frontend_port} was busy, so Forge moved the UI to {frontend_port}")
    print("   terminals: stable PTY mode (backend reload off)\n")

    backend = subprocess.Popen(backend_cmd, cwd=REPO_ROOT, env=env)
    frontend = subprocess.Popen(frontend_cmd, cwd=FRONTEND, env=env)
    processes = [backend, frontend]

    stopping = False

    def stop(*_):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        deadline = time.time() + 3
        while time.time() < deadline and any(proc.poll() is None for proc in processes):
            time.sleep(0.1)
        for proc in processes:
            if proc.poll() is None:
                proc.kill()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    if not args.no_browser:
        if wait_for_port(frontend_port):
            if not open_local_browser(url):
                print(f"   browser:   could not auto-open; open this in Windows manually: {url}")
        else:
            print(f"   browser:   frontend was not ready yet; open manually when it starts: {url}")

    exit_code = 0
    try:
        while not stopping:
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"A Quest Lab process exited with code {code}.")
                    if code != 0:
                        exit_code = code
                    stop()
                    break
            time.sleep(0.5)
    finally:
        stop()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
