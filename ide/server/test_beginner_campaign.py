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
