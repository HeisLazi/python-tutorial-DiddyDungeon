#!/usr/bin/env python3
"""Cut eight separated figures from each new unarmed Home hunter strip.

The generated strips may have uneven spacing and neighbouring cloaks.
Locate their heads and split at the least occupied column between them.
"""
import sys
from PIL import Image, ImageFilter
import from_sheets


def cut_grid(path, band_index, frames):
    img = Image.open(path).convert('RGB')
    width, height = img.size
    px = img.load()
    bg = px[3, 3]
    flat = [sum(abs(a - b) for a, b in zip(px[x, y], bg)) > from_sheets.BG_TOL
            for y in range(height) for x in range(width)]
    flat = from_sheets.fill_hollows(flat, width, height)
    y0, y1 = from_sheets.bands(flat, width, height)[band_index]
    rgba = Image.new('RGBA', img.size, (0, 0, 0, 0))
    out = rgba.load()
    for y in range(y0, y1):
        for x in range(width):
            if flat[y * width + x]:
                src = px[x, y]
                out[x, y] = (src if sum(abs(a - b) for a, b in zip(src, bg)) > from_sheets.BG_TOL else from_sheets.CAPE_FILL) + (255,)
    rgba.putalpha(rgba.getchannel('A').filter(ImageFilter.MedianFilter(3)))
    # Locate each dark head, then split at the emptiest column between heads.
    # The model does not always keep equal spacing and adjacent cloaks can touch.
    occupied = [sum(max(px[x, y]) < 75 for y in range(height // 5, height // 3)) > 8 for x in range(width)]
    spans, start = [], None
    for x, present in enumerate(occupied + [False]):
        if present and start is None:
            start = x
        elif not present and start is not None:
            if x - start > 15:
                spans.append((start, x))
            start = None
    if len(spans) != frames:
        raise ValueError(f'{path}: expected {frames} distinct heads, found {len(spans)}')
    centers = [(a + b) // 2 for a, b in spans]
    boundaries = [0]
    for a, b in zip(centers, centers[1:]):
        candidates = range(round(a + (b - a) * .22), round(b - (b - a) * .12))
        counts = [(sum(flat[y * width + x] for y in range(y0, y1)), x) for x in candidates]
        lowest = min(n for n, _ in counts)
        choices = [x for n, x in counts if n == lowest]
        boundaries.append(choices[len(choices) // 2])
    boundaries.append(width)
    result = []
    for i in range(frames):
        x0, x1 = boundaries[i], boundaries[i + 1]
        cell = rgba.crop((x0, y0, x1, y1))
        bounds = cell.getbbox()
        if bounds is None:
            raise ValueError(f'{path}: frame {i + 1} is empty')
        cell = cell.crop((bounds[0], 0, bounds[2], y1 - y0))
        result.append((cell, cell.size))
    return result


from_sheets.FW = 38
from_sheets.FH = 38
from_sheets.cut = cut_grid
from_sheets.build(sys.argv[1], sys.argv[2], 32, preserve_colors=True)
