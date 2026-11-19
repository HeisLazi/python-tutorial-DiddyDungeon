# Draw the `pilgrim` outfit in the new scythe poses (no weapon, two fists on an invisible pole)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. Its hero wears different outfits. For scythes the
weapon is drawn **separately by code**, so each outfit needs a hero sprite that holds **nothing**, with two closed fists gripping
an invisible pole.

The default outfit (Tate, black coat with gold trim) was already redrawn this way and approved. Your job is the same drawing for the
**pilgrim** outfit: same 8 poses, same size, same fist positions, but this outfit's clothes, colours, hair and build.

## Look at these first (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/scythe-redo/pose-reference.png`: the approved Tate sheets at 4x (top row = action, bottom row = hurt). **Copy these 8
  poses exactly**: body angle, stance, head turn, arm positions. The sheets themselves are `docs/review-art/scythe-redo/codex3/action-sheet.png`
  and `hurt-sheet.png` (512x72, four 128x72 cells each).
- `docs/review-art/scythe-redo/outfits/pilgrim/design.png`: this outfit at 4x in a different pose (top row action, bottom row hurt, 96px cells).
  This is the character design to draw: copy the clothes, colours, hair/head, skin tone, accessories and proportions from it.

## Files to write (only into `docs/review-art/scythe-redo/outfits/pilgrim/`)
- `action-sheet.png` and `hurt-sheet.png`: **512x72** each, four 128x72 cells, transparent background, hard pixel edges, no anti-aliasing,
  no shadow, no glow, no text.
- `preview.png`: both sheets stacked at 4x with nearest-neighbour on a dark blue background.

## Hard requirements
- **No weapon, no pole, no scythe, no object in his hands**, in any frame. Two closed fists only.
- **The same poses as the approved Tate sheets**, and the same scale: about 46 px tall (feet on row 69, body centred near x=60 in each cell).
- **The fists must sit where Tate's are** (within 2 px), because the weapon will be drawn through them by code. Cell pixel coordinates
  (x 0-127, y 0-71), rear fist then front fist, for the four action frames:
  (49,40) (76,48); (56,35) (53,25); (80,44) (88,40); (72,47) (85,46). In the four hurt frames keep the fists where the Tate hurt frames have them.
  Make the fists clearly visible (skin or glove), not hidden behind sleeves or capes.
- The same character in all 8 frames: same face, hair, outfit, colours, build, same boots baseline.
- Dark outline, light from the top-left, palette true to `design.png`, at most about 28 colours.

## Method (required)
Use your **image generation tool**, one frame at a time (8 frames), with the matching Tate pose frame and `design.png` as references.
Prompt: this outfit's hero (describe it from design.png), facing right, in that pose, both fists closed and gripping an invisible pole,
nothing in his hands, Castlevania-style 16-bit pixel art, dark outline, flat solid chroma-green background, full body, no weapon, no text.
Then clean each frame with a script: key out the background, crop to the hero, resize with nearest-neighbour so he is about 46 px tall,
reduce to at most 28 colours with hard edges, set alpha to 0/255, and place him in the 128x72 cell with feet on row 69 and body centred
near x=60. Compare each frame against the Tate pose at 4x and regenerate any frame that is off-pose, off-model, holds an object, has a
hidden fist, or is muddy. Take as many attempts as you need. When done, list the files and name any frame you are unhappy with.
