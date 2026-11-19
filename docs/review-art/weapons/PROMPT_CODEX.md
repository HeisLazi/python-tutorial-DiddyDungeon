# Weapon icons, batch for Codex

You are drawing **23 pixel-art weapon icons** for Quest Lab, a Python-learning RPG with a dark,
Castlevania-inspired look. Work in this repo: `/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade`.

## Style reference (look at these first and match their line weight, lighting and palette depth)
- `ide/frontend/public/campaign-art/items/dawnbringer.png`
- `ide/frontend/public/campaign-art/items/trailkeeper-blade.png`
- `ide/frontend/public/campaign-art/items/hunters-scythe.png`

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
Save each icon as `docs/review-art/weapons/codex/weapon-<item id>.png` (the item id is in the first
column, for example `weapon-lv-01.png`). Create the folder if needed. Do not edit any other file.
When all 23 are saved, list the file names and flag any you are unhappy with.

## Your 23 weapons

| Item id | Name | Shape | Tradition and look | Must hint at |
|---|---|---|---|---|
| lv-02 | Lantern Guard Sword | sword | Japanese katana, lantern-shaped tsuba, amber paper-wrapped hilt | Mend |
| lv-04 | Roadwarden Spear | spear | Greek leaf-blade spear, milestone-carved shaft, road banner | Follow-up |
| bj-card-edge-dagger | Card-Edge Dagger | dagger | Italian Renaissance stiletto, blade edge etched like a card | Follow-up |
| bj-ace-of-spades-blade | Ace of Spades Blade | sword | Spanish rapier, spade-shaped cup guard, black and silver | Combo, payout |
| bj-the-house-cutter | The House Cutter | cutlass | Caribbean cutlass, casino green and gold, a house-edge notch | Payout, precision |
| cas-lever-arm-mace | Lever Arm Mace | mace | Persian flanged mace made from a slot lever, red ball knob | Opening, heavy blow |
| cas-jackpot-hammer | Jackpot Hammer | hammer | Oversized gold maul, glowing 7-7-7 striking face | Heavy blow, payout |
| cas-oil-of-doom | Oil of Doom and Despair | oil | The existing giant bottle, keep its look | Burn |
| dc-lantern-lit-shortsword | Lantern-Lit Shortsword | shortsword | Roman gladius with a caged lantern pommel | Follow-up, mend |
| dc-cartographer-s-spear | Cartographer's Spear | spear | Maori taiaha carving, a rolled map and compass at the butt | Variety |
| hunter-sparring-staff | Hunter's Staff | staff | Slavic carved birch staff, blue crystal | Variety |
| hunter-sparring-greatsword | Hunter's Greatsword | greatsword | German flammard zweihander, wavy flame blade | Heavy blow |
| hunter-sparring-focus | Hunter's Casting Focus | focus | Celtic triquetra gauntlet with a ring of runes | Mend |
| merchant-moonlit-staff | Moonlit Staff | staff | Persian silver crescent-moon staff, night-sky crystal | Variety, opening |
| hunter-gravebound-greatblade | Gravebound Greatblade | greatsword | Gothic bone and rusted iron, shroud-wrapped grip | Heavy blow, last stand |
| campaign-dungeon-syntax-sabre | Oathkeeper Sabre | sabre | Ottoman kilij with oath script engraved in gold | Precision |
| campaign-dungeon-aether-staff | Seeker's Aether Staff | staff | Himalayan staff, vajra head, floating prayer-wheel ring | Extra guard |
| campaign-dungeon-iron-greatsword | Faultbreaker | greatsword | Cracked-stone greatsword, glowing fault-line seams | Retry, heavy blow |
| campaign-dungeon-runic-casting | Scribe's Rune Focus | focus | Egyptian scarab focus ringed by floating hieroglyphs | Mend, follow-up |
| campaign-dungeon-undertow-scythe | Hoardbreaker Scythe | scythe | Viking sea-silver scythe, barnacles, a coin-lock rune | Reap, extra guard |
| campaign-dungeon-last-page | Lich's Last Page | tome | Irish illuminated book, one torn page burning | Mend |
| campaign-dungeon-clockwork-greatblade | Automaton's Greatblade | greatsword | Brass clockwork saw-edged greatsword, turning gears | Retry, heavy blow |
| campaign-dungeon-hollow-fang | Hollow King's Fang | fang | Inuit scrimshaw ivory fang-blade, hollow bore, pale glow | Combo |
