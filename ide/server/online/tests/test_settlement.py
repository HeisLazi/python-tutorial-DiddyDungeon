import json
import tempfile
import unittest
from pathlib import Path

import httpx

from ide.server.online.coordinator import DuelCoordinator
from ide.server.online.duel import Phase
from ide.server.online.evaluator import Evaluation
from ide.server.online.repository import MatchRepository, MatchStoreError
from ide.server.online.settlement import RankedSettlementClient, SettlementUnavailable


class Worker:
    async def evaluate(self, challenge_id, code, evaluation_id): return Evaluation(True, '')


class Gateway:
    def __init__(self): self.calls = []; self.fail = False
    async def settle(self, result):
        self.calls.append(dict(result))
        if self.fail: raise SettlementUnavailable('temporary failure')


class SettlementChecks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'matches.sqlite')
        self.repo = MatchRepository(self.path)
        self.service = DuelCoordinator(Worker(), lambda:1000.0, self.repo)
        invite = await self.service.invite('group', 'host', 'guest', 'potion')
        self.match_id = (await self.service.accept('group', 'guest', invite['invite_id']))['match_id']
        self.record = self.service.matches[self.match_id]

    async def asyncTearDown(self):
        self.repo.close()
        self.temp.cleanup()

    def finish_geared(self):
        # Ranked entry remains unavailable through the public coordinator;
        # construct a completed server-owned record to check the outbox.
        self.record.match.mode = 'geared'
        self.record.match.phase = Phase.FINISHED
        self.record.match.winner = 'host'
        self.repo.save(record=self.record)

    async def test_retry_survives_restart_and_is_removed_once_acknowledged(self):
        self.finish_geared()
        gateway = Gateway()
        gateway.fail = True
        with self.assertRaises(SettlementUnavailable): await self.service.flush_settlements(gateway)
        self.assertEqual(len(self.repo.pending_settlements()), 1)
        self.repo.close()
        self.repo = MatchRepository(self.path)
        self.service = DuelCoordinator(Worker(),lambda:1000.0,self.repo)
        gateway.fail = False
        self.assertEqual(await self.service.flush_settlements(gateway), 1)
        self.assertEqual(await self.service.flush_settlements(gateway), 0)
        self.assertEqual(gateway.calls[0],gateway.calls[1])
        self.assertTrue(self.service.matches[self.match_id].settled)
        self.assertEqual(self.repo.pending_settlements(),[])
        self.repo.close()
        self.repo = MatchRepository(self.path)
        self.service = DuelCoordinator(Worker(),lambda:1000.0,self.repo)
        self.assertTrue(self.service.matches[self.match_id].settled)

    async def test_corrupt_outbox_fails_closed_before_network(self):
        self.finish_geared()
        item = self.repo.pending_settlements()[0]
        item['winning_player'] = 'guest'
        self.repo.connection.execute('update ranked_settlement_outbox set payload=? where match_id=?',
            (json.dumps({'version':1,'data':item}),self.match_id))
        self.repo.connection.commit()
        gateway = Gateway()
        with self.assertRaises(MatchStoreError): await self.service.flush_settlements(gateway)
        self.assertEqual(gateway.calls,[])
        self.assertTrue(self.service.storage_failed)

    async def test_friendly_and_aborted_matches_do_not_queue(self):
        self.record.match.phase = Phase.FINISHED
        self.repo.save(record=self.record)
        self.assertEqual(self.repo.pending_settlements(),[])
        self.record.match.mode = 'geared'
        self.record.match.phase = Phase.ABORTED
        self.repo.save(record=self.record)
        self.assertEqual(self.repo.pending_settlements(),[])

    async def test_pending_settlement_is_not_pruned(self):
        self.finish_geared()
        self.service._prune(1000.0 + 7*60*60)
        self.assertIn(self.match_id,self.service.matches)
        self.assertEqual(len(self.repo.pending_settlements()),1)

    async def test_local_ladder_settlement_is_durable_and_replay_safe(self):
        from ide.server.online.service import LocalRankedSettlement
        self.finish_geared()
        gateway = LocalRankedSettlement(self.repo)
        self.assertEqual(await self.service.flush_settlements(gateway), 1)
        self.assertEqual(await self.service.flush_settlements(gateway), 0)
        rows = self.repo.group_ratings('group')
        self.assertEqual(len(rows), 2)
        winner = next(row for row in rows if row['user_id'] == 'host')
        loser = next(row for row in rows if row['user_id'] == 'guest')
        self.assertEqual((winner['wins'], loser['losses']), (1, 1))
        self.assertEqual(self.repo.pending_settlements(), [])

    async def test_gateway_requires_https_and_sends_only_result_fields(self):
        with self.assertRaises(SettlementUnavailable): RankedSettlementClient('http://example.test', 'x' * 40)
        async def handle(request):
            self.assertEqual(request.url.path, '/rest/v1/rpc/settle_hunter_ranked_match')
            payload = json.loads(request.content)
            self.assertEqual(set(payload), {'match_id','target_group','first_player','second_player','winning_player'})
            self.assertNotIn('source', payload)
            return httpx.Response(204)
        client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
        try:
            gateway = RankedSettlementClient('https://example.test', 'x' * 40, client=client)
            self.finish_geared()
            self.assertEqual(await self.service.flush_settlements(gateway), 1)
        finally:
            await client.aclose()


if __name__ == '__main__': unittest.main()
