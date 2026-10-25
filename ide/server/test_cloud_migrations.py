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
AVATAR_MIGRATION = ROOT / "supabase" / "migrations" / "20260915000400_avatar_storage.sql"
AVATAR_RLS_TEST = ROOT / "supabase" / "tests" / "avatar_storage_rls.sql"
IDENTITY_MIGRATION = ROOT / "supabase" / "migrations" / "20260914000100_profiles_devices.sql"
IDENTITY_RLS_TEST = ROOT / "supabase" / "tests" / "profiles_devices_rls.sql"
BOUNDS_MIGRATION = ROOT / "supabase" / "migrations" / "20260915000300_player_state_value_bounds.sql"
CAMPAIGN_MIGRATION = ROOT / "supabase" / "migrations" / "20260917000100_player_state_campaign_projection.sql"
DUNGEON_GRID_MIGRATION = ROOT / "supabase" / "migrations" / "20261025000100_dungeon_grid_and_boss_phases.sql"


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

    def test_avatar_storage_is_private_and_account_scoped(self):
        sql = AVATAR_MIGRATION.read_text(encoding="utf-8")

        self.assertIn("public = false", sql)
        self.assertIn("  1048576,", sql)
        self.assertIn("array['image/webp']::text[]", sql)
        self.assertIn("profiles_avatar_path_safe", sql)
        self.assertIn("avatar_path = (id::text || '/avatar.webp')", sql)
        for policy in (
            "avatars_objects_select_own",
            "avatars_objects_insert_own",
            "avatars_objects_update_own",
            "avatars_objects_delete_own",
        ):
            self.assertIn(policy, sql)
        self.assertEqual(sql.count("((select auth.uid())::text || '/avatar.webp')"), 5)

    def test_avatar_rls_fixture_exercises_private_cross_account_paths(self):
        sql = AVATAR_RLS_TEST.read_text(encoding="utf-8")

        self.assertIn("avatar-a@example.test", sql)
        self.assertIn("avatar-b@example.test", sql)
        self.assertIn("Avatar RLS failure: User A inserted User B portrait", sql)
        self.assertIn("Avatar RLS failure: User B can read User A portrait", sql)
        self.assertIn("00000000-0000-0000-0000-000000000201/avatar.webp", sql)
        self.assertIn("00000000-0000-0000-0000-000000000202/avatar.webp", sql)

    def test_identity_migration_and_fixture_keep_account_rows_private(self):
        migration = IDENTITY_MIGRATION.read_text(encoding="utf-8")
        fixture = IDENTITY_RLS_TEST.read_text(encoding="utf-8")

        self.assertIn("alter table public.profiles enable row level security", migration)
        self.assertIn("alter table public.devices enable row level security", migration)
        self.assertIn("revoke all on public.profiles from anon", migration)
        self.assertIn("revoke all on public.devices from anon", migration)
        self.assertIn("using ((select auth.uid()) = id)", migration)
        self.assertIn("using ((select auth.uid()) = user_id)", migration)
        self.assertIn("RLS failure: User B can see another users private rows", fixture)
        self.assertIn("RLS failure: User A inserted User B profile", fixture)
        self.assertIn("RLS failure: User A inserted User B device", fixture)

    def test_player_state_bounds_migration_keeps_projection_limits_explicit(self):
        sql = BOUNDS_MIGRATION.read_text(encoding="utf-8")

        for phrase in (
            "player.xp must be below player.xp_next",
            "player.hp must not exceed player.max_hp",
            "player counters are outside their bounds",
            "owned_cosmetics entries must be safe identifiers",
            "equipped values must be safe identifiers",
            "revoke all on function public.validate_player_state_projection(jsonb) from public;",
        ):
            self.assertIn(phrase, sql)

    def test_campaign_projection_migration_keeps_revision_row_allowlisted_and_answer_free(self):
        sql = CAMPAIGN_MIGRATION.read_text(encoding="utf-8")
        for phrase in (
            "'campaign'",
            "validate_campaign_projection",
            "validate_player_state_projection_base",
            "player_state_state_domains",
            "campaign projection is too large",
            "campaign projection contains unsupported domains",
            "project mobs must be a bounded array",
            "codex encounter contains unsupported fields",
            "player_notes",
            "codex player notes must be bounded",
            "dungeon question contains unsupported or hidden fields",
            "dungeon inventory must be a bounded array",
            "dungeon inventory contains unsupported fields",
            "perform public.validate_player_state_projection_base(base_state)",
            "revoke all on function public.validate_player_state_projection(jsonb) from public;",
        ):
            self.assertIn(phrase, sql)

    def test_dungeon_grid_migration_accepts_every_field_the_app_syncs(self):
        import re

        from ide.server.state import LocalStateService

        sql = DUNGEON_GRID_MIGRATION.read_text(encoding="utf-8")

        def allow_list(prefix: str, anchor: str) -> set[str]:
            lists = [set(re.findall(r"'([a-z_]+)'", body)) for body in re.findall(re.escape(prefix) + r" - array\[([^\]]*)\]", sql)]
            found = [names for names in lists if anchor in names]
            self.assertTrue(found, prefix)
            return found[0]

        run = {
            "status": "active", "run_id": "dungeon-1", "seed": "s", "class_id": "syntax-warden", "concept_id": "loops",
            "floor": 1, "room": 2, "room_type": "selector", "score": 5, "run_coins": 3, "started_at": "2026-10-25T00:00:00+00:00",
            "updated_at": "2026-10-25T00:00:00+00:00", "ended_at": None, "question_number": 1, "editor_content": "", "attempts": 0,
            "risk_profile": {"kind": "buff", "room_type": "shrine", "title": "Ember", "preview": "Hits harder."}, "risk_status": "entered",
            "loadout": {"hp": 10}, "inventory": [], "question": None, "room_choices": [],
            "map": {"floor": 1, "current_node_id": "a", "visited_node_ids": ["a"], "nodes": [{"id": "a", "type": "rest", "row": 1, "column": 1, "label": "Camp", "note": ""}], "edges": {"a": ["b"]}},
            "last_result": {"outcome": "risk_entered"}, "history": [],
        }
        synced = LocalStateService._campaign_source_projection({"dungeon_run": run})["dungeon_run"]
        self.assertLessEqual(set(synced), allow_list("item", "run_id"))
        self.assertLessEqual(set(synced["map"]), allow_list("(item -> 'map')", "nodes"))
        self.assertLessEqual(set(synced["map"]["nodes"][0]), allow_list("mob_item", "column"))
        self.assertLessEqual(set(synced["risk_profile"]), allow_list("(item -> 'risk_profile')", "preview"))
        for phrase in ("create or replace function public.validate_campaign_projection", "dungeon map nodes must be bounded", "revoke all on function public.validate_campaign_projection(jsonb) from public;"):
            self.assertIn(phrase, sql)

    def test_dungeon_grid_migration_allows_every_boss_phase(self):
        import re

        from ide.server.state import BOSS_REQUIREMENTS

        sql = DUNGEON_GRID_MIGRATION.read_text(encoding="utf-8")
        phases = re.search(r"field_name not in \(([^)]*)\)", sql)
        self.assertIsNotNone(phases)
        self.assertEqual(set(re.findall(r"'([a-z_]+)'", phases.group(1))), set(BOSS_REQUIREMENTS))
        self.assertIn(f"-> 'verified') > {len(BOSS_REQUIREMENTS)} then", sql)


if __name__ == "__main__":
    unittest.main()
