# Generate 8 raw frames of the `debugger` outfit in fixed poses (no weapon, two fists on an invisible pole)

Quest Lab is a Python-learning RPG with dark Castlevania-style 16-bit pixel art. The hero wears different outfits. For scythes the weapon is
drawn separately by code, so each outfit needs hero frames holding **nothing**, with two closed fists gripping an invisible pole.
The default outfit (Tate) was already drawn this way and approved. Draw the **debugger** outfit in the same 8 poses.

## Look at (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/scythe-redo/pose-reference.png`: the approved Tate poses at 4x. Top row = 4 action frames, bottom row = 4 hurt frames. Copy each pose exactly.
- `docs/review-art/scythe-redo/outfits/debugger/design.png`: this outfit at 4x (top row action, bottom row hurt, different poses). Copy the clothes, colours, hair/head, skin tone, accessories and build from it.

## What to generate (use your image generation tool, one frame at a time, 8 frames)
Each frame: this outfit's hero (describe it from design.png), facing right, in the matching Tate pose, **both fists closed on an invisible pole with
nothing in his hands**, Castlevania-style 16-bit pixel art with a dark outline, light from the top-left, full body in frame with a little margin,
on a flat solid **pure chroma-green (#00FF00) background**, no ground, no shadow, no weapon, no text, no glow.
Keep the same character, colours and scale in all 8 frames. Make both fists clearly visible (skin or glove colour), not hidden under sleeves or capes.
If a frame is off-pose, off-model, holds any object, or has a hidden fist, regenerate it.

## Output
Save the 8 images (PNG or JPG, as generated, full size, no cleanup, no resizing, no cropping) into `docs/review-art/scythe-redo/outfits-agy/debugger/` as:
`action_1`, `action_2`, `action_3`, `action_4`, `hurt_1`, `hurt_2`, `hurt_3`, `hurt_4` (the extension is yours). Do not touch any other file and do not write scripts or
sprite sheets: a separate script cleans the frames afterwards. When done, list the files and name any frame you are unhappy with.
