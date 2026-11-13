import json
import threading

import pytest

from ide.server.dungeon_items import GEAR_BY_NAME, REGIONAL_ARMOURS, REGIONAL_TRINKETS, SIGNATURE_WEAPONS
from ide.server.state import DUNGEON_CLASSES_BY_ID, DUNGEON_MARKET_CATALOG, DUNGEON_REGIONS, MAX_DUNGEON_INVENTORY, LocalStateService, StateCommandError
from ide.server.test_dungeon_weapons import fight, answer, change


def update(path, **values):
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['loadout'].update(values)
    if isinstance(values.get('armor'), str):
        armor = next(item for item in DUNGEON_MARKET_CATALOG if item.get('armor') == values['armor'])
        run.setdefault('inventory', []).append({
            'id': armor['id'], 'name': armor['name'], 'kind': 'armor',
            'armor': armor['armor'], 'description': armor['description'],
        })
    path.write_text(json.dumps(state))


def test_catalog_has_distinct_items_in_every_region():
    assert (len(SIGNATURE_WEAPONS), len(REGIONAL_ARMOURS), len(REGIONAL_TRINKETS)) == (8, 11, 25)
    items = (*SIGNATURE_WEAPONS, *REGIONAL_ARMOURS, *REGIONAL_TRINKETS)
    assert len({item['id'] for item in items}) == len(items)
    for region in DUNGEON_REGIONS:
        assert len([item for item in SIGNATURE_WEAPONS if item['region'] == region]) == 1
        assert any(item['region'] == region for item in REGIONAL_ARMOURS)
        assert len([item for item in REGIONAL_TRINKETS if item['region'] == region]) >= 3


def test_legacy_campaign_loadout_is_scrubbed_from_projection_and_checkpoint_migration(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['inventory'] = None
    run['loadout'].update(weapon="Hunter's Greatsword", armor='Debugger Plate', trinket='Soul Lantern')
    starter_weapon = DUNGEON_CLASSES_BY_ID[run['class_id']]['starter_weapon']
    path.write_text(json.dumps(state))

    projected = service.dungeon_projection(json.loads(path.read_text()))
    assert projected['loadout']['weapon'] == starter_weapon
    assert projected['loadout']['armor'] == 'Apprentice Coat'
    assert projected['loadout']['trinket'] is None
    assert all(item['name'] not in {"Hunter's Greatsword", 'Debugger Plate', 'Soul Lantern'} for item in projected['inventory'])

    migrated = json.loads(path.read_text())['dungeon_run']
    service._dungeon_ensure_loadout_defaults(migrated)
    assert migrated['loadout']['weapon'] == starter_weapon
    assert migrated['loadout']['armor'] == 'Apprentice Coat'
    assert all(item['name'] not in {"Hunter's Greatsword", 'Debugger Plate', 'Soul Lantern'} for item in migrated['inventory'])


def test_dungeon_inventory_rebuilds_item_data_from_run_catalog(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    starter = DUNGEON_CLASSES_BY_ID[run['class_id']]
    starter_weapon = starter['starter_weapon']
    target_weapon = next(item for item in DUNGEON_MARKET_CATALOG if item['kind'] == 'weapon' and item['weapon'] != starter_weapon)
    run['inventory'] = [
        {'id': target_weapon['id'], 'name': "Hunter's Greatsword", 'kind': 'weapon', 'weapon': "Hunter's Greatsword", 'description': 'forged from campaign gear'},
        {'id': 'dungeon-starter-armor', 'name': 'Debugger Plate', 'kind': 'armor', 'armor': 'Debugger Plate', 'description': 'campaign plate'},
    ]
    run['loadout'].update(weapon="Hunter's Greatsword", armor='Debugger Plate')
    path.write_text(json.dumps(state))

    result = service.apply('dungeon_equip_item', {'run_id': run['run_id'], 'item_id': target_weapon['id']}, 'player')['result']['run']
    assert result['loadout']['weapon'] == target_weapon['weapon']
    assert result['loadout']['armor'] == 'Apprentice Coat'
    assert {item['name'] for item in result['inventory']} == {starter_weapon, target_weapon['name'], 'Apprentice Coat'}
    saved = json.loads(path.read_text())['dungeon_run']
    assert {item['name'] for item in saved['inventory']} == {starter_weapon, target_weapon['name'], 'Apprentice Coat'}


def test_field_jacket_reduces_actual_failed_answer_damage(fight):
    service, path = fight
    change(path, 'Loopblade')
    update(path, armor='Field Jacket')
    result = answer(service, path, 'incorrect', 'jacket-test')
    assert result['damage'] == 4  # elite difficulty 3: 10 damage minus 6
    assert 'blocked 6 damage' in result['fight']['weapon_effect']


def test_syntax_cuirass_only_reduces_first_failure_per_floor(fight):
    service, path = fight
    change(path, 'Loopblade')
    update(path, armor='Syntax Cuirass')
    first = answer(service, path, 'incorrect', 'cuirass-1')
    state = json.loads(path.read_text())
    state['dungeon_run']['history'] = []  # truncated history cannot reset the floor effect
    assert LocalStateService._validate_campaign_projection(LocalStateService._campaign_source_projection(state))['dungeon_run']['gear_first_miss_floor'] == 1
    path.write_text(json.dumps(state))
    second = answer(LocalStateService(path, threading.RLock()), path, 'incorrect', 'cuirass-2')
    assert first['damage'] == 5
    assert second['damage'] == 10


def test_damage_banking_stores_actual_damage_and_spends_on_next_correct(fight):
    service, path = fight
    change(path, 'Undertow Scythe')
    bad = answer(service, path, 'incorrect', 'bank-1')
    state = json.loads(path.read_text())
    assert state['dungeon_run']['gear_charge'] == min(10, bad['damage'])
    synced = LocalStateService._validate_campaign_projection(LocalStateService._campaign_source_projection(state))['dungeon_run']
    assert synced['gear_charge'] == state['dungeon_run']['gear_charge']
    assert synced['gear_charge_weapon'] == 'Undertow Scythe'
    good = answer(service, path, 'correct', 'bank-2')
    assert f"+{min(10, bad['damage'])} Resolve" in good['fight']['weapon_effect']
    assert json.loads(path.read_text())['dungeon_run']['gear_charge'] == 0


def test_revive_is_once_per_run_even_after_reopening(fight):
    service, path = fight
    change(path, 'The Last Page', hp=1)
    first = answer(service, path, 'incorrect', 'revive-1')
    assert first['run']['active'] is True
    assert first['run']['loadout']['hp'] == 25
    assert 'revived you' in first['fight']['weapon_effect']
    state = json.loads(path.read_text())
    assert state['dungeon_run']['gear_revive_used'] is True
    sync = LocalStateService._campaign_source_projection(state)
    assert LocalStateService._validate_campaign_projection(sync)['dungeon_run']['gear_revive_used'] is True
    state['dungeon_run']['loadout']['hp'] = 1
    path.write_text(json.dumps(state))
    second = answer(LocalStateService(path, threading.RLock()), path, 'incorrect', 'revive-2')
    assert second['run_died'] is True


@pytest.mark.parametrize('region', list(DUNGEON_REGIONS))
def test_elites_and_bosses_award_their_own_region_items(fight, region):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['region_id'] = region
    elite = service._dungeon_award_loot(run, {'room_type': 'elite', 'misses': 0}, 'loops', state)
    assert elite['trinket']['id'] in {item['id'] for item in REGIONAL_TRINKETS if item['region'] == region}
    boss = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'loops', state)
    assert boss['weapon']['id'] in {item['id'] for item in SIGNATURE_WEAPONS if item['region'] == region}
    assert boss['weapon']['id'] in {item['id'] for item in run['inventory']}
    again = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'loops', state)
    assert 'weapon' not in again


def test_market_cannot_buy_another_regions_armour(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['room_type'] = 'market'
    run['region_id'] = 'basics'
    run['run_coins'] = 1000
    path.write_text(json.dumps(state))
    other = next(item for item in REGIONAL_ARMOURS if item['region'] == 'hollow')
    with pytest.raises(StateCommandError, match='not available'):
        service.apply('dungeon_market_purchase', {'run_id': run['run_id'], 'item_id': other['id']}, 'player')
    available = next(item for item in REGIONAL_ARMOURS if item['region'] == 'basics')
    result = service.apply('dungeon_market_purchase', {'run_id': run['run_id'], 'item_id': available['id']}, 'player')['result']
    assert result['run']['loadout']['armor'] == available['name']
    assert result['run']['run_coins'] == 1000 - available['price']


def test_regional_market_trinket_purchase_is_not_awarded_again(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run.update(room_type='market', region_id='collections', run_coins=1000)
    path.write_text(json.dumps(state))
    trinkets = [item for item in service._dungeon_market_catalog('collections') if item['kind'] == 'trinket']
    regional = next(item for item in trinkets if item.get('region') == 'collections')
    result = service.apply('dungeon_market_purchase', {'run_id': run['run_id'], 'item_id': regional['id']}, 'player')['result']
    assert result['run']['loadout']['trinket'] == regional['name']
    assert result['run']['run_coins'] == 1000 - regional['price']
    state = json.loads(path.read_text())
    award = service._dungeon_award_loot(state['dungeon_run'], {'room_type': 'elite', 'misses': 0}, 'loops', state)
    assert award['trinket']['id'] != regional['id']


def test_effect_catalog_values_are_bounded():
    assert len(GEAR_BY_NAME) == 44
    assert MAX_DUNGEON_INVENTORY >= len(GEAR_BY_NAME)
    for item in GEAR_BY_NAME.values():
        assert all(isinstance(value, int) and 0 < value <= 100 for value in item['effects'].values())


def test_test_mode_gives_a_fresh_run_all_equipment(monkeypatch, tmp_path):
    from ide.server.test_state_service import fixture_progress
    monkeypatch.setenv('QUESTLAB_TEST_UNLOCKS', '1')
    path = tmp_path / 'progress.json'
    path.write_text(json.dumps(fixture_progress()))
    service = LocalStateService(path, threading.RLock())
    run = service.apply('dungeon_start_run', {'region_id': 'basics'}, 'player')['result']['run']
    ids = {item['id'] for item in run['inventory']}
    assert {item['id'] for item in (*SIGNATURE_WEAPONS, *REGIONAL_ARMOURS, *REGIONAL_TRINKETS)} <= ids
    assert run['run_coins'] == 100000
    assert run['loadout']['vision_scrolls'] == 50
