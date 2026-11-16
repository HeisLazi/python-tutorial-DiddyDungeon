# Draw the **Lanternscale Vest** outfit in the `scythe` poses (step 2 of 2)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. You are drawing the hero (the same dark-skinned, black-haired hero) wearing the
**Lanternscale Vest** (look `lanternscale`) in the `scythe` weapon style: 8 frames in 2 sheet(s). The weapon is drawn separately by code,
so the hero holds **nothing**.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/lanternscale/design.md`, `master.png`, `master-large.png`, `icon.png`: this outfit's design. Copy it exactly.
- `docs/review-art/outfits-new/_pose/scythe.png`: Tate at 4x in the poses to copy (row 1 = action; row 2 = hurt). The Tate
  reference may still show a stub of its old weapon or glove colours: ignore those, draw the new outfit and leave hands empty.
- `docs/review-art/scythe-redo/outfits/ivory/preview.png`: an approved example of this kind of sheet (Ivory in the scythe poses) for quality and style.

## Files to write (only into `docs/review-art/outfits-new/lanternscale/scythe/`)
- `action-sheet.png`: 512x72, four 128x72 cells
- `hurt-sheet.png`: 512x72, four 128x72 cells
- `preview.png`: all sheets stacked at 4x with nearest-neighbour on a dark blue background.

## Hard requirements
- **No weapon, pole, staff, whip, spell effect or any object** in any frame. Hold style for this weapon: both fists closed on an invisible long pole, a forearm apart (2-3 px gap between them). Fists/hands clearly visible (skin or glove colour).
- **Copy each pose exactly** (body angle, stance, head turn, arm positions) and match Tate's **scale and place**: each frame's bounding box (x0, y0, x1, y1 in cell
  pixels) should be close to Tate's. Tate's boxes:
  - action: (21, 26, 67, 68), (27, 26, 61, 68), (15, 26, 72, 68), (18, 26, 69, 68)
  - hurt: (29, 26, 67, 68), (29, 26, 67, 68), (28, 26, 68, 68), (28, 26, 69, 68)
- The same hero and the same outfit in every frame (face, hair, garments, palette from design.md). Hard pixel edges, alpha 0 or 255 only, no shadow, no glow, no text,
  at most about 28 colours, dark outline, light from the top-left.

## Method (required)
Use your **image generation tool**, one frame at a time, with the matching Tate pose frame, `master-large.png` and `icon.png` as references. Prompt: the hero
wearing this outfit (describe it from design.md), facing right, in that pose, hands as described, nothing in his hands, Castlevania-style 16-bit pixel art, dark outline,
flat solid chroma-green background, full body, no weapon, no text. Then clean each frame with a script: key out the green, crop to the hero, resize with nearest-neighbour
to Tate's frame height, reduce colours with hard edges, set alpha to 0/255, and place him in his 128x72 cell on Tate's box. Compare every frame against the Tate pose at 4x and
regenerate any frame that is off-pose, off-model, holds an object, hides a hand, or is muddy. Take as many attempts as you need. When done, list the files and name any frame you are unhappy with.
