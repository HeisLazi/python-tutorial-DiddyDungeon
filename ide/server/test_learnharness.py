from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ide.server import app_v2, learnharness


def write_graph(lines: list[str]) -> None:
    graph = Path(os.environ["LEARNHARNESS_DATA_DIR"]) / "graph"
    graph.mkdir(parents=True, exist_ok=True)
    (graph / "nodes.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def node(node_id: str, name: str, statement: str, aliases: list[str] | None = None) -> str:
    return json.dumps({"id": node_id, "name": name, "statement": statement, "aliases": aliases or [], "createdAt": "2026-10-26", "provenance": []})


@pytest.mark.usefixtures("_no_real_learnharness")
class LearnHarnessGraphTests(unittest.TestCase):
    def test_the_graph_is_read_merged_by_id_and_corrupt_lines_are_skipped(self):
        write_graph([
            node("n_1", "Expected value", "The expected value of a bet is the probability-weighted average of its payouts."),
            "{not json",
            json.dumps({"id": "n_2"}),
            node("n_1", "Later name ignored", "Later statement ignored", ["EV"]),
            node("n_2", "Weighted choice", "random.choices picks items in proportion to their weights."),
        ])
        ideas = learnharness.read_propositions()
        self.assertEqual([item["id"] for item in ideas], ["n_1", "n_2"])
        self.assertEqual(ideas[0]["name"], "Expected value")
        self.assertEqual(ideas[0]["aliases"], ["EV"])

    def test_related_ideas_are_ranked_by_shared_words(self):
        write_graph([
            node("n_1", "Expected value", "The expected value of a bet is the probability-weighted average of its payouts."),
            node("n_2", "Weighted choice", "random.choices picks items in proportion to their weights."),
            node("n_3", "Recursion", "A function that calls itself needs a base case."),
        ])
        ranked = learnharness.related(learnharness.read_propositions(), "weighted reels with weights and random choices", 5)
        self.assertEqual([item["id"] for item in ranked], ["n_2", "n_1"])
        self.assertEqual(learnharness.related(learnharness.read_propositions(), "the and for", 5), [])

    def test_no_graph_means_no_ideas(self):
        self.assertEqual(learnharness.read_propositions(), [])

    def test_only_a_local_api_is_ever_called(self):
        os.environ["LEARNHARNESS_URL"] = "http://example.com:3000"
        try:
            self.assertIsNone(learnharness.api_url())
        finally:
            del os.environ["LEARNHARNESS_URL"]


class FakeLearnHarness(BaseHTTPRequestHandler):
    received: list[tuple[str, bytes, str]] = []

    def log_message(self, *args):
        return

    def _reply(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self._reply({"chats": []})

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        FakeLearnHarness.received.append((self.path, body, self.headers.get("Content-Type", "")))
        if self.path == "/api/chats":
            self._reply({"id": "chat_1", "title": json.loads(body)["title"]})
        else:
            self._reply({"results": [{"ok": True}]})


@pytest.mark.usefixtures("_no_real_learnharness")
class LearnHarnessBridgeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_v2.app, base_url="http://127.0.0.1")
        self.host = {"host": "127.0.0.1"}

    def test_without_its_api_the_game_hands_off_a_study_brief(self):
        write_graph([node("n_1", "Weighted choice", "random.choices picks items in proportion to their weights.")])
        status = self.client.get("/api/learnharness/status", headers=self.host).json()
        self.assertEqual((status["mode"], status["ideas"]), ("handoff", 1))
        lore = self.client.get("/api/learnharness/lore", params={"concept": "Weighted random choices"}, headers=self.host).json()
        self.assertEqual([item["name"] for item in lore["ideas"]], ["Weighted choice"])

        learnharness_installed = learnharness.installed
        learnharness.installed = lambda: True
        try:
            study = self.client.post("/api/learnharness/study", headers=self.host, json={"topic": "Weighted random choices", "context": "building weighted reels in silver_reels"}).json()
        finally:
            learnharness.installed = learnharness_installed
        self.assertEqual(study["mode"], "handoff")
        self.assertIn("Weighted random choices", study["brief"])
        self.assertIn("building weighted reels in silver_reels", study["brief"])
        self.assertIn("random.choices picks items", study["brief"])

    def test_notes_are_written_as_markdown_to_import_by_hand(self):
        result = self.client.post("/api/learnharness/notes", headers=self.host).json()
        self.assertEqual(result["mode"], "handoff")
        path = Path(result["path"])
        self.assertTrue(path.is_file())
        self.assertTrue(path.read_text(encoding="utf-8").startswith("# DiddyDungeon notes"))

    def test_with_an_open_local_api_sessions_and_notes_go_straight_in(self):
        FakeLearnHarness.received = []
        server = HTTPServer(("127.0.0.1", 0), FakeLearnHarness)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        os.environ["LEARNHARNESS_URL"] = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            write_graph([node("n_1", "Expected value", "The expected value of a bet is the probability-weighted average of its payouts.")])
            study = self.client.post("/api/learnharness/study", headers=self.host, json={"topic": "Expected value", "context": "auditing a slot machine"}).json()
            self.assertEqual(study["mode"], "direct")
            self.assertEqual(study["title"], "Expected value — auditing a slot machine")
            path, body, _type = FakeLearnHarness.received[0]
            self.assertEqual(path, "/api/chats")
            self.assertEqual(json.loads(body)["graphContext"]["propositions"][0]["id"], "n_1")
            notes = self.client.post("/api/learnharness/notes", headers=self.host).json()
            self.assertEqual(notes["mode"], "direct")
            path, body, content_type = FakeLearnHarness.received[1]
            self.assertEqual(path, "/api/graph/import")
            self.assertIn("multipart/form-data", content_type)
            self.assertIn(b'name="files"; filename="diddydungeon-', body)
        finally:
            del os.environ["LEARNHARNESS_URL"]
            server.shutdown()

    def test_studied_ideas_reach_pyrs_question_prompts(self):
        prompt = app_v2.ai_tutor._studied_part(["Expected value: probability-weighted average"])
        self.assertIn("studied these ideas at home", prompt)
        self.assertEqual(app_v2.ai_tutor._studied_part([]), "")
