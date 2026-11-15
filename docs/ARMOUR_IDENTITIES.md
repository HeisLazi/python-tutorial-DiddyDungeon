# Armour identities

Every armour in the Home armory has an effect of its own. Before this change the four campaign ladders repeated one
damage-reduction curve (10 / 18 / 26 / 35 / 45) and only 11 distinct effect sets covered 33 armours. Now each armour is a
different mix of the roles below, and `ide/server/test_armour_identities.py` fails if two armours ever share an effect.

Names, ids and tiers did not change (saves store armour by name), and effects are never stored in a save.

## Roles an armour can have

| Key | What it does | Where it applies |
|---|---|---|
| `reduction` | % less damage from wrong answers | hunts, spars, duels (as guard) |
| `first_miss_free` | the first wrong answer costs nothing | hunts, spars, duels (+1 guard) |
| `start_guards` | begin the fight with a banked free mistake | hunts, spars, duels (+1 guard) |
| `heal_on_objective` | heal HP on every right answer | hunts, spars, duels (as heal) |
| `impact` + `on` | extra Resolve damage on one kind of question (`any`, `prediction`, `explanation`, `code_checkpoint`, `bug_diagnosis`) | hunts, spars; duels when `any` or code |
| `revive` | survive one lethal hit at 1 HP | hunts, spars |
| `coin_bonus`, `xp_bonus`, `loot_luck` | bounty rewards | hunts only (a spar gives no rewards) |

Armour effects stack with the trinket's: guards and healing add up, the first free mistake and the revive are once per fight.

## The armours

### Lantern Vale

| Armour | Tier | Effect |
|---|---|---|
| Patchwork Travel Coat | common | Heal 1 HP per verified objective. |
| Pilgrim Leather | uncommon | 14% less damage from misses; +5% bounty XP. |
| Wayfarer Brigandine | rare | 22% less damage from misses; start every battle with a free mistake. |
| Lanternscale Vest | epic | +1 impact on EXPLAIN objectives; 20% less damage from misses; heal 2 HP per verified objective. |
| First Light Plate | legendary | 40% less damage from misses; your first miss each battle costs nothing; revive at 1 HP once per battle. |

### Blackjack

| Armour | Tier | Effect |
|---|---|---|
| Dealer's Waistcoat | common | +6% bounty coins. |
| Velvet Felt Jacket | uncommon | Your first miss each battle costs nothing. |
| Pit Boss Coat | rare | 18% less damage from misses; +10% bounty coins. |
| Gilded Lapel Armour | epic | +1 impact on PREDICT objectives; 24% less damage from misses; +10% chance of rarer loot. |
| The High Roller's Mail | legendary | 36% less damage from misses; revive at 1 HP once per battle; +20% bounty coins. |

### Casino Slots

| Armour | Tier | Effect |
|---|---|---|
| Doorman's Livery | common | 12% less damage from misses. |
| Silver Sequin Vest | uncommon | +5% bounty coins; +10% chance of rarer loot. |
| Auditor's Waistcoat | rare | +1 impact on FIX objectives; +12% bounty XP. |
| Vault Guard Plate | epic | 32% less damage from misses; start every battle with a free mistake. |
| The Fortune Mail | legendary | 30% less damage from misses; your first miss each battle costs nothing; +20% chance of rarer loot. |

### Dungeon Crawler

| Armour | Tier | Effect |
|---|---|---|
| Canvas Mining Smock | common | +8% bounty XP. |
| Riveted Leather | uncommon | 16% less damage from misses. |
| Deepvein Brigandine | rare | 20% less damage from misses; heal 1 HP per verified objective. |
| Lamp-Lit Lamellar | epic | +1 impact on BUILD objectives; 26% less damage from misses; start every battle with a free mistake. |
| The Core-Forged Plate | legendary | 42% less damage from misses; revive at 1 HP once per battle; heal 2 HP per verified objective. |

### Hunter's set and the Merchant

| Armour | Tier | Effect |
|---|---|---|
| Merchant Patchwork Coat | common | 10% less damage from misses; +4% bounty coins. |
| Merchant Pilgrim Leather | uncommon | 12% less damage from misses; heal 1 HP per verified objective. |
| Ivory Revel Suit | rare | 16% less damage from misses; +8% bounty coins. |
| Gravebound Warden Plate | rare | 24% less damage from misses; revive at 1 HP once per battle. |
| Harvest Revenant Coat | rare | 16% less damage from misses; +12% chance of rarer loot. |
| Merchant Wayfarer Brigandine | rare | +1 impact on BUILD objectives; 18% less damage from misses. |
| Merchant Oracle Mantle | epic | 18% less damage from misses; your first miss each battle costs nothing; +10% bounty XP. |

### Forged at the Still

| Armour | Tier | Effect |
|---|---|---|
| Lanternbound Coat | uncommon | 10% less damage from misses; start every battle with a free mistake. |
| Norse Mail | uncommon | 20% less damage from misses. |
| Drowned Mail | rare | 30% less damage from misses; heal 1 HP per verified objective. |
| Flowkeeper Plate | rare | +1 impact on every objective; 20% less damage from misses. |

### Journal echoes of run armour

| Armour | Tier | Effect |
|---|---|---|
| Lanternkeeper’s Coat | uncommon | Start every battle with a free mistake; heal 1 HP per verified objective. |
| Wayfarer’s Wardplate | rare | 26% less damage from misses; your first miss each battle costs nothing. |

## Icons and looks

- Every armour has its own icon (`ide/frontend/public/campaign-art/items/armor-<id>.png`, registered in `lanternItemArt.js`, drawn with Codex from `docs/review-art/armour/CODEX_ARMOUR_ICONS_*.md`). A test fails if two share one or a file is missing.
- Every armour has its own look in combat: 10 bespoke outfits plus 23 recolours (see `prototypes/godot-combat/SKIN_WORKFLOW.md`). Recolours share a silhouette with their parent outfit, and Home shows that parent. A truly new silhouette needs a bespoke outfit.
- The Infinite Dungeon's run armours are a separate system with their own effects (`dungeon_items.py`); they were not changed.
