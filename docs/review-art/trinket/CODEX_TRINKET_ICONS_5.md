# Trinket icons for Codex: batch 5 of 6

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
| campaign-dungeon-ash-talisman | Delver's Ash Talisman | rare | a charred ash-grey paper talisman with a faint ember crack down the middle | finishing what is nearly done | ash grey, ember red |
| campaign-dungeon-spectral-chain | Delver's Spectral Chain | rare | a short chain of pale ghostly links, one link half transparent | linking one question to the next | ghost cyan, black |
| campaign-dungeon-ember-heart | Delver's Ember Heart | rare | a heart-shaped ember crystal, glowing from within | a flare when you break a guard | ember orange, black |
| campaign-dungeon-last-spark | Delver's Last Spark | rare | a single white-hot spark floating in a tiny cracked glass vial | one more chance | white-hot yellow, cracked glass |
| elite-00-lantern-vale-echo-knot | Echo Knot | rare | a knotted cord whose loops repeat like an echo, a small silver bell | blocks the first blow; variety | silver, grey-blue |
| elite-00-lantern-vale-delivery-seal | Delivery Seal | rare | a parcel wax seal on a bit of twine with a tiny stamped wheel | mending and a coin for a delivered answer | red wax, twine brown |
| elite-00-lantern-vale-caravan-gear | Caravan Gear | rare | a wooden caravan wheel hub gear with brass pins and a loot-sack strap | a guard at the start; a lucky find | wood brown, brass |
| elite-00-lantern-vale-open-road-token | Open Road Token | rare | a round travel token stamped with a winding road and a star | luck of the road | dusty tan, teal |
| elite-04-casino-slots-debt-ghoul-token | Debt Ghoul Token | rare | a grey-green ghoul-faced casino token on a chain, with an IOU scrap | coins and a strong opening: a hungry grin | grey-green, tarnished gold |
| elite-04-casino-slots-greed-spirits-coin | Greed Spirit's Coin | rare | a translucent violet spirit coin with a greedy hand reaching through it | luck and a coin for clean answers | violet, gold |
| elite-04-casino-slots-balancers-weight | Balancer's Weight | rare | a heavy brass balance-scale weight with a stamped number | blocks the first blow and hits heavy | brass, black |
