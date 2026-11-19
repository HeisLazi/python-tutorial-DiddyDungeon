# Redraw the hero's scythe poses: a weapon-less hero with two real hands on an invisible shaft

Quest Lab is a Python-learning RPG with dark, Castlevania-style pixel art. The combat scene draws the hero
(Tate, the default black-and-gold coat) from 4-frame sprite sheets. For scythes the weapon is going to be drawn
**separately** and combined with the hero in code, so the hero sheets must hold **no weapon at all**, and the hands
must look like they are gripping a pole.

## Why we are redoing this
The current scythe sheets have the pole baked into the hero's hands. Swapping only the blade left a pole in his arms
that never changes with the weapon. A first fix borrowed the sword poses (one hand) and the scythe floated in front of
a one-handed hero. We want the *original two-handed scythe poses* back, but with the weapon removed cleanly.

## Input (read these, do not edit them)
Repo root: `/home/lazi/projects/python-tutorial-DiddyDungeon`
- `prototypes/godot-combat/art/tate-scythe-sheet.png`        512x72, 4 frames of 128x72: idle/ready, wind-up (scythe raised), strike, follow-through
- `prototypes/godot-combat/art/tate-scythe-hurt-sheet.png`   512x72, 4 frames of 128x72: the hurt animation
- `docs/review-art/scythe-redo/current-tate.png`             top row = the original action sheet, bottom row = the original hurt sheet, at 4x on a dark background

## What to produce (write into the output folder you were given; do not touch any other file)
1. `base-tate-scythe-action-sheet.png` and `base-tate-scythe-hurt-sheet.png`: same size and same cell layout as the inputs
   (512x72, 4 cells of 128x72, transparent background, pixel art with hard edges and no anti-aliasing).
   * Remove the **whole** scythe: shaft, blade, gold ferrule, wrapping, any sliver of it. Nothing of the weapon may remain.
   * The hero must stay **pixel-identical everywhere the weapon did not cover him**: same coat, same gold trim, same face and
     hair, same boots, same position inside the cell (the feet stay on the same pixels; this is a drop-in replacement).
   * Where the pole used to cross the hero (over the arms, the coat, the chest) repaint what was hidden underneath so the
     body reads clean: coat folds, sleeve, trim, in the same palette and dither style.
   * The hands must read as **closed fists gripping an invisible pole**: two hands, one near the butt of the shaft and one
     further along, about a forearm's length apart, fingers wrapped round a pole-thick gap (roughly 2 to 3 pixels). They
     should look right even with nothing between them. Keep each hand where the original had it whenever you can.
   * Where the original hero let go of the scythe or was thrown back (hurt frames), keep that pose; if a hand held the pole
     in that frame, leave the fist closed.
2. `scythe-grips.json`: for **each of the 8 frames** the geometry of the invisible shaft, measured on your finished sheets
   in cell pixel coordinates (x 0 to 127, y 0 to 71, origin top-left of that cell):
   ```json
   {"action": [ {"rear": [x, y], "front": [x, y], "butt": [x, y], "head": [x, y]}, ... 4 entries ],
    "hurt":   [ ... 4 entries ]}
   ```
   `rear` = centre of the hand nearest the butt, `front` = centre of the hand nearest the blade, `butt` = where the original
   pole ended behind the rear hand, `head` = where the original blade attached at the far end. The blade end is the end
   where the original blade was. A straight line must run through all four points (within 1 pixel).
3. `preview.png`: the action and hurt sheets stacked, scaled 4x with nearest-neighbour, with each frame's shaft line drawn as a
   thin red line from `butt` to `head` and the two grips as green dots, so a human can check the geometry at a glance.

## Rules
* Pixel art, hard edges, the same palette and shading style as the original sheet (look at it at 4x first).
* Work frame by frame. After each frame, look at it at 4x and fix anything muddy, a stray pixel of the old scythe, a missing
  hand or a changed body.
* Do not change the canvas size, do not reposition the hero, do not add a weapon, glow, shadow or text.
* When done, list the files you wrote and flag any frame you are unhappy with.
