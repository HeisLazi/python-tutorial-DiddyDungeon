import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from ide.server.online.duel import DuelError
from ide.server.online.evaluator import Evaluation
from ide.server.online.raid import PROJECT_TASKS, RaidCoordinator
from ide.server.online.repository import MatchRepository


class Worker:
    async def evaluate(self, challenge_id, code, evaluation_id):
        return Evaluation('bad' not in code, 'All checks passed.')


class CooperativeProjectChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'online.sqlite')
        self.repo = MatchRepository(self.path)
        self.raid = RaidCoordinator(Worker(), self.repo, lambda:1000.0)
        self.group = 'group-a'
        self.members = ['player-a', 'player-b', 'player-c']
        self.created = await self.raid.create(self.group, 'player-a', self.members)
        self.raid_id = self.created['raid_id']

    async def asyncTearDown(self):
        self.repo.close()
        self.temp.cleanup()

    async def test_creator_gets_a_durable_raid_with_fair_task_assignments(self):
        assigned = [task['assignee'] for task in self.created['tasks']]
        self.assertEqual(assigned, ['player-a', 'player-b', 'player-c', 'player-a'])
        self.assertEqual((await self.raid.create(self.group, 'player-b', self.members))['raid_id'], self.raid_id)
        self.assertEqual(len(self.repo.load_raids()), 1)

    async def test_four_members_each_get_one_required_coding_task(self):
        group = 'four-player-group'
        members = ['one', 'two', 'three', 'four']
        result = await self.raid.create(group, members[0], members)
        self.assertEqual([task['assignee'] for task in result['tasks']], members)

    async def test_unsubmitted_work_can_be_volunteered_and_claimed_once(self):
        with self.assertRaises(DuelError):
            await self.raid.open_for_volunteers(self.group, 'player-b', self.raid_id, 'repair-reward')
        opened = await self.raid.open_for_volunteers(self.group, 'player-a', self.raid_id, 'repair-reward')
        self.assertEqual(opened['tasks'][0]['assignee'], '')
        self.assertTrue(opened['tasks'][0]['volunteer_open'])
        claimed = await self.raid.volunteer(self.group, 'player-b', self.raid_id, 'repair-reward')
        self.assertEqual(claimed['tasks'][0]['assignee'], 'player-b')
        self.assertFalse(claimed['tasks'][0]['volunteer_open'])
        with self.assertRaises(DuelError):
            await self.raid.volunteer(self.group, 'player-c', self.raid_id, 'repair-reward')

    async def test_blocked_work_can_be_volunteered_before_its_prerequisite_is_done(self):
        opened = await self.raid.open_for_volunteers(self.group, 'player-b', self.raid_id, 'lock-check')
        self.assertEqual(opened['tasks'][1]['status'], 'blocked')
        claimed = await self.raid.volunteer(self.group, 'player-c', self.raid_id, 'lock-check')
        self.assertEqual(claimed['tasks'][1]['assignee'], 'player-c')
        with self.assertRaises(DuelError):
            await self.raid.submit(self.group, 'player-c', self.raid_id, 'lock-check', 'early', 'def chest_reward(): pass')

    async def test_assignments_can_be_swapped_atomically_while_a_task_is_blocked(self):
        swapped = await self.raid.swap(self.group, 'player-a', self.raid_id, 'repair-reward', 'lock-check', self.members)
        self.assertEqual([task['assignee'] for task in swapped['tasks'][:2]], ['player-b', 'player-a'])
        self.assertEqual(swapped['tasks'][1]['status'], 'blocked')
        restored = RaidCoordinator(Worker(), self.repo, lambda:1001.0)
        after_restart = await restored.view(self.group, 'player-b', self.raid_id)
        self.assertEqual([task['assignee'] for task in after_restart['tasks'][:2]], ['player-b', 'player-a'])
        with self.assertRaises(DuelError):
            await restored.swap(self.group, 'outsider', self.raid_id, 'repair-reward', 'lock-check', self.members)

    async def test_task_requires_prerequisite_and_peer_review_before_advancing(self):
        with self.assertRaises(DuelError):
            await self.raid.submit(self.group, 'player-b', self.raid_id, 'lock-check', 'r1', 'source')
        await self.raid.submit(self.group, 'player-a', self.raid_id, 'repair-reward', 'r1', 'source')
        with self.assertRaises(DuelError):
            await self.raid.review(self.group, 'player-a', self.raid_id, 'repair-reward', 'approve')
        await self.raid.review(self.group, 'player-b', self.raid_id, 'repair-reward', 'approve')
        self.assertEqual((await self.raid.view(self.group, 'player-c', self.raid_id))['tasks'][0]['status'], 'accepted')

    async def test_project_waits_for_boss_before_reward_and_restores(self):
        for task, assignee in zip(PROJECT_TASKS, [row['assignee'] for row in self.created['tasks']]):
            await self.raid.submit(self.group, assignee, self.raid_id, task['id'], 'request-' + task['id'], 'def answer(): return 1')
            reviewer = next(member for member in self.members if member != assignee)
            await self.raid.review(self.group, reviewer, self.raid_id, task['id'], 'approve')
        view = await self.raid.view(self.group, 'player-a', self.raid_id)
        self.assertEqual(view['status'], 'boss_ready')
        self.assertFalse(view['reward_recorded'])
        self.assertEqual([self.repo.online_currency(self.group, member) for member in self.members], [0, 0, 0])
        self.assertEqual(self.repo.online_currency('other-group', 'player-a'), 0)
        self.repo.close()
        self.repo = MatchRepository(self.path)
        resumed = RaidCoordinator(Worker(), self.repo, lambda:1001.0)
        restored = await resumed.view(self.group, 'player-b', self.raid_id)
        self.assertEqual(restored['status'], 'boss_ready')
        self.assertFalse(restored['reward_recorded'])
        self.assertEqual(self.repo.online_currency(self.group, 'player-a'), 0)

    async def test_failed_submission_can_be_retried_but_cannot_claim_completion(self):
        result = await self.raid.submit(self.group, 'player-a', self.raid_id, 'repair-reward', 'failed-1', 'bad source')
        self.assertEqual(result['tasks'][0]['status'], 'failed')
        with self.assertRaises(DuelError):
            await self.raid.review(self.group, 'player-b', self.raid_id, 'repair-reward', 'approve')
        result = await self.raid.submit(self.group, 'player-a', self.raid_id, 'repair-reward', 'retry-1', 'correct source')
        self.assertEqual(result['tasks'][0]['status'], 'submitted')

    async def test_non_member_cannot_read_or_reassign_and_only_creator_can_abandon(self):
        with self.assertRaises(DuelError):
            await self.raid.view(self.group, 'outsider', self.raid_id)
        with self.assertRaises(DuelError):
            await self.raid.assign(self.group, 'player-a', self.raid_id, 'repair-reward', 'outsider')
        with self.assertRaises(DuelError):
            await self.raid.abandon(self.group, 'player-b', self.raid_id)
        result = await self.raid.abandon(self.group, 'player-a', self.raid_id)
        self.assertEqual(result['status'], 'abandoned')
        self.assertEqual(self.repo.online_currency(self.group, 'player-a'), 0)

    async def test_http_creation_uses_the_auth_checked_group_roster(self):
        from ide.server.online import service
        group = '00000000-0000-4000-8000-000000000020'
        members = ['00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000002']
        with patch.object(service, 'authorize_group_members', AsyncMock(return_value=(members[0], members))), \
                patch.object(service, 'raid_coordinator', self.raid):
            result = await service.create_raid(group, 'validated-session')
        self.assertEqual(result['members'], members)
        self.assertEqual(result['group_id'], group)

    async def test_http_read_does_not_leak_project_to_nonmember(self):
        from fastapi import HTTPException
        from ide.server.online import service
        group = '00000000-0000-4000-8000-000000000020'
        with patch.object(service, 'authorize_group', AsyncMock(return_value='outsider')), \
                patch.object(service, 'raid_coordinator', self.raid):
            with self.assertRaises(HTTPException):
                await service.get_raid(group, self.raid_id, 'validated-session')

    async def test_http_volunteer_and_swap_actions_use_authenticated_group_members(self):
        from ide.server.online import service
        group = '00000000-0000-4000-8000-000000000020'
        members = ['00000000-0000-4000-8000-000000000001', '00000000-0000-4000-8000-000000000002', '00000000-0000-4000-8000-000000000003']
        raid = await self.raid.create(group, members[0], members)
        raid_id = raid['raid_id']
        with patch.object(service, 'authorize_group', AsyncMock(return_value=members[0])), \
                patch.object(service, 'raid_coordinator', self.raid):
            opened = await service.open_raid_task_for_volunteers(group, raid_id,
                service.RaidTaskRequest(task_id='repair-reward'), 'owner-session')
        self.assertTrue(opened['tasks'][0]['volunteer_open'])
        with patch.object(service, 'authorize_group', AsyncMock(return_value=members[1])), \
                patch.object(service, 'raid_coordinator', self.raid):
            claimed = await service.volunteer_for_raid_task(group, raid_id,
                service.RaidTaskRequest(task_id='repair-reward'), 'member-session')
        self.assertEqual(claimed['tasks'][0]['assignee'], members[1])
        with patch.object(service, 'authorize_group_members', AsyncMock(return_value=(members[0], members))), \
                patch.object(service, 'raid_coordinator', self.raid):
            swapped = await service.swap_raid_tasks(group, raid_id,
                service.RaidTaskSwapRequest(task_id='lock-check', other_task_id='collect-chests'), 'owner-session')
        self.assertEqual(swapped['tasks'][1]['assignee'], members[2])
        self.assertEqual(swapped['tasks'][2]['assignee'], members[1])

    async def test_http_wallet_uses_the_authenticated_member_in_the_selected_group(self):
        from types import SimpleNamespace
        from ide.server.online import service
        group = '00000000-0000-4000-8000-000000000020'
        player = '00000000-0000-4000-8000-000000000001'
        with patch.object(service, 'authorize_group', AsyncMock(return_value=player)), \
                patch.object(service, 'repository', self.repo), \
                patch.object(service, 'coordinator', SimpleNamespace(storage_failed=False)):
            wallet = await service.group_wallet(group, 'validated-session')
        self.assertEqual(wallet, {'currency':'online', 'balance':0, 'earned':{'raid':0, 'pvp':0}, 'spent':0})

    async def test_http_merchant_uses_server_price_and_grants_account_item_once(self):
        from types import SimpleNamespace
        from fastapi import HTTPException
        from ide.server.online import service
        group = '00000000-0000-4000-8000-000000000020'
        player = '00000000-0000-4000-8000-000000000001'
        self.repo.connection.execute(
            "INSERT INTO online_reward_ledger(raid_id,group_id,user_id,currency,amount) VALUES(?,?,?,?,?)",
            ('raid-reward', group, player, 'online', 100),
        )
        self.repo.connection.commit()
        request = service.MerchantPurchaseRequest(item_id='online-cinder-vow')
        with patch.object(service, 'authorize_group', AsyncMock(return_value=player)), \
                patch.object(service, 'repository', self.repo), \
                patch.object(service, 'coordinator', SimpleNamespace(storage_failed=False)):
            first = await service.purchase_online_item(group, request, 'validated-session')
            retry = await service.purchase_online_item(group, request, 'validated-session')
            with self.assertRaises(HTTPException) as unknown:
                await service.purchase_online_item(group, service.MerchantPurchaseRequest(item_id='client-priced-item'), 'validated-session')
        self.assertTrue(first['purchase']['purchased'])
        self.assertFalse(retry['purchase']['purchased'])
        self.assertEqual(first['purchase']['cost'], 60)
        self.assertEqual(first['wallet']['balance'], 40)
        self.assertEqual(first['owned_ids'], ['online-cinder-vow'])
        self.assertEqual(retry['owned_ids'], ['online-cinder-vow'])
        self.assertEqual(unknown.exception.status_code, 400)

    async def _make_boss_ready(self):
        for task, assignee in zip(PROJECT_TASKS, [row['assignee'] for row in self.created['tasks']]):
            await self.raid.submit(self.group, assignee, self.raid_id, task['id'], 'ready-' + task['id'], 'def answer(): return 1')
            reviewer = next(member for member in self.members if member != assignee)
            await self.raid.review(self.group, reviewer, self.raid_id, task['id'], 'approve')

    async def test_boss_is_locked_until_all_tasks_are_reviewed_and_introduces_seated(self):
        with self.assertRaises(DuelError):
            await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        await self._make_boss_ready()
        started = await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        self.assertEqual(started['status'], 'boss_fight')
        self.assertEqual(started['boss']['name'], 'The Choef Chief')
        self.assertTrue(started['boss']['seated'])
        self.assertEqual(started['boss']['hp'], 35)
        self.assertFalse(started['reward_recorded'])

    async def test_wrong_answer_damages_only_submitter_and_first_answer_makes_chief_stand(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        result = await self.raid.submit_boss(self.group, 'player-b', self.raid_id, 'potion-afford', 'wrong-a', 'bad code')
        self.assertEqual(result['boss']['hunter_hp']['player-b'], 4)
        self.assertEqual(result['boss']['hunter_hp']['player-a'], 5)
        self.assertEqual(result['boss']['hunter_hp']['player-c'], 5)
        self.assertEqual(result['boss']['last_attack']['type'], 'single')
        self.assertEqual(result['boss']['last_attack']['target_players'], ['player-b'])
        self.assertEqual(result['boss']['hp'], 35)
        self.assertFalse(result['boss']['seated'])
        self.assertEqual(result['boss']['question_index'], 0)
        self.assertEqual(self.repo.online_currency(self.group, 'player-b'), 0)

    async def test_ordinary_mistake_on_a_followup_question_remains_single_target(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'followup-open', 'def can_buy(balance, price): return balance >= price')
        before = await self.raid.view(self.group, 'player-a', self.raid_id)
        self.assertEqual(before['boss']['question']['id'], 'potion-purchase')
        self.assertEqual(before['boss']['mechanic_attack'], 'single')
        result = await self.raid.submit_boss(self.group, 'player-c', self.raid_id, 'potion-purchase', 'followup-wrong', 'bad code')
        self.assertEqual(result['boss']['hunter_hp'], {'player-a':5, 'player-b':5, 'player-c':4})
        self.assertEqual(result['boss']['last_attack']['type'], 'single')
        self.assertEqual(result['boss']['last_attack']['target_players'], ['player-c'])

    async def test_missed_final_mechanic_damages_the_whole_party(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        afford = 'def can_buy(balance, price):\n    return balance >= price\n'
        purchase = afford + '\ndef buy_potion(balance, price):\n    if can_buy(balance, price):\n        return balance - price\n    return balance\n'
        await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'aoe-a1', afford)
        await self.raid.submit_boss(self.group, 'player-b', self.raid_id, 'potion-purchase', 'aoe-b1', purchase)
        await self.raid.resolve_boss_feint(self.group, 'player-b', self.raid_id, 'stand_firm')
        before = await self.raid.view(self.group, 'player-a', self.raid_id)
        self.assertEqual(before['boss']['mechanic_attack'], 'aoe')
        result = await self.raid.submit_boss(self.group, 'player-c', self.raid_id, 'potion-negative', 'aoe-c1', 'bad code')
        self.assertEqual(result['boss']['hunter_hp'], {'player-a':4, 'player-b':4, 'player-c':4})
        self.assertEqual(result['boss']['last_attack']['type'], 'aoe')
        self.assertEqual(result['boss']['last_attack']['damage'], 1)
        self.assertEqual(result['boss']['last_attack']['target_players'], self.members)

    async def test_correct_answers_trigger_feint_choice_then_complete_and_reward_once(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        afford = 'def can_buy(balance, price):\n    return balance >= price\n'
        purchase = afford + '\ndef buy_potion(balance, price):\n    if can_buy(balance, price):\n        return balance - price\n    return balance\n'
        await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'boss-a1', afford)
        result = await self.raid.submit_boss(self.group, 'player-b', self.raid_id, 'potion-purchase', 'boss-b1', purchase)
        self.assertTrue(result['boss']['feint_pending'])
        self.assertEqual(result['boss']['hp'], 25)
        self.assertEqual(result['boss']['last_attack']['damage'], 10)
        self.assertEqual(result['status'], 'boss_fight')
        stood = await self.raid.resolve_boss_feint(self.group, 'player-b', self.raid_id, 'stand_firm')
        self.assertEqual(stood['boss']['hp'], 10)
        self.assertEqual(stood['boss']['last_attack']['damage'], 15)
        self.assertEqual(stood['boss']['question_index'], 2)
        negative = purchase + '\n# negative prices must leave the balance unchanged\n'
        complete = await self.raid.submit_boss(self.group, 'player-c', self.raid_id, 'potion-negative', 'boss-c1', negative)
        self.assertEqual(complete['status'], 'completed')
        self.assertEqual(complete['boss']['last_attack']['damage'], 15)
        self.assertTrue(complete['reward_recorded'])
        self.assertEqual([self.repo.online_currency(self.group, member) for member in self.members], [100, 100, 100])
        self.assertEqual(self.repo.online_wallet(self.group, 'player-b'), {
            'currency':'online', 'balance':100, 'earned':{'raid':100, 'pvp':0}, 'spent':0,
        })
        duplicate = await self.raid.view(self.group, 'player-a', self.raid_id)
        self.assertEqual((await self.raid.current(self.group, 'player-b'))['raid_id'], self.raid_id)
        self.assertEqual((await self.raid.current(self.group, 'player-b'))['status'], 'completed')
        # Current group members can discover the group's completed result even
        # if they were invited after the raid roster was created. They still
        # cannot open or mutate a raid they did not participate in.
        late_member = await self.raid.current(self.group, 'group-joiner')
        self.assertEqual(late_member['raid_id'], self.raid_id)
        self.assertEqual(late_member['status'], 'completed')
        with self.assertRaises(DuelError):
            await self.raid.view(self.group, 'group-joiner', self.raid_id)
        self.assertEqual([self.repo.online_currency(self.group, member) for member in self.members], [100, 100, 100])
        self.assertEqual(duplicate['status'], 'completed')
        next_project = await self.raid.create(self.group, 'player-a', self.members)
        self.assertNotEqual(next_project['raid_id'], self.raid_id)
        self.assertEqual((await self.raid.current(self.group, 'player-b'))['raid_id'], next_project['raid_id'])
        self.assertEqual([self.repo.online_currency(self.group, member) for member in self.members], [100, 100, 100])

    async def test_withdrawing_feint_bugs_shared_code_and_requires_repair(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        afford = 'def can_buy(balance, price):\n    return balance >= price\n'
        purchase = afford + '\ndef buy_potion(balance, price):\n    if can_buy(balance, price):\n        return balance - price\n    return balance\n'
        await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'withdraw-a1', afford)
        await self.raid.submit_boss(self.group, 'player-b', self.raid_id, 'potion-purchase', 'withdraw-b1', purchase)
        changed = await self.raid.resolve_boss_feint(self.group, 'player-b', self.raid_id, 'withdraw')
        self.assertIn('return balance > price', changed['boss']['draft_source'])
        self.assertEqual(changed['boss']['question_index'], 1)
        self.assertTrue(changed['boss']['feint_used'])
        self.assertEqual(changed['boss']['mechanic_attack'], 'aoe')
        failed_repair = await self.raid.submit_boss(self.group, 'player-b', self.raid_id, 'potion-purchase', 'withdraw-bad-repair', 'bad code')
        self.assertEqual(failed_repair['boss']['hunter_hp'], {'player-a':4, 'player-b':4, 'player-c':4})
        self.assertEqual(failed_repair['boss']['last_attack']['type'], 'aoe')
        fixed = purchase + '\n# restored the exact-price check\ndef can_buy(balance, price):\n    return balance >= price\n'
        result = await self.raid.submit_boss(self.group, 'player-c', self.raid_id, 'potion-purchase', 'withdraw-b2', fixed)
        self.assertEqual(result['boss']['hp'], 15)
        self.assertEqual(result['boss']['question_index'], 2)
        self.assertFalse(result['boss']['feint_pending'])

    async def test_duplicate_boss_submission_cannot_deal_damage_twice(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        code = 'def can_buy(balance, price): return balance >= price'
        await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'same-request', code)
        duplicate = await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'same-request', code)
        self.assertEqual(duplicate['boss']['hp'], 25)
        self.assertEqual(duplicate['boss']['question_index'], 1)
        with self.assertRaises(DuelError):
            await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'same-request', code + '\n# changed')

    async def test_boss_state_resumes_after_restart_without_replaying_or_losing_progress(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        code = 'def can_buy(balance, price): return balance >= price'
        await self.raid.submit_boss(self.group, 'player-a', self.raid_id, 'potion-afford', 'resume-request', code)
        self.repo.close()
        self.repo = MatchRepository(self.path)
        self.raid = RaidCoordinator(Worker(), self.repo, lambda:1001.0)
        restored = await self.raid.view(self.group, 'player-b', self.raid_id)
        self.assertEqual(restored['status'], 'boss_fight')
        self.assertEqual(restored['boss']['hp'], 25)
        self.assertEqual(restored['boss']['question_index'], 1)
        self.assertFalse(restored['boss']['seated'])
        self.assertEqual(self.repo.online_currency(self.group, 'player-a'), 0)

    async def test_failed_party_can_restart_encounter_without_reward(self):
        await self._make_boss_ready()
        await self.raid.start_boss(self.group, 'player-a', self.raid_id)
        for index in range(15):
            player = self.members[index % len(self.members)]
            view = await self.raid.submit_boss(self.group, player, self.raid_id, 'potion-afford', f'down-{index}', 'bad code')
            if view['status'] == 'boss_failed':
                break
        self.assertEqual(view['status'], 'boss_failed')
        self.assertEqual(self.repo.online_currency(self.group, 'player-a'), 0)
        retry = await self.raid.start_boss(self.group, 'player-b', self.raid_id)
        self.assertEqual(retry['status'], 'boss_fight')
        self.assertEqual(retry['boss']['hunter_hp']['player-a'], 5)
        self.assertEqual(retry['boss']['hp'], 35)


if __name__ == '__main__':
    unittest.main()
