"""Bosses four to eight each add one small run-only perk to every future run."""
import json
import tempfile
import threading
from pathlib import Path

import pytest

from ide.server.state import DUNGEON_REGIONS, JOURNAL_BOSS_PERKS, LocalStateService
from ide.server.test_state_service import fixture_progress

REGIONS = list(DUNGEON_REGIONS)
EXTRAS = ('starting_coins', 'starting_vision_scrolls', 'starting_heals', 'starting_rations', 'starting_tonics')


def projection(count):
    return LocalStateService._dungeon_journal_projection({'dungeon_journal': {'unlocks': [], 'cleared_bosses': REGIONS[:count]}})


def test_each_boss_after_the_third_adds_exactly_one_perk():
    seen = projection(3)['bonuses']
    assert {key: seen[key] for key in EXTRAS} == dict.fromkeys(EXTRAS, 0)
    previous = seen
    for count in range(4, len(REGIONS) + 1):
        bonuses = projection(count)['bonuses']
        key, amount, _ = JOURNAL_BOSS_PERKS[count]
        assert bonuses[key] == amount
        changed = {name for name in bonuses if bonuses[name] != previous[name]}
        assert changed == {key}, (count, changed)
        previous = bonuses
    assert previous == {'starting_hp': 15, 'starting_bandages': 1, 'starting_coins': 10, 'starting_vision_scrolls': 1,
                        'starting_heals': 1, 'starting_rations': 1, 'starting_tonics': 1}


def test_the_title_and_milestone_follow_the_boss_count():
    assert projection(7)['title'] is None
    assert projection(8)['title'] == 'Master Delver'
    assert '+10 starting run coins' in projection(3)['next_milestone']
    assert '4 bosses remaining' in projection(4)['next_milestone']
    assert 'Master Delver' in projection(8)['next_milestone']
    ladder = projection(5)['perks']
    assert [row['boss'] for row in ladder] == list(range(1, 9))
    assert [row['earned'] for row in ladder] == [True] * 5 + [False] * 3


def test_perks_stay_small_next_to_a_runs_economy():
    bonuses = projection(len(REGIONS))['bonuses']
    assert bonuses['starting_coins'] <= 10 and all(bonuses[key] <= 1 for key in EXTRAS if key != 'starting_coins')


@pytest.fixture
def service():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'progress.json'
        path.write_text(json.dumps(fixture_progress()))
        yield LocalStateService(path, threading.RLock()), path


def start_with_bosses(service, path, count):
    state = json.loads(path.read_text())
    state['dungeon_journal'] = {'unlocks': [], 'cleared_bosses': REGIONS[:count]}
    path.write_text(json.dumps(state))
    run = service.apply('dungeon_start_run', {'concept_id': 'loops', 'seed': f'perks-{count}'}, 'player')['result']['run']
    return run, json.loads(path.read_text())['dungeon_run']


def test_a_run_starts_with_the_perks_the_journal_has_earned(service):
    service, path = service
    base_run, base = start_with_bosses(service, path, 0)
    assert (base['loadout']['vision_scrolls'], base['loadout']['tonics']) == (0, 0)
    base_coins, base_heals, base_rations = base['run_coins'], base['loadout']['heals'], base['loadout']['rations']
    state = json.loads(path.read_text()); state['dungeon_run'] = None; path.write_text(json.dumps(state))
    _, full = start_with_bosses(service, path, len(REGIONS))
    loadout = full['loadout']
    assert full['run_coins'] == base_coins + 10 and loadout['coins'] == base['loadout']['coins'] + 10
    assert (loadout['vision_scrolls'], loadout['tonics']) == (1, 1)
    assert (loadout['heals'], loadout['rations']) == (base_heals + 1, base_rations + 1)
    assert (loadout['max_hp'], loadout['bandages']) == (115, 2)


def test_clearing_a_boss_reports_the_new_perk_once(service):
    service, path = service
    state = json.loads(path.read_text())
    state['dungeon_journal'] = {'unlocks': [], 'cleared_bosses': REGIONS[1:4]}
    path.write_text(json.dumps(state))
    service.apply('dungeon_start_run', {'concept_id': 'loops', 'seed': 'perk-loot'}, 'player')
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['region_id'] = REGIONS[0]
    loot = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'lists', state)
    assert loot['journal_perk'] == '+10 starting run coins'
    assert loot['journal_bonus']['starting_coins'] == 10
    again = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'lists', state)
    assert 'journal_perk' not in again
