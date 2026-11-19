# Draw the `debugger` outfit in the staff poses (no weapon, fists on an invisible staff)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero wears different outfits. For staves the weapon is drawn **separately by code**,
so each outfit needs hero frames that hold **nothing**, with a closed fist where the staff is gripped.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/outfits-new/_pose/staff.png`: Tate at 4x in the staff poses (top row = 4 action frames, bottom row = 4 hurt frames). **Copy these 8 poses exactly**: body angle,
  stance, head turn, where each hand is. In the reference he still holds a wooden staff: **do not draw it**, draw the same pose with the hand closed on an invisible staff.
  The reference sheets are `prototypes/godot-combat/art/held/base-tate-staff-action-sheet.png` and `base-tate-staff-hurt-sheet.png` (512x72, four 128x72 cells each).
- `docs/review-art/staff-redo/debugger/design.png`: this outfit. Copy the clothes, colours, hair/head, skin tone, accessories and build from it.
- `docs/review-art/scythe-redo/outfits/ivory/preview.png`: an approved finished sheet (Ivory in the scythe poses) for quality and style.

## Files to write (only into `docs/review-art/staff-redo/debugger/`)
- `action-sheet.png` and `hurt-sheet.png`: **512x72** each, four 128x72 cells, transparent background, hard pixel edges, alpha 0/255 only, no shadow, no glow, no text.
- `preview.png`: both sheets stacked at 4x with nearest-neighbour on a dark blue background.

## Hard requirements
- **No staff, pole, weapon or any object** in any frame. Each hand that held the staff in the reference is a **clearly visible closed fist** (skin or glove colour).
- **The same poses as the Tate reference** and the same scale: about 46 px tall, feet on row 69, body in the same place in the cell as Tate's. The same hero and outfit in all 8 frames.
- Dark outline, light from the top-left, palette true to the design image, at most about 28 colours.

## Method (required)
Use your **image generation tool**, one frame at a time (8 frames), with the matching Tate frame and the design image as references. Prompt: this outfit's hero (describe it
from the design image), facing right, in that pose, fist closed on an invisible staff, nothing in his hands, Castlevania-style 16-bit pixel art, dark outline, flat solid
chroma-green background, full body, no weapon, no text. Then clean each frame with a script: key out the background, crop to the hero, resize with nearest-neighbour so he is about
46 px tall, reduce to at most 28 colours with hard edges, set alpha to 0/255, and place him in the 128x72 cell with feet on row 69 and body in Tate's place. Compare each frame
against the Tate pose at 4x and regenerate any that is off-pose, off-model, holds an object, hides a fist or is muddy. Take as many attempts as you need. When done, list the files and name any frame you are unhappy with.
