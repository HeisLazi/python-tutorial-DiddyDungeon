from ide.server.state import HUNTER_SETS, LocalStateService, armory_catalog
from ide.server.test_campaign_content import use_real_content


def test_set_bonuses_require_all_three_equipped_and_owned():
    use_real_content()
    catalog = armory_catalog()
    for group in HUNTER_SETS:
        weapon, armor, trinket = group['pieces']
        state = {'hunter': {'armory': {'owned': list(group['pieces']), 'weapon': weapon}},
                 'equipment': {'armor': catalog[armor]['name'], 'trinket': catalog[trinket]['name']}}
        effects = LocalStateService._gear_effects(state)
        assert effects['set_bonus'] == group['bonus']
        state['equipment']['trinket'] = 'None'
        assert LocalStateService._gear_effects(state)['set_bonus'] == {}
        state['equipment']['trinket'] = catalog[trinket]['name']
        state['hunter']['armory']['owned'].remove(trinket)
        assert LocalStateService._gear_effects(state)['set_bonus'] == {}


def test_warden_set_changes_real_gear_effects():
    use_real_content()
    catalog = armory_catalog()
    group = next(item for item in HUNTER_SETS if item['id'] == 'gravebound')
    weapon, armor, trinket = group['pieces']
    state = {'hunter': {'armory': {'owned': list(group['pieces']), 'weapon': weapon}},
             'equipment': {'armor': catalog[armor]['name'], 'trinket': catalog[trinket]['name']}}
    effects = LocalStateService._gear_effects(state)
    assert effects['reduction'] == 40
    assert effects['heal_on_objective'] == 2
    state['hunter']['armory']['weapon'] = None
    effects = LocalStateService._gear_effects(state)
    assert effects['reduction'] == 30
    assert effects['heal_on_objective'] == 1


def test_warden_pieces_can_be_bought_equipped_and_show_the_bonus(tmp_path):
    import json
    import threading
    from ide.server.test_campaign_content import user_like_progress
    use_real_content()
    state = user_like_progress()
    state['player']['coins'] = 1000
    path = tmp_path / 'progress.json'
    path.write_text(json.dumps(state))
    service = LocalStateService(path, threading.RLock())
    group = next(item for item in HUNTER_SETS if item['id'] == 'gravebound')
    for item_id in group['pieces']:
        service.apply('armory_buy', {'item_id': item_id}, 'player')
        service.apply('armory_equip', {'item_id': item_id}, 'player')
    saved = service.snapshot()
    projected = service.armory_projection(saved)
    entry = next(item for item in projected['sets'] if item['id'] == 'gravebound')
    assert entry['equipped_count'] == 3
    assert projected['summary']['reduction'] == 40
    assert projected['summary']['heal_on_objective'] == 2
