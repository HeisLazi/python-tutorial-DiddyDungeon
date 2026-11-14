# Weapon icons, redraw batch for Codex (do this AFTER the first 23)

You are drawing **10 pixel-art weapon icons** for Quest Lab, a Python-learning RPG with a dark,
Castlevania-inspired look. Work in this repo: `/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade`.

## Style reference (look at these first and match their line weight, lighting and palette depth)
- `ide/frontend/public/campaign-art/items/dawnbringer.png`
- `ide/frontend/public/campaign-art/items/trailkeeper-blade.png`
- `ide/frontend/public/campaign-art/items/hunters-scythe.png`

## Why these are being redrawn
A first pass of these 10 was made by script, not by an image model, so the shading is flat and two of
them miss the brief. Use your image tool and give them the same hand-dithered, richly shaded look as the
three style references (hundreds of colours of texture are fine, as long as the edges stay hard-pixel
and the background is fully transparent). Look at `docs/review-art/weapons/argon/` for the weapons that
already came out well, and do not copy their silhouettes.

## Rules for every icon
- 128x128 PNG, transparent background, **one weapon only**, laid on a diagonal (grip bottom-left,
  tip top-right), centred with a few pixels of margin. No hand, no text, no ground shadow, no glow halo.
- Pixel art with hard edges, limited palette (about 12 to 20 colours), dark outline, one clear light
  source from the top-left. It must read at 48 px, so keep the silhouette bold and different from the
  other icons in your batch.
- Each weapon is drawn from a **different real-world tradition mixed with fantasy**. The brief names the
  tradition: take its real construction and shapes as inspiration, do not copy a famous design, and do
  not turn it into a stereotype or a costume.
- The "must hint at" column is the weapon's gameplay ability. Show it with one small detail
  (for example a heavy head for Heavy blow, a lantern for Mend), not with text or symbols.
- Do not reuse a pose or silhouette between two weapons. If two come out similar, redraw one.
- Generate one at a time, check it at 48 px, and redraw anything muddy, off-centre or with a stray hand.

## Output
Save each icon as `docs/review-art/weapons/codex-redo/weapon-<item id>.png` (the item id is in the first
column, for example `weapon-lv-01.png`). Create the folder if needed. Do not edit any other file.
When all 10 are saved, list the file names and flag any you are unhappy with.

## Your 10 weapons

| Item id | Name | Shape | Tradition and look | Must hint at |
|---|---|---|---|---|
| campaign-dungeon-minotaur-edge | Minotaur's Judgment | greatsword | **Minoan labrys**: a greatsword whose blade is a broad double-bladed axe head (two crescent edges), bull-horn crossguard. It must read as a double axe-sword, not a mace or club. | Last stand, heavy blow |
| hunter-jack-scythe | Jack-o' Scythe | scythe | Harvest scythe with a clearly visible carved pumpkin (glowing jack-o'-lantern face) fused into the blade socket, orange and black blade, harvest twine on the pole. The pumpkin must be recognisable at 48 px. | Reap, opening, payout |
| campaign-dungeon-oracle-staff | Oracle's Verdict | staff | Delphic laurel-wrapped marble staff topped by an open eye with golden rays | Precision |
| campaign-dungeon-dawn-lantern | Matriarch's Dawnlight | lantern | Chinese festival lantern, red and gold, hung from a crook staff, warm morning glow | Variety |
| campaign-dungeon-warden-chain | Warden's Oathchain | chain | Byzantine bronze chain with cross seals and an open manacle end | Follow-up, chain |
| campaign-dungeon-loopblade | Roundkeeper Blade | sword | Javanese kris, wavy blade engraved with a looping pattern, golden ring guard | Chain |
| campaign-dungeon-pathfinder-whip | Bounty Hunter's Lash | whip | Black braided lash, a wanted-poster tag on the handle, barbed hook tip | Opening, chain |
| campaign-dungeon-grave-scythe | Gravekeeper's Scythe | scythe | Day-of-the-Dead scythe, marigold petals, calavera skull at the blade socket | Reap, last stand |
| hunter-sparring-scythe | Hunter's Scythe | scythe | European war scythe, plain worn steel on an ash pole, the humble starter weapon | Reap |
| merchant-nightfall-greatsword | Nightfall Greatsword | greatsword | Black Valkyrie greatsword with winged crossguard and a star-field blade | Heavy blow |
