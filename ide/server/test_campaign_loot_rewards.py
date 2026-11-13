import json
import threading

import pytest

from ide.server.state import CAMPAIGN_BOSS_GEAR, CAMPAIGN_ELITE_TRINKETS, HOME_ROOM_UPGRADE_CATALOG, LocalStateService, StateCommandError, armory_catalog, load_campaign_bounties
from ide.server.test_campaign_content import use_real_content, user_like_progress


def service_for(tmp_path):
    use_real_content()
    path = tmp_path / 'progress.json'
    path.write_text(json.dumps(user_like_progress()))
    return LocalStateService(path, threading.RLock())


def test_elite_clear_awards_named_trinket_and_spendable_ember(tmp_path):
    service = service_for(tmp_path)
    progress = user_like_progress()
    story = load_campaign_bounties()['00-lantern-vale']
    elite = next(dict(mob, status='available') for mob in story['mobs'] if mob.get('tier') == 'elite')
    project = {'branch': story['branch'], 'name': story['name'], 'boss': story['boss'], 'mobs': [elite]}
    progress['projects'] = [project]
    progress['homestead'] = {'upgrade_tokens': 0}
    result = service._finish_mob(progress, project, project['mobs'], 0, elite, {'pyr_assists': 2}, evidence_id='elite-test', reason='verified')
    assert result['loot']['id'] == 'elite-00-lantern-vale-echo-knot'
    assert result['embers'] == 8 and result['reward_scale'] == 100
    assert progress['homestead']['upgrade_tokens'] == 8
    assert result['loot']['id'] in {item['id'] for item in service.armory_projection(progress)['items']}
    service._armory_equip({'item_id': result['loot']['id']}, progress)
    assert progress['equipment']['trinket'] == result['loot']['name']
    upgrade = next(item for item in HOME_ROOM_UPGRADE_CATALOG if item['cost'] == 1)
    service._homestead_room_upgrade({'upgrade_id': upgrade['id']}, progress)
    assert progress['homestead']['upgrade_tokens'] == 7


@pytest.mark.parametrize('branch', list(CAMPAIGN_BOSS_GEAR))
def test_boss_reward_and_history_are_fixed_and_no_trinkets(tmp_path, branch):
    service = service_for(tmp_path)
    progress = user_like_progress()
    story = load_campaign_bounties()[branch]
    project = {'branch': branch, 'name': story['name'], 'boss': story['boss'], 'status': 'active', 'boss_status': 'available', 'mobs': [{'name': m['name'], 'status': 'defeated'} for m in story['mobs']]}
    progress['projects'] = [project]
    progress['homestead'] = {'upgrade_tokens': 0}
    result = service._record_boss_clear({'evidence_id': 'boss-test', 'explanation_evidence_id': 'explain-test', 'interview_evidence_id': 'interview-test', 'reason': 'verified'}, progress).result
    drops = result['loot']
    assert set(CAMPAIGN_BOSS_GEAR[branch]) <= {item['id'] for item in drops}
    assert not any(item['slot'] == 'trinket' for item in drops)
    assert result['embers'] == 20 and progress['homestead']['upgrade_tokens'] == 20
    assert {armory_catalog()[item]['slot'] for item in CAMPAIGN_BOSS_GEAR[branch]} == {'weapon', 'armor', 'relic'}
    # Completing the final active campaign advances it, so a replay has no
    # active project to clear and must not pay out again.
    with pytest.raises(StateCommandError):
        service._record_boss_clear({'evidence_id': 'boss-test', 'explanation_evidence_id': 'explain-test', 'interview_evidence_id': 'interview-test', 'reason': 'verified'}, progress)
    assert progress['homestead']['upgrade_tokens'] == 20
    for item_id in CAMPAIGN_BOSS_GEAR[branch][:2]:
        service._armory_equip({'item_id': item_id}, progress)


def test_all_authored_elites_have_distinct_keepsakes():
    use_real_content()
    stories = load_campaign_bounties()
    authored = {(branch, mob['name']) for branch, story in stories.items() for mob in story['mobs'] if mob.get('tier') == 'elite'}
    assert authored <= set(CAMPAIGN_ELITE_TRINKETS)
    assert len({(branch, data[0]) for (branch, _), data in CAMPAIGN_ELITE_TRINKETS.items()}) == len(CAMPAIGN_ELITE_TRINKETS)


def test_legacy_clear_recovers_gear_without_granting_embers(tmp_path):
    service = service_for(tmp_path)
    progress = user_like_progress()
    branch = '00-lantern-vale'
    elite_name = next(name for campaign, name in CAMPAIGN_ELITE_TRINKETS if campaign == branch)
    progress['projects'] = [{'branch': branch, 'boss_status': 'defeated', 'mobs': [{'name': elite_name, 'status': 'defeated'}]}]
    progress['homestead'] = {'upgrade_tokens': 0}
    items = {item['id'] for item in service.armory_projection(progress)['items']}
    elite_id = 'elite-' + branch + '-' + CAMPAIGN_ELITE_TRINKETS[(branch, elite_name)][0]
    assert {elite_id, *CAMPAIGN_BOSS_GEAR[branch]} <= items
    assert progress['homestead']['upgrade_tokens'] == 0
    service._armory_equip({'item_id': elite_id}, progress)
    assert elite_id in progress['hunter']['armory']['owned']
