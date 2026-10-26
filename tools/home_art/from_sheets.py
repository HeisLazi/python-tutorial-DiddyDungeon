#!/usr/bin/env python3
"""Cut the hunter's walk sheets (AI-generated, in the user's chosen style) into game frames.

    python3 tools/home_art/from_sheets.py <sheet_dir> <out_dir> [height]

<sheet_dir> holds front_idle.png, side_walk.png, back_walk.png: strips of 8 frames on a
flat grey background (see docs/HOME_AND_ART.md, "How the hunter was made"). For each sheet
this script slices the 8 frames, removes the background, scales every frame of a sheet by the
same factor so the character is `height` px tall, anchors the feet to the bottom, and
snaps everything to ONE shared palette (so the three facings match).

Output: out_dir/hunter_{front,side,back}.png (8 frames in a row, FW x FH each) and
hunter_sheet.json (frame size, counts). The right-facing side view is the mirror of the left.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

TARGET_H = 56
FW, FH = 56, 64          # cell the character is centred in; feet on the bottom row
BG_TOL = 40
COLORS = 56

# sheet -> (file, band index, frames)
SHEETS = {
    "front": ("front_idle.png", 0, 8),
    "side": ("side_walk.png", 0, 8),
    "back": ("back_walk.png", 0, 8),
}


def bands(mask, w, h):
    rows = [any(mask[y * w:(y + 1) * w]) for y in range(h)]
    out, s = [], None
    for y, on in enumerate(rows + [False]):
        if on and s is None:
            s = y
        elif not on and s is not None:
            if y - s > 20:
                out.append((s, y))
            s = None
    return out


def cut(path, band_index, frames):
    """Return a list of RGBA frames (original resolution) for one sheet."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    bg = px[3, 3]
    flat = [sum(abs(a - b) for a, b in zip(px[x, y], bg)) > BG_TOL for y in range(h) for x in range(w)]
    y0, y1 = bands(flat, w, h)[band_index]
    # horizontal extent of all figures, then equal cells (side-view frames touch, so no gap-finding)
    xs = [x for x in range(w) if any(flat[y * w + x] for y in range(y0, y1))]
    x0, x1 = xs[0], xs[-1] + 1
    cell = (x1 - x0) / float(frames)
    rgba = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rp = rgba.load()
    for y in range(h):
        for x in range(w):
            if flat[y * w + x]:
                rp[x, y] = px[x, y] + (255,)
    # a stray pixel here and there is background noise: open the alpha a little
    alpha = rgba.getchannel("A").filter(ImageFilter.MedianFilter(3))
    rgba.putalpha(alpha)
    out = []
    for i in range(frames):
        cx0, cx1 = int(x0 + i * cell), int(x0 + (i + 1) * cell)
        out.append((rgba.crop((cx0, y0, cx1, y1)), (cx1 - cx0, y1 - y0)))
    return out


def clean(im):
    """Keep the main figure: drop blobs that touch the left/right cell edge and are small."""
    w, h = im.size
    a = im.getchannel("A")
    ap = a.load()
    seen = [[0] * w for _ in range(h)]
    comps = []
    for y in range(h):
        for x in range(w):
            if ap[x, y] and not seen[y][x]:
                stack, pts = [(x, y)], []
                seen[y][x] = 1
                while stack:
                    cx, cy = stack.pop()
                    pts.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and ap[nx, ny] and not seen[ny][nx]:
                            seen[ny][nx] = 1
                            stack.append((nx, ny))
                comps.append(pts)
    if not comps:
        return im
    big = max(len(c) for c in comps)
    for pts in comps:
        xs = [p[0] for p in pts]
        touches = min(xs) <= 1 or max(xs) >= w - 2
        if len(pts) < big * 0.12 or (touches and len(pts) < big * 0.5):
            for x, y in pts:
                ap[x, y] = 0
    im.putalpha(a)
    return im


def scale_frame(frame, scale):
    im, (w, h) = frame
    clean(im)
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    small = im.resize(size, Image.LANCZOS)
    a = small.getchannel("A").point(lambda v: 255 if v > 110 else 0)
    small.putalpha(a)
    return small


def place(frame):
    """Centre a scaled frame on the FW x FH cell with its feet on the bottom row."""
    cell = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    bb = frame.getbbox()
    if not bb:
        return cell
    fx = (FW - frame.width) // 2
    cell.alpha_composite(frame, (fx, FH - 1 - frame.height))
    return cell


def build(sheet_dir, out_dir, height=TARGET_H):
    sheet_dir, out_dir = Path(sheet_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cells = {}
    for name, (fname, band, n) in SHEETS.items():
        frames = cut(sheet_dir / fname, band, n)
        band_h = frames[0][1][1]
        scale = height / float(band_h)
        cells[name] = [place(scale_frame(f, scale)) for f in frames]
    # one palette for everything
    for name in cells:
        for i, c in enumerate(cells[name]):
            rgb = c.convert("RGB")
            rgb = ImageEnhance.Contrast(rgb).enhance(1.25)
            rgb = ImageEnhance.Color(rgb).enhance(1.12)
            rgb = ImageEnhance.Brightness(rgb).enhance(1.25)
            lifted = rgb.convert("RGBA")
            lifted.putalpha(c.getchannel("A"))
            cells[name][i] = lifted
    swatch = Image.new("RGB", (FW * 8, FH * len(cells)), (255, 0, 255))
    k = 0
    for name in cells:
        for i, c in enumerate(cells[name]):
            swatch.paste(c.convert("RGB"), (i * FW, k * FH), c.getchannel("A"))
        k += 1
    pal = swatch.quantize(colors=COLORS, method=Image.MEDIANCUT, dither=Image.NONE)
    paletted = Image.new("RGB", (1, 1))
    for name, lst in cells.items():
        sheet = Image.new("RGBA", (FW * len(lst), FH), (0, 0, 0, 0))
        for i, c in enumerate(lst):
            alpha = c.getchannel("A")
            q = c.convert("RGB").quantize(palette=pal, dither=Image.NONE).convert("RGB")
            q = q.convert("RGBA")
            q.putalpha(alpha)
            sheet.paste(q, (i * FW, 0))
        sheet.save(out_dir / f"hunter_{name}.png")
    meta = {"frame": [FW, FH], "frames": 8, "facings": {"down": "front", "left": "side", "right": "side(mirrored)", "up": "back"}}
    (out_dir / "hunter_sheet.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print("wrote", out_dir)


def preview(out_dir, path, scale=6):
    out_dir = Path(out_dir)
    names = ["front", "side", "back"]
    sheets = [Image.open(out_dir / f"hunter_{n}.png") for n in names]
    out = Image.new("RGBA", (sheets[0].width, FH * 3), (54, 52, 82, 255))
    for i, s in enumerate(sheets):
        out.alpha_composite(s, (0, i * FH))
    out.resize((out.width * scale, out.height * scale), Image.NEAREST).save(path)
    print("wrote", path)


if __name__ == "__main__":
    if sys.argv[1] == "preview":
        preview(sys.argv[2], sys.argv[3])
    else:
        build(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else TARGET_H)
