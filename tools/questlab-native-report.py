#!/usr/bin/env python3
"""Read-only native Linux/CachyOS environment report for Quest Lab.

This command does not start Forge, fetch Git, install packages, call Supabase,
write a report file, or touch the player save.  It gives a physical Linux
acceptance run one reproducible snapshot of the checkout, kernel/toolchain and
native frontend dependency boundary before the live K&M/PTY checks begin.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


EXPECTED_BRANCH = "feature/cloud-sync-desktop"
ROLLUP_LINUX_PREFIX = "rollup-linux-"
REQUIRED_FRONTEND_MANIFESTS = (
    Path("node_modules/vite/package.json"),
    Path("node_modules/@supabase/supabase-js/package.json"),
    Path("node_modules/@supabase/functions-js/package.json"),
)


def _git(repo_root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _command_version(command: str, *args: str) -> dict[str, str | bool]:
    path = shutil.which(command)
    if not path:
        return {"available": False, "path": ""}
    try:
        result = subprocess.run(
            [path, *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return {"available": True, "path": path, "version": "<unreadable>"}
    output = (result.stdout or result.stderr).strip().splitlines()
    return {"available": True, "path": path, "version": output[0] if output else "<unknown>"}


def _native_rollup_packages(frontend: Path) -> list[str]:
    rollup_root = frontend / "node_modules" / "@rollup"
    if not rollup_root.is_dir():
        return []
    return sorted(
        package.name
        for package in rollup_root.iterdir()
        if package.is_dir()
        and package.name.startswith(ROLLUP_LINUX_PREFIX)
        and (package / "package.json").is_file()
    )


def build_report(repo_root: Path, *, allow_stale_checkout: bool = False) -> dict[str, Any]:
    repo_root = repo_root.expanduser().resolve()
    frontend = repo_root / "ide" / "frontend"
    branch = _git(repo_root, "branch", "--show-current")
    head_sha = _git(repo_root, "rev-parse", "--verify", "HEAD")
    upstream_sha = _git(repo_root, "rev-parse", "--verify", f"refs/remotes/origin/{EXPECTED_BRANCH}")
    dirty_paths = _git(repo_root, "-c", "core.quotePath=false", "status", "--porcelain=v1").splitlines()
    manifest_status = {
        str(path): (frontend / path).is_file() for path in REQUIRED_FRONTEND_MANIFESTS
    }
    native_rollup = _native_rollup_packages(frontend)
    checks = {
        "repo_exists": repo_root.is_dir(),
        "expected_branch": branch == EXPECTED_BRANCH,
        "head_resolved": bool(head_sha),
        "upstream_matches": allow_stale_checkout or not upstream_sha or head_sha == upstream_sha,
        "native_python": (repo_root / ".venv" / "bin" / "python").is_file(),
        "launcher_executable": os.access(repo_root / "tools" / "questlab-launch.sh", os.X_OK),
        "state_cli_executable": os.access(repo_root / "questlab-state", os.X_OK),
        "frontend_manifests": all(manifest_status.values()),
        "native_rollup": bool(native_rollup),
    }
    return {
        "report": "questlab-native-linux",
        "repo_root": str(repo_root),
        "branch": branch,
        "head_sha": head_sha,
        "upstream_sha": upstream_sha,
        "allow_stale_checkout": allow_stale_checkout,
        "dirty_paths": dirty_paths,
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "distribution": platform.platform(),
            "python": sys.version.splitlines()[0],
        },
        "toolchain": {
            "git": _command_version("git", "--version"),
            "python3": _command_version("python3", "--version"),
            "node": _command_version("node", "--version"),
            "npm": _command_version("npm", "--version"),
        },
        "frontend": {
            "manifest_status": manifest_status,
            "native_rollup_packages": native_rollup,
        },
        "checks": checks,
        "ready": all(checks.values()) or (allow_stale_checkout and all(value for key, value in checks.items() if key != "upstream_matches")),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report a native Linux Quest Lab environment without writing state.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="platform checkout to inspect (default: this checkout)",
    )
    parser.add_argument("--allow-stale-checkout", action="store_true")
    parser.add_argument("--strict", action="store_true", help="exit 1 unless every native check is green")
    parser.add_argument("--json", action="store_true", help="print only the JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_report(Path(args.repo_root), allow_stale_checkout=args.allow_stale_checkout)
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("Quest Lab native Linux report")
        print(f"Checkout:       {report['branch']} @ {report['head_sha'] or '<unresolved>'}")
        print(f"Platform:       {report['platform']['distribution']}")
        print(f"Kernel:         {report['platform']['release']}")
        for name, value in report["toolchain"].items():
            print(f"{name:15} {value.get('version', '<missing>')}")
        print(f"Native Rollup:   {', '.join(report['frontend']['native_rollup_packages']) or '<missing>'}")
        print(f"Dirty paths:     {len(report['dirty_paths'])}")
        print(f"Ready:           {'GREEN' if report['ready'] else 'BLOCKED'}")
        if args.strict and not report["ready"]:
            print(json.dumps(report, indent=2, ensure_ascii=False), file=sys.stderr)
    return 0 if not args.strict or report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
