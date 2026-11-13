import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from ide.server.online.repository import MatchRepository, MatchStoreError


class RankedLadderChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repository = MatchRepository(str(Path(self.temp.name) / 'matches.sqlite'))

    def tearDown(self):
        self.repository.close()
        self.temp.cleanup()

    def result(self, match_id='match-1', group='group-a', first='player-a', second='player-b', winner='player-a'):
        return {'match_id': match_id, 'target_group': group, 'first_player': first,
                'second_player': second, 'winning_player': winner}

    def test_first_win_initializes_and_updates_only_the_match_group(self):
        self.assertTrue(self.repository.settle_ranked_result(self.result()))
        self.assertEqual(self.repository.group_ratings('group-a'), [
            {'user_id':'player-a', 'rating':1016, 'wins':1, 'losses':0, 'draws':0},
            {'user_id':'player-b', 'rating':984, 'wins':0, 'losses':1, 'draws':0},
        ])
        self.assertEqual(self.repository.group_ratings('group-b'), [])

    def test_duplicate_delivery_is_idempotent_and_conflicts_fail_closed(self):
        result = self.result()
        self.assertTrue(self.repository.settle_ranked_result(result))
        before = self.repository.group_ratings('group-a')
        self.assertFalse(self.repository.settle_ranked_result(result))
        self.assertEqual(self.repository.group_ratings('group-a'), before)
        with self.assertRaises(MatchStoreError):
            self.repository.settle_ranked_result(self.result(winner='player-b'))

    def test_draw_updates_both_records_without_rating_drift(self):
        self.assertTrue(self.repository.settle_ranked_result(self.result(winner=None)))
        self.assertEqual(self.repository.group_ratings('group-a'), [
            {'user_id':'player-a', 'rating':1000, 'wins':0, 'losses':0, 'draws':1},
            {'user_id':'player-b', 'rating':1000, 'wins':0, 'losses':0, 'draws':1},
        ])

    def test_invalid_participant_and_result_shapes_are_rejected(self):
        with self.assertRaises(MatchStoreError):
            self.repository.settle_ranked_result(self.result(first='player-a', second='player-a'))
        with self.assertRaises(MatchStoreError):
            self.repository.settle_ranked_result({'match_id':'x'})

    def test_group_ladder_route_checks_membership_before_reading(self):
        from ide.server.online import service
        group = '00000000-0000-4000-8000-000000000010'
        first = '00000000-0000-4000-8000-000000000001'
        second = '00000000-0000-4000-8000-000000000002'
        self.repository.settle_ranked_result({'match_id':'route-match', 'target_group':group,
            'first_player':first, 'second_player':second, 'winning_player':first})
        with patch.object(service, 'authorize_group', AsyncMock(return_value=first)) as authorize, \
             patch.object(service, 'repository', self.repository), \
             patch.object(service, 'coordinator', SimpleNamespace(storage_failed=False)):
            result = asyncio.run(service.group_ladder(group, 'private-session'))
        authorize.assert_awaited_once_with(group, 'private-session')
        self.assertEqual(result['ratings'][0]['user_id'], first)


if __name__ == '__main__':
    unittest.main()
