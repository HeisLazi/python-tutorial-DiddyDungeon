# Armour icons for Codex: batch 1 of 3

You are drawing **10 pixel-art armour icons** for Quest Lab, a Python-learning RPG with a dark,
Castlevania-inspired look. Work in this repo: `/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade`.

## Why
Eighteen armours currently show the *same* leather-coat icon. Every armour is now a different piece of kit
with its own role, so each needs its own, instantly recognisable icon. Each icon's dominant colours will
also become that armour's look on the hero in combat, so follow each palette below.

## Style reference (look at these first and match their line weight, lighting and palette depth)
- `ide/frontend/public/campaign-art/items/dawnbringer.png`
- `ide/frontend/public/campaign-art/items/weapon-campaign-dungeon-grave-scythe.png`
- `ide/frontend/public/campaign-art/items/hunter-fashion/warden.png` (a worn armour set, for the feel of the garment)

## Rules for every icon
- 128x128 PNG, transparent background, **one armour piece only**, front view, centred with a few pixels of
  margin. Draw the garment or plate itself: no body, no mannequin, no hands, no text, no ground shadow, no glow halo.
- Pixel art with hard edges, dark outline, one clear light source from the top-left. Hand-dithered and richly
  shaded like the references (many colours of texture are fine as long as edges stay hard-pixel and the
  background is fully transparent). It must read at 48 px, so keep the silhouette bold.
- Every armour has a **different real-world tradition mixed with fantasy**. Use its real construction and shapes
  as inspiration; do not copy a famous design or turn it into a stereotype or costume.
- The "must hint at" column is the armour's gameplay role. Show it with one small detail, never with text.
- **Palette**: the dominant colours are fixed per armour so that no two armours look alike. Keep to them.
- Do not reuse a silhouette between two armours. If two come out similar, redraw one.
- Generate one at a time, check it at 48 px, and redraw anything muddy or off-centre.

## Output
Save each icon as `docs/review-art/armour/codex/armor-<item id>.png` (the item id is in the first column, for
example `armor-lv-06.png`). Do not edit any other file. When all 10 are saved, list the file names and flag any
you are unhappy with.

## Your 10 armours

| Item id | Name | Tier | Tradition and look | Must hint at | Palette |
|---|---|---|---|---|---|
| lv-06 | Patchwork Travel Coat | common | Japanese boro: a hooded wool travel coat mended with many mismatched patches and visible white stitching, a needle and thread tucked in the collar | mending: heals a little as you go | indigo blue, ochre, cream |
| lv-07 | Pilgrim Leather | uncommon | Camino pilgrim jerkin: brown leather with crossed straps, a scallop-shell badge on the chest and a folded blue sash | a scholar: a small ribbon-marked book at the belt (bonus XP) | tan leather, cobalt blue |
| lv-08 | Wayfarer Brigandine | rare | Hungarian brigandine: rows of brass rivets over small plates under green-teal cloth, a lantern clip at the hip | a banked guard: a small hanging lantern clip | forest green, brass |
| lv-09 | Lanternscale Vest | epic | A vest of overlapping brass-framed glass scales, each scale a tiny lantern pane holding an ember | warm healing glow, a faint eye of insight at the collar | amber, orange, black iron |
| lv-10 | First Light Plate | legendary | Dawn-gilded chest plate with a rising-sun engraving and rays fanning from the pauldrons, a small phoenix at the centre | revival: a phoenix rising from the sun | white-gold, rose dawn |
| bj-dealer-s-waistcoat | Dealer's Waistcoat | common | Casino dealer's waistcoat, gold buttons, a watch chain, a single chip peeking from the pocket | coins: a poker chip in the pocket | black, red, gold |
| bj-velvet-felt-jacket | Velvet Felt Jacket | uncommon | Jacket cut from a green baize card table, felt lapels with faded stitched table lines and brass buttons | a free first mistake: a soft felt panel that blunts a blow | billiard green, brass |
| bj-pit-boss-coat | Pit Boss Coat | rare | Long double-breasted frock coat with gold epaulettes, a cigar pocket and gold cufflinks | reduction and coins: heavy cloth with gold braid | burgundy, charcoal, gold |
| bj-gilded-lapel-armour | Gilded Lapel Armour | epic | A tuxedo-cut steel cuirass with gilded filigree lapels and an ace-of-spades inlay on the chest | prediction and luck: a small crystal-ball cufflink | gold on gunmetal |
| bj-the-high-roller-s-mail | The High Roller's Mail | legendary | A mail shirt whose rings are tiny casino chips, with a stack of chips as a belt buckle | coins and a second life: a tall stack of chips | red, black, gold |
