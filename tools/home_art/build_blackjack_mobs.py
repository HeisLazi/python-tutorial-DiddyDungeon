#!/usr/bin/env python3
"""Slice four illustrated Blackjack encounters without neighbouring-pose bleed."""
from pathlib import Path
import runpy
import sys
from PIL import Image
root=Path(__file__).resolve().parents[2]
combat=root/'prototypes/godot-combat'
sys.argv=[sys.argv[0],'__skip__']
components_of=runpy.run_path(str(combat/'source-art/slice_animations.py'))['components_of']
for name in ('empty-table','dealers-hand','count-keeper','hitman','bust-hound','house-clerk','judge','rematch-shade'):
    source=Image.open(combat/f'source-art/blackjack/{name}-concept.png').convert('RGBA')
    components=components_of(source)
    if len(components)!=4: raise ValueError(f'{name}: expected 4 poses, found {len(components)}')
    sheet=Image.new('RGBA',(512,72))
    for frame in range(4):
        # The Hitman's second generated pose stands fully upright; keep the
        # crouched idle so the enemy does not pop between different heights.
        idx=0 if name=='hitman' and frame==1 else frame
        mask=Image.new('L',source.size); px=mask.load()
        for x,y in components[idx]: px[x,y]=255
        clean=Image.new('RGBA',source.size);clean.paste(source,(0,0),mask)
        center=round((idx+.5)*source.width/4); crop_width=round(source.height*128/72)
        left=center-crop_width//2
        crop=clean.crop((left,0,left+crop_width,source.height))
        sheet.alpha_composite(crop.resize((128,72),Image.Resampling.NEAREST),(frame*128,0))
    sheet.save(combat/f'art/blackjack/{name}.png',optimize=True)
