from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from ide.server import app_v2
from ide.server.state import CUSTODY_CONFIRMATION_TOKEN, LocalStateService, StateCommandError, legacy_state_report


def fixture_progress() -> dict:
    return {
        "meta": {"revision": 4, "updated_at": "2026-09-14T00:00:00+00:00", "device_id": "device-alpha"},
        "player": {"level": 1, "xp": 10, "xp_next": 100, "lifetime_xp": 25, "coins": 50, "hp": 100, "max_hp": 100},
        "learning_state": {"reference_mode": False},
        "assist": {"mode": "clean", "reference_mode_uses": 0, "guided_milestones": 0, "xp_forfeited": 0},
        "stats": {"reference_mode_uses": 0, "guided_milestones": 0},
        "homestead": {
            "owned_cosmetics": ["cursor-basic"],
            "equipped": {"cursor": "cursor-basic"},
            "purchase_history": [],
            "catalog": [
                {"id": "cursor-basic", "name": "Forge Cursor", "kind": "cursor", "price": 0},
                {"id": "cursor-golden-spark", "name": "Golden Spark", "kind": "cursor", "price": 10},
            ],
        },
        "achievements": [{"name": "First Blood", "unlocked": False}],
        "activity": {"activity_score": 0},
        "projects": [
            {
                "branch": "01-blackjack",
                "name": "Blackjack",
                "status": "active",
                "progress": 0,
                "mobs": [
                    {"name": "The Empty Table", "status": "available", "concept": "Variables"},
                    {"name": "The Dealer's Hand", "status": "locked", "concept": "Lists"},
                    {"name": "The Count Keeper", "status": "locked", "concept": "Loops"},
                ],
            }
        ],
    }


class StateServiceBehaviorTests(unittest.TestCase):
    def make_service(self):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "progress.json"
        path.write_text(json.dumps(fixture_progress()), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        return LocalStateService(path, threading.RLock()), path

    def read(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_valid_learning_event_is_bounded_and_auditable(self):
        service, path = self.make_service()
        before = self.read(path)
        result = service.apply(
            "record_learning_event",
            {"kind": "teachback", "evidence_id": "session-001", "reason": "Explained list indexing"},
            "pyr",
        )
        after = self.read(path)

        self.assertTrue(result["changed"])
        self.assertEqual(result["revision"], 5)
        self.assertEqual(after["meta"]["device_id"], "device-alpha")
        self.assertNotEqual(after["meta"]["updated_at"], before["meta"]["updated_at"])
        self.assertEqual(after["learning_state"]["last_evidence_id"], "session-001")
        self.assertEqual(after["state_events"][-1]["reason"], "Explained list indexing")
        self.assertEqual(after["state_events"][-1]["revision"], 5)

    def test_forbidden_and_arbitrary_path_commands_are_rejected(self):
        service, path = self.make_service()
        before = self.read(path)

        with self.assertRaises(StateCommandError) as forbidden:
            service.apply("homestead_purchase", {"item_id": "cursor-golden-spark"}, "pyr")
        self.assertEqual(forbidden.exception.status_code, 403)

        with self.assertRaises(StateCommandError) as arbitrary:
            service.apply(
                "record_learning_event",
                {"path": "player.xp", "value": 999999},
                "pyr",
            )
        self.assertEqual(arbitrary.exception.status_code, 422)
        self.assertEqual(self.read(path), before)

    def test_custody_migration_is_copy_once_revision_stable_and_conflict_safe(self):
        service, path = self.make_service()
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "device" / "progress.json"
            source_bytes = path.read_bytes()

            migrated = service.migrate_local_state(
                destination,
                expected_source_revision=4,
                confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
                forbidden_paths=(Path(directory) / "legacy" / "progress.json",),
            )
            self.assertEqual(migrated["status"], "migrated")
            self.assertTrue(migrated["migration_write_performed"])
            self.assertEqual(destination.read_bytes(), source_bytes)
            self.assertEqual(migrated["revision"], 4)
            self.assertTrue(Path(migrated["marker_path"]).is_file())
            self.assertEqual(self.read(path)["meta"]["revision"], 4)

            repeated = service.migrate_local_state(
                destination,
                expected_source_revision=4,
                confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
            )
            self.assertEqual(repeated["status"], "already-local")
            self.assertFalse(repeated["migration_write_performed"])

            destination.write_text(json.dumps({"meta": {"revision": 99}}), encoding="utf-8")
            with self.assertRaises(StateCommandError) as conflict:
                service.migrate_local_state(
                    destination,
                    expected_source_revision=4,
                    confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
                )
            self.assertEqual(conflict.exception.status_code, 409)

            with self.assertRaises(StateCommandError) as stale:
                service.migrate_local_state(
                    Path(directory) / "other.json",
                    expected_source_revision=3,
                    confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
                )
            self.assertEqual(stale.exception.status_code, 409)

    def test_custody_migration_rejects_wrong_token_and_symlink_destination(self):
        service, path = self.make_service()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(StateCommandError) as token:
                service.migrate_local_state(
                    root / "device" / "progress.json",
                    expected_source_revision=4,
                    confirmation_token="NOPE",
                )
            self.assertEqual(token.exception.status_code, 403)

            destination = root / "device" / "progress.json"
            destination.parent.mkdir()
            try:
                destination.symlink_to(path)
            except (OSError, NotImplementedError):
                self.skipTest("symlinks are unavailable on this filesystem")
            with self.assertRaises(StateCommandError) as symlink:
                service.migrate_local_state(
                    destination,
                    expected_source_revision=4,
                    confirmation_token=CUSTODY_CONFIRMATION_TOKEN,
                )
            self.assertEqual(symlink.exception.status_code, 409)

    def test_system_reward_is_internal_only_and_does_not_grant_from_http_actor(self):
        service, path = self.make_service()
        with self.assertRaises(StateCommandError) as forbidden:
            service.apply(
                "award_learning_reward",
                {"xp": 10, "coins": 5, "reason": "verified", "evidence_id": "mob-001"},
                "pyr",
            )
        self.assertEqual(forbidden.exception.status_code, 403)

        result = service.apply_internal(
            "award_learning_reward",
            {"xp": 10, "coins": 5, "reason": "verified", "evidence_id": "mob-001"},
        )
        self.assertEqual(result["revision"], 5)
        state = self.read(path)
        self.assertEqual(state["player"]["xp"], 20)
        self.assertEqual(state["player"]["coins"], 55)

    def test_internal_hp_and_achievement_commands_are_bounded(self):
        service, path = self.make_service()
        hp = service.apply_internal(
            "player_hp_change",
            {"amount": -9, "reason": "battle_counterattack", "encounter_id": "encounter-001"},
        )
        achievement = service.apply_internal(
            "record_achievement",
            {"achievement_id": "First Blood", "reason": "mob verified", "evidence_id": "mob-001"},
        )
        state = self.read(path)
        self.assertEqual(hp["result"]["hp"], 91)
        self.assertEqual(achievement["result"]["unlocked"], True)
        self.assertEqual(state["player"]["hp"], 91)
        self.assertTrue(state["achievements"][0]["unlocked"])
        self.assertEqual([event["action"] for event in state["state_events"]], ["player_hp_change", "record_achievement"])

    def test_dungeon_checkpoint_survives_service_restart_with_fresh_run_loadout(self):
        service, path = self.make_service()
        before = self.read(path)
        started = service.apply(
            "dungeon_start_run",
            {"concept_id": "lists", "seed": "loop-seed"},
            "player",
        )
        run = started["result"]["run"]
        self.assertTrue(run["active"])
        self.assertEqual(run["floor"], 1)
        self.assertEqual(run["room"], 1)
        self.assertEqual(run["room_type"], "selector")
        self.assertTrue(1 <= len(run["room_choices"]) <= 3)
        self.assertEqual(run["loadout"]["armor"], "Apprentice Coat")
        self.assertIsNone(run["loadout"]["trinket"])
        self.assertEqual(run["loadout"]["heals"], 1)
        self.assertEqual(run["loadout"]["coins"], 0)
        self.assertEqual(run["editor_content"], "")
        self.assertEqual(self.read(path)["player"], before["player"])

        chosen = service.apply(
            "dungeon_choose_room",
            {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in run["room_choices"] if choice["kind"] in {"encounter", "elite"})},
            "player",
        )
        run = chosen["result"]["run"]
        self.assertEqual(run["room_type"], "encounter")
        self.assertIsNotNone(run["question"])
        self.assertTrue(run["encounter"]["name"])
        self.assertTrue(run["encounter"]["category"])
        self.assertIn(run["encounter"]["phase"], {"I", "II", "III"})

        saved = service.apply(
            "dungeon_save_editor",
            {"run_id": run["run_id"], "question_id": run["question"]["id"], "content": "items = ['hit', 'stand']\nprint(items)\n"},
            "player",
        )
        self.assertTrue(saved["result"]["saved"])
        resumed = LocalStateService(path, threading.RLock()).dungeon_projection(
            LocalStateService(path, threading.RLock()).snapshot()
        )
        self.assertEqual(resumed["run_id"], run["run_id"])
        self.assertEqual(resumed["editor_content"], "items = ['hit', 'stand']\nprint(items)\n")
        self.assertEqual(resumed["question"]["concept_id"], "lists")

    def test_dungeon_question_rotation_blanks_editor_and_death_requires_new_run(self):
        service, path = self.make_service()
        started = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "loop-seed"}, "player")
        started_run = started["result"]["run"]
        run_id = started_run["run_id"]
        selected = service.apply("dungeon_choose_room", {"run_id": run_id, "choice_id": next(choice["id"] for choice in started_run["room_choices"] if choice["kind"] in {"encounter", "elite"})}, "player")
        question_id = selected["result"]["run"]["question"]["id"]
        service.apply("dungeon_save_editor", {"run_id": run_id, "question_id": question_id, "content": "tips = 'old'\n"}, "player")

        rotated = service.apply_internal(
            "dungeon_issue_question",
            {
                "run_id": run_id,
                "floor": 1,
                "room": 2,
                "room_type": "encounter",
                "question": {
                    "id": f"{run_id}-q2",
                    "question_type": "bug_hunt",
                    "concept_id": "loops",
                    "difficulty": 2,
                    "prompt": "Find the loop condition that never changes.",
                    "options": [],
                },
            },
        )
        rotated_run = rotated["result"]["run"]
        self.assertEqual(rotated_run["room"], 2)
        self.assertEqual(rotated_run["editor_content"], "")
        self.assertEqual(rotated["event"]["editor_reset"], True)
        self.assertEqual(self.read(path)["dungeon_run"]["editor_content"], "")

        with self.assertRaises(StateCommandError) as stale:
            service.apply(
                "dungeon_save_editor",
                {"run_id": run_id, "question_id": question_id, "content": "late = 'old'\n"},
                "player",
            )
        self.assertEqual(stale.exception.status_code, 409)
        self.assertEqual(self.read(path)["dungeon_run"]["editor_content"], "")

        death = service.apply_internal(
            "dungeon_record_death",
            {"run_id": run_id, "reason": "hp_zero"},
        )
        self.assertFalse(death["result"]["run"]["active"])
        self.assertEqual(death["result"]["run"]["status"], "dead")
        self.assertEqual(death["result"]["run"]["editor_content"], "")
        self.assertIsNone(death["result"]["run"]["question"])

        fresh = service.apply("dungeon_start_run", {"concept_id": "loops"}, "player")
        fresh_run = fresh["result"]["run"]
        self.assertNotEqual(fresh_run["run_id"], run_id)
        self.assertEqual(fresh_run["floor"], 1)
        self.assertEqual(fresh_run["room"], 1)
        self.assertEqual(fresh_run["editor_content"], "")
        self.assertEqual(fresh_run["loadout"]["heals"], 1)

    def test_dungeon_reset_discards_only_active_checkpoint_and_records_event(self):
        service, path = self.make_service()
        started = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "reset-seed"}, "player")
        run_id = started["result"]["run"]["run_id"]
        before = self.read(path)
        reset = service.apply("dungeon_reset_run", {"run_id": run_id}, "player")

        self.assertTrue(reset["changed"])
        self.assertTrue(reset["result"]["reset"])
        self.assertFalse(reset["result"]["run"]["active"])
        self.assertEqual(reset["event"]["reason"], "dungeon_run_reset")
        self.assertTrue(reset["event"]["campaign_untouched"])
        after = self.read(path)
        self.assertIsNone(after["dungeon_run"])
        self.assertEqual(after["player"], before["player"])
        self.assertEqual(after["projects"], before["projects"])
        self.assertEqual(after["state_events"][-1]["action"], "dungeon_reset_run")

    def test_dungeon_questions_reject_hidden_fields_and_active_runs_cannot_reset(self):
        service, _ = self.make_service()
        started = service.apply("dungeon_start_run", {"concept_id": "lists"}, "player")
        run_id = started["result"]["run"]["run_id"]
        with self.assertRaises(StateCommandError) as active:
            service.apply("dungeon_start_run", {"concept_id": "loops"}, "player")
        self.assertEqual(active.exception.status_code, 409)
        with self.assertRaises(StateCommandError) as hidden:
            service.apply_internal(
                "dungeon_issue_question",
                {
                    "run_id": run_id,
                    "question": {
                        "id": f"{run_id}-q2",
                        "question_type": "multiple_choice",
                        "concept_id": "lists",
                        "difficulty": 1,
                        "prompt": "Choose the correct expression.",
                        "options": ["a", "b"],
                        "answer_key": "a",
                    },
                },
            )
        self.assertEqual(hidden.exception.status_code, 422)

    def test_dungeon_verdicts_advance_rooms_without_campaign_rewards_and_support_rest_market_finish(self):
        service, path = self.make_service()
        service.apply("dungeon_start_run", {"concept_id": "lists", "seed": "test-34"}, "player")
        run = self.use_lane_map(service, path)
        run = service.apply(
            "dungeon_choose_room",
            {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in run["room_choices"] if choice["kind"] in {"encounter", "elite"} and choice["id"].endswith("c3"))},
            "player",
        )["result"]["run"]
        initial_player = self.read(path)["player"].copy()

        current = service.dungeon_projection(service.snapshot())
        result = service.apply_internal(
            "dungeon_record_verdict",
            {
                "run_id": run["run_id"],
                "question_id": current["question"]["id"],
                "verdict": "correct",
                "evidence_id": "dungeon-proof-0",
                "reason": "Provider validated the current room",
            },
        )
        self.assertEqual(result["result"]["outcome"], "correct")
        self.assertTrue(result["event"]["mob_name"])

        # The prototype map is intentionally randomized by seed.  Follow the
        # middle lane so this test exercises both market and recovery actions
        # without assuming every row is combat.
        selector = service.dungeon_projection(service.snapshot())
        market = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in selector["room_choices"] if choice["kind"] == "market")}, "player")["result"]["run"]
        self.assertEqual(market["room_type"], "market")
        self.assertTrue(market["market_catalog"])
        state = self.read(path)
        state["dungeon_run"]["run_coins"] = 30
        path.write_text(json.dumps(state), encoding="utf-8")
        purchased = service.apply("dungeon_market_purchase", {"run_id": run["run_id"], "item_id": "dungeon-ward"}, "player")
        self.assertEqual(purchased["result"]["item"]["id"], "dungeon-ward")
        self.assertEqual(purchased["result"]["run"]["loadout"]["armor"], "Ember Ward")
        left = service.apply("dungeon_leave_room", {"run_id": run["run_id"]}, "player")
        self.assertEqual(left["result"]["run"]["room_type"], "selector")

        selector = service.dungeon_projection(service.snapshot())
        rest = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in selector["room_choices"] if choice["kind"] == "rest")}, "player")["result"]["run"]
        self.assertEqual(rest["room_type"], "rest")
        self.assertIsNone(rest["question"])
        state = self.read(path)
        state["dungeon_run"]["loadout"]["hp"] = 40
        path.write_text(json.dumps(state), encoding="utf-8")
        rested = service.apply("dungeon_camp_action", {"run_id": run["run_id"], "action": "rest"}, "player")
        self.assertEqual(rested["result"]["healed"], 30)
        self.assertEqual(rested["result"]["run"]["room_type"], "rest")
        self.assertEqual(rested["result"]["run"]["loadout"]["hp"], 70)
        with self.assertRaises(StateCommandError):
            service.apply("dungeon_camp_action", {"run_id": run["run_id"], "action": "rest"}, "player")
        service.apply("dungeon_leave_room", {"run_id": run["run_id"]}, "player")

        finished = service.apply("dungeon_finish_run", {"run_id": run["run_id"]}, "player")
        self.assertEqual(finished["result"]["run"]["status"], "complete")
        self.assertEqual(self.read(path)["player"], initial_player)
        self.assertTrue(all("answer_key" not in entry for entry in finished["result"]["run"]["history"]))
        self.assertEqual(len(self.read(path)["dungeon_leaderboard"]), 1)
        self.assertEqual(finished["result"]["run"]["leaderboard"][0]["status"], "complete")

    def test_dungeon_verdicts_support_legacy_rest_endpoint(self):
        service, path = self.make_service()
        service.apply("dungeon_start_run", {"concept_id": "lists", "seed": "loop-seed"}, "player")
        run = self.use_lane_map(service, path)
        run = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in run["room_choices"] if choice["kind"] == "encounter")}, "player")["result"]["run"]
        result = service.apply_internal(
            "dungeon_record_verdict",
            {
                "run_id": run["run_id"],
                "question_id": run["question"]["id"],
                "verdict": "correct",
                "evidence_id": "dungeon-proof-rest-compat",
                "reason": "Provider validated the current room",
            },
        )
        selector = service.dungeon_projection(service.snapshot())
        rest = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in selector["room_choices"] if choice["kind"] == "rest")}, "player")["result"]["run"]
        state = self.read(path)
        state["dungeon_run"]["loadout"]["hp"] = 40
        path.write_text(json.dumps(state), encoding="utf-8")
        rested = service.apply("dungeon_use_rest", {"run_id": run["run_id"]}, "player")
        self.assertEqual(rested["result"]["healed"], 30)
        self.assertEqual(rested["result"]["run"]["room_type"], "selector")
        self.assertEqual(rested["result"]["run"]["loadout"]["hp"], 70)

    def test_dungeon_focus_uses_only_recorded_codex_weakness_evidence(self):
        service, path = self.make_service()
        state = self.read(path)
        state["learning_state"]["concept"] = "Fallback concept"
        state["codex"] = {
            "encounters": [
                {
                    "id": "lists-mob",
                    "project_id": "01-blackjack",
                    "mob_name": "The Dealer's Hand",
                    "concept": "Lists and random selection",
                    "results": [{"outcome": "incorrect", "evidence_id": "attempt-1"}],
                    "weaknesses": ["index boundaries"],
                }
            ]
        }
        path.write_text(json.dumps(state), encoding="utf-8")
        started = service.apply("dungeon_start_run", {"seed": "adaptive-seed"}, "player")
        self.assertEqual(started["result"]["run"]["concept_id"], "Lists and random selection")
        self.assertNotIn("answer_key", json.dumps(started["result"]["run"]))

    def test_dungeon_incorrect_verdict_can_end_only_the_run(self):
        service, path = self.make_service()
        started = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "loop-seed"}, "player")
        run = started["result"]["run"]
        run = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in run["room_choices"] if choice["kind"] in {"encounter", "elite"})}, "player")["result"]["run"]
        state = self.read(path)
        state["dungeon_run"]["loadout"]["hp"] = 1
        path.write_text(json.dumps(state), encoding="utf-8")
        result = service.apply_internal(
            "dungeon_record_verdict",
            {
                "run_id": run["run_id"],
                "question_id": run["question"]["id"],
                "verdict": "incorrect",
                "evidence_id": "dungeon-miss-1",
                "reason": "Provider marked the answer incomplete",
            },
        )
        self.assertTrue(result["result"]["run_died"])
        self.assertEqual(result["result"]["run"]["status"], "dead")
        self.assertEqual(result["result"]["run"]["editor_content"], "")
        self.assertIsNone(result["result"]["run"]["question"])

    def test_dungeon_miss_keeps_the_attempt_in_the_editor(self):
        service, path = self.make_service()
        run = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "loop-seed"}, "player")["result"]["run"]
        run = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in run["room_choices"] if choice["kind"] in {"encounter", "elite"})}, "player")["result"]["run"]
        attempt = "# Answer: B\n# Because it looks right\n"
        service.apply("dungeon_save_editor", {"run_id": run["run_id"], "question_id": run["question"]["id"], "content": attempt}, "player")
        result = service.apply_internal(
            "dungeon_record_verdict",
            {"run_id": run["run_id"], "question_id": run["question"]["id"], "verdict": "incorrect", "evidence_id": "dungeon-miss-keep", "reason": "Close, but pop needs an index"},
        )
        self.assertFalse(result["result"]["run_died"])
        self.assertFalse(result["event"]["editor_reset"])
        self.assertEqual(result["result"]["run"]["editor_content"], attempt)
        self.assertEqual(result["result"]["run"]["question"]["id"], run["question"]["id"])

    def practice_answer(self, service, concept, question_type, outcomes):
        started = service.apply("practice_session_started", {"concept": concept, "question_type": question_type, "difficulty": 1}, "player")
        session_id = started["result"]["session"]["session_id"]
        result = None
        for index, outcome in enumerate(outcomes):
            result = service.apply_internal(
                "practice_record_attempt",
                {"session_id": session_id, "outcome": outcome, "evidence_id": f"{session_id}-{index}", "reason": "graded"},
            )
        return result

    def test_hunter_signs_and_stats_grow_from_tutor_answers(self):
        service, path = self.make_service()
        clean = self.practice_answer(service, "Loops & totals", "code_trace", ["correct"])
        self.assertEqual(clean["result"]["hunter_gain"]["signs"], [{"id": "loops", "xp": 3}])
        self.assertEqual(clean["result"]["hunter_gain"]["stats"], {"insight": 2, "vitality": 2})
        recovered = self.practice_answer(service, "Loops & totals", "short_explanation", ["incorrect", "correct"])
        # Recovered (+1) plus a teach-back (+2); Focus grows, Vitality only once a day.
        self.assertEqual(recovered["result"]["hunter_gain"]["signs"], [{"id": "loops", "xp": 3}])
        self.assertEqual(recovered["result"]["hunter_gain"]["stats"], {"focus": 1})
        hunter = service.hunter_projection(self.read(path))
        loops = next(sign for sign in hunter["signs"] if sign["id"] == "loops")
        self.assertEqual((loops["xp"], loops["clean_casts"], loops["recovered"], loops["tutor_passes"], loops["teachbacks"]), (6, 1, 1, 2, 1))
        self.assertEqual(hunter["stats"]["insight"]["xp"], 2)

    def test_hunter_sign_ranks_need_their_gates_and_dulling_keeps_rank_one(self):
        service, path = self.make_service()
        state = self.read(path)
        state["hunter"] = {"signs": {"lists": {"xp": 500, "last_used_at": "2099-01-01T00:00:00+00:00"}}}
        path.write_text(json.dumps(state), encoding="utf-8")
        lists = lambda: next(sign for sign in service.hunter_projection(self.read(path))["signs"] if sign["id"] == "lists")  # noqa: E731
        self.assertEqual((lists()["level"], lists()["rank_name"], lists()["held_by_gate"]), (2, "Uninscribed", True))
        for counters, level, rank in (
            ({"tutor_passes": 1}, 5, "Inscribed"),
            ({"tutor_passes": 1, "clean_casts": 10}, 9, "Honed"),
            ({"tutor_passes": 1, "clean_casts": 10, "campaign_uses": 1, "teachbacks": 1}, 10, "Mastered"),
        ):
            state["hunter"]["signs"]["lists"].update(counters)
            path.write_text(json.dumps(state), encoding="utf-8")
            self.assertEqual((lists()["level"], lists()["rank_name"]), (level, rank))
        # Unused for a week: dull one step, never below rank I.
        state["hunter"]["signs"]["lists"] = {"xp": 15, "tutor_passes": 1, "last_used_at": "2000-01-01T00:00:00+00:00"}
        path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual((lists()["earned_level"], lists()["level"], lists()["dull"]), (3, 3, True))

    def test_hunter_progress_is_seeded_only_from_existing_evidence(self):
        service, path = self.make_service()
        state = self.read(path)
        state.pop("hunter", None)
        state["projects"][0]["mobs"] = [
            {"name": "The Count Keeper", "concept": "Loops and totals", "status": "defeated"},
            {"name": "The Bust Hound", "concept": "Conditionals", "status": "available"},
        ]
        state["practice_sessions"] = [{"session_id": "practice-seed", "concept": "Lists", "question_type": "code_trace", "difficulty": 1, "status": "reviewed", "attempts": 2, "correct": 2, "history": []}]
        path.write_text(json.dumps(state), encoding="utf-8")
        signs = {sign["id"]: sign for sign in service.hunter_projection(self.read(path))["signs"]}
        self.assertEqual((signs["loops"]["xp"], signs["loops"]["campaign_uses"]), (5, 1))
        self.assertEqual((signs["lists"]["xp"], signs["lists"]["clean_casts"], signs["lists"]["tutor_passes"]), (6, 2, 2))
        self.assertEqual(signs["conditionals"]["xp"], 0)
        self.assertNotIn("hunter", self.read(path))  # projecting never writes
        # The first real answer stores the seed plus the new growth.
        self.practice_answer(service, "Loops & totals", "code_trace", ["correct"])
        stored = self.read(path)["hunter"]["signs"]
        self.assertEqual((stored["loops"]["xp"], stored["lists"]["xp"]), (8, 6))

    def test_hunter_stat_points_come_with_levels(self):
        service, path = self.make_service()
        state = self.read(path)
        state["player"]["level"] = 1
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(StateCommandError) as none_yet:
            service.apply("hunter_spend_point", {"stat": "strength"}, "player")
        self.assertEqual(none_yet.exception.status_code, 409)
        state["player"]["level"] = 3
        path.write_text(json.dumps(state), encoding="utf-8")
        spent = service.apply("hunter_spend_point", {"stat": "strength"}, "player")
        self.assertEqual(spent["result"]["hunter"]["stats"]["strength"]["value"], 2)
        self.assertEqual(spent["result"]["hunter"]["free_points"], 1)
        with self.assertRaises(StateCommandError):
            service.apply("hunter_spend_point", {"stat": "luck"}, "player")

    def test_dungeon_clear_after_a_miss_counts_as_recovered(self):
        service, path = self.make_service()
        run = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "loop-seed"}, "player")["result"]["run"]
        run = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": next(choice["id"] for choice in run["room_choices"] if choice["kind"] in {"encounter", "elite"})}, "player")["result"]["run"]
        verdict = {"run_id": run["run_id"], "question_id": run["question"]["id"], "reason": "graded"}
        service.apply_internal("dungeon_record_verdict", {**verdict, "verdict": "incorrect", "evidence_id": "dg-miss"})
        cleared = service.apply_internal("dungeon_record_verdict", {**verdict, "verdict": "correct", "evidence_id": "dg-hit"})
        gain = cleared["result"]["hunter_gain"]
        self.assertTrue(gain["signs"])
        self.assertTrue(all(item["xp"] in {1, 3} for item in gain["signs"]))
        sign = next(item for item in service.hunter_projection(self.read(path))["signs"] if item["id"] == gain["signs"][0]["id"])
        self.assertEqual((sign["recovered"], sign["clean_casts"], sign["dungeon_clean"]), (1, 0, 0))
        self.assertEqual(cleared["result"]["run"]["last_result"]["hunter_gain"], gain)

    def use_lane_map(self, service, path):
        """Pin a run to the legacy three-lane map (tests about room mechanics)."""

        state = self.read(path)
        run = state["dungeon_run"]
        run["map"] = service._dungeon_generate_map(run["seed"], floor=1)
        run.pop("floor_layout", None)
        run["room_choices"] = service._dungeon_route_choices(run)
        path.write_text(json.dumps(state), encoding="utf-8")
        return service.dungeon_projection(self.read(path))

    def enter_dungeon_room(self, service, path, kind, strength=1, insight=1):
        state = self.read(path)
        state["hunter"] = {"signs": {}, "stats_xp": {}, "spent": {"strength": strength - 1, "insight": insight - 1}}
        state["player"]["level"] = max(1, strength + insight - 1)
        path.write_text(json.dumps(state), encoding="utf-8")
        run = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "loop-seed"}, "player")["result"]["run"]
        state = self.read(path)
        node = {"id": "f1-r1-test", "kind": kind, "row": 1, "column": 1, "label": kind}
        state["dungeon_run"]["room_choices"] = [node]
        state["dungeon_run"]["map"]["nodes"] = list(state["dungeon_run"]["map"].get("nodes", [])) + [node]
        path.write_text(json.dumps(state), encoding="utf-8")
        return service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": node["id"]}, "player")["result"]["run"]

    def answer_room(self, service, path, verdict, tag):
        run = self.read(path)["dungeon_run"]
        return service.apply_internal(
            "dungeon_record_verdict",
            {"run_id": run["run_id"], "question_id": run["question"]["id"], "verdict": verdict, "evidence_id": f"dg-{tag}", "reason": "graded"},
        )["result"]

    def test_dungeon_elite_takes_exactly_its_questions_even_with_huge_strength(self):
        service, path = self.make_service()
        run = self.enter_dungeon_room(service, path, "elite", strength=20)
        self.assertEqual(run["encounter"]["fight"]["questions_total"], 3)
        first_question = run["question"]["id"]
        one = self.answer_room(service, path, "correct", "1")
        self.assertFalse(one["fight"]["fight_done"])
        self.assertEqual(one["fight"]["questions_cleared"], 1)
        self.assertEqual(one["run"]["room_type"], "elite")
        self.assertNotEqual(one["run"]["question"]["id"], first_question)
        self.assertTrue(one["fight"]["broke"])  # a huge chip breaks it, but ends nothing
        self.assertEqual(one["coins_delta"], 3)  # only the break bonus before the clear
        two = self.answer_room(service, path, "correct", "2")
        self.assertFalse(two["fight"]["fight_done"])
        three = self.answer_room(service, path, "correct", "3")
        self.assertTrue(three["fight"]["fight_done"])
        self.assertEqual(three["run"]["room_type"], "selector")

    def test_dungeon_break_banks_a_free_mistake_that_absorbs_a_miss(self):
        service, path = self.make_service()
        self.enter_dungeon_room(service, path, "elite", strength=5)
        hit = self.answer_room(service, path, "correct", "hit")
        self.assertTrue(hit["fight"]["broke"])
        self.assertEqual(hit["fight"]["guards"], 1)
        hp_before = self.read(path)["dungeon_run"]["loadout"]["hp"]
        miss = self.answer_room(service, path, "incorrect", "miss")
        self.assertTrue(miss["fight"]["guard_used"])
        self.assertEqual(miss["damage"], 0)
        self.assertEqual(self.read(path)["dungeon_run"]["loadout"]["hp"], hp_before)
        self.assertEqual(miss["fight"]["questions_cleared"], 1)  # a miss never moves progress

    def test_dungeon_boss_self_destruct_fires_on_schedule_and_a_break_interrupts_it(self):
        service, path = self.make_service()
        self.enter_dungeon_room(service, path, "boss")
        # No break: base chip 5 vs 12 Resolve; the countdown of 3 fires on the third answer.
        self.answer_room(service, path, "correct", "b1")
        self.answer_room(service, path, "incorrect", "b2")
        hp_before_third = self.read(path)["dungeon_run"]["loadout"]["hp"]
        third = self.answer_room(service, path, "incorrect", "b3")
        self.assertEqual(third["fight"]["mechanic_fired"], "self_destruct")
        self.assertEqual(third["fight"]["blast"], 15)
        self.assertEqual(self.read(path)["dungeon_run"]["loadout"]["hp"], hp_before_third - third["damage"] - 15)
        self.assertEqual(third["fight"]["questions_cleared"], 1)
        service2, path2 = self.make_service()
        self.enter_dungeon_room(service2, path2, "boss", strength=10)
        broke = self.answer_room(service2, path2, "correct", "s1")
        self.assertTrue(broke["fight"]["broke"])
        self.assertEqual(broke["fight"]["mechanic_countdown"], 3)
        self.assertIsNone(broke["fight"]["mechanic_fired"])

    def test_dungeon_enrage_doubles_counterattacks_and_insight_buys_time(self):
        service, path = self.make_service()
        run = self.enter_dungeon_room(service, path, "elite")
        self.assertEqual(run["encounter"]["fight"]["mechanic"]["every"], 2)
        first = self.answer_room(service, path, "incorrect", "e1")
        second = self.answer_room(service, path, "incorrect", "e2")
        self.assertEqual(second["fight"]["mechanic_fired"], "enrage")
        third = self.answer_room(service, path, "incorrect", "e3")
        self.assertEqual(third["damage"], first["damage"] * 2)
        service2, path2 = self.make_service()
        run = self.enter_dungeon_room(service2, path2, "elite", insight=4)
        self.assertEqual(run["encounter"]["fight"]["mechanic"]["every"], 3)

    def test_vitality_raises_a_new_runs_max_hp(self):
        service, path = self.make_service()
        state = self.read(path)
        state["hunter"] = {"signs": {}, "stats_xp": {"vitality": 20}, "spent": {}}
        path.write_text(json.dumps(state), encoding="utf-8")
        run = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "loop-seed"}, "player")["result"]["run"]
        base = self.read(path)["player"].get("max_hp") or 100
        self.assertEqual(run["loadout"]["max_hp"], base + 10)

    def enter_delve_room(self, service, path, kind, region="collections", trinket=None):
        run = service.apply("dungeon_start_run", {"seed": "delve-seed", "region_id": region}, "player")["result"]["run"]
        state = self.read(path)
        if trinket:
            state["dungeon_run"]["loadout"]["trinket"] = trinket
        node = {"id": "f1-r1-delve", "kind": kind, "row": 1, "column": 1, "label": kind}
        state["dungeon_run"]["room_choices"] = [node]
        state["dungeon_run"]["map"]["nodes"] = list(state["dungeon_run"]["map"].get("nodes", [])) + [node]
        path.write_text(json.dumps(state), encoding="utf-8")
        return service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": node["id"]}, "player")["result"]["run"]

    def test_delve_concepts_map_to_exactly_one_sign(self):
        from ide.server.state import HUNTER_SIGN_CONCEPTS, hunter_signs_for
        for sign_id, concept in HUNTER_SIGN_CONCEPTS.items():
            self.assertEqual(hunter_signs_for(concept), [sign_id])

    def test_delve_elite_still_takes_three_answers_and_drops_parts_and_a_trinket(self):
        service, path = self.make_service()
        run = self.enter_delve_room(service, path, "elite")
        self.assertEqual(run["region"]["id"], "collections")
        self.assertIn(run["question"]["concept_id"], {"lists", "dictionaries", "random selection"})
        self.assertTrue(run["encounter"]["name"].startswith("Elder "))
        one = self.answer_room(service, path, "correct", "d1")
        self.assertIsNone(one["loot"])
        self.answer_room(service, path, "correct", "d2")
        three = self.answer_room(service, path, "correct", "d3")
        self.assertTrue(three["fight"]["fight_done"])
        parts = next(item for item in three["loot"]["items"] if item["id"] != "unmarked-vial")
        self.assertEqual(parts["count"], 3)  # 2 parts + clean bonus
        self.assertEqual(three["loot"]["trinket"]["name"], "Warden Sigil")
        self.assertEqual(three["run"]["loadout"]["trinket"], "Warden Sigil")
        self.assertEqual({item["id"]: item["count"] for item in three["run"]["pack"]}, {parts["id"]: 3, "unmarked-vial": 1})

    def test_delve_pack_banks_on_finish_survives_and_is_lost_on_death(self):
        service, path = self.make_service()
        self.enter_delve_room(service, path, "encounter")
        self.answer_room(service, path, "correct", "p1")
        run = self.read(path)["dungeon_run"]
        finished = service.apply("dungeon_finish_run", {"run_id": run["run_id"]}, "player")["result"]
        self.assertEqual(sum(item["count"] for item in finished["banked"]), 2)
        bank = service.hunter_projection(self.read(path))["materials"]
        self.assertEqual(sum(item["count"] for item in bank), 2)
        sync = service._campaign_source_projection(self.read(path))
        self.assertNotIn("pack", json.dumps(sync.get("dungeon_run") or {}))
        self.assertNotIn("materials", json.dumps(sync))
        service2, path2 = self.make_service()
        self.enter_delve_room(service2, path2, "encounter")
        self.answer_room(service2, path2, "correct", "q1")
        run2 = self.read(path2)["dungeon_run"]
        dead = service2.apply_internal("dungeon_record_death", {"run_id": run2["run_id"], "reason": "fell"})["result"]
        self.assertEqual(sum(item["count"] for item in dead["pack_lost"]), 2)
        self.assertEqual(service2.hunter_projection(self.read(path2))["materials"], [])

    def stock_hunter(self, path, materials, coins=200, oils=None, sign_ranks=None):
        state = self.read(path)
        signs = {}
        for sign_id, rank in (sign_ranks or {}).items():
            # rank 1 = level 3 (15 XP, inscribed); rank 2 = level 6 (48 XP, honed)
            signs[sign_id] = {"xp": 15 if rank == 1 else 48, "tutor_passes": 1, "clean_casts": 10 if rank >= 2 else 0}
        state["hunter"] = {"signs": signs, "stats_xp": {}, "spent": {}, "materials": dict(materials), "oils": dict(oils or {})}
        state["player"]["coins"] = coins
        path.write_text(json.dumps(state), encoding="utf-8")

    def test_crafting_an_oil_spends_parts_and_coins_and_is_rank_gated(self):
        service, path = self.make_service()
        self.stock_hunter(path, {"drowner-link": 5, "cave-essence": 1}, coins=40)
        crafted = service.apply("hunter_craft_oil", {"oil_id": "lists-ward"}, "player")["result"]
        self.assertEqual(crafted["coins"], 30)
        hunter = crafted["hunter"]
        self.assertEqual(hunter["oils"][0]["id"], "lists-ward")
        self.assertEqual(next(item for item in hunter["materials"] if item["id"] == "drowner-link")["count"], 3)
        with self.assertRaises(StateCommandError) as locked:
            service.apply("hunter_craft_oil", {"oil_id": "lists-slowing"}, "player")
        self.assertEqual(locked.exception.status_code, 409)
        self.stock_hunter(path, {"drowner-link": 1}, coins=40)
        with self.assertRaises(StateCommandError):
            service.apply("hunter_craft_oil", {"oil_id": "lists-ward"}, "player")
        self.stock_hunter(path, {"drowner-link": 3, "cave-essence": 1}, coins=40, sign_ranks={"lists": 1})
        slowed = service.apply("hunter_craft_oil", {"oil_id": "lists-slowing"}, "player")["result"]
        self.assertEqual(slowed["coins"], 15)
        self.assertEqual(slowed["hunter"]["materials"], [])

    def test_oils_help_only_their_beast_once_per_fight_and_never_shorten_it(self):
        service, path = self.make_service()
        self.enter_delve_room(service, path, "elite")
        state = self.read(path)
        run = state["dungeon_run"]
        sign = {"lists": "lists", "dictionaries": "dictionaries", "random selection": "random-selection"}[run["question"]["concept_id"]]
        other = "loops"
        state.setdefault("hunter", {"signs": {}, "stats_xp": {}, "spent": {}})["oils"] = {f"{sign}-ward": 1, f"{sign}-slowing": 1, f"{sign}-bane": 1, f"{other}-ward": 1}
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(StateCommandError):
            service.apply("dungeon_apply_oil", {"run_id": run["run_id"], "oil_id": f"{other}-ward"}, "player")
        applied = service.apply("dungeon_apply_oil", {"run_id": run["run_id"], "oil_id": f"{sign}-bane"}, "player")["result"]
        self.assertEqual(applied["run"]["encounter"]["fight"]["oil"]["tier"], "bane")
        self.assertEqual(applied["run"]["encounter"]["sign_id"], sign)
        with self.assertRaises(StateCommandError):
            service.apply("dungeon_apply_oil", {"run_id": run["run_id"], "oil_id": f"{sign}-ward"}, "player")
        one = self.answer_room(service, path, "correct", "o1")
        self.assertEqual(one["fight"]["chip"], 4 + 3)
        self.assertFalse(one["fight"]["fight_done"])
        self.answer_room(service, path, "correct", "o2")
        three = self.answer_room(service, path, "correct", "o3")
        self.assertTrue(three["fight"]["fight_done"])

    def test_ward_and_slowing_oils(self):
        service, path = self.make_service()
        self.enter_delve_room(service, path, "elite")
        state = self.read(path)
        run = state["dungeon_run"]
        sign = {"lists": "lists", "dictionaries": "dictionaries", "random selection": "random-selection"}[run["question"]["concept_id"]]
        state.setdefault("hunter", {"signs": {}, "stats_xp": {}, "spent": {}})["oils"] = {f"{sign}-slowing": 1}
        path.write_text(json.dumps(state), encoding="utf-8")
        slowed = service.apply("dungeon_apply_oil", {"run_id": run["run_id"], "oil_id": f"{sign}-slowing"}, "player")["result"]
        self.assertEqual(slowed["run"]["encounter"]["fight"]["mechanic"]["countdown"], 4)
        service2, path2 = self.make_service()
        self.enter_delve_room(service2, path2, "encounter")
        state = self.read(path2)
        run = state["dungeon_run"]
        sign = {"lists": "lists", "dictionaries": "dictionaries", "random selection": "random-selection"}[run["question"]["concept_id"]]
        state.setdefault("hunter", {"signs": {}, "stats_xp": {}, "spent": {}})["oils"] = {f"{sign}-ward": 1, f"{sign}-slowing": 1}
        path2.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(StateCommandError):
            service2.apply("dungeon_apply_oil", {"run_id": run["run_id"], "oil_id": f"{sign}-slowing"}, "player")
        warded = service2.apply("dungeon_apply_oil", {"run_id": run["run_id"], "oil_id": f"{sign}-ward"}, "player")["result"]
        self.assertEqual(warded["run"]["encounter"]["fight"]["guards"], 1)
        self.assertEqual(warded["hunter"]["oils"], [{"id": f"{sign}-slowing", "sign": sign, "tier": "slowing", "name": warded["hunter"]["oils"][0]["name"], "effect": warded["hunter"]["oils"][0]["effect"], "count": 1}])

    def test_identify_snippets_print_what_their_answer_says(self):
        import contextlib
        import io
        from ide.server.state import HUNTER_BEASTS, _identify_snippet
        for sign_id in HUNTER_BEASTS:
            for seed in range(40):
                puzzle = _identify_snippet(sign_id, f"seed-{seed}")
                self.assertEqual(len(set(puzzle["options"])), 4, (sign_id, puzzle["options"]))
                self.assertEqual(puzzle["options"][puzzle["answer"]], puzzle["answer_text"])
                if sign_id == "random-selection":
                    continue
                code = puzzle["prompt"].split("```python\n", 1)[1].rsplit("\n```", 1)[0]
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    exec(code, {})
                self.assertEqual(out.getvalue().strip(), puzzle["answer_text"], (sign_id, code))

    def test_kit_upgrades_spend_essence_and_carry_into_every_delve(self):
        service, path = self.make_service()
        self.stock_hunter(path, {"village-essence": 1, "cave-essence": 1, "keep-essence": 1}, coins=200)
        coat = service.apply("hunter_upgrade_kit", {"track": "coat"}, "player")["result"]
        self.assertEqual(coat["coins"], 160)
        service.apply("hunter_upgrade_kit", {"track": "satchel"}, "player")
        service.apply("hunter_upgrade_kit", {"track": "blade"}, "player")
        with self.assertRaises(StateCommandError):
            service.apply("hunter_upgrade_kit", {"track": "coat"}, "player")  # level 2 needs 2 essences
        run = service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "kit-seed"}, "player")["result"]["run"]
        base = self.read(path)["player"].get("max_hp") or 100
        self.assertEqual(run["loadout"]["max_hp"], base + 8)
        self.assertEqual(run["loadout"]["bandages"], 2)
        service.apply("dungeon_reset_run", {"run_id": run["run_id"]}, "player")
        self.enter_delve_room(service, path, "elite")
        hit = self.answer_room(service, path, "correct", "k1")
        self.assertEqual(hit["fight"]["chip"], 4 + 1)

    def test_identify_a_vial_by_reading_code(self):
        from ide.server.app_v2 import _without_identify_answer
        service, path = self.make_service()
        self.stock_hunter(path, {})
        with self.assertRaises(StateCommandError):
            service.apply("hunter_identify_start", {}, "player")
        self.stock_hunter(path, {"unmarked-vial": 1})
        started = service.apply("hunter_identify_start", {}, "player")["result"]["hunter"]
        puzzle = started["identify"]
        self.assertNotIn("answer", puzzle)
        self.assertEqual(started["vials"], 1)
        stored = self.read(path)["hunter"]["identify"]
        self.assertNotIn("answer", json.dumps(_without_identify_answer(self.read(path))["hunter"]["identify"]))
        wrong = (stored["answer"] + 1) % 4
        missed = service.apply("hunter_identify_answer", {"puzzle_id": puzzle["id"], "choice": wrong}, "player")["result"]
        self.assertFalse(missed["correct"])
        self.assertEqual(missed["answer"], stored["answer_text"])
        self.assertEqual(missed["hunter"]["vials"], 1)  # a miss never costs the vial
        self.assertNotEqual(missed["hunter"]["identify"]["id"], puzzle["id"])
        stored = self.read(path)["hunter"]["identify"]
        right = service.apply("hunter_identify_answer", {"puzzle_id": stored["id"], "choice": stored["answer"]}, "player")["result"]
        self.assertTrue(right["correct"])
        self.assertEqual(right["oil"]["id"], f"{stored['sign']}-{stored['tier']}")
        self.assertEqual(right["hunter"]["vials"], 0)
        self.assertIsNone(right["hunter"]["identify"])
        self.assertEqual(right["hunter"]["oils"][0]["id"], right["oil"]["id"])
        self.assertTrue(right["hunter_gain"]["signs"])

    def test_grid_floors_are_connected_and_well_formed(self):
        from ide.server.state import LocalStateService
        for seed in range(150):
            for floor, modifier in ((1, None), (3, "deep"), (2, "quiet")):
                grid = LocalStateService._dungeon_generate_grid(f"g{seed}", floor, modifier=modifier, region_id="flow")
                nodes = {node["id"]: node for node in grid["nodes"]}
                edges = grid["edges"]
                self.assertLessEqual(len(nodes), 64)
                self.assertTrue(all(1 <= node["row"] <= 4 and 1 <= node["column"] <= 5 for node in nodes.values()))
                for key, values in edges.items():
                    for value in values:
                        self.assertIn(key, edges[value])  # doors go both ways
                start = grid["current_node_id"]
                seen, queue = {start}, [start]
                while queue:
                    for other in edges[queue.pop()]:
                        if other not in seen:
                            seen.add(other)
                            queue.append(other)
                self.assertEqual(seen, set(nodes))
                kinds = [node["type"] for node in nodes.values()]
                boss = next(node_id for node_id, node in nodes.items() if node["type"] == "boss")
                self.assertNotIn(boss, edges[start])
                self.assertGreaterEqual(kinds.count("encounter"), 3)
                self.assertGreaterEqual(kinds.count("rest"), 2)
                self.assertTrue(any(nodes[other]["type"] in {"encounter", "elite"} for other in edges[start]))
                self.assertEqual(nodes[boss]["label"], "The Endless Warden")

    def walk_floor(self, service, path, rng):
        """Clear every room to the boss with travel thrown in; return stairs."""

        for _ in range(80):
            run = service.dungeon_projection(self.read(path))
            self.assertLessEqual(len(run["room_choices"]), 3)
            kind = run["room_type"]
            if kind in {"encounter", "elite", "boss"}:
                self.answer_room(service, path, "correct", f"w{rng.random()}")
                continue
            if kind in {"rest", "market"}:
                service.apply("dungeon_leave_room", {"run_id": run["run_id"]}, "player")
                continue
            if kind == "mystery":
                state = self.read(path)
                state["dungeon_run"]["room_type"] = "selector"
                state["dungeon_run"]["room_choices"] = service._dungeon_route_choices(state["dungeon_run"])
                path.write_text(json.dumps(state), encoding="utf-8")
                continue
            choices = run["room_choices"]
            if choices and choices[0]["kind"] == "stairs":
                return choices
            if rng.random() < 0.3 and len(run["visited_node_ids"]) > 1:
                service.apply("dungeon_travel", {"run_id": run["run_id"], "node_id": rng.choice(run["visited_node_ids"])}, "player")
                continue
            if not choices:
                # Dead end: walk back to an explored room that still has an unexplored door.
                state = self.read(path)
                route = state["dungeon_run"]["map"]
                visited = set(route["visited_node_ids"])
                target = next(node for node in route["visited_node_ids"] if any(other not in visited for other in route["edges"][node]))
                service.apply("dungeon_travel", {"run_id": run["run_id"], "node_id": target}, "player")
                continue
            service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": rng.choice(choices)["id"]}, "player")
        self.fail("floor was never cleared")

    def test_a_grid_floor_can_be_walked_to_the_boss_and_down_the_stairs(self):
        import random as _random
        for seed in ("walk-a", "walk-b", "walk-c"):
            service, path = self.make_service()
            state = self.read(path)
            state["hunter"] = {"signs": {}, "stats_xp": {}, "spent": {"strength": 19}}
            state["player"]["level"] = 20
            path.write_text(json.dumps(state), encoding="utf-8")
            service.apply("dungeon_start_run", {"seed": seed, "region_id": "basics"}, "player")
            stairs = self.walk_floor(service, path, _random.Random(seed))
            self.assertEqual([choice["label"] for choice in stairs][:2], ["Descend", "Deep stair"])
            region_stair = next(choice for choice in stairs if choice["id"].startswith("stairs-region-"))
            run = self.read(path)["dungeon_run"]
            room_before = run["room"]
            down = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": region_stair["id"]}, "player")["result"]["run"]
            self.assertEqual(down["floor"], 2)
            self.assertEqual(down["room_type"], "rest")
            self.assertEqual(down["region"]["id"], "collections")
            self.assertEqual(down["map"]["layout"], "grid")
            self.assertGreater(down["room"], room_before)
            self.assertEqual(down["pack"], [])  # the camp at the bottom banks it

    def test_walking_back_to_a_camp_is_inert_and_death_still_takes_the_pack(self):
        service, path = self.make_service()
        service.apply("dungeon_start_run", {"seed": "inert", "region_id": "basics"}, "player")
        run = self.read(path)["dungeon_run"]
        start = run["map"]["current_node_id"]
        fight = next(choice for choice in run["room_choices"] if choice["kind"] in {"encounter", "elite"})
        service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": fight["id"]}, "player")
        while self.read(path)["dungeon_run"]["room_type"] in {"encounter", "elite"}:
            self.answer_room(service, path, "correct", f"i{self.read(path)['dungeon_run']['question_number']}")
        self.assertTrue(self.read(path)["dungeon_run"]["pack"])
        back = service.apply("dungeon_travel", {"run_id": run["run_id"], "node_id": start}, "player")["result"]["run"]
        self.assertEqual(back["room_type"], "selector")
        self.assertTrue(back["pack"])
        with self.assertRaises(StateCommandError):
            service.apply("dungeon_travel", {"run_id": run["run_id"], "node_id": fight["id"].replace("-c", "-x")}, "player")
        dead = service.apply_internal("dungeon_record_death", {"run_id": run["run_id"], "reason": "fell"})["result"]
        self.assertTrue(dead["pack_lost"])

    def test_a_legacy_run_stuck_at_its_beaten_boss_is_offered_stairs(self):
        service, path = self.make_service()
        service.apply("dungeon_start_run", {"concept_id": "loops", "seed": "legacy"}, "player")
        state = self.read(path)
        run = state["dungeon_run"]
        lanes = service._dungeon_generate_map(run["seed"], floor=1)
        boss = next(node for node in lanes["nodes"] if node["type"] == "boss")
        lanes["current_node_id"] = boss["id"]
        lanes["visited_node_ids"].append(boss["id"])
        run.update({"map": lanes, "room_type": "selector", "room_choices": []})
        run.pop("floor_layout", None)
        path.write_text(json.dumps(state), encoding="utf-8")
        projected = service.dungeon_projection(self.read(path))
        self.assertEqual([choice["kind"] for choice in projected["room_choices"]], ["stairs"] * 3)
        down = service.apply("dungeon_choose_room", {"run_id": run["run_id"], "choice_id": projected["room_choices"][0]["id"]}, "player")["result"]["run"]
        self.assertEqual((down["floor"], down["map"]["layout"]), (2, "grid"))

    def test_grid_fog_hides_unexplored_rooms(self):
        service, path = self.make_service()
        run = service.apply("dungeon_start_run", {"seed": "fog", "region_id": "flow"}, "player")["result"]["run"]
        full = self.read(path)["dungeon_run"]["map"]
        shown = {node["id"] for node in run["map"]["nodes"]}
        start = full["current_node_id"]
        boss = next(node["id"] for node in full["nodes"] if node["type"] == "boss")
        self.assertEqual(shown, {start, boss, *full["edges"][start]})
        self.assertLess(len(shown), len(full["nodes"]))
        self.assertTrue(all(set(values) <= shown for values in run["map"]["edges"].values()))

    def test_warden_sigil_starts_each_fight_with_a_free_mistake(self):
        service, path = self.make_service()
        run = self.enter_delve_room(service, path, "elite", trinket="Warden Sigil")
        self.assertEqual(run["encounter"]["fight"]["guards"], 1)

    def test_campaign_mob_never_falls_before_its_last_objective(self):
        service, path = self.make_service()
        service.apply_internal("record_battle_objective", {"objective_id": "table_setup", "evidence_id": "mob-000-warmup", "reason": "Verified"})
        state = self.read(path)
        # As if a bonus impact had landed: Resolve is low but both objectives remain.
        state["encounter_state"]["completed_objectives"] = []
        state["encounter_state"]["resolve"] = 2
        path.write_text(json.dumps(state), encoding="utf-8")
        first = service.apply_internal("record_battle_objective", {"objective_id": "table_setup", "evidence_id": "mob-000-table", "reason": "Verified"})
        # Emptying the bar early is a Guard Break: a free mistake, and Resolve
        # becomes what the remaining objective removes.
        self.assertEqual(first["result"]["guard_break"]["guards"], 1)
        self.assertEqual(first["result"]["resolve_after"], 2)
        self.assertFalse(first["result"]["mob_defeated"])
        last = service.apply_internal("record_battle_objective", {"objective_id": "state_explanation", "evidence_id": "mob-000-state", "reason": "Verified"})
        self.assertTrue(last["result"]["mob_defeated"])

    def test_practice_history_is_independent_and_provider_validated(self):
        service, path = self.make_service()
        before = self.read(path)
        started = service.apply(
            "practice_session_started",
            {"concept": "lists", "question_type": "bug_hunt", "difficulty": 3},
            "player",
        )
        session = started["result"]["session"]
        self.assertEqual(session["status"], "requested")
        recorded = service.apply_internal(
            "practice_record_attempt",
            {
                "session_id": session["session_id"],
                "outcome": "correct",
                "evidence_id": "practice-proof-1",
                "reason": "Provider validated the boundary explanation",
            },
        )
        self.assertEqual(recorded["result"]["session"]["correct"], 1)
        after = self.read(path)
        self.assertEqual(after["player"], before["player"])
        self.assertNotIn("dungeon_run", after)
        self.assertNotIn("answer", json.dumps(after["practice_sessions"]))
        self.assertEqual([event["action"] for event in after["state_events"]], ["practice_session_started", "practice_record_attempt"])
        self.assertEqual(service.practice_projection(after)["count"], 1)

    def test_learning_event_cannot_change_progression_fields_outside_its_scope(self):
        service, path = self.make_service()
        before = self.read(path)
        service.apply(
            "record_learning_event",
            {"kind": "review", "evidence_id": "review-001", "reason": "Reviewed a branch"},
            "pyr",
        )
        after = self.read(path)
        self.assertEqual(after["player"], before["player"])
        self.assertEqual(after["assist"], before["assist"])
        self.assertEqual(after["stats"], before["stats"])
        self.assertEqual(after["activity"], before["activity"])

    def test_bad_payload_and_dev_activity_action_are_rejected(self):
        service, _ = self.make_service()
        bad_payloads = [
            {"kind": "teachback", "evidence_id": "bad", "reason": "ok", "path": "player.xp"},
            {"kind": "teachback", "evidence_id": "bad", "reason": 12},
        ]
        for payload in bad_payloads:
            with self.assertRaises(StateCommandError) as error:
                service.apply("record_learning_event", payload, "pyr")
            self.assertEqual(error.exception.status_code, 422)
        with self.assertRaises(StateCommandError) as activity:
            service.apply("update_dev_activity", {"activity_score": 9999}, "player")
        self.assertEqual(activity.exception.status_code, 422)

    def test_concurrent_learning_events_have_unique_serial_revisions(self):
        service, path = self.make_service()

        def apply(index: int) -> int:
            result = service.apply(
                "record_learning_event",
                {"kind": "session", "evidence_id": f"concurrent-{index}", "reason": "bounded test event"},
                "pyr",
            )
            return result["revision"]

        with ThreadPoolExecutor(max_workers=8) as pool:
            revisions = list(pool.map(apply, range(20)))
        state = self.read(path)
        self.assertEqual(sorted(revisions), list(range(5, 25)))
        self.assertEqual(state["meta"]["revision"], 24)
        self.assertEqual(len(state["state_events"]), 20)

    def test_homestead_actions_use_shared_service(self):
        service, path = self.make_service()
        purchase = service.apply("homestead_purchase", {"item_id": "cursor-golden-spark"}, "player")
        equip = service.apply("homestead_equip", {"item_id": "cursor-golden-spark"}, "player")
        state = self.read(path)
        self.assertEqual(purchase["revision"], 5)
        self.assertEqual(equip["revision"], 6)
        self.assertEqual(state["player"]["coins"], 40)
        self.assertEqual(state["homestead"]["equipped"]["cursor"], "cursor-golden-spark")
        self.assertEqual([event["action"] for event in state["state_events"]], ["homestead_purchase", "homestead_equip"])

    def test_campaign_market_purchase_enters_home_inventory(self):
        service, path = self.make_service()
        state = self.read(path)
        state["player"]["coins"] = 200
        state["homestead"]["market_purchases"] = []
        state["equipment"] = {
            "armor": "Apprentice Coat",
            "trinket": "None",
            "title": "Apprentice Coder",
            "owned_armor": ["armor-apprentice-coat"],
            "owned_trinkets": ["trinket-none"],
        }
        path.write_text(json.dumps(state), encoding="utf-8")

        trinket = service.apply("campaign_market_purchase", {"item_id": "syntax-ward"}, "player")
        supply = service.apply("campaign_market_purchase", {"item_id": "field-bandage"}, "player")
        after = self.read(path)

        self.assertTrue(trinket["changed"])
        self.assertTrue(supply["changed"])
        self.assertEqual(after["player"]["coins"], 134)
        self.assertIn("syntax-ward", after["equipment"]["owned_trinkets"])
        self.assertEqual(after["supplies"]["bandages"], 1)
        self.assertEqual(after["homestead"]["market_purchases"], ["syntax-ward", "field-bandage"])
        duplicate = service.apply("campaign_market_purchase", {"item_id": "syntax-ward"}, "player")
        self.assertFalse(duplicate["changed"])
        self.assertEqual(self.read(path)["meta"]["revision"], 6)

    def test_homestead_room_upgrade_uses_authored_catalog_and_migrates_first_token(self):
        service, path = self.make_service()
        built = service.apply("homestead_room_upgrade", {"upgrade_id": "reinforced-hearth"}, "player")
        state = self.read(path)

        self.assertTrue(built["changed"])
        self.assertEqual(built["revision"], 5)
        self.assertEqual(built["result"]["upgrade"]["id"], "reinforced-hearth")
        self.assertEqual(state["homestead"]["room_upgrades"], ["reinforced-hearth"])
        self.assertEqual(state["homestead"]["upgrade_tokens"], 0)
        self.assertEqual(state["player"]["max_hp"], 110)
        self.assertEqual(state["player"]["hp"], 110)
        self.assertEqual(state["state_events"][-1]["action"], "homestead_room_upgrade")

        duplicate = service.apply("homestead_room_upgrade", {"upgrade_id": "reinforced-hearth"}, "player")
        self.assertFalse(duplicate["changed"])
        self.assertEqual(self.read(path)["meta"]["revision"], 5)

    def test_homestead_room_upgrade_rejects_unknown_and_unaffordable_builds(self):
        service, path = self.make_service()
        with self.assertRaises(StateCommandError) as unknown:
            service.apply("homestead_room_upgrade", {"upgrade_id": "not-a-room"}, "player")
        self.assertEqual(unknown.exception.status_code, 404)

        state = self.read(path)
        state["homestead"]["upgrade_tokens"] = 0
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(StateCommandError) as unaffordable:
            service.apply("homestead_room_upgrade", {"upgrade_id": "reinforced-hearth"}, "player")
        self.assertEqual(unaffordable.exception.status_code, 409)
        self.assertEqual(self.read(path)["meta"]["revision"], 4)

    def test_homestead_actions_match_prototype_recovery_supply_and_pyr_loop(self):
        service, path = self.make_service()
        state = self.read(path)
        state["player"].update({"hp": 70, "max_hp": 100, "potions": 1})
        state["supplies"] = {"bandages": 1, "tonics": 0, "meals": 1}
        state["companion"] = {"name": "PYR", "form": "Tiny Code-Flame", "level": 1, "bond": 0}
        path.write_text(json.dumps(state), encoding="utf-8")

        bandage = service.apply("homestead_action", {"action": "bandage"}, "player")
        self.assertEqual(bandage["result"]["healed"], 20)
        self.assertEqual(self.read(path)["supplies"]["bandages"], 0)
        self.assertEqual(self.read(path)["player"]["potions"], 0)

        meal = service.apply("homestead_action", {"action": "meal"}, "player")
        self.assertEqual(meal["result"]["healed"], 10)
        self.assertEqual(self.read(path)["supplies"]["meals"], 0)

        with self.assertRaises(StateCommandError) as no_meals:
            service.apply("homestead_action", {"action": "feed_pyr"}, "player")
        self.assertEqual(no_meals.exception.status_code, 409)

        train = service.apply("homestead_action", {"action": "train_pyr"}, "player")
        self.assertEqual(train["result"]["companion"]["bond"], 1)
        self.assertEqual(self.read(path)["companion"]["energy"], 1)
        self.assertEqual(self.read(path)["state_events"][-1]["action"], "homestead_action")

    def test_hearth_cost_and_emergency_recovery(self):
        service, path = self.make_service()
        state = self.read(path)
        state["player"].update({"hp": 40, "max_hp": 100, "coins": 6})
        path.write_text(json.dumps(state), encoding="utf-8")
        result = service.apply("homestead_action", {"action": "recover"}, "player")
        self.assertEqual((self.read(path)["player"]["hp"], self.read(path)["player"]["coins"]), (100, 0))
        self.assertEqual(result["result"]["coins_spent"], 6)
        state = self.read(path)
        state["player"].update({"hp": 10, "max_hp": 101, "coins": 0})
        path.write_text(json.dumps(state), encoding="utf-8")
        free = service.apply("homestead_action", {"action": "recover"}, "player")
        self.assertEqual((free["result"]["hp"], free["result"]["coins_spent"]), (31, 0))
        with self.assertRaises(StateCommandError):
            service.apply("homestead_action", {"action": "recover"}, "player")
        self.assertEqual(self.read(path)["player"]["hp"], 31)

    def test_boss_retreat_resets_progress_and_locks_home_and_practice(self):
        service, path = self.make_service()
        state = self.read(path)
        project = state["projects"][0]
        service._extend_campaign(state)
        for mob in project["mobs"]:
            mob["status"] = "defeated"
        project.update({"boss_status": "available", "progress": 100})
        path.write_text(json.dumps(state), encoding="utf-8")
        service.apply("boss_start", {}, "player")
        self.assertTrue(service.encounter_projection(self.read(path))["boss_active"])
        active_projection, _ = service.sync_snapshot()
        active_validated = service._validate_sync_projection(active_projection)
        self.assertTrue(service._boss_is_active({"projects": active_validated["campaign"]["projects"]}))
        with self.assertRaises(StateCommandError):
            service.apply("homestead_action", {"action": "recover"}, "player")
        with self.assertRaises(StateCommandError):
            service.apply("practice_session_started", {"concept": "Loops", "question_type": "code_trace", "difficulty": 1}, "player")
        phase = service.encounter_projection(self.read(path))["boss_phase"]
        service.apply_internal("record_boss_requirement", {"requirement_id": phase, "evidence_id": "test-evidence", "reason": "valid"})
        damaged = service.encounter_projection(self.read(path))
        self.assertLess(damaged["boss_resolve"], damaged["boss_max_resolve"])
        service.apply("boss_retreat", {}, "player")
        reset = service.encounter_projection(self.read(path))
        self.assertFalse(reset["boss_active"])
        self.assertEqual(reset["boss_resolve"], reset["boss_max_resolve"])
        self.assertEqual(reset["verified_boss_requirements"], [])
        # The marker uses the existing bounded sync schema and survives projection.
        projection, _ = service.sync_snapshot()
        validated = service._validate_sync_projection(projection)
        self.assertTrue(validated["campaign"]["projects"][0]["boss_validation"]["history"])
        service.apply("boss_start", {}, "player")
        self.assertTrue(service.encounter_projection(self.read(path))["boss_active"])

    def test_boss_retreat_cannot_farm_the_phase_heal(self):
        service, path = self.make_service()
        state = self.read(path)
        project = state["projects"][0]
        project.update({"branch": "00-lantern-vale", "boss": "The Unwritten King", "boss_status": "available", "progress": 100})
        service._extend_campaign(state)
        for mob in project["mobs"]:
            mob["status"] = "defeated"
        state["player"]["hp"] = 50
        path.write_text(json.dumps(state), encoding="utf-8")
        for attempt in range(2):
            service.apply("boss_start", {}, "player")
            for phase in ("required_behavior", "explanation", "edge_cases"):
                service.apply_internal("record_boss_requirement", {"requirement_id": phase, "evidence_id": f"heal-{attempt}-{phase}", "reason": "verified"})
            self.assertEqual(self.read(path)["player"]["hp"], 58)
            service.apply("boss_retreat", {}, "player")

    def test_avatar_appearance_is_validated_projected_and_synced(self):
        service, path = self.make_service()
        self.assertEqual(service.equipment_projection(self.read(path))["avatar"]["hair_style"], "hooded")

        changed = service.apply("set_avatar", {"hair_style": "twists", "outfit": "crimson", "facial_hair": "full_beard", "hair_color": "honey", "beard_color": "silver"}, "player")
        self.assertTrue(changed["changed"])
        avatar = self.read(path)["equipment"]["avatar"]
        self.assertEqual((avatar["hair_style"], avatar["outfit"], avatar["skin"]), ("twists", "crimson", "deep"))
        self.assertEqual(service.equipment_projection(self.read(path))["avatar"]["outfit"], "crimson")

        self.assertEqual((avatar["facial_hair"], avatar["hair_color"], avatar["beard_color"]), ("full_beard", "honey", "silver"))
        for bad in ({"hair_style": "glowing"}, {"wings": "yes"}, {"facial_hair": "lumberjack"}):
            with self.assertRaises(StateCommandError):
                service.apply("set_avatar", bad, "player")

        projection, _metadata = service.sync_snapshot()
        self.assertEqual(projection["equipment"]["avatar"]["hair_style"], "twists")
        with self.assertRaises(StateCommandError):
            service._validate_sync_projection({"equipment": {"avatar": {"skin": "neon"}}})

    def test_campaign_loadout_only_equips_state_owned_gear(self):
        service, path = self.make_service()
        state = self.read(path)
        state["equipment"] = {
            "armor": "Apprentice Coat",
            "trinket": "None",
            "title": "Apprentice Coder",
            "owned_armor": ["armor-apprentice-coat"],
            "owned_trinkets": ["trinket-none"],
        }
        path.write_text(json.dumps(state), encoding="utf-8")

        unlocked = service.apply_internal(
            "record_equipment_unlock",
            {
                "item_id": "armor-leather-guard",
                "evidence_id": "gear-proof-1",
                "reason": "The validated reward history unlocked Leather Guard",
            },
        )
        self.assertEqual(unlocked["result"]["item"]["name"], "Leather Guard")
        projection = service.equipment_projection(service.snapshot())
        armor_slot = next(slot for slot in projection["slots"] if slot["id"] == "armor")
        self.assertEqual([item["name"] for item in armor_slot["items"]], ["Apprentice Coat", "Leather Guard"])
        self.assertTrue(armor_slot["items"][0]["equipped"])

        equipped = service.apply("equip_equipment", {"item_id": "armor-leather-guard"}, "player")
        self.assertTrue(equipped["changed"])
        self.assertEqual(equipped["result"]["item"]["name"], "Leather Guard")
        self.assertEqual(self.read(path)["equipment"]["armor"], "Leather Guard")
        self.assertEqual(self.read(path)["state_events"][-1]["action"], "equip_equipment")

        with self.assertRaises(StateCommandError) as locked:
            service.apply("equip_equipment", {"item_id": "armor-runic-mail"}, "player")
        self.assertEqual(locked.exception.status_code, 409)

    def test_codex_projection_exposes_generic_pages_and_note_action_is_bounded(self):
        service, path = self.make_service()
        state = self.read(path)
        state["codex"] = {
            "encounters": [
                {
                    "id": "blackjack-lists",
                    "project_id": "01-blackjack",
                    "mob_name": "The Dealer's Hand",
                    "concept": "Lists and random selection",
                    "status": "defeated",
                    "question_types": ["prediction"],
                    "weaknesses": ["indexing"],
                    "notes": ["Validated collection reasoning"],
                    "code_snippet": "cards = ['hit', 'stand']\nfor card in cards:\n    print(card)",
                    "attempts": 2,
                    "results": [{"outcome": "defeated", "evidence_id": "mob-1", "answer_key": "secret"}],
                    "interview_history": [],
                    "mastery": {"evidence": 1, "interview_passes": 0, "shield": "none"},
                }
            ]
        }
        path.write_text(json.dumps(state), encoding="utf-8")
        projection = service.codex_projection(service.snapshot())
        lists_page = next(page for page in projection["pages"] if page["id"] == "lists")
        self.assertIn("blackjack-lists", lists_page["encounter_ids"])
        self.assertTrue(lists_page["common_mistakes"])
        self.assertTrue(lists_page["check_prompt"])
        self.assertEqual(projection["entries"][0]["page_id"], "lists")
        self.assertIn("for card in cards", projection["entries"][0]["code_snippet"])
        self.assertNotIn("answer_key", projection["entries"][0]["results"][0])

        saved = service.apply("record_codex_note", {"entry_id": "blackjack-lists", "note": "Revisit indexing tomorrow."}, "player")
        self.assertTrue(saved["changed"])
        self.assertEqual(saved["revision"], 5)
        updated = self.read(path)
        self.assertEqual(updated["codex"]["encounters"][0]["player_notes"], ["Revisit indexing tomorrow."])
        self.assertEqual(updated["state_events"][-1]["action"], "record_codex_note")
        self.assertEqual(updated["state_events"][-1]["note_count"], 1)

        duplicate = service.apply("record_codex_note", {"entry_id": "blackjack-lists", "note": "Revisit indexing tomorrow."}, "player")
        self.assertFalse(duplicate["changed"])
        with self.assertRaises(StateCommandError):
            service.apply("record_codex_note", {"entry_id": "blackjack-lists", "note": "\u0000bad"}, "player")

    def test_verified_objectives_reduce_resolve_and_complete_mob_with_codex_projection(self):
        service, path = self.make_service()
        first = service.apply_internal(
            "record_battle_objective",
            {"objective_id": "table_setup", "evidence_id": "mob-000-table", "reason": "Verified table state explanation", "code_snippet": "table = []\ntable.append('hit')"},
        )
        state = self.read(path)
        self.assertEqual(first["result"]["resolve_before"], 4)
        self.assertEqual(first["result"]["resolve_after"], 2)
        self.assertFalse(first["result"]["mob_defeated"])
        self.assertEqual(state["encounter_state"]["resolve"], 2)
        self.assertEqual(state["state_events"][-1]["impact"], 2)

        second = service.apply_internal(
            "record_battle_objective",
            {"objective_id": "state_explanation", "evidence_id": "mob-000-state", "reason": "Verified state boundary", "code_snippet": "table = []\nfor card in cards:\n    table.append(card)"},
        )
        state = self.read(path)
        self.assertTrue(second["result"]["mob_defeated"])
        self.assertEqual(second["result"]["reward_xp"], 25)
        self.assertEqual(second["result"]["reward_coins"], 10)
        self.assertEqual(state["player"]["xp"], 35)
        self.assertEqual(state["player"]["coins"], 60)
        self.assertEqual(state["stats"]["mobs_defeated"], 1)
        self.assertEqual(state["projects"][0]["mobs"][0]["status"], "defeated")
        self.assertEqual(state["projects"][0]["mobs"][1]["status"], "available")
        self.assertEqual(state["encounter_state"]["status"], "defeated")
        self.assertEqual(state["codex"]["encounters"][0]["status"], "defeated")
        self.assertEqual(state["codex"]["encounters"][0]["attempts"], 2)
        self.assertIn("for card in cards", state["codex"]["encounters"][0]["code_snippet"])
        self.assertTrue(next(item for item in state["achievements"] if item["name"] == "First Blood")["unlocked"])

    def test_bounded_trinket_triggers_are_state_service_owned(self):
        service, path = self.make_service()
        state = self.read(path)
        state["equipment"] = {"armor": "Apprentice Coat", "trinket": "Ember Scythe", "title": "Apprentice Coder"}
        path.write_text(json.dumps(state), encoding="utf-8")

        result = service.apply_internal(
            "record_battle_objective",
            {"objective_id": "table_setup", "evidence_id": "trinket-1", "reason": "Verified the table state"},
        )
        self.assertEqual(result["result"]["impact"], 3)
        self.assertEqual(result["result"]["base_impact"], 2)
        self.assertEqual(result["result"]["bonus_impact"], 1)
        self.assertEqual(result["result"]["trinket_trigger"], "Ember Scythe")
        self.assertEqual(self.read(path)["state_events"][-1]["trinket_trigger"], "Ember Scythe")

        state = self.read(path)
        state["equipment"]["trinket"] = "Guardian Sigil"
        state["player"]["hp"] = 20
        path.write_text(json.dumps(state), encoding="utf-8")
        miss = service.apply_internal(
            "record_battle_miss",
            {
                "objective_id": "state_explanation",
                "encounter_id": "trinket-encounter",
                "evidence_id": "trinket-miss",
                "reason": "The submitted explanation was incomplete",
            },
        )
        self.assertEqual(miss["result"]["damage"], 0)
        self.assertEqual(miss["result"]["prevented_damage"], 6)
        self.assertEqual(miss["result"]["trinket_trigger"], "Guardian Sigil")
        self.assertEqual(self.read(path)["player"]["hp"], 20)

        state = self.read(path)
        state["equipment"]["trinket"] = "Phoenix Ember"
        state["player"]["hp"] = 1
        path.write_text(json.dumps(state), encoding="utf-8")
        revive = service.apply_internal(
            "record_battle_miss",
            {
                "objective_id": "state_explanation",
                "encounter_id": "trinket-revive",
                "evidence_id": "trinket-revive",
                "reason": "The second submission was incomplete",
            },
        )
        self.assertTrue(revive["result"]["revived"])
        self.assertEqual(revive["result"]["trinket_trigger"], "Phoenix Ember")
        self.assertEqual(self.read(path)["player"]["hp"], 1)

    def test_boss_phase_verification_is_persisted_without_revealing_prompts(self):
        service, path = self.make_service()
        state = self.read(path)
        project = state["projects"][0]
        project.update({"boss": "The House", "boss_status": "available", "progress": 100})
        project["mobs"] = [{"name": "The Count Keeper", "status": "defeated", "concept": "Loops"}]
        path.write_text(json.dumps(state), encoding="utf-8")

        phase = service.apply_internal(
            "record_boss_requirement",
            {"requirement_id": "required_behavior", "evidence_id": "boss-phase-1", "reason": "The required behaviour was verified"},
        )
        self.assertTrue(phase["changed"])
        self.assertEqual(phase["result"]["boss_phase"], "explanation")
        self.assertEqual(phase["result"]["boss_damage"], 5)
        self.assertEqual(phase["result"]["boss_resolve_before"], 15)
        self.assertEqual(phase["result"]["boss_resolve_after"], 10)
        self.assertEqual(phase["result"]["verified_boss_requirements"], ["required_behavior"])
        self.assertEqual(phase["result"]["remaining_boss_requirements"], ["explanation", "edge_cases", "interview"])
        projection = service.encounter_projection(self.read(path))
        self.assertEqual(projection["status"], "boss_available")
        self.assertEqual(projection["verified_boss_requirements"], ["required_behavior"])
        self.assertEqual(projection["boss_resolve"], 10)
        self.assertEqual(projection["boss_max_resolve"], 15)
        self.assertEqual(projection["boss_current_requirement"]["id"], "explanation")
        self.assertEqual(projection["boss_current_requirement"]["damage"], 2)
        self.assertEqual(projection["boss_current_requirement"]["question_type"], "snippet_check")
        self.assertEqual(projection["current_quest"]["id"], "explanation")
        self.assertEqual(projection["current_quest"]["quest"], projection["boss_current_requirement"]["quest"])
        self.assertEqual([item["id"] for item in projection["mechanics"]], ["execution_gate", "bug_feedback", "verified_goal"])
        self.assertEqual(projection["reward_envelope"]["xp"], 100)
        self.assertIn("boss_lore", projection)
        self.assertNotIn("prompt", projection)
        duplicate = service.apply_internal(
            "record_boss_requirement",
            {"requirement_id": "required_behavior", "evidence_id": "boss-phase-1", "reason": "Duplicate provider retry"},
        )
        self.assertFalse(duplicate["changed"])

        with self.assertRaises(StateCommandError) as out_of_order:
            service.apply_internal(
                "record_boss_requirement",
                {"requirement_id": "interview", "evidence_id": "boss-phase-skip", "reason": "Skipped the current goal"},
            )
        self.assertEqual(out_of_order.exception.status_code, 409)

    def test_cleared_board_without_stored_boss_status_accepts_boss_verdicts(self):
        # A cloud-synced save can drop boss_status even though every mob is
        # cleared; the projection already reports the boss as available, so
        # the verdict gate must agree instead of answering 409.
        service, path = self.make_service()
        state = self.read(path)
        project = state["projects"][0]
        project.update({"boss": "The House", "progress": 100})
        project.pop("boss_status", None)
        project["mobs"] = [{"name": "The Count Keeper", "status": "defeated", "concept": "Loops"}]
        path.write_text(json.dumps(state), encoding="utf-8")
        self.assertEqual(service.encounter_projection(self.read(path))["status"], "boss_available")

        phase = service.apply_internal(
            "record_boss_requirement",
            {"requirement_id": "required_behavior", "evidence_id": "boss-phase-1", "reason": "Verified behaviour"},
        )
        self.assertTrue(phase["changed"])
        self.assertEqual(self.read(path)["projects"][0]["boss_status"], "available")

        locked = self.read(path)
        locked["projects"][0]["mobs"][0]["status"] = "available"
        locked["projects"][0].pop("boss_status", None)
        path.write_text(json.dumps(locked), encoding="utf-8")
        with self.assertRaises(StateCommandError) as unresolved:
            service.apply_internal(
                "record_boss_requirement",
                {"requirement_id": "explanation", "evidence_id": "boss-phase-2", "reason": "Too early"},
            )
        self.assertEqual(unresolved.exception.status_code, 409)

    def test_final_mob_opens_boss_gate_and_verified_boss_clear_awards_canonical_progression(self):
        service, path = self.make_service()
        state = self.read(path)
        project = state["projects"][0]
        project.update({"boss": "The House", "clean_clear_eligible": True})
        project["mobs"] = [{"name": "The Empty Table", "status": "available", "concept": "Variables"}]
        state["achievements"].extend(
            [
                {"name": "Housebreaker", "unlocked": False},
                {"name": "Clean Clear", "unlocked": False},
            ]
        )
        state["goals"] = {"long_term": [{"id": "first-boss", "done": False}]}
        state["companion"] = {
            "name": "PYR",
            "form": "Tiny Code-Flame",
            "level": 1,
            "bond": 0,
            "next_form": "Ember Sprite",
            "next_form_requirement": "Defeat your first project boss",
        }
        path.write_text(json.dumps(state), encoding="utf-8")

        service.apply_internal(
            "record_battle_objective",
            {"objective_id": "table_setup", "evidence_id": "boss-mob-1", "reason": "Explained the table state"},
        )
        gate = service.apply_internal(
            "record_battle_objective",
            {"objective_id": "state_explanation", "evidence_id": "boss-mob-2", "reason": "Explained the state boundary"},
        )
        self.assertTrue(gate["result"]["mob_defeated"])
        self.assertTrue(gate["result"]["boss_unlocked"])
        self.assertEqual(gate["result"]["boss_status"], "available")
        self.assertEqual(service.encounter_projection(self.read(path))["status"], "boss_available")

        cleared = service.apply_internal(
            "record_boss_clear",
            {
                "evidence_id": "boss-behavior-1",
                "explanation_evidence_id": "boss-explain-1",
                "interview_evidence_id": "boss-interview-1",
                "reason": "Required behavior works and the player passed the short interview",
            },
        )
        self.assertTrue(cleared["result"]["boss_defeated"])
        self.assertTrue(cleared["result"]["project_completed"])
        self.assertEqual(cleared["result"]["reward_xp"], 100)
        self.assertEqual(cleared["result"]["reward_coins"], 0)
        after = self.read(path)
        self.assertEqual(after["player"]["xp"], 35)
        self.assertEqual(after["player"]["lifetime_xp"], 150)
        self.assertEqual(after["player"]["coins"], 60)
        self.assertEqual(after["stats"]["mobs_defeated"], 1)
        self.assertEqual(after["stats"]["projects_cleared"], 1)
        self.assertEqual(after["stats"]["bosses_defeated"], 1)
        self.assertEqual(after["stats"]["clean_clears"], 1)
        self.assertTrue(after["projects"][0]["completed"])
        self.assertEqual(after["projects"][0]["boss_status"], "defeated")
        self.assertTrue(next(item for item in after["achievements"] if item["name"] == "Housebreaker")["unlocked"])
        self.assertTrue(next(item for item in after["achievements"] if item["name"] == "Clean Clear")["unlocked"])
        self.assertTrue(after["goals"]["long_term"][0]["done"])
        self.assertEqual(after["companion"]["form"], "Ember Sprite")
        self.assertEqual(after["companion"]["level"], 2)
        self.assertEqual(after["companion"]["next_form"], "Runic Familiar")
        self.assertEqual(after["state_events"][-1]["action"], "record_boss_clear")
        self.assertTrue(after["state_events"][-1]["project_completed"])
        self.assertEqual(service.encounter_projection(after)["status"], "complete")

    def test_boss_clear_opens_the_next_project_with_a_seeded_bounty_board(self):
        service, path = self.make_service()
        state = self.read(path)
        first = state["projects"][0]
        first.update({"order": 1, "branch": "01-blackjack", "boss": "The House", "boss_status": "available"})
        first["mobs"] = [{"name": "The Empty Table", "status": "defeated", "concept": "Variables"}]
        skipped = {"order": 0, "branch": "05-dungeon-crawler", "name": "The Deep Crawler", "status": "available", "boss": "Die Tozza van Zamalek", "progress": 0}
        upcoming = {"order": 2, "branch": "04-casino-slots", "name": "The Silver Reels", "status": "available", "boss": "Ekse Ouens P Diddy", "progress": 0}
        state["projects"] = [skipped, first, upcoming]
        path.write_text(json.dumps(state), encoding="utf-8")

        cleared = service.apply_internal(
            "record_boss_clear",
            {"evidence_id": "b1", "explanation_evidence_id": "b2", "interview_evidence_id": "b3", "reason": "Boss beaten"},
        )
        self.assertEqual(cleared["result"]["next_project"]["name"], "The Silver Reels")
        self.assertFalse(cleared["result"]["campaign_complete"])
        after = self.read(path)
        by_branch = {item["branch"]: item for item in after["projects"]}
        self.assertEqual(by_branch["01-blackjack"]["status"], "completed")
        casino = by_branch["04-casino-slots"]
        self.assertEqual(casino["status"], "active")
        self.assertEqual(casino["entry_file"], "casino.py")
        self.assertEqual(len(casino["mobs"]), 8)
        self.assertEqual([mob["status"] for mob in casino["mobs"]], ["available"] + ["locked"] * 7)
        self.assertIn("Ekse Ouens P Diddy", after["current_quest"])
        # A fresh board means a fresh encounter, not an instantly open boss gate.
        projection = service.encounter_projection(after)
        self.assertEqual(projection["project_name"], "The Silver Reels")
        self.assertNotEqual(projection["status"], "boss_available")

        # Clearing the last project ahead wraps back to the skipped one.
        casino_done = self.read(path)
        for item in casino_done["projects"]:
            if item["branch"] == "04-casino-slots":
                item["mobs"] = [dict(mob, status="defeated") for mob in item["mobs"]]
                item["boss_status"] = "available"
        path.write_text(json.dumps(casino_done), encoding="utf-8")
        wrapped = service.apply_internal(
            "record_boss_clear",
            {"evidence_id": "c1", "explanation_evidence_id": "c2", "interview_evidence_id": "c3", "reason": "Second boss"},
        )
        self.assertEqual(wrapped["result"]["next_project"]["name"], "The Deep Crawler")

    def test_select_campaign_switches_project_and_keeps_the_old_board(self):
        service, path = self.make_service()
        state = self.read(path)
        first = state["projects"][0]
        first.update({"order": 1, "branch": "01-blackjack", "name": "Blackjack", "boss": "The House", "progress": 40})
        first["mobs"] = [{"name": "The Empty Table", "status": "defeated", "concept": "Variables"}, {"name": "Bust", "status": "available", "concept": "Conditionals"}]
        casino = {"order": 2, "branch": "04-casino-slots", "name": "The Silver Reels", "status": "available", "boss": "Ekse Ouens P Diddy", "progress": 0}
        cleared = {"order": 0, "branch": "00-rps-tournament", "name": "Rock Paper Scissors Tournament", "status": "completed", "boss": "The Pattern Warden"}
        state["projects"] = [cleared, first, casino]
        path.write_text(json.dumps(state), encoding="utf-8")

        switched = service.apply("select_campaign", {"branch": "04-casino-slots"}, "player")
        self.assertEqual(switched["result"]["project"]["name"], "The Silver Reels")
        self.assertEqual(switched["event"]["previous_project_id"], "01-blackjack")
        after = {item["branch"]: item for item in self.read(path)["projects"]}
        self.assertEqual(after["04-casino-slots"]["status"], "active")
        self.assertEqual(after["04-casino-slots"]["entry_file"], "casino.py")
        self.assertEqual([mob["status"] for mob in after["04-casino-slots"]["mobs"]], ["available"] + ["locked"] * 7)
        # The project left behind keeps its board and progress.
        self.assertEqual(after["01-blackjack"]["status"], "available")
        self.assertEqual(after["01-blackjack"]["progress"], 40)
        self.assertEqual([mob["status"] for mob in after["01-blackjack"]["mobs"]], ["defeated", "available"])
        self.assertEqual(service.encounter_projection(self.read(path))["project_name"], "The Silver Reels")

        # Switching back resumes it; selecting the active one is a no-op.
        back = service.apply("select_campaign", {"branch": "01-blackjack"}, "player")
        self.assertEqual([mob["status"] for mob in {i["branch"]: i for i in self.read(path)["projects"]}["01-blackjack"]["mobs"]], ["defeated", "available"])
        self.assertTrue(back["changed"])
        self.assertFalse(service.apply("select_campaign", {"branch": "01-blackjack"}, "player")["changed"])

        for branch, status in (("00-rps-tournament", 409), ("99-nope", 404), ("../escape", 422)):
            with self.assertRaises(StateCommandError) as refused:
                service.apply("select_campaign", {"branch": branch}, "player")
            self.assertEqual(refused.exception.status_code, status)

    def test_approved_legacy_reconciliation_restores_only_reviewed_fields_and_is_idempotent(self):
        service, path = self.make_service()
        state = self.read(path)
        state["current_quest"] = "Blackjack — PYR teaches the next needed concept, then you enter Forge phase and implement it from scratch."
        state["last_session"] = "Forge RPG Shell and Homestead were approved as the next IDE evolution. No learning rewards or purchases were claimed."
        state["player"].update({"level": 1, "xp": 0, "xp_next": 100, "lifetime_xp": 0, "coins": 0})
        state["projects"][0]["mobs"] = [
            {"name": "The Empty Table", "status": "available", "concept": "Variables, input/output and basic program state"},
            {"name": "The Dealer's Hand", "status": "locked", "concept": "Lists and random selection"},
            {"name": "The Count Keeper", "status": "locked", "concept": "Loops and totals"},
            {"name": "The Hitman", "status": "locked", "concept": "Input loops and control flow"},
        ]
        state["projects"][0]["progress"] = 0
        state["goals"] = {
            "daily": [{"id": "first-deal", "done": False}, {"id": "explain-lists", "done": False}],
            "weekly": [{"id": "two-mobs", "target": 2, "progress": 0, "done": False}],
        }
        path.write_text(json.dumps(state), encoding="utf-8")

        payload = {
            "evidence_id": "legacy-blackjack-2026-09-14",
            "source": "questlab-blackjack-session-2026-09-14",
            "reason": "Approved reconciliation of the legacy report and session notes",
            "level": 2,
            "xp": 50,
            "xp_next": 100,
            "lifetime_xp": 150,
            "coins": 55,
            "defeated_mobs": ["The Empty Table", "The Dealer's Hand", "The Count Keeper"],
            "project_progress": 38,
            "sessions": 1,
            "explanations": 3,
            "streak_current": 1,
            "streak_longest": 1,
            "streak_last_active": "2026-09-14",
            "streak_days_logged": ["2026-09-14"],
            "daily_goal_ids": ["first-deal", "explain-lists"],
            "weekly_goal_progress": [{"id": "two-mobs", "progress": 2}],
            "current_quest": "Blackjack — Mob 3: The Hitman (repeatedly choose hit or stand).",
            "last_session": "Cleared Mob 0, Mob 1, and Mob 2 cleanly. Approaching Mob 3.",
        }

        result = service.apply_internal("reconcile_legacy_progress", payload)
        after = self.read(path)
        self.assertTrue(result["changed"])
        self.assertEqual(result["revision"], 5)
        self.assertEqual(after["player"]["level"], 2)
        self.assertEqual(after["player"]["xp"], 50)
        self.assertEqual(after["player"]["lifetime_xp"], 150)
        self.assertEqual(after["player"]["coins"], 55)
        self.assertEqual(after["stats"]["mobs_defeated"], 3)
        self.assertEqual(after["projects"][0]["progress"], 38)
        self.assertEqual([mob["status"] for mob in after["projects"][0]["mobs"]], ["defeated", "defeated", "defeated", "available"])
        self.assertEqual(after["encounter_state"]["mob_name"], "The Hitman")
        self.assertEqual(after["encounter_state"]["resolve"], 8)
        self.assertEqual(after["encounter_state"]["max_resolve"], 8)
        self.assertEqual([entry["mob_name"] for entry in after["codex"]["encounters"]], ["The Empty Table", "The Dealer's Hand", "The Count Keeper"])
        self.assertTrue(all(entry["status"] == "defeated" and entry["attempts"] == 0 for entry in after["codex"]["encounters"]))
        self.assertTrue(next(item for item in after["achievements"] if item["name"] == "First Blood")["unlocked"])
        self.assertEqual(after["learning_state"]["phase"], "forge")
        self.assertEqual(after["streak"]["current"], 1)
        self.assertTrue(next(item for item in after["goals"]["daily"] if item["id"] == "first-deal")["done"])
        self.assertTrue(next(item for item in after["goals"]["weekly"] if item["id"] == "two-mobs")["done"])
        self.assertFalse(result["result"]["reward_history_inferred"])
        self.assertEqual(after["state_events"][-1]["action"], "reconcile_legacy_progress")

        repeated = service.apply_internal("reconcile_legacy_progress", payload)
        self.assertFalse(repeated["changed"])
        self.assertEqual(repeated["revision"], 5)
        self.assertEqual(self.read(path)["meta"]["revision"], 5)

    def test_legacy_reconciliation_refuses_non_default_player_conflicts(self):
        service, path = self.make_service()
        state = self.read(path)
        state["player"]["xp"] = 20
        path.write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaises(StateCommandError) as conflict:
            service.apply_internal(
                "reconcile_legacy_progress",
                {
                    "evidence_id": "legacy-conflict",
                    "source": "legacy-session",
                    "reason": "reviewed evidence",
                    "level": 2,
                    "xp": 50,
                    "lifetime_xp": 150,
                    "coins": 55,
                    "defeated_mobs": ["The Empty Table"],
                    "project_progress": 12,
                },
            )
        self.assertEqual(conflict.exception.status_code, 409)
        self.assertEqual(self.read(path)["player"]["xp"], 20)

    def test_battle_objective_is_internal_and_duplicate_objective_is_bounded(self):
        service, _ = self.make_service()
        with self.assertRaises(StateCommandError) as forbidden:
            service.apply("record_battle_objective", {"objective_id": "table_setup", "evidence_id": "x", "reason": "x"}, "pyr")
        self.assertEqual(forbidden.exception.status_code, 403)
        service.apply_internal("record_battle_objective", {"objective_id": "table_setup", "evidence_id": "x", "reason": "x"})
        with self.assertRaises(StateCommandError) as duplicate:
            service.apply_internal("record_battle_objective", {"objective_id": "table_setup", "evidence_id": "y", "reason": "y"})
        self.assertEqual(duplicate.exception.status_code, 409)

    def test_legacy_report_is_read_only_and_surfaces_candidate_differences(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo" / "progress.json"
            workspace = Path(directory) / "workspace" / "progress.json"
            root.parent.mkdir()
            workspace.parent.mkdir()
            canonical = fixture_progress()
            legacy = fixture_progress()
            legacy["player"]["level"] = 2
            legacy["player"]["xp"] = 50
            legacy["stats"]["mobs_defeated"] = 3
            root.write_text(json.dumps(canonical), encoding="utf-8")
            workspace.write_text(json.dumps(legacy), encoding="utf-8")
            report = legacy_state_report(root, workspace)
        self.assertTrue(report["legacy_present"])
        self.assertFalse(report["legacy_authoritative"])
        self.assertTrue(report["manual_approval_required"])
        self.assertEqual({item["field"] for item in report["differences"]}, {"level", "xp", "mobs_defeated"})

    def test_sync_projection_is_allowlisted_and_preserves_local_learning_data(self):
        service, path = self.make_service()
        state = self.read(path)
        state["equipment"] = {"armor": "leather-guard", "trinket": "spark", "secret": "local"}
        state["companion"] = {"name": "PYR", "form": "Tiny Code-Flame", "level": 2, "bond": 3}
        state["homestead"]["purchase_history"] = [{"item_id": "cursor-basic"}]
        state["codex"] = {"encounters": [{"mob_name": "The Empty Table", "player_notes": ["Review indexing before the next encounter."]}]}
        state["skills"] = [{"concept": "Variables", "shield": {"tier": "bronze"}}]
        service.persist(state)

        projection, metadata = service.sync_snapshot()
        self.assertEqual(metadata["revision"], 5)
        self.assertEqual(projection["player"]["coins"], 50)
        self.assertEqual(projection["equipment"]["armor"], "leather-guard")
        self.assertNotIn("secret", projection["equipment"])
        self.assertEqual(projection["companion"]["bond"], 3)
        self.assertNotIn("purchase_history", projection["homestead"])
        self.assertNotIn("catalog", projection["homestead"])
        self.assertEqual(projection["campaign"]["codex"]["encounters"][0]["mob_name"], "The Empty Table")
        self.assertEqual(projection["campaign"]["codex"]["encounters"][0]["player_notes"], ["Review indexing before the next encounter."])
        self.assertEqual(projection["campaign"]["skills"][0]["concept"], "Variables")
        self.assertEqual(projection["campaign"]["projects"][0]["progress"], 0)
        self.assertNotIn("state_events", projection["campaign"])
        self.assertNotIn("activity", projection["campaign"])
        self.assertNotIn("shop", projection["campaign"])

    def test_valid_cloud_projection_bumps_revision_and_keeps_non_sync_domains(self):
        service, path = self.make_service()
        state = self.read(path)
        state["codex"] = {"encounters": [{"mob_name": "local note"}]}
        state["learning_state"]["last_teachback"] = {"prompt": "local-only evidence"}
        state["projects"][0]["progress"] = 42
        path.write_text(json.dumps(state), encoding="utf-8")
        result = service.apply_cloud_projection(
            {
                "player": {"level": 2, "xp": 4, "xp_next": 100, "coins": 75, "hp": 88, "max_hp": 100},
                "equipment": {"armor": "leather-guard"},
                "companion": {"name": "PYR", "level": 2},
                "homestead": {"owned_cosmetics": ["cursor-basic", "hud-forge"], "equipped": {"cursor": "cursor-basic"}},
            },
            expected_revision=4,
            cloud_revision=8,
        )
        after = self.read(path)
        self.assertTrue(result["changed"])
        self.assertEqual(result["revision"], 5)
        self.assertEqual(result["cloud_revision"], 8)
        self.assertEqual(after["player"]["coins"], 75)
        self.assertEqual(after["equipment"]["armor"], "leather-guard")
        self.assertEqual(after["homestead"]["owned_cosmetics"], ["cursor-basic", "hud-forge"])
        self.assertEqual(after["codex"]["encounters"][0]["mob_name"], "local note")
        self.assertEqual(after["learning_state"]["last_teachback"], {"prompt": "local-only evidence"})
        self.assertEqual(after["projects"][0]["progress"], 42)
        self.assertEqual(after["state_events"][-1]["action"], "sync_apply_cloud")

    def test_campaign_projection_applies_validated_codex_projects_and_dungeon_checkpoint(self):
        service, path = self.make_service()
        result = service.apply_cloud_projection(
            {
                "player": {"level": 2, "xp": 50, "xp_next": 100, "lifetime_xp": 150, "coins": 55, "hp": 100, "max_hp": 100},
                "campaign": {
                    "projects": [{
                        "branch": "01-blackjack",
                        "name": "Blackjack",
                        "status": "active",
                        "progress": 38,
                        "mobs": [
                            {"name": "The Empty Table", "status": "defeated", "concept": "Variables"},
                            {"name": "The Hitman", "status": "available", "resolve": 8, "max_resolve": 8},
                        ],
                    }],
                    "current_quest": "Blackjack - Mob 3: The Hitman",
                    "codex": {"encounters": [{"id": "legacy-empty-table", "project_id": "01-blackjack", "mob_name": "The Empty Table", "concept": "Variables", "status": "defeated", "player_notes": ["Review indexing before the next encounter."], "code_snippet": "score = 0\nscore += 1", "results": [{"outcome": "defeated", "evidence_id": "legacy-1"}]}]},
                    "dungeon_run": {
                        "status": "active",
                        "run_id": "dungeon-1",
                        "floor": 1,
                        "room": 2,
                        "room_type": "encounter",
                        "editor_content": "answer = 1",
                        "question": {"id": "q-1", "question_type": "code_checkpoint", "concept_id": "variables", "difficulty": 1, "prompt": "Use a variable.", "options": []},
                    },
                },
            },
            expected_revision=4,
            cloud_revision=11,
        )
        after = self.read(path)
        self.assertTrue(result["changed"])
        self.assertEqual(result["revision"], 5)
        self.assertEqual(after["player"]["coins"], 55)
        self.assertEqual(after["projects"][0]["progress"], 38)
        self.assertEqual(after["projects"][0]["mobs"][1]["resolve"], 8)
        self.assertEqual(after["codex"]["encounters"][0]["mob_name"], "The Empty Table")
        self.assertEqual(after["codex"]["encounters"][0]["player_notes"], ["Review indexing before the next encounter."])
        self.assertEqual(after["codex"]["encounters"][0]["code_snippet"], "score = 0\nscore += 1")
        self.assertEqual(after["dungeon_run"]["run_id"], "dungeon-1")
        self.assertEqual(after["state_events"][-1]["action"], "sync_apply_cloud")

    def test_campaign_projection_rejects_unknown_or_answer_bearing_fields(self):
        service, path = self.make_service()
        before = self.read(path)
        invalid = [
            {"campaign": {"projects": [{"name": "Blackjack", "future_reward": 99}]}},
            {"campaign": {"dungeon_run": {"status": "active", "question": {"id": "q-1", "answer_key": "secret"}}}},
            {"campaign": {"codex": {"encounters": [{"id": "x", "prompt": "do not copy"}]}}},
        ]
        for projection in invalid:
            with self.assertRaises(StateCommandError):
                service.apply_cloud_projection(projection, expected_revision=4, cloud_revision=2)
        self.assertEqual(self.read(path), before)

    def test_cloud_projection_rejects_stale_revision_unknown_fields_and_invalid_equipment(self):
        service, path = self.make_service()
        before = self.read(path)
        with self.assertRaises(StateCommandError) as stale:
            service.apply_cloud_projection({"player": {"coins": 99}}, expected_revision=3, cloud_revision=2)
        self.assertEqual(stale.exception.status_code, 409)
        self.assertEqual(self.read(path), before)

        invalid = [
            {"player": {"coins": 99, "secret": True}},
            {"player": {"xp": 100, "xp_next": 100}},
            {"player": {"xp": 100}},
            {"player": {"hp": 101}},
            {"homestead": {"owned_cosmetics": ["cursor-basic"], "equipped": {"cursor": "hud-forge"}}},
            {"unknown": {}},
        ]
        for projection in invalid:
            with self.assertRaises(StateCommandError):
                service.apply_cloud_projection(projection, expected_revision=4, cloud_revision=2)
        self.assertEqual(self.read(path), before)


class StateGatewayHttpTests(unittest.TestCase):
    def test_boss_question_from_abandoned_attempt_is_not_cached(self):
        project = {"name": "Test"}
        goal = {"id": "explanation", "question_type": "snippet_check"}
        before = {"project_id": "test", "boss_attempt_id": "attempt-1"}
        after = {"project_id": "test", "boss_attempt_id": "attempt-2"}
        key = "boss:test:explanation"
        written = {"prompt": "Question?", "options": ["a", "b"], "answer": 0}
        with patch.object(app_v2, "_boss_choice_goal", side_effect=[(project, before, goal, key), (project, after, goal, key)]), patch.object(app_v2, "_ai_call", return_value=written), patch.object(app_v2, "_studied_ideas", return_value=[]):
            with self.assertRaises(app_v2.HTTPException) as rejected:
                app_v2.ai_boss_question()
        self.assertEqual(rejected.exception.status_code, 409)
        self.assertNotIn(key, app_v2.BOSS_QUESTIONS)

    def with_temp_progress(self):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "progress.json"
        path.write_text(json.dumps(fixture_progress()), encoding="utf-8")
        self.addCleanup(directory.cleanup)
        original = app_v2.PROGRESS_PATH
        app_v2.PROGRESS_PATH = path
        self.addCleanup(setattr, app_v2, "PROGRESS_PATH", original)
        return path

    def client(self):
        return TestClient(app_v2.app, base_url="http://127.0.0.1")

    def with_split_state_paths(self):
        directory = tempfile.TemporaryDirectory()
        root = Path(directory.name) / "repo"
        workspace = Path(directory.name) / "workspace"
        root.mkdir()
        workspace.mkdir()
        canonical = root / "progress.json"
        legacy = workspace / "progress.json"
        canonical.write_text(json.dumps(fixture_progress()), encoding="utf-8")
        legacy_value = fixture_progress()
        legacy_value["player"]["level"] = 99
        legacy_value["player"]["coins"] = 9999
        legacy.write_text(json.dumps(legacy_value), encoding="utf-8")
        original_root = app_v2.PROGRESS_PATH
        original_workspace = app_v2.WORKSPACE
        app_v2.PROGRESS_PATH = canonical
        app_v2.WORKSPACE = workspace
        self.addCleanup(setattr, app_v2, "PROGRESS_PATH", original_root)
        self.addCleanup(setattr, app_v2, "WORKSPACE", original_workspace)
        self.addCleanup(directory.cleanup)
        return canonical, legacy

    def test_valid_command_and_forbidden_payloads_over_http(self):
        path = self.with_temp_progress()
        client = self.client()
        response = client.post(
            "/api/state/apply",
            headers={"host": "127.0.0.1"},
            json={
                "action": "record_learning_event",
                "actor": "pyr",
                "payload": {"kind": "teachback", "evidence_id": "http-001", "reason": "validated"},
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["revision"], 5)

        reward = client.post(
            "/api/state/apply",
            headers={"host": "127.0.0.1"},
            json={
                "action": "award_learning_reward",
                "actor": "pyr",
                "payload": {"xp": 10, "coins": 5, "reason": "no", "evidence_id": "http-002"},
            },
        )
        self.assertEqual(reward.status_code, 403)
        arbitrary = client.post(
            "/api/state/apply",
            headers={"host": "127.0.0.1"},
            json={"action": "record_learning_event", "actor": "pyr", "payload": {"path": "player.xp", "value": 999}},
        )
        self.assertEqual(arbitrary.status_code, 422)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["player"]["xp"], 10)

    def test_legacy_reconciliation_is_internal_only_over_http(self):
        self.with_temp_progress()
        client = self.client()
        response = client.post(
            "/api/state/apply",
            headers={"host": "127.0.0.1"},
            json={
                "action": "reconcile_legacy_progress",
                "actor": "pyr",
                "payload": {},
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_boss_clear_is_internal_only_over_http(self):
        self.with_temp_progress()
        client = self.client()
        response = client.post(
            "/api/state/apply",
            headers={"host": "127.0.0.1"},
            json={
                "action": "record_boss_clear",
                "actor": "pyr",
                "payload": {
                    "evidence_id": "boss-behavior",
                    "explanation_evidence_id": "boss-explanation",
                    "interview_evidence_id": "boss-interview",
                    "reason": "validated",
                },
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_existing_homestead_routes_delegate_to_gateway(self):
        path = self.with_temp_progress()
        client = self.client()
        purchase = client.post(
            "/api/homestead/purchase",
            headers={"host": "127.0.0.1"},
            json={"item_id": "cursor-golden-spark"},
        )
        self.assertEqual(purchase.status_code, 200)
        self.assertEqual(purchase.json()["revision"], 5)
        equip = client.post(
            "/api/homestead/equip",
            headers={"host": "127.0.0.1"},
            json={"item_id": "cursor-golden-spark"},
        )
        self.assertEqual(equip.status_code, 200)
        self.assertEqual(equip.json()["revision"], 6)
        state = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(state["homestead"]["equipped"]["cursor"], "cursor-golden-spark")

    def test_campaign_loadout_route_returns_revisioned_projection(self):
        path = self.with_temp_progress()
        state = json.loads(path.read_text(encoding="utf-8"))
        state["equipment"] = {
            "armor": "Apprentice Coat",
            "trinket": "None",
            "title": "Apprentice Coder",
            "owned_armor": ["armor-apprentice-coat", "armor-leather-guard"],
            "owned_trinkets": ["trinket-none"],
        }
        path.write_text(json.dumps(state), encoding="utf-8")
        client = self.client()
        response = client.post(
            "/api/equipment/equip",
            headers={"host": "127.0.0.1"},
            json={"item_id": "armor-leather-guard"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["revision"], 5)
        armor_slot = next(slot for slot in body["equipment_projection"]["slots"] if slot["id"] == "armor")
        self.assertEqual(armor_slot["equipped"], "Leather Guard")
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["equipment"]["armor"], "Leather Guard")

    def test_codex_routes_use_canonical_revision_and_player_note_boundary(self):
        path = self.with_temp_progress()
        state = json.loads(path.read_text(encoding="utf-8"))
        state["codex"] = {"encounters": [{"id": "blackjack-table", "project_id": "01-blackjack", "mob_name": "The Empty Table", "concept": "Variables", "status": "defeated"}]}
        path.write_text(json.dumps(state), encoding="utf-8")
        client = self.client()
        projection = client.get("/api/codex", headers={"host": "127.0.0.1"})
        self.assertEqual(projection.status_code, 200)
        self.assertEqual(projection.json()["revision"], 4)
        self.assertEqual(projection.json()["codex"]["entries"][0]["id"], "blackjack-table")

        saved = client.post(
            "/api/codex/note",
            headers={"host": "127.0.0.1"},
            json={"entry_id": "blackjack-table", "note": "Track the state before changing it."},
        )
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["revision"], 5)
        self.assertEqual(saved.json()["codex"]["entries"][0]["player_notes"], ["Track the state before changing it."])
        forbidden = client.post(
            "/api/state/apply",
            headers={"host": "127.0.0.1"},
            json={"action": "record_codex_note", "actor": "pyr", "payload": {"entry_id": "blackjack-table", "note": "provider"}},
        )
        self.assertEqual(forbidden.status_code, 403)

    def test_practice_routes_record_history_without_campaign_mutations(self):
        path = self.with_temp_progress()
        original = app_v2.PYR_PRACTICE_CHALLENGES
        app_v2.PYR_PRACTICE_CHALLENGES = {}
        self.addCleanup(setattr, app_v2, "PYR_PRACTICE_CHALLENGES", original)
        client = self.client()
        started = client.post(
            "/api/practice/session",
            headers={"host": "127.0.0.1"},
            json={"concept": "lists", "question_type": "multiple_choice", "difficulty": 2},
        )
        self.assertEqual(started.status_code, 200)
        session = started.json()["practice"]["sessions"][-1]
        before = json.loads(path.read_text(encoding="utf-8"))["player"].copy()
        bound = client.post(
            "/api/pyr/practice-submission",
            headers={"host": "127.0.0.1"},
            json={"session_id": session["session_id"], "answer": "Make the state explicit."},
        )
        self.assertEqual(bound.status_code, 200)
        submission = bound.json()["submission"]
        verdict = client.post(
            "/api/pyr/practice-verdict",
            headers={"host": "127.0.0.1"},
            json={
                "nonce": submission["nonce"],
                "submission_id": submission["submission_id"],
                "answer_digest": submission["answer_digest"],
                "verdict": "correct",
                "session_id": session["session_id"],
                "evidence_id": submission["evidence_id"],
                "reason": "Provider validated the selected answer.",
            },
        )
        self.assertEqual(verdict.status_code, 200, verdict.text)
        self.assertEqual(verdict.json()["mutation"]["result"]["reward_xp"], 0)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["player"], before)
        self.assertEqual(client.get("/api/practice", headers={"host": "127.0.0.1"}).json()["practice"]["count"], 1)
        replay = client.post(
            "/api/pyr/practice-verdict",
            headers={"host": "127.0.0.1"},
            json={
                "nonce": submission["nonce"],
                "submission_id": submission["submission_id"],
                "answer_digest": submission["answer_digest"],
                "verdict": "correct",
                "session_id": session["session_id"],
                "evidence_id": submission["evidence_id"],
                "reason": "Replay must be rejected.",
            },
        )
        self.assertEqual(replay.status_code, 409)

    def test_revision_and_campaign_ignore_stray_workspace_progress(self):
        canonical, legacy = self.with_split_state_paths()
        client = self.client()
        campaign = client.get("/api/campaign", headers={"host": "127.0.0.1"})
        self.assertEqual(campaign.status_code, 200)
        body = campaign.json()
        self.assertEqual(body["revision"], 4)
        self.assertRegex(body["sync_storage_namespace"], r"^checkout-[0-9a-f]{32}$")
        self.assertEqual(body["progress"]["player"]["level"], 1)
        self.assertEqual(body["encounter"]["mob_name"], "The Empty Table")
        self.assertEqual(body["encounter"]["resolve"], 4)
        self.assertEqual(body["encounter"]["available_objectives"][0]["impact"], 2)
        self.assertEqual(body["encounter"]["available_objectives"][0]["label"], "Set up the table")
        self.assertIn("state", body["encounter"]["available_objectives"][0]["brief"])
        self.assertEqual(body["encounter"]["available_objectives"][0]["question_type"], "prediction")
        self.assertEqual(body["encounter"]["mob"]["name"], "The Empty Table")
        self.assertEqual(body["encounter"]["mob"]["index"], 0)
        self.assertIn("bounded field encounter", body["encounter"]["mob"]["lore"])
        self.assertEqual(body["encounter"]["current_quest"]["id"], "table_setup")
        self.assertEqual(len(body["encounter"]["mechanics"]), 3)
        self.assertEqual(body["encounter"]["reward_envelope"], {"xp": 25, "coins": 10, "authorized_items": []})
        projection_text = json.dumps(body["encounter"])
        self.assertNotIn("The Dealer's Hand", projection_text)
        self.assertNotIn("locked_prompt", projection_text)
        self.assertNotIn("answer_key", projection_text)
        self.assertEqual(body["state_authority"]["canonical_path"], str(canonical.resolve()))
        self.assertFalse(body["state_authority"]["legacy_authoritative"])

        legacy_value = json.loads(legacy.read_text(encoding="utf-8"))
        legacy_value["player"]["level"] = 100
        legacy.write_text(json.dumps(legacy_value), encoding="utf-8")
        revision = client.get("/api/state/revision", headers={"host": "127.0.0.1"})
        self.assertEqual(revision.status_code, 200)
        self.assertEqual(revision.json()["revision"], 4)
        self.assertEqual(client.put("/api/file", headers={"host": "127.0.0.1"}, json={"path": "progress.json", "content": "{}"}).status_code, 403)
        self.assertEqual(json.loads(canonical.read_text(encoding="utf-8"))["player"]["level"], 1)

    def test_state_revision_endpoint_is_cheap_and_legacy_report_is_explicit(self):
        self.with_split_state_paths()
        client = self.client()
        revision = client.get("/api/state/revision", headers={"host": "127.0.0.1"})
        report = client.get("/api/state/legacy", headers={"host": "127.0.0.1"})
        self.assertEqual(revision.status_code, 200)
        self.assertEqual(report.status_code, 200)
        self.assertIn("revision", revision.json())
        self.assertRegex(revision.json()["sync_storage_namespace"], r"^checkout-[0-9a-f]{32}$")
        self.assertTrue(report.json()["manual_approval_required"])

    def test_runtime_report_exposes_upstream_freshness_without_changing_state(self):
        path = self.with_temp_progress()
        before = path.read_text(encoding="utf-8")
        client = self.client()
        response = client.get("/api/runtime", headers={"host": "127.0.0.1"})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("copilot", body["commands"])
        repo_git = body["repo_git"]
        self.assertIn("head_sha", repo_git)
        self.assertIn("upstream_ref", repo_git)
        self.assertIn("upstream_sha", repo_git)
        self.assertIn("behind_upstream", repo_git)
        namespace = body["sync_storage_namespace"]
        self.assertRegex(namespace, r"^checkout-[0-9a-f]{32}$")
        self.assertNotIn(str(app_v2.REPO_ROOT), namespace)
        self.assertEqual(path.read_text(encoding="utf-8"), before)

    def test_checkout_storage_namespace_is_stable_and_path_opaque(self):
        first = app_v2.checkout_storage_namespace(Path("/tmp/questlab/repo-a"), Path("/tmp/questlab/workspace-a"))
        repeat = app_v2.checkout_storage_namespace(Path("/tmp/questlab/repo-a"), Path("/tmp/questlab/workspace-a"))
        other = app_v2.checkout_storage_namespace(Path("/tmp/questlab/repo-b"), Path("/tmp/questlab/workspace-b"))
        self.assertEqual(first, repeat)
        self.assertNotEqual(first, other)
        self.assertRegex(first, r"^checkout-[0-9a-f]{32}$")
        self.assertNotIn("/tmp/questlab", first)

    def test_sync_endpoints_expose_allowlisted_projection_and_compare_and_swap(self):
        path = self.with_temp_progress()
        client = self.client()
        snapshot = client.get("/api/state/sync", headers={"host": "127.0.0.1"})
        self.assertEqual(snapshot.status_code, 200)
        body = snapshot.json()
        self.assertEqual(body["revision"], 4)
        self.assertNotIn("projects", body["projection"])
        self.assertEqual(body["projection"]["campaign"]["projects"][0]["name"], "Blackjack")
        self.assertNotIn("state_events", body["projection"]["campaign"])
        self.assertNotIn("catalog", body["projection"]["homestead"])

        applied = client.post(
            "/api/state/sync/apply",
            headers={"host": "127.0.0.1"},
            json={
                "expected_revision": 4,
                "cloud_revision": 3,
                "projection": {"player": {"coins": 77}},
            },
        )
        self.assertEqual(applied.status_code, 200)
        self.assertEqual(applied.json()["revision"], 5)
        stale = client.post(
            "/api/state/sync/apply",
            headers={"host": "127.0.0.1"},
            json={
                "expected_revision": 4,
                "cloud_revision": 4,
                "projection": {"player": {"coins": 88}},
            },
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["player"]["coins"], 77)


if __name__ == "__main__":
    unittest.main()
