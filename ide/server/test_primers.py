from __future__ import annotations

import contextlib
import io
import json
import threading
from unittest.mock import patch

import pytest

from ide.server import beginner_codex, primers, state
from ide.server.state import campaign_contract
from ide.server.test_campaign_content import use_real_content


@pytest.mark.parametrize("sign", primers.primer_ids())
def test_primer_answer_is_what_the_snippet_really_prints(sign):
    check = primers.PRIMERS[sign]["check"]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        exec(compile(check["code"], f"<primer:{sign}>", "exec"), {})
    assert out.getvalue().strip() == check["options"][check["answer"]]
    assert len(set(check["options"])) == len(check["options"]) >= 2


@pytest.mark.parametrize("sign", primers.primer_ids())
def test_step_examples_run(sign):
    for step in primers.PRIMERS[sign]["steps"]:
        if "code" in step:
            with contextlib.redirect_stdout(io.StringIO()):
                exec(compile(step["code"], f"<primer:{sign}>", "exec"), {})


def test_primers_only_for_known_concepts():
    assert set(primers.primer_ids()) <= set(beginner_codex.BEGINNER_CODEX)


def test_public_primer_hides_answer_and_grading_is_forgiving():
    public = primers.public_primer("loops")
    assert "answer" not in public["check"] and "explain" not in public["check"]
    wrong = primers.grade_check("loops", 0)
    assert wrong["correct"] is False and "answer" not in wrong and wrong["explain"]
    right = primers.grade_check("loops", 1)
    assert right["correct"] is True
    assert primers.grade_check("nope", 0) is None and primers.public_primer("nope") is None


def test_today_plan_lists_next_bounties_and_skips_cleared():
    use_real_content()
    progress = {"projects": [
        {"status": "available", "name": "Other", "mobs": []},
        {"status": "active", "branch": "00-lantern-vale", "name": "Vale", "mobs": [
            {"name": "The First Spark", "status": "defeated", "concept": "x", "encounter": "y"},
            {"name": "The Nameless Wraith", "status": "available", "concept": "Variables", "encounter": "Name things"},
            {"name": "The Whispering Gate", "status": "locked", "concept": "Input", "encounter": "Ask"},
            {"name": "The Forked Path", "status": "locked", "concept": "If", "encounter": "Branch"},
            {"name": "The Endless Echo", "status": "locked", "concept": "Loop", "encounter": "Repeat"},
        ]},
    ]}
    plan = primers.today_plan(progress, campaign_contract)
    assert [b["name"] for b in plan["bounties"]] == ["The Nameless Wraith", "The Whispering Gate", "The Forked Path"]
    assert [b["sign"] for b in plan["bounties"]] == ["variables", "input-output", "conditionals"]
    assert all(b["primer"] and "answer" not in b["primer"]["check"] for b in plan["bounties"])
    assert primers.today_plan({"projects": []}, campaign_contract)["bounties"] == []


def test_today_endpoints(tmp_path):
    from fastapi.testclient import TestClient
    from ide.server import app_v2

    client = TestClient(app_v2.app, base_url="http://127.0.0.1:8000")
    # A wrong answer is graded but never writes the real save.
    wrong = client.post("/api/today/check", json={"sign": "loops", "choice": 0}).json()
    assert wrong["correct"] is False and wrong["recorded"] is False and wrong["changed"] is False
    assert client.post("/api/today/check", json={"sign": "zzz", "choice": 1}).status_code == 404
    assert client.post("/api/today/check", json={"sign": "loops", "choice": 1, "x": 1}).status_code == 422


def _service(tmp_path, streak, daily=None):
    use_real_content()
    from ide.server.test_campaign_content import user_like_progress

    progress = user_like_progress()
    progress["streak"] = streak
    progress["goals"] = {"daily": daily if daily is not None else [
        {"id": "learn-before-forge", "text": "t", "reward_xp": 10, "reward_coins": 5, "done": False},
    ], "weekly": [], "long_term": []}
    progress.setdefault("player", {}).update({"xp": 0, "xp_next": 100, "level": 1, "coins": 0, "lifetime_xp": 0})
    path = tmp_path / "save.json"
    path.write_text(json.dumps(progress))
    return state.LocalStateService(path, threading.RLock()), path


def _check(service, day, choice=1):
    with patch.object(state.time, "strftime", return_value=day):
        return service.apply("today_check_passed", {"sign": "loops", "choice": choice}, "player")


def test_first_pass_logs_streak_activity_and_pays_the_contract_once(tmp_path):
    service, path = _service(tmp_path, {"current": 0, "longest": 0, "freeze_tokens": 0, "days_logged": []})
    out = _check(service, "2026-11-19")
    assert out["changed"] is True and out["result"]["recorded"] and out["result"]["streak"] == 1
    saved = json.loads(path.read_text())
    assert saved["streak"]["days_logged"] == ["2026-11-19"] and saved["streak"]["last_active"] == "2026-11-19"
    assert saved["goals"]["daily"][0]["done"] is True
    assert (saved["player"]["xp"], saved["player"]["coins"]) == (10, 5)
    assert saved["activity_log"]["days"]["2026-11-19"]["answers"] == 1
    again = _check(service, "2026-11-19")
    assert again["changed"] is False and again["result"]["already_recorded"] is True
    assert json.loads(path.read_text())["player"]["xp"] == 10


def test_wrong_answer_records_nothing(tmp_path):
    service, path = _service(tmp_path, {"current": 0, "longest": 0, "freeze_tokens": 0, "days_logged": []})
    before = path.read_text()
    out = _check(service, "2026-11-19", choice=0)
    assert out["changed"] is False and out["result"]["correct"] is False and out["result"]["recorded"] is False
    assert path.read_text() == before


def test_streak_continues_wards_one_missed_day_and_otherwise_restarts(tmp_path):
    base = {"current": 4, "longest": 9, "last_active": "2026-11-18", "freeze_tokens": 0, "days_logged": ["2026-11-18"]}
    service, path = _service(tmp_path, dict(base))
    assert _check(service, "2026-11-19")["result"]["streak"] == 5

    service, path = _service(tmp_path, {**base, "freeze_tokens": 1})
    out = _check(service, "2026-11-20")
    assert out["result"]["streak"] == 5 and out["result"]["streak_ward_used"] is True
    assert json.loads(path.read_text())["streak"]["freeze_tokens"] == 0

    service, path = _service(tmp_path, dict(base))
    assert _check(service, "2026-11-25")["result"]["streak"] == 1
    assert json.loads(path.read_text())["streak"]["longest"] == 9


def test_missing_contract_still_records_the_day(tmp_path):
    service, path = _service(tmp_path, {"current": 0, "longest": 0, "freeze_tokens": 0, "days_logged": []}, daily=[])
    out = _check(service, "2026-11-19")
    assert out["result"]["recorded"] and out["result"]["contract_completed"] is False
    assert json.loads(path.read_text())["player"]["xp"] == 0


def test_unknown_primer_is_rejected(tmp_path):
    service, _ = _service(tmp_path, {"current": 0})
    with pytest.raises(state.StateCommandError):
        service.apply("today_check_passed", {"sign": "zzz", "choice": 0}, "player")
