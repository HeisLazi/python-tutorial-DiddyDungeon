# Armour icons for Codex: batch 2 of 3

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
| cas-doorman-s-livery | Doorman's Livery | common | Padded red doorman's tunic with gold braid frogging and shoulder cords | plain padding: visible quilting | crimson, gold |
| cas-silver-sequin-vest | Silver Sequin Vest | uncommon | Open-fronted vest covered in mirrored silver sequins that throw light, a tiny clover pinned at the lapel | luck: a four-leaf clover pin | silver, violet |
| cas-auditor-s-waistcoat | Auditor's Waistcoat | rare | Ledger-clerk waistcoat buttoned to the top, sleeve garters, a pen in the pocket, a magnifying glass on a chain | bug-hunting: the magnifying glass | slate grey, ink blue, green |
| cas-vault-guard-plate | Vault Guard Plate | epic | A breastplate hammered from a bank-vault door: riveted slab, a round combination dial on the chest | a banked guard: a heavy bolt-locked door | steel grey, brass |
| cas-the-fortune-mail | The Fortune Mail | legendary | Mail of linked gold coins with a fortune-teller's moon-and-star emblem on the chest | luck and a free mistake: a coin on its edge | gold, deep emerald |
| dc-canvas-mining-smock | Canvas Mining Smock | common | Dust-grey canvas smock with ore pouches, a pickaxe loop and a lantern hook | studying: a small notebook tab in a pocket | dust grey, brown |
| dc-riveted-leather | Riveted Leather | uncommon | Thick cuirass of boiled leather held with big iron rivets and visible repair patches | pure toughness: heavy rivets | oxblood red-brown, iron |
| dc-deepvein-brigandine | Deepvein Brigandine | rare | Brigandine with plates of dark rock whose veins glow with teal crystal, sewn under black cloth | healing: a soft crystal glow | dark slate, teal crystal |
| dc-lamp-lit-lamellar | Lamp-Lit Lamellar | epic | Japanese lamellar: small bronze scales laced with orange cord, a lantern hung from the waist, each scale catching its light | focus and a guard: the lantern | bronze, orange |
| dc-the-core-forged-plate | The Core-Forged Plate | legendary | Plate hammered from black obsidian with magma-orange seams and a glowing core in the chest | revival and healing: the glowing core | obsidian black, magma orange |
