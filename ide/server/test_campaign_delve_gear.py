import json
import threading

import pytest

from ide.server.dungeon_items import REGIONAL_TRINKETS, SIGNATURE_WEAPONS
from ide.server.state import CAMPAIGN_DELVE_GEAR, HUNTER_STYLE_WEAPONS, OIL_OF_DOOM, LocalStateService, StateCommandError, armory_catalog, armory_effect_text, load_campaign_bounties
from ide.server.test_campaign_content import use_real_content, user_like_progress
from ide.server.test_dungeon_weapons import fight  # noqa: F401


def test_campaign_versions_have_unique_names_and_working_effects():
    assert sum(item['slot'] == 'weapon' for item in CAMPAIGN_DELVE_GEAR) == 15
    assert sum(item['slot'] == 'trinket' for item in CAMPAIGN_DELVE_GEAR) == 25
    assert sum(item['slot'] == 'armor' for item in CAMPAIGN_DELVE_GEAR) == 2
    assert len({item['name'] for item in CAMPAIGN_DELVE_GEAR}) == 42
    for item in (*CAMPAIGN_DELVE_GEAR, *HUNTER_STYLE_WEAPONS, OIL_OF_DOOM):
        assert item['effect']
        assert armory_effect_text(item['effect']) != 'A keepsake.'
        assert item['id'] in armory_catalog()


def test_regional_elite_and_boss_loot_stays_run_only_and_journal_grants_campaign_echo(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['region_id'] = 'collections'
    elite = service._dungeon_award_loot(run, {'room_type': 'elite', 'misses': 0}, 'lists', state)
    elite_run_id = elite['trinket']['id']
    elite_echo_id = elite['journal_unlock']['id']
    boss = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'lists', state)
    boss_echo_id = boss['journal_unlock']['id']
    boss_run_id = boss['weapon']['id']
    run_gear_ids = {item['id'] for item in (*SIGNATURE_WEAPONS, *REGIONAL_TRINKETS)}
    assert elite_run_id in run_gear_ids and boss_run_id in run_gear_ids
    assert not any(item['id'].startswith('campaign-') for item in elite['items'] + boss['items'])
    assert not any(item_id.startswith('campaign-') for item_id in run['pack'])
    assert {elite_echo_id, boss_echo_id} <= set(state['dungeon_journal']['unlocks'])
    assert {elite_echo_id, boss_echo_id} <= set(state['hunter']['armory']['owned'])
    assert state['dungeon_journal']['cleared_bosses'] == ['collections']
    banked = service._dungeon_bank_pack(run, state)
    assert not {elite_echo_id, boss_echo_id} & {item['id'] for item in banked}
    assert state['dungeon_journal']['cleared_bosses'] == ['collections']
    assert armory_catalog()[boss_echo_id]['name'] == 'Hoardbreaker Scythe'
    again = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'lists', state)
    assert 'journal_unlock' not in again
    assert state['dungeon_journal']['unlocks'].count(boss_echo_id) == 1


def test_legacy_run_pack_campaign_gear_migrates_through_journal_once(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    legacy_id = 'campaign-dungeon-village-lantern'
    run['pack'] = {legacy_id: 1, 'wraith-ash': 2}
    banked = service._dungeon_bank_pack(run, state)
    assert legacy_id in state['dungeon_journal']['unlocks']
    assert legacy_id in state['hunter']['armory']['owned']
    assert state['hunter']['materials']['wraith-ash'] == 2
    assert run['pack'] == {}
    assert legacy_id in {item['id'] for item in banked}


def test_journal_projection_roundtrips_through_bounded_cloud_campaign_schema():
    item_id = CAMPAIGN_DELVE_GEAR[0]['id']
    state = {'dungeon_journal': {'unlocks': [item_id, item_id], 'cleared_bosses': ['basics', 'basics']}}
    source = LocalStateService._campaign_source_projection(state)
    validated = LocalStateService._validate_campaign_projection(source)
    assert validated['dungeon_journal'] == {'unlocks': [item_id], 'cleared_bosses': ['basics']}
    with pytest.raises(StateCommandError):
        LocalStateService._validate_campaign_projection({'dungeon_journal': {'unlocks': ['not-a-catalog-item']}})


def test_legacy_campaign_equipment_is_removed_from_active_run_loadout(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['loadout']['weapon'] = 'Village Lantern'
    run['loadout']['armor'] = 'Gravebound Warden Plate'
    run['inventory'] = [
        {'id': 'campaign-dungeon-village-lantern', 'name': 'Village Lantern', 'kind': 'weapon', 'weapon': 'Village Lantern'},
        {'id': 'hunter-gravebound-plate', 'name': 'Gravebound Warden Plate', 'kind': 'armor', 'armor': 'Gravebound Warden Plate'},
    ]
    projected = service.dungeon_projection(state)
    assert projected['loadout']['weapon'] == 'Aether Staff'
    assert projected['loadout']['armor'] == 'Apprentice Coat'
    assert not any(item['id'].startswith(('campaign-', 'hunter-')) for item in projected['inventory'])
    service._active_dungeon_run(state)
    assert run['loadout']['weapon'] == 'Aether Staff'
    assert run['loadout']['armor'] == 'Apprentice Coat'
    assert not any(item['id'].startswith(('campaign-', 'hunter-')) for item in run['inventory'])


def test_diddy_drops_oil_and_relic_once_without_affecting_other_bosses(tmp_path):
    use_real_content()
    path = tmp_path / 'progress.json'
    state = user_like_progress()
    path.write_text(json.dumps(state))
    service = LocalStateService(path, threading.RLock())
    project = {'branch': '04-casino-slots', 'boss': 'Ekse Ouens P Diddy'}
    drops = service._armory_boss_loot(state, project)
    assert OIL_OF_DOOM['id'] in {item['id'] for item in drops}
    assert any(item['slot'] == 'relic' for item in drops)
    assert OIL_OF_DOOM['id'] in state['hunter']['armory']['owned']
    again = service._armory_boss_loot(state, project)
    assert OIL_OF_DOOM['id'] not in {item['id'] for item in again}
    other = service._armory_boss_loot(user_like_progress(), {'branch': '01-blackjack'})
    assert OIL_OF_DOOM['id'] not in {item['id'] for item in other}


def test_authored_campaign_elite_drops_its_named_trinket(tmp_path):
    use_real_content()
    state = user_like_progress()
    service = LocalStateService(tmp_path / 'progress.json', threading.RLock())
    story = load_campaign_bounties()['00-lantern-vale']
    elite = next(mob for mob in story['mobs'] if mob.get('tier') == 'elite')
    loot = service._armory_contract_drop(state, {'branch': '00-lantern-vale'}, story['mobs'], 0, elite, 'elite-evidence')
    assert loot['slot'] == 'trinket'
    assert loot['id'] == 'elite-00-lantern-vale-echo-knot'
    assert loot['id'] in state['hunter']['armory']['owned']


def test_already_defeated_diddy_makes_the_bottle_available_to_equip(tmp_path):
    state = user_like_progress()
    state['projects'].append({'branch': '04-casino-slots', 'boss_status': 'defeated'})
    path = tmp_path / 'progress.json'
    path.write_text(json.dumps(state))
    service = LocalStateService(path, threading.RLock())
    assert OIL_OF_DOOM['id'] in {item['id'] for item in service.armory_projection(state)['items']}
    result = service.apply('armory_equip', {'item_id': OIL_OF_DOOM['id']}, 'player')['result']
    assert result['armory']['weapon']['id'] == OIL_OF_DOOM['id']
    assert OIL_OF_DOOM['id'] in json.loads(path.read_text())['hunter']['armory']['owned']


def test_relics_apply_passively_and_weapon_effects_are_projected(tmp_path):
    use_real_content()
    state = user_like_progress()
    service = LocalStateService(tmp_path / 'progress.json', threading.RLock())
    service._armory_boss_loot(state, {'branch': '04-casino-slots'})
    effects = service._gear_effects(state)
    assert effects['xp_bonus'] > 0 and effects['coin_bonus'] > 0
    state['hunter']['armory']['weapon'] = OIL_OF_DOOM['id']
    weapon = service.armory_projection(state)['weapon']
    assert weapon['combat_style'] == 'oil'
    assert '+2 impact' in weapon['effect'].lower()
