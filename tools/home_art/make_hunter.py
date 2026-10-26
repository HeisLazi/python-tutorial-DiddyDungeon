#!/usr/bin/env python3
"""The hunter's layered 24x40 overworld sprite, drawn pixel by pixel in code.

    python3 tools/home_art/make_hunter.py [out_dir]

One complete gothic look (a high collar, a long coat, a full cape) built as THREE
layers so the cloth can move on its own, which is what sells it:

  cape   behind the body (in front of it when he faces away); sways on its own
  body   head, locs, collar, torso, arms, legs and boots; the walk cycle
  gown   the long coat skirt, over the legs; swings against the step

Each look ("skin") is a palette plus a few switches on the same cut:
  dracula   black coat, crimson lining and sash, studded waistcoat (the default)
  alucard   black coat with gold trim, silver lining, white cravat, leather belt
  belmont   charcoal tunic, grey-green band, red tabard, crimson-lined cape

The avatar stays the player's own: umber skin, an afro and a goatee.

Output per look (rows = down, left, right, up; right is the mirror of left):
  hunter_<look>_body.png   3 columns: stand, step A, step B
  hunter_<look>_gown.png   3 columns: stand, step A, step B
  hunter_<look>_cape.png   4 columns: sway frames
  hunter.json              frame size and layer notes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from make_tiles import C, Sprite  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
W, H = 24, 40
FACINGS = ["down", "left", "right", "up"]
POSES = ["stand", "stepa", "stepb"]
SWAY = 4

BASE = {
    "sk0": (104, 62, 40), "sk1": (150, 94, 56), "sk2": (192, 128, 82),
    "hair": (24, 20, 38), "hair1": (76, 70, 116), "hair2": (46, 40, 72),
    "white": C["white"], "line": C["line"], "iris": (40, 24, 20),
    "gold": C["gold"], "gold0": C["gold0"], "gold1": C["gold1"],
    "mt0": (80, 86, 112), "mt1": (150, 158, 184), "mt2": (206, 214, 232),
    "boot0": (16, 14, 26), "boot1": (36, 34, 52), "boot2": (64, 62, 88),
}
LOOKS = {
    "dracula": {
        "k0": (14, 12, 24), "k1": (30, 28, 48), "k2": (54, 52, 82), "k3": (90, 88, 124),
        "lin0": (84, 14, 32), "lin1": (160, 30, 48), "lin2": (222, 66, 72),
        "wc0": (34, 30, 54), "wc1": (70, 64, 108),
        "sash0": (110, 20, 40), "sash1": (186, 40, 58), "trim": (150, 108, 28), "trim1": (240, 190, 60),
        "cravat": None, "tabard": False, "belt": False, "collar": 7,
    },
    "alucard": {
        "k0": (10, 10, 18), "k1": (24, 24, 38), "k2": (48, 48, 70), "k3": (96, 96, 130),
        "lin0": (130, 130, 150), "lin1": (190, 192, 208), "lin2": (236, 238, 244),
        "wc0": (30, 30, 46), "wc1": (96, 96, 128),
        "sash0": (92, 56, 34), "sash1": (146, 96, 56), "trim": (190, 120, 36), "trim1": (255, 190, 80),
        "cravat": (240, 238, 246), "tabard": False, "belt": True, "collar": 5,
    },
    "belmont": {
        "k0": (22, 24, 28), "k1": (44, 48, 52), "k2": (70, 76, 80), "k3": (110, 118, 118),
        "lin0": (100, 20, 38), "lin1": (176, 36, 54), "lin2": (232, 76, 80),
        "wc0": (44, 50, 44), "wc1": (96, 108, 90),
        "sash0": (76, 88, 72), "sash1": (134, 148, 120), "trim": (150, 108, 28), "trim1": (240, 190, 60),
        "cravat": None, "tabard": True, "belt": False, "collar": 6,
    },
}


class Layer(Sprite):
    def __init__(self, palette):
        super().__init__(W, H)
        self.p = palette

    def px(self, x, y, c):
        if isinstance(c, str):
            c = (*self.p[c], 255)
        super().px(x, y, c)

    def sym(self, x0, y0, x1, y1, c):
        """A rectangle and its mirror image."""
        self.rect(x0, y0, x1, y1, c)
        self.rect(W - 1 - x1, y0, W - 1 - x0, y1, c)

    def sympx(self, x, y, c):
        self.px(x, y, c)
        self.px(W - 1 - x, y, c)


def pal(look):
    return {**BASE, **LOOKS[look]}


def pose_vals(pose):
    return {
        "arm": {"stand": (0, 0), "stepa": (1, -1), "stepb": (-1, 1)}[pose],
        "lift": {"stand": (0, 0), "stepa": (2, 0), "stepb": (0, 2)}[pose],
        "gown": {"stand": 0, "stepa": 1, "stepb": -1}[pose],
    }


# ── Pieces shared by the front and back views ───────────────────────────────
def legs(s, pose, look):
    v = pose_vals(pose)
    for x0, up in ((8, v["lift"][0]), (12, v["lift"][1])):
        s.rect(x0, 31, x0 + 3, 34 - up, "k1")
        s.vline(x0, 31, 34 - up, "k2")
        s.rect(x0 - 1, 35 - up, x0 + 3, 38 - up, "boot1")
        s.rect(x0 - 1, 35 - up, x0 + 3, 36 - up, "mt1" if look == "alucard" else "boot2")   # folded boot cuff
        s.hline(x0 - 1, x0 + 3, 36 - up, "mt0" if look == "alucard" else "boot0")
        s.vline(x0 - 1, 37 - up, 38 - up, "boot2")
        s.rect(x0 - 1, 38 - up, x0 + 3, 38 - up, "boot0")


def arms(s, pose, look, back=False):
    v = pose_vals(pose)
    for x0, dy in ((3, v["arm"][0]), (17, v["arm"][1])):
        s.rect(x0, 16 + dy, x0 + 3, 26 + dy, "k1")
        s.vline(x0, 16 + dy, 26 + dy, "k2")
        s.vline(x0 + 3, 16 + dy, 26 + dy, "k0")
        s.rect(x0, 25 + dy, x0 + 3, 27 + dy, "trim")             # ornate cuff
        s.hline(x0, x0 + 3, 25 + dy, "trim1")
        s.px(x0 + 1, 26 + dy, "lin1"); s.px(x0 + 2, 26 + dy, "lin1")
        s.rect(x0 + 1, 28 + dy, x0 + 2, 30 + dy, "sk1")
        s.px(x0 + 1, 28 + dy, "sk2")


def shoulders(s):
    s.rect(3, 14, 20, 17, "k2")
    s.hline(3, 20, 14, "k3")
    s.hline(4, 19, 15, "k3")
    s.sympx(3, 14, (0, 0, 0, 0)); s.sympx(3, 15, "k1")



def afro(s, view):
    """A rounded afro (the avatar's hair): bold at 24x40 where locs would blur."""
    rows = {0: (9, 14), 1: (7, 16), 2: (6, 17), 3: (5, 18), 4: (5, 18)}
    for y, (x0, x1) in rows.items():
        s.hline(x0, x1, y, "hair")
    if view == "front":
        for y in range(5, 10):
            s.hline(5, 7, y, "hair"); s.hline(16, 18, y, "hair")
        s.hline(6, 7, 10, "hair"); s.hline(16, 17, 10, "hair")
        s.hline(8, 9, 5, "hair"); s.hline(14, 15, 5, "hair")          # the hairline
        s.px(11, 5, "hair"); s.px(12, 5, "hair")
    elif view == "back":
        for y in range(5, 12):
            s.hline(5 + (1 if y > 9 else 0), 18 - (1 if y > 9 else 0), y, "hair")
        s.hline(8, 15, 12, "hair")
    else:  # left profile: the mass sits up and behind the face
        for y in range(5, 12):
            s.hline(12, 19, y, "hair")
        s.hline(13, 18, 12, "hair")
        s.hline(8, 11, 5, "hair")
    # curl texture: lighter and darker flecks in a loose checker
    for y in range(0, 12):
        for x in range(4, 20):
            if s.img.getpixel((x, y))[3] and s.img.getpixel((x, y))[:3] == tuple(s.p["hair"]):
                if (x + 2 * y) % 5 == 0:
                    s.px(x, y, "hair1")
                elif (x + y) % 4 == 0 and y > 1:
                    s.px(x, y, "hair2")


# ── Facing down (front) ─────────────────────────────────────────────────────
def front_body(look, pose):
    p = pal(look)
    s = Layer(p)
    legs(s, pose, look)
    arms(s, pose, look)
    shoulders(s)
    # coat fronts and the waistcoat, with its stud column
    s.rect(7, 15, 16, 26, "k1")
    s.sym(7, 15, 9, 27, "k2")
    s.vline(9, 17, 27, "lin1"); s.vline(14, 17, 27, "lin1")
    s.rect(10, 15, 13, 27, "wc0")
    for y in (17, 19, 21, 23):
        s.sympx(11, y, "wc1")
        s.px(11, y + 1, "mt1"); s.px(12, y + 1, "mt1")
    s.vline(11, 16, 26, "wc1"); s.vline(12, 16, 26, "wc1")
    if p["trim"]:                                                 # gold coat-edge piping
        s.vline(8, 16, 27, "trim"); s.vline(15, 16, 27, "trim")
    # sash or leather belt, and the tabard front
    if p["belt"]:
        s.rect(7, 25, 16, 26, "sash0"); s.hline(7, 16, 25, "sash1")
        s.rect(11, 25, 12, 26, "gold")
    else:
        s.rect(7, 24, 16, 26, "sash0"); s.hline(7, 16, 24, "sash1"); s.hline(7, 16, 26, "lin0")
        s.rect(15, 25, 16, 27, "sash1")
    # neck, the crimson inner collar and the tall flared collar wings
    s.rect(10, 12, 13, 13, "sk0")
    s.rect(8, 13, 15, 14, "lin1" if not p["cravat"] else "sash0")
    if p["cravat"]:
        s.rect(10, 13, 13, 17, "cravat"); s.hline(10, 13, 15, "mt2"); s.px(11, 16, "mt1")
    ch = p["collar"]
    for side in (0, 1):
        def X(x):
            return x if side == 0 else W - 1 - x
        for y in range(8 + (7 - ch), 17):
            half = 1 + min(4, (y - (8 + (7 - ch))) // 2)
            for x in range(8 - half, 8):
                s.px(X(x), y, "k2")
        s.vline(X(7), 9 + (7 - ch), 15, "k0")
        s.px(X(6), 8 + (7 - ch), "lin2")
        s.vline(X(4), 11 + (7 - ch), 16, "k3")
    # the face: parted fringe, brows, eyes, nose, moustache, goatee
    s.rect(8, 5, 15, 11, "sk1")
    s.rect(8, 7, 9, 10, "sk1"); s.vline(8, 8, 10, "sk0")
    s.rect(13, 7, 15, 10, "sk2")
    s.hline(8, 15, 12, "sk0")
    s.hline(9, 10, 6, "hair"); s.hline(13, 14, 6, "hair")
    s.px(9, 7, "white"); s.px(10, 7, "iris"); s.px(13, 7, "iris"); s.px(14, 7, "white")
    s.px(11, 8, "sk0"); s.px(12, 8, "sk2"); s.px(11, 9, "sk0")
    s.rect(11, 11, 12, 12, "hair")                                   # a small goatee
    afro(s, "front")
    return s.outline()


def front_gown(look, pose):
    p = pal(look)
    s = Layer(p)
    g = pose_vals(pose)["gown"]
    # the coat skirt: a trapezoid with a centre slit that shows the lining
    for y in range(27, 38):
        flare = (y - 27) // 3
        x0 = 7 - flare + (g if y > 33 else 0)
        x1 = W - 1 - 7 + flare + (g if y > 33 else 0)
        s.hline(x0, x1, y, "k1")
        s.px(x0, y, "k3"); s.px(x1, y, "k0")
    for y in range(30, 38):
        s.hline(11, 12, y, "lin0")
        s.px(10, y, "lin1"); s.px(13, y, "lin1")
    if p["trim"]:
        for y in range(27, 38):
            s.px(10, y, "trim") if y < 30 else None
    # a pointed, studded hem
    for x in range(5 + g, 19 + g, 2):
        s.px(x, 38, "k1")
        s.px(x, 37, "k2")
    for x in (7, 16):
        s.px(x + g, 36, "mt1")
    if p["tabard"]:
        s.rect(9, 27, 14, 33, "lin1"); s.hline(9, 14, 28, "lin2"); s.hline(9, 14, 27, "lin0")
        for x, y in ((9, 34), (11, 35), (13, 34)):
            s.px(x + g, y, "lin1")
        s.rect(11, 30, 12, 31, "lin0")
    return s.outline()


def front_cape(look, phase):
    p = pal(look)
    s = Layer(p)
    sway = [0, 1, 0, -1][phase % 4]
    sway2 = [0, -1, 0, 1][phase % 4]
    # the long cape behind: black outside edges, crimson lining showing, ragged hem
    for y in range(13, 38):
        spread = 3 + (y - 13) // 5
        x0 = 3 - (y - 13) // 7 + (sway if y > 28 else 0)
        x1 = W - 1 - 3 + (y - 13) // 7 + (sway2 if y > 28 else 0)
        s.hline(x0, x1, y, "k1")
        s.px(x0, y, "k2"); s.px(x1, y, "k0")
        inner = min(x0 + 2, 11)
        for x in range(inner, 11):
            s.px(x, y, "lin0" if y < 22 else "lin1")
            s.px(W - 1 - x, y, "lin0" if y < 22 else "lin1")
    for x in range(1, 23, 2):
        s.px(x + sway, 38, "lin1"); s.px(x, 38 + 0, "lin1")
    s.hline(2, 21, 37, "lin1")
    s.px(5, 36, "lin2"); s.px(18, 36, "lin2"); s.px(8, 35, "lin2"); s.px(15, 35, "lin2")
    return s.outline()


# ── Facing up (back) ────────────────────────────────────────────────────────
def back_body(look, pose):
    p = pal(look)
    s = Layer(p)
    legs(s, pose, look)
    arms(s, pose, look, back=True)
    shoulders(s)
    s.rect(7, 15, 16, 26, "k1")
    # tall collar wings seen from behind, and the hair swept up
    ch = p["collar"]
    s.rect(4, 8 + (7 - ch), 19, 14, "k2")
    s.hline(4, 19, 8 + (7 - ch), "k3")
    s.rect(7, 12, 16, 15, "k1")
    afro(s, "back")
    return s.outline()


def back_gown(look, pose):
    p = pal(look)
    s = Layer(p)
    g = pose_vals(pose)["gown"]
    for y in range(26, 38):
        flare = (y - 26) // 3
        x0 = 7 - flare + (g if y > 33 else 0)
        x1 = W - 1 - 7 + flare + (g if y > 33 else 0)
        s.hline(x0, x1, y, "k1")
        s.px(x0, y, "k3"); s.px(x1, y, "k0")
    s.vline(11, 28, 37, "k0"); s.vline(12, 28, 37, "k0")
    s.rect(7, 25, 16, 26, "sash0"); s.hline(7, 16, 25, "sash1")
    if not p["belt"]:
        s.rect(10, 26, 13, 29, "sash1"); s.px(11, 29, "sash0"); s.px(12, 29, "sash0")   # the sash tails
    return s.outline()


def back_cape(look, phase):
    """Seen from behind the cape is in front of the body and hides almost all of it."""
    p = pal(look)
    s = Layer(p)
    sway = [0, 1, 0, -1][phase % 4]
    sway2 = [0, -1, 0, 1][phase % 4]
    for y in range(14, 38):
        x0 = 3 - (y - 14) // 7 + (sway if y > 28 else 0)
        x1 = W - 1 - 3 + (y - 14) // 7 + (sway2 if y > 28 else 0)
        s.hline(x0, x1, y, "k1")
        s.px(x0, y, "k2"); s.px(x1, y, "k0")
        if y % 6 == 0:
            s.px(x0 + 3, y, "k2"); s.px(x1 - 3, y, "k0")
    s.vline(11, 16, 37, "k0"); s.vline(12, 16, 37, "k0")
    s.hline(3, 20, 14, "k3")
    # the lining flashing out at the hem
    s.hline(2 + sway, 21 + sway2, 36, "lin0")
    for x in range(2, 22, 2):
        s.px(x, 37, "lin1")
    s.hline(3 + sway, 20 + sway2, 37, "lin1")
    for x in range(3, 21, 3):
        s.px(x, 36, "lin2")
    return s.outline()


# ── Facing left (profile); the right-facing rows are mirrors ────────────────
def side_body(look, pose):
    p = pal(look)
    s = Layer(p)
    step = {"stand": 0, "stepa": 1, "stepb": -1}[pose]
    for lead, tone in ((-1, "boot0"), (1, "boot1")):
        d = step * lead
        x0 = 9 - d * 3
        lift = 1 if d > 0 else 0
        s.rect(x0, 31, x0 + 3, 34 - lift, "k1")
        s.rect(x0 - 2, 35 - lift, x0 + 3, 38 - lift, tone)
        s.rect(x0 - 2, 35 - lift, x0 + 3, 36 - lift, "mt1" if look == "alucard" else "boot2")
        s.hline(x0 - 2, x0 + 3, 36 - lift, "boot0")
        s.rect(x0 - 3, 37 - lift, x0 - 2, 38 - lift, "boot2")                           # the toe
    # torso, waistcoat edge and the swinging near arm
    s.rect(7, 15, 15, 26, "k1")
    s.vline(7, 16, 26, "k2"); s.vline(15, 16, 26, "k0")
    s.rect(7, 16, 8, 26, "wc0")
    for y in (18, 21, 24):
        s.px(7, y, "wc1")
    s.rect(7, 24, 15, 26, "sash0" if not p["belt"] else "sash0"); s.hline(7, 15, 24, "sash1")
    s.rect(6, 14, 16, 17, "k2"); s.hline(6, 16, 14, "k3")
    ax = 9 + step * 2
    s.rect(ax, 16, ax + 3, 26, "k1"); s.vline(ax, 16, 26, "k2"); s.vline(ax + 3, 16, 26, "k0")
    s.rect(ax, 25, ax + 3, 27, "trim"); s.hline(ax, ax + 3, 25, "trim1")
    s.rect(ax + 1, 28, ax + 2, 30, "sk1")
    # the collar wing behind the head, the crimson inside, then the head in profile
    ch = p["collar"]
    s.rect(11, 9 + (7 - ch), 15, 16, "k2"); s.vline(11, 10 + (7 - ch), 16, "lin1" if not p["cravat"] else "k3")
    s.hline(11, 15, 9 + (7 - ch), "k3")
    s.rect(7, 13, 11, 14, "lin1" if not p["cravat"] else "cravat")
    s.rect(8, 5, 12, 11, "sk1"); s.hline(8, 12, 12, "sk0"); s.rect(10, 12, 11, 13, "sk0")
    s.px(7, 8, "sk1"); s.px(7, 9, "sk0")                                              # the nose
    afro(s, "side")
    s.hline(8, 10, 6, "hair"); s.px(9, 7, "iris"); s.px(10, 7, "white")
    s.rect(8, 11, 9, 12, "hair")                                    # a small goatee
    return s.outline()


def side_gown(look, pose):
    p = pal(look)
    s = Layer(p)
    g = {"stand": 0, "stepa": 2, "stepb": -2}[pose]
    for y in range(27, 38):
        flare = (y - 27) // 4
        x0 = 6 - flare - (g if y > 32 else 0)
        x1 = 15 + flare + (g // 2 if y > 32 else 0)
        s.hline(x0, x1, y, "k1")
        s.px(x0, y, "k3"); s.px(x1, y, "k0")
    for y in range(31, 38):
        s.px(9, y, "lin0"); s.px(10, y, "lin1")
    for x in range(5 - g, 17 + g // 2, 2):
        s.px(x, 38, "k1")
    if p["tabard"]:
        s.rect(6, 27, 10, 33, "lin1"); s.hline(6, 10, 28, "lin2")
        for x, y in ((6, 34), (8, 35), (10, 34)):
            s.px(x - g, y, "lin1")
    return s.outline()


def side_cape(look, phase):
    """The cape streams out behind him and rolls with the phase."""
    p = pal(look)
    s = Layer(p)
    roll = [0, 1, 2, 1][phase % 4]
    for y in range(14, 38):
        reach = 3 + min(9, (y - 14) // 2) + (roll if y > 24 else 0)
        x0 = 13
        x1 = min(W - 1, 14 + reach)
        s.hline(x0, x1, y, "k1")
        s.px(x1, y, "k0")
        if y > 20:
            s.hline(x0, min(x0 + 3, x1), y, "lin0")
            s.px(x0 + 4 if x0 + 4 <= x1 else x1, y, "lin1")
    s.hline(13, 17, 14, "k3")
    s.hline(13, min(W - 1, 22 + roll), 37, "lin1")
    for x in range(14, min(W - 1, 22 + roll), 2):
        s.px(x, 38, "lin1")
    s.vline(13, 15, 36, "k2")
    return s.outline()


def build_look(look, out_dir):
    body = Image.new("RGBA", (W * len(POSES), H * len(FACINGS)), (0, 0, 0, 0))
    gown = Image.new("RGBA", (W * len(POSES), H * len(FACINGS)), (0, 0, 0, 0))
    cape = Image.new("RGBA", (W * SWAY, H * len(FACINGS)), (0, 0, 0, 0))
    maker = {"down": (front_body, front_gown, front_cape), "up": (back_body, back_gown, back_cape), "left": (side_body, side_gown, side_cape)}
    for r, facing in enumerate(FACINGS):
        src = maker["left" if facing == "right" else facing]
        for c, pose in enumerate(POSES):
            for sheet, fn in ((body, src[0]), (gown, src[1])):
                img = fn(look, pose).img
                if facing == "right":
                    img = ImageOps.mirror(img)
                sheet.paste(img, (c * W, r * H))
        for c in range(SWAY):
            img = src[2](look, c).img
            if facing == "right":
                img = ImageOps.mirror(img)
            cape.paste(img, (c * W, r * H))
    out_dir.mkdir(parents=True, exist_ok=True)
    body.save(out_dir / f"hunter_{look}_body.png")
    gown.save(out_dir / f"hunter_{look}_gown.png")
    cape.save(out_dir / f"hunter_{look}_cape.png")


def build_all(out_dir):
    for look in LOOKS:
        build_look(look, out_dir)
    meta = {
        "frame": [W, H], "rows": FACINGS, "body_cols": POSES, "gown_cols": POSES, "cape_cols": SWAY,
        "looks": list(LOOKS), "layers": "cape behind body (in front when facing up); gown over the legs",
    }
    (out_dir / "hunter.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", len(LOOKS), "looks to", out_dir)


def preview(out_dir, path, look="dracula", scale=8):
    """A contact sheet: every facing and pose, layers composited (cape under, or over when facing up)."""
    body = Image.open(out_dir / f"hunter_{look}_body.png")
    gown = Image.open(out_dir / f"hunter_{look}_gown.png")
    cape = Image.open(out_dir / f"hunter_{look}_cape.png")
    sheet = Image.new("RGBA", (W * 3, H * 4), (54, 52, 82, 255))
    for r, facing in enumerate(FACINGS):
        for c in range(3):
            box = (c * W, r * H, (c + 1) * W, (r + 1) * H)
            cell = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            cp = cape.crop((c * W, r * H, (c + 1) * W, (r + 1) * H))
            if facing != "up":
                cell.alpha_composite(cp)
            cell.alpha_composite(body.crop(box))
            cell.alpha_composite(gown.crop(box))
            if facing == "up":
                cell.alpha_composite(cp)
            sheet.alpha_composite(cell, (c * W, r * H))
    sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST).save(path)


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ide" / "home-godot" / "art"
    build_all(target)
