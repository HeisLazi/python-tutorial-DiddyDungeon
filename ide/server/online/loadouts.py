"""Server-owned friendly duel equipment catalogue.

Friendlies borrow campaign items for this match only. Their PvP effects are
bounded conversions; original campaign currencies and save state are never
read or changed. Ranked ownership is intentionally not inferred from local saves.
"""
from __future__ import annotations

from ide.server.state import armory_catalog, ARMORY_COMBAT_STYLES, ARMORY_WEAPON_COMBAT_STYLES
from .duel import DuelError

SLOTS = ('weapon', 'armor', 'trinket')
PVP_MODES = ('campaign', 'sparring', 'pvp')


def _pvp_eligible(item: dict) -> bool:
    """Run pickups are private to Infinite Dungeon unless converted by Journal.

    Journal echoes have their own stable ``campaign-*`` IDs and explicit mode
    eligibility in the campaign catalogue. Raw ``dungeon-*`` pickups remain
    run-only even though they share the broader armory item definitions.
    """
    eligibility = item.get('mode_eligibility')
    if isinstance(eligibility, list):
        return 'pvp' in eligibility
    return item.get('campaign') != 'dungeon'


def _positive(value, cap):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return max(0, min(cap, int(value)))


def _bonuses(item):
    effect = item.get('effect') if isinstance(item.get('effect'), dict) else {}
    slot = item.get('slot')
    if slot == 'weapon':
        # Duel questions are always code, so campaign question-specific triggers
        # aren't assumed to apply. These are explicit bounded duel conversions.
        amount = max(_positive(effect.get('impact'), 3), _positive(effect.get('opening_impact'), 3), _positive(effect.get('retry_impact'), 3))
        return {'damage': amount, 'guard': 0, 'heal': 0}
    if slot == 'armor':
        # Armour has a role of its own. Duel questions are always code, so impact only counts when it applies to
        # every question or to code questions; a free first mistake or a banked guard is worth one more guard.
        impact_on = effect.get('on') in ('any', 'code_checkpoint')
        return {
            'damage': _positive(effect.get('impact'), 3) if impact_on else 0,
            'guard': min(5, _positive(effect.get('reduction'), 60) // 10 + (1 if effect.get('first_miss_free') or effect.get('start_guards') else 0)),
            'heal': min(3, _positive(effect.get('heal_on_objective'), 6)),
        }
    if slot == 'trinket':
        # Same rules as armour: a free first mistake or banked guard is a guard, and impact only counts for code questions.
        impact_on = effect.get('on') in ('any', 'code_checkpoint')
        return {
            'damage': min(3, (_positive(effect.get('impact'), 3) if impact_on else 0) + _positive(effect.get('opening_impact'), 3)),
            'guard': min(5, _positive(effect.get('reduction'), 60) // 10 + (1 if effect.get('block_first_miss') or effect.get('start_guards') else 0)),
            'heal': min(3, _positive(effect.get('heal_on_objective'), 6)),
        }
    return {'damage': 0, 'guard': 0, 'heal': 0}


def public_catalog() -> dict[str, list[dict]]:
    result = {slot: [] for slot in SLOTS}
    for item in armory_catalog().values():
        slot = item.get('slot')
        if slot not in result or not _pvp_eligible(item): continue
        style = item.get('combat_style') or ARMORY_WEAPON_COMBAT_STYLES.get(item['id'])
        bonus = _bonuses(item)
        result[slot].append({'id': item['id'], 'name': item['name'], 'slot': slot,
            'tier': item.get('tier', 'common'), 'combat_style': style if style in ARMORY_COMBAT_STYLES else None,
            'duel_bonus': bonus,
            'mode_eligibility': list(item.get('mode_eligibility', PVP_MODES)),
            **({'source':item['source']} if item.get('source') else {})})
    for items in result.values(): items.sort(key=lambda item: (item['name'].casefold(), item['id']))
    return result


def resolve_loadout(selection: dict, mode: str) -> dict:
    if mode not in ('fair', 'friendly') or not isinstance(selection, dict) or set(selection) - set(SLOTS):
        raise DuelError('Invalid duel loadout.')
    catalog = armory_catalog()
    resolved = {}
    bonus = {'damage': 0, 'guard': 0, 'heal': 0}
    for slot in SLOTS:
        item_id = selection.get(slot)
        if item_id in (None, ''):
            resolved[slot] = None
            continue
        if not isinstance(item_id, str) or len(item_id) > 128:
            raise DuelError('Invalid equipment selection.')
        item = catalog.get(item_id)
        if not item or item.get('slot') != slot:
            raise DuelError('That item is not available in this slot.')
        if not _pvp_eligible(item):
            raise DuelError('Infinite Dungeon pickups stay in their run; unlock a Legacy Journal echo to use a permanent reward here.')
        style = item.get('combat_style') or ARMORY_WEAPON_COMBAT_STYLES.get(item_id)
        item_bonus = _bonuses(item) if mode == 'friendly' else {'damage': 0, 'guard': 0, 'heal': 0}
        for key in bonus: bonus[key] += item_bonus[key]
        resolved[slot] = {'id': item_id, 'name': item['name'], 'slot': slot,
            'combat_style': style if style in ARMORY_COMBAT_STYLES else None, 'duel_bonus': item_bonus}
    resolved['bonus'] = {key: min(value, cap) for key, value, cap in (
        ('damage', bonus['damage'], 3), ('guard', bonus['guard'], 5), ('heal', bonus['heal'], 3))}
    return resolved
