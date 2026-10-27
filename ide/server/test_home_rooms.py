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
