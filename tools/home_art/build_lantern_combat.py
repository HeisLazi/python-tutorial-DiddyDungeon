#!/usr/bin/env python3
"""Slice Lantern Vale poses with silhouette masks to prevent frame bleed.

Some attack poses extend into a neighbouring cell. Mask the four connected
figures before cropping, while keeping the original source scale and baseline.
"""
from pathlib import Path
import runpy
import sys
from PIL import Image

root = Path(__file__).resolve().parents[2]
combat = root / 'prototypes/godot-combat'
source_dir = combat / 'source-art/tutorial'
dest = combat / 'art/lantern'
dest.mkdir(parents=True, exist_ok=True)
sys.argv = [sys.argv[0], '__skip__']
components_of = runpy.run_path(str(combat / 'source-art/slice_animations.py'))['components_of']
for path in sorted(source_dir.glob('*-concept.png')):
    source = Image.open(path).convert('RGBA')
    width, height = source.size
    components = components_of(source)
    if len(components) != 4:
        raise ValueError(f'{path.name}: expected four separate poses, found {len(components)}')
    sheet = Image.new('RGBA', (512, 72))
    source_cell_width = round(height * 128 / 72)
    for frame, points in enumerate(components):
        mask = Image.new('L', source.size)
        pixels = mask.load()
        for x, y in points:
            pixels[x, y] = 255
        isolated = Image.new('RGBA', source.size)
        isolated.paste(source, (0, 0), mask)
        center = round((frame + 0.5) * width / 4)
        left = center - source_cell_width // 2
        crop = isolated.crop((left, 0, left + source_cell_width, height))
        sheet.alpha_composite(crop.resize((128, 72), Image.Resampling.NEAREST), (frame * 128, 0))
    sheet.save(dest / (path.stem.removesuffix('-concept') + '.png'), optimize=True)
