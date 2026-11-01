import json
import threading

from ide.server.dungeon_items import REGIONAL_TRINKETS, SIGNATURE_WEAPONS
from ide.server.state import CAMPAIGN_DELVE_GEAR, HUNTER_STYLE_WEAPONS, OIL_OF_DOOM, LocalStateService, armory_catalog, armory_effect_text, load_campaign_bounties
from ide.server.test_campaign_content import use_real_content, user_like_progress
from ide.server.test_dungeon_weapons import fight  # noqa: F401


def test_campaign_versions_have_unique_names_and_working_effects():
    assert sum(item['slot'] == 'weapon' for item in CAMPAIGN_DELVE_GEAR) == 15
    assert sum(item['slot'] == 'trinket' for item in CAMPAIGN_DELVE_GEAR) == 25
    assert len({item['name'] for item in CAMPAIGN_DELVE_GEAR}) == 40
    for item in (*CAMPAIGN_DELVE_GEAR, *HUNTER_STYLE_WEAPONS, OIL_OF_DOOM):
        assert item['effect']
        assert armory_effect_text(item['effect']) != 'A keepsake.'
        assert item['id'] in armory_catalog()


def test_regional_elite_and_boss_gear_is_banked_not_granted_early(fight):
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['region_id'] = 'collections'
    elite = service._dungeon_award_loot(run, {'room_type': 'elite', 'misses': 0}, 'lists', state)
    boss = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'lists', state)
    elite_id = next(item['id'] for item in elite['items'] if item['id'].startswith('campaign-dungeon-'))
    boss_id = 'campaign-' + next(item['id'] for item in SIGNATURE_WEAPONS if item['region'] == 'collections')
    assert boss_id in {item['id'] for item in boss['items']}
    assert elite_id in {'campaign-' + item['id'] for item in REGIONAL_TRINKETS if item['region'] == 'collections'}
    assert elite_id not in (state.get('hunter') or {}).get('armory', {}).get('owned', [])
    banked = service._dungeon_bank_pack(run, state)
    assert {elite_id, boss_id} <= {item['id'] for item in banked}
    assert {elite_id, boss_id} <= set(state['hunter']['armory']['owned'])
    assert armory_catalog()[boss_id]['name'] == 'Hoardbreaker Scythe'
    again = service._dungeon_award_loot(run, {'room_type': 'boss', 'misses': 0}, 'lists', state)
    assert boss_id not in {item['id'] for item in again['items']}


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


def test_authored_campaign_elite_drops_a_permanent_delver_trinket(tmp_path):
    use_real_content()
    state = user_like_progress()
    service = LocalStateService(tmp_path / 'progress.json', threading.RLock())
    story = load_campaign_bounties()['00-lantern-vale']
    elite = next(mob for mob in story['mobs'] if mob.get('tier') == 'elite')
    loot = service._armory_contract_drop(state, {'branch': '00-lantern-vale'}, story['mobs'], 0, elite, 'elite-evidence')
    assert loot['slot'] == 'trinket'
    assert loot['id'].startswith('campaign-dungeon-')
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
