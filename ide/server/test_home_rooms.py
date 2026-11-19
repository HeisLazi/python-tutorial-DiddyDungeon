from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ide.server.home_rooms import HOME_ROOM_LADDERS, effective_room_levels, validate_room_levels


def test_server_catalog_matches_godot_ladders():
    source = (Path(__file__).resolve().parents[1] / 'home-godot/scripts/rooms.gd').read_text()
    literal = source.split('const LADDERS := ', 1)[1].split('\n}\n', 1)[0] + '\n}'
    assert HOME_ROOM_LADDERS == ast.literal_eval(literal)
    assert sum(step['cost'] for ladder in HOME_ROOM_LADDERS.values() for step in ladder) == 2028


def test_legacy_upgrades_project_without_charging_and_explicit_levels_win():
    progress = {'homestead': {'upgrade_tokens': 77, 'room_upgrades': ['reinforced-hearth', 'warding-loom']}}
    legacy = effective_room_levels(progress)
    assert legacy['great_hall'] == 3
    assert legacy['armory'] == 3
    assert legacy['war_room'] == 0
    assert progress['homestead']['upgrade_tokens'] == 77
    assert 'room_levels' not in progress['homestead']
    progress['homestead']['room_levels'] = {**legacy, 'den': 2, 'great_hall': 0}
    assert effective_room_levels(progress)['great_hall'] == 0
    assert effective_room_levels(progress)['den'] == 2


@pytest.mark.parametrize('bad', [None, {}, {'den': 1}, {**{k: 0 for k in HOME_ROOM_LADDERS}, 'den': True}, {**{k: 0 for k in HOME_ROOM_LADDERS}, 'den': 10}])
def test_room_levels_reject_incomplete_or_invalid_maps(bad):
    with pytest.raises(ValueError):
        validate_room_levels(bad)


def test_purchase_migrates_legacy_levels_and_rejects_stale_retry(tmp_path):
    import json
    import threading
    from ide.server.state import LocalStateService, StateCommandError
    from ide.server.test_state_service import fixture_progress

    progress = fixture_progress()
    progress['homestead'].update({'upgrade_tokens': 100, 'room_upgrades': ['reinforced-hearth', 'warding-loom']})
    path = tmp_path / 'isolated-save.json'
    path.write_text(json.dumps(progress))
    service = LocalStateService(path, threading.RLock())
    result = service.apply('home_room_purchase', {'room_id': 'library', 'expected_level': 0}, 'player')
    saved = json.loads(path.read_text())
    assert result['result']['level'] == 1
    assert saved['homestead']['upgrade_tokens'] == 84
    assert saved['homestead']['room_levels']['great_hall'] == 3
    assert saved['homestead']['room_levels']['armory'] == 3
    assert saved['homestead']['room_upgrades'] == ['reinforced-hearth', 'warding-loom']
    with pytest.raises(StateCommandError, match='refresh before buying'):
        service.apply('home_room_purchase', {'room_id': 'library', 'expected_level': 0}, 'player')
    assert json.loads(path.read_text()) == saved


def test_purchase_rejects_insufficient_maxed_invalid_and_non_player(tmp_path):
    import json
    import threading
    from ide.server.state import LocalStateService, StateCommandError
    from ide.server.test_state_service import fixture_progress

    progress = fixture_progress()
    levels = {room: 0 for room in HOME_ROOM_LADDERS}
    levels['den'] = len(HOME_ROOM_LADDERS['den'])
    progress['homestead'].update({'upgrade_tokens': 0, 'room_levels': levels})
    path = tmp_path / 'isolated-save.json'
    path.write_text(json.dumps(progress))
    service = LocalStateService(path, threading.RLock())
    for payload, actor in [({'room_id': 'library', 'expected_level': 0}, 'player'),
                           ({'room_id': 'den', 'expected_level': 9}, 'player'),
                           ({'room_id': 'unknown', 'expected_level': 0}, 'player'),
                           ({'room_id': 'library', 'expected_level': 0}, 'pyr')]:
        with pytest.raises(StateCommandError):
            service.apply('home_room_purchase', payload, actor)
    assert json.loads(path.read_text()) == progress


def test_home_levels_and_currency_round_trip_through_cloud_projection(tmp_path):
    import json
    import threading
    from ide.server.state import LocalStateService, StateCommandError
    from ide.server.test_state_service import fixture_progress

    source = fixture_progress()
    source['homestead'].update({'upgrade_tokens': 100, 'room_upgrades': ['reinforced-hearth']})
    src = tmp_path / 'source.json'
    dst = tmp_path / 'destination.json'
    src.write_text(json.dumps(source))
    dst.write_text(json.dumps(fixture_progress()))
    first = LocalStateService(src, threading.RLock())
    second = LocalStateService(dst, threading.RLock())
    first.apply('home_room_purchase', {'room_id': 'den', 'expected_level': 0}, 'player')
    projection, _ = first.sync_snapshot()
    second.apply_cloud_projection(projection, expected_revision=4, cloud_revision=5)
    imported = json.loads(dst.read_text())['homestead']
    assert imported['room_levels']['den'] == 1
    assert imported['room_levels']['great_hall'] == 3
    assert imported['upgrade_tokens'] == 86
    assert imported['room_upgrades'] == ['reinforced-hearth']
    projection['homestead']['room_levels']['den'] = 999
    with pytest.raises(StateCommandError):
        second.apply_cloud_projection(projection, expected_revision=5, cloud_revision=6)


def test_concurrent_duplicate_purchase_spends_once(tmp_path):
    import json
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from ide.server.state import LocalStateService, StateCommandError
    from ide.server.test_state_service import fixture_progress

    progress = fixture_progress()
    progress['homestead']['upgrade_tokens'] = 100
    path = tmp_path / 'isolated-save.json'
    path.write_text(json.dumps(progress))
    service = LocalStateService(path, threading.RLock())
    def buy():
        try:
            return service.apply('home_room_purchase', {'room_id': 'library', 'expected_level': 0}, 'player')['changed']
        except StateCommandError as exc:
            assert exc.status_code == 409
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: buy(), range(2))) == [False, True]
    saved = json.loads(path.read_text())
    assert saved['homestead']['upgrade_tokens'] == 84
    assert saved['homestead']['room_levels']['library'] == 1


def test_purchase_endpoint_returns_updated_progress(tmp_path, monkeypatch):
    import json
    from fastapi.testclient import TestClient
    from ide.server import app_v2
    from ide.server.test_state_service import fixture_progress

    progress = fixture_progress()
    progress['homestead']['upgrade_tokens'] = 100
    path = tmp_path / 'isolated-save.json'
    path.write_text(json.dumps(progress))
    monkeypatch.setattr(app_v2, 'PROGRESS_PATH', path)
    with TestClient(app_v2.app, base_url="http://127.0.0.1") as client:
        response = client.post('/api/home/rooms/purchase', json={'room_id': 'den', 'expected_level': 0})
        assert response.status_code == 200
        body = response.json()
        assert body['progress']['homestead']['room_levels']['den'] == 1
        assert body['progress']['homestead']['upgrade_tokens'] == 86
        assert body['home_rooms']['levels']['den'] == 1
        assert client.post('/api/home/rooms/purchase', json={'room_id': 'den', 'expected_level': 0}).status_code == 409
