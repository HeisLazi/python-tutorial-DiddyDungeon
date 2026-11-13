"""Ranked equipment eligibility, separate from local campaign saves.

Rows are issued by a trusted reward service and read through the player's
RLS-scoped session. An offline save or client-supplied inventory is never proof.
The campaign award integration is not active yet, so this does not enable rank.
"""
from __future__ import annotations

from .duel import DuelError
from .loadouts import resolve_loadout
from .shop import ONLINE_SHOP_BY_ID

# This is deliberately a small, reviewed set. Expanding it is a game-balance
# decision; a campaign item being available in a friendly does not imply rank.
RANKED_GEAR = frozenset({
    'hunter-sparring-staff', 'hunter-sparring-whip', 'hunter-sparring-greatsword',
    'hunter-sparring-scythe', 'hunter-sparring-focus', 'merchant-vigil-sabre',
    'hunter-gravebound-greatblade', 'hunter-gravebound-plate',
    'hunter-harvest-coat', 'merchant-patchwork-coat', 'merchant-pilgrim-leather',
    'merchant-wayfarer-brigandine', 'hunter-soul-lantern', 'hunter-jacklight-charm',
}) | frozenset(ONLINE_SHOP_BY_ID)


def resolve_ranked_loadout(selection: dict, verified_ids: frozenset[str] | None) -> dict:
    if verified_ids is None:
        raise DuelError('Verified gear ownership is unavailable.')
    if not isinstance(selection, dict):
        raise DuelError('Invalid ranked loadout.')
    for item_id in selection.values():
        if item_id in (None, ''):
            continue
        if not isinstance(item_id, str) or item_id not in RANKED_GEAR:
            raise DuelError('That equipment is not approved for ranked duels.')
        if item_id not in verified_ids:
            raise DuelError('That equipment is not verified for your account.')
    return resolve_loadout(selection, 'friendly')
