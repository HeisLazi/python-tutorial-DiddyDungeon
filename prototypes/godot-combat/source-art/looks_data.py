"""One entry per recoloured look: the parent outfit and the colour-band rules (see looks.py).

Look ids are what hunterEquipment.js returns as `armorLook`; ARMOUR_LOOKS in that file maps each armour to one.
Rules run in order and a pixel takes the first rule that matches it, so put the narrow bands first.
"""

# Tate's gold trim, and his black coat. Trim is saturated and bright; cloth is dark and nearly neutral.
GOLD = dict(hue=(30, 66), sat=(0.28, 1.0), val=(0.3, 1.0))
CLOTH = dict(sat=(0.0, 0.45), val=(0.0, 0.72))
# Any coloured pixel, any neutral dark pixel, any neutral light pixel (for the parents that are not black-and-gold).
COLOURED = dict(sat=(0.14, 1.0), val=(0.05, 1.0))
NEUTRAL_DARK = dict(sat=(0.0, 0.14), val=(0.04, 0.55))
NEUTRAL_LIGHT = dict(sat=(0.0, 0.22), val=(0.5, 1.0))
WHITE = dict(sat=(0.0, 0.2), val=(0.62, 1.0))
BLUE = dict(hue=(165, 262), sat=(0.1, 1.0), val=(0.25, 1.0))
BROWN = dict(hue=(8, 62), sat=(0.15, 1.0), val=(0.05, 1.0))

LOOKS = {
    # Tate: a long black coat. Different trim and cloth colours.
    "dealer": {"parent": "tate", "rules": [("rot", {**GOLD, "set": 2, "dv": 0.95})]},
    "velvet": {"parent": "tate", "rules": [("rot", {**GOLD, "set": 44, "ds": 0.8, "dv": 0.9}), ("tint", {**CLOTH, "to_hue": 140, "sat_to": 0.55, "dv": 1.5, "add_v": 0.07})]},
    "doorman": {"parent": "tate", "rules": [("rot", {**GOLD, "set": 46}), ("tint", {**CLOTH, "to_hue": 352, "sat_to": 0.85, "dv": 2.2, "add_v": 0.1})]},
    "sequin": {"parent": "tate", "rules": [("rot", {**GOLD, "set": 235, "ds": 0.12, "dv": 1.25}), ("tint", {**CLOTH, "to_hue": 275, "sat_to": 0.5, "dv": 1.6, "add_v": 0.09})]},
    "gilded": {"parent": "tate", "rules": [("rot", {**GOLD, "set": 46, "ds": 1.05, "dv": 1.1}), ("tint", {**CLOTH, "to_hue": 215, "sat_to": 0.16, "dv": 1.7, "add_v": 0.2})]},
    # Ivory: a white coat with gold trim.
    "highroller": {"parent": "ivory", "rules": [("tint", {**WHITE, "to_hue": 352, "sat_to": 0.8, "dv": 0.5}), ("tint", {**NEUTRAL_DARK, "to_hue": 352, "sat_to": 0.7, "dv": 1.4, "add_v": 0.04})]},
    # Harvest: ragged dark cloak with orange accents.
    "pitboss": {"parent": "harvest", "rules": [("rot", {**BROWN, "set": 352, "ds": 1.1, "dv": 1.35}), ("tint", {**NEUTRAL_DARK, "to_hue": 350, "sat_to": 0.35, "dv": 1.5, "add_v": 0.05})]},
    # Debugger: steel plate with blue lights.
    "vault": {"parent": "debugger", "rules": [("rot", {**BLUE, "set": 30, "ds": 1.4, "dv": 1.1}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 32, "sat_to": 0.32, "dv": 0.95}), ("tint", {**NEUTRAL_DARK, "to_hue": 28, "sat_to": 0.3, "dv": 1.15, "add_v": 0.03})]},
    "fortune": {"parent": "debugger", "rules": [("rot", {**BLUE, "set": 150, "ds": 1.5, "dv": 1.05}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 46, "sat_to": 0.75, "dv": 1.05}), ("tint", {**NEUTRAL_DARK, "to_hue": 44, "sat_to": 0.6, "dv": 1.25, "add_v": 0.05})]},
    # Arcane: dark silver with teal light.
    "flowkeeper": {"parent": "oracle", "rules": [("rot", {**BLUE, "set": 140, "dv": 1.05}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 150, "sat_to": 0.2}), ("tint", {**NEUTRAL_DARK, "to_hue": 150, "sat_to": 0.25, "dv": 1.2, "add_v": 0.03})]},
    # Warden: spectral heavy plate.
    "deepvein": {"parent": "warden", "rules": [("rot", {**COLOURED, "set": 190, "ds": 0.8, "dv": 0.75}), ("tint", {**NEUTRAL_DARK, "to_hue": 215, "sat_to": 0.12})]},
    "drowned": {"parent": "warden", "rules": [("rot", {**COLOURED, "set": 200, "ds": 0.75, "dv": 1.25}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 28, "sat_to": 0.45}), ("tint", {**NEUTRAL_DARK, "to_hue": 205, "sat_to": 0.3, "dv": 1.4, "add_v": 0.04})]},
    # Wardplate: red-brown plate and cloak.
    "firstlight": {"parent": "wardplate", "rules": [("rot", {**COLOURED, "set": 42, "ds": 0.45, "dv": 1.55}), ("tint", {**NEUTRAL_DARK, "to_hue": 40, "sat_to": 0.2, "dv": 2.2, "add_v": 0.12})]},
    "coreforged": {"parent": "wardplate", "rules": [("rot", {**COLOURED, "set": 18, "ds": 1.5, "dv": 0.5}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 20, "sat_to": 0.1, "dv": 0.3}), ("tint", {**NEUTRAL_DARK, "to_hue": 10, "sat_to": 0.1, "dv": 0.6})]},
    # Norse: grey-blue mail and fur.
    "lamellar": {"parent": "norse", "rules": [("rot", {**COLOURED, "set": 28, "ds": 1.5, "dv": 1.15}), ("tint", {**NEUTRAL_DARK, "to_hue": 28, "sat_to": 0.4, "dv": 1.3, "add_v": 0.03})]},
    # Lanternkeeper: fur collar and a lamp.
    "lanternscale": {"parent": "lanternkeeper", "rules": [("rot", {**COLOURED, "set": 20, "ds": 1.6, "dv": 1.35}), ("tint", {**NEUTRAL_DARK, "to_hue": 14, "sat_to": 0.4, "dv": 1.7, "add_v": 0.06}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 40, "sat_to": 0.4})]},
    "lanternbound": {"parent": "lanternkeeper", "rules": [("rot", {**COLOURED, "set": 38, "ds": 0.3, "dv": 1.45}), ("tint", {**NEUTRAL_DARK, "to_hue": 30, "sat_to": 0.1, "dv": 1.2, "add_v": 0.04}), ("tint", {**NEUTRAL_LIGHT, "to_hue": 48, "sat_to": 0.1})]},
    # Pilgrim: brown, olive and green travel gear.
    "canvas": {"parent": "pilgrim", "rules": [("rot", {**COLOURED, "set": 42, "ds": 0.55, "dv": 1.4}), ("tint", {**NEUTRAL_DARK, "to_hue": 40, "sat_to": 0.2, "dv": 1.5, "add_v": 0.04})]},
    "merchantpilgrim": {"parent": "pilgrim", "rules": [("rot", {**COLOURED, "set": 208, "ds": 0.85, "dv": 1.2}), ("tint", {**NEUTRAL_DARK, "to_hue": 210, "sat_to": 0.3, "dv": 1.4, "add_v": 0.04})]},
    # Wayfarer: brown brigandine.
    "riveted": {"parent": "wayfarer", "rules": [("rot", {**COLOURED, "set": 6, "ds": 1.0, "dv": 0.7}), ("tint", {**NEUTRAL_DARK, "to_hue": 4, "sat_to": 0.2, "dv": 0.9})]},
    "merchantwayfarer": {"parent": "wayfarer", "rules": [("rot", {**COLOURED, "set": 24, "ds": 1.35, "dv": 1.5}), ("tint", {**NEUTRAL_DARK, "to_hue": 20, "sat_to": 0.25, "dv": 1.5, "add_v": 0.05})]},
    # Patchwork: mended olive and brown.
    "merchantpatchwork": {"parent": "patchwork", "rules": [("rot", {"hue": (8, 112), "sat": (0.14, 1.0), "val": (0.4, 1.0), "set": 178, "ds": 1.3, "dv": 1.05}), ("rot", {**BROWN, "set": 28, "ds": 1.0, "dv": 0.95})]},
    "auditor": {"parent": "patchwork", "rules": [("rot", {**COLOURED, "set": 214, "ds": 0.45, "dv": 0.95}), ("tint", {**NEUTRAL_DARK, "to_hue": 215, "sat_to": 0.18, "dv": 1.3, "add_v": 0.03})]},
}
