"""Guarded Supabase migration preflight for Quest Lab campaign sync.

The campaign-sync migrations are intentionally not applied by the normal
launcher.  This helper makes the approval boundary explicit: it verifies the
linked migration ledger, runs a dry-run, and only performs a real push when the
caller supplies the exact confirmation token.  It never reads or writes the
player save.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Sequence


EXPECTED_MIGRATIONS = (
    "20260916000100_player_state_device_ownership.sql",
    "20260917000100_player_state_campaign_projection.sql",
)
CONFIRMATION_TOKEN = "APPLY_QUESTLAB_CAMPAIGN_MIGRATIONS"
MIGRATION_ROW = re.compile(r"`(?P<local>\d{14})`\s*\|\s*`(?P<remote>[^`]*)`")


class MigrationGuardError(RuntimeError):
    """Raised when the remote ledger is not exactly the expected plan."""


def _npx_command() -> str:
    command = shutil.which("npx") or shutil.which("npx.cmd")
    if not command:
        raise MigrationGuardError("npx was not found; install Node.js before using the migration guard")
    return command


def _run(command: Sequence[str]) -> str:
    result = subprocess.run(
        list(command),
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode:
        raise MigrationGuardError(f"Supabase command failed ({result.returncode}):\n{output.strip()}")
    return output


def pending_migration_ids(output: str) -> set[str]:
    """Return local migration IDs whose remote ledger cell is blank."""

    pending: set[str] = set()
    for match in MIGRATION_ROW.finditer(output):
        if not match.group("remote").strip():
            pending.add(match.group("local"))
    return pending


def migration_id(filename: str) -> str:
    match = re.match(r"^(\d{14})_", filename)
    if not match:
        raise MigrationGuardError(f"Migration filename has no timestamp prefix: {filename}")
    return match.group(1)


def expected_ids() -> set[str]:
    return {migration_id(filename) for filename in EXPECTED_MIGRATIONS}


def verify_plan(ledger_output: str, dry_run_output: str) -> None:
    """Fail closed unless both the ledger and dry-run contain the exact plan."""

    actual = pending_migration_ids(ledger_output)
    expected = expected_ids()
    if actual != expected:
        raise MigrationGuardError(
            "Refusing migration: linked Supabase has an unexpected pending plan. "
            f"Expected {sorted(expected)}, found {sorted(actual)}."
        )
    missing = [identifier for identifier in expected if identifier not in dry_run_output]
    if missing:
        raise MigrationGuardError(
            "Refusing migration: dry-run did not propose every expected migration: "
            + ", ".join(sorted(missing))
        )


def command(argv: Sequence[str]) -> list[str]:
    return [_npx_command(), "--yes", "supabase", *argv]


def run_guard(*, apply: bool = False, confirmation: str = "") -> tuple[str, str, str | None]:
    ledger = _run(command(["migration", "list", "--linked"]))
    dry_run = _run(command(["db", "push", "--linked", "--dry-run", "--skip-vault"]))
    verify_plan(ledger, dry_run)
    applied = None
    if apply:
        if confirmation != CONFIRMATION_TOKEN:
            raise MigrationGuardError(
                "A real hosted write requires --confirm " + CONFIRMATION_TOKEN
            )
        applied = _run(command(["db", "push", "--linked", "--skip-vault"]))
    return ledger, dry_run, applied


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify Quest Lab campaign migrations; apply only with explicit confirmation."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="perform the real linked migration after the dry-run passes",
    )
    parser.add_argument(
        "--confirm",
        default="",
        metavar="TOKEN",
        help=f"required with --apply: {CONFIRMATION_TOKEN}",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ledger, dry_run, applied = run_guard(apply=args.apply, confirmation=args.confirm)
    except MigrationGuardError as error:
        print(f"MIGRATION GUARD: BLOCKED\n{error}", file=sys.stderr)
        return 2
    print("MIGRATION GUARD: GREEN")
    print("Expected pending migrations:", ", ".join(EXPECTED_MIGRATIONS))
    print("Dry-run verified; no hosted write was performed." if applied is None else "Hosted migration applied.")
    if args.apply and applied:
        print(applied.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
