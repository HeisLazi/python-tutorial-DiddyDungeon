"""The everything-unlocked test save really unlocks everything and never touches the real save."""
import importlib.util
import json
from pathlib import Path

import pytest

from ide.server.test_campaign_content import use_real_content
from ide.server.state import CAMPAIGN_DELVE_GEAR, DUNGEON_REGIONS, LocalStateService, armory_catalog

SCRIPT = Path(__file__).resolve().parents[2] / 'tools' / 'make_test_save.py'
spec = importlib.util.spec_from_file_location('make_test_save', SCRIPT)
make = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make)


def test_everything_is_unlocked():
    use_real_content()
    state = make.everything_unlocked()
    catalog = armory_catalog()
    stacks = set(state['hunter']['armory']['stack'])
    assert set(state['hunter']['armory']['owned']) | stacks == set(catalog)
    journal = LocalStateService._dungeon_journal_projection(state)
    assert journal['totals'] == {'bosses': len(DUNGEON_REGIONS), 'bosses_total': len(DUNGEON_REGIONS),
                                 'echoes': len(CAMPAIGN_DELVE_GEAR), 'echoes_total': len(CAMPAIGN_DELVE_GEAR)}
    assert journal['title'] == 'Master Delver'
    assert {sign['level'] for sign in LocalStateService.hunter_projection(state)['signs']} == {10}
    assert state['player']['coins'] >= 100_000


def test_it_writes_only_the_path_it_is_given_and_keeps_an_existing_file(tmp_path, monkeypatch):
    use_real_content()
    target = tmp_path / 'progress.json'
    monkeypatch.setattr('sys.argv', ['make_test_save.py', str(target)])
    assert make.main() == 0 and json.loads(target.read_text())['test_save']
    target.write_text('{"keep": true}')
    assert make.main() == 0 and json.loads(target.read_text()) == {'keep': True}
    monkeypatch.setattr('sys.argv', ['make_test_save.py', str(target), '--force'])
    make.main()
    assert 'test_save' in json.loads(target.read_text())


def test_it_refuses_the_real_save_and_relative_paths(monkeypatch):
    for argument in (str(make.ROOT / 'progress.json'), 'relative.json'):
        monkeypatch.setattr('sys.argv', ['make_test_save.py', argument])
        with pytest.raises(SystemExit):
            make.main()


def test_the_installed_app_can_create_the_test_save_only_when_missing(tmp_path):
    use_real_content()
    from ide.server.unlocked_save import initialize_test_save
    target = tmp_path / 'test-mode' / 'progress.json'
    assert initialize_test_save(target) is True and json.loads(target.read_text())['test_save']
    target.write_text('{"progress": "kept"}')
    assert initialize_test_save(target) is False and json.loads(target.read_text()) == {'progress': 'kept'}
    with pytest.raises(ValueError):
        initialize_test_save(Path('relative.json'))
