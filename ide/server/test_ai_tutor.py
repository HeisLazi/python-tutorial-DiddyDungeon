from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from starlette.testclient import TestClient

from ide.server import ai_tutor, app_v2
from ide.server.test_context_bridge import context_progress

# A fake `opencode` CLI. Behaviour is chosen per test through STUB_MODE and
# STUB_REPLY; every argv is appended to STUB_LOG so tests can assert exactly
# what Quest Lab asked OpenCode to do.
STUB = """#!{python}
import json, os, sys
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
args = sys.argv[1:]
if args[:1] == ["--version"]:
    print("opencode v9.9.9")
elif args[:2] == ["auth", "list"]:
    print("OpenCode Go     OpenCode Go                 stored")
    print("Google          API key                     stored")
elif args[:1] == ["models"]:
    print("google/fast-model")
    print("opencode-go/big-model")
elif args[:1] == ["run"]:
    mode = os.environ.get("STUB_MODE", "json")
    print(json.dumps({{"type": "step_start", "part": {{"type": "step-start"}}}}))
    if mode == "error":
        print(json.dumps({{"type": "error", "error": {{"message": "The requested model is not supported."}}}}))
        sys.exit(1)
    text = os.environ.get("STUB_REPLY", "") if mode == "json" else "I think it is fine!"
    print(json.dumps({{"type": "text", "part": {{"type": "text", "text": text}}}}))
"""


class AiTutorTestCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.stub = root / "opencode"
        self.stub.write_text(STUB.format(python=sys.executable), encoding="utf-8")
        self.stub.chmod(0o755)
        self.log = root / "argv.log"
        self.env = {
            "QUESTLAB_OPENCODE_BIN": str(self.stub),
            "QUESTLAB_AI_STATE_DIR": str(root / "state"),
            "STUB_LOG": str(self.log),
            "STUB_MODE": "json",
            "STUB_REPLY": "",
        }
        self.saved_env = {key: os.environ.get(key) for key in self.env}
        os.environ.update(self.env)
        ai_tutor._MODELS_CACHE.update({"at": 0.0, "models": []})

    def tearDown(self):
        for key, value in self.saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.temp.cleanup()

    def reply(self, value):
        os.environ["STUB_MODE"] = "json"
        os.environ["STUB_REPLY"] = value if isinstance(value, str) else json.dumps(value)

    def calls(self):
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()] if self.log.exists() else []


class AiTutorModuleTests(AiTutorTestCase):
    def test_status_lists_integration_names_without_exporting_credentials(self):
        report = ai_tutor.status()
        self.assertTrue(report["installed"])
        self.assertTrue(report["ready"])
        self.assertEqual(report["integrations"], ["OpenCode Go", "Google"])
        self.assertEqual(report["version"], "opencode v9.9.9")
        self.assertNotIn("export", [arg for call in self.calls() for arg in call])

    def test_settings_are_device_local_and_validated(self):
        self.assertEqual(ai_tutor.load_settings()["model"], "")
        saved = ai_tutor.save_settings({"model": "google/fast-model", "auto_grade": False})
        self.assertEqual(saved["model"], "google/fast-model")
        self.assertFalse(ai_tutor.load_settings()["auto_grade"])
        self.assertTrue(ai_tutor.settings_path().is_file())
        with self.assertRaises(ai_tutor.AiTutorError):
            ai_tutor.save_settings({"model": "google/x; rm -rf /"})

    def test_run_prompt_uses_plan_agent_scratch_dir_and_selected_model(self):
        ai_tutor.save_settings({"model": "google/fast-model"})
        self.reply({"verdict": "correct", "reason": "Nice."})
        ai_tutor.judge("practice", context=None, answer="print(1)", question="Print one.")
        run = next(call for call in self.calls() if call[:1] == ["run"])
        self.assertEqual(run[1:5], ["--agent", "plan", "--format", "json"])
        self.assertIn("--model", run)
        self.assertEqual(run[run.index("--model") + 1], "google/fast-model")
        self.assertIn("print(1)", run[-1])

    def test_judge_accepts_only_strict_verdict_json(self):
        self.reply('```json\n{"verdict": "incorrect", "reason": "What happens when the hand is empty?"}\n```')
        self.assertEqual(ai_tutor.judge("battle", context={}, answer="x")["verdict"], "incorrect")

        for bad in ({"verdict": "maybe", "reason": "?"}, {"verdict": "correct"}, {"verdict": "correct", "reason": "ok", "xp": 500}):
            self.reply(bad)
            with self.assertRaises(ai_tutor.AiTutorError):
                ai_tutor.judge("battle", context={}, answer="x")

        os.environ["STUB_MODE"] = "garbage"
        with self.assertRaises(ai_tutor.AiTutorError) as garbage:
            ai_tutor.judge("battle", context={}, answer="x")
        self.assertEqual(garbage.exception.kind, "unparseable")

        os.environ["STUB_MODE"] = "error"
        with self.assertRaises(ai_tutor.AiTutorError) as provider:
            ai_tutor.judge("battle", context={}, answer="x")
        self.assertEqual(provider.exception.kind, "provider")

    def test_dungeon_question_and_lens_shapes(self):
        self.reply({"prompt": "True or false: range(3) yields 3 numbers.", "options": ["yes", "no"]})
        question = ai_tutor.write_dungeon_question(concept="loops", question_type="true_false", difficulty=1, room_type="encounter", floor=1)
        self.assertEqual(question["options"], ["True", "False"])

        self.reply({"lens_id": "trace", "question": "Trace total in this loop…", "why": "Totals are shaky."})
        lens = ai_tutor.choose_practice_lens(concept="loops", lenses=[{"id": "trace", "label": "Trace", "prompt": "Trace it"}], learner={})
        self.assertEqual(lens["lens_id"], "trace")
        self.reply({"lens_id": "invented", "question": "?"})
        with self.assertRaises(ai_tutor.AiTutorError):
            ai_tutor.choose_practice_lens(concept="loops", lenses=[{"id": "trace", "label": "Trace", "prompt": "Trace it"}], learner={})


class AiTutorEndpointTests(AiTutorTestCase):
    def setUp(self):
        super().setUp()
        self.originals = (app_v2.WORKSPACE, app_v2.PROGRESS_PATH, app_v2.DUNGEON_PATH, app_v2.PYR_DUNGEON_CHALLENGE)
        root = Path(self.temp.name)
        workspace = root / "quest"
        workspace.mkdir()
        self.canonical = root / "platform" / "progress.json"
        self.canonical.parent.mkdir()
        self.canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
        app_v2.WORKSPACE = workspace
        app_v2.PROGRESS_PATH = self.canonical
        app_v2.DUNGEON_PATH = workspace / "dungeon.py"
        app_v2.PYR_DUNGEON_CHALLENGE = None
        app_v2.AI_ISSUED_DUNGEON_QUESTIONS.clear()
        self.client = TestClient(app_v2.app, base_url="http://127.0.0.1")
        self.headers = {"host": "127.0.0.1"}

    def tearDown(self):
        app_v2.WORKSPACE, app_v2.PROGRESS_PATH, app_v2.DUNGEON_PATH, app_v2.PYR_DUNGEON_CHALLENGE = self.originals
        super().tearDown()

    def enter_room(self):
        run = self.client.post("/api/dungeon/start", headers=self.headers, json={"concept_id": "lists", "seed": "bridge"}).json()["dungeon"]
        choice = next(c["id"] for c in run["room_choices"] if c["kind"] in {"encounter", "elite"})
        return self.client.post("/api/dungeon/choose", headers=self.headers, json={"run_id": run["run_id"], "choice_id": choice}).json()["dungeon"]

    def bind(self, run, answer):
        challenge = self.client.post("/api/pyr/context", headers=self.headers, json={"active_path": "dungeon.py"}).json()["context"]["dungeon_verdict"]
        bound = self.client.post(
            "/api/pyr/dungeon-submission",
            headers=self.headers,
            json={"nonce": challenge["nonce"], "run_id": run["run_id"], "question_id": run["question"]["id"], "answer": answer},
        )
        self.assertEqual(bound.status_code, 200, bound.text)
        return bound.json()["submission"]

    def test_status_endpoint(self):
        body = self.client.get("/api/ai/status", headers=self.headers).json()
        self.assertTrue(body["opencode"]["ready"])
        self.assertEqual(body["settings"]["provider"], "opencode")

    def test_judge_applies_dungeon_verdict_through_gateway(self):
        run = self.enter_room()
        submission = self.bind(run, "items = ['red']")
        self.reply({"verdict": "correct", "reason": "You built the list the question asked for."})
        judged = self.client.post(
            "/api/ai/judge",
            headers=self.headers,
            json={"kind": "dungeon", "submission": submission, "answer": "items = ['red']"},
        )
        self.assertEqual(judged.status_code, 200, judged.text)
        self.assertEqual(judged.json()["verdict"], "correct")
        self.assertEqual(judged.json()["applied"]["mutation"]["result"]["run"]["room"], 2)

    def test_judge_failure_leaves_challenge_pending_and_costs_nothing(self):
        run = self.enter_room()
        hp_before = json.loads(self.canonical.read_text(encoding="utf-8"))["dungeon_run"].get("hp")
        submission = self.bind(run, "items = ['red']")
        os.environ["STUB_MODE"] = "garbage"
        failed = self.client.post("/api/ai/judge", headers=self.headers, json={"kind": "dungeon", "submission": submission, "answer": "items = ['red']"})
        self.assertEqual(failed.status_code, 502)
        self.assertEqual(failed.json()["detail"]["kind"], "unparseable")
        self.assertEqual(json.loads(self.canonical.read_text(encoding="utf-8"))["dungeon_run"].get("hp"), hp_before)

        self.reply({"verdict": "correct", "reason": "Retry worked."})
        retried = self.client.post("/api/ai/judge", headers=self.headers, json={"kind": "dungeon", "submission": submission, "answer": "items = ['red']"})
        self.assertEqual(retried.status_code, 200, retried.text)

    def test_judge_rejects_an_answer_that_was_not_bound(self):
        run = self.enter_room()
        submission = self.bind(run, "items = ['red']")
        swapped = self.client.post("/api/ai/judge", headers=self.headers, json={"kind": "dungeon", "submission": submission, "answer": "something else"})
        self.assertEqual(swapped.status_code, 409)
        self.assertFalse(any(call[:1] == ["run"] for call in self.calls()))

    def test_dungeon_question_is_rewritten_once_per_room(self):
        run = self.enter_room()
        self.reply({"prompt": "Write a list holding two colours, then print its length.", "options": ["len(x)", "x.size", "count(x)"]})
        first = self.client.post("/api/ai/dungeon-question", headers=self.headers, json={"run_id": run["run_id"]})
        self.assertEqual(first.status_code, 200, first.text)
        self.assertTrue(first.json()["changed"])
        self.assertEqual(first.json()["dungeon"]["question"]["id"], run["question"]["id"])
        self.assertIn("two colours", first.json()["dungeon"]["question"]["prompt"])
        again = self.client.post("/api/ai/dungeon-question", headers=self.headers, json={"run_id": run["run_id"]})
        self.assertFalse(again.json()["changed"])

    def test_dungeon_question_never_rewrites_a_started_answer(self):
        run = self.enter_room()
        saved = self.client.put(
            "/api/dungeon/editor",
            headers=self.headers,
            json={"run_id": run["run_id"], "question_id": run["question"]["id"], "content": "colours = ['red']"},
        )
        self.assertEqual(saved.status_code, 200, saved.text)
        result = self.client.post("/api/ai/dungeon-question", headers=self.headers, json={"run_id": run["run_id"]})
        self.assertFalse(result.json()["changed"])
        self.assertFalse(any(call[:1] == ["run"] for call in self.calls()))


if __name__ == "__main__":
    unittest.main()
