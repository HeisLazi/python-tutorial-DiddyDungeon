from __future__ import annotations

import json
import tempfile
import unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch

from ide import quest
from ide.server import app_v2

ROOT = Path(__file__).resolve().parents[2]


class LauncherContractTests(unittest.TestCase):
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
        self.assertNotIn("$command -join", launcher)
        self.assertNotIn("--reload-backend", launcher)
        self.assertIn("-AllowOtherBranch", launcher)
        self.assertIn("-AllowStaleCheckout", launcher)
        self.assertIn("git -C $repoRoot fetch --quiet origin", launcher)
        self.assertIn("rev-parse '@{u}'", launcher)
        self.assertIn("Canonical progress.json has local player-state changes", launcher)
        self.assertIn("exit_code = 0", python_launcher)
        self.assertIn("raise SystemExit(main())", python_launcher)
        self.assertIn("--confirm-local-state", python_launcher)
        self.assertIn("prepare_local_state", python_launcher)

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
            self.assertTrue(quest.linux_rollup_optional_dependency_ready(frontend))

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


if __name__ == "__main__":
    unittest.main()
