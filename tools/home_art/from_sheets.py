#!/usr/bin/env python3
"""Cut the hunter's walk sheets (AI-generated, in the user's chosen style) into game frames.

    python3 tools/home_art/from_sheets.py <sheet_dir> <out_dir> [height]

<sheet_dir> holds front_idle.png, side_walk.png, back_walk.png: strips of 8 frames on a
flat grey background (see docs/HOME_AND_ART.md, "How the hunter was made"). For each sheet
this script slices the 8 frames, removes the background, scales every frame of a sheet by the
same factor so the character is `height` px tall, anchors the feet to the bottom, and
snaps everything to ONE shared palette (so the three facings match).

Then it cleans each frame: fills the cape's hollow inside (it is background grey in the source),
paints the face one flat colour (no eyes), turns the brown hair black, recolours the skin to
umber, and appends a 4-frame breathing idle (head and torso one pixel lower on half the loop,
from the walk frame whose feet are closest together).

Output: out_dir/hunter_{front,side,back}.png (8 walk frames then 4 idle frames, FW x FH each) and
hunter_sheet.json (frame size, counts). The right-facing side view is the mirror of the left.

    python3 tools/home_art/from_sheets.py tools/home_art/sheets tools/home_art/assets/hunter 40
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import sys as _sys
from pathlib import Path as _P
_sys.path.insert(0, str(_P(__file__).parent))
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

TARGET_H = 40
FW, FH = 48, 46          # cell the character is centred in; feet on the bottom row (derived from the height below)
BG_TOL = 40
COLORS = 56
CAPE_FILL = (46, 46, 66)
FACE = (184, 138, 95)      # the flat face colour, before the skin is darkened
IDLE_FRAMES = 4

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


def fill_hollows(flat, w, h):
    """Mark enclosed background pixels (the cape's inside, which is background grey) as part of the figure."""
    mask = Image.new("L", (w, h), 0)
    mask.putdata([255 if v else 0 for v in flat])
    grown = mask.filter(ImageFilter.MaxFilter(3))                  # close 1px gaps in the outline
    ImageDraw.floodfill(grown, (0, 0), 128)                         # the outside
    inside = grown.point(lambda v: 255 if v == 0 else 0)           # left unfilled: enclosed
    fill = inside.filter(ImageFilter.MaxFilter(3))                  # plus the ring the dilation ate
    fp, mp = fill.load(), mask.load()
    out = list(flat)
    for y in range(h):
        for x in range(w):
            if fp[x, y] and not mp[x, y]:
                out[y * w + x] = True
    return out


def cut(path, band_index, frames):
    """Return a list of RGBA frames (original resolution) for one sheet."""
    img = Image.open(path).convert("RGB")
    w, h = img.size
    px = img.load()
    bg = px[3, 3]
    flat = [sum(abs(a - b) for a, b in zip(px[x, y], bg)) > BG_TOL for y in range(h) for x in range(w)]
    flat = fill_hollows(flat, w, h)
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
                src = px[x, y]
                # hollows we filled are still background-coloured: paint them cape-dark
                rp[x, y] = (src if sum(abs(a - b) for a, b in zip(src, bg)) > BG_TOL else CAPE_FILL) + (255,)
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


def flatten_face(img):
    """The face has no features: paint every bright warm pixel and anything dark inside it as one flat colour."""
    import colorsys
    px = img.load()
    top = next((y for y in range(img.height) if any(px[x, y][3] for x in range(img.width))), None)
    if top is None:
        return
    for y in range(top, min(img.height, top + 15)):
        xs = []
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if not a:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if 0.0 <= hh <= 0.15 and ss > 0.3 and vv > 0.5:
                xs.append(x)
        if not xs:
            continue
        for x in range(min(xs), max(xs) + 1):
            r, g, b, a = px[x, y]
            if a:
                px[x, y] = FACE + (255,)


def blacken_hair(img):
    """Hair is black: brown pixels in the head become near-black with a faint cool highlight."""
    import colorsys
    px = img.load()
    top = next((y for y in range(img.height) if any(px[x, y][3] for x in range(img.width))), None)
    if top is None:
        return
    for y in range(top, min(img.height, top + 14)):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if not a or (r, g, b) == FACE:
                continue
            hh, ss, vv = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            if 0.0 <= hh <= 0.15 and ss > 0.15 and 0.12 < vv < 0.62:
                v = max(r, g, b)
                px[x, y] = (int(v * 0.40), int(v * 0.38), int(v * 0.52), a)


def feet_spread(img):
    """How far apart the dark boot pixels are along the bottom rows (small = feet together)."""
    px = img.load()
    xs = [x for y in range(img.height - 7, img.height) for x in range(img.width)
          if px[x, y][3] and max(px[x, y][:3]) < 90]
    return (max(xs) - min(xs)) if xs else 99


def darken_skin(img):
    """Recolour skin-hued pixels (warm, mid-saturation, bright) to deep umber, keeping the shading."""
    from from_reference import is_skin
    px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a and is_skin((r, g, b)):
                px[x, y] = (int(r * 0.50), int(g * 0.42), int(b * 0.42), a)


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
        for i, c in enumerate(lst):
            alpha = c.getchannel("A")
            q = c.convert("RGB").quantize(palette=pal, dither=Image.NONE).convert("RGB")
            q = q.convert("RGBA")
            q.putalpha(alpha)
            if name != "back":
                flatten_face(q)
            blacken_hair(q)
            darken_skin(q)
            lst[i] = q
        # idle: the same standing frame, torso and head one pixel lower on the second half of the loop
        base = min(lst, key=feet_spread)             # the frame with the feet closest together
        split = FH - 17
        idle = []
        for k in (0, 0, 1, 1):
            f = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
            if k:
                f.alpha_composite(base.crop((0, 0, FW, split)), (0, k))
                f.alpha_composite(base.crop((0, split, FW, FH)), (0, split))
            else:
                f.alpha_composite(base)
            idle.append(f)
        frames = lst + idle
        sheet = Image.new("RGBA", (FW * len(frames), FH), (0, 0, 0, 0))
        for i, q in enumerate(frames):
            sheet.paste(q, (i * FW, 0))
        sheet.save(out_dir / f"hunter_{name}.png")
    meta = {"frame": [FW, FH], "frames": 8, "idle_start": 8, "idle_frames": IDLE_FRAMES, "facings": {"down": "front", "left": "side", "right": "side(mirrored)", "up": "back"}}
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
        meta = json.loads((Path(sys.argv[2]) / "hunter_sheet.json").read_text(encoding="utf-8"))
        FW, FH = meta["frame"]
        preview(sys.argv[2], sys.argv[3])
    else:
        h = int(sys.argv[3]) if len(sys.argv) > 3 else TARGET_H
        FW, FH = int(h * 1.2) // 2 * 2, h + 6        # the side view with its sword is the widest
        build(sys.argv[1], sys.argv[2], h)
