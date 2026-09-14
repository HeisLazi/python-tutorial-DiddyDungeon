from __future__ import annotations

import json
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

from ide.server import app_v2
from ide.server.state import LocalStateService, StateCommandError


def fixture_progress() -> dict:
    return {
        "meta": {"revision": 4, "updated_at": "2026-09-14T00:00:00+00:00", "device_id": "device-alpha"},
        "player": {"xp": 10, "lifetime_xp": 25, "coins": 50, "hp": 100, "max_hp": 100},
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


if __name__ == "__main__":
    unittest.main()
