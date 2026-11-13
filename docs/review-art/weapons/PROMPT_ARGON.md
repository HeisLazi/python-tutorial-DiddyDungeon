# Weapon icons, batch for Argon (Gemini)

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
Save each icon as `docs/review-art/weapons/argon/weapon-<item id>.png` (the item id is in the first
column, for example `weapon-lv-01.png`). Create the folder if needed. Do not edit any other file.
When all 23 are saved, list the file names and flag any you are unhappy with.

## Your 23 weapons

| Item id | Name | Shape | Tradition and look | Must hint at |
|---|---|---|---|---|
| lv-01 | Trailkeeper Blade | sword | Scottish basket-hilt backsword, knotwork guard, moss-green grip | Combo |
| lv-03 | Wayfinder Hammer | hammer | Norse maul, brass compass rose on the face | Heavy blow |
| lv-05 | Dawnbringer | sword | Mesoamerican sun blade, gold sunburst, obsidian teeth on the edge | Combo, extra guard |
| bj-croupier-s-rake | Croupier's Rake | rake | Venetian silvered rake, filigree fork head, long ebony handle | Chain, payout |
| bj-the-shoe-splitter | The Shoe Splitter | cleaver | Broad cleaver with a card-shoe notch cut in the spine | Heavy blow |
| cas-coin-roll-club | Coin Roll Club | club | Zulu knobkerrie wrapped in paper coin rolls | Heavy blow, payout |
| cas-reel-spinner-chakram | Reel Spinner Chakram | chakram | Sikh chakram with a ring of spinning fruit reels | Variety, payout |
| cas-lady-luck-s-sceptre | Lady Luck's Sceptre | sceptre | Akan gold sceptre, four-leaf clover and dice finial | Payout, mend |
| dc-miner-s-pickaxe | Miner's Pickaxe | pickaxe | Cornish miner's pick, rope grip, a hooked lamp | Reap, heavy blow |
| dc-deepvein-warhammer | Deepvein Warhammer | warhammer | Dwarven hammer, glowing blue ore veins in the head | Heavy blow, last stand |
| dc-the-core-breaker | The Core Breaker | greatsword | Cracked obsidian greatsword with molten seams, drill-bit tip | Heavy blow, extra guard |
| hunter-sparring-whip | Hunter's Whip | whip | Gaucho braided leather bullwhip, iron tip | Chain |
| hunter-sparring-scythe | Hunter's Scythe | scythe | European war scythe, plain steel | Reap |
| merchant-vigil-sabre | Vigil Sabre | sabre | Polish szabla, candle-flame guard, deep blue | Precision |
| merchant-nightfall-greatsword | Nightfall Greatsword | greatsword | Black Valkyrie greatsword, star-field blade | Heavy blow |
| hunter-jack-scythe | Jack-o' Scythe | scythe | Pumpkin-carved blade, orange and black, harvest twine | Reap, opening, payout |
| campaign-dungeon-loopblade | Roundkeeper Blade | sword | Javanese kris, wavy blade engraved with a looping pattern | Chain |
| campaign-dungeon-pathfinder-whip | Bounty Hunter's Lash | whip | Black braided lash, a wanted-poster tag on the handle | Opening, chain |
| campaign-dungeon-grave-scythe | Gravekeeper's Scythe | scythe | Day-of-the-Dead scythe, marigold petals, calavera blade | Reap, last stand |
| campaign-dungeon-dawn-lantern | Matriarch's Dawnlight | lantern | Chinese festival lantern on a staff, red and gold, morning glow | Variety |
| campaign-dungeon-warden-chain | Warden's Oathchain | chain | Byzantine bronze chain with cross seals and a manacle end | Follow-up, chain |
| campaign-dungeon-minotaur-edge | Minotaur's Judgment | greatsword | Minoan labrys double-axe edge with bull-horn guard | Last stand, heavy blow |
| campaign-dungeon-oracle-staff | Oracle's Verdict | staff | Delphic laurel-wrapped staff topped by an open eye | Precision |
