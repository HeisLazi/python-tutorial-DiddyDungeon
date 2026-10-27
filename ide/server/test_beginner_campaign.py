from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

from ide.server import app_v2, state
from ide.server.test_campaign_content import use_real_content, user_like_progress


def test_beginner_campaign_can_be_selected_without_losing_existing_progress(tmp_path):
    use_real_content()
    path = tmp_path / 'save.json'
    path.write_text(json.dumps(user_like_progress()))
    service = state.LocalStateService(path, threading.RLock())
    service.apply_internal('campaign_extend', {})
    before = json.loads(path.read_text())
    blackjack = next(p for p in before['projects'] if p['branch'] == '01-blackjack')
    selected = service.apply('select_campaign', {'branch': '00-lantern-vale'}, 'player')
    assert selected['result']['project']['entry_file'] == 'lantern_vale/game.py'
    after = json.loads(path.read_text())
    original = next(p for p in after['projects'] if p['branch'] == '01-blackjack')
    assert original['status'] == 'available'
    assert original['mobs'] == blackjack['mobs']
    encounter = service.encounter_projection(after)
    assert encounter['mob_name'] == 'The First Spark'
    assert [o['id'] for o in encounter['available_objectives']] == [
        'make_folder', 'make_file', 'first_run', 'edit_run', 'explain_run'
    ]
    assert len(service.campaign_view(after)['projects']) == len(after['projects'])


def test_beginner_codex_reference_is_in_tutor_projection(tmp_path):
    service = state.LocalStateService(tmp_path / 'save.json', threading.RLock())
    pages = {page['id']: page for page in service.codex_projection({})['pages']}
    assert 'pure function' in pages['functions']['definition']
    assert 'callback' in pages['functions']['definition']
    assert 'comprehension' in pages['lists']['definition']
    assert 'each instance' in pages['classes']['definition']
    assert 'malformed' in pages['files-json']['definition']
    assert 'assert double(0) == 0' in pages['testing']['examples'][-1]


def test_campaign_question_reads_its_authored_module(tmp_path, monkeypatch):
    folder = tmp_path / 'lantern_vale'
    folder.mkdir()
    (folder / 'game.py').write_text('MAIN_FILE = True\n')
    (folder / 'models.py').write_text('MODEL_FILE = True\n')
    monkeypatch.setattr(app_v2, 'WORKSPACE', tmp_path)
    monkeypatch.setattr(app_v2, '_battle_choice_objective', lambda _: (
        {'projects': [{'status': 'active', 'branch': '00-lantern-vale', 'entry_file': 'lantern_vale/game.py'}]},
        {'project_name': 'The Lantern Vale', 'mob': {'concept': 'classes'}},
        {'file': 'models.py', 'label': 'Explain', 'brief': 'Explain the class'}, 'test-beginner-question'))
    monkeypatch.setattr(app_v2, 'load_campaign_bounties', lambda: {'00-lantern-vale': {'project_dir': 'lantern_vale'}})
    monkeypatch.setattr(app_v2, '_studied_ideas', lambda _: [])
    app_v2.BATTLE_QUESTIONS.pop('test-beginner-question', None)
    app_v2.CHOICE_ANSWER_KEYS.pop('test-beginner-question', None)
    response = {'prompt': 'Which?', 'options': ['one', 'two'], 'answer': 0}
    with patch.object(app_v2, '_ai_call', return_value=response) as call:
        app_v2.ai_battle_question(app_v2.BattleQuestionRequest(objective_id='explain'))
        assert call.call_args.kwargs['code'] == 'MODEL_FILE = True\n'
    app_v2.BATTLE_QUESTIONS.pop('test-beginner-question', None)
    app_v2.CHOICE_ANSWER_KEYS.pop('test-beginner-question', None)


def beginner_service(tmp_path):
    use_real_content()
    path = tmp_path / 'save.json'
    path.write_text(json.dumps(user_like_progress()))
    service = state.LocalStateService(path, threading.RLock())
    service.apply_internal('campaign_extend', {})
    service.apply('select_campaign', {'branch': '00-lantern-vale'}, 'player')
    return service, path


def test_each_elite_rewards_its_own_verified_goal_once(tmp_path):
    import pytest
    for index, expected in [(4, {'guards': 1, 'coins': 0, 'healed': 0}),
                            (9, {'guards': 0, 'coins': 0, 'healed': 0}),
                            (14, {'guards': 0, 'coins': 0, 'healed': 0}),
                            (19, {'guards': 2, 'coins': 0, 'healed': 0})]:
        case = tmp_path / str(index)
        case.mkdir()
        service, path = beginner_service(case)
        save = json.loads(path.read_text())
        save['player']['hp'] = 50
        project = next(p for p in save['projects'] if p['branch'] == '00-lantern-vale')
        for i, mob in enumerate(project['mobs']):
            mob['status'] = 'defeated' if i < index else 'available' if i == index else 'locked'
        save.pop('encounter_state', None)
        path.write_text(json.dumps(save))
        preview = service.encounter_projection(save)
        special = preview['special_mechanic']
        assert special and not special['triggered']
        result = service.apply_internal('record_battle_objective', {
            'objective_id': special['trigger'], 'evidence_id': 'test-mechanic', 'reason': 'Verified by test'})['result']
        assert result['mechanic_reward'] == expected
        after = json.loads(path.read_text())
        assert after['player']['coins'] == 50 + expected['coins']
        assert after['player']['hp'] == 50 + expected['healed']
        assert service.encounter_projection(after)['special_mechanic']['triggered']
        assert not result['mob_defeated']  # a reward never skips remaining objectives
        if index == 9:
            miss = service.apply_internal('record_battle_miss', {'objective_id': 'build', 'encounter_id': 'shelter-test', 'reason': 'Miss'})['result']
            assert miss['damage'] == max(1, state.canonical_battle_raw_damage(index) - 3)
        if index == 14:
            hit = service.apply_internal('record_battle_objective', {'objective_id': 'build', 'evidence_id': 'focus-test', 'reason': 'Verified'})['result']
            assert hit['impact'] == hit['base_impact'] + 1
        with pytest.raises(state.StateCommandError):
            service.apply_internal('record_battle_objective', {
                'objective_id': special['trigger'], 'evidence_id': 'test-repeat', 'reason': 'Repeat'})


def test_boss_twist_is_a_required_phase_and_heals_once(tmp_path):
    service, path = beginner_service(tmp_path)
    save = json.loads(path.read_text())
    save['player']['hp'] = 50
    project = next(p for p in save['projects'] if p['branch'] == '00-lantern-vale')
    for mob in project['mobs']:
        mob['status'] = 'defeated'
    project['boss_status'] = 'available'
    path.write_text(json.dumps(save))
    for phase in ['required_behavior', 'explanation']:
        service.apply_internal('record_boss_requirement', {'requirement_id': phase, 'evidence_id': phase, 'reason': 'Verified'})
    projection = service.encounter_projection(json.loads(path.read_text()))
    assert projection['boss_phase'] == 'edge_cases'
    assert 'second delivery' in projection['current_quest']['quest']
    assert not projection['special_mechanic']['triggered']
    result = service.apply_internal('record_boss_requirement', {'requirement_id': 'edge_cases', 'evidence_id': 'twist', 'reason': 'Verified'})['result']
    assert result['mechanic_reward']['healed'] == 8
    assert result['boss_phase'] == 'interview'
    repeated = service.apply_internal('record_boss_requirement', {'requirement_id': 'edge_cases', 'evidence_id': 'repeat', 'reason': 'Repeat'})['result']
    assert repeated['already_verified']
    assert json.loads(path.read_text())['player']['hp'] == 58


def test_all_beginner_objectives_and_boss_phases_advance_in_order(tmp_path):
    service, path = beginner_service(tmp_path)
    for index in range(20):
        save = json.loads(path.read_text())
        encounter = service.encounter_projection(save)
        assert encounter['mob_index'] == index
        objectives = list(encounter['available_objectives'])
        for number, objective in enumerate(objectives):
            result = service.apply_internal('record_battle_objective', {
                'objective_id': objective['id'], 'evidence_id': f'e-{index}-{number}', 'reason': 'Simulated verified result'})['result']
            assert result['mob_defeated'] is (number == len(objectives) - 1)
        assert result['loot'] is not None
    for phase in ['required_behavior', 'explanation', 'edge_cases', 'interview']:
        projection = service.encounter_projection(json.loads(path.read_text()))
        assert projection['boss_phase'] == phase
        service.apply_internal('record_boss_requirement', {'requirement_id': phase, 'evidence_id': f'boss-{phase}', 'reason': 'Simulated verified result'})
    assert service.encounter_projection(json.loads(path.read_text()))['boss_phase'] == 'ready_to_clear'
    cleared = service.apply_internal('record_boss_clear', {'evidence_id': 'boss', 'explanation_evidence_id': 'read', 'interview_evidence_id': 'interview', 'reason': 'Simulated clear'})['result']
    loot = cleared['loot']
    assert any(item['slot'] == 'relic' for item in loot)
    assert any(item['tier'] == 'legendary' and item['slot'] in state.ARMORY_GEAR_SLOTS for item in loot)
