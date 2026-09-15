from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2
from ide.server.state import LocalStateService, StateCommandError, legacy_state_report


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
            {"concept_id": "lists", "seed": "test-seed"},
            "player",
        )
        run = started["result"]["run"]
        self.assertTrue(run["active"])
        self.assertEqual(run["floor"], 1)
        self.assertEqual(run["room"], 1)
        self.assertEqual(run["loadout"]["armor"], "Apprentice Coat")
        self.assertIsNone(run["loadout"]["trinket"])
        self.assertEqual(run["loadout"]["heals"], 1)
        self.assertEqual(run["loadout"]["coins"], 0)
        self.assertEqual(run["editor_content"], "")
        self.assertEqual(self.read(path)["player"], before["player"])

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
        started = service.apply("dungeon_start_run", {"concept_id": "loops"}, "player")
        run_id = started["result"]["run"]["run_id"]
        question_id = started["result"]["run"]["question"]["id"]
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
        started = service.apply("dungeon_start_run", {"concept_id": "lists", "seed": "loop-seed"}, "player")
        run = started["result"]["run"]
        initial_player = self.read(path)["player"].copy()

        for index in range(4):
            current = service.dungeon_projection(service.snapshot())
            result = service.apply_internal(
                "dungeon_record_verdict",
                {
                    "run_id": run["run_id"],
                    "question_id": current["question"]["id"],
                    "verdict": "correct",
                    "evidence_id": f"dungeon-proof-{index}",
                    "reason": "Provider validated the current room",
                },
            )
            self.assertEqual(result["result"]["outcome"], "correct")

        rest = service.dungeon_projection(service.snapshot())
        self.assertEqual(rest["room"], 5)
        self.assertEqual(rest["room_type"], "rest")
        self.assertIsNone(rest["question"])
        state = self.read(path)
        state["dungeon_run"]["loadout"]["hp"] = 40
        path.write_text(json.dumps(state), encoding="utf-8")
        rested = service.apply("dungeon_use_rest", {"run_id": run["run_id"]}, "player")
        self.assertEqual(rested["result"]["healed"], 30)
        self.assertEqual(rested["result"]["run"]["room_type"], "encounter")
        self.assertEqual(rested["result"]["run"]["loadout"]["hp"], 70)

        for index in range(1):
            current = service.dungeon_projection(service.snapshot())
            service.apply_internal(
                "dungeon_record_verdict",
                {
                    "run_id": run["run_id"],
                    "question_id": current["question"]["id"],
                    "verdict": "correct",
                    "evidence_id": f"dungeon-proof-market-{index}",
                    "reason": "Provider validated the current room",
                },
            )
        market = service.dungeon_projection(service.snapshot())
        self.assertEqual(market["room_type"], "market")
        self.assertTrue(market["market_catalog"])
        purchased = service.apply("dungeon_market_purchase", {"run_id": run["run_id"], "item_id": "dungeon-ward"}, "player")
        self.assertEqual(purchased["result"]["item"]["id"], "dungeon-ward")
        self.assertEqual(purchased["result"]["run"]["loadout"]["armor"], "Ember Ward")
        left = service.apply("dungeon_leave_room", {"run_id": run["run_id"]}, "player")
        self.assertEqual(left["result"]["run"]["room_type"], "encounter")

        finished = service.apply("dungeon_finish_run", {"run_id": run["run_id"]}, "player")
        self.assertEqual(finished["result"]["run"]["status"], "complete")
        self.assertEqual(self.read(path)["player"], initial_player)
        self.assertTrue(all("answer_key" not in entry for entry in finished["result"]["run"]["history"]))
        self.assertEqual(len(self.read(path)["dungeon_leaderboard"]), 1)
        self.assertEqual(finished["result"]["run"]["leaderboard"][0]["status"], "complete")

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
        started = service.apply("dungeon_start_run", {"concept_id": "loops"}, "player")
        run = started["result"]["run"]
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
        self.assertEqual(projection["entries"][0]["page_id"], "lists")
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
            {"objective_id": "table_setup", "evidence_id": "mob-000-table", "reason": "Verified table state explanation"},
        )
        state = self.read(path)
        self.assertEqual(first["result"]["resolve_before"], 4)
        self.assertEqual(first["result"]["resolve_after"], 2)
        self.assertFalse(first["result"]["mob_defeated"])
        self.assertEqual(state["encounter_state"]["resolve"], 2)
        self.assertEqual(state["state_events"][-1]["impact"], 2)

        second = service.apply_internal(
            "record_battle_objective",
            {"objective_id": "state_explanation", "evidence_id": "mob-000-state", "reason": "Verified state boundary"},
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
        self.assertTrue(next(item for item in state["achievements"] if item["name"] == "First Blood")["unlocked"])

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
        state["codex"] = {"encounters": [{"mob_name": "The Empty Table"}]}
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
        self.assertNotIn("codex", projection)
        self.assertNotIn("skills", projection)

    def test_valid_cloud_projection_bumps_revision_and_keeps_non_sync_domains(self):
        service, path = self.make_service()
        state = self.read(path)
        state["codex"] = {"encounters": [{"mob_name": "local note"}]}
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
        self.assertEqual(after["projects"][0]["progress"], 42)
        self.assertEqual(after["state_events"][-1]["action"], "sync_apply_cloud")

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
        self.assertEqual(body["progress"]["player"]["level"], 1)
        self.assertEqual(body["encounter"]["mob_name"], "The Empty Table")
        self.assertEqual(body["encounter"]["resolve"], 4)
        self.assertEqual(body["encounter"]["available_objectives"][0]["impact"], 2)
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
        self.assertTrue(report.json()["manual_approval_required"])

    def test_sync_endpoints_expose_allowlisted_projection_and_compare_and_swap(self):
        path = self.with_temp_progress()
        client = self.client()
        snapshot = client.get("/api/state/sync", headers={"host": "127.0.0.1"})
        self.assertEqual(snapshot.status_code, 200)
        body = snapshot.json()
        self.assertEqual(body["revision"], 4)
        self.assertNotIn("projects", body["projection"])
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
