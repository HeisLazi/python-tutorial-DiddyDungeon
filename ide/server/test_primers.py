from __future__ import annotations

import contextlib
import io

import pytest

from ide.server import beginner_codex, primers
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
    assert client.post("/api/today/check", json={"sign": "loops", "choice": 1}).json()["correct"] is True
    assert client.post("/api/today/check", json={"sign": "zzz", "choice": 1}).status_code == 404
    assert client.post("/api/today/check", json={"sign": "loops", "choice": 1, "x": 1}).status_code == 422
