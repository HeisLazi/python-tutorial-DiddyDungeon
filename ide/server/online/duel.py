"""Authoritative duel state; no network, client authentication or code execution.

The caller must authenticate group membership before creating a match and must
invoke `complete_evaluation` only with results from a trusted isolated worker.
This module never accepts verdicts from a network client.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping
import math
from uuid import uuid4


class DuelError(ValueError):
    pass


class Phase(str, Enum):
    LOADOUT = 'loadout'
    CODING = 'coding'
    EVALUATING = 'evaluating'
    EXCHANGE = 'exchange'
    BONUS = 'bonus'
    FINISHED = 'finished'
    ABORTED = 'aborted'


@dataclass(frozen=True)
class Challenge:
    id: str
    duration_seconds: int = 180
    # Only the coordinator knows the content; the duel just needs to know when a
    # bonus question follows this round.
    bonus_after: bool = False


@dataclass
class Submission:
    # This is a reference owned by an internal worker queue, never source text.
    evaluation_id: str
    stance: str
    passed: bool | None = None
    timed_out: bool = False


@dataclass
class Fighter:
    player_id: str
    hp: int = 100
    focus: int = 0
    submission: Submission | None = None
    ready: bool = False
    loadout: dict | None = None
    bonus_answered: bool = False
    bonus_correct: bool = False
    bonus_choice: str = ''
    next_guard: int = 0
    next_damage: int = 0


@dataclass
class Duel:
    LOADOUT_TIMEOUT_SECONDS = 120
    READY_TIMEOUT_SECONDS = 60

    match_id: str
    group_id: str
    challenges: tuple[Challenge, ...]
    fighters: dict[str, Fighter]
    deadline: float
    phase: Phase = Phase.CODING
    round_index: int = 0
    exchange: dict[str, dict] = field(default_factory=dict)
    winner: str | None = None
    revision: int = 0
    mode: str = 'fair'
    bonus_results: dict[str, dict] = field(default_factory=dict)

    def _bonus_question(self) -> dict:
        if self.challenges[0].id.startswith('chest-'):
            return {'prompt': 'What does a Python function return when it reaches the end without a return statement?',
                    'options': ['None', 'Zero', 'An empty string'], 'answer': 0,
                    'explanation': 'A function without an explicit return returns None.'}
        return {'prompt': 'True or false: a Python function can call another function.',
                'options': ['True', 'False'], 'answer': 0,
                'explanation': 'Functions can call other functions to reuse their behaviour.'}

    @classmethod
    def create(cls, group_id: str, player_ids: tuple[str, str], challenges: tuple[Challenge, ...], now: float, *, mode: str = 'fair', setup: bool = False) -> 'Duel':
        if not group_id or len(player_ids) != 2 or not all(player_ids) or player_ids[0] == player_ids[1]:
            raise DuelError('A duel needs two different group members.')
        if not challenges or any(not c.id or c.duration_seconds < 1 for c in challenges):
            raise DuelError('A duel needs valid challenges.')
        if not math.isfinite(now):
            raise DuelError('Invalid time.')
        if mode not in ('fair', 'friendly', 'geared'):
            raise DuelError('This duel mode is not available.')
        duel = cls(str(uuid4()), group_id, challenges,
                   {p: Fighter(p) for p in player_ids}, now + challenges[0].duration_seconds, mode=mode)
        if setup:
            duel.phase = Phase.LOADOUT
            duel.deadline = now + cls.LOADOUT_TIMEOUT_SECONDS
        return duel

    def set_loadout(self, player_id: str, loadout: dict, now: float) -> None:
        fighter = self._fighter(player_id)
        if self.phase is not Phase.LOADOUT or not math.isfinite(now):
            raise DuelError('Loadout selection is closed.')
        if fighter.loadout is not None:
            raise DuelError('Your loadout is already locked.')
        # Only the coordinator may pass its resolved, server-owned catalogue entry.
        fighter.loadout = loadout
        self.revision += 1
        if all(member.loadout is not None for member in self.fighters.values()):
            self.phase = Phase.CODING
            self.deadline = now + self.challenges[0].duration_seconds
            self.revision += 1

    def _fighter(self, player_id: str) -> Fighter:
        try:
            return self.fighters[player_id]
        except KeyError as exc:
            raise DuelError('Player is not in this match.') from exc

    def accept_submission(self, player_id: str, stance: str, evaluation_id: str, now: float) -> None:
        fighter = self._fighter(player_id)
        if self.phase is not Phase.CODING or now >= self.deadline or not math.isfinite(now):
            raise DuelError('This round is closed.')
        if stance not in ('attack', 'guard', 'focus') or not isinstance(evaluation_id, str) or not evaluation_id or len(evaluation_id) > 128:
            raise DuelError('Invalid submission.')
        if fighter.submission is not None:
            raise DuelError('You have already submitted this round.')
        if any(f.submission and f.submission.evaluation_id == evaluation_id for f in self.fighters.values()):
            raise DuelError('Evaluation identifier already used.')
        fighter.submission = Submission(evaluation_id=evaluation_id, stance=stance)
        self.revision += 1
        if all(f.submission is not None for f in self.fighters.values()):
            self.phase = Phase.EVALUATING
            self._resolve_if_complete(now)

    def expire(self, now: float) -> bool:
        if not math.isfinite(now):
            raise DuelError('Invalid time.')
        if now < self.deadline:
            return False
        if self.phase is Phase.LOADOUT:
            self.phase = Phase.ABORTED
            self.revision += 1
            return True
        if self.phase is Phase.BONUS:
            self._finish_bonus(now)
            return True
        if self.phase is Phase.EXCHANGE:
            ready = [fighter for fighter in self.fighters.values() if fighter.ready]
            if len(ready) == 1:
                forfeiting = next(fighter for fighter in self.fighters.values() if not fighter.ready)
                forfeiting.hp = 0
                self.winner = ready[0].player_id
                self.phase = Phase.FINISHED
            else:
                self.winner = None
                self.phase = Phase.ABORTED
            self.revision += 1
            return True
        if self.phase is not Phase.CODING:
            return False
        for fighter in self.fighters.values():
            if fighter.submission is None:
                fighter.submission = Submission(evaluation_id='', stance='attack', passed=False, timed_out=True)
        self.phase = Phase.EVALUATING
        self.revision += 1
        self._resolve_if_complete(now)
        return True

    def complete_evaluation(self, evaluation_id: str, passed: bool, now: float) -> None:
        if not isinstance(passed, bool) or not evaluation_id:
            raise DuelError('Invalid worker result.')
        if not math.isfinite(now):
            raise DuelError('Invalid time.')
        if self.phase not in (Phase.CODING, Phase.EVALUATING):
            raise DuelError('Round is already resolved.')
        submission = next((f.submission for f in self.fighters.values()
                           if f.submission and f.submission.evaluation_id == evaluation_id), None)
        if submission is None:
            raise DuelError('Unknown evaluation.')
        if submission.passed is not None:
            if submission.passed == passed:
                return  # worker retries are idempotent
            raise DuelError('Conflicting worker result.')
        submission.passed = passed
        self.revision += 1
        self._resolve_if_complete(now)

    def _resolve_if_complete(self, now: float) -> None:
        if self.phase is not Phase.EVALUATING or any(f.submission is None or f.submission.passed is None for f in self.fighters.values()):
            return
        a, b = self.fighters.values()
        damage: dict[str, int] = {}
        # Damage before the rival's guard stance and gear; the gap is what was blocked.
        raw: dict[str, int] = {}
        for fighter, opponent in ((a, b), (b, a)):
            submission, other = fighter.submission, opponent.submission
            dealt = (20 if other.passed else 30) if submission.passed else 0
            if submission.passed:
                dealt += fighter.focus
                dealt += fighter.next_damage
                fighter.next_damage = 0
                dealt += (fighter.loadout or {}).get('bonus', {}).get('damage', 0)
                fighter.focus = 0
                if submission.stance == 'attack': dealt += 10
                if submission.stance == 'focus': fighter.focus = 10
            raw[fighter.player_id] = dealt
            if other.stance == 'guard': dealt = max(0, dealt - 10)
            dealt = max(0, dealt - opponent.next_guard)
            dealt = max(0, dealt - (opponent.loadout or {}).get('bonus', {}).get('guard', 0))
            damage[fighter.player_id] = dealt
        a.next_guard = b.next_guard = 0
        a.hp = max(0, a.hp - damage[b.player_id])
        b.hp = max(0, b.hp - damage[a.player_id])
        healed: dict[str, int] = {}
        for fighter in (a, b):
            before = fighter.hp
            if fighter.hp > 0 and fighter.submission.passed:
                fighter.hp = min(100, fighter.hp + (fighter.loadout or {}).get('bonus', {}).get('heal', 0))
            healed[fighter.player_id] = fighter.hp - before
        self.exchange = {fighter.player_id: {'passed': fighter.submission.passed,
            'timed_out': fighter.submission.timed_out, 'dealt': damage[fighter.player_id],
            'taken': damage[opponent.player_id], 'healed': healed[fighter.player_id], 'opponent_passed': opponent.submission.passed,
            # A timed-out round has no stance to report. `blocked` is damage this
            # fighter's own guard, gear and bonus prevented.
            'stance': '' if fighter.submission.timed_out else fighter.submission.stance,
            'opponent_stance': '' if opponent.submission.timed_out else opponent.submission.stance,
            'blocked': raw[opponent.player_id] - damage[opponent.player_id],
            'rival_blocked': raw[fighter.player_id] - damage[fighter.player_id]}
            for fighter, opponent in ((a, b), (b, a))}
        self.phase = Phase.FINISHED if self.round_index == len(self.challenges) - 1 or min(a.hp, b.hp) == 0 else Phase.EXCHANGE
        if self.phase is Phase.FINISHED:
            self.winner = None if a.hp == b.hp else (a.player_id if a.hp > b.hp else b.player_id)
        else:
            self.deadline = now + self.READY_TIMEOUT_SECONDS
        self.revision += 1

    def ready_for_next(self, player_id: str, now: float) -> None:
        fighter = self._fighter(player_id)
        if self.phase is not Phase.EXCHANGE or not math.isfinite(now):
            raise DuelError('The next challenge is not available.')
        if fighter.ready:
            return
        fighter.ready = True
        self.deadline = now + self.READY_TIMEOUT_SECONDS
        self.revision += 1
        if all(f.ready for f in self.fighters.values()):
            for member in self.fighters.values():
                member.ready = False
            if self.challenges[self.round_index].bonus_after:
                self.phase = Phase.BONUS
                self.deadline = now + 30
            else:
                self._next_round(now)
            self.revision += 1

    def answer_bonus(self, player_id: str, answer: int, reward: str, now: float) -> None:
        fighter = self._fighter(player_id)
        question = self._bonus_question()
        if self.phase is not Phase.BONUS or not math.isfinite(now) or now >= self.deadline:
            raise DuelError('The bonus question is closed.')
        if type(answer) is not int or not 0 <= answer < len(question['options']) or reward not in ('heal', 'guard', 'boon'):
            raise DuelError('Choose a valid answer and reward.')
        if fighter.bonus_answered:
            raise DuelError('Your bonus answer is already locked.')
        fighter.bonus_answered = True
        fighter.bonus_correct = answer == question['answer']
        fighter.bonus_choice = reward
        self.revision += 1
        if all(member.bonus_answered for member in self.fighters.values()):
            self._finish_bonus(now)

    def _finish_bonus(self, now: float) -> None:
        question = self._bonus_question()
        for fighter in self.fighters.values():
            correct = fighter.bonus_answered and fighter.bonus_correct
            applied = ''
            if correct and fighter.bonus_choice == 'heal':
                healed = min(10, 100 - fighter.hp)
                fighter.hp += healed
                applied = f'Restored {healed} HP.'
            elif correct and fighter.bonus_choice == 'guard':
                fighter.next_guard = 10
                applied = 'Guard reduces damage in the next exchange by 10.'
            elif correct and fighter.bonus_choice == 'boon':
                fighter.next_damage = 5
                applied = 'Your next successful attack deals 5 more damage.'
            self.bonus_results[fighter.player_id] = {'correct': correct, 'timed_out': not fighter.bonus_answered,
                'explanation': question['explanation'], 'reward': applied}
        self._next_round(now)
        self.revision += 1

    def _next_round(self, now: float) -> None:
        self.round_index += 1
        for member in self.fighters.values():
            member.submission = None
        self.exchange = {}
        self.deadline = now + self.challenges[self.round_index].duration_seconds
        self.phase = Phase.CODING

    def abort(self) -> None:
        """Abort on infrastructure failure; an aborted duel cannot award rank."""
        if self.phase not in (Phase.FINISHED, Phase.ABORTED):
            self.phase = Phase.ABORTED
            self.winner = None
            self.revision += 1

    def forfeit(self, player_id: str) -> None:
        """Finish a live ranked match when a player deliberately abandons it."""
        if self.phase in (Phase.FINISHED, Phase.ABORTED):
            raise DuelError('This duel has already ended.')
        forfeiting = self._fighter(player_id)
        winner = next(fighter for fighter in self.fighters.values() if fighter is not forfeiting)
        forfeiting.hp = 0
        self.winner = winner.player_id
        self.phase = Phase.FINISHED
        self.revision += 1

    def view_for(self, player_id: str) -> Mapping:
        fighter = self._fighter(player_id)
        rival = next(f for f in self.fighters.values() if f is not fighter)
        bonus_question = self._bonus_question() if self.phase is Phase.BONUS else None
        return {'match_id': self.match_id, 'phase': self.phase.value, 'round': self.round_index, 'mode': self.mode,
                'challenge_id': self.challenges[self.round_index].id, 'deadline': self.deadline,
                'you': {'hp': fighter.hp, 'focus': fighter.focus, 'submitted': fighter.submission is not None, 'ready': fighter.ready, 'loadout': fighter.loadout},
                'opponent': {'hp': rival.hp, 'submitted': rival.submission is not None, 'ready': rival.ready,
                             'loadout_locked': rival.loadout is not None, 'loadout': rival.loadout if self.phase is not Phase.LOADOUT else None},
                'bonus_question': {'prompt': bonus_question['prompt'], 'options': bonus_question['options'],
                    'answered': fighter.bonus_answered, 'opponent_answered': rival.bonus_answered, 'duration_seconds': 30} if bonus_question else None,
                'bonus_result': self.bonus_results.get(player_id),
                'exchange': self.exchange.get(player_id), 'winner': self.winner, 'revision': self.revision}
