"""Hand-magic held weapons: a focus, chakram, sceptre or tome shown small at the casting hand.

The hand-magic sheets are already weapon-less (the hunter casts with bare hands), so the base is a copy of the
sheet and the weapon is drawn where the cast spark glows, in the windup and strike frames only. The item is
"conjured" for the cast and is absent in the rest poses, which is why no hand position needs to be guessed there.

Usage:  python3 held_hands.py        (then `godot --headless --path .. --import`)
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from PIL import Image

import held_weapons as hw
import native_weapons
from held_weapons import ART, HELD, OUTFITS, components, load_icon

SIZE = 15  # longest side of the drawn item, in pixels
HAND_MAGIC_WEAPONS = [
    "cas-reel-spinner-chakram", "cas-lady-luck-s-sceptre", "hunter-sparring-focus",
    "campaign-dungeon-runic-casting", "campaign-dungeon-last-page",
]


def spark_centre(cell: np.ndarray):
    r, g, b = cell[:, :, 0], cell[:, :, 1], cell[:, :, 2]
    mask = (cell[:, :, 3] > 0) & (b > 170) & (r > 110) & (g < 130) & (b > g + 70)
    parts = [p for p in components(mask) if len(p) >= 4]
    if not parts:
        return None
    return max(parts, key=len).mean(0)


def draw_item(icon: Image.Image, size: int) -> Image.Image:
    box = icon.getbbox()
    icon = icon.crop(box)
    scale = size / max(icon.size)
    small = icon.resize((max(1, round(icon.width * scale)), max(1, round(icon.height * scale))), Image.LANCZOS)
    a = np.array(small)
    a[:, :, 3] = np.where(a[:, :, 3] >= 110, 255, 0)
    a[:, :, :3] = (255 * (a[:, :, :3] / 255.0) ** 0.7).astype(np.uint8)
    a[a[:, :, 3] == 0] = 0
    return Image.fromarray(a, "RGBA")


def build(skin: str, force: bool) -> dict:
    prefix = OUTFITS[skin]
    head = "tate" if prefix is None else f"tate-{prefix}"
    report = {}
    for key, name in (("action", f"{head}-handmagic-sheet.png"), ("hurt", f"{head}-handmagic-hurt-sheet.png")):
        sheet = Image.open(ART / name).convert("RGBA")
        sheet.save(HELD / f"base-{skin}-handmagic-{key}-sheet.png")
        arr = np.array(sheet).astype(int)
        centres = [spark_centre(arr[:, i * 128 : (i + 1) * 128]) for i in range(4)]
        report[key] = [None if c is None else [round(float(c[0]), 1), round(float(c[1]), 1)] for c in centres]
        for item_id in HAND_MAGIC_WEAPONS:
            target = HELD / f"{item_id}-{skin}-handmagic-{key}.png"
            if target.exists() and not force:
                continue
            icon = load_icon(item_id)
            if icon is None:
                print(f"skip {item_id}: no icon", file=sys.stderr)
                continue
            drawn = native_weapons.load("handmagic", item_id)
            out = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
            if drawn is not None:
                # The pixel-art sprite drawn for this item. A long one (a sceptre or focus) is held tilted up, a round one (a chakram, a page) upright.
                sprite, grip = drawn
                long = sprite.width / sprite.height > 1.6
                for i, c in enumerate(centres):
                    if c is None:
                        continue
                    if long:
                        cell = native_weapons.place(sprite, grip, (float(c[0]), float(c[1])), -50.0, (128, sheet.height))
                    else:
                        cell = Image.new("RGBA", (128, sheet.height), (0, 0, 0, 0))
                        cell.alpha_composite(sprite, (int(round(c[0] - sprite.width / 2)), int(round(c[1] - sprite.height / 2))))
                    out.alpha_composite(cell, (i * 128, 0))
                out.save(target)
                continue
            item = draw_item(icon, SIZE)
            for i, c in enumerate(centres):
                if c is not None:
                    out.alpha_composite(item, (int(round(i * 128 + c[0] - item.width / 2)), int(round(c[1] - item.height / 2))))
            out.save(target)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    for skin in OUTFITS:
        print(skin, build(skin, args.force))


if __name__ == "__main__":
    main()
