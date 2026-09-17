"""Bounded, read-only context projection for the local PYR bridge.

The bridge is deliberately separate from the state mutation service.  It gives
the tutor a current, validated view of the local campaign plus explicitly
captured editor/terminal context, but it never writes player state or exposes
the state files themselves.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_CONTEXT_TEXT_BYTES = 20_000
MAX_CONTEXT_FILE_BYTES = 40_000
MAX_CONTEXT_DIFF_BYTES = 24_000
MAX_CONTEXT_LINES = 80

_SENSITIVE_BASENAMES = {
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets.json",
    "service-account.json",
}
_SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".secret")

_ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")


class ContextValueError(ValueError):
    """Raised when a caller supplies an oversized or unsafe context value."""


def is_sensitive_path(value: object) -> bool:
    """Return whether a workspace path looks like a secret-bearing file."""

    if isinstance(value, Path):
        parts = value.parts
    elif isinstance(value, str):
        parts = tuple(part for part in re.split(r"[/\\]+", value) if part)
    else:
        return False
    for part in parts:
        name = str(part).casefold()
        if name.startswith(".env") or name in _SENSITIVE_BASENAMES or name.endswith(_SENSITIVE_SUFFIXES):
            return True
    return False


def bounded_text(value: object, field: str, *, max_bytes: int = MAX_CONTEXT_TEXT_BYTES) -> tuple[str, bool]:
    """Normalize user-visible context text and return ``(text, truncated)``.

    Terminal output may contain ANSI escape sequences and carriage returns.  We
    remove those before storing the ephemeral bridge context so an AI client
    receives plain text rather than control sequences.
    """

    if value is None:
        return "", False
    if not isinstance(value, str):
        raise ContextValueError(f"{field} must be text")
    clean = _ANSI_ESCAPE.sub("", value).replace("\x00", "")
    clean = "".join(character for character in clean if character in {"\n", "\r", "\t"} or ord(character) >= 32)
    clean = clean.replace("\r\n", "\n").replace("\r", "\n")
    encoded = clean.encode("utf-8")
    if len(encoded) <= max_bytes:
        return clean, False
    # Truncate on a UTF-8 boundary and make the truncation explicit to the
    # tutor.  A hard byte limit keeps a pasted terminal/context payload bounded.
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    return truncated, True


def bounded_file(path: Path) -> dict[str, Any]:
    """Read one already-authorized workspace file for context."""

    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            raw = handle.read(MAX_CONTEXT_FILE_BYTES)
            has_more = bool(handle.read(1))
    except FileNotFoundError as exc:
        raise ContextValueError("Active file was not found") from exc
    except OSError as exc:
        raise ContextValueError("Active file could not be read") from exc
    truncated = size > MAX_CONTEXT_FILE_BYTES or has_more
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        # A valid UTF-8 code point may straddle the bounded read boundary. If
        # the decoder failed near that boundary, discard only the incomplete
        # suffix; invalid bytes earlier in the file still fail closed.
        if not truncated or exc.start < max(0, len(raw) - 3):
            raise ContextValueError("Active file is not UTF-8 text") from exc
        try:
            content = raw[: exc.start].decode("utf-8")
        except UnicodeDecodeError as nested:
            raise ContextValueError("Active file is not UTF-8 text") from nested
    text, text_truncated = bounded_text(content, "active_file", max_bytes=MAX_CONTEXT_FILE_BYTES)
    return {"content": text, "bytes": size, "truncated": truncated or text_truncated}


def _run_git(workspace: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(workspace), *args],
            check=False,
            capture_output=True,
            text=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if isinstance(result.stdout, bytes):
        return result.stdout.decode("utf-8", errors="replace")
    return result.stdout or ""


def git_context(workspace: Path) -> dict[str, Any]:
    """Return safe, bounded git metadata without player-state diffs."""

    branch = _run_git(workspace, "branch", "--show-current").strip() or "detached"
    # State files are intentionally excluded.  They are managed by the state
    # gateway and may contain private progression/session evidence.
    diff = _run_git(
        workspace,
        "diff",
        "HEAD",
        "--no-ext-diff",
        "--unified=3",
        "--",
        ".",
        ":(exclude,glob)**/progress.json",
        ":(exclude,glob)**/.env*",
        ":(exclude,glob)**/*.pem",
        ":(exclude,glob)**/*.key",
    )
    diff, diff_truncated = bounded_text(diff, "git_diff", max_bytes=MAX_CONTEXT_DIFF_BYTES)
    return {
        "branch": branch,
        "diff": diff,
        "diff_truncated": diff_truncated,
    }


def quest_context(progress: Mapping[str, Any], encounter: Mapping[str, Any] | None) -> dict[str, Any]:
    """Project only the current quest and encounter, never future locked mobs."""

    projects = progress.get("projects")
    active = next(
        (item for item in projects if isinstance(item, Mapping) and item.get("status") == "active"),
        None,
    ) if isinstance(projects, list) else None
    if not isinstance(active, Mapping):
        return {"project": None, "mob": None}

    project_id = str(active.get("branch") or active.get("id") or "")
    project = {
        "id": project_id,
        "name": str(active.get("name") or project_id),
        "progress": active.get("progress", 0),
        "boss": str(active.get("boss") or ""),
    }
    mob: Mapping[str, Any] | None = None
    mobs = active.get("mobs")
    mob_name = encounter.get("mob_name") if isinstance(encounter, Mapping) else None
    if isinstance(mobs, list) and mob_name:
        mob = next((item for item in mobs if isinstance(item, Mapping) and item.get("name") == mob_name), None)

    current = None
    if isinstance(encounter, Mapping) and encounter.get("mob_name"):
        current = {
            "name": str(encounter.get("mob_name")),
            "index": encounter.get("mob_index"),
            "status": str(encounter.get("status") or "locked"),
            "resolve": encounter.get("resolve"),
            "max_resolve": encounter.get("max_resolve"),
            "attempts": encounter.get("attempts", 0),
            "question_types": [item for item in encounter.get("question_types", []) if isinstance(item, str)][
                :MAX_CONTEXT_LINES
            ],
            "available_objectives": [
                {
                    "id": item.get("id"),
                    "question_type": item.get("question_type"),
                    "impact": item.get("impact"),
                }
                for item in encounter.get("available_objectives", [])
                if isinstance(item, Mapping)
            ][:MAX_CONTEXT_LINES],
        }
        if isinstance(mob, Mapping):
            # This is canonical metadata for the current encounter only; no
            # future locked encounter prompt or answer is included.
            current["concept"] = str(mob.get("concept") or "")
            current["encounter"] = str(mob.get("encounter") or "")

    learning = progress.get("learning_state")
    learning = learning if isinstance(learning, Mapping) else {}
    assist = progress.get("assist")
    assist = assist if isinstance(assist, Mapping) else {}
    clean_clear = learning.get("clean_clear_eligible")
    if clean_clear is None:
        clean_clear = active.get("clean_clear_eligible", True)
    assistance = {
        "mode": str(assist.get("mode") or "clean"),
        "reference_mode": bool(learning.get("reference_mode", False)),
        "clean_clear_eligible": bool(clean_clear),
        "reference_mode_uses": assist.get("reference_mode_uses", 0),
        "guided_milestones": assist.get("guided_milestones", 0),
    }
    return {
        "project": project,
        "mob": current,
        "phase": str(learning.get("phase") or "teach"),
        "concept": str(learning.get("concept") or (current or {}).get("concept") or ""),
        "assistance": assistance,
    }


def build_context(
    *,
    progress: Mapping[str, Any],
    revision: int,
    encounter: Mapping[str, Any] | None,
    workspace: Path,
    active_path: str | None,
    active_file: dict[str, Any] | None,
    selection: str,
    selection_truncated: bool,
    terminal_tail: str,
    terminal_truncated: bool,
) -> dict[str, Any]:
    """Build the JSON-safe context envelope returned to local PYR clients."""

    return {
        "version": 1,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "revision": int(revision),
        "active_file": (
            {"path": active_path, **active_file} if active_path and active_file is not None else None
        ),
        "selection": {"text": selection, "truncated": selection_truncated},
        "terminal": {"tail": terminal_tail, "truncated": terminal_truncated},
        "git": git_context(workspace),
        "quest": quest_context(progress, encounter),
        "encounter": encounter,
    }
