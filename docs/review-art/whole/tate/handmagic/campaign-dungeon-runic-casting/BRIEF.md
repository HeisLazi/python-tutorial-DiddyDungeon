# Redraw the `tate` hero's handmagic sheets with him holding the **Scribe’s Rune Focus**

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero in the `tate` outfit has finished, approved sprite sheets for the handmagic style, holding a
default casting focus. They are the quality bar. Make the same sheets with one change: **the weapon in his hands is the Scribe’s Rune Focus**. Hero and weapon are drawn
**together as one sprite**, exactly as in the originals, so his hands really grip it.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/whole/_ref/tate-handmagic/<key>-sheet.png` for key in ['action', 'hurt']: the originals (512x72, four 128x72 cells each).
- `docs/review-art/whole/_ref/tate-handmagic/<key>_1.png` .. `<key>_4.png`: each original frame at 8x on green. Use the matching one as the image reference for each frame.
- `docs/review-art/whole/tate/handmagic/campaign-dungeon-runic-casting/icon.png`: the Scribe’s Rune Focus. Copy its design: silhouette, materials, ornament and colours.

## Files to write (only into `docs/review-art/whole/tate/handmagic/campaign-dungeon-runic-casting/`)
- `action-sheet.png`, `hurt-sheet.png`: 512x72 each, four 128x72 cells, transparent background, hard pixel edges, alpha 0 or 255 only.
- `preview.png`: for each sheet the ORIGINAL then YOURS, stacked, at 4x nearest-neighbour on a dark blue background.

## Hard requirements
- **Same hero, same pose, same place** in every frame: the same face, hair and outfit; body angle, stance and hands where the original has them. His body is the same size and sits
  on the same pixels as the original (feet on the same row, head at the same height). Check by overlaying your frame on the original.
- **The weapon is the Scribe’s Rune Focus**, held exactly where the original weapon is held: gripped by the same hand(s), at the same angle, about the same total length, pointing the same way.
  Match the original weapon's thickness and pixel density: thin clean lines and simple shading, no thick outline blobs, no oversized head, no blur. Frames where the original shows
  no weapon (if any) stay weapon-less. Keep any spell or motion effect the original has.
- **The handle matters as much as the head.** Draw the Scribe’s Rune Focus's own handle or shaft from the icon (its colour, wrap and fittings), not the original weapon's. It is one
  straight, unbroken line of constant thickness that visibly passes through the gripping fist(s) and comes out the other side, with the same length and colours in every frame.
- The weapon stays inside the cell in every frame and is the same weapon, same colours, in every frame of every sheet.
- No added glow, shadow or text. At most about 30 colours.

## Method (required)
Use your **image generation tool**, one frame at a time, giving it the matching 8x reference frame and the icon: "the same sprite in the same pose, but the weapon is replaced by
<describe the Scribe’s Rune Focus from the icon>, held the same way, 16-bit Castlevania pixel art, flat chroma-green background". Then clean each frame with a script: key out the green, resize
with nearest-neighbour by the factor that makes the hero's body the same height as in the original frame, snap alpha to 0/255, reduce colours with hard edges, and place it in the
128x72 cell so the feet and head coincide with the original's. Compare with the original at 4x and regenerate any frame where the hero is off-model or moved, the hands are not on
the weapon, or the weapon is the wrong size, cut off, blobby or inconsistent with the other frames. Take as many attempts as you need; quality matters more than speed.
When done, list the files and name any frame you are unhappy with.
