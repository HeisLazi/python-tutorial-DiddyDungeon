#!/usr/bin/env python3
"""Rig the hunter: cut the converted turnaround views into animated layers.

    python3 tools/home_art/rig_hunter.py [out_dir]          # writes the sheets
    python3 tools/home_art/rig_hunter.py preview <out.png>  # a contact sheet to look at

Source art: tools/home_art/assets/alucard_{front,side,back}.png, made by
from_reference.py out of an AI turnaround (see docs/HOME_AND_ART.md, "How the
hunter was made"). Every pixel is a palette colour, so its class (coat, gold,
lining, skin, hair, boot ...) is known, and the sprite can be cut into parts:

  hair   hair below the head, shifted per row with a wave, so it flows
  cape   the cape's crimson lining below the shoulders, swaying
  body   everything else: head, collar, coat, arms and legs; the coat hem shears
         and the legs step (a lifted foot) for the walk cycle

Frames are 40x70, feet on row 68. Sheets (rows: down, left, right, up; right is the
mirror of left): hunter_<look>_body.png (3 cols: stand, step A, step B),
hunter_<look>_cape.png and hunter_<look>_hair.png (4 cols: phases).
The skin and hair are recoloured to the avatar (umber skin, dark plum hair) and the
coat is lifted a little so the figure reads on a dark floor.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).parent))
from from_reference import PALETTE  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ASSETS = Path(__file__).parent / "assets"
FW, FH = 40, 70
FEET_Y = 68
POSES = ("stand", "stepa", "stand", "stepb")   # 4-phase walk; the body bobs up on the steps
FACINGS = ["down", "left", "right", "up"]
SIDE_POSES = ("contA", "stepa", "contB", "stepb")   # side view: contact, passing, contact, passing
# near-leg x / lift, far-leg x / lift (x is forward of the hip, lift in px off the floor)
SIDE_LEGS = {
    "stand": (0, 0, 0, 0), "contA": (4, 0, -4, 0), "stepa": (0, 0, 1, 3),
    "contB": (-4, 0, 4, 0), "stepb": (1, 3, 0, 0),
}

CLASS_OF = {name: cls for name, (_rgb, cls) in PALETTE.items()}
BY_RGB = {rgb: name for name, (rgb, _cls) in PALETTE.items()}

# The avatar and the room's value range: umber skin, plum-black hair, a lifted coat.
RECOLOR = {
    "sk0": (52, 30, 22), "sk1": (84, 50, 34), "sk2": (118, 74, 50), "sk3": (152, 100, 68),
    "h0": (18, 12, 28), "h1": (42, 28, 54), "h2": (74, 54, 94), "h3": (114, 88, 140),
    "ck0": (36, 36, 62), "ck1": (70, 70, 108), "ck2": (108, 108, 152), "ck3": (156, 156, 198),
    "b0": (26, 24, 42), "b1": (56, 54, 82), "b2": (100, 98, 134),
}


def rgb_of(name):
    return RECOLOR.get(name, PALETTE[name][0])


def load(view, mirror=False):
    """Return {(x, y): name} placed bottom-centre in the frame."""
    img = Image.open(ASSETS / f"alucard_{view}.png").convert("RGBA")
    if mirror:
        img = ImageOps.mirror(img)
    w, h = img.size
    ox, oy = (FW - w) // 2, FEET_Y - h + 1
    px = img.load()
    out = {}
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a:
                out[(ox + x, oy + y)] = BY_RGB.get((r, g, b), "ck1")
    return out


def bounds(pix):
    xs = [p[0] for p in pix]
    ys = [p[1] for p in pix]
    return min(xs), min(ys), max(xs), max(ys)


class Rig:
    def __init__(self, view, mirror=False):
        self.pix = load(view, mirror)
        self.view = view
        x0, y0, x1, y1 = bounds(self.pix)
        self.x0, self.y0, self.x1, self.y1 = x0, y0, x1, y1
        self.cx = (x0 + x1) / 2.0
        height = y1 - y0 + 1
        self.head_end = y0 + int(height * 0.21)               # hair above this stays put (the crown)
        boots = [p[1] for p, n in self.pix.items() if CLASS_OF[n] == "boot" and p[1] > y0 + height * 0.6]
        self.hem = (min(boots) if boots else y0 + int(height * 0.78)) - 1
        self.shoulder = y0 + int(height * 0.26)
        self.mirror = mirror
        skin = [p for p, n in self.pix.items() if CLASS_OF[n] == "skin" and p[1] < y0 + height * 0.3]
        self.face = bounds(skin) if skin else (int(self.cx) - 4, y0 + 4, int(self.cx) + 4, y0 + 14)

    # ── parts ──────────────────────────────────────────────────────────────
    def hair_pixels(self):
        """The long hair of the source art: dropped, the afro replaces it."""
        return {p: n for p, n in self.pix.items() if CLASS_OF[n] == "hair" and p[1] >= self.head_end}

    def afro(self, phase):
        """A round afro around the head, drawn over the crown and behind the face."""
        fx0, fy0, fx1, fy1 = self.face
        cx, cy = (fx0 + fx1) / 2.0, fy0 + 1
        rx = (fx1 - fx0) / 2.0 + (3.4 if self.view != "side" else 3.0)
        ry = 7.4 if self.view != "back" else 9.0
        if self.view == "back":
            rx += 1.5
        if self.view == "side":
            cx += -3.0 if not self.mirror else 3.0       # sits back from the face
        cy += [0, -1, 0, -1][phase % 4]                  # bobs with the steps
        skin = {p for p, n in self.pix.items() if CLASS_OF[n] == "skin"}
        out = {}
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
                edge = 1.0 + 0.09 * (((x * 5 + y * 11) % 4) - 1.5)     # bumpy coil edge
                if d > edge:
                    continue
                if self.view != "back" and y > cy + ry * 0.2:
                    continue                             # not below the temples
                if (x, y + (0 if phase % 2 == 0 else 1)) in skin and self.view != "back":
                    continue                             # the face shows through
                # tight coils: noise shading, lighter toward the top-left
                h = (x * 7 + y * 13 + (x ^ y) * 3) % 5
                light = (cx - x) * 0.04 + (cy - y) * 0.05 - d * 0.6
                k = 3 if (light > 0.55 and h < 2) else 2 if (light > 0.2 and h < 3) else 1 if d < 0.8 else 0
                out[(x, y)] = ("h0", "h1", "h2", "h3")[k]
        return out

    def cape_pixels(self):
        return {p: n for p, n in self.pix.items() if CLASS_OF[n] == "lining" and p[1] >= self.shoulder + 4}

    def static_pixels(self):
        gone = set(self.hair_pixels()) | set(self.cape_pixels())
        return {p: n for p, n in self.pix.items() if p not in gone}

    # ── frames ─────────────────────────────────────────────────────────────
    def body(self, pose):
        """The body with the coat hem sheared and the feet stepping."""
        base = self.static_pixels()
        # the holes left by the hair and cape are filled with coat so nothing shows through
        for p in list(self.hair_pixels()) + list(self.cape_pixels()):
            base[p] = "ck1"
        fx0, fy0, fx1, fy1 = self.face
        if self.view == "back":
            for q in [q for q, n in base.items() if CLASS_OF[n] in ("skin", "belt") and q[1] < self.shoulder + 3]:
                base[q] = "h1"
        for p in [q for q, n in base.items() if CLASS_OF[n] == "hair"]:
            if self.view != "back" and fx0 <= p[0] <= fx1 and fy0 + 2 <= p[1] <= fy1:
                base[p] = "sk1"                                # bangs removed: it was face
            else:
                del base[p]
        if self.view == "side":
            return self.side_body(base, pose)
        g = {"stand": 0, "stepa": 1, "stepb": -1}[pose]
        bob = -1 if pose in ("stepa", "stepb") else 0
        lift = {"stand": (0, 0), "stepa": (1, 0), "stepb": (0, 1)}[pose]
        out = {}
        for (x, y), n in base.items():
            nx, ny = x, y
            if y >= self.hem + 1:                                # the legs and boots
                left = x < self.cx
                up = lift[0] if left else lift[1]
                if self.view == "side":
                    # one leg forward, one back, scissoring
                    d = 0
                    nx, ny = x + d, y - (1 if (left and g > 0) or (not left and g < 0) else 0)
                else:
                    ny = y - (up if y >= FEET_Y - 4 else 0)         # only the foot lifts
            out[(nx, ny + (bob if y < self.hem + 1 else 0))] = n
            if bob and y == self.hem:
                out[(nx, y)] = n                                  # no seam where the torso lifts off the legs
        # a feet row can lift off the floor: close gaps above lifted boots with the coat
        return out

    def side_body(self, base, pose):
        """Side walk: the torso bobs, the hem swings, and two real legs scissor and lift."""
        d = 1 if self.mirror else -1                    # +x is forward for the right-facing mirror
        bob = -1 if pose in ("stepa", "stepb") else 0
        swing = {"stand": 0, "contA": 1, "stepa": 0, "contB": -1, "stepb": 0}[pose]
        out = {}
        new_hem = FEET_Y - 14                            # coat to the knee, then 14 rows of leg
        src = {(x, y): n for (x, y), n in base.items() if y <= self.hem}
        rows = {}
        for (x, y), n in src.items():
            rows.setdefault(y, {})[x] = n
        for y in range(self.hem + 1, new_hem + 1):        # stretch the skirt: repeat the lower coat rows
            rows[y] = {x: (n if CLASS_OF[n] == "coat" else "ck1") for x, n in rows[self.hem - 2].items()}
        # the trimmed hem row goes last
        rows[new_hem] = rows[self.hem]
        for y, row in rows.items():
            if y > new_hem:
                continue
            for x, n in row.items():
                nx = x + (d * swing if y > new_hem - 8 else 0)
                out[(nx, y + bob)] = n
        self.hem_row = new_hem
        hip = int(round(self.cx)) + (1 if self.mirror else -1) * 0
        near_x, near_up, far_x, far_up = SIDE_LEGS[pose]
        for x, up, shade in ((far_x, far_up, ("b0", "b0", "b1")), (near_x, near_up, ("b1", "b2", "b2"))):
            self.leg(out, hip, d * x, up, shade, d)
        return out

    def hem_fill(self, bob):
        """Coat pixels along the hem row so the torso and legs never show a seam."""
        return {(x, self.hem): n for (x, y), n in self.pix.items() if y == self.hem and CLASS_OF[n] == "coat"}

    def leg(self, out, hip, fx, up, shade, d):
        """One leg: a 4px boot column from the hem to the foot (fx forward, up lifted) with a toe."""
        top, bottom = getattr(self, "hem_row", self.hem) + 1, FEET_Y - up
        for y in range(top, bottom + 1):
            t = (y - top) / max(1, bottom - top)
            cx = hip + int(round(fx * t))
            if up and t > 0.55:
                cx -= d * int(round((t - 0.55) * 4))     # a lifted leg folds back at the knee
            for k in range(-2, 3):
                col = shade[0] if k in (-2, 2) else shade[1] if k <= 0 else shade[2]
                out[(cx + k, y)] = col
            if y == top + 3:
                for k in range(-2, 3):
                    out[(cx + k, y)] = "s1"              # the silver boot cuff
        for k in range(1, 4):                            # toe pointing forward
            out[(hip + int(round(fx)) + (-1 if d < 0 else 1) * (k - (2 if d < 0 else 3)) + (0), bottom)] = shade[1]
        toe_dir = d
        for k in range(1, 4):
            out[(hip + int(round(fx)) + toe_dir * (1 + k), bottom)] = shade[1]
            out[(hip + int(round(fx)) + toe_dir * (1 + k), bottom - 1)] = shade[0]

    def hair(self, phase):
        return self.afro(phase)

    def cape(self, phase):
        out = {}
        for (x, y), n in self.cape_pixels().items():
            t = min(1.0, (y - self.shoulder) / 28.0)
            side = -1 if x < self.cx else 1
            sway = [0, 1, 2, 1][phase % 4] * t
            out[(x + int(round(side * sway * (0.8 if self.view != "side" else 0.3))), y)] = n
        return out


def draw(pix, with_outline=True):
    img = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    px = img.load()
    for (x, y), n in pix.items():
        if 0 <= x < FW and 0 <= y < FH:
            r, g, b = rgb_of(n)
            px[x, y] = (r, g, b, 255)
    for y in range(FH):                                   # drop lone pixels the shifts leave behind
        for x in range(FW):
            if px[x, y][3] and not any(
                0 <= x + dx < FW and 0 <= y + dy < FH and px[x + dx, y + dy][3]
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                px[x, y] = (0, 0, 0, 0)
    if with_outline:
        out = img.copy()
        dst = out.load()
        for y in range(FH):
            for x in range(FW):
                if px[x, y][3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < FW and 0 <= ny < FH and px[nx, ny][3]:
                        dst[x, y] = (14, 10, 24, 255)
                        break
        img = out
    return img


def rigs():
    return {"down": Rig("front"), "left": Rig("side"), "right": Rig("side", mirror=True), "up": Rig("back")}


def build(out_dir, look="alucard"):
    sheets = {
        "body": Image.new("RGBA", (FW * 5, FH * 4), (0, 0, 0, 0)),
        "cape": Image.new("RGBA", (FW * 4, FH * 4), (0, 0, 0, 0)),
        "hair": Image.new("RGBA", (FW * 4, FH * 4), (0, 0, 0, 0)),
    }
    for r, facing in enumerate(FACINGS):
        rig = rigs()[facing]
        walk = SIDE_POSES if facing in ("left", "right") else POSES
        sheets["body"].paste(draw(rig.body("stand")), (0, r * FH))          # col 0: idle
        for c in range(4):
            sheets["body"].paste(draw(rig.body(walk[c])), ((c + 1) * FW, r * FH))
        for c in range(4):
            sheets["cape"].paste(draw(rig.cape(c)), (c * FW, r * FH))
            sheets["hair"].paste(draw(rig.hair(c)), (c * FW, r * FH))
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for kind, img in sheets.items():
        img.save(out_dir / f"hunter_{look}_{kind}.png")
    meta = {"frame": [FW, FH], "feet_row": FEET_Y, "rows": FACINGS, "body_cols": ["idle", "walk0", "walk1", "walk2", "walk3"], "phases": 4, "bob": [0, -1, 0, -1],
            "layers": ["cape", "body", "hair"], "looks": [look]}
    (out_dir / "hunter.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", look, "to", out_dir)


def preview(path, scale=6):
    """Every facing: three walk poses with the cape and hair phases layered in."""
    out = Image.new("RGBA", (FW * 8, FH * 4), (54, 52, 82, 255))
    for r, facing in enumerate(FACINGS):
        rig = rigs()[facing]
        for c in range(8):
            cell = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
            for layer in (draw(rig.cape(c)), draw(rig.body((SIDE_POSES if facing in ("left", "right") else POSES)[c % 4])), draw(rig.hair(c))):
                cell.alpha_composite(layer)
            out.alpha_composite(cell, (c * FW, r * FH))
    out.resize((out.width * scale, out.height * scale), Image.NEAREST).save(path)
    print("wrote", path)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "preview":
        preview(Path(sys.argv[2]))
    else:
        build(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "ide" / "home-godot" / "art")
