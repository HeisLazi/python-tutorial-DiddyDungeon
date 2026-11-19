#!/usr/bin/env python3
"""Build Home's 38px hunter strips from the authored four-pose turnaround.

Run with system Python and Pillow: python3 tools/home_art/build_hunter_v3.py
The source has three rows (front, side, back) and four poses per row. Frame
zero of the side row faces left; the other three are mirrored to match it.
"""
from collections import deque
from pathlib import Path
from PIL import Image
import json

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/home_art/sheets/hunter_v3/walk_source.png'
TURNAROUND = ROOT / 'tools/home_art/sheets/hunter_v3/turnaround.png'
OUTPUT = ROOT / 'tools/home_art/assets/hunter_v3'
CELL = 38


def extract(image, bg):
    """Flood the neutral backdrop from the edges, preserving enclosed details."""
    image = image.convert('RGBA')
    width, height = image.size
    pix = image.load()
    outside = set()
    queue = deque([(x, 0) for x in range(width)] + [(x, height - 1) for x in range(width)] + [(0, y) for y in range(height)] + [(width - 1, y) for y in range(height)])
    while queue:
        x, y = queue.popleft()
        if (x, y) in outside or not (0 <= x < width and 0 <= y < height):
            continue
        if sum(abs(pix[x, y][i] - bg[i]) for i in range(3)) > 42:
            continue
        outside.add((x, y))
        queue.extend(((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)))
    for x, y in outside:
        pix[x, y] = (0, 0, 0, 0)
    box = image.getbbox()
    if not box:
        raise ValueError('empty sprite frame')
    return image.crop(box)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = Image.open(SOURCE)
    w, h = source.size
    bg = source.convert("RGB").getpixel((0, 0))
    turnaround = Image.open(TURNAROUND)
    idle_bg = turnaround.convert("RGB").getpixel((0, 0))
    idle_bounds = {"front": (0, 620), "side": (620, 1030), "back": (1030, 1510)}
    xs = [0, 440, 765, 1090, w]
    ys = [0, 340, 660, h]
    for row, name in enumerate(('front', 'side', 'back')):
        frames = []
        for col in range(4):
            crop = source.crop((xs[col], ys[row], xs[col+1], ys[row+1]))
            frame = extract(crop, bg)
            if name == 'side' and col > 0:
                frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            frames.append(frame)
        scale = min(32 / max(f.height for f in frames), 34 / max(f.width for f in frames))
        cells = []
        for frame in frames:
            frame = frame.resize((max(1, round(frame.width*scale)), max(1, round(frame.height*scale))), Image.Resampling.NEAREST)
            cell = Image.new('RGBA', (CELL, CELL))
            cell.alpha_composite(frame, ((CELL-frame.width)//2, CELL-2-frame.height))
            cells.append(cell)
        # Duplicate the four-frame gait to fit the engine's eight-frame contract.
        walk = cells * 2
        left, right = idle_bounds[name]
        pose = extract(turnaround.crop((left, 0, right, turnaround.height)), idle_bg)
        if name == "side":
            pose = pose.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        idle_scale = min(32 / pose.height, 34 / pose.width)
        pose = pose.resize((round(pose.width * idle_scale), round(pose.height * idle_scale)), Image.Resampling.NEAREST)
        base = Image.new("RGBA", (CELL, CELL))
        base.alpha_composite(pose, ((CELL - pose.width) // 2, CELL - 2 - pose.height))
        idle = []
        for offset in (0, 0, 1, 1):
            frame = Image.new('RGBA', (CELL, CELL))
            split = CELL - 10
            frame.alpha_composite(base.crop((0, 0, CELL, split)), (0, offset))
            frame.alpha_composite(base.crop((0, split, CELL, CELL)), (0, split))
            idle.append(frame)
        strip = Image.new('RGBA', (CELL * 12, CELL))
        for col, frame in enumerate(walk + idle):
            strip.alpha_composite(frame, (col*CELL, 0))
        strip.save(OUTPUT / f'hunter_{name}.png')
    (OUTPUT / 'hunter_sheet.json').write_text(json.dumps({'frame': [CELL, CELL], 'frames': 8, 'idle_start': 8, 'idle_frames': 4, 'facings': {'down':'front', 'left':'side', 'right':'side(mirrored)', 'up':'back'}}, indent=1) + '\n')

if __name__ == '__main__':
    main()
