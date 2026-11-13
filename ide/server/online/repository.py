"""Dedicated SQLite persistence for online match state, never campaign saves.

One match-service process owns a database on a durable private volume. Records
contain only match metadata and evaluator IDs: never source code or auth tokens.
"""
from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from pathlib import Path

from .challenges import CHAINS
from .content_revision import chain_revision
from .duel import Challenge, Duel, Fighter, Phase, Submission
from .shop import ONLINE_MASTERY_BY_ID, WEAPON_MASTERY_NAMES


class MatchStoreError(RuntimeError):
    pass


class InsufficientOnlineCurrencyError(MatchStoreError):
    pass


class MatchRepository:
    VERSION = 1

    def __init__(self, path: str):
        if not path or path == ':memory:':
            raise MatchStoreError('A dedicated durable match database path is required.')
        target = Path(path).expanduser().resolve()
        if target.name.lower() == 'progress.json' or target.suffix.lower() not in ('.sqlite', '.sqlite3', '.db'):
            raise MatchStoreError('Choose a dedicated SQLite file, never a player save.')
        if not target.parent.is_dir():
            raise MatchStoreError('The match database directory does not exist.')
        self._lock = None
        try:
            self._lock = open(str(target) + '.lock', 'a+b')
            if os.name == 'posix':
                import fcntl
                fcntl.flock(self._lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            elif os.name == 'nt':
                import msvcrt
                self._lock.seek(0)
                if not self._lock.read(1):
                    self._lock.write(b'0'); self._lock.flush()
                self._lock.seek(0)
                msvcrt.locking(self._lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                raise MatchStoreError('This host cannot lock the match database safely.')
            self.connection = sqlite3.connect(str(target), timeout=5, check_same_thread=False)
            if os.name == 'posix': os.chmod(target, 0o600)
            self.connection.execute('PRAGMA journal_mode=WAL')
            self.connection.execute('PRAGMA synchronous=FULL')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_matches (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_invites (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS ranked_settlement_outbox (match_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS ranked_match_results (match_id TEXT PRIMARY KEY, group_id TEXT NOT NULL, first_player TEXT NOT NULL, second_player TEXT NOT NULL, winning_player TEXT, settled_at INTEGER NOT NULL DEFAULT (unixepoch()))')
            self.connection.execute('CREATE TABLE IF NOT EXISTS ranked_group_ratings (group_id TEXT NOT NULL, user_id TEXT NOT NULL, rating INTEGER NOT NULL DEFAULT 1000, wins INTEGER NOT NULL DEFAULT 0, losses INTEGER NOT NULL DEFAULT 0, draws INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(group_id,user_id))')
            self.connection.execute('CREATE INDEX IF NOT EXISTS ranked_group_ratings_order ON ranked_group_ratings(group_id,rating DESC,user_id)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_raids (id TEXT PRIMARY KEY, group_id TEXT NOT NULL, payload TEXT NOT NULL)')
            self.connection.execute('CREATE INDEX IF NOT EXISTS online_raids_group ON online_raids(group_id)')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_reward_ledger (raid_id TEXT NOT NULL, group_id TEXT NOT NULL, user_id TEXT NOT NULL, currency TEXT NOT NULL, amount INTEGER NOT NULL, created_at INTEGER NOT NULL DEFAULT (unixepoch()), PRIMARY KEY(raid_id,user_id))')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_duel_reward_ledger (match_id TEXT NOT NULL, group_id TEXT NOT NULL, user_id TEXT NOT NULL, currency TEXT NOT NULL, amount INTEGER NOT NULL, created_at INTEGER NOT NULL DEFAULT (unixepoch()), PRIMARY KEY(match_id,user_id))')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_purchase_ledger (group_id TEXT NOT NULL, user_id TEXT NOT NULL, item_id TEXT NOT NULL, cost INTEGER NOT NULL, created_at INTEGER NOT NULL DEFAULT (unixepoch()), PRIMARY KEY(group_id,user_id,item_id))')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_item_ownership (user_id TEXT NOT NULL, item_id TEXT NOT NULL, group_id TEXT NOT NULL, cost INTEGER NOT NULL, created_at INTEGER NOT NULL DEFAULT (unixepoch()), PRIMARY KEY(user_id,item_id))')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_mastery_match_ledger (match_id TEXT NOT NULL, user_id TEXT NOT NULL, style TEXT NOT NULL DEFAULT \'\', won INTEGER NOT NULL CHECK(won IN (0,1)), created_at INTEGER NOT NULL DEFAULT (unixepoch()), PRIMARY KEY(match_id,user_id))')
            self.connection.execute('CREATE TABLE IF NOT EXISTS online_mastery_progress (user_id TEXT NOT NULL, style TEXT NOT NULL, wins INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id,style))')
            self.connection.commit()
        except (OSError, sqlite3.Error, MatchStoreError) as exc:
            if self._lock is not None:
                self._lock.close()
            raise MatchStoreError('Could not open the match database.') from exc

    @staticmethod
    def _json(value: dict) -> str:
        return json.dumps({'version': MatchRepository.VERSION, 'data': value}, separators=(',', ':'), allow_nan=False)

    def save(self, *, invite=None, record=None, remove_invites=(), remove_matches=(), remove_settlements=()) -> None:
        try:
            with self.connection:
                if invite is not None:
                    self.connection.execute('INSERT INTO online_invites(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (invite.id, self._json(asdict(invite))))
                if record is not None:
                    ids = tuple(challenge.id for challenge in record.chain)
                    chain_id = next((key for key, chain in CHAINS.items() if tuple(c.id for c in chain) == ids), None)
                    if not chain_id: raise MatchStoreError('Unknown challenge chain cannot be saved.')
                    payload = {'match': asdict(record.match), 'chain_id': chain_id, 'chain_revision': chain_revision(record.chain),
                               'previous_passed': record.previous_passed, 'created': record.created, 'settled': record.settled}
                    self.connection.execute('INSERT INTO online_matches(id,payload) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload', (record.match.match_id, self._json(payload)))
                    if record.match.mode == 'geared' and record.match.phase is Phase.FINISHED and not record.settled:
                        players = list(record.match.fighters)
                        if len(players) != 2 or record.match.winner not in (None, *players):
                            raise MatchStoreError('Invalid ranked result cannot be queued.')
                        settlement = {'match_id':record.match.match_id, 'target_group':record.match.group_id,
                                      'first_player':players[0], 'second_player':players[1], 'winning_player':record.match.winner}
                        self.connection.execute('INSERT INTO ranked_settlement_outbox(match_id,payload) VALUES(?,?) ON CONFLICT(match_id) DO NOTHING', (record.match.match_id, self._json(settlement)))
                    if record.match.phase is Phase.FINISHED:
                        # The winner earns a small reward. The match/player key
                        # prevents save/retry farming; draws award no currency.
                        winner = record.match.winner
                        if winner in record.match.fighters:
                            self.connection.execute(
                                'INSERT INTO online_duel_reward_ledger(match_id,group_id,user_id,currency,amount) VALUES(?,?,?,?,?) ON CONFLICT(match_id,user_id) DO NOTHING',
                                (record.match.match_id, record.match.group_id, winner, 'online', 5),
                            )
                        self._record_mastery_result(record)
                self.connection.executemany('DELETE FROM online_invites WHERE id=?', ((value,) for value in remove_invites))
                self.connection.executemany('DELETE FROM online_matches WHERE id=?', ((value,) for value in remove_matches))
                self.connection.executemany('DELETE FROM ranked_settlement_outbox WHERE match_id=?', ((value,) for value in remove_settlements))
        except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not persist the online match; service stopped safely.') from exc

    def pending_settlements(self, limit: int = 20) -> list[dict]:
        try:
            rows = self.connection.execute('SELECT payload FROM ranked_settlement_outbox ORDER BY rowid LIMIT ?', (max(1, min(limit, 100)),))
            result = []
            for row in rows:
                value = json.loads(row[0])
                if value.get('version') != self.VERSION or not isinstance(value.get('data'), dict):
                    raise ValueError('Unknown settlement format')
                result.append(value['data'])
            return result
        except (sqlite3.Error, ValueError, TypeError, AttributeError) as exc:
            raise MatchStoreError('Could not read ranked settlements.') from exc

    def settle_ranked_result(self, result: dict) -> bool:
        """Apply one authoritative result once, keeping the group ladder local."""
        allowed = {'match_id', 'target_group', 'first_player', 'second_player', 'winning_player'}
        if not isinstance(result, dict) or set(result) != allowed:
            raise MatchStoreError('Invalid ranked result.')
        match_id, group_id = result['match_id'], result['target_group']
        first, second, winner = result['first_player'], result['second_player'], result['winning_player']
        if (not all(isinstance(value, str) and value and len(value) <= 128 for value in (match_id, group_id, first, second))
                or first == second or (winner is not None and winner not in (first, second))):
            raise MatchStoreError('Invalid ranked result.')
        try:
            with self.connection:
                existing = self.connection.execute(
                    'SELECT group_id,first_player,second_player,winning_player FROM ranked_match_results WHERE match_id=?',
                    (match_id,),
                ).fetchone()
                expected = (group_id, first, second, winner)
                if existing is not None:
                    if tuple(existing) != expected:
                        raise MatchStoreError('A ranked match was replayed with conflicting results.')
                    return False
                self.connection.execute(
                    'INSERT INTO ranked_match_results(match_id,group_id,first_player,second_player,winning_player) VALUES(?,?,?,?,?)',
                    (match_id, group_id, first, second, winner),
                )
                self.connection.executemany(
                    'INSERT INTO ranked_group_ratings(group_id,user_id) VALUES(?,?) ON CONFLICT(group_id,user_id) DO NOTHING',
                    ((group_id, first), (group_id, second)),
                )
                ratings = dict(self.connection.execute(
                    'SELECT user_id,rating FROM ranked_group_ratings WHERE group_id=? AND user_id IN (?,?)',
                    (group_id, first, second),
                ))
                first_rating, second_rating = ratings[first], ratings[second]
                first_score = 0.5 if winner is None else (1.0 if winner == first else 0.0)
                expected_first = 1.0 / (1.0 + 10.0 ** ((second_rating - first_rating) / 400.0))
                delta = int(32 * (first_score - expected_first) + (0.5 if first_score > expected_first else -0.5))
                first_delta = delta
                second_delta = -delta
                if winner is None:
                    self.connection.execute(
                        'UPDATE ranked_group_ratings SET rating=rating+?,draws=draws+1 WHERE group_id=? AND user_id=?',
                        (first_delta, group_id, first),
                    )
                    self.connection.execute(
                        'UPDATE ranked_group_ratings SET rating=rating+?,draws=draws+1 WHERE group_id=? AND user_id=?',
                        (second_delta, group_id, second),
                    )
                else:
                    first_won = winner == first
                    self.connection.execute(
                        'UPDATE ranked_group_ratings SET rating=rating+?,wins=wins+?,losses=losses+? WHERE group_id=? AND user_id=?',
                        (first_delta, int(first_won), int(not first_won), group_id, first),
                    )
                    self.connection.execute(
                        'UPDATE ranked_group_ratings SET rating=rating+?,wins=wins+?,losses=losses+? WHERE group_id=? AND user_id=?',
                        (second_delta, int(not first_won), int(first_won), group_id, second),
                    )
            return True
        except MatchStoreError:
            raise
        except (sqlite3.Error, TypeError, ValueError, OverflowError) as exc:
            raise MatchStoreError('Could not settle the ranked result.') from exc

    def group_ratings(self, group_id: str) -> list[dict]:
        if not isinstance(group_id, str) or not group_id:
            raise MatchStoreError('Invalid group identifier.')
        try:
            rows = self.connection.execute(
                'SELECT user_id,rating,wins,losses,draws FROM ranked_group_ratings WHERE group_id=? ORDER BY rating DESC,user_id',
                (group_id,),
            )
            return [{'user_id': row[0], 'rating': row[1], 'wins': row[2], 'losses': row[3], 'draws': row[4]} for row in rows]
        except sqlite3.Error as exc:
            raise MatchStoreError('Could not read the private group ladder.') from exc

    def save_raid(self, record) -> bool:
        """Persist one raid revision and, at completion, grant its reward once."""
        from dataclasses import asdict
        payload = asdict(record)
        payload['members'] = list(record.members)
        payload['reward_recorded'] = record.reward_recorded or record.status == 'completed'
        try:
            with self.connection:
                self.connection.execute(
                    'INSERT INTO online_raids(id,group_id,payload) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',
                    (record.raid_id, record.group_id, self._json(payload)),
                )
                if record.status == 'completed':
                    # Online currency is kept separate from campaign coins.
                    # A stable raid/player key makes completion retries safe.
                    self.connection.executemany(
                        'INSERT INTO online_reward_ledger(raid_id,group_id,user_id,currency,amount) VALUES(?,?,?,?,?) ON CONFLICT(raid_id,user_id) DO NOTHING',
                        ((record.raid_id, record.group_id, member, 'online', 100) for member in record.members),
                    )
                exists = self.connection.execute(
                    'SELECT 1 FROM online_reward_ledger WHERE raid_id=? LIMIT 1', (record.raid_id,)
                ).fetchone() is not None
            return exists
        except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not persist the cooperative project.') from exc

    def load_raids(self) -> list[dict]:
        def unpack(raw: str) -> dict:
            value = json.loads(raw)
            if not isinstance(value, dict) or value.get('version') != self.VERSION or not isinstance(value.get('data'), dict):
                raise ValueError('Unknown raid format')
            return value['data']
        try:
            return [unpack(row[0]) for row in self.connection.execute('SELECT payload FROM online_raids')]
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise MatchStoreError('Could not restore cooperative projects.') from exc

    def online_currency(self, group_id: str, user_id: str) -> int:
        try:
            row = self.connection.execute(
                "SELECT "
                "COALESCE((SELECT SUM(amount) FROM online_reward_ledger WHERE group_id=? AND user_id=? AND currency='online'),0) + "
                "COALESCE((SELECT SUM(amount) FROM online_duel_reward_ledger WHERE group_id=? AND user_id=? AND currency='online'),0) - "
                "COALESCE((SELECT SUM(cost) FROM online_purchase_ledger WHERE group_id=? AND user_id=?),0)",
                (group_id, user_id, group_id, user_id, group_id, user_id),
            ).fetchone()
            return int(row[0])
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not read online rewards.') from exc

    def online_wallet(self, group_id: str, user_id: str) -> dict:
        try:
            raid = self.connection.execute(
                "SELECT COALESCE(SUM(amount),0) FROM online_reward_ledger WHERE group_id=? AND user_id=? AND currency='online'",
                (group_id, user_id),
            ).fetchone()
            pvp = self.connection.execute(
                "SELECT COALESCE(SUM(amount),0) FROM online_duel_reward_ledger WHERE group_id=? AND user_id=? AND currency='online'",
                (group_id, user_id),
            ).fetchone()
            spent = self.connection.execute(
                "SELECT COALESCE(SUM(cost),0) FROM online_purchase_ledger WHERE group_id=? AND user_id=?",
                (group_id, user_id),
            ).fetchone()
            return {'currency':'online', 'balance':max(0, int(raid[0]) + int(pvp[0]) - int(spent[0])),
                    'earned':{'raid':int(raid[0]), 'pvp':int(pvp[0])}, 'spent':int(spent[0])}
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not read online rewards.') from exc

    def online_purchase(self, group_id: str, user_id: str, item_id: str, cost: int) -> dict:
        """Buy once per account; inventory follows the player across groups."""
        if (not isinstance(group_id, str) or not group_id or len(group_id) > 128
                or not isinstance(user_id, str) or not user_id or len(user_id) > 128
                or not isinstance(item_id, str) or not item_id or len(item_id) > 128
                or isinstance(cost, bool) or not isinstance(cost, int) or not 1 <= cost <= 100000):
            raise MatchStoreError('Invalid online purchase.')
        try:
            with self.connection:
                existing = self.connection.execute(
                    'SELECT group_id,cost FROM online_item_ownership WHERE user_id=? AND item_id=?',
                    (user_id, item_id),
                ).fetchone()
                if existing is not None:
                    return {'item_id':item_id, 'cost':int(existing[1]), 'group_id':str(existing[0]), 'purchased':False, 'owned':True}
                balance = self.online_currency(group_id, user_id)
                if balance < cost:
                    raise InsufficientOnlineCurrencyError('You do not have enough online currency for this item.')
                self.connection.execute(
                    'INSERT INTO online_purchase_ledger(group_id,user_id,item_id,cost) VALUES(?,?,?,?)',
                    (group_id, user_id, item_id, cost),
                )
                self.connection.execute(
                    'INSERT INTO online_item_ownership(user_id,item_id,group_id,cost) VALUES(?,?,?,?)',
                    (user_id, item_id, group_id, cost),
                )
            return {'item_id':item_id, 'cost':cost, 'group_id':group_id, 'purchased':True, 'owned':True}
        except MatchStoreError:
            raise
        except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not complete the online purchase.') from exc

    def online_owned_items(self, group_id: str, user_id: str) -> list[str]:
        """Return account ownership (the group argument remains for callers)."""
        try:
            rows = self.connection.execute(
                'SELECT item_id FROM online_item_ownership WHERE user_id=? ORDER BY created_at,item_id',
                (user_id,),
            )
            return [str(row[0]) for row in rows]
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not read online ownership.') from exc

    def _record_mastery_result(self, record) -> None:
        """Record verified PvP wins once, then grant account-wide cosmetics."""
        match = record.match
        if match.phase is not Phase.FINISHED or len(match.fighters) != 2 or match.winner not in (None, *match.fighters):
            raise MatchStoreError('Invalid completed duel cannot advance mastery.')
        for user_id, fighter in match.fighters.items():
            weapon = fighter.loadout.get('weapon') if isinstance(fighter.loadout, dict) else None
            style = weapon.get('combat_style', '') if isinstance(weapon, dict) else ''
            if style not in WEAPON_MASTERY_NAMES:
                style = ''
            won = int(match.winner == user_id)
            inserted = self.connection.execute(
                'INSERT INTO online_mastery_match_ledger(match_id,user_id,style,won) VALUES(?,?,?,?) ON CONFLICT(match_id,user_id) DO NOTHING',
                (match.match_id, user_id, style, won),
            ).rowcount
            if not inserted or not won:
                continue
            for progress_style in ('all', style) if style else ('all',):
                self.connection.execute(
                    'INSERT INTO online_mastery_progress(user_id,style,wins) VALUES(?,?,1) '
                    'ON CONFLICT(user_id,style) DO UPDATE SET wins=wins+1',
                    (user_id, progress_style),
                )
            total_wins = int(self.connection.execute(
                "SELECT wins FROM online_mastery_progress WHERE user_id=? AND style='all'", (user_id,),
            ).fetchone()[0])
            style_wins = int(self.connection.execute(
                'SELECT wins FROM online_mastery_progress WHERE user_id=? AND style=?', (user_id, style),
            ).fetchone()[0]) if style else 0
            candidates = [
                item_id for item_id, item in ONLINE_MASTERY_BY_ID.items()
                if (item['unlock_rule'] == 'total_wins' and total_wins >= item['required_wins'])
                or (item['unlock_rule'] == 'style_wins' and item.get('style') == style and style_wins >= item['required_wins'])
            ]
            self.connection.executemany(
                'INSERT INTO online_item_ownership(user_id,item_id,group_id,cost) VALUES(?,?,?,0) ON CONFLICT(user_id,item_id) DO NOTHING',
                ((user_id, item_id, match.group_id) for item_id in candidates),
            )

    def online_mastery_progress(self, user_id: str) -> dict:
        try:
            rows = self.connection.execute(
                'SELECT style,wins FROM online_mastery_progress WHERE user_id=?', (user_id,),
            ).fetchall()
            counts = {str(style):int(wins) for style, wins in rows}
            owned = self.connection.execute(
                "SELECT item_id FROM online_item_ownership WHERE user_id=? AND item_id LIKE 'online-mastery-%' ORDER BY item_id",
                (user_id,),
            ).fetchall()
            return {'total_wins':counts.get('all', 0),
                    'weapon_wins':{style:count for style,count in counts.items() if style != 'all'},
                    'owned_ids':[str(row[0]) for row in owned]}
        except (sqlite3.Error, TypeError, ValueError) as exc:
            raise MatchStoreError('Could not read online mastery progress.') from exc

    def load(self) -> tuple[list[dict], list[dict]]:
        def unpack(raw: str) -> dict:
            value = json.loads(raw)
            if not isinstance(value, dict) or value.get('version') != self.VERSION or not isinstance(value.get('data'), dict):
                raise ValueError('Unknown match format')
            return value['data']
        try:
            invites = [unpack(row[0]) for row in self.connection.execute('SELECT payload FROM online_invites')]
            matches = [unpack(row[0]) for row in self.connection.execute('SELECT payload FROM online_matches')]
            return invites, matches
        except (sqlite3.Error, ValueError, TypeError) as exc:
            raise MatchStoreError('Could not restore the match database.') from exc

    def close(self) -> None:
        self.connection.close()
        if self._lock is not None:
            self._lock.close()
            self._lock = None


def restore_duel(value: dict) -> Duel:
    """Restore typed state; reject unknown fields/formats rather than guessing."""
    data = dict(value)
    data['phase'] = Phase(data['phase'])
    data['challenges'] = tuple(Challenge(**item) for item in data['challenges'])
    fighters = {}
    for player_id, raw in data['fighters'].items():
        fighter = dict(raw)
        if fighter.get('submission') is not None:
            fighter['submission'] = Submission(**fighter['submission'])
        fighters[player_id] = Fighter(**fighter)
    data['fighters'] = fighters
    return Duel(**data)
