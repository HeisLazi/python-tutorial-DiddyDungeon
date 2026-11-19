#!/usr/bin/env python3
"""Cut an AI-generated PROP SHEET into individual game sprites (the same idea as from_sheets.py).

    python3 tools/home_art/from_props.py <sheet.png> <name[@height]> <name[@height]> ... [--out tools/home_art/props]

The sheet is one image of separate props on a flat plain background (see docs/HOME_AND_ART.md,
"Prop sheets"). Props are found as separate blobs and named in READING ORDER (top row first,
left to right), so list the names in that order. `name@48!0-45` also makes a 2-frame flicker pair name_0/name_1 (rows 0-45% shift up 1 px); `!55-88,28-70` limits the shift to a column range and also makes a cold `_out` frame; `>bg` adds dim (b) and blue (g) variants for the hearth; `name@48` scales that prop to 48 px tall
(width follows); with no height the prop keeps the size it would have at --scale (default 0.25).
Each prop gets a contrast/colour lift, hard alpha, a 56-colour palette shared across the sheet, and
a 1 px dark outline, and is written to <out>/<name>.png. make_tiles.py loads every PNG in
tools/home_art/props/ into the atlas, overriding a code-drawn piece with the same name, so an
image-sourced prop drops in without touching the room code.

Animated props: name the frames `name_0`, `name_1` (as the room code expects).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

BG_TOL = 40
MIN_AREA = 120          # ignore specks smaller than this (at sheet resolution)
COLORS = 56
OUTLINE = (16, 12, 28, 255)


def components(mask, w, h):
    seen = bytearray(w * h)
    comps = []
    for y in range(h):
        for x in range(w):
            i = y * w + x
            if mask[i] and not seen[i]:
                stack, pts = [i], []
                seen[i] = 1
                while stack:
                    j = stack.pop()
                    pts.append(j)
                    cx, cy = j % w, j // w
                    for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                        if 0 <= nx < w and 0 <= ny < h:
                            k = ny * w + nx
                            if mask[k] and not seen[k]:
                                seen[k] = 1
                                stack.append(k)
                comps.append(pts)
    return comps


def is_shadow(r, g, b):
    """The soft cast shadow the image model paints under props: a flat, slightly bluish, darker grey."""
    return abs(r - g) <= 6 and 8 <= (b - r) <= 32 and 85 <= r <= 140


def find_props(img):
    from collections import deque
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    bg = px[2, 2]
    solid = bytearray(w * h)          # 1 = part of a prop (before cleaning)
    line_rows = []
    for y in range(h):
        row_dark = 0
        for x in range(w):
            r, g, b = px[x, y]
            if sum(abs(a - c) for a, c in zip((r, g, b), bg)) > BG_TOL:
                solid[y * w + x] = 1
                if r < 60 and g < 60 and b < 70:
                    row_dark += 1
        if row_dark > w * 0.5:        # a ground line across the whole sheet: not a prop
            line_rows.append(y)
            for x in range(w):
                solid[y * w + x] = 0
    for ly in line_rows:              # and its antialiased edge rows
        for y in range(max(0, ly - 3), min(h, ly + 4)):
            for x in range(w):
                solid[y * w + x] = 0
    # the outside: background plus cast shadows connected to it, flooded from the border
    outside = bytearray(w * h)
    dq = deque()
    for x in range(w):
        for y in (0, h - 1):
            dq.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            dq.append((x, y))
    while dq:
        x, y = dq.popleft()
        i = y * w + x
        if outside[i]:
            continue
        r, g, b = px[x, y]
        if solid[i] and not is_shadow(r, g, b):
            continue
        outside[i] = 1
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if 0 <= nx < w and 0 <= ny < h and not outside[ny * w + nx]:
                dq.append((nx, ny))
    flat = [0 if outside[i] else 1 for i in range(w * h)]
    # bridge small gaps inside a prop (so a prop and its dark outline stay one blob)
    m = Image.new("L", (w, h))
    m.putdata([255 if v else 0 for v in flat])
    grown = m.filter(ImageFilter.MaxFilter(5))
    gp = grown.load()
    mask = [1 if gp[x, y] else 0 for y in range(h) for x in range(w)]
    boxes = []
    for pts in components(mask, w, h):
        if len(pts) < MIN_AREA:
            continue
        xs = [p % w for p in pts]
        ys = [p // w for p in pts]
        if max(xs) - min(xs) < 24 or max(ys) - min(ys) < 24:
            continue                  # a speck or a leftover sliver of shadow
        boxes.append((min(xs), min(ys), max(xs) + 1, max(ys) + 1))
    # reading order: group into rows by vertical overlap, then left to right
    boxes.sort(key=lambda b: b[1])
    rows, cur = [], []
    for b in boxes:
        if cur and b[1] > max(c[3] for c in cur) - (b[3] - b[1]) * 0.5:
            rows.append(cur)
            cur = []
        cur.append(b)
    if cur:
        rows.append(cur)
    ordered = [b for r in rows for b in sorted(r, key=lambda b: b[0])]
    return rgb, ordered, bg, flat, w


def build(sheet, names, out_dir, scale=0.25):
    img = Image.open(sheet)
    rgb, boxes, bg, flat, w = find_props(img)
    if len(boxes) != len(names):
        print(f"found {len(boxes)} props but {len(names)} names; boxes (reading order):")
        for i, b in enumerate(boxes):
            print(f"  {i}: {b} ({b[2] - b[0]}x{b[3] - b[1]})")
        raise SystemExit("fix the name list (or re-generate the sheet with clearer gaps)")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    tiles = []
    for (x0, y0, x1, y1), spec in zip(boxes, names):
        if spec == "-":
            continue                  # a prop on the sheet we do not want
        name, _, rest = spec.partition("@")
        ht, _, flick = rest.partition("!")
        flick, _, variants = flick.partition(">")
        crop = rgb.crop((x0, y0, x1, y1))
        alpha = Image.new("L", crop.size, 0)
        ap, cp = alpha.load(), crop.load()
        for yy in range(crop.height):
            for xx in range(crop.width):
                if flat[(y0 + yy) * w + (x0 + xx)]:
                    ap[xx, yy] = 255
        s = (int(ht) / crop.height) if ht else scale
        size = (max(1, round(crop.width * s)), max(1, round(crop.height * s)))
        small = crop.resize(size, Image.LANCZOS)
        small = ImageEnhance.Contrast(small).enhance(1.15)
        small = ImageEnhance.Color(small).enhance(1.1)
        a = alpha.resize(size, Image.BOX).point(lambda v: 255 if v > 120 else 0)
        if flick:
            band, _, cols = flick.partition(",")
            r0, _, r1 = band.partition("-")
            r0, r1 = (int(r0), int(r1)) if r1 else (0, int(r0))
            c0, _, c1 = cols.partition("-")
            c0, c1 = (int(c0), int(c1)) if c1 else (0, 100)
            box = (int(small.width * c0 / 100), int(small.height * r0 / 100), int(small.width * c1 / 100), int(small.height * r1 / 100))

            def with_region(img, region):
                out = img.copy()
                out.paste(region, (box[0], box[1]))
                return out

            region = small.crop(box)
            f1 = small.copy()
            f1.paste(region, (box[0], box[1] - 1))                      # the flames rise 1 px
            ash = Image.new("RGB", region.size, (34, 26, 36))
            f_out = with_region(small, ash) if cols else None           # a cold hearth
            sets = {name: (small, f1, f_out)}
            for letter in variants:
                stem = name[:-1] + letter
                if letter == "b":                                       # a low fire: the same flames, dimmed
                    dim = ImageEnhance.Brightness(region).enhance(0.5)
                    base = with_region(small, dim)
                    r1_ = base.crop(box)
                    f1b = base.copy(); f1b.paste(r1_, (box[0], box[1] - 1))
                    sets[stem] = (base, f1b, f_out)
                elif letter == "g":                                     # blue-white fire
                    hsv = region.convert("HSV")
                    hh, ss, vv = hsv.split()
                    hh = hh.point(lambda v: (v + 138) % 256)
                    blue = Image.merge("HSV", (hh, ss, vv)).convert("RGB")
                    base = with_region(small, blue)
                    r1_ = base.crop(box)
                    f1g = base.copy(); f1g.paste(r1_, (box[0], box[1] - 1))
                    sets[stem] = (base, f1g, f_out)
            for stem, (f0, ff, fo) in sets.items():
                tiles.append((stem + "_0", f0, a))
                tiles.append((stem + "_1", ff, a))
                if fo is not None:
                    tiles.append((stem + "_out", with_region(f0, ash), a))
        else:
            tiles.append((name, small, a))
    # one palette for the sheet
    total_w = sum(t[1].width for t in tiles) + 2 * len(tiles)
    swatch = Image.new("RGB", (total_w, max(t[1].height for t in tiles)), (255, 0, 255))
    x = 0
    for _, im, a in tiles:
        swatch.paste(im, (x, 0), a)
        x += im.width + 2
    pal = swatch.quantize(colors=COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    for name, im, a in tiles:
        q = im.quantize(palette=pal, dither=Image.NONE).convert("RGBA")
        q.putalpha(a)
        # 1 px outline in the room's dark
        padded = Image.new("RGBA", (q.width + 2, q.height + 2), (0, 0, 0, 0))
        padded.paste(q, (1, 1))
        src, dst = padded.copy().load(), padded.load()
        for yy in range(padded.height):
            for xx in range(padded.width):
                if src[xx, yy][3]:
                    continue
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = xx + dx, yy + dy
                    if 0 <= nx < padded.width and 0 <= ny < padded.height and src[nx, ny][3]:
                        dst[xx, yy] = OUTLINE
                        break
        padded.save(out_dir / f"{name}.png")
        print("wrote", out_dir / f"{name}.png", padded.size)


if __name__ == "__main__":
    args = sys.argv[1:]
    out = "tools/home_art/props"
    scale = 0.25
    if "--out" in args:
        i = args.index("--out")
        out = args[i + 1]
        del args[i:i + 2]
    if "--scale" in args:
        i = args.index("--scale")
        scale = float(args[i + 1])
        del args[i:i + 2]
    if len(args) < 2:
        raise SystemExit(__doc__)
    build(args[0], args[1:], out, scale)
