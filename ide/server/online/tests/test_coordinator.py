import asyncio
import unittest

from ide.server.online.coordinator import DuelCoordinator
from ide.server.online.duel import DuelError
from ide.server.online.evaluator import Evaluation, EvaluatorUnavailable


class Worker:
    async def evaluate(self, challenge_id, code, evaluation_id):
        return Evaluation(code == 'correct', 'private worker details')

    async def practice(self, code, stdin, request_id):
        return {'output': f'{code}:{stdin}', 'exit_code':0, 'reason':'finished'}


class BadWorker:
    async def evaluate(self, challenge_id, code, evaluation_id):
        raise RuntimeError('worker unavailable')


class CoordinatorChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.now = 1000.0
        self.coordinator = DuelCoordinator(Worker(), lambda: self.now)
        invitation = await self.coordinator.invite('group', 'host', 'guest', 'potion')
        self.invitation = invitation['invite_id']
        self.match = (await self.coordinator.accept('group', 'guest', self.invitation))['match_id']
        await self.coordinator.loadout('group', 'host', self.match, {})
        await self.coordinator.loadout('group', 'guest', self.match, {})

    async def test_private_exchange_and_recovery(self):
        c = self.coordinator
        initial = await c.view('group', 'host', self.match)
        self.assertEqual(initial['phase'], 'coding')
        self.assertNotIn('checks', initial['challenge'])
        with self.assertRaises(DuelError):
            await c.view('group', 'intruder', self.match)
        first = await c.submit('group', 'host', self.match, 'attack', 'correct')
        self.assertEqual(first['phase'], 'coding')
        self.assertIsNone(first['exchange'])
        second = await c.submit('group', 'guest', self.match, 'guard', 'wrong')
        self.assertEqual(second['phase'], 'exchange')
        self.assertEqual(second['you']['hp'], 70)  # 30 + 10 - 10
        self.assertEqual(second['opponent']['hp'], 100)
        self.assertFalse(second['exchange']['passed'])
        self.assertNotIn('private worker details', repr(second))
        await c.ready('group', 'host', self.match)
        bonus = await c.ready('group', 'guest', self.match)
        self.assertEqual(bonus['phase'], 'bonus')
        self.assertNotIn('answer', bonus['bonus_question'])
        first_bonus = await c.bonus('group', 'host', self.match, 0, 'boon')
        self.assertNotIn('correct', first_bonus['bonus_question'])
        next_round = await c.bonus('group', 'guest', self.match, 1, 'guard')
        self.assertEqual(next_round['round'], 1)
        self.assertFalse(next_round['bonus_result']['correct'])
        self.assertIn('def can_buy', next_round['challenge']['recovery_baseline'])
        self.assertNotIn('recovery_baseline', (await c.view('group', 'host', self.match))['challenge'])

    async def test_recoverable_matches_are_scoped_and_contain_only_resume_metadata(self):
        matches = await self.coordinator.recoverable_for('group', 'host')
        self.assertEqual(matches, [{
            'match_id': self.match, 'phase': 'coding', 'mode': 'fair', 'round': 0,
            'opponent_id': 'guest',
        }])
        self.assertEqual(await self.coordinator.recoverable_for('another-group', 'host'), [])
        self.assertEqual(await self.coordinator.recoverable_for('group', 'intruder'), [])
        self.assertNotIn('source', repr(matches))

    async def test_deadline_is_server_owned(self):
        self.now += 181
        result = await self.coordinator.view('group', 'host', self.match)
        self.assertEqual(result['phase'], 'exchange')
        self.assertTrue(result['exchange']['timed_out'])
        with self.assertRaises(DuelError):
            await self.coordinator.submit('group', 'host', self.match, 'attack', 'correct')

    async def test_bonus_timeout_and_rewards_do_not_damage(self):
        c = self.coordinator
        await c.submit('group', 'host', self.match, 'attack', 'correct')
        await c.submit('group', 'guest', self.match, 'attack', 'wrong')
        await c.ready('group', 'host', self.match)
        await c.ready('group', 'guest', self.match)
        await c.bonus('group', 'host', self.match, 0, 'guard')
        self.now += 31
        guest = await c.view('group', 'guest', self.match)
        self.assertEqual(guest['phase'], 'coding')
        self.assertTrue(guest['bonus_result']['timed_out'])
        self.assertEqual(guest['you']['hp'], 60)
        await c.submit('group', 'host', self.match, 'attack', 'wrong')
        host = await c.submit('group', 'guest', self.match, 'attack', 'correct')
        host_view = await c.view('group', 'host', self.match)
        self.assertEqual(host['opponent']['hp'], 70)  # 40 incoming, reduced by bonus guard
        self.assertEqual(host_view['exchange']['taken'], 30)

    async def test_invite_is_recipient_only_and_idempotent(self):
        result = await self.coordinator.accept('group', 'guest', self.invitation)
        self.assertEqual(result['match_id'], self.match)
        with self.assertRaises(DuelError):
            await self.coordinator.accept('group', 'intruder', self.invitation)
        with self.assertRaises(DuelError):
            await self.coordinator.view('other-group', 'host', self.match)

    async def test_practice_does_not_submit_or_share_output(self):
        c = self.coordinator
        result = await c.practice('group', 'host', self.match, 'my private code', 'sample input')
        self.assertEqual(result['output'], 'my private code:sample input')
        rival = await c.view('group', 'guest', self.match)
        self.assertFalse(rival['opponent']['submitted'])
        self.assertNotIn('my private code', repr(rival))
        with self.assertRaises(DuelError):
            await c.practice('group', 'intruder', self.match, 'pass', '')
        await c.submit('group', 'host', self.match, 'attack', 'correct')
        with self.assertRaises(DuelError):
            await c.practice('group', 'host', self.match, 'pass', '')

    async def test_worker_failure_aborts_without_winner(self):
        self.coordinator.evaluator = BadWorker()
        with self.assertRaises(EvaluatorUnavailable):
            await self.coordinator.submit('group', 'host', self.match, 'attack', 'correct')
        view = await self.coordinator.view('group', 'guest', self.match)
        self.assertEqual(view['phase'], 'aborted')
        self.assertIsNone(view['winner'])
        self.assertEqual(view['you']['hp'], 100)

    async def test_fail_closed_without_worker(self):
        coordinator = DuelCoordinator(None, lambda: self.now)
        with self.assertRaises(EvaluatorUnavailable):
            await coordinator.invite('group', 'host', 'guest', 'potion')

    async def test_simultaneous_submissions_only_resolve_once(self):
        c = self.coordinator
        await asyncio.gather(c.submit('group', 'host', self.match, 'attack', 'correct'),
                             c.submit('group', 'guest', self.match, 'focus', 'correct'))
        host = await c.view('group', 'host', self.match)
        guest = await c.view('group', 'guest', self.match)
        self.assertEqual(host['you']['hp'], 80)
        self.assertEqual(guest['you']['hp'], 70)
        self.assertEqual(guest['you']['focus'], 10)
        with self.assertRaises(DuelError):
            await c.submit('group', 'guest', self.match, 'attack', 'correct')

    async def test_friendly_gear_is_borrowed_and_server_resolved(self):
        c = DuelCoordinator(Worker(), lambda: self.now)
        invite = await c.invite('group', 'host', 'guest', 'potion', 'friendly')
        match_id = (await c.accept('group', 'guest', invite['invite_id']))['match_id']
        with self.assertRaises(DuelError):
            await c.loadout('group', 'host', match_id, {'weapon':'invented-blade'})
        first = await c.loadout('group', 'host', match_id, {'weapon':'hunter-sparring-greatsword'})
        self.assertEqual(first['phase'], 'loadout')
        self.assertIsNone(first['opponent']['loadout'])
        await c.loadout('group', 'guest', match_id, {'armor':'hunter-gravebound-plate'})
        await c.submit('group', 'host', match_id, 'attack', 'correct')
        view = await c.submit('group', 'guest', match_id, 'guard', 'wrong')
        self.assertEqual(view['you']['hp'], 71)  # 30 + 10 + 1 - 10 - 2 (the Warden Plate's 24% reduction is worth 2 guard)
        self.assertEqual(view['opponent']['loadout']['weapon']['id'], 'hunter-sparring-greatsword')
        self.assertEqual(view['mode'], 'friendly')

    async def test_fair_gear_is_cosmetic_and_timer_waits_for_both(self):
        c = DuelCoordinator(Worker(), lambda: self.now)
        invite = await c.invite('group', 'host', 'guest', 'potion', 'fair')
        match_id = (await c.accept('group', 'guest', invite['invite_id']))['match_id']
        await c.loadout('group', 'host', match_id, {'weapon':'hunter-sparring-greatsword'})
        self.now += 60
        waiting = await c.view('group', 'guest', match_id)
        self.assertEqual(waiting['phase'], 'loadout')
        self.assertEqual(waiting['deadline'], 1120.0)
        with self.assertRaises(DuelError):
            await c.loadout('group', 'host', match_id, {'weapon':'hunter-sparring-whip'})
        active = await c.loadout('group', 'guest', match_id, {'armor':'hunter-gravebound-plate'})
        self.assertEqual(active['deadline'], self.now + 180)
        await c.submit('group', 'host', match_id, 'attack', 'correct')
        view = await c.submit('group', 'guest', match_id, 'guard', 'wrong')
        self.assertEqual(view['you']['hp'], 70)  # fair mode ignores equipment bonuses
        self.assertEqual(view['you']['loadout']['bonus'], {'damage':0, 'guard':0, 'heal':0})

    async def test_mastery_appearances_are_owned_style_matched_and_cosmetic(self):
        c = DuelCoordinator(Worker(), lambda: self.now)
        invite = await c.invite('group', 'host', 'guest', 'potion', 'friendly')
        match_id = (await c.accept('group', 'guest', invite['invite_id']))['match_id']
        selection = {'weapon':'hunter-sparring-whip',
                     'weapon_appearance':'online-mastery-weapon-whip-rare',
                     'armor_appearance':'online-mastery-armor-rare'}
        with self.assertRaises(DuelError):
            await c.loadout('group', 'host', match_id, selection,
                            mastery_owned_ids=frozenset({'online-mastery-armor-rare'}))
        with self.assertRaises(DuelError):
            await c.loadout('group', 'host', match_id,
                            {**selection, 'weapon':'hunter-sparring-greatsword'},
                            mastery_owned_ids=frozenset(selection.values()))
        result = await c.loadout('group', 'host', match_id, selection,
                                 mastery_owned_ids=frozenset(selection.values()))
        appearances = result['you']['loadout']['appearances']
        self.assertEqual(appearances['weapon']['tier'], 'rare')
        self.assertEqual(appearances['armor']['tier'], 'rare')
        self.assertEqual(result['you']['loadout']['bonus'], {'damage':0, 'guard':0, 'heal':0})

    async def test_ranked_ready_timeout_forfeits_to_the_connected_player(self):
        c = self.coordinator
        c.matches[self.match].match.mode = 'geared'
        await c.submit('group', 'host', self.match, 'attack', 'correct')
        exchange = await c.submit('group', 'guest', self.match, 'guard', 'wrong')
        self.assertEqual(exchange['phase'], 'exchange')
        await c.ready('group', 'host', self.match)
        self.now = c.matches[self.match].match.deadline
        result = await c.view('group', 'guest', self.match)
        self.assertEqual(result['phase'], 'finished')
        self.assertEqual(result['winner'], 'host')
        self.assertEqual(result['you']['hp'], 0)

    async def test_double_disconnect_aborts_without_a_rank_result(self):
        c = self.coordinator
        c.matches[self.match].match.mode = 'geared'
        await c.submit('group', 'host', self.match, 'attack', 'correct')
        await c.submit('group', 'guest', self.match, 'guard', 'wrong')
        self.now = c.matches[self.match].match.deadline
        result = await c.view('group', 'host', self.match)
        self.assertEqual(result['phase'], 'aborted')
        self.assertIsNone(result['winner'])
        self.assertIsNone(result['settlement'])

    async def test_ranked_cancel_after_start_is_a_forfeit(self):
        c = self.coordinator
        c.matches[self.match].match.mode = 'geared'
        result = await c.cancel('group', 'guest', self.match)
        self.assertEqual(result['phase'], 'finished')
        self.assertEqual(result['winner'], 'host')

    async def test_unstarted_loadout_timeout_aborts_without_rank(self):
        c = DuelCoordinator(Worker(), lambda: self.now)
        invite = await c.invite('group', 'host', 'guest', 'potion', 'geared')
        match = (await c.accept('group', 'guest', invite['invite_id']))['match_id']
        self.now += 120
        result = await c.view('group', 'host', match)
        self.assertEqual(result['phase'], 'aborted')
        self.assertIsNone(result['settlement'])


if __name__ == '__main__':
    unittest.main()
