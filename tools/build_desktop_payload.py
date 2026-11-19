"""Stage a portable Windows or Linux payload using a standalone Python runtime.

Windows dependencies can be resolved cross-platform for a later Windows build.
The output contains no save or workspace and is staging input, not an installer.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KEY_PATTERN = re.compile(rb"sb_(?:publishable|secret)_[A-Za-z0-9_-]{16,}")


def check_frontend(dist: Path) -> None:
    if not (dist / "index.html").is_file():
        raise ValueError("Build the frontend before staging the desktop payload")
    for path in dist.rglob("*"):
        if (
            path.is_file()
            and path.suffix in {".js", ".json", ".html", ".css", ".map"}
            and KEY_PATTERN.search(path.read_bytes())
        ):
            raise ValueError("The built frontend contains an embedded API key; rebuild without credentials")


def source_ignore(directory: str, names: list[str]) -> set[str]:
    # ``ide/server/online`` contains production routes and models for the
    # private online game. Exclude tests and Python caches by file name, but
    # never drop a production package just because it is named ``online``.
    return {name for name in names if name in {"__pycache__", "conftest.py", ".pytest_cache"} or name.startswith("test_") or name.endswith(".pyc")}


def stage(
    output: Path,
    runtime: Path,
    *,
    target_platform: str | None = None,
    install_dependencies: bool = True,
) -> None:
    dist = ROOT / "ide" / "frontend" / "dist"
    check_frontend(dist)
    runtime = runtime.resolve(strict=True)
    target_platform = target_platform or ("windows" if os.name == "nt" else "linux")
    if target_platform not in {"windows", "linux"}:
        raise ValueError("Desktop payloads support only Windows and Linux")
    executable = runtime / ("python.exe" if target_platform == "windows" else "bin/python3")
    if not executable.is_file():
        raise ValueError("The supplied directory is not a standalone Python runtime")
    if output.exists():
        raise FileExistsError("Output must be a new path; existing files are never replaced")
    output.mkdir(parents=True)
    app = output / "app"
    (app / "ide").mkdir(parents=True)
    for name in ("__init__.py", "quest.py", "state_cli.py", "workspace_transfer.py"):
        shutil.copy2(ROOT / "ide" / name, app / "ide" / name)
    shutil.copytree(ROOT / "ide" / "server", app / "ide" / "server", ignore=source_ignore)
    shutil.copytree(dist, output / "frontend")
    shutil.copytree(runtime, output / "python", symlinks=True)
    if target_platform == "linux":
        # Quest Lab has no Tk UI. Removing the optional Tk extension keeps
        # linuxdeploy from trying to resolve an unavailable Tcl runtime.
        for extension in (output / "python" / "lib").glob("python*/lib-dynload/_tkinter*.so"):
            extension.unlink()
    if install_dependencies:
        python = output / "python" / ("python.exe" if target_platform == "windows" else "bin/python3")
        command = ["uv", "pip", "install", "--target", str(output / "vendor")]
        if target_platform == "windows" and os.name != "nt":
            # Resolve Windows wheels and environment markers from Linux so the
            # payload can be transferred to the Windows packaging host.
            command.extend(["--python-platform", "x86_64-pc-windows-msvc", "--python-version", "3.11"])
        else:
            command.extend(["--python", str(python)])
        command.extend(["-r", str(ROOT / "ide" / "server" / "requirements.txt")])
        subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--platform", choices=("linux", "windows"), default=None)
    args = parser.parse_args()
    stage(args.output.absolute(), args.runtime, target_platform=args.platform)
    print(f"Desktop payload staged at {args.output.absolute()}")


if __name__ == "__main__":
    main()
