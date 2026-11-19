import asyncio
import copy
import json
import tempfile
import unittest
from pathlib import Path

from ide.server.online.coordinator import DuelCoordinator
from ide.server.online.duel import Phase
from ide.server.online.evaluator import Evaluation
from ide.server.online.repository import MatchRepository, MatchStoreError


class Worker:
    async def evaluate(self, challenge_id, code, evaluation_id):
        return Evaluation(True, '')


class RepositoryChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'online.sqlite')
        self.clock = 1000.0
        self.repo = MatchRepository(self.path)
        self.c = DuelCoordinator(Worker(), lambda:self.clock, self.repo)
        invitation = await self.c.invite('group','a','b','potion')
        self.invitation = invitation['invite_id']
        self.match = (await self.c.accept('group','b',self.invitation))['match_id']

    async def asyncTearDown(self):
        if self.repo is not None: self.repo.close()
        self.temp.cleanup()

    async def test_restores_match_and_never_stores_source(self):
        await self.c.loadout('group','a',self.match,{})
        await self.c.loadout('group','b',self.match,{})
        await self.c.submit('group','a',self.match,'guard','private learner source')
        rows = self.repo.connection.execute('select payload from online_matches').fetchall()
        self.assertNotIn('private learner source', repr(rows))
        self.repo.close()
        self.repo = MatchRepository(self.path)
        resumed = DuelCoordinator(Worker(),lambda:self.clock,self.repo)
        view = await resumed.view('group','b',self.match)
        self.assertEqual(view['phase'],'coding')
        self.assertTrue(view['opponent']['submitted'])
        await resumed.submit('group','b',self.match,'attack','other source')
        result = await resumed.view('group','a',self.match)
        self.assertEqual(result['phase'],'exchange')
        self.assertEqual(result['you']['hp'],80)

    async def test_fresh_session_can_discover_a_durable_live_match(self):
        self.repo.close()
        self.repo = MatchRepository(self.path)
        resumed = DuelCoordinator(Worker(), lambda:self.clock, self.repo)
        rows = await resumed.recoverable_for('group', 'a')
        self.assertEqual(rows, [{
            'match_id': self.match, 'phase': 'loadout', 'mode': 'fair', 'round': 0,
            'opponent_id': 'b',
        }])
        finished = await resumed.cancel('group', 'a', self.match)
        self.assertEqual(finished['phase'], 'aborted')
        self.assertEqual(await resumed.recoverable_for('group', 'a'), [])

    async def test_interrupted_evaluation_aborts_without_result(self):
        await self.c.loadout('group','a',self.match,{})
        await self.c.loadout('group','b',self.match,{})
        record = self.c.matches[self.match]
        record.match.accept_submission('a','attack','pending-evaluation',self.clock)
        self.repo.save(record=record)
        self.repo.close()
        self.repo = MatchRepository(self.path)
        resumed = DuelCoordinator(Worker(),lambda:self.clock,self.repo)
        view = await resumed.view('group','a',self.match)
        self.assertEqual(view['phase'],Phase.ABORTED.value)
        self.assertIsNone(view['winner'])
        self.assertEqual(view['you']['hp'],100)

    async def test_changed_challenge_revision_aborts_active_match(self):
        row = self.repo.connection.execute('select payload from online_matches where id=?', (self.match,)).fetchone()
        payload = json.loads(row[0])
        payload['data']['chain_revision'] = 'old-content'
        self.repo.connection.execute('update online_matches set payload=? where id=?', (json.dumps(payload), self.match))
        self.repo.connection.commit()
        self.repo.close()
        self.repo = MatchRepository(self.path)
        resumed = DuelCoordinator(Worker(), lambda:self.clock, self.repo)
        view = await resumed.view('group', 'a', self.match)
        self.assertEqual(view['phase'], Phase.ABORTED.value)
        self.assertIsNone(view['winner'])

    async def test_accepted_invitation_recovers_after_original_expiry(self):
        self.repo.close()
        self.repo = MatchRepository(self.path)
        self.clock += 301
        resumed = DuelCoordinator(Worker(),lambda:self.clock,self.repo)
        self.assertEqual((await resumed.accept('group','b',self.invitation))['match_id'],self.match)

    async def test_single_process_lock_and_save_protection(self):
        with self.assertRaises(MatchStoreError):
            MatchRepository(self.path)
        with self.assertRaises(MatchStoreError):
            MatchRepository(str(Path(self.temp.name) / 'progress.json'))

    async def test_finished_duel_awards_each_player_small_currency_once(self):
        record = self.c.matches[self.match]
        self.assertEqual(self.repo.online_wallet('group', 'a'), {
            'currency':'online', 'balance':0, 'earned':{'raid':0, 'pvp':0}, 'spent':0,
        })
        record.match.phase = Phase.FINISHED
        record.match.winner = 'a'
        self.repo.save(record=record)
        self.assertEqual(self.repo.online_wallet('group', 'a'), {
            'currency':'online', 'balance':5, 'earned':{'raid':0, 'pvp':5}, 'spent':0,
        })
        self.assertEqual(self.repo.online_currency('group', 'b'), 5)
        self.repo.save(record=record)
        self.assertEqual(self.repo.online_currency('group', 'a'), 5)
        self.assertEqual(self.repo.connection.execute('SELECT COUNT(*) FROM online_duel_reward_ledger').fetchone()[0], 2)

    async def test_pvp_mastery_unlocks_are_style_specific_and_retry_safe(self):
        base = self.c.matches[self.match]
        base.match.phase = Phase.FINISHED
        base.match.winner = 'a'
        base.match.fighters['a'].loadout = {'weapon': {'combat_style':'sword'}}
        base.match.fighters['b'].loadout = {'weapon': {'combat_style':'whip'}}
        for index in range(5):
            record = copy.deepcopy(base)
            record.match.match_id = f'mastery-match-{index}'
            self.repo.save(record=record)
            if index == 0:
                self.repo.save(record=record)  # repeating the same completion is not another win
        progress = self.repo.online_mastery_progress('a')
        owned = set(progress['owned_ids'])
        self.assertEqual(progress['total_wins'], 5)
        self.assertEqual(progress['weapon_wins'], {'sword':5})
        self.assertIn('online-mastery-armor-rare', owned)
        self.assertIn('online-mastery-weapon-sword-rare', owned)
        self.assertNotIn('online-mastery-weapon-whip-rare', owned)
        self.assertNotIn('online-mastery-weapon-sword-legendary', owned)
        self.assertEqual(self.repo.online_currency('group', 'a'), 25)

    async def test_online_purchase_deducts_once_and_preserves_item_ownership(self):
        record = self.c.matches[self.match]
        record.match.phase = Phase.FINISHED
        record.match.winner = 'a'
        self.repo.save(record=record)
        first = self.repo.online_purchase('group', 'a', 'online-test-charm', 5)
        retry = self.repo.online_purchase('group', 'a', 'online-test-charm', 20)
        self.assertTrue(first['purchased'])
        self.assertFalse(retry['purchased'])
        self.assertEqual(retry['cost'], 5)
        self.assertEqual(self.repo.online_owned_items('group', 'a'), ['online-test-charm'])
        cross_group_retry = self.repo.online_purchase('other-group', 'a', 'online-test-charm', 20)
        self.assertFalse(cross_group_retry['purchased'])
        self.assertEqual(self.repo.online_owned_items('other-group', 'a'), ['online-test-charm'])
        self.assertEqual(self.repo.online_currency('other-group', 'a'), 0)
        self.assertEqual(self.repo.online_wallet('group', 'a'), {
            'currency':'online', 'balance':0, 'earned':{'raid':0, 'pvp':5}, 'spent':5,
        })
        with self.assertRaises(MatchStoreError):
            self.repo.online_purchase('group', 'a', 'online-out-of-reach', 1)

    async def test_storage_error_fails_closed(self):
        original = self.repo.save
        def fail(**_kwargs): raise MatchStoreError('disk unavailable')
        self.repo.save = fail
        with self.assertRaises(MatchStoreError):
            await self.c.loadout('group','a',self.match,{})
        self.repo.save = original
        with self.assertRaises(MatchStoreError):
            await self.c.view('group','a',self.match)


if __name__ == '__main__': unittest.main()
