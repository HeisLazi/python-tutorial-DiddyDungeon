"""Armour and shop-weapon echoes follow "prove it in battle": win a boss using the gear."""
import json

from ide.server.state import CAMPAIGN_DELVE_GEAR, DUNGEON_MARKET_CATALOG, armory_catalog
from ide.server.test_dungeon_weapons import fight  # noqa: F401

BOSS = {'room_type': 'boss', 'misses': 0}
ARMOUR_ECHO = 'campaign-dungeon-lantern-coat'
WARD_ECHO = 'campaign-dungeon-pilgrim-ward'
BLADE_ECHO = 'campaign-dungeon-loopblade'


def equip(run, item_id):
    """Hold and equip a market item the way a purchase does."""
    item = next(entry for entry in DUNGEON_MARKET_CATALOG if entry['id'] == item_id)
    entry = {key: item[key] for key in ('id', 'name', 'kind', 'weapon', 'armor', 'trinket', 'description') if key in item}
    run['inventory'] = [held for held in run.get('inventory') or [] if held['id'] != item_id] + [entry]
    run['loadout'][item['kind']] = item[item['kind']]


def start(fight_fixture, region='basics'):
    service, path = fight_fixture
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run['region_id'] = region
    service._dungeon_ensure_loadout_defaults(run)
    return service, state, run


def proofs(loot):
    return [echo['id'] for echo in loot.get('journal_proofs', [])]


def test_winning_the_basics_boss_in_its_armour_unlocks_the_echo_once(fight):
    service, state, run = start(fight)
    equip(run, 'dungeon-lantern-coat')
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert ARMOUR_ECHO in proofs(loot)
    assert ARMOUR_ECHO in state['dungeon_journal']['unlocks']
    assert ARMOUR_ECHO in state['hunter']['armory']['owned']
    assert armory_catalog()[ARMOUR_ECHO]['name'] == 'Lanternkeeper’s Coat'
    again = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert 'journal_proofs' not in again
    assert state['dungeon_journal']['unlocks'].count(ARMOUR_ECHO) == 1


def test_other_basics_armour_unlocks_only_its_own_echo(fight):
    service, state, run = start(fight)
    equip(run, 'dungeon-pilgrim-ward')
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert proofs(loot) == [WARD_ECHO]
    assert ARMOUR_ECHO not in state['dungeon_journal']['unlocks']


def test_regional_armour_does_not_count_at_another_regions_boss(fight):
    service, state, run = start(fight, region='collections')
    equip(run, 'dungeon-lantern-coat')
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert 'journal_proofs' not in loot
    assert ARMOUR_ECHO not in state['dungeon_journal']['unlocks']


def test_starter_armour_and_fights_that_are_not_bosses_unlock_nothing(fight):
    service, state, run = start(fight)
    assert run['loadout']['armor'] == 'Apprentice Coat'
    assert 'journal_proofs' not in service._dungeon_award_loot(run, BOSS, 'lists', state)
    equip(run, 'dungeon-lantern-coat')
    for room_type in ('encounter', 'elite'):
        loot = service._dungeon_award_loot(run, {'room_type': room_type, 'misses': 0}, 'lists', state)
        assert 'journal_proofs' not in loot
    assert ARMOUR_ECHO not in state['dungeon_journal']['unlocks']


def test_armour_that_is_only_named_in_the_loadout_does_not_count(fight):
    service, state, run = start(fight)
    run['loadout']['armor'] = 'Lantern Coat'  # equipped by name but never bought or held
    run['inventory'] = [entry for entry in run['inventory'] if entry['id'] != 'dungeon-lantern-coat']
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert 'journal_proofs' not in loot


def test_a_bought_market_weapon_earns_its_echo_at_any_boss(fight):
    service, state, run = start(fight, region='flow')
    equip(run, 'dungeon-loopblade')
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert BLADE_ECHO in proofs(loot)
    assert BLADE_ECHO in state['hunter']['armory']['owned']


def test_the_class_starter_weapon_does_not_count(fight):
    service, state, run = start(fight)
    starter_id = 'dungeon-aether-staff'
    assert run['loadout']['weapon'] == 'Aether Staff'
    assert any(entry['id'] == starter_id for entry in run['inventory'])
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert 'campaign-' + starter_id not in proofs(loot)
    assert 'campaign-' + starter_id not in state['dungeon_journal']['unlocks']


def test_the_weapon_must_be_equipped_not_just_carried(fight):
    service, state, run = start(fight)
    equip(run, 'dungeon-loopblade')
    run['loadout']['weapon'] = 'Aether Staff'
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert BLADE_ECHO not in proofs(loot)


def test_boss_signature_weapon_still_unlocks_alongside_the_armour_echo(fight):
    service, state, run = start(fight)
    equip(run, 'dungeon-lantern-coat')
    loot = service._dungeon_award_loot(run, BOSS, 'lists', state)
    assert loot['journal_unlock']['id'] == 'campaign-dungeon-dawn-lantern'
    assert proofs(loot) == [ARMOUR_ECHO]
    assert {'campaign-dungeon-dawn-lantern', ARMOUR_ECHO} <= set(state['dungeon_journal']['unlocks'])


def test_armour_echoes_are_friendly_campaign_gear_with_their_own_role(fight):
    echoes = [item for item in CAMPAIGN_DELVE_GEAR if item['slot'] == 'armor']
    assert [item['id'] for item in echoes] == [ARMOUR_ECHO, WARD_ECHO]
    for item in echoes:
        assert item['effect']  # every armour has a role of its own, not just damage reduction
        assert set(item['mode_eligibility']) == {'campaign', 'sparring', 'pvp'}
        assert item['region'] == 'basics'
        assert armory_catalog()[item['id']]['slot'] == 'armor'


def test_buying_in_the_market_then_winning_the_boss_unlocks_the_echoes(fight):
    """The real path: buy through the market command, equip by purchase, then clear the boss."""
    service, path = fight
    state = json.loads(path.read_text())
    run = state['dungeon_run']
    run.update(room_type='market', region_id='basics', run_coins=1000)
    path.write_text(json.dumps(state))
    for item_id in ('dungeon-pilgrim-ward', 'dungeon-loopblade'):
        service.apply('dungeon_market_purchase', {'run_id': run['run_id'], 'item_id': item_id}, 'player')
    state = json.loads(path.read_text())
    assert state['dungeon_run']['loadout']['armor'] == 'Pilgrim Ward'
    assert state['dungeon_run']['loadout']['weapon'] == 'Loopblade'
    loot = service._dungeon_award_loot(state['dungeon_run'], BOSS, 'lists', state)
    assert set(proofs(loot)) == {WARD_ECHO, BLADE_ECHO}
    assert {WARD_ECHO, BLADE_ECHO} <= set(state['hunter']['armory']['owned'])
