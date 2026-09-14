#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import signal
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
    return parser.parse_args()


def main():
    args = parse_args()
    workspace = Path(args.workspace).expanduser().resolve()
    if not workspace.exists() or not workspace.is_dir():
        raise SystemExit(f"Workspace does not exist: {workspace}")
    if not (FRONTEND / "node_modules").exists():
        raise SystemExit("Frontend dependencies are missing. Run: cd ide/frontend && npm install")
    if not shutil.which("npm"):
        raise SystemExit("npm is not on PATH")

    env = os.environ.copy()
    env["QUESTLAB_REPO_ROOT"] = str(REPO_ROOT)
    env["QUESTLAB_WORKSPACE"] = str(workspace)

    backend_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "ide.server.app:app",
        "--host",
        "127.0.0.1",
        "--port",
        "7331",
        "--reload",
    ]
    frontend_cmd = ["npm", "run", "dev", "--", "--host", "127.0.0.1"]

    print("\n🔥 Python Quest Lab IDE")
    print(f"   platform:  {REPO_ROOT}")
    print(f"   workspace: {workspace}")
    print("   web:       http://127.0.0.1:5173\n")

    backend = subprocess.Popen(backend_cmd, cwd=REPO_ROOT, env=env)
    frontend = subprocess.Popen(frontend_cmd, cwd=FRONTEND, env=env)
    processes = [backend, frontend]

    def stop(*_):
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        deadline = time.time() + 3
        while time.time() < deadline and any(proc.poll() is None for proc in processes):
            time.sleep(0.1)
        for proc in processes:
            if proc.poll() is None:
                proc.kill()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    if not args.no_browser:
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:5173")

    try:
        while True:
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    print(f"A Quest Lab process exited with code {code}.")
                    stop()
            time.sleep(0.5)
    finally:
        stop()


if __name__ == "__main__":
    main()
