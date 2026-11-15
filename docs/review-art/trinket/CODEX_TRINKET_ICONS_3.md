# Trinket icons for Codex: batch 3 of 6

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
| hunter-jacklight-charm | Jacklight Charm | rare | a carved miniature pumpkin jack-o'-lantern charm with a glowing face on a cord | foresight and luck: a flickering glow | orange, black |
| campaign-dungeon-village-lantern | Delver's Village Lantern | rare | a small wood-and-paper village lantern with a warm lit window | foresight and mending: warm window light | warm orange, wood brown |
| campaign-dungeon-pilgrim-knot | Delver's Pilgrim Knot | rare | a looped hemp-rope pilgrim knot with a single wooden bead | a banked guard: a tight knot | hemp tan, brown |
| campaign-dungeon-warm-ember | Delver's Warm Ember | rare | a glowing ember held in a tiny clay pot | warmth that heals and draws luck | red-orange, terracotta |
| campaign-dungeon-tidal-pearl | Delver's Tidal Pearl | rare | a pearl resting in an open scallop shell with a wave swirl | spotting flaws and soothing a break: a small wave curl | pearl white, sea blue |
| campaign-dungeon-cave-shell | Delver's Cave Shell | rare | a spiral cave-snail shell, stone hard, with cave-mineral crust | a block: a hard shell | sand, cave grey |
| campaign-dungeon-hoard-token | Delver's Hoard Token | rare | a heavy gold token stamped with a dragon-scale pattern | coins when a guard breaks: a crack of gold | gold, black |
| campaign-dungeon-loop-thread | Delver's Loop Thread | rare | a wooden spool with its thread wound into an infinity loop | a chain: an endless loop | indigo thread, pale wood |
| campaign-dungeon-still-clock | Delver's Still Clock | rare | a small stopped pocket clock with a hush mark, frozen mid-second | a hush before your first answer | pewter, cold blue |
| campaign-dungeon-keepers-ring | Delver's Keeper’s Ring | rare | a heavy silver signet ring with a keyhole sigil and a garnet | the first strike: a sharp point on the sigil | silver, garnet |
| campaign-dungeon-ink-seal | Delver's Ink Seal | rare | a wax-seal stamp with an ink-blot and a quill, one clean red seal beside it | clean answers: a spotless seal | black ink, red wax |
