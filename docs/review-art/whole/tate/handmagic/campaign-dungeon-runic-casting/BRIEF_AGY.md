# Generate raw frames: the `tate` hero in the handmagic poses holding the **Scribe’s Rune Focus**

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero has finished, approved sprite frames for the handmagic style holding a default weapon.
Generate the same frames with one change: **the weapon in his hands is the Scribe’s Rune Focus**. Hero and weapon are drawn together as one sprite so his hands really grip it.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/whole/_ref/tate-handmagic/<frame>.png` for the frames `action_1`, `action_2`, `action_3`, `action_4`, `hurt_1`, `hurt_2`, `hurt_3`, `hurt_4`: each original frame at 8x on green. Use the matching one as the image reference.
- `docs/review-art/whole/tate/handmagic/campaign-dungeon-runic-casting/icon.png`: the Scribe’s Rune Focus. Copy its design: silhouette, materials, ornament and colours.

## What to generate (your image generation tool, one image per frame, 8 frames)
"The same sprite in the same pose and framing, but the weapon is replaced by <describe the Scribe’s Rune Focus from the icon>, held the same way by the same hand(s), 16-bit Castlevania pixel art,
dark outline, flat solid pure chroma-green (#00FF00) background, no shadow, no text."
- The hero is unchanged: same face, hair, outfit, pose, proportions. Whole hero and whole weapon inside the image with a margin.
- The weapon is held where the original is held, at the same angle and about the same length, thin and clean like the original (no oversized head, no blobs).
- **The handle matters as much as the head**: the Scribe’s Rune Focus's own handle from the icon, one straight unbroken line of constant thickness that passes through the gripping fist(s),
  with the same colours and length in every frame. The same weapon in every frame.
- A frame whose original shows no weapon stays weapon-less. Keep any spell or motion effect the original has.
- Regenerate any frame where the hero changed, a hand is off the weapon, or the weapon is the wrong size, broken or inconsistent.

## Output
Save the images as generated (PNG or JPG, full size, no cleanup, no resizing, no cropping) into `docs/review-art/whole/tate/handmagic/campaign-dungeon-runic-casting/raw/` named exactly `action_1`, `action_2`, `action_3`, `action_4`, `hurt_1`, `hurt_2`, `hurt_3`, `hurt_4` plus the extension.
Do not write scripts or sprite sheets and do not touch any other file: a separate script cleans the frames. When done, list the files and name any frame you are unhappy with.
