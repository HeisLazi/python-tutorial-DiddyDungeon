# Draw 7 `greatsword` weapons as real pixel art (batch 1)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero sprite is chunky pixel art with a 1 px dark outline.
Held weapons are currently the painted Market icons shrunk onto the sprite, which looks soft and off-style. Redraw each weapon below **natively as pixel art**
so it matches the hero. A script will rotate each one and place it in the hero's hands, so you only draw it **straight and horizontal**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/_pose/greatsword.png` if it exists (the hero at 4x, to judge the pixel density), and `docs/review-art/scythe-redo/outfits/ivory/preview.png`: a finished hero sheet.
- Each weapon's painted icon (table below): copy its **design**: silhouette, materials, ornament, colours.

| Item id | Name | Icon | Notes |
|---|---|---|---|
| lv-03 | Wayfinder Hammer | `docs/review-art/weapons-native/greatsword/icons/lv-03.png` | {'impact': 2, 'on': 'bug_diagnosis', 'chip_heavy': 1} |
| bj-the-shoe-splitter | The Shoe Splitter | `docs/review-art/weapons-native/greatsword/icons/bj-the-shoe-splitter.png` | {'impact': 2, 'on': 'any', 'break_coins': 3, 'chip_heavy': 2} |
| cas-coin-roll-club | Coin Roll Club | `docs/review-art/weapons-native/greatsword/icons/cas-coin-roll-club.png` | {'impact': 1, 'on': 'prediction', 'coin_clean': 1, 'chip_heavy': 1} |
| cas-lever-arm-mace | Lever Arm Mace | `docs/review-art/weapons-native/greatsword/icons/cas-lever-arm-mace.png` | {'impact': 1, 'on': 'any', 'opening_impact': 1, 'chip_heavy': 1} |
| cas-jackpot-hammer | Jackpot Hammer | `docs/review-art/weapons-native/greatsword/icons/cas-jackpot-hammer.png` | {'impact': 2, 'on': 'any', 'break_coins': 3, 'chip_heavy': 2, 'coin_clean': 1} |
| dc-deepvein-warhammer | Deepvein Warhammer | `docs/review-art/weapons-native/greatsword/icons/dc-deepvein-warhammer.png` | {'impact': 2, 'on': 'bug_diagnosis', 'chip_heavy': 2, 'chip_low': 1} |
| dc-the-core-breaker | The Core Breaker | `docs/review-art/weapons-native/greatsword/icons/dc-the-core-breaker.png` | {'impact': 3, 'on': 'any', 'break_coins': 6, 'chip_heavy': 2, 'break_guard': 1} |

## Sprite spec (every weapon)
- **Horizontal**: the butt/pommel at the LEFT, the tip or head at the RIGHT, the long axis along the centre row. Total length **about 52 px**; blade or head 8-12 px at the widest, grip 3-4 px.
- Transparent background, **hard pixel edges, alpha 0 or 255 only**, a **1 px dark outline** (about #16101a) all round, at most **12 colours**, light from the top-left, a one-pixel highlight along the lit edge, simple 2-3 tone shading. No anti-aliasing, no glow, no motion trail, no text, no hand or arm.
- Keep the weapon's identity at this tiny size: the skull on a gravekeeper's scythe, the gears on a clockwork blade, the coin on a coin club, the runes on a casting item. Drop detail that cannot be read in 52 px.
- Canvas = the weapon's tight bounding box plus 2 px of transparent margin on every side.

## Output (only into `docs/review-art/weapons-native/greatsword/`)
For each item id: `<item id>.png` (the sprite) and `<item id>.json` with `{"grip": X}` where X is the x pixel (from the left edge of the PNG) where the hero's fist closes on it (the centre of the handle or shaft grip).
Also write `contact-sheet-1.png`: all sprites in this batch at 6x on a dark blue background with labels.

## Method (required)
Use your **image generation tool** to draw each weapon large and straight on a flat chroma-green background, then clean it with a script: key out the green, crop, resize with nearest-neighbour to the length above, reduce colours with hard edges, add the 1 px outline, set alpha to 0/255. Review each at 6x against its icon and regenerate any that is muddy, off-design, bent, or not horizontal. When done, list the files and name any you are unhappy with.
