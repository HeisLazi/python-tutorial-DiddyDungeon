"""Keep tests independent of the shipped campaign story files.

Most tests build small fixture boards; the authored contracts in
ide/server/campaigns/ would extend them. Tests that cover the authored
campaign set state.CAMPAIGN_CONTENT_DIR back to the real folder.
"""

import pytest

from ide.server import state


@pytest.fixture(autouse=True)
def _no_shipped_campaign_content(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "CAMPAIGN_CONTENT_DIR", tmp_path / "no-campaigns")
    state._CAMPAIGN_CACHE.update(key=None, data={})
    yield
    state._CAMPAIGN_CACHE.update(key=None, data={})
