import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path

from ide.quest import packaged_frontend_dist


class PackagedLauncherTests(unittest.TestCase):
    def test_dist_must_be_absolute_existing_and_in_app_mode(self):
        self.assertIsNone(packaged_frontend_dist({}, app_mode=True))
        with tempfile.TemporaryDirectory() as directory:
            dist = Path(directory) / "dist"
            dist.mkdir()
            with self.assertRaises(SystemExit):
                packaged_frontend_dist({"QUESTLAB_BUNDLED_DIST": str(dist)}, app_mode=True)
            (dist / "index.html").write_text("test", encoding="utf-8")
            self.assertEqual(packaged_frontend_dist({"QUESTLAB_BUNDLED_DIST": str(dist)}, app_mode=True), dist)
            with self.assertRaises(SystemExit):
                packaged_frontend_dist({"QUESTLAB_BUNDLED_DIST": str(dist)}, app_mode=False)
            with self.assertRaises(SystemExit):
                packaged_frontend_dist({"QUESTLAB_BUNDLED_DIST": "relative"}, app_mode=True)

    def test_app_serves_prebuilt_dist_without_node_or_npm(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            dist = root / "dist"
            dist.mkdir()
            (dist / "index.html").write_text("packaged-ui-marker", encoding="utf-8")
            save = root / "progress.json"
            env = os.environ.copy()
            env.update({"PATH": str(root), "QUESTLAB_BUNDLED_DIST": str(dist), "QUESTLAB_STATE_PATH": str(save), "QUESTLAB_INITIALIZE_SAVE": "1"})
            launcher = subprocess.Popen(
                [sys.executable, "-u", "-m", "ide.quest", "--app", "--no-browser", "--backend-port", "17345", "--workspace", str(root)],
                env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            )
            try:
                ready = None
                for line in launcher.stdout:
                    if line.startswith("QUESTLAB_READY "):
                        ready = line.split(None, 1)[1].strip()
                        break
                    if line.startswith("QUESTLAB_FAILED"):
                        break
                self.assertIsNotNone(ready, "Packaged app failed to start")
                with urllib.request.urlopen(ready, timeout=5) as response:
                    self.assertEqual(response.read().decode(), "packaged-ui-marker")
                with urllib.request.urlopen(ready + "/api/campaign", timeout=5) as response:
                    campaign = json.load(response)
                    self.assertEqual(campaign["progress"]["player"]["level"], 1)
                    self.assertTrue(any(p["branch"] == "00-lantern-vale" for p in campaign["progress"]["projects"]))
                with urllib.request.urlopen(ready + "/api/runtime", timeout=5) as response:
                    runtime = json.load(response)
                    self.assertTrue(runtime["packaged"])
            finally:
                launcher.terminate()
                launcher.wait(timeout=8)
                launcher.stdout.close()


if __name__ == "__main__":
    unittest.main()
