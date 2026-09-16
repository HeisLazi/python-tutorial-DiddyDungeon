"""Static contracts for the unapplied hosted sync migration.

These checks intentionally do not connect to Supabase.  They keep the
committed migration and its executable SQL fixture aligned until the hosted
Milestone C approval gate permits applying and running them against Postgres.
"""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "supabase" / "migrations" / "20260916000100_player_state_device_ownership.sql"
RLS_TEST = ROOT / "supabase" / "tests" / "player_state_rls.sql"


class CloudMigrationContractTests(unittest.TestCase):
    def test_player_state_rpc_binds_provenance_to_authenticated_device(self):
        sql = MIGRATION.read_text(encoding="utf-8")

        ownership_check = "from public.devices\n    where id = source_device_id\n      and user_id = auth.uid()"
        self.assertIn(ownership_check, sql)
        self.assertIn("source_device_id does not belong to the authenticated account", sql)
        self.assertIn("using errcode = '42501'", sql)
        self.assertIn("perform public.validate_player_state_projection(next_state)", sql)
        self.assertIn("revoke all on function public.save_player_state(bigint, jsonb, uuid) from public;", sql)
        self.assertIn("grant execute on function public.save_player_state(bigint, jsonb, uuid) to authenticated;", sql)

        # Provenance must be checked before validation and before the row lock.
        self.assertLess(sql.index(ownership_check), sql.index("perform public.validate_player_state_projection"))
        self.assertLess(sql.index(ownership_check), sql.index("select * into current_row"))

    def test_rls_fixture_exercises_foreign_and_owned_device_paths(self):
        sql = RLS_TEST.read_text(encoding="utf-8")

        self.assertIn("State A device", sql)
        self.assertIn("State B device", sql)
        self.assertIn("Provenance failure: User A used User B device", sql)
        self.assertIn("00000000-0000-0000-0000-000000000112", sql)
        self.assertIn("00000000-0000-0000-0000-000000000111", sql)
        self.assertIn("select revision into saved_revision", sql)


if __name__ == "__main__":
    unittest.main()
