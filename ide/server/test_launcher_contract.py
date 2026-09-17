from __future__ import annotations

import json
import importlib.util
import tempfile
import threading
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from ide import quest
from ide.server import app_v2
from ide.server.state import LocalStateService

ROOT = Path(__file__).resolve().parents[2]


class LauncherContractTests(unittest.TestCase):
    def _native_preflight_module(self):
        path = ROOT / "tools" / "questlab-km-preflight.py"
        spec = importlib.util.spec_from_file_location("questlab_native_preflight", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _local_sync_sim_module(self):
        path = ROOT / "tools" / "questlab-local-sync-sim.py"
        spec = importlib.util.spec_from_file_location("questlab_local_sync_sim", path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_native_linux_preflight_is_read_only_and_checks_isolated_authority(self):
        preflight = (ROOT / "tools" / "questlab-km-preflight.py").read_text(encoding="utf-8")
        self.assertIn("CachyOS", (ROOT / "FRIEND_ONBOARDING.md").read_text(encoding="utf-8"))
        self.assertIn("urlopen", preflight)
        self.assertIn('method="GET"', preflight)
        self.assertNotIn('method="POST"', preflight)
        self.assertIn("--require-isolated-state", preflight)
        self.assertIn("canonical_authoritative", preflight)
        self.assertIn("legacy_authoritative", preflight)

        module = self._native_preflight_module()
        self.assertEqual(module.normalize_path(r"C:\Quest Lab\progress.json"), "c:/quest lab/progress.json")
        self.assertEqual(module.normalize_path("/tmp/state/progress.json"), "/tmp/state/progress.json")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            authority = {
                "canonical_path": str(root / "device" / "progress.json"),
                "legacy_path": str(root / "workspace" / "progress.json"),
                "canonical_authoritative": True,
                "legacy_authoritative": False,
            }
            runtime = {
                "repo_git": {"branch": "feature/cloud-sync-desktop", "head_sha": "abc123"},
                "state_authority": authority,
            }
            args = SimpleNamespace(
                repo_root=str(root),
                backend_port=7395,
                frontend_port=5215,
                allow_stale_checkout=True,
                skip_frontend_source=False,
                require_isolated_state=True,
            )
            with patch.object(module, "_git", side_effect=["feature/cloud-sync-desktop", "abc123", ""]), patch.object(
                module, "_read_json", side_effect=[runtime, runtime, {"revision": 5}]
            ), patch.object(
                module,
                "_read_text",
                return_value="campaignReady data-react-stat top-stats FRONTEND_BUILD_SHA data-frontend-build-sha",
            ):
                result = module.run_preflight(args)
            self.assertEqual(result["revision"], 5)
            self.assertTrue(result["isolated_state_required"])

            protected = dict(authority)
            protected["canonical_path"] = str(root / "progress.json")
            protected_runtime = {**runtime, "state_authority": protected}
            with patch.object(module, "_git", side_effect=["feature/cloud-sync-desktop", "abc123", ""]), patch.object(
                module, "_read_json", side_effect=[protected_runtime, protected_runtime, {"revision": 5}]
            ):
                with self.assertRaisesRegex(module.PreflightError, "isolated local state"):
                    module.run_preflight(args)

    def test_local_sync_simulator_uses_real_state_service_and_never_writes_source(self):
        simulator = self._local_sync_sim_module()
        source = ROOT / "progress.json"
        before = source.read_bytes()

        result = simulator.run_simulation(source)

        self.assertTrue(result["ok"])
        self.assertEqual(result["source_digest_before"], result["source_digest_after"])
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(result["mailbox_conflict"]["status_code"], 409)
        self.assertEqual(result["conflict"]["status_code"], 409)
        self.assertEqual(result["resolution"], "keep-device")
        self.assertEqual(result["sync_event_action"], "sync_apply_cloud")
        self.assertGreaterEqual(result["final_campaign"]["project_count"], 1)
        self.assertEqual(result["final_campaign"]["cleared_mob_count"], result["initial_campaign"]["cleared_mob_count"])
        self.assertEqual(result["final_campaign"]["codex_encounter_count"], result["initial_campaign"]["codex_encounter_count"])
        self.assertEqual(result["final_campaign"]["dungeon_run_id"], result["initial_campaign"]["dungeon_run_id"])
        initial_player = result["initial_player"]
        final_player = result["final_player"]
        # The explicit keep-device choice retains B's first push (+2) and
        # offline reward (+5); A's intervening +3 is intentionally discarded.
        self.assertEqual(final_player["coins"], initial_player["coins"] + 7)
        self.assertEqual(final_player["lifetime_xp"], initial_player["lifetime_xp"] + 5)

    def test_windows_launcher_requires_the_intended_checkout_and_stable_pty_mode(self):
        launcher = (ROOT / "tools" / "questlab-launch.ps1").read_text(encoding="utf-8")
        python_launcher = (ROOT / "ide" / "quest.py").read_text(encoding="utf-8")
        self.assertIn("$expectedBranch = 'feature/cloud-sync-desktop'", launcher)
        self.assertIn("ide/quest.py", launcher)
        self.assertIn("Canonical state:", launcher)
        self.assertIn("MigrateLocalState", launcher)
        self.assertIn("--use-local-state", launcher)
        self.assertIn("--backend-port $BackendPort", launcher)
        self.assertIn("--frontend-port $FrontendPort", launcher)
        self.assertIn("$command = \"cd $(Quote-BashLiteral $repoWsl) && exec", launcher)
        self.assertIn("env PYTHONPATH=. .venv/bin/python -m ide.quest", launcher)
        self.assertNotIn("exec .venv/bin/python ide/quest.py", launcher)
        self.assertNotIn("$command -join", launcher)
        self.assertNotIn("--reload-backend", launcher)
        self.assertIn("-AllowOtherBranch", launcher)
        self.assertIn("-AllowStaleCheckout", launcher)
        self.assertIn("git -C $repoRoot fetch --quiet origin", launcher)
        self.assertIn("for-each-ref --format='%(upstream:short)'", launcher)
        self.assertIn("rev-parse --verify --quiet", launcher)
        self.assertNotIn("rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null", launcher)
        self.assertIn("Canonical progress.json has local player-state changes", launcher)
        self.assertIn("exit_code = 0", python_launcher)
        self.assertIn("raise SystemExit(main())", python_launcher)
        self.assertIn("--confirm-local-state", python_launcher)
        self.assertIn("prepare_local_state", python_launcher)
        self.assertIn("checkout_head_sha", python_launcher)
        self.assertIn('env["QUESTLAB_BUILD_SHA"]', python_launcher)

    def test_native_linux_launcher_requires_intended_checkout_and_stable_pty_mode(self):
        launcher = (ROOT / "tools" / "questlab-launch.sh").read_text(encoding="utf-8")
        self.assertIn("expected_branch='feature/cloud-sync-desktop'", launcher)
        self.assertIn("git -C \"$repo_root\" fetch --quiet origin", launcher)
        self.assertIn("for-each-ref --format='%(upstream:short)'", launcher)
        self.assertIn("rev-parse --verify --quiet", launcher)
        self.assertIn("--allow-other-branch", launcher)
        self.assertIn("--allow-stale-checkout", launcher)
        self.assertIn("--migrate-local-state", launcher)
        self.assertIn("PYTHONPATH=. \"${launcher[@]}\"", launcher)
        self.assertIn('"$repo_root/.venv/bin/python" -m ide.quest', launcher)
        self.assertNotIn("--reload-backend", launcher)
        self.assertIn("progress.json has local player-state changes", launcher)

    def test_native_linux_report_is_read_only_and_captures_toolchain_identity(self):
        report = (ROOT / "tools" / "questlab-native-report.py").read_text(encoding="utf-8")
        onboarding = (ROOT / "FRIEND_ONBOARDING.md").read_text(encoding="utf-8")
        self.assertIn("Read-only native Linux/CachyOS environment report", report)
        self.assertIn("EXPECTED_BRANCH = \"feature/cloud-sync-desktop\"", report)
        self.assertIn("native_rollup_packages", report)
        self.assertIn("--strict", report)
        self.assertNotIn("write_text", report)
        self.assertNotIn("os.remove", report)
        self.assertIn("questlab-native-report.py", onboarding)
        self.assertIn("--strict", onboarding)

    def test_km_preflight_is_read_only_and_rejects_stale_frontend_source(self):
        preflight = (ROOT / "tools" / "questlab-km-preflight.ps1").read_text(encoding="utf-8")
        self.assertIn("$expectedBranch = 'feature/cloud-sync-desktop'", preflight)
        self.assertIn("/api/runtime", preflight)
        self.assertIn("$frontendRuntime = Get-Json", preflight)
        self.assertIn("frontend /api proxy HEAD", preflight)
        self.assertIn("frontend /api proxy state paths", preflight)
        self.assertIn("/api/state/revision", preflight)
        self.assertIn("/src/AppV2.jsx", preflight)
        self.assertIn("campaignReady", preflight)
        self.assertIn("data-react-stat", preflight)
        self.assertIn("FRONTEND_BUILD_SHA", preflight)
        self.assertIn("data-frontend-build-sha", preflight)
        self.assertIn("canonical_authoritative", preflight)
        self.assertIn("legacy_authoritative", preflight)
        self.assertIn("SkipFrontendSource", preflight)
        self.assertIn("RequireIsolatedState", preflight)
        self.assertIn("mutating K&M requires an isolated local state cache", preflight)
        self.assertIn("repo_root for the isolated state-custody check", preflight)
        self.assertIn(".TrimEnd('/', '\\')", preflight)
        self.assertIn(".Replace('\\', '/')", preflight)
        self.assertNotIn(".TrimEnd('/', '\\\\')", preflight)
        self.assertNotIn(".Replace('\\\\', '/')", preflight)
        self.assertNotIn("-Method Post", preflight)
        self.assertNotIn("git -C $repoRoot fetch", preflight)
        self.assertNotIn("Remove-Item", preflight)

    def test_hud_icon_contract_scopes_stat_pills_to_direct_children(self):
        styles = (ROOT / "ide" / "frontend" / "src" / "styles.css").read_text(encoding="utf-8")
        polish = (ROOT / "ide" / "frontend" / "src" / "uiPolish.js").read_text(encoding="utf-8")

        self.assertIn(".top-stats > span,.git-pill", styles)
        self.assertIn('.app-shell[data-hud="hud-adventurer"] .top-stats > span', styles)
        self.assertNotIn(".top-stats span,", styles)
        self.assertNotIn('.app-shell[data-hud="hud-adventurer"] .top-stats span', styles)
        self.assertIn(".top-stats > span .quest-icon", styles)
        self.assertIn(".top-stats > span [data-stat-value]", styles)
        self.assertIn("border:0;padding:0;border-radius:0;background:transparent", styles)
        self.assertIn("querySelectorAll('.top-stats > span')", polish)

    def test_launcher_rejects_confirmation_without_local_state_opt_in(self):
        with patch.object(
            quest,
            "parse_args",
            return_value=SimpleNamespace(confirm_local_state=True, use_local_state=False),
        ):
            with self.assertRaisesRegex(SystemExit, "requires --use-local-state"):
                quest.main()

    def test_friend_onboarding_names_the_single_authority_and_read_only_health_commands(self):
        onboarding = (ROOT / "FRIEND_ONBOARDING.md").read_text(encoding="utf-8")
        self.assertIn("questlab-state runtime", onboarding)
        self.assertIn("A workspace", onboarding)
        self.assertIn("legacy evidence", onboarding)
        self.assertIn("Do not copy", onboarding)
        self.assertIn("two-device sync acceptance", onboarding)
        self.assertIn("native Linux Rollup", onboarding)
        self.assertIn("npm ci", onboarding)
        self.assertIn("Linux filesystem", onboarding)
        self.assertIn("Never run\n`npm install` or `npm ci`", onboarding)
        self.assertIn("tools/questlab-km-preflight.py", onboarding)
        self.assertIn("--require-isolated-state", onboarding)
        self.assertIn("separate workspace", onboarding)
        self.assertIn("custody boundary, not a mode removal", onboarding)
        self.assertIn("workspace-scoped `/api/tutor`", onboarding)

    def test_friend_bundle_archives_committed_source_without_personal_worktree_files(self):
        packager = (ROOT / "tools" / "questlab-package.ps1").read_text(encoding="utf-8")
        self.assertIn("$expectedBranch = 'feature/cloud-sync-desktop'", packager)
        self.assertIn("git archive", packager)
        self.assertIn("uncommitted progress.json", packager)
        self.assertIn("untracked tutor.py", packager)
        self.assertIn("untracked tutor.py/dungeon.py", packager)
        self.assertIn("notes(?:/|\\\\)", packager)
        self.assertIn("Compress-Archive", packager)
        self.assertIn("FRIEND_ONBOARDING.md", packager)
        self.assertIn("npm ci", packager)
        self.assertNotIn("Copy-Item -LiteralPath (Join-Path $repoRoot 'progress.json')", packager)

    def test_packager_requires_exact_path_for_protected_untracked_data(self):
        packager = (ROOT / "tools" / "questlab-package.ps1").read_text(encoding="utf-8")
        onboarding = (ROOT / "FRIEND_ONBOARDING.md").read_text(encoding="utf-8")
        self.assertIn("[string[]]$IgnoreUntrackedPath", packager)
        self.assertIn("must stay inside the repository", packager)
        self.assertIn("must be untracked", packager)
        self.assertIn("$ignoredUntracked.Keys", packager)
        self.assertIn("-IgnoreUntrackedPath", onboarding)
        self.assertIn("blanket ignore of dirty source is not available", onboarding)

    def test_public_activity_workflow_has_a_narrow_write_boundary(self):
        workflow = (ROOT / ".github" / "workflows" / "sync-activity.yml").read_text(encoding="utf-8")
        activity = (ROOT / "tools" / "sync_activity.py").read_text(encoding="utf-8")
        self.assertIn("permissions:\n  contents: write", workflow)
        self.assertIn("if: github.actor != 'github-actions[bot]'", workflow)
        self.assertIn("paths-ignore:", workflow)
        self.assertIn("git add activity.json README.md", workflow)
        self.assertNotIn("issues: write", workflow)
        self.assertNotIn("pull-requests: write", workflow)
        self.assertNotIn("progress.json", workflow)
        self.assertIn("GITHUB_TOKEN", activity)
        self.assertIn("ACTIVITY_PATH.write_text", activity)
        self.assertIn("README_PATH.write_text", activity)

    @patch("ide.quest.running_under_wsl", return_value=True)
    def test_wsl_launcher_detects_missing_native_rollup_optional_dependency(self, _running):
        import tempfile

        with self.subTest("missing package"), tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            self.assertFalse(quest.linux_rollup_optional_dependency_ready(frontend))

        with self.subTest("clean package"), tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            package = frontend / "node_modules" / "@rollup" / "rollup-linux-x64-gnu"
            package.mkdir(parents=True)
            (package / "package.json").write_text("{}", encoding="utf-8")
            self.assertTrue(quest.linux_rollup_optional_dependency_ready(frontend))

    @patch("ide.quest.running_under_wsl", return_value=True)
    def test_launcher_rejects_partial_one_drive_dependency_tree(self, _running):
        import tempfile

        with tempfile.TemporaryDirectory() as directory:
            frontend = Path(directory)
            node_modules = frontend / "node_modules"
            for package in (
                node_modules / "vite",
                node_modules / "@supabase" / "supabase-js",
                node_modules / "@supabase" / "functions-js",
                node_modules / "@rollup" / "rollup-linux-x64-gnu",
            ):
                package.mkdir(parents=True)
                (package / "package.json").write_text("{}", encoding="utf-8")
            self.assertTrue(quest.frontend_dependencies_ready(frontend))
            (node_modules / "@supabase" / "functions-js" / "package.json").unlink()
            self.assertFalse(quest.frontend_dependencies_ready(frontend))

    def test_launcher_custody_opt_in_requires_confirmation_without_copying_by_default(self):
        original_quest_root = quest.REPO_ROOT
        original_app_root = app_v2.REPO_ROOT
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            workspace = Path(directory) / "quest"
            local_root = Path(directory) / "local"
            root.mkdir()
            workspace.mkdir()
            canonical = root / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 2}, "player": {"coins": 55}}), encoding="utf-8")
            quest.REPO_ROOT = root
            app_v2.REPO_ROOT = root
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            try:
                with patch.dict("os.environ", {"QUESTLAB_LOCAL_STATE_ROOT": str(local_root)}), patch(
                    "ide.quest.sys.stdin.isatty", return_value=False
                ):
                    with self.assertRaises(SystemExit) as raised:
                        quest.prepare_local_state(workspace, use_local_state=True, confirm_local_state=False)
                self.assertIn("not confirmed", str(raised.exception))
                self.assertFalse(local_root.exists())
            finally:
                quest.REPO_ROOT = original_quest_root
                app_v2.REPO_ROOT = original_app_root
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

    def test_launcher_custody_opt_in_switches_only_after_confirmed_copy(self):
        original_quest_root = quest.REPO_ROOT
        original_app_root = app_v2.REPO_ROOT
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            workspace = Path(directory) / "quest"
            local_root = Path(directory) / "local"
            root.mkdir()
            workspace.mkdir()
            canonical = root / "progress.json"
            source = {"meta": {"revision": 2}, "player": {"coins": 55}}
            canonical.write_text(json.dumps(source), encoding="utf-8")
            quest.REPO_ROOT = root
            app_v2.REPO_ROOT = root
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            try:
                with patch.dict("os.environ", {"QUESTLAB_LOCAL_STATE_ROOT": str(local_root)}):
                    destination = quest.prepare_local_state(
                        workspace,
                        use_local_state=True,
                        confirm_local_state=True,
                    )
                self.assertTrue(destination.is_file())
                self.assertEqual(destination.read_bytes(), canonical.read_bytes())
                self.assertEqual(json.loads(canonical.read_text(encoding="utf-8")), source)
            finally:
                quest.REPO_ROOT = original_quest_root
                app_v2.REPO_ROOT = original_app_root
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

    def test_launcher_resumes_verified_local_custody_after_local_progress(self):
        original_quest_root = quest.REPO_ROOT
        original_app_root = app_v2.REPO_ROOT
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "platform"
            workspace = Path(directory) / "quest"
            local_root = Path(directory) / "local"
            root.mkdir()
            workspace.mkdir()
            canonical = root / "progress.json"
            canonical.write_text(json.dumps({"meta": {"revision": 2}, "player": {"coins": 55}}), encoding="utf-8")
            quest.REPO_ROOT = root
            app_v2.REPO_ROOT = root
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            try:
                with patch.dict("os.environ", {"QUESTLAB_LOCAL_STATE_ROOT": str(local_root)}):
                    destination = quest.prepare_local_state(
                        workspace,
                        use_local_state=True,
                        confirm_local_state=True,
                    )
                    local_service = LocalStateService(destination, threading.RLock())
                    advanced = json.loads(destination.read_text(encoding="utf-8"))
                    advanced["player"]["coins"] = 56
                    local_service.persist(advanced)

                    resumed = quest.prepare_local_state(
                        workspace,
                        use_local_state=True,
                        confirm_local_state=False,
                    )
                    resumed_coins = json.loads(destination.read_text(encoding="utf-8"))["player"]["coins"]
            finally:
                quest.REPO_ROOT = original_quest_root
                app_v2.REPO_ROOT = original_app_root
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

        self.assertEqual(resumed, destination)
        self.assertEqual(resumed_coins, 56)


if __name__ == "__main__":
    unittest.main()
