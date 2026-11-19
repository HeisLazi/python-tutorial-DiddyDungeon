#!/usr/bin/env python3
"""Slice The House's overlapping attack poses using their connected silhouettes."""
from pathlib import Path
import runpy
import sys
from PIL import Image, ImageOps

root = Path(__file__).resolve().parents[2]
combat = root / 'prototypes/godot-combat'
# Reuse the pixel component slicer without triggering its sheet build loop.
sys.argv = [sys.argv[0], '__slice_house_only__']
components_of = runpy.run_path(str(combat / 'source-art/slice_animations.py'))['components_of']
source = Image.open(combat / 'source-art/bosses/the-house-concept.png').convert('RGBA')
components = components_of(source)
if len(components) != 4:
    raise ValueError(f'Expected four separate House poses, found {len(components)}')
sheet = Image.new('RGBA', (512, 72))
for frame, (points, anchor) in enumerate(zip(components, (270, 800, 1320, 1850))):
    mask = Image.new('L', source.size)
    mask_pixels = mask.load()
    for x, y in points:
        mask_pixels[x, y] = 255
    clean = Image.new('RGBA', source.size)
    clean.paste(source, (0, 0), mask)
    crop = clean.crop((anchor - 640, 0, anchor + 640, 720))
    sheet.alpha_composite(crop.resize((128, 72), Image.Resampling.NEAREST), (frame * 128, 0))
sheet.save(combat / 'art/the-house-sheet.png', optimize=True)
bg = Image.open(combat / 'source-art/bosses/the-house-arena-concept.png').convert('RGB')
ImageOps.fit(bg, (320, 180), method=Image.Resampling.LANCZOS).save(combat / 'art/the-house-arena.png', optimize=True)
