#!/usr/bin/env python3
"""Make pixel-sized inventory icons from transparent Lantern Vale item art."""
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parents[2]
source = root / 'prototypes/godot-combat/source-art/trinkets'
out = root / 'ide/frontend/public/campaign-art/items'
out.mkdir(parents=True, exist_ok=True)
for path in list(source.glob('*.png')) + list((source.parent / 'weapons').glob('*.png')):
    image = Image.open(path).convert('RGBA')
    bbox = image.getchannel('A').point(lambda a: 255 if a > 80 else 0).getbbox()
    if not bbox:
        raise ValueError(f'Empty item art: {path}')
    image = image.crop(bbox)
    image.thumbnail((56, 56), Image.Resampling.NEAREST)
    icon = Image.new('RGBA', (64, 64))
    icon.alpha_composite(image, ((64-image.width)//2, (64-image.height)//2))
    icon.save(out / path.name, optimize=True)
