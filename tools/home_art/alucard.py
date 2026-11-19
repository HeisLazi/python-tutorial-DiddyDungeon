#!/usr/bin/env python3
"""Alucard-based hunter, 32x48, drawn in shaped and cel-shaded forms (pixlib).

Four layers so cloth and hair move on their own:
  cape   red-lined black cape behind the body (sways)
  body   head, collar, cravat, coat, waistcoat, arms, legs, boots (walk cycle)
  gown   the coat skirt over the legs (swings against the step)
  hair   the avatar's long wavy hair, over everything (flows, 4 frames)

Style reference: the Castlevania roster sprites (Grimoire of Souls, Nam-Pixel).
Run directly to render a preview sheet:  python3 tools/home_art/alucard.py <out.png>
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from pixlib import Canvas  # noqa: E402

W, H = 32, 48

PAL = {
    "line": (14, 10, 24),
    # the black coat
    "ck0": (10, 10, 18), "ck1": (26, 26, 42), "ck2": (46, 46, 70), "ck3": (84, 84, 118),
    # gold piping
    "g0": (150, 96, 24), "g1": (214, 148, 48), "g2": (255, 208, 104),
    # the cape's red lining
    "r0": (84, 12, 30), "r1": (140, 24, 46), "r2": (200, 44, 62), "r3": (244, 104, 98),
    # waistcoat, silver, cravat
    "w0": (48, 52, 74), "w1": (92, 98, 128), "w2": (146, 154, 184),
    "s0": (84, 90, 118), "s1": (158, 166, 192), "s2": (224, 230, 244),
    "cr0": (176, 182, 206), "cr1": (232, 234, 246),
    # leather
    "l0": (58, 34, 24), "l1": (102, 62, 36), "l2": (150, 100, 58),
    # the avatar: umber skin, dark wavy hair, a goatee
    "sk0": (98, 58, 38), "sk1": (144, 90, 54), "sk2": (188, 124, 80), "sk3": (216, 152, 102),
    "h0": (14, 12, 26), "h1": (34, 30, 58), "h2": (66, 60, 104), "h3": (110, 104, 156),
    # boots
    "b0": (12, 10, 20), "b1": (30, 28, 46), "b2": (62, 60, 88),
    "white": (242, 239, 230), "iris": (44, 26, 22), "lip": (120, 62, 54),
}

POSES = ("stand", "stepa", "stepb")


def pv(pose):
    return {
        "lift": {"stand": (0, 0), "stepa": (3, 0), "stepb": (0, 3)}[pose],
        "arm": {"stand": (0, 0), "stepa": (2, -2), "stepb": (-2, 2)}[pose],
        "gown": {"stand": 0, "stepa": 2, "stepb": -2}[pose],
    }


# ── the body ────────────────────────────────────────────────────────────────
def front_body(pose):
    s = Canvas(W, H, PAL)
    v = pv(pose)
    # tall boots with folded silver cuffs, under black trousers
    for x0, up in ((10, v["lift"][0]), (17, v["lift"][1])):
        s.rows(32, 38 - up, lambda y, x0=x0: x0 + 1, lambda y, x0=x0: x0 + 4, ("ck2", "ck1", "ck0"))
        s.rows(38 - up, 46 - up, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 5, ("b2", "b1", "b0"))
        s.rows(38 - up, 40 - up, lambda y, x0=x0: x0 - 1, lambda y, x0=x0: x0 + 6, ("s2", "s1", "s0"))     # the folded cuff
        s.hline(x0 - 1, x0 + 6, 40 - up, "s0")
        s.px(x0 + 1, 42 - up, "b2"); s.px(x0 + 1, 43 - up, "b2")
        s.rect(x0 - 1, 46 - up, x0 + 5, 47 - up, "b0")                                                      # the sole
        s.px(x0 - 2, 47 - up, "b0")
    # the coat: broad shoulders, a lit left, tapering to the waist
    s.rows(14, 28, lambda y: 8 + min(3, max(0, (y - 17) // 3)), lambda y: 23 - min(3, max(0, (y - 17) // 3)), ("ck2", "ck1", "ck0"), split=(0.2, 0.8))
    s.hline(9, 22, 14, "ck3"); s.hline(8, 23, 15, "ck2")
    # the waistcoat between the lapels, with silver buckles
    s.rows(15, 27, lambda y: 13, lambda y: 18, ("w2", "w1", "w0"), split=(0.22, 0.7))
    for y in (18, 21, 24):
        s.rect(14, y, 17, y + 1, "s1"); s.hline(14, 17, y, "s2"); s.hline(14, 17, y + 1, "s0")
    s.vline(12, 15, 28, "g1"); s.vline(19, 15, 28, "g0")                                                  # gold lapel piping
    s.vline(11, 16, 28, "ck3"); s.vline(20, 16, 28, "ck0")
    # the belt
    s.rows(26, 27, lambda y: 11, lambda y: 20, ("l2", "l1", "l0"))
    s.rect(14, 26, 17, 27, "g1"); s.px(14, 26, "g2"); s.px(15, 27, "g0"); s.px(16, 27, "g0")
    # the cravat, neck and the tall collar wings with a crimson lining
    s.rows(12, 17, lambda y: 14 + (y - 12) // 3, lambda y: 17 - (y - 12) // 3, ("cr1", "cr1", "cr0"))
    s.rows(11, 13, lambda y: 14, lambda y: 17, ("sk1", "sk1", "sk0"))
    for side in (0, 1):
        def X(x, side=side):
            return x if side == 0 else W - 1 - x
        for y in range(6, 17):
            lo = int(round(6.0 - (y - 6) * 0.1))
            hi = 11 if y > 8 else 9 + (y - 6)
            for x in range(lo, hi + 1):
                t = (x - lo) / max(1, hi - lo)
                col = "ck2" if t < 0.3 else ("ck1" if t < 0.7 else "r1")
                if x == lo:
                    col = "g1" if side == 0 else "g0"
                if x == hi and y > 8:
                    col = "r2" if side == 0 else "r0"
                s.px(X(x), y, col)
    # the head: small and finely drawn; brows, eyes, nose, mouth and a short goatee
    face = {5: (13, 18), 6: (12, 19), 7: (12, 19), 8: (12, 19), 9: (12, 19), 10: (13, 18), 11: (14, 17)}
    for y, (xl, xr) in face.items():
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("sk3", "sk2", "sk1"), split=(0.25, 0.62))
    s.hline(13, 14, 7, "h0"); s.hline(17, 18, 7, "h0")
    s.px(13, 8, "white"); s.px(14, 8, "iris"); s.px(17, 8, "iris"); s.px(18, 8, "white")
    s.px(15, 9, "sk1"); s.px(16, 9, "sk0")
    s.hline(15, 16, 10, "lip")
    s.rect(14, 11, 17, 11, "h1"); s.hline(15, 16, 12, "h1")
    # the arms: coat sleeves banded in gold, black gloves
    for x0, dy, side in ((4, v["arm"][0], 0), (24, v["arm"][1], 1)):
        s.rows(15 + dy, 28 + dy, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 3, ("ck2", "ck1", "ck0") if side == 0 else ("ck1", "ck1", "ck0"))
        for yy in (25, 27, 28):
            s.hline(x0, x0 + 3, yy + dy, "g1" if side == 0 else "g0")
        s.rows(29 + dy, 33 + dy, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 3, ("b2", "b1", "b0"))
        s.px(x0 + 1, 30 + dy, "b2")
    return s.outline()


def front_gown(pose):
    s = Canvas(W, H, PAL)
    g = pv(pose)["gown"]
    # the long coat skirt flaring from the belt, open at the front
    for y in range(28, 39):
        flare = (y - 28) * 0.45
        xl = int(round(10 - flare + (g if y > 35 else 0)))
        xr = int(round(21 + flare + (g if y > 35 else 0)))
        gap_l, gap_r = 14, 17
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, gap_l=gap_l: gap_l - 1, ("ck2", "ck1", "ck0"), split=(0.2, 0.8))
        s.rows(y, y, lambda _y, gap_r=gap_r: gap_r + 1, lambda _y, xr=xr: xr, ("ck1", "ck0", "ck0"), split=(0.2, 0.8))
        s.px(gap_l, y, "r1" if y > 29 else "r0"); s.px(gap_r, y, "r1" if y > 29 else "r0")
        s.px(xl, y, "g1"); s.px(xr, y, "g0")
    for x in range(7 + g, 25 + g, 3):
        s.px(x, 39, "ck1"); s.px(x + 1, 39, "ck0")
    return s.outline()


def front_cape(phase):
    s = Canvas(W, H, PAL)
    sw = [0, 1, 2, 1][phase % 4]
    sw2 = [0, -1, -2, -1][phase % 4]
    # the cape seen from the inside: crimson lining with a black edge, swaying
    for y in range(14, 45):
        spread = (y - 14) * 0.16
        xl = int(round(7 - spread + (sw * (y - 26) / 12.0 if y > 26 else 0)))
        xr = int(round(24 + spread + (sw2 * (y - 26) / 12.0 if y > 26 else 0)))
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("r2", "r1", "r0"), split=(0.25, 0.7), rim=False)
        s.rect(xl, y, xl + 1, y, "ck1"); s.rect(xr - 1, y, xr, y, "ck0")
        if y % 5 == 0:
            s.hline(xl + 4, xl + 5, y, "r3")
    for x in range(5, 28, 2):                                  # ragged hem
        s.px(x + (sw if x < 16 else sw2), 44, "r0")
    s.hline(6, 25, 43, "ck1")
    return s.outline()


def front_hair(phase):
    """Long wavy hair: a parted crown, bangs, and locks that flow with the phase."""
    s = Canvas(W, H, PAL)
    cap = {1: (13, 18), 2: (11, 20), 3: (10, 21), 4: (10, 21)}
    for y, (xl, xr) in cap.items():
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("h2", "h1", "h0"), split=(0.3, 0.7))
    s.rows(5, 5, lambda y: 10, lambda y: 12, ("h2", "h1", "h0")); s.rows(5, 5, lambda y: 19, lambda y: 21, ("h2", "h1", "h0"))
    s.rows(6, 7, lambda y: 10, lambda y: 11, ("h2", "h1", "h0")); s.rows(6, 7, lambda y: 20, lambda y: 21, ("h2", "h1", "h0"))
    s.line((12, 2), (11, 4), "h3"); s.line((15, 1), (13, 3), "h3"); s.px(18, 2, "h3")
    # the side locks: two on each side, swept past the shoulders, flowing
    for x0, ln, amp, ph in ((11, 15, 1.6, 0.0), (9, 11, 1.3, 1.2), (20, 15, 1.6, 0.8), (22, 11, 1.3, 2.0)):
        def w(i, amp=amp, ph=ph):
            return amp * math.sin(phase * math.pi / 2 + ph + i * 0.30) * min(1.0, i / 8.0)
        s.strand(x0, 6, ln, (2.6, 1.0), w, ("h2", "h1", "h0"))
    return s.outline()


# ── left profile (the right-facing rows are mirrors) ────────────────────────
def side_body(pose):
    s = Canvas(W, H, PAL)
    step = {"stand": 0, "stepa": 1, "stepb": -1}[pose]
    for lead, tones in ((-1, ("b1", "b0", "b0")), (1, ("b2", "b1", "b0"))):
        d = step * lead
        x0 = 12 - d * 3
        up = 2 if d > 0 else 0
        s.rows(32, 38 - up, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 4, ("ck2", "ck1", "ck0"))
        s.rows(38 - up, 46 - up, lambda y, x0=x0: x0 - 1, lambda y, x0=x0: x0 + 5, tones)
        s.rows(38 - up, 40 - up, lambda y, x0=x0: x0 - 2, lambda y, x0=x0: x0 + 6, ("s2", "s1", "s0"))
        s.hline(x0 - 2, x0 + 6, 40 - up, "s0")
        s.rect(x0 - 3, 45 - up, x0 - 1, 47 - up, "b0"); s.rect(x0 - 1, 46 - up, x0 + 5, 47 - up, "b0")          # toe and sole
    # the torso in profile, with the waistcoat edge at the front
    s.rows(14, 28, lambda y: 11, lambda y: 21, ("ck2", "ck1", "ck0"), split=(0.22, 0.8))
    s.rows(15, 27, lambda y: 11, lambda y: 13, ("w2", "w1", "w0"))
    s.vline(13, 15, 28, "g1")
    for y in (18, 21, 24):
        s.hline(11, 13, y, "s2"); s.hline(11, 13, y + 1, "s0")
    s.rows(26, 27, lambda y: 11, lambda y: 20, ("l2", "l1", "l0"))
    s.rect(11, 26, 13, 27, "g1")
    # the tall collar wing behind the head, its lining toward the face
    for y in range(6, 17):
        lo = 17
        hi = 22 - (1 if y < 9 else 0)
        for x in range(lo, hi + 1):
            col = "r1" if x == lo else ("ck1" if x < hi - 1 else "g0")
            if x == lo + 1:
                col = "ck2"
            s.px(x, y, col)
    # the cravat, neck and the head in profile
    s.rows(12, 17, lambda y: 12, lambda y: 16 - (y - 12) // 4, ("cr1", "cr1", "cr0"))
    s.rows(11, 13, lambda y: 14, lambda y: 17, ("sk1", "sk1", "sk0"))
    face = {5: (13, 17), 6: (12, 17), 7: (11, 17), 8: (11, 17), 9: (11, 17), 10: (12, 17), 11: (13, 16)}
    for y, (xl, xr) in face.items():
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("sk3", "sk2", "sk1"), split=(0.3, 0.7))
    s.hline(13, 15, 7, "h0")
    s.px(13, 8, "iris"); s.px(14, 8, "white")
    s.px(11, 9, "sk1"); s.px(11, 8, "sk2")
    s.px(12, 10, "lip")
    s.rect(12, 11, 13, 12, "h1")
    # the swinging near arm in a banded sleeve and a black glove
    ax = 13 + step * 3
    s.rows(15, 28, lambda y: ax, lambda y: ax + 3, ("ck3", "ck2", "ck1"))
    for yy in (25, 27, 28):
        s.hline(ax, ax + 3, yy, "g1")
    s.rows(29, 33, lambda y: ax, lambda y: ax + 3, ("b2", "b1", "b0"))
    return s.outline()


def side_gown(pose):
    s = Canvas(W, H, PAL)
    g = {"stand": 0, "stepa": 2, "stepb": -2}[pose]
    for y in range(28, 39):
        flare = (y - 28) * 0.4
        xl = int(round(10 - flare - (g if y > 35 else 0)))
        xr = int(round(21 + flare * 1.3 + (g if y > 35 else 0)))
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("ck2", "ck1", "ck0"), split=(0.2, 0.8))
        s.px(xl, y, "g1"); s.px(xl + 2, y, "r1" if y > 30 else "r0")
    for x in range(8 - g, 27 + g, 3):
        s.px(x, 39, "ck1")
    return s.outline()


def side_cape(phase):
    """The cape streams out behind him: red lining along its front edge, black outside."""
    s = Canvas(W, H, PAL)
    roll = [0, 1, 2, 1][phase % 4]
    for y in range(14, 44):
        reach = 3 + min(11, (y - 14) * 0.45) + (roll * (y - 24) / 10.0 if y > 24 else 0)
        xl = 17
        xr = int(round(min(W - 1, 18 + reach)))
        s.rows(y, y, lambda _y: xl, lambda _y, xr=xr: xr, ("ck2", "ck1", "ck0"), split=(0.3, 0.8), rim=False)
        s.rect(xl, y, xl + 1, y, "r1")
        if y > 20:
            s.px(xr - 1, y, "g0")
        if y % 6 == 0:
            s.hline(xl + 3, xl + 5, y, "ck2")
    for x in range(18, 30, 2):
        s.px(x, 43 + (roll if x > 22 else 0), "r0")
    s.hline(18, 28 + roll, 42, "r1")
    return s.outline()


def side_hair(phase):
    """The crown and the long hair streaming back with the wind."""
    s = Canvas(W, H, PAL)
    cap = {1: (13, 19), 2: (12, 21), 3: (12, 22), 4: (12, 22), 5: (12, 22), 6: (14, 22)}
    for y, (xl, xr) in cap.items():
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("h2", "h1", "h0"), split=(0.3, 0.7))
    s.rows(6, 8, lambda y: 11, lambda y: 12, ("h2", "h1", "h0"))       # a lock over the brow
    s.line((14, 2), (12, 5), "h3"); s.line((17, 1), (15, 4), "h3")
    for x0, ln, amp, ph, lean in ((19, 20, 1.4, 0.0, 0.16), (21, 16, 1.2, 1.1, 0.2), (17, 14, 1.0, 2.0, 0.14)):
        def w(i, amp=amp, ph=ph, lean=lean):
            return lean * i + amp * math.sin(phase * math.pi / 2 + ph + i * 0.30) * min(1.0, i / 8.0)
        s.strand(x0, 6, ln, (3.2, 1.2), w, ("h2", "h1", "h0"))
    return s.outline()


# ── back ────────────────────────────────────────────────────────────────────
def back_body(pose):
    s = Canvas(W, H, PAL)
    v = pv(pose)
    for x0, up in ((10, v["lift"][0]), (17, v["lift"][1])):
        s.rows(32, 38 - up, lambda y, x0=x0: x0 + 1, lambda y, x0=x0: x0 + 4, ("ck1", "ck1", "ck0"))
        s.rows(38 - up, 46 - up, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 5, ("b2", "b1", "b0"))
        s.rows(38 - up, 40 - up, lambda y, x0=x0: x0 - 1, lambda y, x0=x0: x0 + 6, ("s2", "s1", "s0"))
        s.hline(x0 - 1, x0 + 6, 40 - up, "s0")
        s.rect(x0 - 1, 46 - up, x0 + 5, 47 - up, "b0")
    s.rows(14, 28, lambda y: 8 + min(3, max(0, (y - 17) // 3)), lambda y: 23 - min(3, max(0, (y - 17) // 3)), ("ck2", "ck1", "ck0"), split=(0.18, 0.78))
    s.hline(9, 22, 14, "ck3")
    s.rows(26, 27, lambda y: 11, lambda y: 20, ("l2", "l1", "l0"))
    for side in (0, 1):
        def X(x, side=side):
            return x if side == 0 else W - 1 - x
        for y in range(6, 17):
            lo = int(round(6.0 - (y - 6) * 0.1))
            hi = 11
            for x in range(lo, hi + 1):
                t = (x - lo) / max(1, hi - lo)
                s.px(X(x), y, "g1" if x == lo and side == 0 else ("g0" if x == lo else ("ck2" if t < 0.4 else "ck1")))
    s.rows(11, 14, lambda y: 13, lambda y: 18, ("sk1", "sk1", "sk0"))
    for x0, dy, side in ((4, v["arm"][0], 0), (24, v["arm"][1], 1)):
        s.rows(15 + dy, 28 + dy, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 3, ("ck2", "ck1", "ck0") if side == 0 else ("ck1", "ck1", "ck0"))
        for yy in (25, 27, 28):
            s.hline(x0, x0 + 3, yy + dy, "g1" if side == 0 else "g0")
        s.rows(29 + dy, 33 + dy, lambda y, x0=x0: x0, lambda y, x0=x0: x0 + 3, ("b2", "b1", "b0"))
    return s.outline()


def back_gown(pose):
    return Canvas(W, H, PAL).outline()


def back_cape(phase):
    """Seen from behind the cape hangs in front of the body: black with gold edging."""
    s = Canvas(W, H, PAL)
    sw = [0, 1, 2, 1][phase % 4]
    sw2 = [0, -1, -2, -1][phase % 4]
    for y in range(15, 45):
        spread = (y - 15) * 0.15
        xl = int(round(8 - spread + (sw * (y - 28) / 12.0 if y > 28 else 0)))
        xr = int(round(23 + spread + (sw2 * (y - 28) / 12.0 if y > 28 else 0)))
        s.rows(y, y, lambda _y, xl=xl: xl, lambda _y, xr=xr: xr, ("ck2", "ck1", "ck0"), split=(0.2, 0.75), rim=False)
        s.px(xl, y, "g1"); s.px(xr, y, "g0")
        if y % 6 == 3:
            s.hline(xl + 3, xl + 5, y, "ck3"); s.hline(xr - 5, xr - 3, y, "ck2")
    s.vline(15, 18, 44, "ck0"); s.vline(16, 18, 44, "ck0")
    s.hline(8, 23, 15, "ck3")
    s.hline(6 + sw, 25 + sw2, 43, "r0")
    for x in range(6, 26, 2):
        s.px(x + (sw if x < 16 else sw2), 44, "r1")
    return s.outline()


def back_hair(phase):
    s = Canvas(W, H, PAL)
    s.rows(1, 13, lambda y: 10 + (1 if y < 3 else 0), lambda y: 21 - (1 if y < 3 else 0), ("h2", "h1", "h0"), split=(0.3, 0.75))
    s.rows(14, 22, lambda y: 11, lambda y: 20, ("h2", "h1", "h0"), split=(0.3, 0.75))
    s.line((13, 2), (11, 6), "h3"); s.line((17, 3), (15, 8), "h3")
    for x0, ln, amp, ph in ((12, 12, 1.4, 0.0), (15, 14, 1.6, 0.9), (18, 12, 1.4, 1.8), (20, 9, 1.1, 2.6)):
        def w(i, amp=amp, ph=ph):
            return amp * math.sin(phase * math.pi / 2 + ph + i * 0.30) * min(1.0, i / 7.0)
        s.strand(x0, 22, ln, (3.0, 1.2), w, ("h2", "h1", "h0"))
    return s.outline()


# ── the sheets ──────────────────────────────────────────────────────────────
FACINGS = ["down", "left", "right", "up"]
MAKERS = {
    "down": (front_body, front_gown, front_cape, front_hair),
    "left": (side_body, side_gown, side_cape, side_hair),
    "up": (back_body, back_gown, back_cape, back_hair),
}


def build(out_dir, name="alucard"):
    """Write hunter_<name>_{body,gown,cape,hair}.png (rows: down, left, right, up)."""
    from PIL import ImageOps
    sheets = {
        "body": Image.new("RGBA", (W * 3, H * 4), (0, 0, 0, 0)),
        "gown": Image.new("RGBA", (W * 3, H * 4), (0, 0, 0, 0)),
        "cape": Image.new("RGBA", (W * 4, H * 4), (0, 0, 0, 0)),
        "hair": Image.new("RGBA", (W * 4, H * 4), (0, 0, 0, 0)),
    }
    for r, facing in enumerate(FACINGS):
        body, gown, cape, hair = MAKERS["left" if facing == "right" else facing]
        for kind, fn, count in (("body", body, 3), ("gown", gown, 3), ("cape", cape, 4), ("hair", hair, 4)):
            for c in range(count):
                img = fn(POSES[c] if kind in ("body", "gown") else c).img
                if facing == "right":
                    img = ImageOps.mirror(img)
                sheets[kind].paste(img, (c * W, r * H))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for kind, img in sheets.items():
        img.save(out_dir / f"hunter_{name}_{kind}.png")
    print("wrote", name, "to", out_dir)


def preview_all(path, scale=6):
    """Every facing and pose, all four layers composited (cape under, or over when facing up)."""
    from PIL import ImageOps
    out = Image.new("RGBA", (W * 6, H * 4), (54, 52, 82, 255))
    for r, facing in enumerate(FACINGS):
        body, gown, cape, hair = MAKERS["left" if facing == "right" else facing]
        for c in range(6):
            pose = POSES[c % 3]
            phase = c
            cell = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            layers = [cape(phase).img, body(pose).img, gown(pose).img]
            if facing == "up":
                layers = [body(pose).img, gown(pose).img, cape(phase).img]
            layers.append(hair(phase).img)
            for layer in layers:
                cell.alpha_composite(ImageOps.mirror(layer) if facing == "right" else layer)
            out.alpha_composite(cell, (c * W, r * H))
    out.resize((out.width * scale, out.height * scale), Image.NEAREST).save(path)
    print("wrote", path)


def sheet(path, scale=8):
    """A preview: the four layers composited, with three cape/hair phases."""
    cells = []
    for phase in range(4):
        cell = Image.new("RGBA", (W, H), (54, 52, 82, 255))
        for layer in (front_cape(phase).img, front_body("stand").img, front_gown("stand").img, front_hair(phase).img):
            cell.alpha_composite(layer)
        cells.append(cell)
    for pose in POSES:
        cell = Image.new("RGBA", (W, H), (54, 52, 82, 255))
        for layer in (front_cape(0).img, front_body(pose).img, front_gown(pose).img, front_hair(0).img):
            cell.alpha_composite(layer)
        cells.append(cell)
    out = Image.new("RGBA", (W * 4, H * 2), (54, 52, 82, 255))
    for i, cell in enumerate(cells):
        out.alpha_composite(cell, ((i % 4) * W, (i // 4) * H))
    out.resize((out.width * scale, out.height * scale), Image.NEAREST).save(path)
    print("wrote", path)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "build":
        build(Path(sys.argv[2]))
    else:
        preview_all(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("alucard_preview.png"))
