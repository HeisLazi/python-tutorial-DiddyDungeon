# Game direction

Agreed 2026-10-24. This is the north star for Quest Lab ("Diddy Dungeon"); new
features should fit it, and open questions are listed at the end.

## The fantasy

You are **Tate Buti, a monster hunter**. In this world bad code breeds monsters:
every bug is a **beast**, and every Python concept is a **sign** (a spell) that
beats one. Learning Python is how you hunt.

## Three modes, three jobs

| Mode | Job | Feel |
| --- | --- | --- |
| **Campaign** | The story. Each project is a town with a monster; its bounties are story contracts you build in the Forge; the boss is the town's monster. | Narrative, building real code |
| **Tutor (Hunter's Codex)** | Training. Contracts board, Bestiary and Signs; study the beast, train the sign, safely. | Calm, no risk |
| **Infinite Dungeon** | A dungeon crawler. Delve for crafting materials, XP and coins. | Risky, rewarding |

Rule: **combat stays code.** Every fight in every mode is a code challenge
(predict, trace, fix or write); the crawler adds exploration, loot and risk
around it, never instead of it.

## Signs: how you get better at one

Each sign (concept) has three ranks, each earned in a different mode:

| Rank | Proves | Earned in |
| --- | --- | --- |
| I · Inscribed | You understand it | Tutor: read the page and pass a warm-up drill |
| II · Honed | You can use it under pressure | Dungeon: clean kills of that sign's beasts |
| III · Mastered | You can build with it | Campaign: a verified bounty that uses it, plus a one-sentence teach-back to PYR |

- **Dulling:** a sign unused for about a week dulls one step (never below
  rank I); a quick drill restores it. Spaced repetition as blade upkeep.
- **Power:** higher ranks deal more damage to that sign's beasts and give hint
  glyphs in the Dungeon, exploit boss weaknesses in the campaign, and can be
  etched onto gear.

## Dungeon crawler (first pass)

- **Choose a delve** by region (Basics Village outskirts, Collection Caves,
  Flow Keep). Beasts come from that region's bestiary, weighted toward the
  player's weakest signs.
- **Map:** branching paths between floors; a small grid of rooms inside each
  floor (doors, chests, traps, shrines, camp, merchant, boss room).
- **Risk:** HP carries across a floor. Bank loot at a camp or push deeper;
  dying loses only unbanked loot (banked materials, XP and sign progress stay).
- **Loot:** crafting materials (beast parts, ores), XP, coins, recipes and sign
  progress. Materials are the one thing that leaves a run and enters the save.
- **Length:** a delve should fit in 10 to 15 minutes.

## Shared progression

- **Signs:** charged by all three modes (see above).
- **Trophies and materials:** from Dungeon kills and campaign contracts; spent
  at the Merchant on gear, beast oils (bonus damage against one beast type) and
  potions.
- **Hunter level:** XP from every mode; unlocks regions and towns.
- **Familiar places, re-themed:** Homestead is the hunter's camp (rest,
  loadout); Market is the Merchant; PYR is your familiar and mentor.

## Build order

1. **Campaign story pass:** Blackjack first; a story arc, hunter-voice contract
   briefs, each contract showing its beast and sign and linking to the Codex.
2. **Dungeon as a crawler:** region delves, bestiary mobs weighted to weak
   signs, floor goals and named bosses, plus a polish pass.
3. **Materials and crafting:** drops, banking, Merchant recipes.
4. **Sign ranks with real effects:** rank I/II/III tracking, dulling, power in
   fights.

No new top-level screens until these land.

## Open questions (to brainstorm)

- Hunter level: what does a level give? Talent trees (Combat, Signs, Alchemy)?
- Crafting: which materials, which recipes, how gear changes a fight.
- Campaign stories for the other towns (Detective, Creature Battle, Casino…).
- How campaign bosses use signs mechanically.
- Elite trinket drops (promised in the Dungeon UI, not granted yet).
