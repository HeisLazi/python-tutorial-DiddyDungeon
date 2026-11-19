# Trinket icons for Codex: batch 6 of 6

You are drawing **9 pixel-art trinket icons** for Quest Lab, a Python-learning RPG with a dark,
Castlevania-inspired look. Work in this repo: `/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade`.

## Why
Sixty-four trinkets have just been given a distinct effect each, but most still share a handful of generic
icons. Each trinket needs its own icon that reads as a different object at a glance. They are small keepsakes
worn on the hunter, so each must also read at 24 px.

## Style reference (match their line weight, lighting and palette depth)
- `ide/frontend/public/campaign-art/items/dawnbringer.png`
- `ide/frontend/public/campaign-art/items/armor-bj-pit-boss-coat.png` (the newest armour icons: same quality bar)
- `ide/frontend/public/campaign-art/items/weapon-campaign-dungeon-grave-scythe.png`

## Rules for every icon
- 128x128 PNG, transparent background, **one object only**, centred with a few pixels of margin. The object
  fills about two thirds of the canvas. No hand, no body, no text, no ground shadow, no glow halo.
- Pixel art with hard edges, dark outline, one light source from the top-left, hand-dithered and richly shaded
  like the references. It must read at 48 px and still be recognisable at 24 px, so keep the silhouette bold.
- Every object in the table is a different shape. Do not reuse a silhouette between two icons in your batch; if
  two come out alike, redraw one.
- The "must hint at" column is the trinket's gameplay role. Show it with one small detail, never with text.
- Keep to each row's palette.
- Generate one at a time, check it at 48 px, and redraw anything muddy or off-centre.

## Output
Save each icon as `docs/review-art/trinket/codex/trinket-<item id>.png` (the item id is in the first column).
Do not edit any other file. When all 9 are saved, list the file names and flag any you are unhappy with.

## Your 9 trinkets

| Item id | Name | Tier | Object and look | Must hint at | Palette |
|---|---|---|---|---|---|
| elite-04-casino-slots-front-door-key | Front Door Key | rare | a big ornate casino front door key with a red tassel | a guard at the start and a coin | iron, red tassel |
| elite-05-dungeon-crawler-seeded-maze-knot | Seeded Maze Knot | rare | a cord tied in a maze pattern with a single seed bead | luck and follow-ups: a path through the maze | green cord, brown seed |
| elite-05-dungeon-crawler-star-seekers-lens | Star Seeker's Lens | rare | a telescope lens with a small star caught in it and a brass ring | learning and a second try: a bright star | brass, night blue |
| elite-05-dungeon-crawler-context-keepers-seal | Context Keeper's Seal | rare | a round bronze seal showing a closed book inside a circle | blocks the first blow; code focus | bronze, teal patina |
| elite-05-dungeon-crawler-lantern-keepers-wick | Lantern Keeper's Wick | rare | a coil of lantern wick with a small flame and a brass trimmer | mending and a flare when you break a guard | cream wick, warm flame |
| elite-05-dungeon-crawler-inquisitors-sigil | Inquisitor's Sigil | rare | a black iron sigil pendant of an open eye over a bug | a guard at the start and bug hunting | black iron, red eye |
| online-cinder-vow | Cinder Vow | rare | a warm iron oath-ring glowing with cinders along its band | retrying hits harder; a flare when you break a guard | dark iron, cinder orange |
| online-pale-guard-locket | Pale Guard Locket | legendary | a moon-pale silver locket engraved with a crescent, slightly open | a ward: it softens mistakes and blocks the first blow | moon silver, pale blue |
| online-last-laugh-charm | Last Laugh Charm | ethereal | a glass charm shaped like a laughing theatre mask, glowing from within | a guarded start, healing and a second life | glass, rose gold, prism light |
