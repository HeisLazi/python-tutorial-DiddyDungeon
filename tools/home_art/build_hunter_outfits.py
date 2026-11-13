#!/usr/bin/env python3
"""Build 38px Home walk/idle strips from the authored outfit turnarounds.

Run with system Python and Pillow. Each source preserves the original hunter
walk sheet's four poses per facing; 8 walk frames repeat that four-pose cycle.
"""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'tools/home_art/sheets/hunter_outfits'
OUTPUT = ROOT / 'ide/home-godot/art'
CELL = 38


def extract(image):
    image = image.convert('RGBA')
    # Generated sheets have translucent glow around figures. Keep solid art
    # only, so black or white halos do not travel across the lit Home scene.
    alpha = image.getchannel('A').point(lambda a: 255 if a >= 180 else 0)
    image.putalpha(alpha)
    box = alpha.getbbox()
    if not box:
        raise ValueError('empty outfit pose')
    return image.crop(box)


def shrink(image, size, outfit):
    """Nearest-neighbour for hand-gridded art; area average for the Wardplate's fine beadwork.

    Nearest-neighbour turns the Wardplate's tiny beads into white speckle, so it is averaged in
    premultiplied alpha and the edge is snapped back to hard alpha.
    """
    if outfit != 'wardplate':
        return image.resize(size, Image.Resampling.NEAREST)
    small = image.convert('RGBa').resize(size, Image.Resampling.BOX).convert('RGBA')
    small.putalpha(small.getchannel('A').point(lambda a: 255 if a >= 128 else 0))
    return small


def build(outfit):
    source = Image.open(SOURCE / outfit / 'walk_source.png').convert('RGBA')
    turnaround = Image.open(SOURCE / outfit / 'turnaround.png').convert('RGBA')
    if source.size != (1536, 1024) or turnaround.size != (2172, 724):
        raise ValueError(f'{outfit}: source dimensions changed; review crop coordinates')
    xs = [0, 440, 765, 1090, 1536]
    ys = [0, 340, 660, 1024]
    idle_bounds = {'front': (0, 620), 'side': (620, 1030), 'back': (1030, 1510)}
    for row, direction in enumerate(('front', 'side', 'back')):
        frames = []
        for col in range(4):
            frame = extract(source.crop((xs[col], ys[row], xs[col + 1], ys[row + 1])))
            if direction == 'side' and (outfit == 'norse' or col > 0):
                frame = frame.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            frames.append(frame)
        scale = min(32 / max(f.height for f in frames), 34 / max(f.width for f in frames))
        cells = []
        for frame in frames:
            frame = shrink(frame, (max(1, round(frame.width * scale)), max(1, round(frame.height * scale))), outfit)
            cell = Image.new('RGBA', (CELL, CELL))
            cell.alpha_composite(frame, ((CELL - frame.width) // 2, CELL - 2 - frame.height))
            cells.append(cell)
        left, right = idle_bounds[direction]
        pose = extract(turnaround.crop((left, 0, right, turnaround.height)))
        if direction == 'side':
            pose = pose.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        scale = min(32 / pose.height, 34 / pose.width)
        pose = shrink(pose, (round(pose.width * scale), round(pose.height * scale)), outfit)
        base = Image.new('RGBA', (CELL, CELL))
        base.alpha_composite(pose, ((CELL - pose.width) // 2, CELL - 2 - pose.height))
        idle = []
        for offset in (0, 0, 1, 1):
            cell = Image.new('RGBA', (CELL, CELL))
            split = CELL - 10
            cell.alpha_composite(base.crop((0, 0, CELL, split)), (0, offset))
            cell.alpha_composite(base.crop((0, split, CELL, CELL)), (0, split))
            idle.append(cell)
        sheet = Image.new('RGBA', (CELL * 12, CELL))
        for col, cell in enumerate(cells * 2 + idle):
            sheet.alpha_composite(cell, (col * CELL, 0))
        sheet.save(OUTPUT / f'hunter_{outfit}_{direction}.png')


if __name__ == '__main__':
    for name in ('ivory', 'warden', 'harvest', 'arcane', 'patchwork', 'pilgrim', 'wayfarer', 'norse', 'lanternkeeper', 'wardplate'):
        build(name)
