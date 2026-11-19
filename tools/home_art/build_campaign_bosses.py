#!/usr/bin/env python3
"""Build campaign boss poses and 320x180 arenas from editable art studies."""
from pathlib import Path
import runpy
import sys
from PIL import Image, ImageOps
root = Path(__file__).resolve().parents[2]
combat = root / 'prototypes/godot-combat'
sys.argv = [sys.argv[0], '__skip__']
components_of = runpy.run_path(str(combat / 'source-art/slice_animations.py'))['components_of']
for name, anchors in {'silver-mogul': (270, 800, 1320, 1850), 'tozza': (270, 800, 1320, 1850)}.items():
    source = Image.open(combat / f'source-art/bosses/{name}-concept.png').convert('RGBA')
    components = components_of(source)
    if len(components) != 4:
        raise ValueError(f'{name}: expected four poses, found {len(components)}')
    sheet = Image.new('RGBA', (512,72))
    for i, (points, anchor) in enumerate(zip(components, anchors)):
        mask=Image.new('L', source.size); pixels=mask.load()
        for x,y in points: pixels[x,y]=255
        clean=Image.new('RGBA',source.size);clean.paste(source,(0,0),mask)
        crop=clean.crop((anchor-640,0,anchor+640,720))
        sheet.alpha_composite(crop.resize((128,72),Image.Resampling.NEAREST),(i*128,0))
    sheet.save(combat / f'art/{name}-sheet.png', optimize=True)
for name in ('unwritten-king', 'silver-mogul', 'tozza'):
    image = Image.open(combat / f'source-art/bosses/{name}-arena-concept.png').convert('RGB')
    ImageOps.fit(image,(320,180),method=Image.Resampling.LANCZOS).save(combat / f'art/{name}-arena.png',optimize=True)
