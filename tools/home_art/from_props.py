#!/usr/bin/env python3
"""Cut an AI-generated PROP SHEET into individual game sprites (the same idea as from_sheets.py).

    python3 tools/home_art/from_props.py <sheet.png> <name[@height]> <name[@height]> ... [--out tools/home_art/props]

The sheet is one image of separate props on a flat plain background (see docs/HOME_AND_ART.md,
"Prop sheets"). Props are found as separate blobs and named in READING ORDER (top row first,
left to right), so list the names in that order. `name@48` scales that prop to 48 px tall
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


def find_props(img):
    rgb = img.convert("RGB")
    w, h = rgb.size
    px = rgb.load()
    bg = px[2, 2]
    flat = [sum(abs(a - b) for a, b in zip(px[x, y], bg)) > BG_TOL for y in range(h) for x in range(w)]
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
        name, _, ht = spec.partition("@")
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
