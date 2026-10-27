"""Authoritative server catalog and bounded legacy Home-level projection.

The catalog mirrors the Godot room definitions; a contract test detects drift.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

HOME_ROOM_LADDERS = {'great_hall': [{'name': 'Clear and mend the hall',
                 'cost': 18,
                 'note': 'rubble, puddles and cobwebs cleared, benches and barrels mended'},
                {'name': 'Rebuild the hearth',
                 'cost': 30,
                 'note': 'a proper fire, warmer light, and a second torch lit'},
                {'name': 'Hang crest banners', 'cost': 20, 'note': 'the torn rags are replaced'},
                {'name': 'Lay the crimson runner',
                 'cost': 24,
                 'note': 'a carpet from the door to the hearth'},
                {'name': 'Reglaze the windows',
                 'cost': 28,
                 'note': 'stained glass, coloured light on the floor'},
                {'name': 'Floor the hall in marble',
                 'cost': 68,
                 'note': 'polished marble over the whole floor, and columns on the walls'},
                {'name': 'Hang the chandelier', 'cost': 44, 'note': 'a chandelier and two guards'},
                {'name': 'Set the banquet', 'cost': 52, 'note': 'a long table, chairs and a rug'},
                {'name': 'The grand finish',
                 'cost': 60,
                 'note': 'blue-gold hearth, gold door, trim, urns, four guards'}],
 'library': [{'name': 'Dust and sort',
              'cost': 16,
              'note': 'cobwebs and scattered papers cleared, scrolls stacked'},
             {'name': 'A proper desk', 'cost': 20, 'note': 'a big oak desk, a quill and an open book'},
             {'name': 'Fill the shelves', 'cost': 24, 'note': 'two full bookcases'},
             {'name': 'Light the reading lamps', 'cost': 28, 'note': 'blue candelabra and wall sconces'},
             {'name': 'Hang the star chart', 'cost': 30, 'note': 'a constellation chart and navy banners'},
             {'name': 'Lay the rugs', 'cost': 34, 'note': 'a crimson rug under the desk'},
             {'name': 'The globe and orrery', 'cost': 40, 'note': 'a globe and a brass orrery'},
             {'name': 'Enchant the shelves',
              'cost': 48,
              'note': 'glowing tomes, crystals and a rolling ladder'},
             {'name': 'Open the skylight', 'cost': 56, 'note': 'a skylight, moonlight and floating pages'}],
 'pantry': [{'name': 'Sweep and clean', 'cost': 16, 'note': 'cobwebs and scraps cleared'},
            {'name': 'Light the hearth', 'cost': 20, 'note': 'the cold hearth burns again'},
            {'name': 'Hang the herbs', 'cost': 22, 'note': 'herbs, garlic and sausages hung to dry'},
            {'name': 'Stock the shelves', 'cost': 26, 'note': 'jars, bread and sacks on the shelves'},
            {'name': 'Fill the barrels and crates',
             'cost': 30,
             'note': 'barrels, vegetable crates and sacks'},
            {'name': 'Fix the cooking range', 'cost': 34, 'note': 'a range with steaming copper pots'},
            {'name': 'Set the table', 'cost': 40, 'note': 'a roast ham, bread and bowls'},
            {'name': 'Stoke the feast', 'cost': 50, 'note': 'a roaring fire, torches and steam everywhere'}],
 'gallery': [{'name': 'Dust and clear', 'cost': 16, 'note': 'cobwebs and dust cleared'},
             {'name': 'Mend the display case',
              'cost': 20,
              'note': 'a glass case with a greatsword and a horn'},
             {'name': 'Hang the banners', 'cost': 22, 'note': 'flame banners replace the torn ones'},
             {'name': 'First relics', 'cost': 26, 'note': 'a golden chalice on the central plinth'},
             {'name': 'Lay the carpet and ropes', 'cost': 30, 'note': 'a crimson carpet and gold stanchions'},
             {'name': 'Spotlights', 'cost': 34, 'note': 'the plinths and the case are lit'},
             {'name': 'Mount the beasts', 'cost': 40, 'note': 'a ram, a wolf and a dragon on the wall'},
             {'name': 'Glowing relics', 'cost': 46, 'note': 'a glowing heart and a burning claw'},
             {'name': 'Portrait of the hunter',
              'cost': 54,
              'note': 'a gold-framed portrait and stained glass'}],
 'den': [{'name': 'Clear the nook', 'cost': 14, 'note': "twigs and cobwebs cleared from Pyr's room"},
         {'name': 'A proper perch', 'cost': 20, 'note': 'a stone ledge supports the perch'},
         {'name': 'Build a nest', 'cost': 24, 'note': 'a straw nest for Pyr'},
         {'name': 'Light the lamps', 'cost': 28, 'note': 'warm lantern light fills the nook'},
         {'name': 'Open the wall', 'cost': 36, 'note': 'a cave arch opens onto a mountain sunrise'},
         {'name': 'Vines and glowing flowers',
          'cost': 40,
          'note': 'vines and flowers bring the aerie to life'},
         {'name': 'Carve the eagle perch', 'cost': 48, 'note': 'an ornate blue and gold perch'},
         {'name': 'The golden nest', 'cost': 28, 'note': 'a glowing golden feather nest'},
         {'name': 'The phoenix aerie', 'cost': 28, 'note': 'a blue lantern and drifting golden embers'}],
 'war_room': [{'name': 'Clear the war room', 'cost': 16, 'note': 'cobwebs and rubble cleared'},
              {'name': 'Mend the table', 'cost': 20, 'note': 'a repaired planning table and parchment'},
              {'name': 'Light the candles', 'cost': 24, 'note': 'candlelight illuminates the planning table'},
              {'name': 'Pin the maps', 'cost': 28, 'note': 'maps and charts cover the wall'},
              {'name': 'Hang the banners', 'cost': 30, 'note': "the war room's banners are raised"},
              {'name': 'Lay the rug', 'cost': 34, 'note': 'a crimson rug beneath the table'},
              {'name': 'The great map table',
               'cost': 42,
               'note': 'an illuminated map with markers and seals'},
              {'name': 'Hang the chandelier', 'cost': 48, 'note': 'a flickering chandelier lights the room'},
              {'name': 'Crystal ball and chests',
               'cost': 54,
               'note': 'a glowing crystal ball and treasure chests'}],
 'armory': [{'name': 'Sweep and clear', 'cost': 16, 'note': 'cobwebs and rubble cleared'},
            {'name': 'Stock the rack',
             'cost': 20,
             'note': 'a few swords and spears on the rack, a barrel of spears'},
            {'name': 'Mend the dummy', 'cost': 24, 'note': 'a new wooden training dummy'},
            {'name': 'Light the braziers', 'cost': 28, 'note': 'two braziers and a second torch'},
            {'name': 'Hang the banners', 'cost': 30, 'note': 'crossed-sword banners and shields'},
            {'name': 'Lay the ring in stone', 'cost': 36, 'note': 'a stone-walled ring with a rope'},
            {'name': 'The weapon wall', 'cost': 42, 'note': 'a full rack of axes, swords and shields'},
            {'name': 'Iron dummies', 'cost': 48, 'note': 'armoured dummies and an archery target'},
            {'name': 'Enchant the arms',
             'cost': 56,
             'note': 'glowing runes and floating blades on stone pedestals'}]}

HOME_ROOM_LABELS = {
    "great_hall": "Great Hall", "library": "Library", "armory": "Hall of Arms",
    "pantry": "Pantry", "gallery": "Trophy Gallery", "war_room": "War Room", "den": "Pyr's Den",
}
LEGACY_HOME_UPGRADES = {
    "great_hall": ("reinforced-hearth", "field-kitchen", "siphon-basin"),
    "armory": ("warding-loom", "breaker-workbench"),
}


def validate_room_levels(value: object) -> dict[str, int]:
    """Require a complete, bounded map so partial cloud writes cannot erase rooms."""
    if not isinstance(value, Mapping) or set(value) != set(HOME_ROOM_LADDERS):
        raise ValueError("room_levels must contain exactly the seven Home rooms")
    result: dict[str, int] = {}
    for room, ladder in HOME_ROOM_LADDERS.items():
        level = value[room]
        if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= len(ladder):
            raise ValueError(f"room_levels.{room} is outside the room ladder")
        result[room] = level
    return result


def effective_room_levels(progress: Mapping[str, Any]) -> dict[str, int]:
    """Project legacy visual tiers once; never spend currency during migration.

    The old app derived hearth and armory tiers from owned upgrade IDs. The map
    tier was never persisted by the app, so its legacy value is zero.
    """
    home = progress.get("homestead", {})
    if not isinstance(home, Mapping):
        raise ValueError("homestead must be an object")
    if "room_levels" in home:
        return validate_room_levels(home["room_levels"])
    owned = home.get("room_upgrades", [])
    if not isinstance(owned, list) or any(not isinstance(item, str) for item in owned):
        raise ValueError("homestead.room_upgrades must be a list of identifiers")
    levels = {room: 0 for room in HOME_ROOM_LADDERS}
    for room, ids in LEGACY_HOME_UPGRADES.items():
        tier = sum(item in owned for item in ids)
        levels[room] = int(tier * len(HOME_ROOM_LADDERS[room]) / 3 + 0.5)
    return levels
