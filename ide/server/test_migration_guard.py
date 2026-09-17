from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest import TestCase, mock


MODULE_PATH = Path(__file__).resolve().parents[2] / "tools" / "questlab_supabase_migrate.py"
SPEC = importlib.util.spec_from_file_location("questlab_supabase_migrate", MODULE_PATH)
assert SPEC and SPEC.loader
migration_guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration_guard)


LEDGER = """
   Local            | Remote           | Time (UTC)
  ------------------|------------------|-----------------------
   `20260915000400` | `20260915000400` | `2026-09-15 00:04:00`
   `20260916000100` | ` `              | `2026-09-16 00:01:00`
   `20260917000100` | ` `              | `2026-09-17 00:01:00`
"""
DRY_RUN = "Would apply 20260916000100 and 20260917000100"


class MigrationGuardTests(TestCase):
    def test_pending_parser_extracts_only_blank_remote_cells(self):
        self.assertEqual(
            migration_guard.pending_migration_ids(LEDGER),
            {"20260916000100", "20260917000100"},
        )

    def test_plan_rejects_unexpected_pending_migration(self):
        with self.assertRaises(migration_guard.MigrationGuardError):
            migration_guard.verify_plan(
                LEDGER.replace("20260917000100", "20260918000100"),
                DRY_RUN,
            )

    def test_plan_requires_every_expected_dry_run_entry(self):
        with self.assertRaises(migration_guard.MigrationGuardError):
            migration_guard.verify_plan(LEDGER, "Would apply 20260916000100")

    @mock.patch.object(migration_guard, "_run")
    def test_default_guard_is_read_only(self, run):
        run.side_effect = [LEDGER, DRY_RUN]
        ledger, dry_run, applied = migration_guard.run_guard()
        self.assertEqual(ledger, LEDGER)
        self.assertEqual(dry_run, DRY_RUN)
        self.assertIsNone(applied)
        self.assertEqual(run.call_count, 2)
        self.assertIn("--dry-run", run.call_args_list[1].args[0])

    @mock.patch.object(migration_guard, "_run")
    def test_apply_requires_exact_confirmation_token(self, run):
        run.side_effect = [LEDGER, DRY_RUN]
        with self.assertRaises(migration_guard.MigrationGuardError):
            migration_guard.run_guard(apply=True, confirmation="yes")
        self.assertEqual(run.call_count, 2)

