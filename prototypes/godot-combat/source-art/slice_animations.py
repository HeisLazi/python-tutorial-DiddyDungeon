#!/usr/bin/env python3
"""Slice the animated study into fixed cells while preserving each full pose.

Use system Python with Pillow. The single scale and common foot baseline keep
characters grounded, and connected masks separate overlapping source bounds.
"""
from collections import deque
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
# A horizontal anchor near the hips for each pose. Relative to 96x72 cells,
# Tate's anchor is at x=35; the left-facing hollow's anchor is at x=55.
SHEETS = {
    'tate-idle': ((240, 785, 1300, 1870), 35),
    'tate-hurt': ((240, 740, 1305, 1900), 35),
    'tate-followthrough': ((240, 755, 1255, 1900), 35),
    'hollow-action': ((300, 805, 1300, 1900), 55),
    'hollow-hurt': ((300, 845, 1370, 1900), 55),
    'mimic-action': ((300, 835, 1350, 1890), 55),
    'mimic-hurt': ((300, 840, 1405, 1900), 55),
}

def components_of(source):
    w, h = source.size
    alpha = source.getchannel('A').load()
    seen = bytearray(w * h)
    components = []
    for y in range(h):
        for x in range(w):
            index = y * w + x
            if seen[index] or alpha[x, y] <= 128:
                continue
            seen[index] = 1
            queue = deque([(x, y)])
            points = []
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = px + dx, py + dy
                        if 0 <= nx < w and 0 <= ny < h:
                            ni = ny * w + nx
                            if not seen[ni] and alpha[nx, ny] > 128:
                                seen[ni] = 1
                                queue.append((nx, ny))
            if len(points) > 20_000:
                components.append(points)
    return sorted(components, key=lambda points: min(x for x, _ in points))

for name, (anchors, target_x) in SHEETS.items():
    source = Image.open(HERE / (name + '-concept.png')).convert('RGBA')
    w, h = source.size
    components = components_of(source)
    if len(components) != 4:
        raise RuntimeError(f'{name}: expected 4 main poses, found {len(components)}')
    sheet = Image.new('RGBA', (96 * 4, 72))
    for frame, (points, anchor) in enumerate(zip(components, anchors)):
        mask = Image.new('L', (w, h))
        pix = mask.load()
        for x, y in points:
            pix[x, y] = 255
        clean = Image.new('RGBA', (w, h))
        clean.paste(source, (0, 0), mask)
        left = anchor - target_x * 10
        top = {'tate-followthrough': -23, 'mimic-action': -70, 'mimic-hurt': -80}.get(name, -10)
        crop = clean.crop((left, top, left + 960, top + 720))
        sheet.alpha_composite(crop.resize((96, 72), Image.Resampling.NEAREST), (frame * 96, 0))
    sheet.save(HERE.parent / 'art' / (name + '-sheet.png'))
