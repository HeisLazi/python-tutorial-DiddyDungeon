# Draw 5 `scythe` weapons as real pixel art (batch 1)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero sprite is chunky pixel art with a 1 px dark outline.
Held weapons are currently the painted Market icons shrunk onto the sprite, which looks soft and off-style. Redraw each weapon below **natively as pixel art**
so it matches the hero. A script will rotate each one and place it in the hero's hands, so you only draw it **straight and horizontal**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/_pose/scythe.png` if it exists (the hero at 4x, to judge the pixel density), and `docs/review-art/scythe-redo/outfits/ivory/preview.png`: a finished hero sheet.
- Each weapon's painted icon (table below): copy its **design**: silhouette, materials, ornament, colours.

| Item id | Name | Icon | Notes |
|---|---|---|---|
| hunter-sparring-scythe | Hunter's Scythe | `docs/review-art/weapons-native/scythe/icons/hunter-sparring-scythe.png` | {'impact': 1, 'on': 'bug_diagnosis', 'chip_finish': 1} |
| hunter-jack-scythe | Jack-o’ Scythe | `docs/review-art/weapons-native/scythe/icons/hunter-jack-scythe.png` | {'impact': 1, 'on': 'prediction', 'chip_finish': 1, 'opening_impact': 1, 'coin_clean': 1} |
| campaign-dungeon-grave-scythe | Gravekeeper’s Scythe | `docs/review-art/weapons-native/scythe/icons/campaign-dungeon-grave-scythe.png` | {'impact': 1, 'on': 'bug_diagnosis', 'break_coins': 2, 'heal_on_break': 3, 'chip_finish':  |
| campaign-dungeon-undertow-scythe | Hoardbreaker Scythe | `docs/review-art/weapons-native/scythe/icons/campaign-dungeon-undertow-scythe.png` | {'impact': 2, 'on': 'bug_diagnosis', 'chip_finish': 2, 'break_guard': 1} |
| dc-miner-s-pickaxe | Miner's Pickaxe | `docs/review-art/weapons-native/scythe/icons/dc-miner-s-pickaxe.png` | {'impact': 1, 'on': 'code_checkpoint', 'chip_finish': 1, 'chip_heavy': 1} |

## Sprite spec (every weapon)
- **Horizontal**: the butt/pommel at the LEFT, the tip or head at the RIGHT, the long axis along the centre row. Total length **about 56 px**; shaft 3 px, head up to 18 px across.
- Transparent background, **hard pixel edges, alpha 0 or 255 only**, a **1 px dark outline** (about #16101a) all round, at most **12 colours**, light from the top-left, a one-pixel highlight along the lit edge, simple 2-3 tone shading. No anti-aliasing, no glow, no motion trail, no text, no hand or arm.
- Keep the weapon's identity at this tiny size: the skull on a gravekeeper's scythe, the gears on a clockwork blade, the coin on a coin club, the runes on a casting item. Drop detail that cannot be read in 56 px.
- Canvas = the weapon's tight bounding box plus 2 px of transparent margin on every side.

## Output (only into `docs/review-art/weapons-native/scythe/`)
For each item id: `<item id>.png` (the sprite) and `<item id>.json` with `{"grip": X}` where X is the x pixel (from the left edge of the PNG) where the hero's fist closes on it (the centre of the handle or shaft grip).
Also write `contact-sheet-1.png`: all sprites in this batch at 6x on a dark blue background with labels.

## Method (required)
Use your **image generation tool** to draw each weapon large and straight on a flat chroma-green background, then clean it with a script: key out the green, crop, resize with nearest-neighbour to the length above, reduce colours with hard edges, add the 1 px outline, set alpha to 0/255. Review each at 6x against its icon and regenerate any that is muddy, off-design, bent, or not horizontal. When done, list the files and name any you are unhappy with.
