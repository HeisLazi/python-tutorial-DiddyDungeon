"""Briefs for drawing hero and weapon TOGETHER as one sprite (the way the original sheets were made).

Pasting a separately drawn weapon onto a weapon-less hero never looked right: the hands did not grip it and the pixels did not match. Each
(outfit, style, weapon) instead gets its own sheets, redrawn from the outfit's original sheets for that style with only the weapon changed.

Writes docs/review-art/whole/_ref/<skin>-<style>/   the original sheets and each frame at 8x on green
       docs/review-art/whole/<skin>/<style>/<item id>/BRIEF.md + icon.png
Usage:  python3 whole_briefs.py <skin> <style> <item id> [<item id> ...]
"""
from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import held_weapons as hw  # noqa: E402
from looks import source_stem  # noqa: E402

REPO = HERE.parents[2]
OUT = REPO / "docs" / "review-art" / "whole"
KEYS = {"sword": ("idle", "action", "follow", "hurt")}
CELL = {"sword": 96}
KIND = {"sword": "sword", "greatsword": "two-handed weapon", "scythe": "scythe", "staff": "staff", "handmagic": "casting focus", "whip": "whip"}


def names() -> dict:
    code = "import json;from ide.server.state import armory_catalog;print(json.dumps({i['id']:i['name'] for i in armory_catalog().values() if i['slot']=='weapon'}))"
    return json.loads(subprocess.run([str(REPO / ".venv/bin/python"), "-c", code], cwd=REPO, capture_output=True, text=True, check=True).stdout)


def refs(skin: str, style: str) -> tuple[Path, list[str]]:
    d = OUT / "_ref" / f"{skin}-{style}"
    d.mkdir(parents=True, exist_ok=True)
    cw = CELL.get(style, 128)
    keys = KEYS.get(style, ("action", "hurt"))
    for key in keys:
        im = Image.open(hw.ART / f"{source_stem(style, key, hw.OUTFITS[skin] or '')}.png").convert("RGBA")
        im.save(d / f"{key}-sheet.png")
        for i in range(im.width // cw):
            c = im.crop((i * cw, 0, (i + 1) * cw, im.height))
            bg = Image.new("RGBA", c.size, (0, 255, 0, 255))
            bg.alpha_composite(c)
            bg.resize((c.width * 8, c.height * 8), Image.NEAREST).save(d / f"{key}_{i + 1}.png")
    return d, list(keys)


def brief(skin: str, style: str, item: str, name: str, keys: list[str]) -> str:
    cw = CELL.get(style, 128)
    ref = f"docs/review-art/whole/_ref/{skin}-{style}"
    out = f"docs/review-art/whole/{skin}/{style}/{item}"
    sheets = ", ".join(f"`{k}-sheet.png`" for k in keys)
    return f"""# Redraw the `{skin}` hero's {style} sheets with him holding the **{name}**

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero in the `{skin}` outfit has finished, approved sprite sheets for the {style} style, holding a
default {KIND[style]}. They are the quality bar. Make the same sheets with one change: **the weapon in his hands is the {name}**. Hero and weapon are drawn
**together as one sprite**, exactly as in the originals, so his hands really grip it.

## Look at (repo root `{REPO}`)
- `{ref}/<key>-sheet.png` for key in {keys}: the originals ({cw * 4}x72, four {cw}x72 cells each).
- `{ref}/<key>_1.png` .. `<key>_4.png`: each original frame at 8x on green. Use the matching one as the image reference for each frame.
- `{out}/icon.png`: the {name}. Copy its design: silhouette, materials, ornament and colours.

## Files to write (only into `{out}/`)
- {sheets}: {cw * 4}x72 each, four {cw}x72 cells, transparent background, hard pixel edges, alpha 0 or 255 only.
- `preview.png`: for each sheet the ORIGINAL then YOURS, stacked, at 4x nearest-neighbour on a dark blue background.

## Hard requirements
- **Same hero, same pose, same place** in every frame: the same face, hair and outfit; body angle, stance and hands where the original has them. His body is the same size and sits
  on the same pixels as the original (feet on the same row, head at the same height). Check by overlaying your frame on the original.
- **The weapon is the {name}**, held exactly where the original weapon is held: gripped by the same hand(s), at the same angle, about the same total length, pointing the same way.
  Match the original weapon's thickness and pixel density: thin clean lines and simple shading, no thick outline blobs, no oversized head, no blur. Frames where the original shows
  no weapon (if any) stay weapon-less. Keep any spell or motion effect the original has.
- The weapon stays inside the cell in every frame and is the same weapon, same colours, in every frame of every sheet.
- No added glow, shadow or text. At most about 30 colours.

## Method (required)
Use your **image generation tool**, one frame at a time, giving it the matching 8x reference frame and the icon: "the same sprite in the same pose, but the weapon is replaced by
<describe the {name} from the icon>, held the same way, 16-bit Castlevania pixel art, flat chroma-green background". Then clean each frame with a script: key out the green, resize
with nearest-neighbour by the factor that makes the hero's body the same height as in the original frame, snap alpha to 0/255, reduce colours with hard edges, and place it in the
{cw}x72 cell so the feet and head coincide with the original's. Compare with the original at 4x and regenerate any frame where the hero is off-model or moved, the hands are not on
the weapon, or the weapon is the wrong size, cut off, blobby or inconsistent with the other frames. Take as many attempts as you need; quality matters more than speed.
When done, list the files and name any frame you are unhappy with.
"""


def main() -> None:
    skin, style, items = sys.argv[1], sys.argv[2], sys.argv[3:]
    cat = names()
    _, keys = refs(skin, style)
    for item in items:
        d = OUT / skin / style / item
        d.mkdir(parents=True, exist_ok=True)
        hw.load_icon(item).save(d / "icon.png")
        name = cat.get(item) or cat.get(item.replace("campaign-dungeon-", "dungeon-")) or item
        (d / "BRIEF.md").write_text(brief(skin, style, item, name, keys))
        print(f"{skin}/{style}/{item}")


if __name__ == "__main__":
    main()
