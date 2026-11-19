"""Briefs for drawing every held weapon natively as pixel art (instead of shrinking the painted Market icon).

Each weapon becomes a small horizontal sprite (butt at the left, tip or head at the right, 1px dark outline, a handful of colours) saved as
docs/review-art/weapons-native/<style>/<item id>.png plus <item id>.json {"grip": x}. A script then rotates and places it on every outfit's pose.

Usage:  python3 weapon_briefs.py        (writes docs/review-art/weapons-native/<style>/BRIEF_<n>.md and copies each icon next to its sprite slot)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import held_hands, held_heads, held_polearms, held_weapons as hw  # noqa: E402

REPO = HERE.parents[2]
OUT = REPO / "docs" / "review-art" / "weapons-native"
LENGTH = {"sword": 34, "greatsword": 52, "scythe": 56, "staff": 52, "handmagic": 14}
THICK = {"sword": "blade 5-7 px wide at the widest, hilt 3-4 px", "greatsword": "blade or head 8-12 px at the widest, grip 3-4 px",
         "scythe": "shaft 3 px, head up to 18 px across", "staff": "shaft 3 px, head up to 14 px across", "handmagic": "about 14 px on its longest side"}
BATCH = {"sword": 6, "greatsword": 7, "scythe": 11, "staff": 11, "handmagic": 5}


def weapons() -> dict[str, list[str]]:
    return {
        "sword": list(hw.SWORD_WEAPONS), "greatsword": list(hw.GREATSWORD_WEAPONS),
        "scythe": list(held_polearms.SCYTHE_WEAPONS), "staff": list(held_heads.STAFF_WEAPONS), "handmagic": list(held_hands.HAND_MAGIC_WEAPONS),
    }


def names() -> dict[str, dict]:
    import subprocess
    code = ("import json;from ide.server.state import armory_catalog;print(json.dumps({i['id']:{'name':i['name'],'effect':str(i.get('effect',''))} "
            "for i in armory_catalog().values() if i['slot']=='weapon'}))")
    out = subprocess.run([str(REPO / ".venv" / "bin" / "python"), "-c", code], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def brief(style: str, items: list[tuple[str, str, str]], n: int) -> str:
    rows = "\n".join(f"| {i} | {name} | `docs/review-art/weapons-native/{style}/icons/{i}.png` | {desc} |" for i, name, desc in items)
    return f"""# Draw {len(items)} `{style}` weapons as real pixel art (batch {n})

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero sprite is chunky pixel art with a 1 px dark outline.
Held weapons are currently the painted Market icons shrunk onto the sprite, which looks soft and off-style. Redraw each weapon below **natively as pixel art**
so it matches the hero. A script will rotate each one and place it in the hero's hands, so you only draw it **straight and horizontal**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/_pose/{'sword' if style == 'sword' else style if style != 'scythe' else 'scythe'}.png` if it exists (the hero at 4x, to judge the pixel density), and `docs/review-art/scythe-redo/outfits/ivory/preview.png`: a finished hero sheet.
- Each weapon's painted icon (table below): copy its **design**: silhouette, materials, ornament, colours.

| Item id | Name | Icon | Notes |
|---|---|---|---|
{rows}

## Sprite spec (every weapon)
- **Horizontal**: the butt/pommel at the LEFT, the tip or head at the RIGHT, the long axis along the centre row. Total length **about {LENGTH[style]} px**; {THICK[style]}.
- Transparent background, **hard pixel edges, alpha 0 or 255 only**, a **1 px dark outline** (about #16101a) all round, at most **12 colours**, light from the top-left, a one-pixel highlight along the lit edge, simple 2-3 tone shading. No anti-aliasing, no glow, no motion trail, no text, no hand or arm.
- Keep the weapon's identity at this tiny size: the skull on a gravekeeper's scythe, the gears on a clockwork blade, the coin on a coin club, the runes on a casting item. Drop detail that cannot be read in {LENGTH[style]} px.
- Canvas = the weapon's tight bounding box plus 2 px of transparent margin on every side.

## Output (only into `docs/review-art/weapons-native/{style}/`)
For each item id: `<item id>.png` (the sprite) and `<item id>.json` with `{{"grip": X}}` where X is the x pixel (from the left edge of the PNG) where the hero's fist closes on it (the centre of the handle or shaft grip).
Also write `contact-sheet-{n}.png`: all sprites in this batch at 6x on a dark blue background with labels.

## Method (required)
Use your **image generation tool** to draw each weapon large and straight on a flat chroma-green background, then clean it with a script: key out the green, crop, resize with nearest-neighbour to the length above, reduce colours with hard edges, add the 1 px outline, set alpha to 0/255. Review each at 6x against its icon and regenerate any that is muddy, off-design, bent, or not horizontal. When done, list the files and name any you are unhappy with.
"""


def main() -> None:
    cat = names()
    for style, ids in weapons().items():
        icons = OUT / style / "icons"
        icons.mkdir(parents=True, exist_ok=True)
        items = []
        for item_id in ids:
            icon = hw.load_icon(item_id)
            if icon is None:
                print("no icon", item_id)
                continue
            icon.save(icons / f"{item_id}.png")
            info = cat.get(item_id) or cat.get(item_id.replace("campaign-dungeon-", "dungeon-")) or {}
            items.append((item_id, info.get("name", item_id), info.get("effect", "")[:90]))
        size = BATCH[style]
        for n, start in enumerate(range(0, len(items), size), 1):
            (OUT / style / f"BRIEF_{n}.md").write_text(brief(style, items[start:start + size], n))
            print(style, "batch", n, len(items[start:start + size]), "weapons")


if __name__ == "__main__":
    main()
