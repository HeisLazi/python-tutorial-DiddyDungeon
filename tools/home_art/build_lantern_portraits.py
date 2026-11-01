#!/usr/bin/env python3
"""Prepare the two idle poses used by Lantern Vale's encounter portraits."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
src = ROOT / 'prototypes/godot-combat/source-art/tutorial'
out = ROOT / 'ide/frontend/public/campaign-art/lantern-vale'
out.mkdir(parents=True, exist_ok=True)
# Bounds isolate each idle pose from the adjacent action poses.
BOUNDS = {
    'broken-number': ((52, 560), (576, 1100)), 'clockwork-caravan': ((56, 536), (572, 1068)),
    'counting-moth': ((48, 532), (572, 1048)), 'delivery-beast': ((40, 536), (568, 1088)),
    'endless-echo': ((28, 488), (512, 980)), 'first-spark': ((80, 488), (640, 1032)),
    'inventory-drowner': ((64, 528), (580, 1048)), 'little-lantern': ((76, 492), (576, 1008)),
    'mapkeeper': ((48, 472), (608, 1016)), 'memory-keeper': ((56, 484), (532, 968)),
    'module-mason': ((20, 500), (568, 1040)), 'remembering-shade': ((48, 480), (544, 984)),
    'selfless-golem': ((56, 452), (528, 940)), 'test-lantern': ((104, 508), (584, 972)),
    'unwritten-king': ((0, 543), (543, 1086)), 'unwritten-road': ((64, 496), (548, 1008)),
    'whispering-gate': ((32, 536), (580, 1080)),
    'transformation-sprite': ((52, 508), (584, 1040)), 'quiet-flame': ((84, 412), (632, 972)),
}
for name, bounds in BOUNDS.items():
    source = Image.open(src / (name + '-concept.png')).convert('RGBA')
    sheet = Image.new('RGBA', (128, 72))
    for frame, (left, right) in enumerate(bounds):
        crop = source.crop((left, 0, right + 4, 724))
        crop.thumbnail((54, 72), Image.Resampling.NEAREST)
        sheet.alpha_composite(crop, (frame * 64 + (64 - crop.width) // 2, 0))
    sheet.save(out / (name + '.png'), optimize=True)
for name, file in [('nameless-wraith', 'wraith-v2'), ('forked-path', 'forked-path')]:
    source = Image.open(ROOT / 'prototypes/godot-combat/art' / (file + '-sheet.png')).convert('RGBA')
    sheet = Image.new('RGBA', (128, 72))
    for frame in range(2):
        crop = source.crop((frame * 128, 0, (frame + 1) * 128, 72))
        bbox = crop.getbbox()
        if bbox:
            crop = crop.crop(bbox)
        crop.thumbnail((54, 64), Image.Resampling.NEAREST)
        sheet.alpha_composite(crop, (frame * 64 + (64 - crop.width) // 2, 72 - crop.height))
    sheet.save(out / (name + '.png'), optimize=True)
