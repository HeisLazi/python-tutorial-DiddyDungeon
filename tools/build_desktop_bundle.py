"""Build a Tauri installer from an already staged desktop payload."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TAURI = ROOT / "ide" / "tauri-app" / "src-tauri"
WORKTREE_TARGET = ROOT / ".build" / "tauri-target"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--bundle", choices=("deb", "appimage", "nsis"), required=True)
    parser.add_argument("--target", default=None)
    parser.add_argument("--runner", default=None)
    args = parser.parse_args()
    if os.name == "nt" and args.bundle != "nsis":
        parser.error("Build Linux installers on Linux")
    if args.bundle == "nsis" and os.name != "nt":
        # Tauri supports NSIS cross-builds from Linux via cargo-xwin. Keep the
        # supported target explicit so this path remains reproducible.
        if args.target not in (None, "x86_64-pc-windows-msvc"):
            parser.error("Linux cross-builds currently support x86_64-pc-windows-msvc only")
        args.target = "x86_64-pc-windows-msvc"
        args.runner = args.runner or "cargo-xwin"
        bundled_runner = ROOT / ".build" / "cargo-xwin" / "bin" / args.runner
        if bundled_runner.is_file():
            args.runner = str(bundled_runner)
        if not shutil.which(args.runner):
            parser.error("Install cargo-xwin to build the Windows NSIS installer from Linux")
    elif args.target and args.bundle != "nsis":
        parser.error("--target is supported only for Windows NSIS bundles")
    payload = args.payload.resolve(strict=True)
    for name in ("app", "frontend", "python", "vendor"):
        if not (payload / name).is_dir():
            parser.error(f"Payload is missing {name}")
    # This checkout's src-tauri/target can be a symlink to the main repository.
    # Always keep compiler output inside the authorized worktree.
    WORKTREE_TARGET.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["CARGO_TARGET_DIR"] = str(WORKTREE_TARGET.resolve())
    if args.bundle == "nsis" and os.name != "nt":
        env.setdefault("XWIN_CACHE_DIR", str((ROOT / ".build" / "xwin-cache").resolve()))
        nsis_wrapper = ROOT / ".build" / "nsis-bin"
        cargo_xwin_bin = ROOT / ".build" / "cargo-xwin" / "bin"
        env["PATH"] = os.pathsep.join((str(nsis_wrapper), str(cargo_xwin_bin), env.get("PATH", "")))
    # The AppImage bundler reuses its Debian staging directory. Clear it so a
    # prior payload cannot leak stale files into a later package.
    stale_appimage_stage = WORKTREE_TARGET / "release" / "bundle" / "appimage_deb"
    if args.bundle == "appimage" and stale_appimage_stage.exists():
        shutil.rmtree(stale_appimage_stage)
    # A resource mapping fixes the target path independent of where staging ran.
    config = {"bundle": {"resources": {str(payload) + os.sep: "questlab/"}}}
    env.setdefault("CARGO_BUILD_JOBS", "1")
    tauri = shutil.which("tauri")
    cargo = shutil.which("cargo")
    if tauri:
        command = [tauri, "build"]
    elif cargo:
        command = [cargo, "tauri", "build"]
    else:
        parser.error("Install the Tauri CLI (tauri or cargo tauri) before building")
    command.extend(["--bundles", args.bundle, "--config", json.dumps(config)])
    if args.runner:
        command.extend(["--runner", args.runner])
    if args.target:
        command.extend(["--target", args.target])
    subprocess.run(command, cwd=TAURI, env=env, check=True)


if __name__ == "__main__":
    main()
