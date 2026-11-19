#!/usr/bin/env python3
"""Separate connected poses, keeping the whole sword and hand together.

Run using system Python with Pillow. All frames have a fixed baseline and use
one scale so the character does not resize between poses.
"""
from collections import deque
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
source = Image.open(HERE / 'tate-sword-v2-concept.png').convert('RGBA')
w, h = source.size
alpha = source.getchannel('A')
pixels = alpha.load()
seen = bytearray(w * h)
components = []
for y in range(h):
    for x in range(w):
        i = y*w + x
        if seen[i] or pixels[x, y] <= 128:
            continue
        seen[i] = 1
        q = deque([(x, y)])
        points = []
        while q:
            px, py = q.popleft()
            points.append((px, py))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    nx, ny = px+dx, py+dy
                    if 0 <= nx < w and 0 <= ny < h:
                        index = ny*w+nx
                        if not seen[index] and pixels[nx, ny] > 128:
                            seen[index] = 1
                            q.append((nx, ny))
        if len(points) > 20_000:
            components.append(points)
components.sort(key=lambda points: min(x for x, _ in points))
if len(components) != 4:
    raise RuntimeError(f'Expected four whole poses, found {len(components)}')
# Source order is idle, wind-up, strike, in-between. Reorder the complete
# silhouettes into their animation sequence, retaining one uniform scale.
anchors = (240, 755, 1830, 1255)
ordered = [components[i] for i in (0, 1, 3, 2)]
sheet = Image.new('RGBA', (96*4, 72))
for frame, (points, anchor) in enumerate(zip(ordered, anchors)):
    mask = Image.new('L', (w,h))
    mask.putdata([0]*(w*h))
    mp = mask.load()
    for x,y in points:
        mp[x,y] = 255
    clean = Image.new('RGBA', (w,h))
    clean.paste(source, (0,0), mask)
    # Align the actor's approximate hip and common foot baseline in each cell.
    crop = clean.crop((anchor - 350, -10, anchor + 610, 710))
    cell = crop.resize((96,72), Image.Resampling.NEAREST)
    sheet.alpha_composite(cell, (frame*96,0))
sheet.save(HERE.parent / 'art' / 'tate-sword-v2-sheet.png')
