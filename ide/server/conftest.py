"""Keep tests independent of the shipped campaign story files.

Most tests build small fixture boards; the authored contracts in
ide/server/campaigns/ would extend them. Tests that cover the authored
campaign set state.CAMPAIGN_CONTENT_DIR back to the real folder (and drop
the legacy base layer, as the shipped game does).
"""

from pathlib import Path

import pytest

from ide.server import learnharness, state

# The archived boards of the retired campaigns: small, stable fixture content.
LEGACY_BOARDS = Path(state.__file__).parent / "campaigns_archive" / "legacy_bounties.json"


@pytest.fixture(autouse=True)
def _no_real_learnharness(tmp_path, monkeypatch):
    """Never read the learner's real LearnHarness data or open the app."""

    monkeypatch.setenv("LEARNHARNESS_DATA_DIR", str(tmp_path / "learnharness-data"))
    monkeypatch.setenv("LEARNHARNESS_NOTES_DIR", str(tmp_path / "learnharness-notes"))
    monkeypatch.delenv("LEARNHARNESS_URL", raising=False)
    monkeypatch.setattr(learnharness, "launch", lambda: False)
    learnharness._API_CACHE.update(url=None, ok=False, at=0.0)


@pytest.fixture(autouse=True)
def _no_real_save(tmp_path, monkeypatch):
    """Never write the real save: the app's state service works on a copy.

    Saving a file now logs code activity in the save, so any test that
    saves through the API would otherwise write the checkout's progress.json
    (which, in a player's checkout, is their game)."""

    from ide.server import app_v2

    copy = tmp_path / "test-save" / "progress.json"
    copy.parent.mkdir()
    if app_v2.PROGRESS_PATH.is_file():
        copy.write_bytes(app_v2.PROGRESS_PATH.read_bytes())
    monkeypatch.setattr(app_v2, "PROGRESS_PATH", copy)


@pytest.fixture(autouse=True)
def _no_shipped_campaign_content(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "CAMPAIGN_BOUNTIES_PATH", LEGACY_BOARDS)
    monkeypatch.setattr(state, "CAMPAIGN_CONTENT_DIR", tmp_path / "no-campaigns")
    state._CAMPAIGN_CACHE.update(key=None, data={})
    yield
    state._CAMPAIGN_CACHE.update(key=None, data={})
