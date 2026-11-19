#!/usr/bin/env python3
"""Generate the Home hall tileset and objects: a gothic castle hall (Castlevania
meets GBA Pokemon), in the app's dark indigo palette with crimson and gold.

Writes ide/home-godot/art/tiles.png (an atlas), tiles.json and tiles_data.gd
(name -> region) so the Godot scene can place any piece by name. Everything is
drawn in code with a fixed palette, a 1px dark outline and flat 3-4 tone
shading; re-run this script to regenerate. Animated pieces are separate
regions (flame_0, flame_1, ...).

Run with the system Python (it has Pillow):  python3 tools/home_art/make_tiles.py
"""

from __future__ import annotations

import sys
import json
import random
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ide" / "home-godot" / "art"

C = {
    "line": (16, 12, 28),
    # cool castle stone
    "st0": (30, 28, 50), "st1": (46, 44, 74), "st2": (66, 64, 100), "st3": (92, 90, 130), "st4": (122, 120, 160),
    # polished dark marble floor
    "m0": (22, 20, 38), "m1": (36, 34, 58), "m2": (54, 52, 82), "m3": (78, 76, 112),
    # crimson carpet and banners
    "red0": (92, 20, 38), "red": (150, 32, 52), "red1": (200, 56, 66), "red2": (236, 110, 102),
    # gold and ember
    "gold0": (150, 108, 28), "gold": (240, 190, 60), "gold1": (255, 232, 140),
    "ember0": (214, 70, 30), "ember": (255, 122, 42), "ember1": (255, 209, 102),
    # dark wood and iron
    "wd0": (44, 28, 24), "wd1": (80, 50, 38), "wd2": (122, 78, 52), "wd3": (166, 112, 72),
    "mt0": (60, 64, 88), "mt1": (122, 130, 158), "mt2": (190, 198, 222),
    # parchment, glass, plants, wax
    "par0": (190, 168, 112), "par1": (226, 210, 160), "par2": (246, 238, 206),
    "gl0": (36, 54, 120), "gl1": (64, 96, 186), "gl2": (120, 160, 232), "gp0": (84, 52, 140), "gp1": (130, 92, 200),
    "gr0": (34, 90, 56), "gr1": (60, 132, 80),
    "wax": (236, 228, 204), "white": (242, 239, 230), "moon": (140, 170, 230),
}


def rgba(name, alpha=255):
    r, g, b = C[name]
    return (r, g, b, alpha)


class Sprite:
    def __init__(self, w, h):
        self.img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        self.w, self.h = w, h

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.img.putpixel((x, y), rgba(c) if isinstance(c, str) else c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px(x, y, c)

    def hline(self, x0, x1, y, c):
        self.rect(x0, y, x1, y, c)

    def vline(self, x, y0, y1, c):
        self.rect(x, y0, x, y1, c)

    def disc(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r + r // 2:
                    self.px(x, y, c)

    def outline(self, color="line"):
        out = self.img.copy()
        src, dst = self.img.load(), out.load()
        for y in range(self.h):
            for x in range(self.w):
                if src[x, y][3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.w and 0 <= ny < self.h and src[nx, ny][3]:
                        dst[x, y] = rgba(color)
                        break
        self.img = out
        return self


def noise(seed):
    return random.Random(seed)


# ── Floor, carpet and walls (tileable) ───────────────────────────────────────
def floor_tile(variant):
    """Polished dark marble in a checker, each cell bevelled."""
    s = Sprite(16, 16)
    rng = noise(300 + variant)
    for cy in (0, 1):
        for cx in (0, 1):
            light = (cx + cy) % 2 == 0
            x0, y0 = cx * 8, cy * 8
            s.rect(x0, y0, x0 + 7, y0 + 7, "m2" if light else "m1")
            s.hline(x0, x0 + 7, y0, "m3" if light else "m2")        # lit top edge
            s.vline(x0, y0, y0 + 7, "m3" if light else "m2")        # lit left edge
            s.hline(x0, x0 + 7, y0 + 7, "m0")                       # shade bottom
            s.vline(x0 + 7, y0, y0 + 7, "m0")
    for _ in range(4 + variant * 3):                                # veins and flecks
        x, y = rng.randrange(16), rng.randrange(16)
        s.px(x, y, "m3" if rng.random() < 0.5 else "m0")
    if variant:
        for i in range(4):
            s.px(10 + i, 3 + i, "m3")
    return s


def carpet_tile():
    """A 2-tile-wide crimson runner (32x16) that tiles vertically."""
    s = Sprite(32, 16)
    s.rect(0, 0, 31, 15, "red")
    s.rect(0, 0, 1, 15, "gold0")
    s.rect(30, 0, 31, 15, "gold0")
    s.vline(2, 0, 15, "gold")
    s.vline(29, 0, 15, "gold")
    s.rect(3, 0, 4, 15, "red0")
    s.rect(27, 0, 28, 15, "red0")
    cx = 16
    s.px(cx - 1, 7, "gold"); s.px(cx, 7, "gold")
    s.px(cx - 2, 8, "gold0"); s.px(cx - 1, 8, "gold1"); s.px(cx, 8, "gold1"); s.px(cx + 1, 8, "gold0")
    s.px(cx - 1, 9, "gold"); s.px(cx, 9, "gold")
    s.px(cx - 1, 6, "red1"); s.px(cx, 6, "red1"); s.px(cx - 1, 10, "red1"); s.px(cx, 10, "red1")
    for x in range(6, 26, 4):
        s.px(x, 2, "red1")
        s.px(x + 2, 13, "red1")
    return s


def wall_face_tile(variant):
    """Large cool stone blocks (16x8 courses, offset)."""
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "st1")
    rng = noise(400 + variant)
    for row in range(2):
        y = row * 8
        off = 0 if (row + variant) % 2 == 0 else 8
        s.hline(0, 15, y + 7, "st0")
        s.hline(0, 15, y, "st2")
        for x in (off % 16, (off + 8) % 16):
            s.vline(x, y, y + 6, "st0")
            if x + 1 < 16:
                s.vline(x + 1, y + 1, y + 5, "st2")
        for _ in range(5):
            s.px(rng.randrange(16), y + 1 + rng.randrange(5), "st3" if rng.random() < 0.4 else "st0")
    return s


def wall_top_tile():
    """The top cornice: a dark band with a lit lip."""
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "st0")
    s.hline(0, 15, 9, "st1")
    s.hline(0, 15, 10, "st2")
    s.rect(0, 11, 15, 12, "st3")
    s.hline(0, 15, 13, "st1")
    s.hline(0, 15, 14, "st0")
    for x in range(1, 16, 4):                                       # corbels
        s.rect(x, 5, x + 1, 9, "st1")
        s.px(x, 5, "st2")
    return s


def plinth_tile():
    """The stone plinth where the wall meets the marble."""
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "st2")
    s.hline(0, 15, 0, "st4")
    s.hline(0, 15, 1, "st3")
    s.rect(0, 2, 15, 6, "st2")
    s.hline(0, 15, 7, "st1")
    s.hline(0, 15, 8, "st0")
    s.rect(0, 9, 15, 15, "m0")                                      # its shadow on the floor
    s.hline(0, 15, 9, "m1")
    for x in (4, 12):
        s.vline(x, 2, 6, "st1")
    return s


# ── Objects ──────────────────────────────────────────────────────────────────
def window_arch():
    """A tall pointed-arch stained-glass window (16x32) with moonlight."""
    s = Sprite(16, 32)
    s.rect(1, 3, 14, 31, "st3")
    for y, x in ((2, 5), (1, 7)):
        s.rect(x, y, 15 - x, y, "st3")
    s.rect(3, 6, 12, 29, "gl0")
    s.rect(4, 5, 11, 5, "gl0")
    s.rect(6, 4, 9, 4, "gl0")
    s.rect(4, 8, 11, 28, "gl1")
    s.rect(5, 6, 10, 7, "gl1")
    s.rect(6, 5, 9, 5, "gl1")
    s.rect(5, 9, 10, 14, "gp0")                                     # stained glass panes
    s.rect(6, 10, 9, 13, "gp1")
    s.rect(5, 17, 10, 22, "red0")
    s.rect(6, 18, 9, 21, "red")
    s.px(7, 11, "gold1"); s.px(8, 19, "gold")
    s.vline(7, 5, 29, "st1")                                        # mullions and tracery
    s.vline(8, 5, 29, "st1")
    s.hline(4, 11, 15, "st1")
    s.hline(4, 11, 16, "st1")
    s.hline(4, 11, 24, "st1")
    s.px(5, 7, "gl2"); s.px(5, 8, "gl2"); s.px(10, 26, "gl2"); s.px(10, 27, "gl2")
    s.rect(1, 29, 14, 31, "st2")                                    # sill
    s.hline(1, 14, 29, "st4")
    return s.outline()


def banner():
    """A crimson banner on a pole (16x32) with a gold flame crest."""
    s = Sprite(16, 32)
    s.rect(1, 1, 14, 1, "gold0")
    s.hline(1, 14, 2, "gold")
    s.px(1, 1, "gold1"); s.px(14, 1, "gold1")
    s.rect(2, 3, 13, 24, "red")
    s.vline(2, 3, 24, "red0"); s.vline(13, 3, 24, "red0")
    s.vline(3, 3, 24, "red1")
    for i in range(6):                                              # swallowtail
        s.hline(2 + i, 13 - i, 25 + i, "red")
        s.px(2 + i, 25 + i, "red0"); s.px(13 - i, 25 + i, "red0")
    s.hline(2, 13, 4, "red1")
    s.rect(6, 8, 9, 15, "gold")                                     # crest: a flame
    s.rect(7, 6, 8, 9, "gold1")
    s.px(6, 12, "gold0"); s.px(9, 12, "gold0")
    s.rect(5, 17, 10, 17, "gold0")
    s.rect(7, 18, 8, 20, "gold0")
    return s.outline()


def sconce(frame):
    s = Sprite(16, 16)
    s.rect(6, 9, 9, 13, "mt0")
    s.hline(6, 9, 9, "mt1")
    s.rect(4, 8, 11, 9, "mt0")
    s.hline(4, 11, 8, "mt1")
    s.rect(7, 13, 8, 14, "mt0")
    s.rect(7, 5, 8, 7, "wax")
    s.px(7, 5, "white")
    f = [(7, 3, 8, 4), (7, 2, 8, 4)][frame]
    s.rect(*f, "ember")
    s.px(7 + frame, 3 if frame == 0 else 2, "ember1")
    return s.outline()


def pillar():
    """A fluted stone column (16x48) with a capital and a base."""
    s = Sprite(16, 48)
    s.rect(1, 0, 14, 5, "st3")
    s.hline(1, 14, 0, "st4")
    s.rect(2, 5, 13, 7, "st2")
    s.rect(3, 8, 12, 39, "st2")
    s.vline(3, 8, 39, "st3"); s.vline(4, 8, 39, "st3")
    s.vline(11, 8, 39, "st1"); s.vline(12, 8, 39, "st0")
    s.vline(7, 8, 39, "st1"); s.vline(8, 8, 39, "st1")
    s.rect(2, 40, 13, 42, "st2")
    s.rect(1, 43, 14, 47, "st3")
    s.hline(1, 14, 43, "st4")
    s.hline(1, 14, 47, "st1")
    return s.outline()


def candelabra(frame):
    """A standing iron candelabra (16x32) with three flames."""
    s = Sprite(16, 32)
    s.rect(7, 12, 8, 27, "mt0")
    s.vline(7, 12, 27, "mt1")
    s.rect(4, 27, 11, 29, "mt0")
    s.hline(4, 11, 27, "mt1")
    s.rect(5, 30, 10, 30, "mt0")
    s.hline(2, 13, 11, "mt0")
    s.vline(2, 8, 11, "mt0"); s.vline(13, 8, 11, "mt0")
    for cx, top in ((2, 5), (7, 3), (13, 5)):
        x0 = cx if cx != 7 else 7
        x1 = cx if cx != 7 else 8
        s.rect(x0, top + 2, x1, top + 6, "wax")
        s.px(x0, top + 2, "white")
        s.rect(x0, top - 1 - frame, x1, top + 1, "ember")
        s.px(x0, top - frame, "ember1")
    return s.outline()


def brazier(frame):
    """An iron fire bowl on a tripod (16x24)."""
    s = Sprite(16, 24)
    s.rect(2, 12, 13, 14, "mt0")
    s.hline(2, 13, 12, "mt1")
    s.rect(3, 14, 12, 16, "mt0")
    s.rect(5, 17, 10, 17, "mt0")
    for x, y in ((4, 18), (11, 18)):
        s.vline(x, y, 22, "mt0")
    s.vline(7, 18, 22, "mt0"); s.vline(8, 18, 22, "mt0")
    s.hline(3, 12, 22, "mt0")
    s.rect(4, 10, 11, 11, "ember0")
    flame = [((5, 5, 10, 10), (6, 3, 9, 7)), ((5, 4, 10, 10), (7, 2, 8, 6))][frame]
    s.rect(*flame[0], "ember")
    s.rect(*flame[1], "ember1")
    return s.outline()


def armor_statue():
    """A suit of armour on a plinth (16x32)."""
    s = Sprite(16, 32)
    s.rect(2, 27, 13, 30, "st2"); s.hline(2, 13, 27, "st3")
    s.rect(5, 17, 10, 26, "mt0"); s.rect(5, 17, 6, 26, "mt1")      # legs
    s.vline(8, 20, 26, "line")
    s.rect(3, 9, 12, 17, "mt0"); s.rect(3, 9, 5, 17, "mt1")        # torso and pauldrons
    s.rect(7, 11, 8, 15, "gold0")
    s.rect(5, 1, 10, 8, "mt0"); s.rect(5, 1, 7, 8, "mt1")          # helmet
    s.hline(6, 9, 4, "line"); s.px(7, 5, "line"); s.px(8, 5, "line")
    s.rect(7, 0, 8, 1, "red1")                                      # plume
    s.rect(1, 12, 2, 24, "mt2")                                     # a sword at rest
    s.rect(0, 11, 3, 11, "gold")
    return s.outline()


def chest():
    s = Sprite(16, 16)
    s.rect(2, 5, 13, 14, "wd2"); s.rect(2, 5, 13, 7, "wd3")
    s.rect(2, 12, 13, 14, "wd1")
    s.hline(2, 13, 8, "mt0")
    s.rect(7, 8, 8, 10, "gold")
    s.vline(2, 5, 14, "mt0"); s.vline(13, 5, 14, "mt0")
    s.hline(3, 12, 4, "wd2")
    return s.outline()


def urn():
    s = Sprite(16, 16)
    s.rect(5, 12, 10, 14, "st2")
    s.rect(4, 7, 11, 11, "st3"); s.rect(4, 7, 5, 11, "st4")
    s.rect(5, 5, 10, 6, "st2")
    s.hline(4, 11, 9, "gold0")
    s.disc(8, 3, 2, "gr1"); s.px(7, 2, "gr0"); s.px(10, 4, "red1")
    return s.outline()


def bookshelf():
    s = Sprite(16, 32)
    s.rect(1, 1, 14, 30, "wd1")
    s.rect(2, 2, 13, 29, "wd0")
    cols = ["red", "gp1", "gold0", "gr1", "gl1", "par0", "red0", "gp0"]
    rng = noise(7)
    for shelf in range(3):
        top = 3 + shelf * 9
        x = 3
        while x < 13:
            w = rng.choice((1, 2, 2, 3))
            h = rng.choice((5, 6, 7))
            col = cols[rng.randrange(len(cols))]
            s.rect(x, top + 8 - h, min(12, x + w - 1), top + 7, col)
            s.px(x, top + 8 - h, "white")
            x += w + (0 if rng.random() < 0.7 else 1)
        s.hline(2, 13, top + 8, "wd2")
    s.rect(1, 1, 14, 1, "wd3")
    return s.outline()


def door():
    """A grand double door in a tall pointed stone arch (32x44)."""
    s = Sprite(32, 44)
    arch = {1: 15, 2: 13, 3: 11, 4: 9, 5: 7, 6: 6, 7: 5, 8: 4, 9: 3, 10: 2, 11: 1}
    s.rect(1, 12, 30, 43, "st3")
    for y, x in arch.items():
        s.rect(x, y, 31 - x, y, "st3")
    s.rect(4, 14, 27, 43, "st0")
    for y, x in arch.items():
        if y >= 4:
            s.rect(x + 3, y + 1, 28 - x, y + 1, "st0")
    s.rect(5, 13, 26, 43, "st0")
    s.rect(5, 15, 15, 43, "wd1"); s.rect(16, 15, 26, 43, "wd1")
    for y, x in ((14, 6), (13, 8), (12, 11), (11, 13), (10, 15)):
        s.rect(x, y, 31 - x, y, "wd1")
    for x in (7, 10, 13, 18, 21, 24):
        s.vline(x, 15, 43, "wd0")
    s.vline(15, 11, 43, "line"); s.vline(16, 11, 43, "line")
    for y in (20, 31):
        s.hline(5, 26, y, "mt0"); s.hline(5, 26, y + 1, "mt1")
    for x in (13, 18):
        s.disc(x, 30, 1, "gold")
    s.px(15, 6, "red1"); s.px(16, 6, "red1")
    s.hline(1, 30, 43, "st1")
    s.vline(4, 14, 43, "st4"); s.vline(27, 14, 43, "st1")
    return s.outline()


def hearth(frame):
    """A grand pointed-arch stone fireplace (32x32) with a live fire (frame 2: cold)."""
    s = Sprite(32, 32)
    s.rect(1, 2, 30, 31, "st2")
    s.rect(1, 2, 30, 4, "st3"); s.hline(1, 30, 2, "st4")           # mantle
    s.rect(3, 5, 28, 6, "st1")
    s.rect(4, 7, 27, 31, "st1")
    for y, x in ((11, 8), (9, 10), (8, 12), (7, 14)):               # the pointed arch
        s.rect(x, y, 31 - x, y, "line")
    s.rect(7, 12, 24, 31, "line")
    s.rect(8, 12, 23, 31, "st0")
    s.rect(9, 11, 22, 11, "st0"); s.rect(11, 10, 20, 10, "st0"); s.rect(13, 9, 18, 9, "st0")
    s.rect(10, 27, 21, 29, "wd1"); s.hline(10, 21, 27, "wd3")      # logs
    s.rect(12, 25, 19, 26, "wd2")
    if frame == 2:
        s.px(15, 26, "ember0"); s.px(16, 26, "ember")
    else:
        flames = [
            [(15, 13, 16, 19), (13, 17, 18, 25), (11, 21, 20, 26)],
            [(14, 12, 17, 18), (12, 16, 19, 24), (11, 21, 20, 26)],
        ][frame]
        s.rect(*flames[2], "ember0")
        s.rect(*flames[1], "ember")
        s.rect(*flames[0], "ember1")
        s.rect(14, 22, 17, 26, "ember1")
    for cx in (5, 25):                                              # candlesticks on the mantle
        s.rect(cx, 0, cx + 1, 2, "wax"); s.px(cx, 0, "ember1")
    s.px(15, 4, "red1"); s.px(16, 4, "red1")
    return s.outline()


def armory():
    """The weapon rack: iron-banded dark wood with a sword, an axe and a round shield."""
    s = Sprite(32, 28)
    s.rect(1, 1, 30, 24, "wd1")
    s.rect(2, 2, 29, 23, "wd0")
    s.hline(1, 30, 1, "wd2")
    for y in (6, 17):
        s.hline(2, 29, y, "mt0"); s.hline(2, 29, y + 1, "mt1")
    s.rect(7, 3, 8, 15, "mt1"); s.vline(7, 3, 15, "mt2")
    s.rect(5, 15, 10, 16, "gold")
    s.rect(7, 17, 8, 21, "wd2")
    s.px(7, 22, "gold0"); s.px(8, 22, "gold0")
    s.disc(18, 12, 6, "red0"); s.disc(18, 12, 4, "red"); s.disc(18, 12, 1, "gold")
    s.px(18, 6, "gold0")
    s.rect(26, 4, 27, 21, "wd2"); s.rect(23, 5, 25, 10, "mt1"); s.vline(23, 5, 10, "mt2")
    s.rect(2, 24, 29, 26, "st2"); s.hline(2, 29, 26, "st0")
    return s.outline()


def map_table(frame):
    """The Map table: a heavy dark-wood table with a parchment map and a candle."""
    s = Sprite(32, 28)
    s.rect(1, 6, 30, 22, "wd1")
    s.hline(1, 30, 6, "wd2")
    s.rect(1, 20, 30, 23, "wd0")
    s.rect(3, 23, 5, 27, "wd0"); s.rect(26, 23, 28, 27, "wd0")
    s.rect(4, 8, 24, 19, "par1")
    s.hline(4, 24, 8, "par2"); s.hline(4, 24, 19, "par0")
    path = [(6, 17), (9, 15), (12, 16), (15, 13), (18, 14), (21, 11)]
    for a, b in zip(path, path[1:]):
        for t in range(5):
            s.px(a[0] + (b[0] - a[0]) * t // 5, a[1] + (b[1] - a[1]) * t // 5, "red0")
    for gx, gy in ((7, 10), (13, 10), (19, 17)):
        s.px(gx, gy, "st1"); s.px(gx - 1, gy + 1, "st0"); s.px(gx + 1, gy + 1, "st0")
    s.px(21, 11, "red"); s.px(22, 12, "red"); s.px(20, 12, "red")
    s.rect(26, 3, 27, 7, "wax"); s.px(26, 3, "white")
    s.px(26 + frame, 1, "ember"); s.px(26 + frame, 2, "ember1"); s.px(27 - frame, 2, "ember")
    return s.outline()


def trophy_case():
    """The Trophy wall: a glass-fronted case with a cup, a crown and a skull (32x32)."""
    s = Sprite(32, 32)
    s.rect(1, 1, 30, 30, "wd1")
    s.rect(2, 2, 29, 29, "wd0")
    s.hline(1, 30, 1, "wd2")
    s.rect(3, 3, 28, 26, "gl0")
    s.rect(4, 4, 27, 25, "st0")
    s.rect(4, 4, 27, 5, "gl1")
    s.hline(4, 27, 14, "wd2"); s.hline(4, 27, 15, "wd0")
    s.hline(4, 27, 25, "wd2")
    # a golden cup, a crown and a skull on the shelves
    s.rect(7, 8, 12, 9, "gold"); s.rect(8, 10, 11, 12, "gold"); s.rect(9, 13, 10, 13, "gold0"); s.hline(7, 12, 8, "gold1")
    s.px(6, 9, "gold0"); s.px(13, 9, "gold0")
    s.rect(15, 10, 20, 13, "gold"); s.px(15, 8, "gold1"); s.px(17, 7, "gold1"); s.px(20, 8, "gold1")
    s.px(17, 11, "red1"); s.px(19, 11, "gl2")
    s.rect(22, 9, 26, 13, "par1"); s.px(23, 11, "line"); s.px(25, 11, "line"); s.px(24, 13, "line")
    s.rect(7, 18, 11, 24, "mt1"); s.rect(8, 19, 10, 20, "mt2")                   # a relic sword hilt
    s.rect(15, 21, 20, 24, "red"); s.rect(16, 19, 19, 21, "red1")                # a cushion with a gem
    s.px(17, 19, "gl2")
    s.rect(23, 20, 27, 24, "gp1"); s.px(25, 19, "gold1")
    s.rect(4, 4, 6, 24, (140, 170, 230, 40))                                     # glass glare
    s.rect(11, 27, 20, 29, "gold0"); s.hline(11, 20, 27, "gold1")                # the plaque
    return s.outline()


def study_desk(frame):
    """The Study desk: a writing desk with an open book, a quill and a lamp (32x28)."""
    s = Sprite(32, 28)
    s.rect(1, 8, 30, 22, "wd1"); s.hline(1, 30, 8, "wd2"); s.rect(1, 20, 30, 23, "wd0")
    s.rect(3, 23, 5, 27, "wd0"); s.rect(26, 23, 28, 27, "wd0")
    s.rect(5, 9, 17, 18, "par1"); s.vline(11, 9, 18, "par0")                        # the open book
    for y in (11, 13, 15):
        s.hline(6, 10, y, "par0"); s.hline(12, 16, y, "par0")
    s.hline(5, 17, 9, "par2")
    s.rect(20, 9, 25, 11, "red"); s.rect(20, 12, 25, 14, "gp1")                     # stacked books
    s.rect(20, 9, 20, 14, "red0")
    s.rect(19, 15, 21, 18, "mt0")                                                    # inkwell
    s.px(19, 14, "par2"); s.px(18, 13, "par2"); s.px(17, 12, "par1")               # the quill
    s.rect(27, 4, 28, 12, "gold0"); s.rect(26, 3, 29, 4, "gold")                     # the brass lamp
    s.px(27 + frame, 1, "ember"); s.px(27 + frame, 2, "ember1")
    return s.outline()


def dummy():
    """A straw training dummy on a post (16x32)."""
    s = Sprite(16, 32)
    s.rect(7, 12, 8, 29, "wd1"); s.vline(7, 12, 29, "wd2")
    s.rect(2, 11, 13, 13, "wd1"); s.hline(2, 13, 11, "wd2")
    s.rect(4, 12, 11, 24, "par0"); s.rect(4, 12, 6, 24, "par1")
    s.disc(8, 18, 3, "red"); s.disc(8, 18, 1, "par2"); s.px(8, 18, "red1")
    s.rect(5, 3, 10, 10, "par1"); s.rect(5, 3, 7, 10, "par2")
    s.px(6, 6, "line"); s.px(9, 6, "line"); s.hline(6, 9, 8, "line")
    s.rect(5, 2, 10, 3, "wd2")
    s.rect(3, 29, 12, 30, "st2"); s.hline(3, 12, 29, "st3")
    for x, y in ((3, 13), (12, 14), (4, 22), (11, 23)):
        s.px(x, y, "gold0")
    return s.outline()


def ring():
    """A rune circle on the floor for training (64x40, translucent)."""
    s = Sprite(64, 40)
    import math
    cx, cy = 31.5, 19.5
    for y in range(40):
        for x in range(64):
            d = math.hypot((x - cx) / 30.0, (y - cy) / 18.0)
            if 0.9 <= d <= 1.0:
                s.px(x, y, (240, 190, 60, 200))
            elif 0.78 <= d < 0.9:
                s.px(x, y, (150, 108, 28, 110))
            elif d < 0.78:
                s.px(x, y, (20, 16, 34, 70))
    for i in range(8):                                                           # rune ticks
        a = i * math.pi / 4
        x, y = int(cx + math.cos(a) * 24), int(cy + math.sin(a) * 14)
        s.px(x, y, "gold1"); s.px(x + 1, y, "gold")
    return s


def cauldron(frame):
    """The Pantry's cauldron: bubbling stew over a small fire (16x24)."""
    s = Sprite(16, 24)
    s.rect(2, 8, 13, 17, "mt0"); s.rect(2, 8, 4, 17, "mt1")
    s.hline(1, 14, 8, "mt1"); s.hline(1, 14, 9, "mt0")
    s.rect(3, 9, 12, 10, "gr0"); s.hline(4, 11, 9, "gr1")                           # the stew
    s.px(5 + frame, 7, "gr1"); s.px(9 - frame, 6, "gr1"); s.px(7, 7 - frame, "gr1")
    s.rect(3, 18, 4, 20, "mt0"); s.rect(11, 18, 12, 20, "mt0")
    s.rect(4, 20, 11, 21, "wd1")
    s.rect(5, 19, 10, 20, "ember0")
    s.rect(6 + frame, 17, 9, 19, "ember"); s.px(7, 18, "ember1")
    return s.outline()


def pantry_shelf():
    """The Pantry shelves: jars, bread, bottles and hanging herbs (32x32)."""
    s = Sprite(32, 32)
    s.rect(1, 1, 30, 30, "st2"); s.hline(1, 30, 1, "st3")
    s.rect(3, 3, 28, 29, "st0")
    for y in (13, 22):
        s.rect(3, y, 28, y + 1, "wd2"); s.hline(3, 28, y + 1, "wd0")
    for x, col in ((5, "red"), (9, "gr1"), (13, "gp1"), (17, "gold0"), (21, "red1")):  # bottles
        s.rect(x, 7, x + 2, 12, col); s.px(x + 1, 6, "mt1"); s.px(x, 7, "white")
    for x in (5, 11, 17):                                                           # loaves
        s.rect(x, 17, x + 4, 21, "wd3"); s.hline(x, x + 4, 17, "gold0"); s.px(x + 2, 19, "wd2")
    s.rect(23, 15, 27, 21, "wd1"); s.hline(23, 27, 15, "wd2"); s.hline(23, 27, 18, "mt0")  # a keg
    for x in (6, 12, 18, 24):                                                       # jars
        s.rect(x, 24, x + 3, 28, "par0"); s.rect(x, 24, x + 3, 25, "par1"); s.px(x + 1, 26, "red")
    return s.outline()


def perch():
    """Pyr's perch: an iron stand with a red cushion and a ring of embers (16x32)."""
    s = Sprite(16, 32)
    s.rect(7, 12, 8, 27, "mt0"); s.vline(7, 12, 27, "mt1")
    s.rect(4, 27, 11, 29, "mt0"); s.hline(4, 11, 27, "mt1"); s.rect(5, 30, 10, 30, "mt0")
    s.rect(2, 7, 13, 11, "red"); s.hline(2, 13, 7, "red1"); s.hline(2, 13, 11, "red0")
    s.rect(1, 9, 1, 10, "gold"); s.rect(14, 9, 14, 10, "gold")
    s.px(4, 8, "gold1"); s.px(11, 8, "gold1")
    s.px(5, 5, "ember"); s.px(10, 4, "ember1"); s.px(8, 3, "ember")                 # drifting embers
    return s.outline()



def pyr(frame):
    """Pyr, the Tiny Code-Flame: a little living flame with bright eyes."""
    s = Sprite(16, 16)
    bob = frame
    s.disc(8, 9 + bob, 4, "ember0")
    s.disc(8, 9 + bob, 3, "ember")
    s.rect(7, 4 + bob, 8, 6 + bob, "ember")
    s.px(8, 3 + bob, "ember1"); s.px(7, 4 + bob, "ember1")
    s.rect(6, 9 + bob, 7, 10 + bob, "ember1")
    s.rect(6, 9 + bob, 6, 10 + bob, "line")
    s.rect(9, 9 + bob, 9, 10 + bob, "line")
    s.px(6, 9 + bob, "white"); s.px(9, 9 + bob, "white")
    return s.outline()


def shadow():
    s = Sprite(16, 8)
    for y, (x0, x1) in enumerate([(5, 10), (3, 12), (2, 13), (2, 13), (3, 12), (5, 10)], start=1):
        for x in range(x0, x1 + 1):
            s.px(x, y, (6, 4, 14, 110))
    return s


def moonbeam():
    """A soft slanted shaft of moonlight on the marble (32x48, translucent)."""
    s = Sprite(32, 48)
    for y in range(48):
        for x in range(32):
            lean = y // 3
            if 4 + lean <= x <= 14 + lean:
                edge = min(x - (4 + lean), (14 + lean) - x)
                s.px(x, y, (140, 170, 230, 26 if edge > 1 else 14))
    return s


def build():
    pieces = {}
    for v in (0, 1):
        pieces[f"floor_{v}"] = floor_tile(v)
        pieces[f"wall_face_{v}"] = wall_face_tile(v)
    pieces["carpet"] = carpet_tile()
    pieces["wall_top"] = wall_top_tile()
    pieces["plinth"] = plinth_tile()
    for f in (0, 1):
        pieces[f"sconce_{f}"] = sconce(f)
        pieces[f"fire_{f}"] = hearth(f)
        pieces[f"candle_{f}"] = map_table(f)
        pieces[f"pyr_{f}"] = pyr(f)
        pieces[f"candelabra_{f}"] = candelabra(f)
        pieces[f"brazier_{f}"] = brazier(f)
    pieces["fire_out"] = hearth(2)
    pieces["window"] = window_arch()
    pieces["banner"] = banner()
    pieces["pillar"] = pillar()
    pieces["armor"] = armor_statue()
    pieces["door"] = door()
    pieces["trophy_case"] = trophy_case()
    for f in (0, 1):
        pieces[f"desk_{f}"] = study_desk(f)
        pieces[f"cauldron_{f}"] = cauldron(f)
    pieces["dummy"] = dummy()
    pieces["ring"] = ring()
    pieces["pantry_shelf"] = pantry_shelf()
    pieces["perch"] = perch()
    pieces["chest"] = chest()
    pieces["urn"] = urn()
    pieces["bookshelf"] = bookshelf()
    pieces["armory"] = armory()
    pieces["shadow"] = shadow()
    pieces["moonbeam"] = moonbeam()
    import hall_pieces
    hall_pieces.add(pieces, Sprite, C, noise)
    # Props cut from AI prop sheets (tools/home_art/from_props.py) override a code-drawn piece of the same name.
    props_dir = Path(__file__).resolve().parent / "props"
    for png in sorted(props_dir.glob("*.png")) if props_dir.exists() else []:
        img = Image.open(png).convert("RGBA")
        spr = Sprite(img.width, img.height)
        spr.img = img
        pieces[png.stem] = spr
        if png.stem.endswith("_l") and not (props_dir / (png.stem[:-2] + "_r.png")).exists():
            mirrored = Sprite(img.width, img.height)           # a left-facing prop gets a mirrored right-facing twin
            mirrored.img = img.transpose(Image.FLIP_LEFT_RIGHT)
            pieces[png.stem[:-2] + "_r"] = mirrored

    atlas_w = 384
    x = y = row_h = 0
    placed, positions = {}, []
    for name, sprite in pieces.items():
        if x + sprite.w > atlas_w:
            x, y, row_h = 0, y + row_h + 1, 0
        positions.append((name, x, y))
        placed[name] = {"x": x, "y": y, "w": sprite.w, "h": sprite.h}
        x += sprite.w + 1
        row_h = max(row_h, sprite.h)
    atlas = Image.new("RGBA", (atlas_w, y + row_h + 1), (0, 0, 0, 0))
    for name, px, py in positions:
        atlas.paste(pieces[name].img, (px, py))
    OUT.mkdir(parents=True, exist_ok=True)
    atlas.save(OUT / "tiles.png")
    (OUT / "tiles.json").write_text(json.dumps(placed, indent=1), encoding="utf-8")
    lines = ["# Generated by tools/home_art/make_tiles.py. Do not edit.", "class_name TilesData", "", "const REGIONS := {"]
    for name, r in placed.items():
        lines.append(f'\t"{name}": Rect2({r["x"]}, {r["y"]}, {r["w"]}, {r["h"]}),')
    lines.append("}")
    (OUT / "tiles_data.gd").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'tiles.png'} ({atlas.width}x{atlas.height}, {len(placed)} pieces)")


if __name__ == "__main__":
    build()
