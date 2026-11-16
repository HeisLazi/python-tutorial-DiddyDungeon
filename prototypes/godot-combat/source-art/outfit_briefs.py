"""Write the Codex briefs for brand-new (not recoloured) armour outfits.

Each outfit is the same hero (Tate: dark skin, black swept hair) wearing that armour, drawn from scratch in Tate's poses for every weapon style.
Per outfit this makes   docs/review-art/outfits-new/<look>/DESIGN_BRIEF.md          (step 1: design.md + master.png)
                        docs/review-art/outfits-new/<look>/<style>/BRIEF.md        (step 2: the style's sheets)
The pose references are Tate's weapon-less bases at 4x (docs/review-art/outfits-new/_pose/<style>.png); the garment design is the armour's own icon.

Usage:  python3 outfit_briefs.py [look ...]      (all looks but highroller when none are named)
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
NEW = REPO / "docs" / "review-art" / "outfits-new"
HELD = HERE.parent / "art" / "held"
KEEP = {"highroller"}  # bloody Ivory stays as it is
CELL = {"sword": 96, "greatsword": 128, "scythe": 128, "staff": 128, "handmagic": 128, "whip": 128}
SHEETS = {
    "sword": ["idle", "action", "follow", "hurt"],
    "greatsword": ["action", "hurt"], "scythe": ["action", "hurt"], "staff": ["action", "hurt"],
    "handmagic": ["action", "hurt"], "whip": ["action", "hurt"],
}
HOLD = {
    "sword": "one hand gripping an invisible sword hilt (a closed fist), the other hand free or on the hip",
    "greatsword": "both fists closed on an invisible two-handed sword hilt, a forearm apart",
    "scythe": "both fists closed on an invisible long pole, a forearm apart (2-3 px gap between them)",
    "staff": "one or both fists closed on an invisible staff; the staff itself is NOT drawn",
    "handmagic": "casting: open or half-open hand(s) raised, fingers spread, with NO spell effect, glow or object drawn",
    "whip": "one fist closed on an invisible whip handle, the other arm balanced; no whip drawn",
}


def boxes(style: str) -> str:
    rows = []
    for key in SHEETS[style]:
        path = HELD / f"base-tate-{style}-{key}-sheet.png"
        im = Image.open(path).convert("RGBA")
        cw = CELL[style]
        cells = []
        for i in range(im.width // cw):
            bb = im.crop((i * cw, 0, (i + 1) * cw, im.height)).getbbox()
            cells.append(str(bb))
        rows.append(f"  - {key}: " + ", ".join(cells))
    return "\n".join(rows)


def design_brief(look: str, info: dict) -> str:
    return f"""# Design the **{info['armour']}** outfit for the hero (step 1 of 2)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero (Tate: dark brown skin, black swept hair, athletic build) wears many
armours. The **{info['armour']}** (look id `{look}`, effect: {info['effect']}) must become its own **fully distinct outfit**, not a recolour of another one.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/{look}/icon.png`: this armour's icon. **This is the garment design**: its shapes, materials, colours and details.
- `docs/review-art/outfits-new/_pose/sword.png`: Tate at 4x in his sword poses (top row idle, then action, follow-through, hurt). Use the FIRST frame of the top row (the idle stance).
- `docs/review-art/scythe-redo/outfits/ivory/preview.png`: an example of an approved finished outfit sheet (the white Ivory coat) to match for quality and pixel-art style.

## Files to write (only into `docs/review-art/outfits-new/{look}/`)
1. `design.md`: a precise written spec of this outfit as worn by the hero: every garment and accessory, each material, the palette as hex colours (at most 14,
   light source top-left), what shows at the collar, shoulders, chest, waist, sleeves, legs, boots and gloves; how the silhouette differs from the old Tate coat
   (e.g. a shorter vest, plate pauldrons, a long cloak, a skirt of scales). The hero's face, skin tone and black swept hair do NOT change.
2. `master.png`: the hero wearing it in Tate's first idle sword frame pose, facing right, as a 96x72 pixel-art cell at **1x** (transparent background,
   hard pixel edges, about 42 px tall, feet near the bottom row, dark outline, no weapon, nothing in his hands) AND `master-large.png`: the same drawing
   generated large (about 512 px tall) on a flat chroma-green background for later reference.

## Rules
- It must read at a glance as the armour in the icon, and be clearly different in silhouette and colour from Tate's black coat, the white Ivory coat and the other outfits.
- No weapon, no text, no glow, no shadow. Pixel art, hard edges, at most about 28 colours.
- Use your image generation tool, check the result at 4x against the icon, and regenerate until it is faithful and clean. When done, list the files.
"""


def style_brief(look: str, style: str, info: dict) -> str:
    cw = CELL[style]
    names = SHEETS[style]
    files = "\n".join(f"- `{n}-sheet.png`: {cw * 4}x72, four {cw}x72 cells" for n in names)
    return f"""# Draw the **{info['armour']}** outfit in the `{style}` poses (step 2 of 2)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. You are drawing the hero (the same dark-skinned, black-haired hero) wearing the
**{info['armour']}** (look `{look}`) in the `{style}` weapon style: {len(names) * 4} frames in {len(names)} sheet(s). The weapon is drawn separately by code,
so the hero holds **nothing**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/{look}/design.md`, `master.png`, `master-large.png`, `icon.png`: this outfit's design. Copy it exactly.
- `docs/review-art/outfits-new/_pose/{style}.png`: Tate at 4x in the poses to copy ({'; '.join(f'row {i + 1} = {n}' for i, n in enumerate(names))}). The Tate
  reference may still show a stub of its old weapon or glove colours: ignore those, draw the new outfit and leave hands empty.
- `docs/review-art/scythe-redo/outfits/ivory/preview.png`: an approved example of this kind of sheet (Ivory in the scythe poses) for quality and style.

## Files to write (only into `docs/review-art/outfits-new/{look}/{style}/`)
{files}
- `preview.png`: all sheets stacked at 4x with nearest-neighbour on a dark blue background.

## Hard requirements
- **No weapon, pole, staff, whip, spell effect or any object** in any frame. Hold style for this weapon: {HOLD[style]}. Fists/hands clearly visible (skin or glove colour).
- **Copy each pose exactly** (body angle, stance, head turn, arm positions) and match Tate's **scale and place**: each frame's bounding box (x0, y0, x1, y1 in cell
  pixels) should be close to Tate's. Tate's boxes:
{boxes(style)}
- The same hero and the same outfit in every frame (face, hair, garments, palette from design.md). Hard pixel edges, alpha 0 or 255 only, no shadow, no glow, no text,
  at most about 28 colours, dark outline, light from the top-left.

## Method (required)
Use your **image generation tool**, one frame at a time, with the matching Tate pose frame, `master-large.png` and `icon.png` as references. Prompt: the hero
wearing this outfit (describe it from design.md), facing right, in that pose, hands as described, nothing in his hands, Castlevania-style 16-bit pixel art, dark outline,
flat solid chroma-green background, full body, no weapon, no text. Then clean each frame with a script: key out the green, crop to the hero, resize with nearest-neighbour
to Tate's frame height, reduce colours with hard edges, set alpha to 0/255, and place him in his {cw}x72 cell on Tate's box. Compare every frame against the Tate pose at 4x and
regenerate any frame that is off-pose, off-model, holds an object, hides a hand, or is muddy. Take as many attempts as you need. When done, list the files and name any frame you are unhappy with.
"""


def main() -> None:
    info = json.loads((NEW / "looks_map.json").read_text())
    looks = sys.argv[1:] or [k for k in info if k not in KEEP]
    for look in looks:
        d = NEW / look
        d.mkdir(parents=True, exist_ok=True)
        icon = REPO / info[look]["icon"]
        Image.open(icon).convert("RGBA").save(d / "icon.png")
        (d / "DESIGN_BRIEF.md").write_text(design_brief(look, info[look]))
        for style in SHEETS:
            (d / style).mkdir(exist_ok=True)
            (d / style / "BRIEF.md").write_text(style_brief(look, style, info[look]))
        print(look, "briefs written")


if __name__ == "__main__":
    main()
