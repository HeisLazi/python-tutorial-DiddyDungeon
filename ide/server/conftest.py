"""Keep tests independent of the shipped campaign story files.

Most tests build small fixture boards; the authored contracts in
ide/server/campaigns/ would extend them. Tests that cover the authored
campaign set state.CAMPAIGN_CONTENT_DIR back to the real folder.
"""

import pytest

from ide.server import learnharness, state


@pytest.fixture(autouse=True)
def _no_real_learnharness(tmp_path, monkeypatch):
    """Never read the learner's real LearnHarness data or open the app."""

    monkeypatch.setenv("LEARNHARNESS_DATA_DIR", str(tmp_path / "learnharness-data"))
    monkeypatch.setenv("LEARNHARNESS_NOTES_DIR", str(tmp_path / "learnharness-notes"))
    monkeypatch.delenv("LEARNHARNESS_URL", raising=False)
    monkeypatch.setattr(learnharness, "launch", lambda: False)
    learnharness._API_CACHE.update(url=None, ok=False, at=0.0)


@pytest.fixture(autouse=True)
def _no_shipped_campaign_content(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "CAMPAIGN_CONTENT_DIR", tmp_path / "no-campaigns")
    state._CAMPAIGN_CACHE.update(key=None, data={})
    yield
    state._CAMPAIGN_CACHE.update(key=None, data={})
