#!/usr/bin/env python3
"""The hunter's 16x32 overworld sprite sheet: a vampire hunter, drawn in code.

    python3 tools/home_art/make_hunter.py [out.png]

A 3D render shrunk to 16x32 turns to mush, so the walking sprite is hand-placed
pixel art (like FireRed's own); Blender stays for the big pieces (portraits,
props, turnarounds; see hunter_blender.py).

The look follows the Castlevania hunters (Trevor Belmont): a black high-collared
cloak lined crimson, a dark armoured tunic with a grey-green belt band, a torn
red tabard, gold-and-steel bracers, a sword scabbard, a chain whip and black
boots. The player's own avatar stays: umber skin, locs and a goatee.

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
    "sk0": (104, 62, 40), "sk1": (150, 94, 56), "sk2": (192, 128, 82),
    "hair": (26, 22, 42), "hair1": (84, 78, 124),
    "ch0": (30, 28, 46), "ch1": (66, 64, 94), "ch2": (98, 96, 134), "ch3": (140, 138, 176),
    "red0": (112, 22, 42), "red": (196, 44, 60), "red1": (250, 96, 96),
    "gv0": (70, 80, 70), "gv1": (112, 124, 104), "gv2": (156, 168, 140),
    "gold": C["gold"], "gold0": C["gold0"], "gold1": C["gold1"],
    "steel": (176, 188, 210), "steel0": (104, 114, 140),
    "tr": (62, 72, 66), "tr1": (92, 104, 92),
    "boot0": (20, 18, 32), "boot1": (58, 54, 80), "boot2": (110, 104, 140),
    "white": C["white"], "line": C["line"], "iris": (40, 24, 20),
}
FACINGS = ["down", "left", "right", "up"]
POSES = ["stand", "stepa", "stepb"]


class Hunter(Sprite):
    def px(self, x, y, c):
        super().px(x, y, (*P[c], 255) if isinstance(c, str) else c)


def boots(s, pose, spread=0):
    """Black tall boots under dark trousers; one foot lifts on a step."""
    lift = {"stand": (0, 0), "stepa": (2, 0), "stepb": (0, 2)}[pose]
    for x0, up in ((5 - spread, lift[0]), (8 + spread, lift[1])):
        s.rect(x0, 25 - up, x0 + 2, 27 - up, "tr")
        s.vline(x0, 25 - up, 27 - up, "tr1")
        s.rect(x0 - 1, 28 - up, x0 + 2, 30 - up, "boot1")
        s.rect(x0 - 1, 29 - up, x0 + 2, 30 - up, "boot0")
        s.hline(x0 - 1, x0 + 2, 28 - up, "boot2")                    # the boot cuff
        s.vline(x0 - 1, 29 - up, 30 - up, "boot2")
        s.px(x0 + 1, 28 - up, "gold0")


def hair_front(s):
    """Messy swept-back hair with tufts, and locs falling at the sides."""
    s.rect(4, 2, 11, 2, "hair")
    s.px(5, 1, "hair"); s.px(8, 1, "hair"); s.px(10, 1, "hair"); s.px(7, 0, "hair")
    s.rect(3, 3, 12, 5, "hair")
    s.hline(5, 6, 3, "hair1"); s.px(9, 4, "hair1"); s.px(4, 4, "hair1")
    s.rect(4, 6, 5, 6, "hair"); s.rect(10, 6, 11, 6, "hair"); s.hline(7, 8, 6, "hair")
    s.rect(3, 6, 3, 8, "hair"); s.rect(12, 6, 12, 8, "hair")
    for lx, ln in ((2, 3), (13, 3)):
        s.rect(lx, 5, lx, 5 + ln, "hair")
    s.px(2, 7, "hair1"); s.px(13, 7, "hair1")


def face_front(s):
    s.rect(4, 6, 11, 12, "sk1")
    s.rect(4, 7, 5, 11, "sk1"); s.px(4, 9, "sk0"); s.px(4, 10, "sk0")
    s.rect(9, 8, 11, 10, "sk2")
    s.hline(4, 11, 12, "sk0")
    hair_front(s)
    s.hline(5, 6, 7, "hair"); s.hline(9, 10, 7, "hair")             # brows
    s.px(5, 8, "white"); s.px(6, 8, "iris"); s.px(9, 8, "iris"); s.px(10, 8, "white")
    s.px(5, 9, "sk0"); s.px(10, 9, "sk0"); s.px(7, 9, "sk0"); s.px(8, 9, "sk2")
    s.rect(7, 11, 8, 12, "hair")                                    # the goatee


def cloak_collar(s):
    """The tall black collar wings, lined crimson, either side of the face."""
    for x0, x1, inner in ((2, 3, 3), (12, 13, 12)):
        s.rect(x0, 9, x1, 14, "ch2")
        s.vline(x0, 9, 14, "ch3")
        s.px(x0, 14, "ch1")
    s.hline(2, 13, 14, "ch1")


def front(pose, sway=0):
    s = Hunter(16, 32)
    boots(s, pose)
    # the cloak: heavy black drapes at both sides with crimson lining, ragged hem
    for x0, x1 in ((1, 4), (11, 14)):
        s.rect(x0, 15, x1, 24, "ch1")
        s.vline(x0, 15, 24, "ch2")
        s.vline(x1, 15, 24, "ch0")
    s.vline(4, 16, 24, "red0"); s.vline(11, 16, 24, "red0")
    s.vline(5, 17, 23, "red"); s.vline(10, 17, 23, "red")
    s.hline(1, 14, 15, "ch3")
    s.hline(1, 14, 14, "ch2")
    for x in (1, 3, 12, 14):                                        # ragged hem
        s.px(x, 25 + (sway if x < 8 else -sway), "ch1")
    # the dark tunic with plate lines, then the grey-green belt band
    s.rect(5, 15, 10, 22, "ch1")
    s.vline(7, 16, 19, "ch0"); s.vline(8, 16, 19, "ch0")
    s.hline(5, 10, 16, "ch2")
    s.rect(4, 19, 11, 20, "gv1"); s.hline(4, 11, 19, "gv2"); s.hline(4, 11, 20, "gv0")
    s.rect(8, 19, 8, 20, "gold")
    # the torn red tabard
    s.rect(5, 21, 10, 23, "red")
    s.hline(5, 10, 22, "red1")
    s.hline(5, 10, 21, "red0")
    for x, y in ((5, 24), (7, 25), (9, 24), (10, 25)):
        s.px(x, y, "red")
    s.px(6, 24, "red0"); s.px(8, 24, "red0")
    # a sword on the hip, hilt peeking over the belt
    s.vline(11, 21, 24, "ch0"); s.px(11, 24, "gold")
    s.px(12, 19, "gold1"); s.px(13, 19, "gold")
    # arms: bracers of grey-green and gold, bare hands; the chain whip hangs from one
    for x0 in (1, 13):
        s.rect(x0, 17, x0 + 1, 18, "ch2")
        s.rect(x0, 19, x0 + 1, 21, "gv1"); s.hline(x0, x0 + 1, 19, "gold")
        s.rect(x0, 22, x0 + 1, 23, "sk1")
    for i, y in enumerate(range(24, 29)):
        s.px(14 if i % 2 == 0 else 15, y, "steel")
    s.px(14, 23, "gold1")
    # the neck, the collar and the face
    s.rect(6, 13, 9, 13, "sk0")
    face_front(s)
    cloak_collar(s)
    s.rect(6, 14, 9, 14, "red")                                     # the red knot at the throat
    s.px(7, 14, "red1")
    return s.outline()


def back(pose, sway=0):
    s = Hunter(16, 32)
    boots(s, pose)
    # a long cloak covering the back, flaring at the hem with its crimson lining showing
    s.rect(1, 12, 14, 23, "ch1")
    s.hline(2, 13, 12, "ch3"); s.hline(1, 14, 13, "ch2")
    s.vline(1, 13, 23, "ch2"); s.vline(14, 13, 23, "ch0")
    s.vline(7, 14, 23, "ch0"); s.vline(8, 14, 23, "ch0")           # the back seam
    s.vline(4, 14, 23, "ch2"); s.vline(11, 14, 23, "ch2")
    s.hline(2, 13, 14, "ch3"); s.px(5, 18, "ch3"); s.px(10, 20, "ch3")
    s.rect(0, 24, 15, 24, "ch2")
    s.rect(0, 25, 15, 25, "ch1")
    s.hline(0, 15, 26, "red0")
    for x in range(1, 15, 2):
        s.px(x, 26 + (sway if x < 8 else -sway), "red")
    for x in (3, 7, 11):
        s.px(x, 25, "red0")
    s.rect(1, 13, 2, 14, "red"); s.rect(13, 13, 14, 14, "red")    # collar lining at the ends
    # locs and swept hair over the collar
    s.rect(4, 2, 11, 2, "hair")
    s.px(5, 1, "hair"); s.px(8, 1, "hair"); s.px(10, 1, "hair"); s.px(7, 0, "hair")
    s.rect(3, 3, 12, 11, "hair")
    s.rect(2, 5, 13, 10, "hair")
    for lx, ln in ((3, 9), (5, 11), (7, 8), (9, 11), (11, 8), (12, 9)):
        s.rect(lx, 6, lx, 6 + ln, "hair")
    s.hline(5, 6, 3, "hair1"); s.px(9, 4, "hair1"); s.px(4, 7, "hair1"); s.px(10, 8, "hair1")
    s.px(5, 12, "hair1"); s.px(9, 13, "hair1")
    s.rect(6, 12, 9, 13, "red")                                     # the knot
    s.px(7, 12, "red1")
    return s.outline()


def side(pose, sway=0):
    """Facing left: the cloak streams out behind him; the red tabard hangs in front."""
    s = Hunter(16, 32)
    step = {"stand": 0, "stepa": 1, "stepb": -1}[pose]
    for lead, tone in ((-1, "boot0"), (1, "boot1")):
        d = step * lead
        x0 = 6 - d * 2
        lift = 1 if d > 0 else 0
        s.rect(x0, 25 - lift, x0 + 2, 27 - lift, "tr")
        s.rect(x0 - 1, 28 - lift, x0 + 2, 30 - lift, tone)
        s.hline(x0 - 1, x0 + 2, 28 - lift, "boot2")
        s.px(x0 - 1, 29 - lift, "boot2")
    # the cloak billowing behind: a wedge with a crimson underside
    s.rect(9, 13, 13, 24, "ch1")
    s.rect(11, 15, 14, 25, "ch1")
    s.vline(13, 14, 24, "ch0"); s.vline(14, 16, 25, "ch0")
    s.rect(9, 14, 10, 24, "red0"); s.vline(9, 15, 24, "red")
    s.hline(9, 14, 13, "ch3")
    for x, y in ((10, 24), (12, 26), (14, 26)):
        s.px(x, y + sway, "red")
    s.px(11, 25, "red0")
    # the tunic, belt band, tabard and sword
    s.rect(4, 14, 10, 20, "ch1")
    s.hline(4, 10, 14, "ch2"); s.vline(4, 15, 20, "ch2")
    s.rect(4, 19, 10, 20, "gv1"); s.hline(4, 10, 19, "gv2"); s.hline(4, 10, 20, "gv0")
    s.rect(3, 21, 8, 23, "red"); s.hline(3, 8, 21, "red0"); s.hline(3, 8, 22, "red1")
    for x, y in ((3, 24), (5, 25), (7, 24)):
        s.px(x, y, "red")
    s.px(5, 24, "red0")
    s.vline(9, 19, 24, "ch0"); s.px(9, 24, "gold"); s.px(9, 18, "gold1")
    # the near arm: bracer and hand, swinging; the chain whip hangs from it
    ax = 6 + step
    s.rect(ax, 15, ax + 1, 18, "ch2")
    s.rect(ax, 19, ax + 1, 21, "gv1"); s.hline(ax, ax + 1, 19, "gold")
    s.rect(ax, 22, ax + 1, 23, "sk1")
    for i, y in enumerate(range(24, 29)):
        s.px(ax + (i % 2), y, "steel")
    # the head in profile with a tall collar behind it
    s.rect(4, 6, 8, 12, "sk1"); s.hline(4, 8, 12, "sk0")
    s.px(3, 9, "sk1"); s.px(3, 10, "sk0")
    s.rect(9, 9, 12, 14, "ch2"); s.vline(9, 10, 14, "red"); s.px(9, 9, "red1")
    s.rect(9, 5, 12, 8, "hair")
    s.rect(4, 3, 12, 5, "hair"); s.rect(4, 2, 11, 2, "hair")
    s.px(5, 1, "hair"); s.px(8, 1, "hair"); s.px(10, 1, "hair"); s.px(7, 0, "hair")
    s.rect(4, 6, 6, 6, "hair")
    s.rect(11, 6, 11, 12, "hair"); s.px(12, 8, "hair1"); s.hline(6, 8, 3, "hair1")
    s.hline(5, 6, 7, "hair")
    s.px(5, 8, "iris"); s.px(6, 8, "white")
    s.rect(4, 12, 4, 13, "hair"); s.px(5, 13, "hair")              # the goatee
    s.rect(5, 13, 8, 14, "red"); s.px(6, 13, "red1")               # the knot at the throat
    return s.outline()


def build(out):
    sheet = Image.new("RGBA", (16 * len(POSES), 32 * len(FACINGS)), (0, 0, 0, 0))
    for c, pose in enumerate(POSES):
        sway = {"stand": 0, "stepa": 1, "stepb": -1}[pose]
        frames = {"down": front(pose, sway), "up": back(pose, sway), "left": side(pose, sway)}
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
