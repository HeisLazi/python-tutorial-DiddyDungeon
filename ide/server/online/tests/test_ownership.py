import unittest
from unittest.mock import AsyncMock, Mock, patch

from ide.server.online.coordinator import DuelCoordinator
from ide.server.online.duel import DuelError
from ide.server.online.evaluator import Evaluation
from ide.server.online.loadouts import public_catalog, resolve_loadout
from ide.server.online.ownership import RANKED_GEAR, resolve_ranked_loadout


class OwnershipChecks(unittest.TestCase):
    def test_mastery_catalog_is_visual_only_and_not_purchasable(self):
        from ide.server.online.shop import ONLINE_MASTERY_BY_ID, ONLINE_SHOP_BY_ID, public_shop_catalog
        self.assertEqual(len(ONLINE_MASTERY_BY_ID), 24)
        self.assertEqual(len([item for item in public_shop_catalog() if item['source'] == 'pvp-mastery']), 24)
        for item in ONLINE_MASTERY_BY_ID.values():
            self.assertEqual(item['price'], 0)
            self.assertFalse(item['purchasable'])
            self.assertEqual(item['mode_eligibility'], ['campaign', 'sparring', 'pvp'])
            self.assertNotIn(item['id'], ONLINE_SHOP_BY_ID)

    def test_verified_approved_item_is_resolved_by_catalogue(self):
        gear = 'hunter-sparring-greatsword'
        result = resolve_ranked_loadout({'weapon':gear}, frozenset({gear}))
        self.assertEqual(result['weapon']['id'], gear)
        self.assertEqual(result['weapon']['combat_style'], 'greatsword')

    def test_inventory_claims_cannot_replace_verification(self):
        gear = 'hunter-sparring-greatsword'
        with self.assertRaises(DuelError): resolve_ranked_loadout({'weapon':gear}, None)
        with self.assertRaises(DuelError): resolve_ranked_loadout({'weapon':gear}, frozenset())
        with self.assertRaises(DuelError): resolve_ranked_loadout({'weapon':'not-real'}, frozenset({'not-real'}))
        with self.assertRaises(DuelError): resolve_ranked_loadout({'weapon':gear, 'damage':900}, frozenset({gear}))

    def test_curated_items_exist_in_campaign_catalogue(self):
        from ide.server.state import armory_catalog
        catalog = armory_catalog()
        self.assertTrue(RANKED_GEAR)
        self.assertFalse(RANKED_GEAR - set(catalog))

    def test_dungeon_run_pickups_stay_out_of_pvp_but_journal_echoes_are_eligible(self):
        catalog = public_catalog()
        pvp_ids = {item['id'] for items in catalog.values() for item in items}
        run_pickup = 'dungeon-aether-staff'
        journal_echo = 'campaign-dungeon-aether-staff'
        self.assertIn(journal_echo, pvp_ids)
        self.assertEqual(next(item for item in catalog['weapon'] if item['id'] == journal_echo)['mode_eligibility'],
                         ['campaign', 'sparring', 'pvp'])
        self.assertEqual(resolve_loadout({'weapon': journal_echo}, 'friendly')['weapon']['id'], journal_echo)
        run_catalog_entry = {run_pickup: {'id': run_pickup, 'name': 'Aether Staff', 'slot': 'weapon', 'campaign': 'dungeon'}}
        with patch('ide.server.online.loadouts.armory_catalog', return_value=run_catalog_entry):
            self.assertNotIn(run_pickup, {item['id'] for item in public_catalog()['weapon']})
            for mode in ('fair', 'friendly'):
                with self.subTest(mode=mode), self.assertRaisesRegex(DuelError, 'Infinite Dungeon pickups stay in their run'):
                    resolve_loadout({'weapon': run_pickup}, mode)


class RankedCoordinatorChecks(unittest.IsolatedAsyncioTestCase):
    async def test_geared_ranked_invitation_is_supported(self):
        class Worker:
            async def evaluate(self, challenge_id, code, evaluation_id): return Evaluation(True, '')
        coordinator = DuelCoordinator(Worker(), lambda: 1000.0)
        invitation = await coordinator.invite('group', 'host', 'guest', 'potion', 'geared')
        match_id = (await coordinator.accept('group', 'guest', invitation['invite_id']))['match_id']
        self.assertEqual(coordinator.matches[match_id].match.mode, 'geared')

    async def test_geared_loadout_requires_server_verified_ownership(self):
        class Worker:
            async def evaluate(self, challenge_id, code, evaluation_id):
                return Evaluation(True, '')
        coordinator = DuelCoordinator(Worker(), lambda: 1000.0)
        invitation = await coordinator.invite('group', 'host', 'guest', 'potion', 'friendly')
        match_id = (await coordinator.accept('group', 'guest', invitation['invite_id']))['match_id']
        # Ranked invitations remain disabled until awards and settlement are configured.
        coordinator.matches[match_id].match.mode = 'geared'
        selection = {'weapon': 'hunter-sparring-greatsword'}
        with self.assertRaises(DuelError):
            await coordinator.loadout('group', 'host', match_id, selection)
        with self.assertRaises(DuelError):
            await coordinator.loadout('group', 'host', match_id, selection, verified_ids=frozenset())
        view = await coordinator.loadout('group', 'host', match_id, selection,
                                         verified_ids=frozenset({'hunter-sparring-greatsword'}))
        self.assertEqual(view['you']['loadout']['weapon']['id'], 'hunter-sparring-greatsword')

    async def test_service_gets_ownership_for_authenticated_player(self):
        from ide.server.online import service
        player = '00000000-0000-4000-8000-000000000001'
        group = '00000000-0000-4000-8000-000000000002'
        coordinator = type('Coordinator', (), {})()
        coordinator.view = AsyncMock(return_value={'mode': 'geared'})
        coordinator.loadout = AsyncMock(return_value={'ok': True})
        authorize = AsyncMock(return_value=player)
        owned = AsyncMock(return_value=frozenset({'hunter-sparring-greatsword'}))
        online_owned = Mock(return_value=['online-cinder-vow'])
        repository = type('Repository', (), {'online_owned_items': online_owned})()
        with patch.object(service, 'coordinator', coordinator), patch.object(service, 'repository', repository), \
                patch.object(service, 'authorize_group', authorize), patch.object(service, 'verified_gear', owned):
            result = await service.loadout(group, 'match', service.LoadoutRequest(trinket='online-cinder-vow'), 'test-session')
        self.assertEqual(result, {'ok': True})
        owned.assert_awaited_once_with(player, 'test-session')
        online_owned.assert_called_once_with(group, player)
        self.assertEqual(coordinator.loadout.await_args.kwargs['verified_ids'],
                         frozenset({'hunter-sparring-greatsword', 'online-cinder-vow'}))

    async def test_geared_catalog_merges_authenticated_shop_and_verified_gear(self):
        from types import SimpleNamespace
        from ide.server.online import service
        player = '00000000-0000-4000-8000-000000000001'
        group = '00000000-0000-4000-8000-000000000002'
        online_owned = Mock(return_value=['online-cinder-vow'])
        repository = SimpleNamespace(online_owned_items=online_owned)
        verified = AsyncMock(return_value=frozenset({'hunter-sparring-greatsword'}))
        with patch.object(service, 'authorize_group', AsyncMock(return_value=player)), \
                patch.object(service, 'repository', repository), \
                patch.object(service, 'settler', object()), \
                patch.object(service, 'verified_gear', verified):
            result = await service.loadout_catalog(group, 'geared', 'test-session')
        self.assertEqual(result['owned_ids'], ['hunter-sparring-greatsword', 'online-cinder-vow'])
        self.assertIn('online-cinder-vow', [item['id'] for item in result['catalog']['trinket']])
        self.assertNotIn('online-last-laugh-charm', [item['id'] for item in result['catalog']['trinket']])
        online_owned.assert_called_once_with(group, player)
        verified.assert_awaited_once_with(player, 'test-session')


if __name__ == '__main__': unittest.main()
