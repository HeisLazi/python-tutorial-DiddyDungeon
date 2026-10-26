#!/usr/bin/env python3
"""Generate the Home room tileset and objects (GBA / FireRed look, dark-arcade palette).

Writes ide/home-godot/art/tiles.png (an atlas) and tiles.json (name -> region),
so the Godot scene can place any piece by name. Every sprite is drawn in code
with a fixed palette, a 1px dark outline and flat 3-tone shading; re-run this
script to regenerate. Frames of animated pieces are separate regions
(torch_0, torch_1, fire_0, ...).

Run with the system Python (it has Pillow):  python3 tools/home_art/make_tiles.py
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "ide" / "home-godot" / "art"

# ── Palette: the app's deep indigo shadows with warm wood, ember and gold ─────
C = {
    "line": (20, 16, 31),
    "st0": (35, 30, 56), "st1": (49, 43, 78), "st2": (66, 59, 102), "st3": (92, 84, 134),
    "br0": (56, 32, 46), "br1": (84, 48, 64), "br2": (112, 66, 84), "br3": (140, 88, 104),
    "wd0": (60, 36, 24), "wd1": (98, 60, 34), "wd2": (140, 88, 48), "wd3": (186, 124, 68),
    "gold": (245, 197, 66), "gold0": (176, 130, 32), "gold1": (255, 232, 140),
    "ember": (255, 122, 42), "ember0": (214, 70, 30), "ember1": (255, 209, 102),
    "red": (192, 57, 43), "red0": (132, 34, 36),
    "pur0": (62, 44, 112), "pur1": (96, 70, 164), "pur2": (132, 104, 208),
    "par0": (205, 183, 122), "par1": (232, 217, 168), "par2": (248, 240, 208),
    "gr0": (38, 106, 53), "gr1": (63, 143, 74), "gr2": (110, 186, 110),
    "mt0": (93, 102, 124), "mt1": (154, 163, 184), "mt2": (214, 220, 232),
    "white": (242, 239, 230), "glass": (120, 170, 230), "glass0": (62, 100, 170),
}


def rgba(name: str, alpha: int = 255):
    r, g, b = C[name]
    return (r, g, b, alpha)


class Sprite:
    def __init__(self, w: int, h: int):
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
        """A 1px dark outline around every opaque pixel (kept inside the canvas)."""
        out = self.img.copy()
        src = self.img.load()
        dst = out.load()
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


def noise(seed: int):
    return random.Random(seed)


# ── Floor and wall tiles (16x16, tileable) ───────────────────────────────────
def floor_tile(variant: int) -> Sprite:
    """Warm wooden planks (FireRed house floors), two planks per tile with staggered joints."""
    s = Sprite(16, 16)
    rng = noise(100 + variant)
    s.rect(0, 0, 15, 15, "wd2")
    joints = [(5, 12), (11, 4)][variant]
    for plank, top in enumerate((0, 8)):
        s.hline(0, 15, top, "wd3")              # lit top edge
        s.hline(0, 15, top + 6, "wd1")          # shade before the seam
        s.hline(0, 15, top + 7, "wd0")          # seam
        s.vline(joints[plank], top, top + 6, "wd0")
        s.vline(joints[plank] + 1, top + 1, top + 5, "wd3")
        for _ in range(5):                       # grain flecks
            s.px(rng.randrange(16), top + 1 + rng.randrange(5), "wd1" if rng.random() < 0.6 else "wd3")
    return s


def rug_tile(kind: str) -> Sprite:
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "pur0")
    s.rect(1, 1, 14, 14, "pur1")
    if kind == "mid":
        for i in range(0, 16, 4):
            s.px(i + 2, 7, "gold")
            s.px(i + 2, 8, "gold0")
        s.hline(0, 15, 0, "pur0")
        s.hline(0, 15, 15, "pur0")
    s.vline(0, 0, 15, "gold0")
    s.vline(15, 0, 15, "gold0")
    return s


def wall_face_tile(variant: int) -> Sprite:
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "br1")
    rng = noise(200 + variant)
    for row in range(4):  # four brick rows, offset every other row
        y = row * 4
        s.hline(0, 15, y + 3, "br0")
        off = 0 if row % 2 == 0 else 4
        for x in range(off, 16, 8):
            s.vline(x, y, y + 2, "br0")
        s.hline(0, 15, y, "br2")
        for _ in range(2):
            s.px(rng.randrange(16), y + 1 + rng.randrange(2), "br3")
    return s


def wall_top_tile() -> Sprite:
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "st0")
    s.hline(0, 15, 12, "st1")
    s.hline(0, 15, 13, "st2")
    s.hline(0, 15, 14, "st3")
    s.hline(0, 15, 15, "line")
    return s


def skirting_tile() -> Sprite:
    s = Sprite(16, 16)
    s.rect(0, 0, 15, 15, "st1")
    s.rect(0, 0, 15, 3, "wd1")
    s.hline(0, 15, 0, "wd3")
    s.hline(0, 15, 3, "wd0")
    s.hline(0, 15, 7, "st0")
    s.hline(0, 15, 15, "st0")
    s.vline(7, 8, 14, "st0")
    s.hline(0, 15, 8, "st2")
    return s


# ── Objects ──────────────────────────────────────────────────────────────────
def torch(frame: int) -> Sprite:
    s = Sprite(16, 16)
    s.rect(7, 9, 8, 14, "wd2")
    s.vline(7, 9, 14, "wd1")
    s.rect(5, 8, 10, 9, "mt0")
    s.hline(5, 10, 8, "mt1")
    flame = [(7, 4, 8, 7), (6, 5, 9, 7)] if frame == 0 else [(7, 3, 8, 7), (6, 5, 9, 7)]
    s.rect(*flame[1], "ember0")
    s.rect(*flame[0], "ember")
    s.rect(7, 6, 8, 7, "ember1")
    s.px(8 if frame else 7, 2 if frame else 3, "ember1")
    return s.outline()


def window() -> Sprite:
    s = Sprite(16, 16)
    s.rect(2, 1, 13, 14, "wd2")
    s.rect(3, 2, 12, 13, "glass0")
    s.rect(4, 3, 11, 12, "glass")
    s.vline(7, 2, 13, "wd1")
    s.vline(8, 2, 13, "wd2")
    s.hline(3, 12, 7, "wd1")
    s.hline(3, 12, 8, "wd2")
    s.px(5, 4, "white")
    s.px(5, 5, "white")
    s.px(10, 10, "par2")
    s.rect(1, 14, 14, 14, "wd0")
    return s.outline()


def door() -> Sprite:
    s = Sprite(16, 24)
    s.rect(1, 1, 14, 23, "wd1")
    s.rect(2, 2, 13, 23, "wd2")
    for x in (5, 8, 11):
        s.vline(x, 2, 23, "wd1")
    s.hline(2, 13, 2, "wd3")
    s.rect(2, 20, 13, 23, "wd0")
    s.px(11, 13, "gold")
    s.px(11, 14, "gold0")
    s.rect(0, 0, 15, 0, "line")
    return s.outline()


def barrel() -> Sprite:
    s = Sprite(16, 16)
    s.rect(3, 2, 12, 13, "wd2")
    s.rect(3, 2, 5, 13, "wd3")
    s.rect(10, 2, 12, 13, "wd1")
    for y in (4, 11):
        s.hline(3, 12, y, "mt0")
        s.hline(3, 12, y + 1, "mt1")
    s.hline(4, 11, 1, "wd3")
    s.hline(4, 11, 14, "wd0")
    return s.outline()


def crate() -> Sprite:
    s = Sprite(16, 16)
    s.rect(2, 3, 13, 14, "wd2")
    s.rect(2, 3, 13, 4, "wd3")
    s.rect(2, 13, 13, 14, "wd0")
    s.rect(2, 3, 3, 14, "wd1")
    s.rect(12, 3, 13, 14, "wd1")
    for i in range(4, 12):
        s.px(i, 4 + (i - 4) * 9 // 8, "wd1")
    return s.outline()


def plant() -> Sprite:
    s = Sprite(16, 16)
    s.rect(5, 10, 10, 14, "br2")
    s.rect(5, 10, 10, 11, "br3")
    s.rect(5, 14, 10, 14, "br0")
    s.disc(8, 6, 4, "gr1")
    s.disc(5, 8, 2, "gr0")
    s.disc(11, 8, 2, "gr0")
    s.px(7, 4, "gr2")
    s.px(9, 5, "gr2")
    s.px(6, 6, "gr2")
    return s.outline()


def bookshelf() -> Sprite:
    s = Sprite(16, 32)
    s.rect(1, 1, 14, 30, "wd1")
    s.rect(2, 2, 13, 29, "wd0")
    cols = ["red", "pur1", "gold0", "gr1", "glass0", "par0", "red0", "pur2"]
    rng = noise(7)
    for shelf in range(3):
        top = 3 + shelf * 9
        x = 3
        while x < 13:
            w = rng.choice((1, 2, 2, 3))
            h = rng.choice((5, 6, 7))
            col = cols[rng.randrange(len(cols))]
            s.rect(x, top + 8 - h, min(12, x + w - 1), top + 7, col)
            s.px(x, top + 8 - h, "white" if col != "par0" else "par2")
            x += w + (0 if rng.random() < 0.7 else 1)
        s.hline(2, 13, top + 8, "wd2")
    s.rect(1, 1, 14, 1, "wd3")
    return s.outline()


def rug(w_tiles: int, h_tiles: int) -> Sprite:
    s = Sprite(w_tiles * 16, h_tiles * 16)
    s.rect(0, 0, s.w - 1, s.h - 1, "pur0")
    s.rect(2, 2, s.w - 3, s.h - 3, "pur1")
    s.rect(3, 3, s.w - 4, s.h - 4, "pur2")
    s.rect(5, 5, s.w - 6, s.h - 6, "pur1")
    for x in range(8, s.w - 8, 4):
        s.px(x, s.h // 2, "gold")
        s.px(x + 1, s.h // 2, "gold0")
    s.rect(0, 0, s.w - 1, 0, "gold0")
    s.rect(0, s.h - 1, s.w - 1, s.h - 1, "gold0")
    return s


def hearth(frame: int) -> Sprite:
    """The Hearth station: a stone fireplace with a mantle and a live fire."""
    s = Sprite(32, 32)
    s.rect(1, 1, 30, 30, "st2")
    s.rect(1, 1, 30, 3, "st3")                     # mantle top
    s.rect(1, 4, 30, 5, "wd1")                     # mantle beam
    s.hline(1, 30, 4, "wd3")
    s.rect(4, 6, 27, 29, "st1")                    # chimney breast
    s.rect(7, 12, 24, 29, "line")                  # firebox
    s.rect(8, 13, 23, 29, "st0")
    for y in range(13, 30, 4):                     # inner bricks
        s.hline(8, 23, y, "line")
    # logs
    s.rect(10, 26, 21, 28, "wd1")
    s.hline(10, 21, 26, "wd3")
    s.rect(12, 24, 19, 25, "wd2")
    # fire (two frames), or an unlit grate (frame 2) with one ember left
    if frame == 2:
        s.px(15, 25, "ember0")
        s.px(16, 25, "ember")
    else:
        flames = [
            [(15, 14, 16, 18), (13, 17, 18, 24), (11, 20, 20, 25)],
            [(14, 13, 17, 17), (12, 16, 19, 23), (11, 20, 20, 25)],
        ][frame]
        s.rect(*(flames[2][0], flames[2][1], flames[2][2], flames[2][3]), "ember0")
        s.rect(*(flames[1][0], flames[1][1], flames[1][2], flames[1][3]), "ember")
        s.rect(*(flames[0][0], flames[0][1], flames[0][2], flames[0][3]), "ember1")
        s.rect(14, 21, 17, 25, "ember1")
    # candlesticks on the mantle
    for cx in (5, 26):
        s.rect(cx, 0, cx + 1, 1, "par2")
        s.px(cx, 0, "ember1")
    # hanging pot hook
    s.hline(7, 24, 12, "mt0")
    return s.outline()


def armory(frame: int = 0) -> Sprite:
    """The Armory rack: a wooden board with a sword, an axe and a round shield."""
    s = Sprite(32, 28)
    s.rect(1, 1, 30, 24, "wd1")
    s.rect(2, 2, 29, 23, "wd0")
    s.hline(1, 30, 1, "wd3")
    s.hline(2, 29, 12, "wd1")                      # a rail
    s.hline(2, 29, 13, "wd2")
    # sword (blade up, gold hilt)
    s.rect(7, 3, 8, 15, "mt1")
    s.vline(7, 3, 15, "mt2")
    s.rect(5, 15, 10, 16, "gold")
    s.rect(7, 17, 8, 21, "wd2")
    s.px(7, 22, "gold0")
    s.px(8, 22, "gold0")
    # round shield
    s.disc(18, 11, 6, "pur1")
    s.disc(18, 11, 4, "pur2")
    s.disc(18, 11, 1, "gold")
    s.px(18, 5, "gold0")
    # axe
    s.rect(26, 4, 27, 21, "wd2")
    s.rect(23, 5, 25, 10, "mt1")
    s.vline(23, 5, 10, "mt2")
    s.rect(28, 4, 28, 21, "wd1")
    # floor stand
    s.rect(2, 24, 29, 26, "wd2")
    s.hline(2, 29, 26, "wd0")
    return s.outline()


def map_table(frame: int) -> Sprite:
    """The Map table: a wooden table with a parchment map and a lit candle."""
    s = Sprite(32, 28)
    s.rect(1, 6, 30, 22, "wd2")
    s.hline(1, 30, 6, "wd3")
    s.rect(1, 20, 30, 23, "wd1")
    s.rect(3, 23, 5, 27, "wd0")
    s.rect(26, 23, 28, 27, "wd0")
    s.rect(4, 8, 24, 19, "par1")                   # the map
    s.hline(4, 24, 8, "par2")
    s.hline(4, 24, 19, "par0")
    path = [(6, 17), (9, 15), (12, 16), (15, 13), (18, 14), (21, 11)]
    for a, b in zip(path, path[1:]):
        for t in range(5):
            s.px(a[0] + (b[0] - a[0]) * t // 5, a[1] + (b[1] - a[1]) * t // 5, "red0")
    for gx, gy in ((7, 10), (13, 10), (19, 17)):    # little mountains
        s.px(gx, gy, "br2")
        s.px(gx - 1, gy + 1, "br1")
        s.px(gx + 1, gy + 1, "br1")
    s.px(21, 11, "red")
    s.px(22, 12, "red")
    s.px(20, 12, "red")
    s.rect(26, 3, 27, 7, "par2")                    # candle
    s.px(26, 3, "par1")
    flame = 0 if frame == 0 else 1
    s.px(26 + flame, 1, "ember")
    s.px(26 + flame, 2, "ember1")
    s.px(27 - flame, 2, "ember")
    return s.outline()


def pyr(frame: int) -> Sprite:
    """Pyr, the Tiny Code-Flame: a little living flame with bright eyes."""
    s = Sprite(16, 16)
    bob = frame
    s.disc(8, 9 + bob, 4, "ember0")
    s.disc(8, 9 + bob, 3, "ember")
    s.rect(7, 4 + bob, 8, 6 + bob, "ember")         # the flame tip
    s.px(8, 3 + bob, "ember1")
    s.px(7, 4 + bob, "ember1")
    s.rect(6, 9 + bob, 7, 10 + bob, "ember1")
    s.rect(6, 9 + bob, 6, 10 + bob, "line")        # eyes
    s.rect(9, 9 + bob, 9, 10 + bob, "line")
    s.px(6, 9 + bob, "white")
    s.px(9, 9 + bob, "white")
    return s.outline()


def shadow() -> Sprite:
    s = Sprite(16, 8)
    for y, (x0, x1) in enumerate([(5, 10), (3, 12), (2, 13), (2, 13), (3, 12), (5, 10)], start=1):
        for x in range(x0, x1 + 1):
            s.px(x, y, (10, 8, 20, 96))
    return s


def build() -> None:
    pieces: dict[str, Sprite] = {}
    for variant in (0, 1):
        pieces[f"floor_{variant}"] = floor_tile(variant)
    pieces["rug_edge"] = rug_tile("edge")
    pieces["rug_mid"] = rug_tile("mid")
    for variant in (0, 1):
        pieces[f"wall_face_{variant}"] = wall_face_tile(variant)
    pieces["wall_top"] = wall_top_tile()
    pieces["skirting"] = skirting_tile()
    for frame in (0, 1):
        pieces[f"torch_{frame}"] = torch(frame)
        pieces[f"fire_{frame}"] = hearth(frame)
        pieces[f"candle_{frame}"] = map_table(frame)
        pieces[f"pyr_{frame}"] = pyr(frame)
    pieces["fire_out"] = hearth(2)
    pieces["window"] = window()
    pieces["door"] = door()
    pieces["barrel"] = barrel()
    pieces["crate"] = crate()
    pieces["plant"] = plant()
    pieces["bookshelf"] = bookshelf()
    pieces["rug_big"] = rug(5, 3)
    pieces["armory"] = armory()
    pieces["shadow"] = shadow()

    # Pack into a simple shelf atlas (rows grow as needed).
    atlas_w = 256
    x = y = row_h = 0
    placed: dict[str, dict[str, int]] = {}
    positions: list[tuple[str, int, int]] = []
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
    # The same map as GDScript, so an exported build never needs a loose JSON file.
    lines = ["# Generated by tools/home_art/make_tiles.py. Do not edit.", "class_name TilesData", "", "const REGIONS := {"]
    for name, r in placed.items():
        lines.append(f'\t"{name}": Rect2({r["x"]}, {r["y"]}, {r["w"]}, {r["h"]}),')
    lines.append("}")
    (OUT / "tiles_data.gd").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT / 'tiles.png'} ({atlas.width}x{atlas.height}, {len(placed)} pieces)")


if __name__ == "__main__":
    build()
