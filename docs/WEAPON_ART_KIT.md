# Weapon art kit — 2026-11-13

Phase 2 of `docs/ITEM_REDESIGN_PLAN.md`. The abilities are in the game (`ide/server/weapon_signatures.py`).
This kit is what the art needs so each of the 46 weapons *looks* like its own thing, drawn from a
different real tradition mixed with fantasy (Lazi's direction: pull from cultures across the world and
fantasy worlds). Inspired by, not copied from. Check the real construction first, as in `docs/ARMOUR_IDEAS.md`.

## What exists today and what is missing

- The combat scene draws a weapon only as part of the hunter sheets (`tate-<outfit>-<style>`), so every
  weapon of a style looks identical. 46 weapons share 7 styles.
- Shop and pack icons exist for 17 of 46 weapons (`lanternItemArt.js`); the other 29 fall back to stock art.

## Two deliverables per weapon

1. **Icon**, 128x128 PNG, transparent, weapon only at a diagonal, same pixel-art style as
   `ide/frontend/public/campaign-art/items/`. File `weapon-<item id>.png`. This alone fixes the shop,
   pack and loot screens and can ship first.
2. **Held-weapon strip**, 4 frames x 128 px (sword family 96 px) in one row, weapon only on transparent
   background, facing right, grip point on the same pixel in every frame: idle, windup, strike,
   recovery. File `held-<item id>.png`. Claude will turn the hunter sheets into weapon-less bases and
   draw this strip as a layer over them, so a new weapon never needs a new character sheet.
   Do not start these until the weapon-less bases exist (Claude does that first).

A weapon's `shape` below is its real silhouette. Shapes with no matching animation yet need one new
style in the combat scene: **spear** (thrust), **hammer** (overhead one-hand smash; also club, mace,
warhammer, jackpot hammer) and **thrown** (chakram). Until then they use the closest existing style
(the `style` column), so nothing is blocked.

## The 46 briefs

Colours are a starting point. Keep every silhouette readable at 72 px and clearly different from the
others in its family.

| Item id | Name | Shape | Style now | Tradition and look | Ability it must hint at |
|---|---|---|---|---|---|
| lv-01 | Trailkeeper Blade | sword | sword | Scottish basket-hilt backsword, knotwork guard, moss-green grip | Combo |
| lv-02 | Lantern Guard Sword | sword | sword | Japanese katana, lantern-shaped tsuba, amber paper-wrapped hilt | Mend |
| lv-03 | Wayfinder Hammer | hammer | greatsword | Norse maul, brass compass rose on the face | Heavy blow |
| lv-04 | Roadwarden Spear | spear | staff | Greek leaf-blade spear, milestone-carved shaft, road banner | Follow-up |
| lv-05 | Dawnbringer | sword | sword | Mesoamerican sun blade, gold sunburst, obsidian teeth on the edge | Combo, extra guard |
| bj-card-edge-dagger | Card-Edge Dagger | dagger | sword | Italian Renaissance stiletto, blade edge etched like a card | Follow-up |
| bj-croupier-s-rake | Croupier's Rake | rake | whip | Venetian silvered rake, filigree fork head, long ebony handle | Chain, payout |
| bj-ace-of-spades-blade | Ace of Spades Blade | sword | sword | Spanish rapier, spade-shaped cup guard, black and silver | Combo, payout |
| bj-the-shoe-splitter | The Shoe Splitter | cleaver | greatsword | Broad cleaver with a card-shoe notch cut in the spine | Heavy blow |
| bj-the-house-cutter | The House Cutter | cutlass | sword | Caribbean cutlass, casino green and gold, a house-edge notch | Payout, precision |
| cas-coin-roll-club | Coin Roll Club | club | greatsword | Zulu knobkerrie wrapped in paper coin rolls | Heavy blow, payout |
| cas-lever-arm-mace | Lever Arm Mace | mace | greatsword | Persian flanged mace made from a slot lever, red ball knob | Opening, heavy blow |
| cas-reel-spinner-chakram | Reel Spinner Chakram | chakram | handmagic | Sikh chakram with a ring of spinning fruit reels | Variety, payout |
| cas-jackpot-hammer | Jackpot Hammer | hammer | greatsword | Oversized gold maul, glowing 7-7-7 striking face | Heavy blow, payout |
| cas-lady-luck-s-sceptre | Lady Luck's Sceptre | sceptre | handmagic | Akan gold sceptre, four-leaf clover and dice finial | Payout, mend |
| cas-oil-of-doom | Oil of Doom and Despair | oil | oil | The existing giant bottle, keep its look | Burn |
| dc-miner-s-pickaxe | Miner's Pickaxe | pickaxe | scythe | Cornish miner's pick, rope grip, a hooked lamp | Reap, heavy blow |
| dc-lantern-lit-shortsword | Lantern-Lit Shortsword | shortsword | sword | Roman gladius with a caged lantern pommel | Follow-up, mend |
| dc-deepvein-warhammer | Deepvein Warhammer | warhammer | greatsword | Dwarven hammer, glowing blue ore veins in the head | Heavy blow, last stand |
| dc-cartographer-s-spear | Cartographer's Spear | spear | staff | Maori taiaha carving, a rolled map and compass at the butt | Variety |
| dc-the-core-breaker | The Core Breaker | greatsword | greatsword | Cracked obsidian greatsword with molten seams, drill-bit tip | Heavy blow, extra guard |
| hunter-sparring-staff | Hunter's Staff | staff | staff | Slavic carved birch staff, blue crystal | Variety |
| hunter-sparring-whip | Hunter's Whip | whip | whip | Gaucho braided leather bullwhip, iron tip | Chain |
| hunter-sparring-greatsword | Hunter's Greatsword | greatsword | greatsword | German flammard zweihander, wavy flame blade | Heavy blow |
| hunter-sparring-scythe | Hunter's Scythe | scythe | scythe | European war scythe, plain steel | Reap |
| hunter-sparring-focus | Hunter's Casting Focus | focus | handmagic | Celtic triquetra gauntlet with a ring of runes | Mend |
| merchant-vigil-sabre | Vigil Sabre | sabre | sword | Polish szabla, candle-flame guard, deep blue | Precision |
| merchant-moonlit-staff | Moonlit Staff | staff | staff | Persian silver crescent-moon staff, night-sky crystal | Variety, opening |
| merchant-nightfall-greatsword | Nightfall Greatsword | greatsword | greatsword | Black Valkyrie greatsword, star-field blade | Heavy blow |
| hunter-gravebound-greatblade | Gravebound Greatblade | greatsword | greatsword | Gothic bone and rusted iron, shroud-wrapped grip | Heavy blow, last stand |
| hunter-jack-scythe | Jack-o' Scythe | scythe | scythe | Pumpkin-carved blade, orange and black, harvest twine | Reap, opening, payout |
| campaign-dungeon-syntax-sabre | Oathkeeper Sabre | sabre | sword | Ottoman kilij with oath script engraved in gold | Precision |
| campaign-dungeon-loopblade | Roundkeeper Blade | sword | sword | Javanese kris, wavy blade engraved with a looping pattern | Chain |
| campaign-dungeon-aether-staff | Seeker's Aether Staff | staff | staff | Himalayan staff, vajra head, floating prayer-wheel ring | Extra guard |
| campaign-dungeon-pathfinder-whip | Bounty Hunter's Lash | whip | whip | Black braided lash, a wanted-poster tag on the handle | Opening, chain |
| campaign-dungeon-iron-greatsword | Faultbreaker | greatsword | greatsword | Cracked-stone greatsword, glowing fault-line seams | Retry, heavy blow |
| campaign-dungeon-grave-scythe | Gravekeeper's Scythe | scythe | scythe | Day-of-the-Dead scythe, marigold petals, calavera blade | Reap, last stand |
| campaign-dungeon-runic-casting | Scribe's Rune Focus | focus | handmagic | Egyptian scarab focus ringed by floating hieroglyphs | Mend, follow-up |
| campaign-dungeon-dawn-lantern | Matriarch's Dawnlight | lantern | staff | Chinese festival lantern on a staff, red and gold, morning glow | Variety |
| campaign-dungeon-undertow-scythe | Hoardbreaker Scythe | scythe | scythe | Viking sea-silver scythe, barnacles, a coin-lock rune | Reap, extra guard |
| campaign-dungeon-warden-chain | Warden's Oathchain | chain | whip | Byzantine bronze chain with cross seals and a manacle end | Follow-up, chain |
| campaign-dungeon-last-page | Lich's Last Page | tome | handmagic | Irish illuminated book, one torn page burning | Mend |
| campaign-dungeon-minotaur-edge | Minotaur's Judgment | greatsword | greatsword | Minoan labrys double-axe edge with bull-horn guard | Last stand, heavy blow |
| campaign-dungeon-clockwork-greatblade | Automaton's Greatblade | greatsword | greatsword | Brass clockwork saw-edged greatsword, turning gears | Retry, heavy blow |
| campaign-dungeon-oracle-staff | Oracle's Verdict | staff | staff | Delphic laurel-wrapped staff topped by an open eye | Precision |
| campaign-dungeon-hollow-fang | Hollow King's Fang | fang | sword | Inuit scrimshaw ivory fang-blade, hollow bore, pale glow | Combo |

## Prompt template (one weapon at a time, with a reference image of an existing icon)

> Pixel-art game icon in a dark Castlevania-inspired style, 128x128, transparent background, one
> weapon on a diagonal: **{NAME}**, {TRADITION AND LOOK}. Readable at 48 px, strong silhouette,
> limited palette, no text, no hand, no ground shadow. Match the line weight and lighting of the
> reference icon.

For the held strip add: "four poses in one row (idle, windup, strike, recovery), weapon only,
facing right, same grip point in every frame".

## What Claude does once the images exist

1. Drop icons into `ide/frontend/public/campaign-art/items/` and map them in `lanternItemArt.js`
   (and add a test that fails if a weapon has no icon, so none are forgotten).
2. Build weapon-less hunter bases and the held-weapon layer, then register the new `spear`,
   `hammer` and `thrown` styles in `combat_catalog.gd` and `arena.gd`.
3. Show the ability text and last trigger on the weapon card, rebuild the exports, run the Godot
   smoke tests, and check every weapon on the test save.
