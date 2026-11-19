# Draw 6 `sword` weapons as real pixel art (batch 1)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero sprite is chunky pixel art with a 1 px dark outline.
Held weapons are currently the painted Market icons shrunk onto the sprite, which looks soft and off-style. Redraw each weapon below **natively as pixel art**
so it matches the hero. A script will rotate each one and place it in the hero's hands, so you only draw it **straight and horizontal**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/_pose/sword.png` if it exists (the hero at 4x, to judge the pixel density), and `docs/review-art/scythe-redo/outfits/ivory/preview.png`: a finished hero sheet.
- Each weapon's painted icon (table below): copy its **design**: silhouette, materials, ornament, colours.

| Item id | Name | Icon | Notes |
|---|---|---|---|
| lv-01 | Trailkeeper Blade | `docs/review-art/weapons-native/sword/icons/lv-01.png` | {'impact': 1, 'on': 'code_checkpoint', 'chip_streak': 1} |
| lv-02 | Lantern Guard Sword | `docs/review-art/weapons-native/sword/icons/lv-02.png` | {'impact': 1, 'on': 'any', 'heal_clean': 1} |
| lv-05 | Dawnbringer | `docs/review-art/weapons-native/sword/icons/lv-05.png` | {'impact': 1, 'on': 'any', 'opening_impact': 2, 'heal_on_break': 4, 'chip_streak': 2, 'bre |
| bj-card-edge-dagger | Card-Edge Dagger | `docs/review-art/weapons-native/sword/icons/bj-card-edge-dagger.png` | {'impact': 1, 'on': 'code_checkpoint', 'chip_follow': 1} |
| bj-ace-of-spades-blade | Ace of Spades Blade | `docs/review-art/weapons-native/sword/icons/bj-ace-of-spades-blade.png` | {'impact': 2, 'on': 'bug_diagnosis', 'chip_streak': 1, 'coin_clean': 1} |
| bj-the-house-cutter | The House Cutter | `docs/review-art/weapons-native/sword/icons/bj-the-house-cutter.png` | {'impact': 2, 'on': 'explanation', 'break_coins': 8, 'coin_clean': 2, 'chip_clean': 1} |

## Sprite spec (every weapon)
- **Horizontal**: the butt/pommel at the LEFT, the tip or head at the RIGHT, the long axis along the centre row. Total length **about 34 px**; blade 5-7 px wide at the widest, hilt 3-4 px.
- Transparent background, **hard pixel edges, alpha 0 or 255 only**, a **1 px dark outline** (about #16101a) all round, at most **12 colours**, light from the top-left, a one-pixel highlight along the lit edge, simple 2-3 tone shading. No anti-aliasing, no glow, no motion trail, no text, no hand or arm.
- Keep the weapon's identity at this tiny size: the skull on a gravekeeper's scythe, the gears on a clockwork blade, the coin on a coin club, the runes on a casting item. Drop detail that cannot be read in 34 px.
- Canvas = the weapon's tight bounding box plus 2 px of transparent margin on every side.

## Output (only into `docs/review-art/weapons-native/sword/`)
For each item id: `<item id>.png` (the sprite) and `<item id>.json` with `{"grip": X}` where X is the x pixel (from the left edge of the PNG) where the hero's fist closes on it (the centre of the handle or shaft grip).
Also write `contact-sheet-1.png`: all sprites in this batch at 6x on a dark blue background with labels.

## Method (required)
Use your **image generation tool** to draw each weapon large and straight on a flat chroma-green background, then clean it with a script: key out the green, crop, resize with nearest-neighbour to the length above, reduce colours with hard edges, add the 1 px outline, set alpha to 0/255. Review each at 6x against its icon and regenerate any that is muddy, off-design, bent, or not horizontal. When done, list the files and name any you are unhappy with.
