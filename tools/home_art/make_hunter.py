#!/usr/bin/env python3
"""The hunter's 16x32 overworld sprite sheet, drawn pixel by pixel in code.

    python3 tools/home_art/make_hunter.py [out.png]

A 3D render shrunk to 16x32 loses the face and turns to mush, so the walking
sprite is hand-placed pixel art (like FireRed's own); Blender stays for the big
pieces (portraits, props, 3D-to-2D turnarounds; see hunter_blender.py).
The look follows the player's avatar: umber skin, locs, a goatee, a charcoal
indigo cloak with a white scarf, gold belt trim.

Sheet: rows are down, left, right, up; columns are stand, step A, step B.
The walk cycle is stand, A, stand, B. Right is the mirror of left.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from make_tiles import C, Sprite  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
P = {
    "sk0": (112, 66, 40), "sk1": (156, 98, 58), "sk2": (194, 130, 82),
    "hair": (28, 24, 44), "hair1": (66, 58, 98),
    "cl0": (48, 42, 88), "cl1": (74, 64, 132), "cl2": (104, 90, 176),
    "cape0": (70, 44, 118), "cape1": (104, 70, 172),
    "trim": C["gold"], "trim0": C["gold0"], "white": C["white"], "grey": (176, 176, 200),
    "boot0": (30, 26, 48), "boot1": (62, 54, 92), "line": C["line"],
}
FACINGS = ["down", "left", "right", "up"]
POSES = ["stand", "stepa", "stepb"]


class Hunter(Sprite):
    def px(self, x, y, c):
        super().px(x, y, (*P[c], 255) if isinstance(c, str) else c)


def legs_front(s: Hunter, pose: str):
    """Legs seen from the front or back: one lifts on a step."""
    lift = {"stand": (0, 0), "stepa": (2, 0), "stepb": (0, 2)}[pose]
    for x0, up in ((4, lift[0]), (8, lift[1])):
        s.rect(x0, 23, x0 + 3, 27 - up, "cl0")
        s.vline(x0, 23, 27 - up, "cl1")
        s.rect(x0, 28 - up, x0 + 3, 29 - up, "boot0")
        s.hline(x0, x0 + 3, 28 - up, "boot1")


def arms_front(s: Hunter, pose: str):
    swing = {"stand": (0, 0), "stepa": (1, -1), "stepb": (-1, 1)}[pose]
    for x0, dy in ((1, swing[0]), (13, swing[1])):
        s.rect(x0, 16 + dy, x0 + 1, 20 + dy, "cl1")
        s.vline(x0, 16 + dy, 20 + dy, "cl0")
        s.rect(x0, 21 + dy, x0 + 1, 22 + dy, "sk1")


def front(pose: str) -> Hunter:
    s = Hunter(16, 32)
    legs_front(s, pose)
    arms_front(s, pose)
    # torso and belt
    s.rect(3, 16, 12, 22, "cl1")
    s.hline(3, 12, 16, "cl2")
    s.vline(3, 17, 22, "cl0")
    s.vline(12, 17, 22, "cl0")
    s.rect(7, 17, 8, 20, "white")
    s.hline(3, 12, 21, "trim")
    s.hline(3, 12, 22, "trim0")
    s.rect(7, 21, 8, 21, "white")
    # scarf
    s.rect(4, 14, 11, 15, "white")
    s.hline(4, 11, 15, "grey")
    # locs hanging at the sides, then the head
    s.rect(2, 6, 3, 12, "hair")
    s.rect(12, 6, 13, 12, "hair")
    s.px(2, 8, "hair1")
    s.px(13, 10, "hair1")
    s.rect(4, 7, 11, 13, "sk1")
    s.hline(4, 11, 13, "sk0")
    s.rect(5, 8, 6, 8, "sk2")
    s.rect(3, 3, 12, 6, "hair")
    for x in (3, 12):
        s.px(x, 3, (0, 0, 0, 0))
    s.rect(4, 7, 5, 7, "hair")
    s.rect(10, 7, 11, 7, "hair")
    s.hline(7, 8, 7, "hair")
    s.hline(5, 6, 4, "hair1")
    s.px(9, 4, "hair1")
    s.px(10, 5, "hair1")
    # face: eyes, the goatee and a mouth
    for ex in (5, 10):
        s.rect(ex, 9, ex, 10, "line")
        s.px(ex, 9, "white")
    s.px(5, 9, "white")
    s.px(5, 10, "line")
    s.px(10, 9, "white")
    s.px(10, 10, "line")
    s.rect(7, 12, 8, 13, "hair")
    s.hline(6, 6, 12, "hair")
    s.hline(9, 9, 12, "hair")
    return s.outline()


def back(pose: str) -> Hunter:
    s = Hunter(16, 32)
    legs_front(s, pose)
    arms_front(s, pose)
    s.rect(3, 15, 12, 24, "cape0")
    s.rect(4, 16, 11, 23, "cape1")
    s.vline(7, 16, 23, "cape0")
    s.vline(8, 16, 23, "cape0")
    s.hline(3, 12, 24, "trim")
    s.hline(3, 12, 15, "white")
    s.rect(3, 3, 12, 14, "hair")
    s.rect(2, 6, 13, 12, "hair")
    for x in (3, 12):
        s.px(x, 3, (0, 0, 0, 0))
    for lx in (3, 6, 9, 12):  # the locs hang over the cloak
        s.rect(lx, 14, lx + 1, 17, "hair")
        s.px(lx, 15, "hair1")
    s.hline(5, 6, 4, "hair1")
    s.px(9, 5, "hair1")
    s.px(5, 8, "hair1")
    s.px(10, 9, "hair1")
    return s.outline()


def side(pose: str) -> Hunter:
    """Facing left; the right-facing sheet row is its mirror."""
    s = Hunter(16, 32)
    step = {"stand": 0, "stepa": 1, "stepb": -1}[pose]
    # back leg then front leg (so the front one overlaps)
    for lead, shade in ((-1, "cl0"), (1, "cl1")):
        d = step * lead
        x0 = 6 - d * 2
        lift = 1 if d > 0 else 0
        s.rect(x0, 23, x0 + 3, 27 - lift, shade)
        s.rect(x0 - 1, 28 - lift, x0 + 3, 29 - lift, "boot0")
        s.hline(x0 - 1, x0 + 3, 28 - lift, "boot1")
    # torso
    s.rect(4, 16, 11, 22, "cl1")
    s.hline(4, 11, 16, "cl2")
    s.rect(10, 16, 12, 23, "cape1")
    s.vline(12, 16, 23, "cape0")
    s.hline(4, 12, 21, "trim")
    s.hline(4, 12, 22, "trim0")
    s.rect(4, 14, 11, 15, "white")
    s.hline(4, 11, 15, "grey")
    # the near arm swings
    ax = 7 + step
    s.rect(ax, 16, ax + 1, 20, "cl2")
    s.vline(ax + 1, 16, 20, "cl0")
    s.rect(ax, 21, ax + 1, 22, "sk1")
    # head: face on the left, hair and locs behind
    s.rect(4, 7, 8, 13, "sk1")
    s.hline(4, 8, 13, "sk0")
    s.px(3, 10, "sk1")      # nose
    s.px(3, 11, "sk0")
    s.rect(9, 6, 13, 13, "hair")
    s.rect(4, 3, 12, 6, "hair")
    for x in (4, 12):
        s.px(x, 3, (0, 0, 0, 0))
    s.rect(4, 7, 6, 7, "hair")
    s.rect(11, 13, 12, 17, "hair")
    s.px(11, 15, "hair1")
    s.hline(6, 8, 4, "hair1")
    s.px(10, 8, "hair1")
    s.rect(5, 9, 5, 10, "line")
    s.px(5, 9, "white")
    s.rect(4, 12, 4, 13, "hair")
    s.px(3, 12, "hair")
    return s.outline()


def build(out: Path) -> None:
    sheet = Image.new("RGBA", (16 * len(POSES), 32 * len(FACINGS)), (0, 0, 0, 0))
    for c, pose in enumerate(POSES):
        frames = {"down": front(pose), "up": back(pose), "left": side(pose)}
        frames["right"] = Hunter(16, 32)
        frames["right"].img = ImageOps.mirror(frames["left"].img)
        for r, facing in enumerate(FACINGS):
            sheet.paste(frames[facing].img, (c * 16, r * 32))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    meta = {"frame": [16, 32], "rows": FACINGS, "cols": POSES, "walk": ["stand", "stepa", "stand", "stepb"]}
    out.with_suffix(".json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", out, sheet.size)


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ide" / "home-godot" / "art" / "hunter.png")
