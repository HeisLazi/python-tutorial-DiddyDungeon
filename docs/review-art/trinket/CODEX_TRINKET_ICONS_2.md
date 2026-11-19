# Trinket icons for Codex: batch 2 of 6

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
| cas-weighted-die | Weighted Die | uncommon | a translucent green die with a visible lead weight inside and a different pip pattern on each visible face | variety: changing patterns | green, ivory |
| cas-auditor-s-ledger | Auditor's Ledger | rare | a small hardbound ledger with a ribbon marker and a red-ink check mark on the cover | bug hunting: a magnifier-shaped clasp | slate, ink blue, red |
| cas-four-leaf-clip | Four-Leaf Clip | epic | a silver lapel clip holding a four-leaf clover, with a tiny coin hanging from the clip | luck and a blocked blow: the clover shimmers | silver, clover green |
| cas-the-probability-lens | The Probability Lens | legendary | a round brass monocle whose glass shows faint dice and probability arcs | the odds: tiny dice inside the glass | brass, violet glass |
| dc-canary-feather | Canary Feather | common | a bright yellow canary feather held in a tiny brass tube | a little breath returns: a soft glow at the tip | yellow, brass |
| dc-compass-needle | Compass Needle | uncommon | a bare magnetic needle balanced on a pin, one end red, mirrored shine | only forward: clean follow-ups hit harder | steel, red tip |
| dc-ore-sniffer-charm | Ore Sniffer Charm | rare | a small copper charm shaped like a snuffling snout with glints of ore on its nose | luck with loot: sparkling ore flecks | copper, gem sparkle |
| dc-brigid-s-hard-hat-badge | Brigid's Hard Hat Badge | epic | a miner's helmet badge: a dented metal plate with a pickaxe and a small lamp | the first rock misses: a dent that turned a blow | safety yellow-orange, iron |
| dc-the-heart-of-the-mine | The Heart of the Mine | legendary | a faceted ore heart: a crystal vein shaped like a heart inside raw rock, a pickaxe scratch across it | a second life, healing and a heavy blow: molten orange crystal | stone grey, molten orange, crystal blue |
| hunter-pink-cap-charm | Pink Cap Charm | rare | a tiny pink bottle cap charm with a droplet of baby oil falling from it | a party coin: a sparkle | pink, white |
| hunter-soul-lantern | Soul Lantern | rare | a small glass lantern holding a teal soul-flame with a ghost wisp, black iron frame | mending: a gentle teal glow | teal, black iron |
