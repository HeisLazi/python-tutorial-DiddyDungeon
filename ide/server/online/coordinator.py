"""Authoritative process-local duel coordinator.

This is not a deployable service by itself: the caller must authenticate the
principal and verify group membership for *every* operation. Evaluation must
be supplied by a trusted isolated worker. Ranked settlement is not enabled.
"""
from __future__ import annotations

import asyncio
import secrets
import time
from dataclasses import dataclass, field
from typing import Protocol

from .challenges import CHAINS, DuelChallenge, public_challenge
from .content_revision import chain_revision
from .duel import Challenge, Duel, DuelError, Phase
from .evaluator import Evaluation, EvaluatorUnavailable
from .loadouts import resolve_loadout
from .ownership import resolve_ranked_loadout
from .shop import ONLINE_MASTERY_BY_ID
from .repository import MatchRepository, MatchStoreError, restore_duel


class Evaluator(Protocol):
    async def evaluate(self, challenge_id: str, code: str, evaluation_id: str) -> Evaluation: ...
    async def practice(self, code: str, stdin: str, request_id: str) -> dict: ...


@dataclass
class PendingInvite:
    id: str
    group_id: str
    host_id: str
    guest_id: str
    chain_id: str
    created: float
    mode: str = 'fair'
    match_id: str = ''


@dataclass
class MatchRecord:
    match: Duel
    chain: tuple[DuelChallenge, ...]
    previous_passed: dict[str, bool | None] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    settled: bool = False


class DuelCoordinator:
    """Call methods only after a verified account is authorized for the group."""
    INVITE_LIFETIME = 300
    MAX_PENDING = 128
    MAX_MATCHES = 128

    def __init__(self, evaluator: Evaluator | None, clock=time.time, repository: MatchRepository | None = None):
        self.evaluator = evaluator
        self.clock = clock
        self.lock = asyncio.Lock()
        self.settlement_lock = asyncio.Lock()
        self.invites: dict[str, PendingInvite] = {}
        self.matches: dict[str, MatchRecord] = {}
        self.practice_inflight: set[tuple[str, str]] = set()
        self.repository = repository
        self.storage_failed = False
        if repository is not None:
            self._restore()

    def _restore(self) -> None:
        try:
            invites, matches = self.repository.load()
            for raw in matches:
                chain = CHAINS[raw['chain_id']]
                match = restore_duel(raw['match'])
                if tuple(c.id for c in match.challenges) != tuple(c.id for c in chain):
                    raise ValueError('Stored challenge chain changed')
                record = MatchRecord(match, chain, raw['previous_passed'], created=raw['created'], settled=raw.get('settled', False))
                self.matches[match.match_id] = record
                # Source is intentionally never persisted. If a worker was in
                # flight during restart, no result can safely be reconstructed.
                if (match.phase not in (Phase.FINISHED, Phase.ABORTED) and
                    (raw.get('chain_revision') != chain_revision(chain) or
                     any(f.submission and f.submission.passed is None for f in match.fighters.values()))):
                    match.abort()
                    self.repository.save(record=record)
            for raw in invites:
                invitation = PendingInvite(**raw)
                self.invites[invitation.id] = invitation
        except (KeyError, TypeError, ValueError, MatchStoreError) as exc:
            raise MatchStoreError('Could not safely restore online matches.') from exc

    def _ensure_store(self) -> None:
        if self.storage_failed:
            raise MatchStoreError('Online match storage is unavailable.')

    def _save(self, **kwargs) -> None:
        self._ensure_store()
        if self.repository is not None:
            try:
                self.repository.save(**kwargs)
            except MatchStoreError:
                self.storage_failed = True
                raise

    def _prune(self, now: float) -> None:
        # Clear abandoned sessions so a small private service can keep running.
        removed_matches = []
        old_invites = set(self.invites)
        for match_id, record in tuple(self.matches.items()):
            if now - record.created > 6 * 60 * 60 and not (record.match.mode == 'geared' and record.match.phase is Phase.FINISHED and not record.settled):
                record.match.abort()
                del self.matches[match_id]
                removed_matches.append(match_id)
        self.invites = {key: invitation for key, invitation in self.invites.items()
                        if (invitation.match_id in self.matches if invitation.match_id
                            else now - invitation.created < self.INVITE_LIFETIME)}
        self._save(remove_invites=old_invites - set(self.invites), remove_matches=removed_matches)

    async def invite(self, group_id: str, host_id: str, guest_id: str, chain_id: str, mode: str = 'fair') -> dict:
        if self.evaluator is None:
            raise EvaluatorUnavailable('Online duels are unavailable until an isolated evaluator is configured.')
        if not group_id or not host_id or not guest_id or host_id == guest_id or chain_id not in CHAINS or mode not in ('fair', 'friendly', 'geared'):
            raise DuelError('Choose a different group member and a valid challenge.')
        async with self.lock:
            self._ensure_store()
            now = self.clock()
            self._prune(now)
            if len(self.invites) >= self.MAX_PENDING:
                raise DuelError('The duel lobby is full.')
            invite = PendingInvite(secrets.token_urlsafe(24), group_id, host_id, guest_id, chain_id, now, mode)
            self.invites[invite.id] = invite
            self._save(invite=invite)
            return {'invite_id': invite.id, 'expires_at': now + self.INVITE_LIFETIME}

    async def pending_for(self, group_id: str, player_id: str) -> list[dict]:
        async with self.lock:
            self._ensure_store()
            now = self.clock()
            return [{'invite_id': i.id, 'host_id': i.host_id, 'chain_id': i.chain_id, 'mode': i.mode,
                     'expires_at': i.created + self.INVITE_LIFETIME}
                    for i in self.invites.values() if i.group_id == group_id and i.guest_id == player_id
                    and not i.match_id and now - i.created < self.INVITE_LIFETIME]

    async def accept(self, group_id: str, guest_id: str, invite_id: str) -> dict:
        if self.evaluator is None:
            raise EvaluatorUnavailable('Online duels are unavailable until an isolated evaluator is configured.')
        async with self.lock:
            self._ensure_store()
            invitation = self.invites.get(invite_id)
            now = self.clock()
            if not invitation or invitation.group_id != group_id or invitation.guest_id != guest_id or (not invitation.match_id and now - invitation.created >= self.INVITE_LIFETIME):
                raise DuelError('This invitation is unavailable or expired.')
            if invitation.match_id:
                return {'match_id': invitation.match_id}  # retry, no duplicate match
            if len(self.matches) >= self.MAX_MATCHES:
                raise DuelError('The duel service is full.')
            chain = CHAINS[invitation.chain_id]
            duel = Duel.create(group_id, (invitation.host_id, guest_id), tuple(Challenge(c.id, c.duration_seconds, c.bonus_after) for c in chain), now, mode=invitation.mode, setup=True)
            self.matches[duel.match_id] = MatchRecord(duel, chain, {invitation.host_id: None, guest_id: None}, created=now)
            invitation.match_id = duel.match_id
            self._save(invite=invitation, record=self.matches[duel.match_id])
            return {'match_id': duel.match_id}

    async def invitation_status(self, group_id: str, player_id: str, invite_id: str) -> dict:
        async with self.lock:
            self._ensure_store()
            invitation = self.invites.get(invite_id)
            if not invitation or invitation.group_id != group_id or player_id not in (invitation.host_id, invitation.guest_id):
                raise DuelError('Invitation not found.')
            return {'match_id': invitation.match_id or None, 'expired': self.clock() - invitation.created >= self.INVITE_LIFETIME and not invitation.match_id}

    async def withdraw(self, group_id: str, host_id: str, invite_id: str) -> None:
        async with self.lock:
            self._ensure_store()
            invitation = self.invites.get(invite_id)
            if not invitation or invitation.group_id != group_id or invitation.host_id != host_id:
                raise DuelError('Invitation not found.')
            if invitation.match_id:
                raise DuelError('The invitation was accepted. Cancel the match instead.')
            del self.invites[invite_id]
            self._save(remove_invites=(invite_id,))

    def _record(self, group_id: str, player_id: str, match_id: str) -> MatchRecord:
        self._ensure_store()
        record = self.matches.get(match_id)
        if not record or record.match.group_id != group_id or player_id not in record.match.fighters:
            raise DuelError('Match not found.')
        return record

    def _view(self, record: MatchRecord, player_id: str) -> dict:
        match = record.match
        now = self.clock()
        if match.expire(now):
            self._save(record=record)
        view = dict(match.view_for(player_id))
        view['server_now'] = now
        view['settlement'] = ('settled' if record.settled else 'pending') if match.mode == 'geared' and match.phase is Phase.FINISHED else None
        current = record.chain[match.round_index]
        challenge = public_challenge(current, record.previous_passed[player_id])
        if current.kind == 'code' and current.builds_on_previous and record.previous_passed[player_id] is False:
            # Restore the last working code answer; choice rounds carry none.
            baseline = next((c.baseline for c in reversed(record.chain[:match.round_index]) if c.kind == 'code'), '')
            if baseline:
                challenge['recovery_baseline'] = baseline
        view['challenge'] = challenge
        return view

    async def view(self, group_id: str, player_id: str, match_id: str) -> dict:
        async with self.lock:
            return self._view(self._record(group_id, player_id, match_id), player_id)

    async def recoverable_for(self, group_id: str, player_id: str) -> list[dict]:
        """List this player's live duels so a fresh app session can resume them.

        Only match references and public state are returned. Submitted source,
        evaluator internals and the other player's private answer are never
        included in the lobby recovery response.
        """
        async with self.lock:
            self._ensure_store()
            self._prune(self.clock())
            recoverable = []
            for record in self.matches.values():
                match = record.match
                if match.group_id != group_id or player_id not in match.fighters:
                    continue
                view = self._view(record, player_id)
                if view['phase'] in (Phase.FINISHED.value, Phase.ABORTED.value):
                    continue
                opponent_id = next(member for member in match.fighters if member != player_id)
                recoverable.append((record.created, {
                    'match_id': match.match_id,
                    'phase': view['phase'],
                    'mode': match.mode,
                    'round': view['round'],
                    'opponent_id': opponent_id,
                }))
            recoverable.sort(key=lambda item: item[0], reverse=True)
            return [item for _, item in recoverable[:10]]

    async def loadout(self, group_id: str, player_id: str, match_id: str, selection: dict,
                      *, verified_ids: frozenset[str] | None = None,
                      mastery_owned_ids: frozenset[str] = frozenset()) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            if not isinstance(selection, dict) or set(selection) - {
                'weapon', 'armor', 'trinket', 'weapon_appearance', 'armor_appearance'
            }:
                raise DuelError('Invalid duel loadout.')
            gear_selection = {slot:selection.get(slot) for slot in ('weapon', 'armor', 'trinket')}
            resolved = (resolve_ranked_loadout(gear_selection, verified_ids) if record.match.mode == 'geared'
                        else resolve_loadout(gear_selection, record.match.mode))
            appearances = {}
            weapon_style = (resolved.get('weapon') or {}).get('combat_style')
            for key, appearance_type in (('weapon_appearance', 'weapon'), ('armor_appearance', 'armor')):
                appearance_id = selection.get(key)
                if appearance_id in (None, ''):
                    continue
                item = ONLINE_MASTERY_BY_ID.get(appearance_id) if isinstance(appearance_id, str) else None
                if not item or item.get('appearance_type') != appearance_type:
                    raise DuelError('That mastery appearance is not available in this slot.')
                if appearance_id not in mastery_owned_ids:
                    raise DuelError('That mastery appearance has not been earned on this account.')
                if appearance_type == 'weapon' and item.get('style') != weapon_style:
                    raise DuelError('Choose a mastery appearance for the weapon you equipped.')
                # Keep the match snapshot cosmetic-only: no stats/effects from this record.
                appearances[appearance_type] = {
                    'id':item['id'], 'name':item['name'], 'tier':item['tier'],
                    'appearance_type':appearance_type, 'style':item.get('style'),
                }
            resolved['appearances'] = appearances
            record.match.set_loadout(player_id, resolved, self.clock())
            self._save(record=record)
            return self._view(record, player_id)

    async def submit(self, group_id: str, player_id: str, match_id: str, stance: str, code: str = '', choice: int | None = None) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            match = record.match
            if match.expire(self.clock()):
                self._save(record=record)
            current = record.chain[match.round_index]
            if current.kind == 'choice':
                # Graded here: the answer key never leaves the service and needs no sandbox.
                if type(choice) is not int or not 0 <= choice < len(current.options):
                    raise DuelError('This round is a multiple-choice question. Pick an answer, or update Quest Lab if you cannot see the options.')
                evaluation_id = secrets.token_urlsafe(24)
                match.accept_submission(player_id, stance, evaluation_id, self.clock())
                match.complete_evaluation(evaluation_id, choice == current.answer, self.clock())
                self._save(record=record)
                return self._view(record, player_id)
        if choice is not None:
            raise DuelError('This round needs code, not a multiple-choice answer.')
        if self.evaluator is None:
            raise EvaluatorUnavailable('Online duels are unavailable until an isolated evaluator is configured.')
        if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 20000:
            raise DuelError('Provide Python code of at most 20 KB.')
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            match = record.match
            if match.expire(self.clock()):
                self._save(record=record)
            evaluation_id = secrets.token_urlsafe(24)
            match.accept_submission(player_id, stance, evaluation_id, self.clock())
            self._save(record=record)
            challenge_id = record.chain[match.round_index].id
        try:
            evaluation = await self.evaluator.evaluate(challenge_id, code, evaluation_id)
        except asyncio.CancelledError:
            async with self.lock:
                match.abort()
                self._save(record=record)
            raise
        except Exception as exc:
            # An outage never awards a victory or marks a learner incorrect.
            async with self.lock:
                match.abort()
                self._save(record=record)
            raise EvaluatorUnavailable('The isolated evaluator failed; the duel was cancelled without a result.') from exc
        async with self.lock:
            if match.phase in (Phase.ABORTED, Phase.FINISHED):
                return self._view(record, player_id)
            match.complete_evaluation(evaluation_id, evaluation.passed, self.clock())
            self._save(record=record)
            return self._view(record, player_id)

    async def ready(self, group_id: str, player_id: str, match_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            match = record.match
            if match.expire(self.clock()):
                self._save(record=record)
                return self._view(record, player_id)
            if record.chain[match.round_index].kind == 'code':
                # Only code rounds decide whether the next step can build on a working answer.
                for pid, result in match.exchange.items():
                    record.previous_passed[pid] = bool(result['passed'])
            match.ready_for_next(player_id, self.clock())
            self._save(record=record)
            return self._view(record, player_id)

    async def practice(self, group_id: str, player_id: str, match_id: str, code: str, stdin: str) -> dict:
        if self.evaluator is None or not callable(getattr(self.evaluator, 'practice', None)):
            raise EvaluatorUnavailable('The isolated practice runner is unavailable.')
        if (not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 20000
                or not isinstance(stdin, str) or len(stdin.encode('utf-8')) > 4000):
            raise DuelError('Invalid practice code or input.')
        key = (match_id, player_id)
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            match = record.match
            if match.expire(self.clock()):
                self._save(record=record)
            if match.phase is not Phase.CODING or match.fighters[player_id].submission is not None:
                raise DuelError('Practice is available before submitting the current challenge.')
            if key in self.practice_inflight:
                raise DuelError('A practice run is already in progress.')
            self.practice_inflight.add(key)
        try:
            return await self.evaluator.practice(code, stdin, secrets.token_urlsafe(24))
        except Exception as exc:
            # Practice failure does not resolve, abort, or award damage.
            raise EvaluatorUnavailable('The isolated practice runner is unavailable.') from exc
        finally:
            async with self.lock:
                self.practice_inflight.discard(key)

    async def bonus(self, group_id: str, player_id: str, match_id: str, answer: int, reward: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            if record.match.expire(self.clock()):
                self._save(record=record)
            record.match.answer_bonus(player_id, answer, reward, self.clock())
            self._save(record=record)
            return self._view(record, player_id)

    async def cancel(self, group_id: str, player_id: str, match_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, match_id)
            match = record.match
            if match.phase not in (Phase.FINISHED, Phase.ABORTED):
                if match.mode == 'geared' and match.phase is not Phase.LOADOUT:
                    match.forfeit(player_id)
                else:
                    match.abort()
            self._save(record=record)
            return self._view(record, player_id)

    async def flush_settlements(self, gateway) -> int:
        """Replay durable, idempotent results; never hold the match lock over I/O."""
        if self.repository is None:
            raise MatchStoreError('Ranked settlement requires durable match storage.')
        async with self.settlement_lock:
            async with self.lock:
                self._ensure_store()
                try:
                    pending = self.repository.pending_settlements()
                except MatchStoreError:
                    self.storage_failed = True
                    raise
            completed = 0
            for result in pending:
                async with self.lock:
                    record = self.matches.get(result.get('match_id'))
                    if record is None or record.match.mode != 'geared' or record.match.phase is not Phase.FINISHED or record.settled:
                        self.storage_failed = True
                        raise MatchStoreError('Ranked settlement state is inconsistent.')
                    players = list(record.match.fighters)
                    if len(players) != 2:
                        self.storage_failed = True
                        raise MatchStoreError('Ranked settlement state is inconsistent.')
                    expected = {'match_id':record.match.match_id, 'target_group':record.match.group_id,
                                'first_player':players[0], 'second_player':players[1], 'winning_player':record.match.winner}
                    if result != expected:
                        self.storage_failed = True
                        raise MatchStoreError('Ranked settlement state is inconsistent.')
                try:
                    await gateway.settle(result)
                except MatchStoreError:
                    async with self.lock:
                        self.storage_failed = True
                    raise
                async with self.lock:
                    self._ensure_store()
                    record = self.matches.get(result['match_id'])
                    if record is None or record.match.mode != 'geared' or record.match.phase is not Phase.FINISHED:
                        self.storage_failed = True
                        raise MatchStoreError('Ranked settlement state is inconsistent.')
                    record.settled = True
                    self._save(record=record, remove_settlements=(record.match.match_id,))
                    completed += 1
            return completed

    async def expire_inactive(self) -> int:
        """Persist server-owned timeout, ready-grace, and disconnect outcomes."""
        now = self.clock()
        expired = 0
        async with self.lock:
            self._ensure_store()
            for record in tuple(self.matches.values()):
                if record.match.expire(now):
                    self._save(record=record)
                    expired += 1
        return expired
