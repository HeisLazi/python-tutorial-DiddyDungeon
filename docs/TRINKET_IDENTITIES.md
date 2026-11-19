# Trinket identities

Before this change 64 trinkets shared 17 effect sets, and the 25 Journal echoes of run trinkets had been squeezed into four
(a free first miss, healing, +10% coins, or +1 impact on one question type). Now each trinket is a different mix of the roles
below, and `ide/server/test_trinket_identities.py` fails if two trinkets ever share an effect or read the same in words.

Names, ids and tiers did not change (saves store trinkets by name), and effects are never stored in a save.

## Roles a trinket can have

A trinket can do everything an armour can (see `ARMOUR_IDENTITIES.md`) and carry the same **triggers** a weapon carries.
Weapons and trinkets share one trigger set: `_gear_effects` sums them (capped) into `effects["triggers"]`, and the campaign fight, the Sparring Ring and friendly duels all read that sum.

| Trigger | What it does |
|---|---|
| `opening_impact` | extra impact on the first right answer |
| `retry_impact` | extra impact when you correct a missed objective (not in a spar: there are no retries) |
| `chip_streak` Combo | third clean answer in a row |
| `chip_switch` Variety / `chip_chain` Chain | the question type changes / repeats |
| `chip_heavy` Heavy blow | an objective worth 4 or more |
| `chip_finish` Reap | the foe is at 40% Resolve or less |
| `chip_low` Last stand | you are at half HP or less |
| `chip_clean` Precision / `chip_follow` Follow-up | right first time / a clean follow-up |
| `heal_clean` Mend | heal on a clean answer |
| `heal_on_break`, `break_coins`, `break_guard` | bonuses when you break the foe's guard |
| `coin_clean` Pay-out | coins on a clean answer (hunts only) |

Rewards (`coin_bonus`, `xp_bonus`, `loot_luck`, `break_coins`, `coin_clean`) only matter in hunts: a spar gives none.

## The trinkets

### Lantern Vale

| Trinket | Tier | Effect |
|---|---|---|
| Amber Seed | common | +10% bounty XP. |
| Traveler Compass | uncommon | +2 impact when correcting a missed bounty objective. |
| Little Beacon Charm | rare | Restore 2 HP on a bounty Guard Break; start every battle with a free mistake. |
| Mira Road Badge | epic | +4 coins on a Guard Break; blocks the first counterattack each battle; +15% bounty coins. |
| Heart of the Vale | legendary | Start every battle with a free mistake; revive at 1 HP once per battle; heal 2 HP per verified objective; +10% chance of rarer loot. |

### Blackjack

| Trinket | Tier | Effect |
|---|---|---|
| Lucky Chip | common | +10% bounty coins. |
| Marked Card | uncommon | +1 impact on PREDICT objectives. |
| Counting Abacus | rare | +1 impact on your third clean objective in a row; +6% bounty XP. |
| Mara's Pocket Watch | epic | +1 impact on the first verified bounty objective; blocks the first counterattack each battle; +15% bounty XP. |
| The Gilded Ace | legendary | +1 impact on an objective you get right first time; start every battle with a free mistake; revive at 1 HP once per battle; +15% bounty coins. |

### Casino Slots

| Trinket | Tier | Effect |
|---|---|---|
| Silver Dollar | common | +1 coins on an objective you get right first time. |
| Weighted Die | uncommon | +1 impact when the question type changes. |
| Auditor's Ledger | rare | +1 impact on FIX objectives; +8% bounty XP. |
| Four-Leaf Clip | epic | Blocks the first counterattack each battle; +8% bounty coins; +15% chance of rarer loot. |
| The Probability Lens | legendary | +1 impact when the question type repeats; revive at 1 HP once per battle; +10% bounty XP; +20% chance of rarer loot. |

### Dungeon Crawler

| Trinket | Tier | Effect |
|---|---|---|
| Canary Feather | common | Heal 1 HP per verified objective. |
| Compass Needle | uncommon | +1 impact on a clean follow-up (not the first objective). |
| Ore Sniffer Charm | rare | +6% bounty coins; +15% chance of rarer loot. |
| Brigid's Hard Hat Badge | epic | Restore 2 HP on a bounty Guard Break; 10% less damage from misses; blocks the first counterattack each battle. |
| The Heart of the Mine | legendary | +1 impact on objectives worth 4 or more; start every battle with a free mistake; revive at 1 HP once per battle; heal 2 HP per verified objective. |

### Hunter's set pieces

| Trinket | Tier | Effect |
|---|---|---|
| Jacklight Charm | rare | +1 impact on PREDICT objectives; +8% chance of rarer loot. |
| Pink Cap Charm | rare | +12% bounty coins; +5% chance of rarer loot. |
| Soul Lantern | rare | +1 impact when correcting a missed bounty objective; heal 1 HP per verified objective. |

### Journal echoes of Infinite Dungeon trinkets

| Trinket | Tier | Effect |
|---|---|---|
| Delver's Ash Talisman | rare | +2 impact once the enemy is at 40% Resolve or less. |
| Delver's Book Clasp | rare | Blocks the first counterattack each battle; +10% bounty XP. |
| Delver's Brass Gear | rare | 6% less damage from misses; start every battle with a free mistake. |
| Delver's Bull Ring | rare | +2 impact while you are at half HP or less. |
| Delver's Cave Shell | rare | 8% less damage from misses; blocks the first counterattack each battle. |
| Delver's Copper Spring | rare | +2 impact when correcting a missed bounty objective; +5% bounty XP. |
| Delver's Ember Heart | rare | Restore 4 HP on a bounty Guard Break; heal 1 HP per verified objective. |
| Delver's Hoard Token | rare | +3 coins on a Guard Break; +12% bounty coins. |
| Delver's Ink Seal | rare | +1 impact on an objective you get right first time; +8% bounty XP. |
| Delver's Keeper’s Ring | rare | +2 impact on the first verified bounty objective. |
| Delver's Last Spark | rare | Revive at 1 HP once per battle; heal 1 HP per verified objective. |
| Delver's Loop Thread | rare | +1 impact when the question type repeats; +6% bounty XP. |
| Delver's Oracle Lens | rare | +2 impact on an objective you get right first time. |
| Delver's Pilgrim Knot | rare | Start every battle with a free mistake; +5% bounty XP. |
| Delver's Quiet Page | rare | Heal 1 HP on an objective you get right first time; heal 1 HP per verified objective. |
| Delver's Spectral Chain | rare | +1 impact when the question type repeats; start every battle with a free mistake. |
| Delver's Star Thread | rare | Heal 2 HP on an objective you get right first time. |
| Delver's Still Clock | rare | +1 impact on the first verified bounty objective; start every battle with a free mistake. |
| Delver's Stone Eye | rare | +1 impact while you are at half HP or less; blocks the first counterattack each battle. |
| Delver's Thread Spool | rare | +1 impact on EXPLAIN objectives; +1 impact on a clean follow-up (not the first objective). |
| Delver's Tidal Pearl | rare | +1 impact on FIX objectives; restore 2 HP on a bounty Guard Break. |
| Delver's Tuning Fork | rare | +6 coins on a Guard Break; +8% bounty coins. |
| Delver's Village Lantern | rare | +1 impact on PREDICT objectives; heal 1 HP per verified objective. |
| Delver's Warding Star | rare | Blocks the first counterattack each battle; heal 1 HP per verified objective. |
| Delver's Warm Ember | rare | Heal 2 HP per verified objective; +6% chance of rarer loot. |

### Elite keepsakes

| Trinket | Tier | Effect |
|---|---|---|
| Balancer’s Weight | rare | +1 impact on objectives worth 4 or more; blocks the first counterattack each battle. |
| Caravan Gear | rare | Start every battle with a free mistake; +6% chance of rarer loot. |
| Context Keeper’s Seal | rare | +1 impact on BUILD objectives; blocks the first counterattack each battle. |
| Debt Ghoul Token | rare | +1 impact on the first verified bounty objective; +10% bounty coins. |
| Delivery Seal | rare | Heal 1 HP per verified objective; +6% bounty coins. |
| Echo Knot | rare | +1 impact when the question type changes; blocks the first counterattack each battle. |
| Front Door Key | rare | Start every battle with a free mistake; +5% bounty coins. |
| Greed Spirit’s Coin | rare | +1 coins on an objective you get right first time; +12% chance of rarer loot. |
| Inquisitor’s Sigil | rare | +1 impact on FIX objectives; start every battle with a free mistake. |
| Lantern Keeper’s Wick | rare | Restore 3 HP on a bounty Guard Break; heal 1 HP per verified objective. |
| Open Road Token | rare | +5% bounty XP; +10% chance of rarer loot. |
| Seeded Maze Knot | rare | +1 impact on a clean follow-up (not the first objective); +10% chance of rarer loot. |
| Star Seeker’s Lens | rare | +1 impact when correcting a missed bounty objective; +12% bounty XP. |

### Online shop

| Trinket | Tier | Effect |
|---|---|---|
| Cinder Vow | rare | +2 impact when correcting a missed bounty objective; restore 2 HP on a bounty Guard Break. |
| Pale Guard Locket | legendary | 14% less damage from misses; blocks the first counterattack each battle. |
| Last Laugh Charm | ethereal | Start every battle with a free mistake; revive at 1 HP once per battle; heal 3 HP per verified objective; +10% bounty XP. |

## Icons and worn charms

- Every trinket has its own icon (`ide/frontend/public/campaign-art/items/trinket-<id>.png`, registered in `lanternItemArt.js`, drawn with Codex from `docs/review-art/trinket/CODEX_TRINKET_ICONS_*.md`). A test fails if two share one or a file is missing.
- Every trinket is also worn on the hero in combat as a tiny charm made from its own icon (`prototypes/godot-combat/source-art/charms.py`).
- The Infinite Dungeon's run trinkets are a separate system (`dungeon_items.py`) and were not changed.
