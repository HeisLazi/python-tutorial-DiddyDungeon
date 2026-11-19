"""Damage, stance and content rules for the online duel (no network, no sandbox)."""
import json
import unittest

from ide.server.online.challenges import CHAINS, public_challenge
from ide.server.online.duel import Challenge, Duel
from ide.server.online.worker.cases import CASES


def exchange(stance_a, passed_a, stance_b, passed_b):
    duel = Duel.create('g', ('A', 'B'), (Challenge('c1'), Challenge('c2'), Challenge('c3')), 0.0)
    duel.accept_submission('A', stance_a, 'ea', 1.0)
    duel.accept_submission('B', stance_b, 'eb', 1.0)
    duel.complete_evaluation('ea', passed_a, 2.0)
    duel.complete_evaluation('eb', passed_b, 2.0)
    return duel


class DamageAndStances(unittest.TestCase):
    def check(self, combo, hp_a, hp_b):
        duel = exchange(*combo)
        self.assertEqual((duel.fighters['A'].hp, duel.fighters['B'].hp), (hp_a, hp_b), combo)
        return duel

    def test_stance_table(self):
        # (A stance, A passed, B stance, B passed) -> (A HP, B HP)
        self.check(('attack', True, 'attack', True), 70, 70)    # 20 base + 10 attack each
        self.check(('attack', True, 'attack', False), 100, 60)  # 30 base + 10 attack
        self.check(('guard', True, 'attack', True), 80, 80)     # guard blocks 10 of B's 30
        self.check(('guard', False, 'attack', True), 70, 100)   # guard still blocks 10 of B's 40
        self.check(('focus', True, 'attack', True), 70, 80)     # focus trades the attack bonus
        self.check(('guard', False, 'guard', True), 80, 100)

    def test_neither_passing_deals_no_damage(self):
        duel = self.check(('attack', False, 'attack', False), 100, 100)
        self.assertEqual(duel.exchange['A']['dealt'], 0)
        self.assertEqual(duel.exchange['A']['taken'], 0)

    def test_focus_pays_out_on_the_next_hit(self):
        duel = Duel.create('g', ('A', 'B'), (Challenge('c1', bonus_after=True), Challenge('c2')), 0.0)
        duel.accept_submission('A', 'focus', 'ea', 1.0)
        duel.accept_submission('B', 'attack', 'eb', 1.0)
        duel.complete_evaluation('ea', True, 2.0)
        duel.complete_evaluation('eb', False, 2.0)
        self.assertEqual(duel.fighters['A'].focus, 10)
        duel.ready_for_next('A', 3.0)
        duel.ready_for_next('B', 3.0)
        duel.answer_bonus('A', 0, 'heal', 4.0)
        duel.answer_bonus('B', 0, 'heal', 4.0)
        self.assertEqual(duel.round_index, 1)
        duel.accept_submission('A', 'attack', 'ea2', 5.0)
        duel.accept_submission('B', 'attack', 'eb2', 5.0)
        duel.complete_evaluation('ea2', True, 6.0)
        duel.complete_evaluation('eb2', False, 6.0)
        self.assertEqual(duel.exchange['A']['dealt'], 50)  # 30 base + 10 attack + 10 focus
        self.assertEqual(duel.fighters['A'].focus, 0)

    def test_exchange_reports_stances_and_blocked_damage(self):
        duel = exchange('guard', True, 'attack', True)
        mine, theirs = duel.exchange['A'], duel.exchange['B']
        self.assertEqual((mine['stance'], mine['opponent_stance']), ('guard', 'attack'))
        self.assertEqual((mine['dealt'], mine['taken'], mine['blocked']), (20, 20, 10))
        self.assertEqual((theirs['dealt'], theirs['taken'], theirs['blocked']), (20, 20, 0))
        self.assertEqual((mine['rival_blocked'], theirs['rival_blocked']), (0, 10))  # the attacker sees the guard

    def test_timed_out_round_has_no_stance(self):
        duel = Duel.create('g', ('A', 'B'), (Challenge('c1'), Challenge('c2')), 0.0)
        duel.expire(1000.0)
        self.assertEqual(duel.exchange['A']['stance'], '')
        self.assertEqual(duel.exchange['A']['opponent_stance'], '')
        self.assertEqual((duel.fighters['A'].hp, duel.fighters['B'].hp), (100, 100))


def run_cases(source, challenge_id):
    """Grade like the sandbox: JSON in, and only bool/int/str/None with the exact type out."""
    try:
        for name, args, expected in CASES[challenge_id]:
            scope = {'__name__': '__questlab_answer__'}
            exec(compile(source, '<answer>', 'exec'), scope)
            value = scope[name](*json.loads(json.dumps(args)))
            if type(value) not in (bool, int, str, type(None)) or type(value) is not type(expected) or value != expected:
                return False
        return True
    except Exception:
        return False


def code_rounds():
    return [(name, c) for name, chain in CHAINS.items() for c in chain if c.kind == 'code']


def choice_rounds():
    return [(name, c) for name, chain in CHAINS.items() for c in chain if c.kind == 'choice']


class ChallengeContent(unittest.TestCase):
    def test_every_code_round_has_worker_cases_with_sandbox_types(self):
        for _, challenge in code_rounds():
            self.assertIn(challenge.id, CASES, challenge.id)
            for _, args, expected in CASES[challenge.id]:
                self.assertIn(type(expected), (bool, int, str), challenge.id)
                json.dumps(args)

    def test_reference_answers_pass_their_own_cases(self):
        for _, challenge in code_rounds():
            if challenge.baseline:  # the final code round of a legacy chain has nothing to restore into
                self.assertTrue(run_cases(challenge.baseline, challenge.id), challenge.id)
        for name in ('basic', 'normal', 'advanced', 'bughunt'):
            for challenge in CHAINS[name]:
                if challenge.kind == 'code':
                    self.assertTrue(run_cases(challenge.baseline, challenge.id), challenge.id)

    def test_blank_and_unchanged_starters_fail(self):
        for _, challenge in code_rounds():
            self.assertFalse(run_cases('pass\n', challenge.id), challenge.id)
            if challenge.starter:
                self.assertFalse(run_cases(challenge.starter, challenge.id), challenge.id)

    def test_later_baselines_include_the_earlier_work_they_build_on(self):
        checked = 0
        for name in ('basic', 'normal', 'advanced', 'bughunt'):
            chain = CHAINS[name]
            for earlier, later in zip(chain, chain[1:]):
                if earlier.kind == 'code' and later.kind == 'code' and later.builds_on_previous:
                    # A player who recovers into `later` starts from `earlier`'s baseline,
                    # so the later reference answer must still contain it.
                    self.assertIn(earlier.baseline, later.baseline, f'{name}/{later.id}')
                    checked += 1
        self.assertGreaterEqual(checked, 3)  # the poker steps

    def test_choice_rounds_have_a_valid_answer_key(self):
        self.assertTrue(choice_rounds())
        for _, challenge in choice_rounds():
            self.assertGreaterEqual(len(challenge.options), 2, challenge.id)
            self.assertEqual(len(set(challenge.options)), len(challenge.options), challenge.id)
            self.assertTrue(0 <= challenge.answer < len(challenge.options), challenge.id)

    def test_correct_answers_do_not_sit_in_one_position(self):
        positions = {challenge.answer for _, challenge in choice_rounds() if challenge.id.startswith(('basic', 'normal', 'advanced'))}
        self.assertGreaterEqual(len(positions), 2)

    def test_player_view_never_contains_the_answer_key_or_checks(self):
        for chain in CHAINS.values():
            for challenge in chain:
                for previous in (None, True, False):
                    view = public_challenge(challenge, previous)
                    self.assertNotIn('answer', view)
                    self.assertNotIn('checks', view)
                    self.assertNotIn('baseline', view)
                    if challenge.kind == 'choice':
                        self.assertEqual(view['options'], list(challenge.options))

    def test_each_tier_matches_its_brief(self):
        self.assertEqual({c.kind for c in CHAINS['basic']}, {'choice', 'code'})
        self.assertGreater(sum(c.kind == 'choice' for c in CHAINS['basic']), sum(c.kind == 'code' for c in CHAINS['basic']) - 1)
        self.assertTrue(any(c.kind == 'code' for c in CHAINS['normal']) and any(c.kind == 'choice' for c in CHAINS['normal']))
        advanced = CHAINS['advanced']
        self.assertTrue(all(c.kind == 'code' for c in advanced[:-1]))
        self.assertEqual(advanced[-1].kind, 'choice')  # the interview closes the match
        self.assertTrue(all(not c.bonus_after for name in ('basic', 'normal', 'advanced') for c in CHAINS[name]))

    def test_standalone_code_steps_always_receive_their_starter(self):
        for _, challenge in code_rounds():
            view = public_challenge(challenge, True)
            if not challenge.builds_on_previous:
                self.assertEqual(view['starter'], challenge.starter)
                self.assertTrue(view['fresh'])


if __name__ == '__main__':
    unittest.main()
