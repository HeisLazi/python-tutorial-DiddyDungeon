# Design the **Lanternscale Vest** outfit for the hero (step 1 of 2)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero (Tate: dark brown skin, black swept hair, athletic build) wears many
armours. The **Lanternscale Vest** (look id `lanternscale`, effect: {'reduction': 20, 'heal_on_objective': 2, 'impact': 1, 'on': 'explanation'}) must become its own **fully distinct outfit**, not a recolour of another one.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/lanternscale/icon.png`: this armour's icon. **This is the garment design**: its shapes, materials, colours and details.
- `docs/review-art/outfits-new/_pose/sword.png`: Tate at 4x in his sword poses (top row idle, then action, follow-through, hurt). Use the FIRST frame of the top row (the idle stance).
- `docs/review-art/scythe-redo/outfits/ivory/preview.png`: an example of an approved finished outfit sheet (the white Ivory coat) to match for quality and pixel-art style.

## Files to write (only into `docs/review-art/outfits-new/lanternscale/`)
1. `design.md`: a precise written spec of this outfit as worn by the hero: every garment and accessory, each material, the palette as hex colours (at most 14,
   light source top-left), what shows at the collar, shoulders, chest, waist, sleeves, legs, boots and gloves; how the silhouette differs from the old Tate coat
   (e.g. a shorter vest, plate pauldrons, a long cloak, a skirt of scales). The hero's face, skin tone and black swept hair do NOT change.
2. `master.png`: the hero wearing it in Tate's first idle sword frame pose, facing right, as a 96x72 pixel-art cell at **1x** (transparent background,
   hard pixel edges, about 42 px tall, feet near the bottom row, dark outline, no weapon, nothing in his hands) AND `master-large.png`: the same drawing
   generated large (about 512 px tall) on a flat chroma-green background for later reference.

## Rules
- It must read at a glance as the armour in the icon, and be clearly different in silhouette and colour from Tate's black coat, the white Ivory coat and the other outfits.
- No weapon, no text, no glow, no shadow. Pixel art, hard edges, at most about 28 colours.
- Use your image generation tool, check the result at 4x against the icon, and regenerate until it is faithful and clean. When done, list the files.
