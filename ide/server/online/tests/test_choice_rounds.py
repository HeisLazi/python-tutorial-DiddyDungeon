"""Multiple-choice rounds and difficulty tiers, played through the real coordinator."""
import unittest

from ide.server.online.challenges import CHAINS
from ide.server.online.coordinator import DuelCoordinator
from ide.server.online.duel import DuelError
from ide.server.online.evaluator import Evaluation


class Worker:
    async def evaluate(self, challenge_id, code, evaluation_id):
        return Evaluation(code == 'correct', 'private worker details')


class ChoiceRounds(unittest.IsolatedAsyncioTestCase):
    async def start(self, chain, evaluator=None):
        self.now = 1000.0
        self.c = DuelCoordinator(evaluator or Worker(), lambda: self.now)
        invitation = await self.c.invite('group', 'host', 'guest', chain)
        self.match = (await self.c.accept('group', 'guest', invitation['invite_id']))['match_id']
        await self.c.loadout('group', 'host', self.match, {})
        await self.c.loadout('group', 'guest', self.match, {})

    async def ready_up(self):
        await self.c.ready('group', 'host', self.match)
        return await self.c.ready('group', 'guest', self.match)

    async def test_oracle_plays_to_the_end_with_no_code_graded(self):
        await self.start('oracle')
        view = await self.c.view('group', 'host', self.match)
        self.assertEqual(view['challenge']['kind'], 'choice')
        self.assertNotIn('answer', view['challenge'])
        self.assertIn('snippet', view['challenge'])
        for index, challenge in enumerate(CHAINS['oracle']):
            wrong = (challenge.answer + 1) % len(challenge.options)
            await self.c.submit('group', 'host', self.match, 'attack', '', challenge.answer)
            result = await self.c.submit('group', 'guest', self.match, 'guard', '', wrong)
            if result['phase'] == 'finished':
                break  # a knockout can end the match before the last question
            self.assertEqual(result['phase'], 'exchange')
            self.assertTrue(result['exchange']['opponent_passed'])
            self.assertFalse(result['exchange']['passed'])
            self.assertEqual(result['round'], index)
            result = await self.ready_up()
            self.assertEqual(result['phase'], 'coding')  # no bonus detour in the tiers
            self.assertEqual(result['round'], index + 1)
        self.assertEqual(result['phase'], 'finished')
        host = await self.c.view('group', 'host', self.match)
        self.assertGreater(host['you']['hp'], host['opponent']['hp'])

    async def test_a_wrong_choice_deals_no_damage_to_the_rival(self):
        await self.start('oracle')
        challenge = CHAINS['oracle'][0]
        wrong = (challenge.answer + 1) % len(challenge.options)
        await self.c.submit('group', 'host', self.match, 'attack', '', wrong)
        result = await self.c.submit('group', 'guest', self.match, 'attack', '', wrong)
        self.assertEqual((result['you']['hp'], result['opponent']['hp']), (100, 100))

    async def test_invalid_or_mismatched_answers_are_rejected(self):
        await self.start('oracle', Worker())
        with self.assertRaises(DuelError):
            await self.c.submit('group', 'host', self.match, 'attack', 'correct')  # old client: code for a choice round
        with self.assertRaises(DuelError):
            await self.c.submit('group', 'host', self.match, 'attack', '', 99)
        with self.assertRaises(DuelError):
            await self.c.submit('group', 'host', self.match, 'attack', '', True)
        await self.c.submit('group', 'host', self.match, 'attack', '', 0)
        with self.assertRaises(DuelError):
            await self.c.submit('group', 'host', self.match, 'attack', '', 0)  # already locked

    async def test_code_rounds_still_need_code_and_reject_choices(self):
        await self.start('basic', Worker())
        # Round 0 is a choice round; answer it, then reach the standalone code round.
        first = CHAINS['basic'][0]
        await self.c.submit('group', 'host', self.match, 'attack', '', first.answer)
        await self.c.submit('group', 'guest', self.match, 'attack', '', first.answer)
        view = await self.ready_up()
        self.assertEqual(view['challenge']['kind'], 'code')
        self.assertTrue(view['challenge']['starter'])
        self.assertTrue(view['challenge']['fresh'])
        with self.assertRaises(DuelError):
            await self.c.submit('group', 'host', self.match, 'attack', '', 0)
        await self.c.submit('group', 'host', self.match, 'attack', 'correct')
        result = await self.c.submit('group', 'guest', self.match, 'attack', 'wrong')
        self.assertEqual(result['phase'], 'exchange')
        self.assertFalse(result['exchange']['passed'])

    async def test_only_a_missed_code_step_triggers_recovery(self):
        await self.start('advanced', Worker())
        await self.c.submit('group', 'host', self.match, 'attack', 'correct')
        await self.c.submit('group', 'guest', self.match, 'attack', 'wrong')
        await self.ready_up()  # the guest missed the first code step
        guest = await self.c.view('group', 'guest', self.match)
        host = await self.c.view('group', 'host', self.match)
        self.assertIn('def card_rank', guest['challenge']['recovery_baseline'])
        self.assertNotIn('recovery_baseline', host['challenge'])
        self.assertEqual(host['challenge']['starter'], '')  # builds on the host's own working code

    async def test_a_missed_choice_never_triggers_code_recovery(self):
        await self.start('basic', Worker())
        first = CHAINS['basic'][0]
        wrong = (first.answer + 1) % len(first.options)
        await self.c.submit('group', 'host', self.match, 'attack', '', first.answer)
        await self.c.submit('group', 'guest', self.match, 'attack', '', wrong)
        await self.ready_up()
        guest = await self.c.view('group', 'guest', self.match)
        self.assertNotIn('recovery_baseline', guest['challenge'])

    async def test_every_playable_chain_can_be_invited(self):
        for chain in ('basic', 'normal', 'advanced', 'bughunt', 'oracle'):
            await self.start(chain)
            view = await self.c.view('group', 'host', self.match)
            self.assertEqual(view['challenge']['id'], CHAINS[chain][0].id)


if __name__ == '__main__':
    unittest.main()
