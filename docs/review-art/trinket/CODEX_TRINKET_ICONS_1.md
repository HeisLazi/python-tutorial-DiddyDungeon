# Trinket icons for Codex: batch 1 of 6

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
| lv-11 | Amber Seed | common | a glossy amber seed with a tiny sprout curl frozen inside, on a thin cord | studying: a faint rune glows inside the amber | amber, honey gold |
| lv-12 | Traveler Compass | uncommon | a brass pocket compass with an open lid; the needle points to a small red 'return' arrow | finding your way back after a miss | brass, red needle, green patina |
| lv-13 | Little Beacon Charm | rare | a tiny lighthouse charm in white stone with a flaring lantern top | a guard at the start and a flare when you break through | white stone, warm yellow light |
| lv-14 | Mira Road Badge | epic | an embossed bronze road-warden badge shaped like a shield, a crossing-road emblem and a coin hole | blocks the first blow; a toll coin hangs from it | bronze, copper |
| lv-15 | Heart of the Vale | legendary | a crystalline heart-shaped valley stone with a tiny village lantern glowing inside, wrapped in green vines | a second life: a flame at its core | emerald, gold, white |
| bj-lucky-chip | Lucky Chip | common | a single red casino poker chip with a four-leaf pattern on its edge, worn smooth | coins: the chip is slightly chipped gold at the rim | red, white |
| bj-marked-card | Marked Card | uncommon | an ace of hearts with one corner deliberately bent and a tiny eye mark in the pip | foresight: you know what comes next | cream, red, black |
| bj-counting-abacus | Counting Abacus | rare | a tiny brass abacus with ivory beads, three beads slid across | a streak: three clean answers in a row | brass, ivory |
| bj-mara-s-pocket-watch | Mara's Pocket Watch | epic | an engraved silver pocket watch, open, with the second hand about to start | a strong opening: the hands poised to begin | silver, deep blue, gold |
| bj-the-gilded-ace | The Gilded Ace | legendary | a gilded ace of spades seen edge-on at an angle, ornate gold border and a ruby pip | a second life and a clean strike: the ruby pip | gold, black, ruby |
| cas-silver-dollar | Silver Dollar | common | a large silver coin with a laurel wreath and one bright glint | a coin for every clean answer: a tiny extra coin stacked behind it | silver, pale blue |
