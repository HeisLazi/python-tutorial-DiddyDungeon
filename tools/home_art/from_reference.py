#!/usr/bin/env python3
"""Turn an AI turnaround reference into palette-snapped sprite views.

    python3 tools/home_art/from_reference.py <reference.png> <out_dir> [height]

1. finds each figure on the flat background (the soft floor shadow is ignored),
2. scales all figures to one height with an area filter, after a little sharpening,
3. snaps every pixel to the fixed hunter palette (so gold stays gold, crimson stays
   crimson, the avatar's umber skin replaces the tan, hair stays hair), and
4. adds a 1px dark outline.

Because each pixel keeps its palette *class* (coat, gold, lining, skin, hair, ...)
the next step (make_hunter.py) can cut the sprite into animatable layers by class.
Output: view_<i>.png (left to right), classes in view_<i>.cls.json-free form (the
palette index is the class), and contact.png.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

BG_TOL = 46

# name -> (rgb, class). The class decides which animation layer a pixel belongs to.
PALETTE = {
    "line": ((14, 10, 24), "line"),
    "ck0": ((10, 10, 18), "coat"), "ck1": ((26, 26, 40), "coat"), "ck2": ((46, 46, 68), "coat"), "ck3": ((84, 84, 116), "coat"),
    "g0": ((140, 92, 24), "gold"), "g1": ((206, 144, 48), "gold"), "g2": ((250, 204, 100), "gold"),
    "r0": ((84, 12, 30), "lining"), "r1": ((140, 24, 46), "lining"), "r2": ((200, 44, 62), "lining"),
    "w0": ((48, 52, 74), "vest"), "w1": ((92, 98, 128), "vest"), "w2": ((146, 154, 184), "vest"),
    "cr0": ((176, 182, 206), "cravat"), "cr1": ((236, 238, 248), "cravat"),
    "l0": ((58, 34, 24), "belt"), "l1": ((102, 62, 36), "belt"),
    "sk0": ((98, 58, 38), "skin"), "sk1": ((144, 90, 54), "skin"), "sk2": ((188, 124, 80), "skin"), "sk3": ((216, 152, 102), "skin"),
    "h0": ((24, 14, 26), "hair"), "h1": ((52, 30, 44), "hair"), "h2": ((86, 52, 66), "hair"), "h3": ((126, 82, 96), "hair"),
    "b0": ((12, 10, 20), "boot"), "b1": ((32, 30, 46), "boot"), "b2": ((64, 62, 88), "boot"),
    "s1": ((150, 158, 184), "silver"), "s2": ((222, 228, 242), "silver"),
}
NAMES = list(PALETTE)
RGBS = [PALETTE[n][0] for n in NAMES]


def figures(img):
    rgb = img.convert("RGB")
    w, h = rgb.size
    bg = rgb.getpixel((4, 4))
    px = rgb.load()
    mask = Image.new("L", (w, h), 0)
    mp = mask.load()
    for y in range(h):
        for x in range(w):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > BG_TOL:
                mp[x, y] = 255
    mask = mask.filter(ImageFilter.MedianFilter(5))
    cols = [any(mask.getpixel((x, y)) for y in range(0, h, 3)) for x in range(w)]
    boxes, start = [], None
    for x, on in enumerate(cols + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start > w * 0.04:
                bb = mask.crop((start, 0, x, h)).getbbox()
                boxes.append((start + bb[0], bb[1], start + bb[2], bb[3]))
            start = None
    return boxes, mask


def is_skin(rgb):
    """Warm, lowish-saturation, mid-bright pixels are skin (gold is more yellow and saturated)."""
    import colorsys
    r, g, b = (v / 255.0 for v in rgb)
    h, sat, val = colorsys.rgb_to_hsv(r, g, b)
    return 0.02 < h < 0.098 and 0.22 < sat < 0.62 and val > 0.42


SKIN_IDX = [NAMES.index(n) for n in ("sk0", "sk1", "sk2", "sk3")]


def nearest(rgb):
    if is_skin(rgb):
        r, g, b = rgb
        return min(SKIN_IDX, key=lambda i: (r - RGBS[i][0]) ** 2 + (g - RGBS[i][1]) ** 2 + (b - RGBS[i][2]) ** 2)
    r, g, b = rgb
    best, best_d = 0, 1e18
    for i, (pr, pg, pb) in enumerate(RGBS):
        # weight green a little more (the eye is more sensitive to it)
        d = 2 * (r - pr) ** 2 + 3 * (g - pg) ** 2 + 2 * (b - pb) ** 2
        if d < best_d:
            best, best_d = i, d
    return best


def convert(path, out_dir, height=56):
    img = Image.open(path).convert("RGB")
    boxes, mask = figures(img)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tallest = max(b[3] - b[1] for b in boxes)
    sheet_views = []
    for i, (x0, y0, x1, y1) in enumerate(boxes):
        crop = img.crop((x0, y0, x1, y1))
        crop = ImageEnhance.Contrast(crop).enhance(1.25)
        crop = ImageEnhance.Color(crop).enhance(1.05)
        m = mask.crop((x0, y0, x1, y1))
        cp, mp2 = crop.load(), m.load()
        ch = crop.height
        for yy in range(int(ch * 0.9), ch):
            for xx in range(crop.width):
                rr, gg, bb = cp[xx, yy]
                if max(rr, gg, bb) - min(rr, gg, bb) < 22 and max(rr, gg, bb) > 70:
                    mp2[xx, yy] = 0
        scale = height / tallest
        size = (max(1, round((x1 - x0) * scale)), max(1, round((y1 - y0) * scale)))
        small = crop.resize(size, Image.LANCZOS)
        msmall = m.resize(size, Image.BOX).point(lambda v: 255 if v > 120 else 0)
        idx = Image.new("P", size)
        out = Image.new("RGBA", size, (0, 0, 0, 0))
        po, pi = out.load(), small.load()
        for y in range(size[1]):
            for x in range(size[0]):
                if msmall.getpixel((x, y)):
                    k = nearest(pi[x, y])
                    r, g, b = RGBS[k]
                    po[x, y] = (r, g, b, 255)
        out.save(out_dir / f"view_{i}.png")
        sheet_views.append(out)
    gap = 4
    sheet = Image.new("RGBA", (sum(v.width for v in sheet_views) + gap * (len(sheet_views) + 1), height + 8), (70, 68, 96, 255))
    x = gap
    for v in sheet_views:
        sheet.alpha_composite(v, (x, 4))
        x += v.width + gap
    sheet.resize((sheet.width * 7, sheet.height * 7), Image.NEAREST).save(out_dir / "contact.png")
    print("views:", [(v.width, v.height) for v in sheet_views], "->", out_dir)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 56)
