from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2


def context_progress() -> dict:
    return {
        "meta": {"revision": 7, "updated_at": "2026-09-15T00:00:00+00:00", "device_id": "local-forge"},
        "player": {"level": 2, "xp": 50, "xp_next": 100, "lifetime_xp": 150, "coins": 55, "hp": 100, "max_hp": 100},
        "learning_state": {
            "project": "01-blackjack",
            "concept": "Input loops and control flow",
            "phase": "forge",
            "reference_mode": False,
            "clean_clear_eligible": True,
        },
        "assist": {"mode": "clean", "reference_mode_uses": 0, "guided_milestones": 0},
        "projects": [
            {
                "branch": "01-blackjack",
                "name": "Blackjack",
                "status": "active",
                "progress": 38,
                "boss": "The House",
                "mobs": [
                    {"name": "The Empty Table", "status": "defeated", "concept": "Variables"},
                    {"name": "The Dealer's Hand", "status": "defeated", "concept": "Lists"},
                    {"name": "The Count Keeper", "status": "defeated", "concept": "Loops"},
                    {
                        "name": "The Hitman",
                        "status": "available",
                        "concept": "Input loops and control flow",
                        "encounter": "Reason about repeated player choices.",
                        "max_resolve": 8,
                        "resolve": 8,
                    },
                    {"name": "The Bust Hound", "status": "locked", "concept": "Conditionals"},
                ],
            }
        ],
        "encounter_state": {
            "project_id": "01-blackjack",
            "mob_name": "The Hitman",
            "status": "active",
            "resolve": 8,
            "max_resolve": 8,
            "completed_objectives": [],
            "attempts": 0,
            "question_types": [],
        },
        "state_events": [],
    }


class PyrContextBridgeTests(unittest.TestCase):
    def test_dungeon_checkpoint_uses_state_gateway_and_context_projection(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        original_dungeon = app_v2.DUNGEON_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            (workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (workspace / "progress.json").write_text('{"player":{"level":99}}', encoding="utf-8")
            (workspace / "tutor.py").write_text("print('legacy')\n", encoding="utf-8")
            (workspace / "dungeon.py.tmp").write_text("stale\n", encoding="utf-8")
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.DUNGEON_PATH = workspace / "dungeon.py"
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                tree = client.get("/api/tree", headers={"host": "127.0.0.1"})
                self.assertEqual(tree.status_code, 200)
                self.assertNotIn("tutor.py", {item["path"] for item in tree.json()["items"]})
                self.assertNotIn("progress.json", {item["path"] for item in tree.json()["items"]})
                self.assertNotIn("dungeon.py.tmp", {item["path"] for item in tree.json()["items"]})
                tutor_context = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"active_path": "tutor.py"},
                )
                self.assertEqual(tutor_context.status_code, 200, tutor_context.text)
                self.assertEqual(tutor_context.json()["context"]["active_file"]["content"], "print('legacy')\n")
                idle = client.get("/api/dungeon", headers={"host": "127.0.0.1"})
                self.assertEqual(idle.status_code, 200)
                self.assertEqual(idle.json()["dungeon"]["status"], "idle")
                self.assertTrue((workspace / "dungeon.py").exists())
                self.assertEqual((workspace / "dungeon.py").read_text(encoding="utf-8"), "")

                started = client.post(
                    "/api/dungeon/start",
                    headers={"host": "127.0.0.1"},
                    json={"concept_id": "lists", "seed": "bridge-seed"},
                )
                self.assertEqual(started.status_code, 200)
                run = started.json()["dungeon"]
                self.assertTrue(run["active"])
                self.assertEqual(run["floor"], 1)
                self.assertEqual(run["loadout"]["armor"], "Apprentice Coat")
                self.assertEqual(run["loadout"]["heals"], 1)
                self.assertEqual(run["inventory"][0]["id"], "dungeon-starter-armor")
                self.assertTrue(run["inventory"][0]["equipped"])
                self.assertEqual(run["editor_content"], "")
                chosen = client.post(
                    "/api/dungeon/choose",
                    headers={"host": "127.0.0.1"},
                    json={"run_id": run["run_id"], "choice_id": run["room_choices"][0]["id"]},
                )
                self.assertEqual(chosen.status_code, 200, chosen.text)
                run = chosen.json()["dungeon"]

                saved = client.put(
                    "/api/dungeon/editor",
                    headers={"host": "127.0.0.1"},
                    json={"run_id": run["run_id"], "question_id": run["question"]["id"], "content": "items = []\n"},
                )
                self.assertEqual(saved.status_code, 200)
                self.assertEqual(saved.json()["dungeon"]["editor_content"], "items = []\n")
                self.assertEqual((workspace / "dungeon.py").read_text(encoding="utf-8"), "items = []\n")

                context = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"active_path": "dungeon.py"},
                )
                self.assertEqual(context.status_code, 200)
                self.assertEqual(context.json()["context"]["active_file"]["content"], "items = []\n")

                direct_read = client.get("/api/file?path=dungeon.py", headers={"host": "127.0.0.1"})
                self.assertEqual(direct_read.status_code, 403)
                direct_write = client.put(
                    "/api/file",
                    headers={"host": "127.0.0.1"},
                    json={"path": "dungeon.py", "content": "tips = 'leak'\n"},
                )
                self.assertEqual(direct_write.status_code, 403)
                legacy_read = client.get("/api/file?path=tutor.py", headers={"host": "127.0.0.1"})
                self.assertEqual(legacy_read.status_code, 403)
                legacy_format = client.post(
                    "/api/format",
                    headers={"host": "127.0.0.1"},
                    json={"path": "tutor.py", "content": "print('legacy')\n"},
                )
                self.assertEqual(legacy_format.status_code, 403)

                next_question = app_v2.STATE_SERVICE.apply_internal(
                    "dungeon_issue_question",
                    {
                        "run_id": run["run_id"],
                        "floor": 1,
                        "room": 2,
                        "question": {
                            "id": f"{run['run_id']}-q2",
                            "question_type": "true_false",
                            "concept_id": "lists",
                            "difficulty": 2,
                            "prompt": "Is indexing zero-based?",
                            "options": ["True", "False"],
                        },
                    },
                )
                self.assertTrue(next_question["changed"])
                stale_save = client.put(
                    "/api/dungeon/editor",
                    headers={"host": "127.0.0.1"},
                    json={"run_id": run["run_id"], "question_id": run["question"]["id"], "content": "late = 'old'\n"},
                )
                self.assertEqual(stale_save.status_code, 409)
                refreshed = client.get("/api/dungeon", headers={"host": "127.0.0.1"})
                self.assertEqual(refreshed.status_code, 200)
                self.assertEqual(refreshed.json()["dungeon"]["room"], 2)
                self.assertEqual(refreshed.json()["dungeon"]["editor_content"], "")
                self.assertEqual((workspace / "dungeon.py").read_text(encoding="utf-8"), "")
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                app_v2.DUNGEON_PATH = original_dungeon

    def test_campaign_polling_survives_invalid_dungeon_projection(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        original_dungeon = app_v2.DUNGEON_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            state = context_progress()
            state["dungeon_run"] = {"status": "corrupt", "run_id": "bad-run"}
            canonical.write_text(json.dumps(state), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.DUNGEON_PATH = workspace / "dungeon.py"
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                response = client.get("/api/campaign", headers={"host": "127.0.0.1"})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["dungeon"]["status"], "invalid")
                self.assertEqual(response.json()["progress"]["player"]["level"], 2)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                app_v2.DUNGEON_PATH = original_dungeon

    def test_dungeon_provider_bridge_binds_answer_and_rotates_only_after_verdict(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        original_dungeon = app_v2.DUNGEON_PATH
        original_challenge = app_v2.PYR_DUNGEON_CHALLENGE
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.DUNGEON_PATH = workspace / "dungeon.py"
            app_v2.PYR_DUNGEON_CHALLENGE = None
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                started = client.post("/api/dungeon/start", headers={"host": "127.0.0.1"}, json={"concept_id": "lists", "seed": "bridge"})
                self.assertEqual(started.status_code, 200)
                run = started.json()["dungeon"]
                chosen = client.post("/api/dungeon/choose", headers={"host": "127.0.0.1"}, json={"run_id": run["run_id"], "choice_id": run["room_choices"][0]["id"]})
                self.assertEqual(chosen.status_code, 200, chosen.text)
                run = chosen.json()["dungeon"]
                context = client.post("/api/pyr/context", headers={"host": "127.0.0.1"}, json={"active_path": "dungeon.py"})
                self.assertEqual(context.status_code, 200, context.text)
                challenge = context.json()["context"]["dungeon_verdict"]
                self.assertEqual(challenge["run_id"], run["run_id"])
                bound = client.post(
                    "/api/pyr/dungeon-submission",
                    headers={"host": "127.0.0.1"},
                    json={"nonce": challenge["nonce"], "run_id": run["run_id"], "question_id": run["question"]["id"], "answer": "items = ['red']"},
                )
                self.assertEqual(bound.status_code, 200, bound.text)
                submission = bound.json()["submission"]
                verdict = client.post(
                    "/api/pyr/dungeon-verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": submission["nonce"],
                        "submission_id": submission["submission_id"],
                        "answer_digest": submission["answer_digest"],
                        "verdict": "correct",
                        "run_id": run["run_id"],
                        "question_id": run["question"]["id"],
                        "evidence_id": submission["evidence_id"],
                        "reason": "Provider validated the current Dungeon answer.",
                    },
                )
                self.assertEqual(verdict.status_code, 200, verdict.text)
                self.assertEqual(verdict.json()["mutation"]["result"]["run"]["room"], 2)
                self.assertEqual(verdict.json()["mutation"]["event"]["action"], "dungeon_record_verdict")
                self.assertEqual(json.loads(canonical.read_text(encoding="utf-8"))["player"]["coins"], 55)
                replay = client.post(
                    "/api/pyr/dungeon-verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": submission["nonce"],
                        "submission_id": submission["submission_id"],
                        "answer_digest": submission["answer_digest"],
                        "verdict": "correct",
                        "run_id": run["run_id"],
                        "question_id": run["question"]["id"],
                        "evidence_id": submission["evidence_id"],
                        "reason": "Replay must fail.",
                    },
                )
                self.assertEqual(replay.status_code, 409)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                app_v2.DUNGEON_PATH = original_dungeon
                app_v2.PYR_DUNGEON_CHALLENGE = original_challenge

    def test_context_is_bounded_live_and_does_not_mutate_player_state(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            (workspace / "main.py").write_text("print('hello')\n", encoding="utf-8")
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.PYR_CONTEXT_INPUT.update({"active_path": None, "selection": "", "terminal_tail": ""})
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                response = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={
                        "active_path": "main.py",
                        "selection": "\x1b[31mwhile\x1b[0m choice:\n    print(choice)",
                        "terminal_tail": "\x1b[2KTraceback\r\nValueError: bad input\r\n",
                    },
                )
                self.assertEqual(response.status_code, 200)
                context = response.json()["context"]
                self.assertEqual(context["revision"], 7)
                nonce = context["verdict"]["nonce"]
                self.assertEqual(context["verdict"]["mob_name"], "The Hitman")
                self.assertEqual(context["active_file"]["path"], "main.py")
                self.assertEqual(context["active_file"]["content"], "print('hello')\n")
                self.assertEqual(context["selection"]["text"], "while choice:\n    print(choice)")
                self.assertEqual(context["terminal"]["tail"], "Traceback\nValueError: bad input\n")
                self.assertEqual(context["quest"]["mob"]["name"], "The Hitman")
                self.assertEqual(context["quest"]["mob"]["concept"], "Input loops and control flow")
                self.assertEqual(context["quest"]["assistance"]["mode"], "clean")
                self.assertNotIn("The Bust Hound", json.dumps(context["quest"]["mob"]))

                persisted = json.loads(canonical.read_text(encoding="utf-8"))
                self.assertEqual(persisted["meta"]["revision"], 7)
                self.assertEqual(persisted["state_events"], [])

                submission_response = client.post(
                    "/api/pyr/battle-submission",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": nonce,
                        "objective_id": "choice_flow",
                        "answer": "I would stop asking for cards when the choice is no longer true.",
                    },
                )
                self.assertEqual(submission_response.status_code, 200)
                submission = submission_response.json()["submission"]
                self.assertEqual(submission["objective_id"], "choice_flow")
                self.assertEqual(submission["question_type"], "code_checkpoint")
                self.assertEqual(submission["impact"], 4)
                self.assertEqual(submission["evidence_id"], submission["submission_id"])
                self.assertEqual(len(submission["answer_digest"]), 64)
                self.assertEqual(json.loads(canonical.read_text(encoding="utf-8"))["meta"]["revision"], 7)
                pending_context = client.get("/api/pyr/context", headers={"host": "127.0.0.1"})
                self.assertEqual(pending_context.status_code, 200)
                self.assertEqual(pending_context.json()["context"]["verdict"]["nonce"], nonce)
                self.assertEqual(pending_context.json()["context"]["verdict"]["submission_id"], submission["submission_id"])

                mismatched_verdict = client.post(
                    "/api/pyr/verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": nonce,
                        "submission_id": submission["submission_id"],
                        "answer_digest": "0" * 64,
                        "verdict": "correct",
                        "objective_id": "choice_flow",
                        "evidence_id": submission["evidence_id"],
                        "reason": "The digest does not match the submitted answer.",
                    },
                )
                self.assertEqual(mismatched_verdict.status_code, 409)

                verdict = client.post(
                    "/api/pyr/verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": nonce,
                        "submission_id": submission["submission_id"],
                        "answer_digest": submission["answer_digest"],
                        "verdict": "correct",
                        "objective_id": "choice_flow",
                        "evidence_id": submission["evidence_id"],
                        "reason": "PYR verified the stop and continue explanation.",
                    },
                )
                self.assertEqual(verdict.status_code, 200)
                mutation = verdict.json()["mutation"]
                self.assertEqual(mutation["result"]["resolve_after"], 4)
                self.assertEqual(mutation["event"]["action"], "record_battle_objective")
                self.assertEqual(mutation["revision"], 8)

                replay = client.post(
                    "/api/pyr/verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": nonce,
                        "submission_id": submission["submission_id"],
                        "answer_digest": submission["answer_digest"],
                        "verdict": "correct",
                        "objective_id": "stop_condition",
                        "evidence_id": submission["evidence_id"],
                        "reason": "Replay must be rejected.",
                    },
                )
                self.assertEqual(replay.status_code, 409)

                fetched = client.get("/api/pyr/context", headers={"host": "127.0.0.1"})
                self.assertEqual(fetched.status_code, 200)
                refreshed_context = fetched.json()["context"]
                self.assertEqual(refreshed_context["active_file"]["path"], "main.py")
                self.assertNotEqual(refreshed_context["verdict"]["nonce"], nonce)

                miss_submission_response = client.post(
                    "/api/pyr/battle-submission",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": refreshed_context["verdict"]["nonce"],
                        "objective_id": "stop_condition",
                        "answer": "I would keep looping without checking whether the player wants another card.",
                    },
                )
                self.assertEqual(miss_submission_response.status_code, 200)
                miss_submission = miss_submission_response.json()["submission"]

                miss = client.post(
                    "/api/pyr/verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": refreshed_context["verdict"]["nonce"],
                        "submission_id": miss_submission["submission_id"],
                        "answer_digest": miss_submission["answer_digest"],
                        "verdict": "incorrect",
                        "objective_id": "stop_condition",
                        "evidence_id": miss_submission["evidence_id"],
                        "reason": "PYR marked the submitted explanation incomplete.",
                    },
                )
                self.assertEqual(miss.status_code, 200)
                miss_mutation = miss.json()["mutation"]
                self.assertEqual(miss_mutation["event"]["action"], "record_battle_miss")
                self.assertEqual(miss_mutation["result"]["damage"], 18)
                self.assertEqual(miss_mutation["event"]["evidence_id"], miss_submission["evidence_id"])
                self.assertEqual(miss_mutation["result"]["mob_name"], "The Hitman")
                self.assertEqual(miss_mutation["result"]["objective_id"], "stop_condition")
                self.assertEqual(miss_mutation["result"]["question_type"], "bug_diagnosis")

                reconciled = json.loads(canonical.read_text(encoding="utf-8"))
                encounter = reconciled["encounter_state"]
                self.assertEqual(encounter["attempts"], 2)
                self.assertEqual(encounter["question_types"], ["code_checkpoint", "bug_diagnosis"])
                codex_entry = reconciled["codex"]["encounters"][0]
                self.assertEqual(codex_entry["attempts"], 2)
                self.assertEqual(codex_entry["question_types"], ["code_checkpoint", "bug_diagnosis"])
                self.assertEqual([item["outcome"] for item in codex_entry["results"]], ["verified", "incorrect"])
                self.assertEqual(codex_entry["mastery"]["evidence"], 1)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

    def test_battle_and_dungeon_challenges_are_isolated_per_tab(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        original_dungeon = app_v2.DUNGEON_PATH
        original_context_challenge = app_v2.PYR_CONTEXT_CHALLENGE
        original_dungeon_challenge = app_v2.PYR_DUNGEON_CHALLENGE
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.DUNGEON_PATH = workspace / "dungeon.py"
            app_v2.PYR_CONTEXT_CHALLENGE = None
            app_v2.PYR_DUNGEON_CHALLENGE = None
            app_v2.PYR_CONTEXT_CHALLENGES.clear()
            app_v2.PYR_DUNGEON_CHALLENGES.clear()
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                tab_a = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "tab-a"},
                ).json()["context"]["verdict"]
                tab_b = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "tab-b"},
                ).json()["context"]["verdict"]
                self.assertNotEqual(tab_a["nonce"], tab_b["nonce"])

                # Issuing a challenge in tab B must not invalidate tab A's
                # pending answer, which was the old process-global-slot bug.
                bound = client.post(
                    "/api/pyr/battle-submission",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": tab_a["nonce"],
                        "objective_id": "choice_flow",
                        "answer": "I stop when the player's choice is no longer true.",
                    },
                )
                self.assertEqual(bound.status_code, 200, bound.text)

                started = client.post(
                    "/api/dungeon/start",
                    headers={"host": "127.0.0.1"},
                    json={"concept_id": "lists", "seed": "tab-isolation"},
                )
                self.assertEqual(started.status_code, 200, started.text)
                run = started.json()["dungeon"]
                chosen = client.post(
                    "/api/dungeon/choose",
                    headers={"host": "127.0.0.1"},
                    json={"run_id": run["run_id"], "choice_id": run["room_choices"][0]["id"]},
                )
                self.assertEqual(chosen.status_code, 200, chosen.text)
                run = chosen.json()["dungeon"]
                dungeon_a = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "tab-a", "active_path": "dungeon.py"},
                ).json()["context"]["dungeon_verdict"]
                dungeon_b = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "tab-b", "active_path": "dungeon.py"},
                ).json()["context"]["dungeon_verdict"]
                self.assertNotEqual(dungeon_a["nonce"], dungeon_b["nonce"])
                dungeon_bound = client.post(
                    "/api/pyr/dungeon-submission",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": dungeon_a["nonce"],
                        "run_id": run["run_id"],
                        "question_id": run["question"]["id"],
                        "answer": "items = []",
                    },
                )
                self.assertEqual(dungeon_bound.status_code, 200, dungeon_bound.text)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                app_v2.DUNGEON_PATH = original_dungeon
                app_v2.PYR_CONTEXT_CHALLENGE = original_context_challenge
                app_v2.PYR_DUNGEON_CHALLENGE = original_dungeon_challenge
                app_v2.PYR_CONTEXT_CHALLENGES.clear()
                app_v2.PYR_DUNGEON_CHALLENGES.clear()

    def test_context_reads_are_isolated_per_tab(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        original_context_input = dict(app_v2.PYR_CONTEXT_INPUT)
        original_context_inputs = {
            key: dict(value) for key, value in app_v2.PYR_CONTEXT_INPUTS.items()
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            with app_v2.PYR_CONTEXT_LOCK:
                app_v2.PYR_CONTEXT_INPUTS.clear()
                app_v2.PYR_CONTEXT_INPUT.update(
                    {"active_path": None, "selection": "", "terminal_tail": "", "client_id": "default"}
                )
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                posted_a = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "tab-a", "selection": "marker-A", "terminal_tail": "tail-A"},
                )
                posted_b = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "tab-b", "selection": "marker-B", "terminal_tail": "tail-B"},
                )
                self.assertEqual(posted_a.status_code, 200, posted_a.text)
                self.assertEqual(posted_b.status_code, 200, posted_b.text)

                read_a = client.get(
                    "/api/pyr/context",
                    params={"client_id": "tab-a"},
                    headers={"host": "127.0.0.1"},
                )
                read_b = client.get(
                    "/api/pyr/context",
                    params={"client_id": "tab-b"},
                    headers={"host": "127.0.0.1"},
                )
                self.assertEqual(read_a.status_code, 200, read_a.text)
                self.assertEqual(read_b.status_code, 200, read_b.text)
                self.assertEqual(read_a.json()["context"]["selection"]["text"], "marker-A")
                self.assertEqual(read_a.json()["context"]["terminal"]["tail"], "tail-A")
                self.assertEqual(read_b.json()["context"]["selection"]["text"], "marker-B")
                self.assertEqual(read_b.json()["context"]["terminal"]["tail"], "tail-B")

                default = client.get(
                    "/api/pyr/context", headers={"host": "127.0.0.1"}
                )
                self.assertEqual(default.status_code, 200, default.text)
                self.assertNotIn("marker-A", json.dumps(default.json()["context"]))
                self.assertNotIn("marker-B", json.dumps(default.json()["context"]))
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                with app_v2.PYR_CONTEXT_LOCK:
                    app_v2.PYR_CONTEXT_INPUTS.clear()
                    app_v2.PYR_CONTEXT_INPUTS.update(original_context_inputs)
                    app_v2.PYR_CONTEXT_INPUT.clear()
                    app_v2.PYR_CONTEXT_INPUT.update(original_context_input)

    def test_boss_challenges_are_isolated_and_default_slot_stays_compatible(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        original_context_challenge = app_v2.PYR_CONTEXT_CHALLENGE
        original_context_input = dict(app_v2.PYR_CONTEXT_INPUT)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            state = context_progress()
            project = state["projects"][0]
            project.update({"progress": 100, "boss_status": "available", "mob_sequence_complete": True})
            for mob in project["mobs"]:
                mob.update({"status": "defeated", "resolve": 0})
            state["stats"] = {"mobs_defeated": len(project["mobs"])}
            state["achievements"] = [
                {"name": "Housebreaker", "unlocked": False},
                {"name": "Clean Clear", "unlocked": False},
            ]
            canonical.write_text(json.dumps(state), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.PYR_CONTEXT_CHALLENGE = None
            app_v2.PYR_CONTEXT_CHALLENGES.clear()
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                default = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={},
                ).json()["context"]["verdict"]
                self.assertEqual(default["challenge_type"], "boss")
                self.assertIs(app_v2.PYR_CONTEXT_CHALLENGES["default"], app_v2.PYR_CONTEXT_CHALLENGE)

                tab_a = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "boss-tab-a"},
                ).json()["context"]["verdict"]
                tab_b = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"client_id": "boss-tab-b"},
                ).json()["context"]["verdict"]
                self.assertNotEqual(default["nonce"], tab_a["nonce"])
                self.assertNotEqual(tab_a["nonce"], tab_b["nonce"])

                submission = client.post(
                    "/api/pyr/boss-submission",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": tab_a["nonce"],
                        "requirement_id": "required_behavior",
                        "answer": "I stop when the required behaviour is satisfied.",
                    },
                )
                self.assertEqual(submission.status_code, 200, submission.text)
                body = submission.json()["submission"]
                verdict = client.post(
                    "/api/pyr/boss-verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": tab_a["nonce"],
                        "submission_id": body["submission_id"],
                        "answer_digest": body["answer_digest"],
                        "verdict": "correct",
                        "requirement_id": "required_behavior",
                        "evidence_id": body["evidence_id"],
                        "reason": "The bounded behaviour evidence is present.",
                    },
                )
                self.assertEqual(verdict.status_code, 200, verdict.text)
                self.assertEqual(verdict.json()["verified_requirements"], ["required_behavior"])
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                app_v2.PYR_CONTEXT_CHALLENGE = original_context_challenge
                app_v2.PYR_CONTEXT_INPUT.clear()
                app_v2.PYR_CONTEXT_INPUT.update(original_context_input)
                app_v2.PYR_CONTEXT_CHALLENGES.clear()

    def test_context_rejects_state_file_and_bounds_large_text(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            (workspace / "progress.json").write_text("{}", encoding="utf-8")
            canonical = root / "progress.json"
            canonical.write_text(json.dumps(context_progress()), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.PYR_CONTEXT_INPUT.update({"active_path": None, "selection": "", "terminal_tail": ""})
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                rejected = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"active_path": "progress.json"},
                )
                self.assertEqual(rejected.status_code, 403)

                (workspace / ".env").write_text("SECRET=do-not-forward\n", encoding="utf-8")
                secret_rejected = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"active_path": ".env"},
                )
                self.assertEqual(secret_rejected.status_code, 403)

                large_file = workspace / "large.py"
                large_file.write_text("# bounded\n" + ("x" * 50_000), encoding="utf-8")
                large_context = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"active_path": "large.py"},
                )
                self.assertEqual(large_context.status_code, 200)
                large_active_file = large_context.json()["context"]["active_file"]
                self.assertTrue(large_active_file["truncated"])
                self.assertEqual(large_active_file["bytes"], large_file.stat().st_size)
                self.assertLessEqual(len(large_active_file["content"].encode()), 40_000)

                bounded = client.post(
                    "/api/pyr/context",
                    headers={"host": "127.0.0.1"},
                    json={"selection": "x" * 25_000, "terminal_tail": "y" * 25_000},
                )
                self.assertEqual(bounded.status_code, 200)
                context = bounded.json()["context"]
                self.assertTrue(context["selection"]["truncated"])
                self.assertTrue(context["terminal"]["truncated"])
                self.assertLessEqual(len(context["selection"]["text"].encode()), 20_000)
                self.assertLessEqual(len(context["terminal"]["tail"].encode()), 20_000)

                missing_submission = client.post(
                    "/api/pyr/verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": context["verdict"]["nonce"],
                        "submission_id": "battle-missing",
                        "answer_digest": "0" * 64,
                        "verdict": "incorrect",
                        "objective_id": "choice_flow",
                        "evidence_id": "battle-missing",
                        "reason": "No submission exists.",
                    },
                )
                self.assertEqual(missing_submission.status_code, 409)

                forbidden = client.post(
                    "/api/pyr/verdict",
                    headers={"host": "127.0.0.1"},
                    json={
                        "nonce": context["verdict"]["nonce"],
                        "verdict": "incorrect",
                        "objective_id": "choice_flow",
                        "evidence_id": "wrong-001",
                        "reason": "The answer was incomplete.",
                        "raw_damage": 1,
                    },
                )
                self.assertEqual(forbidden.status_code, 422)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress

    def test_boss_bridge_requires_three_bound_evidence_verdicts_before_clear(self):
        original_workspace = app_v2.WORKSPACE
        original_progress = app_v2.PROGRESS_PATH
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / "quest"
            workspace.mkdir()
            canonical = root / "platform" / "progress.json"
            canonical.parent.mkdir()
            state = context_progress()
            project = state["projects"][0]
            project["progress"] = 100
            project["boss"] = "The House"
            project["boss_status"] = "available"
            project["mob_sequence_complete"] = True
            for mob in project["mobs"]:
                mob["status"] = "defeated"
                mob["resolve"] = 0
            state["stats"] = {"mobs_defeated": len(project["mobs"])}
            state["achievements"] = [{"name": "Housebreaker", "unlocked": False}, {"name": "Clean Clear", "unlocked": False}]
            canonical.write_text(json.dumps(state), encoding="utf-8")
            app_v2.WORKSPACE = workspace
            app_v2.PROGRESS_PATH = canonical
            app_v2.PYR_CONTEXT_CHALLENGE = None
            try:
                client = TestClient(app_v2.app, base_url="http://127.0.0.1")
                context = client.post("/api/pyr/context", headers={"host": "127.0.0.1"}, json={}).json()["context"]
                self.assertEqual(context["verdict"]["challenge_type"], "boss")
                self.assertEqual(context["verdict"]["requirements"], ["required_behavior", "explanation", "interview"])
                nonce = context["verdict"]["nonce"]

                for index, requirement in enumerate(("required_behavior", "explanation", "interview")):
                    submission = client.post(
                        "/api/pyr/boss-submission",
                        headers={"host": "127.0.0.1"},
                        json={"nonce": nonce, "requirement_id": requirement, "answer": f"Evidence for {requirement}"},
                    )
                    self.assertEqual(submission.status_code, 200)
                    body = submission.json()["submission"]
                    verdict = client.post(
                        "/api/pyr/boss-verdict",
                        headers={"host": "127.0.0.1"},
                        json={
                            "nonce": nonce,
                            "submission_id": body["submission_id"],
                            "answer_digest": body["answer_digest"],
                            "verdict": "correct",
                            "requirement_id": requirement,
                            "evidence_id": body["evidence_id"],
                            "reason": f"Validated {requirement}",
                        },
                    )
                    self.assertEqual(verdict.status_code, 200, verdict.text)
                    if index < 2:
                        self.assertFalse(verdict.json()["complete"])
                        self.assertEqual(verdict.json()["verified_requirements"], sorted(["required_behavior", "explanation"][: index + 1]))
                    else:
                        self.assertTrue(verdict.json()["complete"])
                        self.assertEqual(verdict.json()["mutation"]["event"]["action"], "record_boss_clear")
                        self.assertEqual(verdict.json()["mutation"]["revision"], 11)

                final = json.loads(canonical.read_text(encoding="utf-8"))
                self.assertTrue(final["projects"][0]["completed"])
                self.assertEqual(final["projects"][0]["boss_status"], "defeated")
                self.assertEqual(final["player"]["xp"], 50)
                self.assertEqual(final["player"]["level"], 3)
                self.assertEqual(final["player"]["lifetime_xp"], 250)
                self.assertEqual(final["stats"]["bosses_defeated"], 1)
            finally:
                app_v2.WORKSPACE = original_workspace
                app_v2.PROGRESS_PATH = original_progress
                app_v2.PYR_CONTEXT_CHALLENGE = None


if __name__ == "__main__":
    unittest.main()
