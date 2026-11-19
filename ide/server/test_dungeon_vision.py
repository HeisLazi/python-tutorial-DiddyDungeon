import json
import tempfile
import threading
from pathlib import Path

import pytest

from ide.server.state import LocalStateService, StateCommandError
from ide.server.test_state_service import fixture_progress


def service_with_scrolls():
    temp = tempfile.TemporaryDirectory()
    path = Path(temp.name) / 'progress.json'
    path.write_text(json.dumps(fixture_progress()), encoding='utf-8')
    service = LocalStateService(path, threading.RLock())
    run = service.apply('dungeon_start_run', {'concept_id': 'lists', 'seed': 'vision-test'}, 'player')['result']['run']
    save = json.loads(path.read_text(encoding='utf-8'))
    save['dungeon_run']['loadout']['vision_scrolls'] = 2
    path.write_text(json.dumps(save), encoding='utf-8')
    return temp, path, service, run


def test_scroll_reveals_only_current_floor_and_spends_once():
    temp, path, service, run = service_with_scrolls()
    try:
        initial = service.dungeon_projection(json.loads(path.read_text(encoding='utf-8')))
        full_map = json.loads(path.read_text(encoding='utf-8'))['dungeon_run']['map']
        assert len(initial['map']['nodes']) < len(full_map['nodes'])
        result = service.apply('dungeon_reveal_risk', {'run_id': run['run_id']}, 'player')['result']
        revealed = result['run']
        assert revealed['map']['revealed'] is True
        assert len(revealed['map']['nodes']) == len(full_map['nodes'])
        assert revealed['loadout']['vision_scrolls'] == 1
        assert revealed['room_choices'] == initial['room_choices']
        assert revealed['question'] is None
        allowed = {choice['id'] for choice in revealed['room_choices']}
        distant = next(node['id'] for node in revealed['map']['nodes'] if node['id'] not in allowed and node['id'] != revealed['map']['current_node_id'])
        with pytest.raises(StateCommandError, match='no longer available'):
            service.apply('dungeon_choose_room', {'run_id': run['run_id'], 'choice_id': distant}, 'player')
        assert all(set(node) <= {'id', 'type', 'row', 'column', 'label', 'note'} for node in revealed['map']['nodes'])
        again = service.apply('dungeon_reveal_risk', {'run_id': run['run_id']}, 'player')['result']
        assert again['revealed'] is False
        assert again['run']['loadout']['vision_scrolls'] == 1
        reopened = LocalStateService(path, threading.RLock()).dungeon_projection(json.loads(path.read_text(encoding='utf-8')))
        assert reopened['map']['revealed'] is True
        assert not LocalStateService._dungeon_generate_grid('vision-test', 2).get('revealed', False)
        sync = LocalStateService._campaign_source_projection(json.loads(path.read_text(encoding='utf-8')))
        synced_run = LocalStateService._validate_campaign_projection(sync)['dungeon_run']
        assert synced_run['map']['revealed'] is True
        assert synced_run['floor_layout'] == 'grid'
    finally:
        temp.cleanup()


def test_scroll_requires_inventory_and_safe_route():
    temp, path, service, run = service_with_scrolls()
    try:
        save = json.loads(path.read_text(encoding='utf-8'))
        save['dungeon_run']['loadout']['vision_scrolls'] = 0
        path.write_text(json.dumps(save), encoding='utf-8')
        with pytest.raises(StateCommandError, match='vision scroll'):
            service.apply('dungeon_reveal_risk', {'run_id': run['run_id']}, 'player')
        save['dungeon_run']['loadout']['vision_scrolls'] = 1
        save['dungeon_run']['room_type'] = 'market'
        path.write_text(json.dumps(save), encoding='utf-8')
        with pytest.raises(StateCommandError, match='choosing a route'):
            service.apply('dungeon_reveal_risk', {'run_id': run['run_id']}, 'player')
        assert json.loads(path.read_text(encoding='utf-8'))['dungeon_run']['loadout']['vision_scrolls'] == 1
    finally:
        temp.cleanup()


def test_map_endpoint_reveals_floor_without_writing_workspace_files(monkeypatch):
    from fastapi.testclient import TestClient
    from ide.server import app_v2

    temp, path, service, run = service_with_scrolls()
    try:
        monkeypatch.setattr(app_v2, 'STATE_SERVICE', service)
        monkeypatch.setattr(app_v2, 'sync_dungeon_projection', service.dungeon_projection)
        response = TestClient(app_v2.app, base_url='http://localhost').post('/api/dungeon/map/reveal', json={'run_id': run['run_id']})
        assert response.status_code == 200, response.text
        data = response.json()
        assert data['dungeon']['map']['revealed'] is True
        assert data['dungeon']['loadout']['vision_scrolls'] == 1
    finally:
        temp.cleanup()
