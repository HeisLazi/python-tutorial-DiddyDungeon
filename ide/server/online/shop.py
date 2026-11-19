"""Curated, online-only rewards sold for the separate online wallet."""
from __future__ import annotations

from copy import deepcopy


ONLINE_SHOP_GEAR = (
    {
        'id': 'online-cinder-vow',
        'name': 'Cinder Vow',
        'slot': 'trinket',
        'tier': 'rare',
        'price': 60,
        'description': 'A warm iron oath-ring, earned from the online merchant.',
        'effect': {'retry_impact': 2, 'heal_on_break': 2},
        'art': 'flame-charm',
        'mode_eligibility': ['campaign', 'sparring', 'pvp'],
        'source': 'online-merchant',
    },
    {
        'id': 'online-pale-guard-locket',
        'name': 'Pale Guard Locket',
        'slot': 'trinket',
        'tier': 'legendary',
        'price': 120,
        'description': 'A moon-pale ward that softens the cost of a mistake.',
        'effect': {'reduction': 14, 'block_first_miss': True},
        'art': 'shield',
        'mode_eligibility': ['campaign', 'sparring', 'pvp'],
        'source': 'online-merchant',
    },
    {
        'id': 'online-last-laugh-charm',
        'name': 'Last Laugh Charm',
        'slot': 'trinket',
        'tier': 'ethereal',
        'price': 220,
        'description': 'A glass charm that returns health for verified work, starts you guarded and brings you back once.',
        'effect': {'heal_on_objective': 3, 'revive': True, 'start_guards': 1, 'xp_bonus': 10},
        'art': 'gemstone',
        'mode_eligibility': ['campaign', 'sparring', 'pvp'],
        'source': 'online-merchant',
    },
)

# Appearance rewards are earned through completed PvP wins, never bought for
# power. The weapon line follows the server-resolved combat style in a duel.
# Tier variants are distinct visual unlocks over existing equipment.
MASTERY_TIERS = (('rare', 5), ('legendary', 15), ('ethereal', 30))
WEAPON_MASTERY_NAMES = {
    'sword': ('Gloamsteel Edge', 'Sunward Oathblade', 'Wraith Regent'),
    'staff': ('Cinderwood Focus', 'Goldstar Scepter', 'Astral Beacon'),
    'whip': ('Dustlash', 'Gilded Coil', 'Wraithsilk Lash'),
    'greatsword': ('Oathbreaker', 'Crownbreaker', 'Ethereal Decree'),
    'handmagic': ('Runehand', 'Sigilweaver', 'Aether Sovereign'),
    'scythe': ('Grim Harvest', 'Chapel Reaper', 'Veil Reaper'),
    'oil': ('Pink-Cap Crusher', 'Gilded Oilbrand', 'The Eternal Bottle'),
}
ARMOR_MASTERY_NAMES = ('Gilt Houseguard', 'Colosseum Warden', 'Spectral Crownwarden')


def _mastery_catalog() -> list[dict]:
    result = []
    for tier_index, (tier, wins) in enumerate(MASTERY_TIERS):
        result.append({
            'id': f'online-mastery-armor-{tier}',
            'name': ARMOR_MASTERY_NAMES[tier_index],
            'slot': 'appearance', 'appearance_type': 'armor', 'tier': tier,
            'price': 0, 'purchasable': False,
            'description': f'A {tier} House Champions armour appearance. Cosmetic only; armour stats stay unchanged.',
            'art': f'mastery-armor-{tier}', 'mode_eligibility': ['campaign', 'sparring', 'pvp'],
            'source': 'pvp-mastery', 'unlock_rule': 'total_wins', 'required_wins': wins,
        })
        for style, names in WEAPON_MASTERY_NAMES.items():
            result.append({
                'id': f'online-mastery-weapon-{style}-{tier}',
                'name': names[tier_index],
                'slot': 'appearance', 'appearance_type': 'weapon', 'style': style, 'tier': tier,
                'price': 0, 'purchasable': False,
                'description': f'A {tier} {style} mastery appearance. Cosmetic only; weapon effects stay unchanged.',
                'art': f'mastery-weapon-{style}-{tier}', 'mode_eligibility': ['campaign', 'sparring', 'pvp'],
                'source': 'pvp-mastery', 'unlock_rule': 'style_wins', 'required_wins': wins,
            })
    return result


ONLINE_MASTERY_CATALOG = tuple(_mastery_catalog())
ONLINE_MASTERY_BY_ID = {item['id']: item for item in ONLINE_MASTERY_CATALOG}

ONLINE_SHOP_BY_ID = {item['id']: item for item in ONLINE_SHOP_GEAR}


def public_shop_catalog() -> list[dict]:
    """Return client-safe stock and mastery rewards; all rewards are server-authored."""
    return deepcopy([*ONLINE_SHOP_GEAR, *ONLINE_MASTERY_CATALOG])
