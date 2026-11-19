# Trinket icons for Codex: batch 4 of 6

You are drawing **11 pixel-art trinket icons** for Quest Lab, a Python-learning RPG with a dark,
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
Do not edit any other file. When all 11 are saved, list the file names and flag any you are unhappy with.

## Your 11 trinkets

| Item id | Name | Tier | Object and look | Must hint at | Palette |
|---|---|---|---|---|---|
| campaign-dungeon-book-clasp | Delver's Book Clasp | rare | a brass book clasp and lock closing on a tiny tome | it shuts on the first blow | brass, leather brown |
| campaign-dungeon-quiet-page | Delver's Quiet Page | rare | a single folded parchment page with a finger-to-lips hush mark | quiet mending | parchment, grey-green |
| campaign-dungeon-thread-spool | Delver's Thread Spool | rare | a spool with red thread linking two buttons and a needle | follow-ups: one thread leads to the next | red thread, wood |
| campaign-dungeon-stone-eye | Delver's Stone Eye | rare | a polished stone eye amulet with a carved pupil and an amber iris | blocks the first blow, wakes when you are hurt | grey stone, amber |
| campaign-dungeon-bull-ring | Delver's Bull Ring | rare | a hammered iron bull's nose ring with a bloodied edge | strength when hurt | iron, blood red |
| campaign-dungeon-copper-spring | Delver's Copper Spring | rare | a tightly coiled copper spring, partly verdigris | snaps back harder after a miss | copper, verdigris |
| campaign-dungeon-brass-gear | Delver's Brass Gear | rare | two interlocking brass gears, one with a missing tooth | turns aside the first mistake | brass, steel |
| campaign-dungeon-tuning-fork | Delver's Tuning Fork | rare | a silver tuning fork humming, with gold sound-rings around the tines | coins when a guard rings | silver, gold rings |
| campaign-dungeon-oracle-lens | Delver's Oracle Lens | rare | a crystal lens with an open eye and fine rays | clean answers: a perfectly clear lens | crystal, violet |
| campaign-dungeon-star-thread | Delver's Star Thread | rare | a thread of starlight tied in a five-point star knot | a clean answer pulls starlight back | midnight blue, silver |
| campaign-dungeon-warding-star | Delver's Warding Star | rare | an eight-pointed star ward pendant with a soft glow | blocks the first blow and mends | white-gold, blue |
