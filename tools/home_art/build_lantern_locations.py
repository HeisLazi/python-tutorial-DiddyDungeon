#!/usr/bin/env python3
"""Prepare pixel-sized Forge backdrops for the four Lantern Vale acts."""
from pathlib import Path
from PIL import Image

root = Path(__file__).resolve().parents[2]
source = root / 'prototypes/godot-combat/source-art/tutorial-locations'
out = root / 'ide/frontend/public/campaign-art/lantern-vale/locations'
out.mkdir(parents=True, exist_ok=True)
for name in ('first-light', 'vale-road', 'workshop', 'living-vale'):
    image = Image.open(source / (name + '.png')).convert('RGB')
    image.resize((320, 180), Image.Resampling.NEAREST).save(out / (name + '.png'), optimize=True)
