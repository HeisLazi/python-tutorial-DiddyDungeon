# Draw a NEW hero sprite for scythe combat: no weapon, two hands gripping an invisible pole

Quest Lab is a Python-learning RPG with dark Castlevania-style pixel art. The combat scene shows the hero (Tate:
dark skin, black swept hair, long black coat with gold trim and a white collar, black boots with white spats) in
4-frame sprite sheets. For scythes, the **weapon is drawn separately by code** and combined with the hero afterwards, so
the hero sprite must hold **nothing**, and the hands must be closed fists gripping an invisible pole.

You are not editing the old sprite. **Draw a brand-new sprite sheet from scratch** (any method: an image generator, your own
pixel drawing, a script; it is up to you), keeping the same character design and the same pixel-art style.

## Look at these first (repo root `/home/lazi/projects/python-tutorial-DiddyDungeon`)
- `docs/review-art/scythe-redo/current-tate.png`: the old sheets at 4x (top row action, bottom row hurt). Copy the character
  design, the palette, the proportions and the **poses** from here. The scythe in these frames is what we are removing.
- `prototypes/godot-combat/art/held/base-tate-sword-action-sheet.png`: more Tate, weapon-less, one-handed, for style and proportions.

## Poses to draw (each is one 128x72 frame; the hero is about 46 px tall, feet near the bottom of the cell)
Action sheet, 4 frames, left to right:
1. **Ready**: low guard, both fists on an invisible pole held low and slightly back, blade end trailing forward-down.
2. **Wind-up**: both arms raised high, fists together above and behind the head as if the pole is lifted overhead.
3. **Strike**: lunging forward, both arms thrust forward and slightly down, fists a forearm apart on a pole pointing forward.
4. **Follow-through**: swing finished, body low and turned, fists forward at hip height.
Hurt sheet, 4 frames: hit and stagger back, head turned away, then recover. Fists stay closed.
The hero faces **right**. The hands must read as two fists with a 2-3 pixel gap between them where a pole would be, and the
two fists must lie on one straight line (the pole line) in every frame where he holds it.

## Hard requirements
- Output size **512x72** per sheet: four 128x72 cells, transparent background, hard pixel edges, no anti-aliasing, no shadow, no glow.
- **No weapon, no pole, no scythe, no staff, no extra object at all** in any frame.
- The same hero in all 8 frames: same face, hair, coat, trim, boots, same size (about 46 px tall) and same feet baseline.
- Palette: near-black coat, gold trim, white collar and spats, dark-brown skin. Dark outline, light from the top-left.
- If you draw bigger and shrink it, shrink with nearest-neighbour and clean the result so edges are hard pixels.

## Files to write (only into the output folder you were given)
- `action-sheet.png` and `hurt-sheet.png` (512x72 each)
- `grips.json`: for each frame of each sheet the centre of the rear fist and of the front fist, in cell pixel coordinates (x 0-127, y 0-71):
  `{"action": [{"rear":[x,y],"front":[x,y]}, ... 4], "hurt": [ ... 4 ]}`; the pole runs from rear to front and on towards the blade end (the forward end).
- `preview.png`: both sheets stacked, scaled 4x with nearest-neighbour on a dark blue background, a green dot on each fist and a thin red line through them.

Look at every frame at 4x and redraw any frame that is muddy, off-model, or shows anything held. When done, list the files and
name any frame you are unhappy with.

## Method (required: the first attempt hand-coded crude blocky pixels and the result was not good enough)
Use your **image generation tool**, one frame at a time (8 frames), with `current-tate.png` as the character reference.
Each prompt: the same dark-skinned hero with swept black hair, long black coat with gold trim, white collar, black boots with
white spats, facing right, in the named pose, **both fists closed and gripping an invisible pole, nothing in his hands**,
Castlevania-style 16-bit pixel art, dark outline, flat solid chroma-green background, full body visible, no weapon, no text.
Then clean each generated frame with a script: key out the background, crop to the hero, resize with nearest-neighbour so the hero is
about 46 px tall, reduce to at most 24 colours with hard edges, drop the alpha to 0/255, and place it in its 128x72 cell with the
feet on row 68 and the body centred near x=60. Compare each cleaned frame against the old sheet at 4x and regenerate any frame that
looks off-model, holds an object, has a missing hand, or is muddy. A frame that is richly drawn and faithful matters more than
speed: take as many attempts as you need.
