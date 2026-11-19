"""Whip held weapons: a signature piece on the end of the baked lash.

A lash curves and swings, so there is no rigid axis to redraw a weapon along (the sword and scythe generators
do that). Recolouring it by colour was tried and does not hold across outfits. Instead the baked lash stays and
each whip adds one small piece at the far tip in the strike frame, where the lash is stretched out and its end is
simply the right-most opaque pixel. That needs no colour matching and no hand position:

  croupier's rake  -> a brass comb head
  warden's oathchain -> iron links ending in a weight
  bounty hunter's lash -> a steel barb

The Hunter's Whip is the plain lash and keeps the baked art. The base sheets are copies of the whip sheets
(they are already weapon-less in the sense that matters: nothing is erased). Any outfit whose strike frame has no
clear tip gets no strip for that frame and simply shows the plain lash.

Usage:  python3 held_whips.py [--force]       (then `godot --headless --path .. --import`)
"""
from __future__ import annotations

import argparse
import math

import numpy as np
from PIL import Image

from held_weapons import ART, HELD, OUTFITS

CELL = 128
STRIKE = 2  # the frame where the lash is stretched out
WHIP_WEAPONS = ["bj-croupier-s-rake", "campaign-dungeon-warden-chain", "campaign-dungeon-pathfinder-whip"]


def px(grid: list[str], palette: dict[str, tuple[int, int, int]]) -> Image.Image:
    """A tiny piece from rows of characters, pointing right; '.' is empty."""
    h, w = len(grid), max(len(r) for r in grid)
    arr = np.zeros((h, w, 4), np.uint8)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in palette:
                arr[y, x] = (*palette[ch], 255)
    return Image.fromarray(arr, "RGBA")


PIECES = {
    # brass comb: a spine across the end of the lash with three teeth
    "bj-croupier-s-rake": px(
        ["...ab.",
         "..aab.",
         "bbaabb",
         "..aab.",
         "bbaabb",
         "..aab.",
         "...ab."],
        {"a": (214, 174, 74), "b": (138, 98, 40)},
    ),
    # iron links ending in a weight
    "campaign-dungeon-warden-chain": px(
        ["........",
         "cc.cc.dd",
         "c.c.c.dd",
         "cc.cc.dd",
         "........"],
        {"c": (168, 176, 190), "d": (70, 76, 90)},
    ),
    # steel barb
    "campaign-dungeon-pathfinder-whip": px(
        ["..s.....",
         ".sss....",
         "sSSSss..",
         ".sss....",
         "..s....."],
        {"s": (206, 214, 226), "S": (120, 130, 148)},
    ),
}


def tip_of(cell: np.ndarray):
    """The end of the lash in a strike frame: ((x, y), angle in degrees), or None when it is not stretched out."""
    alpha = cell[:, :, 3] > 0
    ys, xs = np.nonzero(alpha)
    if len(xs) == 0 or xs.max() < 100:  # a coiled whip stays near the body
        return None
    x = int(xs.max())
    near = ys[xs >= x - 1]
    y = float(near.mean())
    back = ys[(xs >= x - 9) & (xs <= x - 5)]
    if len(back) == 0:
        return None
    angle = math.degrees(math.atan2(y - float(back.mean()), 6.0))
    return (x, y), max(-35.0, min(35.0, angle))


def build(skin: str, force: bool) -> dict:
    prefix = OUTFITS[skin]
    head = "tate" if prefix is None else f"tate-{prefix}"
    report = {}
    for key, name in (("action", f"{head}-whip-sheet.png"), ("hurt", f"{head}-whip-hurt-sheet.png")):
        sheet = Image.open(ART / name).convert("RGBA")
        sheet.save(HELD / f"base-{skin}-whip-{key}-sheet.png")
        found = None
        if key == "action":
            found = tip_of(np.array(sheet)[:, STRIKE * CELL : (STRIKE + 1) * CELL])
        report[key] = None if found is None else [found[0][0], round(found[0][1], 1), round(found[1], 1)]
        for item_id in WHIP_WEAPONS:
            target = HELD / f"{item_id}-{skin}-whip-{key}.png"
            if target.exists() and not force:
                continue
            out = Image.new("RGBA", sheet.size, (0, 0, 0, 0))
            if found is not None:
                piece = PIECES[item_id].rotate(-found[1], expand=True, resample=Image.NEAREST)
                (x, y), _ = found
                out.alpha_composite(piece, (int(STRIKE * CELL + x - 1), int(round(y - piece.height / 2))))
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
