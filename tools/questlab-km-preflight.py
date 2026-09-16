#!/usr/bin/env python3
"""Read-only, cross-platform preflight for a manual Quest Lab K&M run.

The PowerShell gate remains the Windows/WSL entry point.  This companion lets
native Linux installs (including CachyOS) perform the same identity, authority
and served-source checks without requiring PowerShell.  It intentionally uses
only Git reads and HTTP GETs: it never mutates state, calls Supabase, restarts
Forge or touches either PTY.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXPECTED_BRANCH = "feature/cloud-sync-desktop"


class PreflightError(RuntimeError):
    """A fail-closed preflight condition."""


def _git(repo_root: Path, *arguments: str, required: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), *arguments],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        if required:
            raise PreflightError(f"could not run git: {exc}") from exc
        return ""
    value = result.stdout.strip()
    if result.returncode != 0 and required:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise PreflightError(f"git {' '.join(arguments)} failed: {detail}")
    return value if result.returncode == 0 else ""


def _read_json(url: str, timeout: float = 5.0) -> dict[str, Any]:
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            value = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PreflightError(f"could not read {url}: {exc}") from exc
    if not isinstance(value, dict):
        raise PreflightError(f"{url} did not return a JSON object")
    return value


def _read_text(url: str, timeout: float = 5.0) -> str:
    request = Request(url, headers={"Accept": "text/plain"}, method="GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise PreflightError(f"could not read {url}: {exc}") from exc


def normalize_path(value: object) -> str:
    """Normalize a served Windows/POSIX path for identity comparisons."""

    return str(value or "").strip().replace("\\", "/").rstrip("/").casefold()


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PreflightError(message)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the read-only Quest Lab K&M preflight.")
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="platform checkout containing the expected branch (default: this checkout)",
    )
    parser.add_argument("--backend-port", type=int, default=7331)
    parser.add_argument("--frontend-port", type=int, default=5173)
    parser.add_argument("--allow-stale-checkout", action="store_true")
    parser.add_argument("--skip-frontend-source", action="store_true")
    parser.add_argument("--require-isolated-state", action="store_true")
    return parser


def run_preflight(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = Path(args.repo_root).expanduser().resolve()
    _require(repo_root.is_dir(), f"repository root does not exist: {repo_root}")

    branch = _git(repo_root, "branch", "--show-current")
    if not args.allow_stale_checkout:
        _require(branch == EXPECTED_BRANCH, f"checkout branch is '{branch}'; expected '{EXPECTED_BRANCH}'")

    head_sha = _git(repo_root, "rev-parse", "--verify", "HEAD")
    _require(bool(head_sha), "could not resolve checkout HEAD")
    upstream_sha = _git(repo_root, "rev-parse", "--verify", f"refs/remotes/origin/{EXPECTED_BRANCH}", required=False)
    if not args.allow_stale_checkout and upstream_sha:
        _require(head_sha == upstream_sha, f"HEAD {head_sha} is not origin/{EXPECTED_BRANCH} {upstream_sha}")

    backend_base = f"http://127.0.0.1:{args.backend_port}"
    frontend_base = f"http://127.0.0.1:{args.frontend_port}"
    runtime = _read_json(f"{backend_base}/api/runtime")
    repo_git = runtime.get("repo_git")
    _require(isinstance(repo_git, dict) and bool(repo_git.get("head_sha")), "backend runtime health does not expose repo HEAD identity")
    if repo_git.get("branch"):
        _require(repo_git["branch"] == EXPECTED_BRANCH, f"backend reports repo branch '{repo_git['branch']}'")
    if not args.allow_stale_checkout and upstream_sha:
        _require(repo_git["head_sha"] == upstream_sha, f"backend HEAD {repo_git['head_sha']} does not match origin/{EXPECTED_BRANCH} {upstream_sha}")

    frontend_runtime = _read_json(f"{frontend_base}/api/runtime")
    frontend_git = frontend_runtime.get("repo_git")
    _require(isinstance(frontend_git, dict) and bool(frontend_git.get("head_sha")), "frontend /api proxy does not expose repo HEAD identity")
    _require(frontend_git.get("head_sha") == repo_git.get("head_sha"), "frontend /api proxy HEAD differs from backend")
    if frontend_git.get("branch") and repo_git.get("branch"):
        _require(frontend_git["branch"] == repo_git["branch"], "frontend /api proxy branch differs from backend")

    authority = runtime.get("state_authority")
    frontend_authority = frontend_runtime.get("state_authority")
    _require(isinstance(authority, dict), "runtime did not expose state authority")
    _require(isinstance(frontend_authority, dict), "frontend /api proxy did not expose state authority")
    for key in ("canonical_path", "legacy_path"):
        _require(authority.get(key), f"runtime state authority has no {key}")
        _require(frontend_authority.get(key), f"frontend state authority has no {key}")
        _require(normalize_path(authority[key]) == normalize_path(frontend_authority[key]), f"frontend /api proxy {key} differs from backend")
    _require(bool(authority.get("canonical_authoritative")), "runtime did not mark one canonical state path authoritative")
    _require(not authority.get("legacy_authoritative"), "runtime marked the legacy/workspace state path authoritative")
    _require(normalize_path(authority["canonical_path"]) != normalize_path(authority["legacy_path"]), "canonical and legacy state paths are not distinct")

    if args.require_isolated_state:
        repo_canonical = normalize_path(repo_root / "progress.json")
        _require(
            normalize_path(authority["canonical_path"]) != repo_canonical,
            "mutating K&M requires an isolated local state cache; active canonical path is the protected repository save",
        )

    revision = _read_json(f"{backend_base}/api/state/revision")
    _require(isinstance(revision.get("revision"), int), "state revision probe returned no revision")

    if not args.skip_frontend_source:
        source = _read_text(f"{frontend_base}/src/AppV2.jsx")
        _require("campaignReady" in source and "data-react-stat" in source and "top-stats" in source, "served AppV2 source is stale or missing current loading/SVG HUD markers")
        _require("♥ ${player.hp" not in source, "served AppV2 source still contains the old emoji stat renderer")

    result = {
        "branch": branch,
        "head_sha": head_sha,
        "backend_port": args.backend_port,
        "frontend_port": args.frontend_port,
        "revision": revision["revision"],
        "canonical_path": authority["canonical_path"],
        "legacy_path": authority["legacy_path"],
        "isolated_state_required": bool(args.require_isolated_state),
    }
    print("K&M preflight: GREEN")
    print(f"Checkout:          {branch} @ {head_sha}")
    print(f"Backend:           127.0.0.1:{args.backend_port}")
    print(f"Frontend:          127.0.0.1:{args.frontend_port}")
    print(f"Campaign revision: {revision['revision']}")
    print(f"Canonical state:   {authority['canonical_path']}")
    print(f"Legacy evidence:   {authority['legacy_path']} (non-authoritative)")
    if args.require_isolated_state:
        print("Mutation gate:      isolated local state required and verified")
    return result


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 1 <= args.backend_port <= 65535 or not 1 <= args.frontend_port <= 65535:
        print("K&M preflight failed: ports must be between 1 and 65535", file=sys.stderr)
        return 1
    try:
        run_preflight(args)
    except PreflightError as exc:
        print(f"K&M preflight failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
