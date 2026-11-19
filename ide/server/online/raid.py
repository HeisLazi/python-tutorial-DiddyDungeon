"""Small, durable cooperative coding project for private hunter groups.

Raid source is intentionally visible to members of the same verified group so
they can review one another's work. It is stored only in the dedicated online
database, never in campaign saves or evaluator logs.
"""
from __future__ import annotations

import asyncio
import hashlib
import secrets
import time
from dataclasses import dataclass, field

from .challenges import CHAINS
from .duel import DuelError
from .evaluator import EvaluatorUnavailable
from .repository import MatchRepository, MatchStoreError


PROJECT_TASKS = (
    {'id':'repair-reward', 'challenge_id':'chest-fix', 'title':'Repair the reward calculation',
     'objective':'Fix the treasure ledger so an opened chest adds its reward.', 'prerequisites':()},
    {'id':'lock-check', 'challenge_id':'chest-locked', 'title':'Add a lock check',
     'objective':'Extend the ledger so a closed chest keeps its gold.', 'prerequisites':('repair-reward',)},
    {'id':'collect-chests', 'challenge_id':'chest-collect', 'title':'Combine the chest records',
     'objective':'Build the collector that uses the earlier ledger functions.', 'prerequisites':('lock-check',)},
    {'id':'refund-boundary', 'challenge_id':'chest-refund', 'title':'Protect the refund boundary',
     'objective':'Add a refund helper that handles negative amounts and never lets the ledger drop below zero.', 'prerequisites':('collect-chests',)},
)
TASK_BY_ID = {task['id']:task for task in PROJECT_TASKS}
BOSS_CHALLENGES = CHAINS['potion']


@dataclass
class TaskRecord:
    task_id: str
    assignee: str
    status: str = 'available'
    source: str = ''
    source_hash: str = ''
    evaluation_id: str = ''
    passed: bool | None = None
    reviewers: dict[str, str] = field(default_factory=dict)
    volunteer_open: bool = False


@dataclass
class BossRecord:
    hp: int = 35
    max_hp: int = 35
    hunter_hp: dict[str, int] = field(default_factory=dict)
    question_index: int = 0
    seated: bool = True
    feint_pending: bool = False
    feint_player: str = ''
    feint_used: bool = False
    draft_source: str = ''
    evaluating_id: str = ''
    evaluating_hash: str = ''
    requests: dict[str, str] = field(default_factory=dict)
    attack_sequence: int = 0
    last_attack: dict = field(default_factory=dict)


@dataclass
class RaidRecord:
    raid_id: str
    group_id: str
    creator_id: str
    members: tuple[str, ...]
    created_at: float
    status: str
    tasks: dict[str, TaskRecord]
    reward_recorded: bool = False
    boss: BossRecord | None = None


class RaidCoordinator:
    """All methods are called only after the service verifies group membership."""
    MAX_ACTIVE_PER_GROUP = 1

    def __init__(self, evaluator, repository: MatchRepository, clock=time.time):
        self.evaluator = evaluator
        self.repository = repository
        self.clock = clock
        self.lock = asyncio.Lock()
        self.raids: dict[str, RaidRecord] = {}
        self.storage_failed = False
        try:
            for raw in repository.load_raids():
                tasks = {key: TaskRecord(**value) for key, value in raw['tasks'].items()}
                record = RaidRecord(raw['raid_id'], raw['group_id'], raw['creator_id'], tuple(raw['members']),
                                    raw['created_at'], raw['status'], tasks, raw.get('reward_recorded', False),
                                    BossRecord(**raw['boss']) if raw.get('boss') else None)
                # An in-flight evaluator call cannot safely be resumed after a
                # host restart; let its owner retry from the last durable state.
                recovered_evaluation = False
                for task in tasks.values():
                    if task.status == 'evaluating':
                        task.status = 'available'
                        task.evaluation_id = ''
                        task.source_hash = ''
                        recovered_evaluation = True
                if record.boss and record.boss.evaluating_id:
                    record.boss.requests.pop(record.boss.evaluating_id, None)
                    record.boss.evaluating_id = ''
                    record.boss.evaluating_hash = ''
                    recovered_evaluation = True
                self.raids[record.raid_id] = record
                if recovered_evaluation:
                    self.repository.save_raid(record)
        except (KeyError, TypeError, ValueError, MatchStoreError) as exc:
            raise MatchStoreError('Could not safely restore the cooperative project.') from exc

    def _ensure_store(self):
        if self.storage_failed:
            raise MatchStoreError('Online project storage is unavailable.')

    def _save(self, record: RaidRecord):
        self._ensure_store()
        try:
            record.reward_recorded = self.repository.save_raid(record)
        except MatchStoreError:
            self.storage_failed = True
            raise

    def _record(self, group_id: str, player_id: str, raid_id: str) -> RaidRecord:
        self._ensure_store()
        record = self.raids.get(raid_id)
        if not record or record.group_id != group_id or player_id not in record.members:
            raise DuelError('Cooperative project not found.')
        return record

    def _view(self, record: RaidRecord) -> dict:
        challenges = {challenge.id:challenge for challenge in CHAINS['chest']}
        task_rows = []
        for index, (task_id, task) in enumerate(record.tasks.items()):
            content = TASK_BY_ID[task_id]
            challenge = challenges[content['challenge_id']]
            previous = list(record.tasks.values())[:index]
            starter = next((item.source for item in reversed(previous) if item.status == 'accepted' and item.source), challenge.starter)
            task_rows.append({'id':task_id, 'title':content['title'], 'objective':content['objective'],
                              'prompt':challenge.prompt, 'starter':starter,
                              'prerequisites':list(content['prerequisites']), 'assignee':task.assignee,
                              'status':task.status, 'passed':task.passed, 'source':task.source,
                              'reviewers':dict(task.reviewers), 'volunteer_open':task.volunteer_open})
        return {'raid_id':record.raid_id, 'group_id':record.group_id, 'creator_id':record.creator_id, 'status':record.status,
                'created_at':record.created_at, 'members':list(record.members),
                'tasks':task_rows,
                'reward_recorded':record.reward_recorded,
                'boss':self._boss_view(record)}

    def _boss_view(self, record: RaidRecord) -> dict | None:
        boss = record.boss
        if boss is None:
            return None
        question_index = min(boss.question_index, len(BOSS_CHALLENGES) - 1)
        challenge = BOSS_CHALLENGES[question_index]
        attack_type = self._boss_attack_type(boss, challenge)
        phase = 0 if boss.hp > 24 else (1 if boss.hp > 12 else 2)
        return {'name':'The Choef Chief', 'title':'Keeper of the Choefs',
                'hp':boss.hp, 'max_hp':boss.max_hp, 'hunter_hp':dict(boss.hunter_hp),
                'question_index':boss.question_index,
                'question_count':len(BOSS_CHALLENGES),
                'question':{'id':challenge.id, 'title':challenge.title,
                            'prompt':challenge.prompt,
                            'starter':boss.draft_source or challenge.starter},
                'draft_source':boss.draft_source,
                'seated':boss.seated, 'feint_pending':boss.feint_pending,
                'feint_player':boss.feint_player, 'feint_used':boss.feint_used,
                'mechanic_attack':attack_type,
                'attack_sequence':boss.attack_sequence,
                'last_attack':dict(boss.last_attack),
                'phase':phase, 'defeated':record.status == 'completed',
                'failed':record.status == 'boss_failed'}

    @staticmethod
    def _boss_attack_type(boss: BossRecord, challenge) -> str:
        # Missing a marked coding mechanic, or failing to repair the Chief's
        # tampering after withdrawing from his feint, triggers a party-wide hit.
        if challenge.raid_attack_type == 'aoe':
            return 'aoe'
        if boss.feint_used and challenge.id == 'potion-purchase':
            return 'aoe'
        return 'single'

    async def create(self, group_id: str, player_id: str, members: list[str]) -> dict:
        if not self.repository or len(members) < 2 or len(members) > 4 or player_id not in members or len(set(members)) != len(members):
            raise DuelError('A cooperative project needs two to four distinct group members.')
        async with self.lock:
            self._ensure_store()
            active = [r for r in self.raids.values() if r.group_id == group_id and r.status in ('active', 'boss_ready', 'boss_fight', 'boss_failed')]
            if active:
                return self._view(active[0])
            assignments = {task['id']: members[index % len(members)] for index, task in enumerate(PROJECT_TASKS)}
            record = RaidRecord(secrets.token_urlsafe(18), group_id, player_id, tuple(members), self.clock(), 'active',
                                {task_id:TaskRecord(task_id, assignee,
                                    'available' if not TASK_BY_ID[task_id]['prerequisites'] else 'blocked')
                                 for task_id, assignee in assignments.items()})
            self.raids[record.raid_id] = record
            self._save(record)
            return self._view(record)

    async def view(self, group_id: str, player_id: str, raid_id: str) -> dict:
        async with self.lock:
            return self._view(self._record(group_id, player_id, raid_id))

    async def current(self, group_id: str, player_id: str) -> dict | None:
        async with self.lock:
            self._ensure_store()
            # The authenticated route already verifies current group
            # membership. Keep the group's project visible after a member
            # leaves or the roster changes, so returning group members can
            # still see a completed result instead of being offered a blank
            # new project. Mutation endpoints continue to enforce the raid's
            # original member roster through _record().
            visible = [item for item in self.raids.values() if item.group_id == group_id]
            active = [item for item in visible
                      if item.status in ('active', 'boss_ready', 'boss_fight', 'boss_failed')]
            record = max(active, key=lambda item: item.created_at) if active else max(
                (item for item in visible if item.status == 'completed'),
                key=lambda item: item.created_at,
                default=None,
            )
            return self._view(record) if record else None

    async def assign(self, group_id: str, player_id: str, raid_id: str, task_id: str, target_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks.get(task_id)
            if record.status != 'active' or task is None or target_id not in record.members:
                raise DuelError('That task cannot be assigned.')
            if player_id not in (task.assignee, record.creator_id) or task.status not in ('available', 'blocked'):
                raise DuelError('Only the task owner or project creator can reassign unsubmitted work.')
            task.assignee = target_id
            task.volunteer_open = False
            self._save(record)
            return self._view(record)

    async def open_for_volunteers(self, group_id: str, player_id: str, raid_id: str, task_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks.get(task_id)
            if (record.status != 'active' or task is None or task.status not in ('available', 'blocked') or
                    not task.assignee or player_id not in (task.assignee, record.creator_id)):
                raise DuelError('Only the task owner or project creator can open unsubmitted work for volunteers.')
            task.assignee = ''
            task.volunteer_open = True
            self._save(record)
            return self._view(record)

    async def volunteer(self, group_id: str, player_id: str, raid_id: str, task_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks.get(task_id)
            if (record.status != 'active' or task is None or task.status not in ('available', 'blocked') or
                    not task.volunteer_open or task.assignee):
                raise DuelError('This task is not open for volunteers.')
            task.assignee = player_id
            task.volunteer_open = False
            self._save(record)
            return self._view(record)

    async def swap(self, group_id: str, player_id: str, raid_id: str, task_id: str, other_task_id: str,
                   eligible_members: list[str] | None = None) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks.get(task_id)
            other = record.tasks.get(other_task_id)
            allowed_statuses = ('available', 'blocked')
            if (record.status != 'active' or task is None or other is None or task is other or
                    task.status not in allowed_statuses or other.status not in allowed_statuses or
                    task.volunteer_open or other.volunteer_open or not task.assignee or not other.assignee):
                raise DuelError('Choose two assigned, unsubmitted tasks to swap.')
            if player_id != record.creator_id and player_id not in (task.assignee, other.assignee):
                raise DuelError('Only a task owner or project creator can swap assignments.')
            if task.assignee == other.assignee:
                raise DuelError('These tasks already belong to the same member.')
            if eligible_members is not None and (task.assignee not in eligible_members or other.assignee not in eligible_members):
                raise DuelError('Only current group members can hold assigned work.')
            task.assignee, other.assignee = other.assignee, task.assignee
            self._save(record)
            return self._view(record)

    async def submit(self, group_id: str, player_id: str, raid_id: str, task_id: str,
                     request_id: str, source: str) -> dict:
        if self.evaluator is None:
            raise EvaluatorUnavailable('The isolated evaluator is unavailable.')
        if (not isinstance(request_id, str) or not request_id or len(request_id) > 128 or
                not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > 20000):
            raise DuelError('Provide code of at most 20 KB and a submission identifier.')
        digest = hashlib.sha256(source.encode('utf-8')).hexdigest()
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks.get(task_id)
            if record.status != 'active' or task is None or task.assignee != player_id:
                raise DuelError('Only the assigned group member can submit this task.')
            if any(record.tasks[needed].status != 'accepted' for needed in TASK_BY_ID[task_id]['prerequisites']):
                raise DuelError('Finish the earlier task before submitting this one.')
            if task.status in ('evaluating', 'submitted') and task.evaluation_id == request_id and task.source_hash == digest:
                return self._view(record)
            if task.status not in ('available', 'changes_requested', 'failed'):
                raise DuelError('This task is already being reviewed or has been accepted.')
            task.status = 'evaluating'
            task.evaluation_id = request_id
            task.source_hash = digest
            self._save(record)
        try:
            result = await self.evaluator.evaluate(TASK_BY_ID[task_id]['challenge_id'], source, request_id)
        except Exception:
            async with self.lock:
                record = self.raids.get(raid_id)
                task = record.tasks.get(task_id) if record else None
                if task and task.evaluation_id == request_id and task.status == 'evaluating':
                    task.status = 'available'
                    task.evaluation_id = ''
                    self._save(record)
            raise
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks[task_id]
            if task.status != 'evaluating' or task.evaluation_id != request_id or task.source_hash != digest:
                raise DuelError('The task changed while the evaluator was running; retry from the current board.')
            task.source = source
            task.passed = bool(result.passed)
            task.status = 'submitted' if result.passed else 'failed'
            task.reviewers = {}
            self._save(record)
            return self._view(record)

    async def review(self, group_id: str, player_id: str, raid_id: str, task_id: str, decision: str) -> dict:
        if decision not in ('approve', 'request_changes'):
            raise DuelError('Choose approve or request changes.')
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            task = record.tasks.get(task_id)
            if record.status != 'active' or not task or task.status != 'submitted':
                raise DuelError('This task is not ready for peer review.')
            if player_id == task.assignee:
                raise DuelError('Review another member’s contribution, not your own.')
            if task.reviewers.get(player_id) in ('approve', 'request_changes'):
                raise DuelError('Your review has already been recorded.')
            task.reviewers[player_id] = decision
            if decision == 'request_changes':
                task.status = 'changes_requested'
                task.passed = False
            elif len(task.reviewers) >= 1:
                task.status = 'accepted'
                for next_task_id, next_record in record.tasks.items():
                    if (next_record.status == 'blocked' and
                            all(record.tasks[needed].status == 'accepted' for needed in TASK_BY_ID[next_task_id]['prerequisites'])):
                        next_record.status = 'available'
            if all(item.status == 'accepted' for item in record.tasks.values()):
                record.status = 'boss_ready'
            self._save(record)
            return self._view(record)

    async def abandon(self, group_id: str, player_id: str, raid_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            if player_id != record.creator_id or record.status not in ('active', 'boss_ready', 'boss_fight'):
                raise DuelError('Only the project creator can abandon this active project.')
            record.status = 'abandoned'
            self._save(record)
            return self._view(record)

    async def start_boss(self, group_id: str, player_id: str, raid_id: str) -> dict:
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            if record.status == 'boss_fight':
                return self._view(record)
            if record.status == 'completed':
                return self._view(record)
            if record.status not in ('boss_ready', 'boss_failed'):
                raise DuelError('Complete and peer-review every task before entering the throne room.')
            record.status = 'boss_fight'
            record.boss = BossRecord(hunter_hp={member:5 for member in record.members})
            self._save(record)
            return self._view(record)

    async def submit_boss(self, group_id: str, player_id: str, raid_id: str, question_id: str,
                         request_id: str, source: str) -> dict:
        if self.evaluator is None:
            raise EvaluatorUnavailable('The isolated evaluator is unavailable.')
        if (not isinstance(request_id, str) or not request_id or len(request_id) > 128 or
                not isinstance(source, str) or not source.strip() or len(source.encode('utf-8')) > 20000):
            raise DuelError('Provide code of at most 20 KB and a submission identifier.')
        digest = hashlib.sha256(source.encode('utf-8')).hexdigest()
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            boss = record.boss
            if record.status != 'boss_fight' or boss is None:
                raise DuelError('The throne room encounter is not active.')
            if boss.hunter_hp.get(player_id, 0) <= 0:
                raise DuelError('This hunter is down; another group member must submit the next answer.')
            if request_id in boss.requests:
                if boss.requests[request_id] != digest:
                    raise DuelError('That submission identifier was already used for different code.')
                return self._view(record)
            if boss.feint_pending:
                raise DuelError('Resolve the Chief’s sarcasm feint before another submission.')
            if boss.question_index >= len(BOSS_CHALLENGES):
                raise DuelError('The Chief has no unanswered challenge.')
            challenge = BOSS_CHALLENGES[boss.question_index]
            if question_id != challenge.id:
                raise DuelError('The shared question changed. Refresh the encounter before submitting.')
            if boss.evaluating_id:
                raise DuelError('A group submission is already being checked.')
            boss.evaluating_id = request_id
            boss.evaluating_hash = digest
            boss.requests[request_id] = digest
            while len(boss.requests) > 128:
                boss.requests.pop(next(iter(boss.requests)))
            self._save(record)
        try:
            result = await self.evaluator.evaluate(challenge.id, source, request_id)
        except Exception:
            async with self.lock:
                record = self.raids.get(raid_id)
                boss = record.boss if record else None
                if boss and boss.evaluating_id == request_id:
                    boss.evaluating_id = ''
                    boss.evaluating_hash = ''
                    boss.requests.pop(request_id, None)
                    self._save(record)
            raise
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            boss = record.boss
            if (record.status != 'boss_fight' or boss is None or boss.evaluating_id != request_id or
                    boss.evaluating_hash != digest or boss.question_index >= len(BOSS_CHALLENGES) or
                    BOSS_CHALLENGES[boss.question_index].id != challenge.id):
                raise DuelError('The encounter changed while the isolated checker was running; refresh and retry.')
            boss.evaluating_id = ''
            boss.evaluating_hash = ''
            boss.seated = False
            boss.draft_source = source
            if result.passed and boss.question_index == 1 and not boss.feint_used:
                boss.feint_pending = True
                boss.feint_player = player_id
            elif result.passed:
                damage = 15 if boss.question_index == 2 else 10
                boss.hp = max(0, boss.hp - damage)
                boss.attack_sequence += 1
                boss.last_attack = {'sequence':boss.attack_sequence, 'type':'hunter',
                                    'source_player':player_id, 'target_players':[],
                                    'challenge_id':challenge.id, 'damage':damage}
                boss.question_index += 1
            else:
                attack_type = self._boss_attack_type(boss, challenge)
                targets = list(boss.hunter_hp) if attack_type == 'aoe' else [player_id]
                for target_id in targets:
                    boss.hunter_hp[target_id] = max(0, boss.hunter_hp.get(target_id, 5) - 1)
                boss.attack_sequence += 1
                boss.last_attack = {'sequence':boss.attack_sequence,
                                    'type':attack_type,
                                    'source_player':player_id, 'target_players':targets,
                                    'damage':1, 'challenge_id':challenge.id}
                if not any(hp > 0 for hp in boss.hunter_hp.values()):
                    record.status = 'boss_failed'
            if boss.hp <= 0 or boss.question_index >= len(BOSS_CHALLENGES):
                record.status = 'completed'
            self._save(record)
            return self._view(record)

    async def resolve_boss_feint(self, group_id: str, player_id: str, raid_id: str, decision: str) -> dict:
        if decision not in ('stand_firm', 'withdraw'):
            raise DuelError('Choose to stand firm or withdraw your answer.')
        async with self.lock:
            record = self._record(group_id, player_id, raid_id)
            boss = record.boss
            if record.status != 'boss_fight' or boss is None or not boss.feint_pending:
                raise DuelError('There is no active sarcasm feint to resolve.')
            if boss.feint_player != player_id:
                raise DuelError('The hunter who submitted this answer must choose whether to stand firm.')
            boss.feint_pending = False
            boss.feint_player = ''
            boss.feint_used = True
            if decision == 'stand_firm':
                damage = 15
                boss.hp = max(0, boss.hp - damage)
                boss.attack_sequence += 1
                boss.last_attack = {'sequence':boss.attack_sequence, 'type':'hunter',
                                    'source_player':player_id, 'target_players':[],
                                    'challenge_id':BOSS_CHALLENGES[boss.question_index].id,
                                    'damage':damage}
                boss.question_index += 1
            else:
                # The Chief visibly tampers with the shared helper. This remains
                # ordinary source text and must pass the same isolated checks.
                boss.draft_source = (boss.draft_source.rstrip() +
                    '\n\n# The Choef Chief tampered with your helper. Fix the exact-price check.\n'
                    'def can_buy(balance, price):\n    return balance > price\n')
            if boss.hp <= 0 or boss.question_index >= len(BOSS_CHALLENGES):
                record.status = 'completed'
            self._save(record)
            return self._view(record)
