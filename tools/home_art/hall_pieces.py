#!/usr/bin/env python3
"""Great Hall pieces, drawn at the scale of the 40 px hunter (hearth ~56 px, doors ~48 px).

Imported by make_tiles.py (`add(pieces, Sprite, C, noise)`); run directly to write a 4x contact
sheet for review:  python3 tools/home_art/hall_pieces.py ide/home-godot/shot_pieces.png

Concept art (the target look): tools/home_art/concepts/great_hall_base.png (cold, bare, grey stone,
a small fire, torn banners) to great_hall_max.png (navy/cream marble, crimson runner, blue-gold hearth,
stained glass, chandelier, knights, banquet table). Same top-down 3/4 camera as the rest of the Home.
Light comes from the top-left; every piece has a 1 px dark outline and 3-4 tones.
"""

from __future__ import annotations

NEW_COLORS = {
    # cold grey-blue castle stone (the base hall)
    "gs0": (24, 26, 38), "gs1": (40, 44, 60), "gs2": (58, 62, 82), "gs3": (82, 88, 110), "gs4": (112, 120, 144),
    # flagstone floor
    "fl0": (38, 40, 54), "fl1": (58, 60, 76), "fl2": (78, 80, 98), "fl3": (102, 104, 124),
    # navy and cream marble (the max hall)
    "nv0": (16, 22, 54), "nv1": (26, 38, 84), "nv2": (42, 60, 120), "nv3": (74, 98, 170),
    "cr0": (128, 132, 152), "cr1": (170, 176, 198), "cr2": (214, 220, 238), "cr3": (242, 244, 252),
    # blue fire
    "bf0": (28, 66, 190), "bf1": (58, 128, 238), "bf2": (130, 200, 255), "bf3": (232, 248, 255),
    "web": (176, 180, 204), "dust": (96, 100, 120),
}


def add(pieces, Sprite, C, noise):
    C.update(NEW_COLORS)
    rng = noise

    # ── tiles ───────────────────────────────────────────────────────────────
    def flag(variant):
        s = Sprite(16, 16)
        r = rng(900 + variant)
        s.rect(0, 0, 15, 15, "fl1")
        rows = [(0, 7), (8, 15)]
        for ri, (y0, y1) in enumerate(rows):
            cut = 4 + r.randrange(0, 7) if ri == 0 else 7 + r.randrange(-3, 4)
            for x0, x1 in ((0, cut - 1), (cut, 15)):
                s.hline(x0, x1, y0, "fl2")                       # lit top edge
                s.vline(x0, y0, y1, "fl2")
                s.hline(x0, x1, y1, "fl0")                       # shade bottom
                s.vline(x1, y0, y1, "fl0")
        for _ in range(7):
            s.px(r.randrange(16), r.randrange(16), "fl3" if r.random() < 0.4 else "fl0")
        if variant == 1:
            for i in range(5):
                s.px(3 + i, 9 + i, "fl0")                       # a crack
        if variant == 2:
            for i in range(4):
                s.px(10 + i, 2 + i // 2, "fl0")
        return s

    def checker(variant):
        """One big marble flag per tile (cream or navy), bevelled, calmer than a fine checker."""
        s = Sprite(16, 16)
        r = rng(970 + variant)
        light = variant % 2 == 0
        base, hi, lo = ("cr0", "cr1", "gs1") if light else ("nv1", "nv2", "nv0")
        s.rect(0, 0, 15, 15, base)
        s.hline(0, 15, 0, hi); s.hline(0, 15, 1, hi) if light else None
        s.vline(0, 0, 15, hi)
        s.hline(0, 15, 15, lo); s.vline(15, 0, 15, lo)
        s.hline(1, 14, 14, lo) if light else None
        if light:
            for i in range(6):
                s.px(3 + i, 11 - i, "cr1")                       # a polished sheen
            s.px(9, 4, "cr0"); s.px(5, 9, "cr0")
        else:
            for _ in range(4):
                s.px(2 + r.randrange(12), 2 + r.randrange(12), "nv2")
            s.px(4, 4, "nv3"); s.px(5, 3, "nv3")
        return s

    def stone_wall(variant):
        s = Sprite(16, 16)
        r = rng(950 + variant)
        s.rect(0, 0, 15, 15, "gs0")                              # mortar
        for ri, y0 in enumerate((0, 8)):
            off = 0 if (ri + variant) % 2 == 0 else 8
            for bx in (off - 8, off, off + 8):
                x0, x1 = max(bx + 1, 0), min(bx + 7, 15)
                if x1 < x0:
                    continue
                s.rect(x0, y0 + 1, x1, y0 + 6, "gs2")
                s.hline(x0, x1, y0 + 1, "gs3")
                s.hline(x0, x1, y0 + 6, "gs1")
                if r.random() < 0.5:
                    s.px(x0 + r.randrange(0, max(1, x1 - x0)), y0 + 3 + r.randrange(0, 2), "gs1")
                if r.random() < 0.3:
                    s.px(x0 + r.randrange(0, max(1, x1 - x0)), y0 + 2, "gs4")
        return s

    def wall_cap():
        s = Sprite(16, 16)
        s.rect(0, 0, 15, 15, "gs1")
        s.hline(0, 15, 0, "gs0")
        s.rect(0, 11, 15, 15, "gs2")
        s.hline(0, 15, 11, "gs3")
        s.hline(0, 15, 15, "gs0")
        for x in (3, 11):
            s.vline(x, 1, 10, "gs0")
        return s

    def plinth():
        s = Sprite(16, 16)
        s.rect(0, 0, 15, 15, "gs2")
        s.hline(0, 15, 0, "gs4")
        s.hline(0, 15, 1, "gs3")
        s.rect(0, 12, 15, 15, "gs0")
        s.hline(0, 15, 11, "gs1")
        for x in (0, 8):
            s.vline(x + 1, 2, 10, "gs1")
        return s

    def cobweb(flip):
        s = Sprite(14, 14)
        for i in range(14):
            s.px(i, 0, "web") if i % 2 == 0 else None
            s.px(0, i, "web") if i % 2 == 0 else None
            s.px(i, i, "web") if i < 12 else None
        for k in (4, 8, 12):
            for t in range(k):
                x, y = t, k - 1 - t
                s.px(x, y, "web") if (x + y) % 2 == 0 else None
        if flip:
            s.img = s.img.transpose(0)   # mirror horizontally
        return s

    # ── the hearth: base (small fire), mid (full fire), max (blue-gold) ──────
    def hearth(kind, frame):
        w, h = 48, 56
        s = Sprite(w, h)
        mid = w // 2
        # chimney breast up the wall
        s.rect(10, 0, 37, 30, "gs2")
        s.vline(10, 0, 30, "gs3"); s.vline(11, 0, 30, "gs3")
        s.vline(36, 0, 30, "gs1"); s.vline(37, 0, 30, "gs0")
        for y in range(2, 30, 6):
            s.hline(12, 35, y, "gs1")
            for x in range(14 + (y // 6 % 2) * 5, 36, 10):
                s.vline(x, y, min(y + 5, 30), "gs1")
        # mantle slab
        s.rect(2, 30, 45, 34, "gs3")
        s.hline(2, 45, 30, "gs4")
        s.hline(2, 45, 34, "gs0")
        # side piers and the firebox
        s.rect(4, 35, 11, 55, "gs2"); s.vline(4, 35, 55, "gs3"); s.vline(11, 35, 55, "gs1")
        s.rect(36, 35, 43, 55, "gs2"); s.vline(36, 35, 55, "gs3"); s.vline(43, 35, 55, "gs1")
        s.rect(12, 38, 35, 55, "gs0")                            # the opening
        s.rect(13, 36, 34, 37, "gs1")
        s.rect(14, 35, 33, 35, "gs1")
        s.rect(3, 52, 44, 55, "gs3")                             # the hearthstone
        s.hline(3, 44, 52, "gs4")
        s.hline(3, 44, 55, "gs0")
        if kind == "mid":
            s.hline(2, 45, 31, "gold0")
            for x in range(6, 42, 6):
                s.px(x, 32, "gold0"); s.px(x + 1, 32, "gold")
        if kind == "max":
            s.hline(2, 45, 31, "gold")
            s.hline(2, 45, 33, "gold0")
            for x in range(5, 44, 4):
                s.px(x, 32, "gold1")
            s.rect(mid - 5, 8, mid + 4, 22, "red0")             # a crest on the chimney breast
            s.rect(mid - 4, 9, mid + 3, 21, "red")
            s.rect(mid - 1, 11, mid, 18, "gold")
            s.px(mid - 2, 14, "gold"); s.px(mid + 1, 14, "gold")
            s.hline(mid - 5, mid + 4, 8, "gold"); s.hline(mid - 5, mid + 4, 22, "gold0")
            for x in (6, 38):                                    # gold caps on the piers
                s.rect(x - 2, 35, x + 5, 36, "gold0")
        # logs
        s.rect(15, 51, 32, 53, "wd1"); s.hline(15, 32, 51, "wd2"); s.hline(15, 32, 53, "wd0")
        if frame == 2:                                           # a cold hearth: ash and dead embers
            s.rect(17, 49, 30, 51, "gs1"); s.px(20, 49, "dust"); s.px(26, 50, "dust")
            return s.outline()
        if kind == "base":
            fl, hi = (("ember", "ember1"), ("ember", "ember0"))[frame]
            s.rect(21, 46 - frame, 26, 51, fl); s.rect(22, 44 - frame, 25, 47, hi)
            s.px(23, 42 - frame, "ember1")
        elif kind == "mid":
            top = 38 + frame
            s.rect(16, 46, 31, 51, "ember0"); s.rect(18, top + 3, 29, 51, "ember"); s.rect(21, top + 1, 26, 49, "ember1")
            s.px(20, top + 2, "ember"); s.px(27, top + 4 - frame, "ember")
        else:
            top = 38 + frame
            s.rect(16, 46, 31, 51, "bf0"); s.rect(18, top + 3, 29, 51, "bf1"); s.rect(21, top + 1, 26, 49, "bf2")
            s.rect(22, 47, 25, 51, "bf3"); s.px(20, top + 2, "bf1"); s.px(27, top + 4 - frame, "bf1")
            s.px(23, top - 1 + frame, "bf2")
        return s.outline()

    # ── windows and banners ─────────────────────────────────────────────────
    def window(kind):
        w, h = 20, 40
        s = Sprite(w, h)
        s.rect(1, 6, 18, 39, "gs3")
        for i, (x0, x1) in enumerate(((5, 14), (3, 16), (2, 17))):
            s.rect(x0, 2 + i * 2, x1, 3 + i * 2, "gs3")
        s.rect(4, 3, 15, 5, "gs3")
        s.rect(7, 1, 12, 2, "gs3")
        s.rect(3, 8, 16, 35, "gs0")                              # the opening
        s.rect(4, 6, 15, 7, "gs0"); s.rect(6, 4, 13, 5, "gs0"); s.rect(8, 3, 11, 3, "gs0")
        if kind == "plain":
            s.rect(4, 8, 15, 35, "nv0")
            s.rect(5, 7, 14, 7, "nv0"); s.rect(7, 5, 12, 6, "nv0")
            s.vline(9, 4, 35, "gs2"); s.vline(10, 4, 35, "gs2")  # a mullion
            s.hline(4, 15, 20, "gs2")
            s.px(6, 12, "nv2"); s.px(12, 26, "nv2"); s.px(13, 27, "nv1")
        else:
            panes = [("red0", "red"), ("gl0", "gl1"), ("gold0", "gold"), ("gp0", "gp1"), ("gl0", "gl2"), ("red0", "red1")]
            s.rect(4, 8, 15, 35, "gl0")
            s.rect(5, 7, 14, 7, "gl0"); s.rect(7, 5, 12, 6, "gl0")
            k = 0
            for y0 in (8, 16, 24):
                for x0 in (4, 10):
                    dark, light = panes[k % len(panes)]
                    s.rect(x0, y0, x0 + 5, y0 + 6, dark)
                    s.rect(x0 + 1, y0 + 1, x0 + 4, y0 + 5, light)
                    s.px(x0 + 1, y0 + 1, "gold1")
                    k += 1
            s.rect(7, 5, 12, 6, "gold0"); s.px(9, 5, "gold1")
            s.vline(9, 4, 35, "gs1"); s.vline(10, 4, 35, "gs1")
            for y in (15, 23):
                s.hline(4, 15, y, "gs1")
        s.rect(0, 35, 19, 39, "gs3")                             # sill
        s.hline(0, 19, 35, "gs4")
        s.hline(0, 19, 39, "gs0")
        return s.outline()

    def banner(kind):
        w, h = 14, 36
        s = Sprite(w, h)
        s.rect(0, 0, 13, 1, "wd1"); s.hline(0, 13, 0, "wd2")
        s.px(0, 0, "gold"); s.px(13, 0, "gold")
        body = "red" if kind == "crest" else "wd1"
        dark = "red0" if kind == "crest" else "wd0"
        light = "red1" if kind == "crest" else "wd2"
        s.rect(1, 2, 12, 28, body)
        s.vline(1, 2, 28, dark); s.vline(12, 2, 28, dark); s.vline(2, 2, 28, light)
        for i in range(6):
            s.hline(1 + i, 12 - i, 29 + i, body)
            s.px(1 + i, 29 + i, dark); s.px(12 - i, 29 + i, dark)
        if kind == "crest":
            s.rect(5, 8, 8, 17, "gold")                           # a gold phoenix-like crest
            s.rect(3, 11, 10, 13, "gold0")
            s.rect(6, 5, 7, 9, "gold1")
            s.px(4, 10, "gold"); s.px(9, 10, "gold"); s.px(5, 18, "gold0"); s.px(8, 18, "gold0")
            s.hline(1, 12, 3, "gold0")
            s.hline(1, 12, 26, "gold0")
        else:                                                      # torn and faded
            for x, y in ((4, 9), (5, 9), (8, 15), (3, 20), (9, 22), (6, 25)):
                s.px(x, y, "wd0")
            for x in (3, 6, 9):
                s.vline(x, 29 + abs(x - 6) // 2, 34, "line")
            s.px(7, 12, "gs2"); s.px(2, 16, "gs2")
        return s.outline()

    # ── doors ───────────────────────────────────────────────────────────────
    def door(kind):
        w, h = 40, 52
        s = Sprite(w, h)
        frame, frame_hi = ("gs3", "gs4") if kind == "wood" else ("gold0", "gold")
        s.rect(2, 12, 37, 51, "gs2")
        for i, (x0, x1) in enumerate(((10, 29), (6, 33), (4, 35), (3, 36))):
            s.rect(x0, 3 + i * 3, x1, 5 + i * 3, "gs2")
        s.rect(2, 12, 37, 13, "gs2")
        # the arch ring
        for y in range(8, 51):
            s.px(3, y, "gs1")
            s.px(36, y, "gs0")
        s.rect(7, 12, 32, 51, frame if kind == "gold" else "gs0")
        # door leaves
        d0, d1, d2 = ("wd0", "wd1", "wd2") if kind == "wood" else ("gold0", "wd1", "gold")
        s.rect(8, 14, 31, 51, d1)
        s.rect(10, 11, 29, 13, d1); s.rect(14, 9, 25, 10, d1)
        s.rect(8, 14, 31, 14, d2)
        s.vline(19, 9, 51, d0); s.vline(20, 9, 51, d0)           # the split
        for y in (20, 36):                                       # iron bands / gold bands
            s.hline(8, 31, y, "mt0" if kind == "wood" else "gold")
            s.hline(8, 31, y + 1, "mt1" if kind == "wood" else "gold1")
        for x in (9, 12, 27, 30):
            s.px(x, 20, "mt2" if kind == "wood" else "gold1")
            s.px(x, 36, "mt2" if kind == "wood" else "gold1")
        s.rect(16, 30, 17, 32, "mt1" if kind == "wood" else "gold1")   # ring pulls
        s.rect(22, 30, 23, 32, "mt1" if kind == "wood" else "gold1")
        if kind == "gold":
            for y in range(16, 50, 4):
                s.px(13, y, "gold"); s.px(26, y, "gold")
            for x in range(10, 30, 3):
                s.px(x, 25, "gold0")
            s.rect(18, 9, 21, 10, "gold1")                       # keystone
        else:
            s.rect(18, 7, 21, 9, "gs3")
        s.hline(2, 37, 51, "gs0")
        return s.outline()

    # ── furniture ───────────────────────────────────────────────────────────
    def bench(broken):
        w, h = 30, 14
        s = Sprite(w, h)
        top = 2 + (1 if broken else 0)
        s.rect(1, top, 28, top + 4, "wd2"); s.hline(1, 28, top, "wd3")
        s.rect(1, top + 5, 28, top + 7, "wd1"); s.hline(1, 28, top + 7, "wd0")
        for x in (3, 25):
            s.rect(x, top + 8, x + 2, 13, "wd1"); s.vline(x, top + 8, 13, "wd2")
        if broken:
            s.rect(14, top, 15, top + 7, "wd0")                   # a split plank
            s.px(13, top + 1, "wd0"); s.px(16, top + 6, "wd0")
            s.rect(25, top + 8, 27, 13, "line")
        return s.outline()

    def table(kind):
        w, h = (24, 18) if kind == "small" else (64, 30)
        s = Sprite(w, h)
        if kind == "small":
            s.rect(1, 1, 22, 8, "wd2"); s.hline(1, 22, 1, "wd3")
            s.rect(1, 9, 22, 11, "wd1"); s.hline(1, 22, 11, "wd0")
            for x in (2, 19):
                s.rect(x, 12, x + 2, 17, "wd1")
            s.vline(10, 2, 8, "wd1")
            return s.outline()
        s.rect(1, 1, 62, 14, "wd2"); s.hline(1, 62, 1, "wd3")
        s.rect(4, 3, 59, 12, "red0")                              # a crimson runner cloth
        s.rect(5, 4, 58, 11, "red")
        s.hline(5, 58, 4, "red1")
        s.hline(4, 59, 3, "gold0"); s.hline(4, 59, 12, "gold0")
        s.rect(1, 15, 62, 19, "wd1"); s.hline(1, 62, 19, "wd0")
        for x in (3, 29, 57):
            s.rect(x, 20, x + 3, 29, "wd1"); s.vline(x, 20, 29, "wd2")
        for gx in (12, 22, 42, 50):                               # goblets
            s.rect(gx, 6, gx + 1, 8, "gold"); s.px(gx, 5, "gold1")
        for cx in (30, 34):                                       # candles
            s.rect(cx, 4, cx, 8, "wax"); s.px(cx, 3, "ember1"); s.px(cx, 2, "ember")
        return s.outline()

    def chair(side):
        w, h = 14, 24
        s = Sprite(w, h)
        s.rect(2, 1, 11, 11, "wd1"); s.rect(2, 1, 11, 1, "wd2")   # tall back
        s.rect(4, 3, 9, 9, "red0"); s.rect(5, 4, 8, 8, "red")
        s.rect(1, 12, 12, 15, "wd2"); s.hline(1, 12, 12, "wd3")    # seat
        s.rect(2, 13, 11, 14, "red")
        s.rect(1, 16, 12, 17, "wd1")
        for x in (2, 10):
            s.rect(x, 18, x + 1, 23, "wd1")
        if side == "r":
            s.img = s.img.transpose(0)
        return s.outline()

    def chandelier(frame):
        w, h = 44, 44
        s = Sprite(w, h)
        s.vline(21, 0, 14, "mt1"); s.vline(22, 0, 14, "mt0")    # chain
        for y in range(1, 14, 3):
            s.px(20, y, "mt0"); s.px(23, y, "mt0")
        s.rect(4, 22, 39, 24, "mt0"); s.hline(4, 39, 22, "mt1")   # the ring
        s.rect(8, 25, 35, 25, "mt0")
        s.rect(2, 20, 3, 23, "mt0"); s.rect(40, 20, 41, 23, "mt0")
        for y in range(15, 22):                                   # spokes to the chain
            s.px(21 - (21 - 6) * (y - 15) // 7, y, "mt0")
            s.px(22 + (37 - 22) * (y - 15) // 7, y, "mt0")
        for i, cx in enumerate((5, 12, 19, 25, 32, 38)):
            top = 14 + (i % 2)
            s.rect(cx, top + 3, cx + 1, 21, "wax"); s.px(cx, top + 3, "white")
            s.rect(cx, top - 1 - (frame if i % 2 == 0 else 1 - frame), cx + 1, top + 2, "ember")
            s.px(cx, top - 1 - (frame if i % 2 == 0 else 1 - frame), "ember1")
        s.rect(18, 26, 25, 30, "mt0"); s.px(21, 31, "mt1"); s.px(22, 31, "mt1"); s.px(21, 32, "gold"); s.px(22, 32, "gold")
        return s.outline()

    def knight():
        w, h = 20, 44
        s = Sprite(w, h)
        s.rect(2, 38, 17, 43, "gs3"); s.hline(2, 17, 38, "gs4"); s.hline(2, 17, 43, "gs0")   # plinth
        s.rect(6, 26, 13, 37, "mt0"); s.rect(6, 26, 8, 37, "mt1"); s.vline(10, 30, 37, "line")  # legs
        s.rect(5, 12, 14, 26, "mt0"); s.rect(5, 12, 7, 26, "mt1")                                # torso
        s.rect(7, 14, 12, 24, "red"); s.rect(7, 14, 8, 24, "red1"); s.rect(9, 16, 10, 20, "gold")  # tabard
        s.rect(2, 12, 6, 16, "mt1"); s.rect(13, 12, 17, 16, "mt0")                               # pauldrons
        s.rect(6, 3, 13, 11, "mt0"); s.rect(6, 3, 8, 11, "mt1")                                  # helm
        s.rect(8, 7, 12, 8, "line")
        s.rect(9, 0, 10, 3, "red"); s.px(9, 0, "red1")                                           # plume
        s.vline(18, 4, 38, "wd1"); s.px(18, 3, "mt2"); s.px(17, 4, "mt1"); s.px(19, 4, "mt1")   # a spear
        s.rect(1, 17, 6, 26, "red0"); s.rect(2, 18, 5, 25, "gold0"); s.px(3, 20, "gold1")       # a shield
        return s.outline()

    def torch(frame):
        w, h = 12, 28
        s = Sprite(w, h)
        s.rect(5, 12, 6, 24, "wd1"); s.vline(5, 12, 24, "wd2")
        s.rect(3, 10, 8, 13, "mt0"); s.hline(3, 8, 10, "mt1")
        s.rect(2, 24, 9, 26, "mt0"); s.hline(2, 9, 24, "mt1")
        s.rect(4, 6 - frame, 7, 10, "ember0")
        s.rect(4, 4 - frame, 7, 8, "ember")
        s.rect(5, 2 - frame, 6, 6, "ember1")
        s.px(5, 1 - frame, "ember1")
        return s.outline()

    def barrel():
        s = Sprite(18, 20)
        s.rect(2, 2, 15, 17, "wd1"); s.vline(2, 2, 17, "wd2"); s.vline(3, 2, 17, "wd2"); s.vline(15, 2, 17, "wd0")
        s.hline(2, 15, 6, "mt0"); s.hline(2, 15, 13, "mt0")
        s.hline(3, 14, 2, "wd3"); s.hline(3, 14, 17, "wd0")
        return s.outline()

    pieces["floor_flag_0"] = flag(0)
    pieces["floor_flag_1"] = flag(1)
    pieces["floor_flag_2"] = flag(2)
    pieces["floor_chk_0"] = checker(0)
    pieces["floor_chk_1"] = checker(1)
    pieces["wall_s_0"] = stone_wall(0)
    pieces["wall_s_1"] = stone_wall(1)
    pieces["wall_cap"] = wall_cap()
    pieces["plinth_s"] = plinth()
    pieces["cobweb_l"] = cobweb(False)
    pieces["cobweb_r"] = cobweb(True)
    for kind in ("base", "mid", "max"):
        for f in (0, 1, 2):
            name = {"base": "hearthb", "mid": "hearthm", "max": "hearthg"}[kind]
            pieces[f"{name}_{f if f < 2 else 'out'}"] = hearth(kind, f)
    pieces["window_plain"] = window("plain")
    pieces["window_glass"] = window("glass")
    pieces["banner_torn"] = banner("torn")
    pieces["banner_crest"] = banner("crest")
    pieces["door_wood"] = door("wood")
    pieces["door_gold"] = door("gold")
    pieces["bench"] = bench(False)
    pieces["bench_broken"] = bench(True)
    pieces["table_small"] = table("small")
    pieces["table_long"] = table("long")
    pieces["chair_l"] = chair("l")
    pieces["chair_r"] = chair("r")
    for f in (0, 1):
        pieces[f"chandelier_{f}"] = chandelier(f)
        pieces[f"torch_{f}"] = torch(f)
    pieces["knight"] = knight()
    pieces["barrel"] = barrel()


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent))
    import make_tiles as mt
    from PIL import Image
    pieces = {}
    add(pieces, mt.Sprite, mt.C, mt.noise)
    names = [n for n in pieces]
    scale = 4
    pad = 6
    x = y = pad
    row_h = 0
    width = 1500
    canvas = Image.new("RGBA", (width, 1400), (58, 56, 80, 255))
    for n in names:
        im = pieces[n].img.resize((pieces[n].w * scale, pieces[n].h * scale), Image.NEAREST)
        if x + im.width + pad > width:
            x = pad
            y += row_h + pad
            row_h = 0
        canvas.alpha_composite(im, (x, y))
        x += im.width + pad
        row_h = max(row_h, im.height)
    canvas.crop((0, 0, width, y + row_h + pad)).save(sys.argv[1])
    print("wrote", sys.argv[1], len(names), "pieces")
