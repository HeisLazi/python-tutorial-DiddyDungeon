from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from ide import quest

ROOT = Path(__file__).resolve().parents[2]


class LauncherContractTests(unittest.TestCase):
    def test_windows_launcher_requires_the_intended_checkout_and_stable_pty_mode(self):
        launcher = (ROOT / "tools" / "questlab-launch.ps1").read_text(encoding="utf-8")
        python_launcher = (ROOT / "ide" / "quest.py").read_text(encoding="utf-8")
        self.assertIn("$expectedBranch = 'feature/cloud-sync-desktop'", launcher)
        self.assertIn("ide/quest.py", launcher)
        self.assertIn("Canonical state:", launcher)
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


if __name__ == "__main__":
    unittest.main()
