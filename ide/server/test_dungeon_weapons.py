import json
import tempfile
import threading
from pathlib import Path

import pytest

from ide.server.state import LocalStateService
from ide.server.test_state_service import fixture_progress


@pytest.fixture
def fight():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'progress.json'
        path.write_text(json.dumps(fixture_progress()))
        service = LocalStateService(path, threading.RLock())
        run = service.apply('dungeon_start_run', {'concept_id': 'loops', 'seed': 'weapon-test'}, 'player')['result']['run']
        state = json.loads(path.read_text())
        node = {'id': 'f1-r1-test', 'kind': 'elite', 'row': 1, 'column': 1, 'label': 'elite'}
        state['dungeon_run']['room_choices'] = [node]
        state['dungeon_run']['map']['nodes'].append(node)
        path.write_text(json.dumps(state))
        service.apply('dungeon_choose_room', {'run_id': run['run_id'], 'choice_id': node['id']}, 'player')
        yield service, path


def change(path, weapon, *, hp=None, resolve=None, cleared=None, question_type=None):
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['loadout']['weapon'] = weapon
    if hp is not None:
        run['loadout']['hp'] = hp
    if resolve is not None:
        run['fight']['resolve'] = resolve
    if cleared is not None:
        run['fight']['questions_cleared'] = cleared
    if question_type is not None:
        run['question']['question_type'] = question_type
    path.write_text(json.dumps(state))


def answer(service, path, verdict, tag):
    run = service.dungeon_projection(json.loads(path.read_text()))
    return service.apply_internal('dungeon_record_verdict', {'run_id': run['run_id'], 'question_id': run['question']['id'], 'verdict': verdict, 'evidence_id': tag, 'reason': 'test'})['result']


@pytest.mark.parametrize(('weapon', 'effect'), [
    ('Pathfinder Whip', 'opening answer'),
    ('Loopblade', 'against elites'),
    ('Syntax Sabre', 'for explaining'),
])
def test_weapon_bonus_is_applied_to_actual_resolve(fight, weapon, effect):
    service, path = fight
    change(path, weapon, question_type='short_explanation')
    result = answer(service, path, 'correct', weapon.lower().replace(' ', '-'))
    assert effect in result['fight']['weapon_effect']
    assert result['fight']['chip'] >= 4


def test_staff_mitigates_only_first_mistake(fight):
    service, path = fight
    change(path, 'Aether Staff')
    first = answer(service, path, 'incorrect', 'staff-first')
    second = answer(service, path, 'incorrect', 'staff-second')
    assert first['damage'] == second['damage'] - 2
    assert 'blocked 2' in first['fight']['weapon_effect']
    assert second['fight']['weapon_effect'] is None


def test_greatsword_rewards_correcting_an_answer(fight):
    service, path = fight
    change(path, 'Iron Greatsword')
    answer(service, path, 'incorrect', 'greatsword-wrong')
    result = answer(service, path, 'correct', 'greatsword-correct')
    assert '+2 Resolve' in result['fight']['weapon_effect']


def test_runic_casting_rewards_clean_follow_up(fight):
    service, path = fight
    change(path, 'Runic Casting')
    first = answer(service, path, 'correct', 'runic-first')
    second = answer(service, path, 'correct', 'runic-second')
    assert first['fight']['weapon_effect'] is None
    assert 'clean follow-up' in second['fight']['weapon_effect']


def test_scythe_heals_on_break_without_exceeding_max_hp(fight):
    service, path = fight
    change(path, 'Grave Scythe', hp=99, resolve=1)
    result = answer(service, path, 'correct', 'scythe-break')
    assert result['fight']['broke'] is True
    assert result['run']['loadout']['hp'] == 100
    assert '+1 HP' in result['fight']['weapon_effect']
