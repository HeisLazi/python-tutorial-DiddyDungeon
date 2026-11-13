"""Ephemeral shared-hub movement; caller authenticates group membership.

Presence is visual only. It never grants access to equipment, matches, or saves.
Coordinates use the hideout's logical 320×180 space.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


class PresenceError(ValueError):
    pass


@dataclass
class Visitor:
    player_id: str
    name: str
    appearance: str
    x: float
    y: float
    sequence: int
    updated: float


class HideoutPresence:
    MAX_VISITORS = 4
    STALE_SECONDS = 30.0
    MAX_SPEED = 140.0  # logical pixels/second, including network jitter margin
    WALKABLE = (24.0, 104.0, 296.0, 165.0)
    APPEARANCES = frozenset(('classic', 'ivory', 'spectral', 'harvest', 'oracle',
                             'patchwork', 'pilgrim', 'wayfarer', 'lanternkeeper', 'wardplate',
                             'debugger', 'merchant-oracle'))

    def __init__(self, group_id: str):
        if not group_id:
            raise PresenceError('Group is required.')
        self.group_id = group_id
        self.visitors: dict[str, Visitor] = {}

    def _prune(self, now: float) -> None:
        for player_id in tuple(self.visitors):
            if now - self.visitors[player_id].updated > self.STALE_SECONDS:
                del self.visitors[player_id]

    def join(self, player_id: str, name: str, appearance: str, now: float) -> None:
        if not isinstance(player_id, str) or not player_id or len(player_id) > 128 or not isinstance(name, str) or not name.strip() or len(name.strip()) > 24:
            raise PresenceError('Invalid hunter.')
        if appearance not in self.APPEARANCES or not math.isfinite(now):
            raise PresenceError('Invalid appearance or time.')
        self._prune(now)
        if player_id not in self.visitors and len(self.visitors) >= self.MAX_VISITORS:
            raise PresenceError('The hideout is full.')
        if player_id in self.visitors:
            visitor = self.visitors[player_id]
            visitor.name, visitor.appearance, visitor.updated = name.strip(), appearance, now
        else:
            self.visitors[player_id] = Visitor(player_id, name.strip(), appearance, 160.0, 145.0, -1, now)

    def move(self, player_id: str, x: float, y: float, sequence: int, now: float) -> None:
        visitor = self.visitors.get(player_id)
        if visitor is None:
            raise PresenceError('Join the hideout first.')
        if (not isinstance(sequence, int) or isinstance(sequence, bool) or sequence <= visitor.sequence
                or not isinstance(x, (int, float)) or isinstance(x, bool)
                or not isinstance(y, (int, float)) or isinstance(y, bool)
                or not all(math.isfinite(v) for v in (x, y, now)) or now < visitor.updated):
            raise PresenceError('Invalid or out-of-order movement.')
        left, top, right, bottom = self.WALKABLE
        x, y = max(left, min(right, float(x))), max(top, min(bottom, float(y)))
        elapsed = min(1.0, now - visitor.updated)
        distance = math.hypot(x - visitor.x, y - visitor.y)
        limit = self.MAX_SPEED * elapsed + 4.0
        if distance > limit:
            ratio = limit / distance
            x = visitor.x + (x - visitor.x) * ratio
            y = visitor.y + (y - visitor.y) * ratio
        visitor.x, visitor.y, visitor.sequence, visitor.updated = x, y, sequence, now

    def leave(self, player_id: str) -> None:
        self.visitors.pop(player_id, None)

    def snapshot(self, now: float) -> list[dict]:
        if not math.isfinite(now):
            raise PresenceError('Invalid time.')
        self._prune(now)
        return [{'player_id': v.player_id, 'name': v.name, 'appearance': v.appearance,
                 'x': round(v.x, 1), 'y': round(v.y, 1), 'sequence': v.sequence}
                for v in self.visitors.values()]
