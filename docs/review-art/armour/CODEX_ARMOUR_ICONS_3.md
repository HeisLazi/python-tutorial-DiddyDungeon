# Armour icons for Codex: batch 3 of 3

You are drawing **13 pixel-art armour icons** for Quest Lab, a Python-learning RPG with a dark,
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
example `armor-lv-06.png`). Do not edit any other file. When all 13 are saved, list the file names and flag any
you are unhappy with.

## Your 13 armours

| Item id | Name | Tier | Tradition and look | Must hint at | Palette |
|---|---|---|---|---|---|
| merchant-patchwork-coat | Merchant Patchwork Coat | common | A shopkeeper's mended coat with neat square patches, a ledger tag and a coin pouch at the belt | coin: the pouch | warm brown, teal patches |
| merchant-pilgrim-leather | Merchant Pilgrim Leather | uncommon | A fitted grey-blue leather coat with silver clasps, a scarf and a rolled bandage at the belt | healing: the bandage roll | grey-blue, silver |
| hunter-ivory-revel-suit | Ivory Revel Suit | rare | A white party suit with a pink bow tie and a tiny baby-oil bottle as the buttonhole flower | coin: a champagne-bottle glint | ivory, pink |
| hunter-gravebound-plate | Gravebound Warden Plate | rare | Spectral plate armour that looks half transparent, hollow, with a skull on one pauldron and ghostly wisps | a second life: a faint soul-flame at the chest | spectral cyan-green, black |
| hunter-harvest-coat | Harvest Revenant Coat | rare | Autumn harvest coat with pumpkin buttons, straw trim and scarecrow patches | loot luck: a small pumpkin charm | orange, black, straw |
| merchant-wayfarer-brigandine | Merchant Wayfarer Brigandine | rare | Layered expedition brigandine with rolled map scrolls strapped across and brass buckles | code focus: a map scroll | burnt sienna, crimson |
| merchant-oracle-mantle | Merchant Oracle Mantle | epic | An embroidered mantle with silver stars and a single open eye at the clasp | scholar and a free first mistake: the eye | violet, silver |
| forged-lantern-coat | Lanternbound Coat | uncommon | A coat stitched from mimic hide: a toothy chest-lid collar and brass hinge buckles | a banked guard: the chest-lid collar clamped shut | brown, brass, ivory teeth |
| forged-norse-mail | Norse Mail | uncommon | Viking byrnie of riveted rings with a fur mantle and a bronze hammer clasp | pure bulwark: heavy rings and fur | iron grey, fur brown, deep blue |
| forged-divers-mail | Drowned Mail | rare | Corroded diver's mail crusted with barnacles and a pearl, green with verdigris | healing: a pearl glowing faintly | verdigris copper, sea blue |
| forged-keeper-plate | Flowkeeper Plate | rare | Plate covered in emerald serpent scales with an ouroboros biting its own tail on the chest | every answer counts: the endless loop | emerald, silver |
| campaign-dungeon-lantern-coat | Lanternkeeper's Coat | uncommon | A cream keeper's coat with lamp-wick trim and little brass lamp pendants glowing at the hem | a guard and healing: a glowing lamp | cream, brass, ember glow |
| campaign-dungeon-pilgrim-ward | Wayfarer's Wardplate | rare | A flat hammered ward plate engraved with pilgrim sigils and blue enamel inlay, a cross-shaped boss at the centre | a free first mistake: a ward sigil | steel, blue, white |
