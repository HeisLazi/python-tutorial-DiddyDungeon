# Draw 6 `greatsword` weapons as real pixel art (batch 2)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero sprite is chunky pixel art with a 1 px dark outline.
Held weapons are currently the painted Market icons shrunk onto the sprite, which looks soft and off-style. Redraw each weapon below **natively as pixel art**
so it matches the hero. A script will rotate each one and place it in the hero's hands, so you only draw it **straight and horizontal**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/_pose/greatsword.png` if it exists (the hero at 4x, to judge the pixel density), and `docs/review-art/scythe-redo/outfits/ivory/preview.png`: a finished hero sheet.
- Each weapon's painted icon (table below): copy its **design**: silhouette, materials, ornament, colours.

| Item id | Name | Icon | Notes |
|---|---|---|---|
| hunter-sparring-greatsword | Hunter's Greatsword | `docs/review-art/weapons-native/greatsword/icons/hunter-sparring-greatsword.png` | {'impact': 1, 'on': 'code_checkpoint', 'chip_heavy': 1} |
| merchant-nightfall-greatsword | Nightfall Greatsword | `docs/review-art/weapons-native/greatsword/icons/merchant-nightfall-greatsword.png` | {'retry_impact': 2, 'chip_heavy': 1} |
| campaign-dungeon-iron-greatsword | Faultbreaker | `docs/review-art/weapons-native/greatsword/icons/campaign-dungeon-iron-greatsword.png` | {'impact': 2, 'on': 'bug_diagnosis', 'retry_impact': 2, 'chip_heavy': 1} |
| campaign-dungeon-minotaur-edge | Minotaur’s Judgment | `docs/review-art/weapons-native/greatsword/icons/campaign-dungeon-minotaur-edge.png` | {'impact': 2, 'on': 'code_checkpoint', 'chip_low': 2, 'chip_heavy': 1} |
| campaign-dungeon-clockwork-greatblade | Automaton’s Greatblade | `docs/review-art/weapons-native/greatsword/icons/campaign-dungeon-clockwork-greatblade.png` | {'impact': 2, 'on': 'bug_diagnosis', 'retry_impact': 3, 'chip_heavy': 1} |
| hunter-gravebound-greatblade | Gravebound Greatblade | `docs/review-art/weapons-native/greatsword/icons/hunter-gravebound-greatblade.png` | {'retry_impact': 2, 'heal_on_break': 2, 'chip_heavy': 1, 'chip_low': 1} |

## Sprite spec (every weapon)
- **Horizontal**: the butt/pommel at the LEFT, the tip or head at the RIGHT, the long axis along the centre row. Total length **about 52 px**; blade or head 8-12 px at the widest, grip 3-4 px.
- Transparent background, **hard pixel edges, alpha 0 or 255 only**, a **1 px dark outline** (about #16101a) all round, at most **12 colours**, light from the top-left, a one-pixel highlight along the lit edge, simple 2-3 tone shading. No anti-aliasing, no glow, no motion trail, no text, no hand or arm.
- Keep the weapon's identity at this tiny size: the skull on a gravekeeper's scythe, the gears on a clockwork blade, the coin on a coin club, the runes on a casting item. Drop detail that cannot be read in 52 px.
- Canvas = the weapon's tight bounding box plus 2 px of transparent margin on every side.

## Output (only into `docs/review-art/weapons-native/greatsword/`)
For each item id: `<item id>.png` (the sprite) and `<item id>.json` with `{"grip": X}` where X is the x pixel (from the left edge of the PNG) where the hero's fist closes on it (the centre of the handle or shaft grip).
Also write `contact-sheet-2.png`: all sprites in this batch at 6x on a dark blue background with labels.

## Method (required)
Use your **image generation tool** to draw each weapon large and straight on a flat chroma-green background, then clean it with a script: key out the green, crop, resize with nearest-neighbour to the length above, reduce colours with hard edges, add the 1 px outline, set alpha to 0/255. Review each at 6x against its icon and regenerate any that is muddy, off-design, bent, or not horizontal. When done, list the files and name any you are unhappy with.
