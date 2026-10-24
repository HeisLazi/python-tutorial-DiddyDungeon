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

## Signs and stats (proposed 2026-10-24, awaiting sign-off)

Signs are **what you know**; stats are **how you fight**. Both grow by doing.

### Signs level up by use

Every challenge where a concept is used correctly gives that sign XP:

| Event | Sign XP |
| --- | --- |
| Clean cast (solved first try, no bugs) | +3 |
| Recovered (solved after a miss) | +1 |
| Used in a verified campaign bounty | +5 |
| Teach-back to PYR | +2 |

Signs level 1 to 10. Ranks need the XP **and** an achievement gate, so drills
alone can't reach mastery:

| Level | Rank | Gate |
| --- | --- | --- |
| 3 | I · Inscribed | Read the page and pass a drill (Tutor) |
| 6 | II · Honed | e.g. 10 clean casts with the concept in the Dungeon |
| 10 | III · Mastered | Used in a real campaign bounty, plus a teach-back |

- **Perks:** each rank unlocks a sign perk that gives protection or
  information, never a skipped question (e.g. Fork II: your first
  wrong-branch mistake in a fight costs no HP; Chain III: bigger Resolve chips
  against Drowners).
- **Dulling:** a sign unused for about a week loses a little XP and dulls one
  step (never below rank I); practice restores it. Spaced repetition as
  blade upkeep.
- Mastered signs exploit boss weaknesses in the campaign and can be etched
  onto gear.

### Stats grow from how you play

| Stat | Effect | Grows from |
| --- | --- | --- |
| Strength | Bigger Resolve chips per correct answer, so breaks come sooner | Writing and fixing code (bug hunts, code tasks) |
| Insight | Reveals weaknesses and traps, identifies unknown items | Reading code (predict output, trace variables) |
| Focus | Stronger and more PYR hints; sign perks hit harder | Explaining (teach-backs, explain questions) |
| Vitality | More max HP | Consistency (days practised, delves survived) |

Plus one free stat point per hunter level.

### The iron rule: questions are the fight

**A fight with N questions always takes N correct answers.** No stat, sign,
perk, gear or potion skips a question or shortens a fight. A wrong answer
means that question is answered again. Getting stronger makes fights safer
and calmer, never shorter.

### Resolve: the enemy's guard, not its health

A fight has two separate bars:

- **Progress:** the questions. Only correct answers move it.
- **Resolve:** the enemy's guard. Every correct answer chips it; Strength and
  the matching sign's level make each chip bigger. At zero the enemy is
  **broken**, then its Resolve refills.

A break only ever **helps**:

- **Free mistake:** your next wrong answer costs no HP.
- **Mechanic interrupted:** whatever the enemy is charging stops (a
  self-destruct countdown, an enrage, a heal, "scrambling your code").
- **A small loot bonus.**

Example: The House (5 questions) starts a Lockdown countdown. Two clean
answers break its Resolve: the Lockdown stops and a free mistake is banked. A
wrong third answer is absorbed and re-answered. The fight ends after exactly
five correct answers.

Stats and sign perks follow the same rule: Strength means faster breaks,
Insight shows mechanics coming, Focus gives better hints, Vitality gives more
HP, and perks give protection or information. None changes the question
count.

### Where it shows

The Character screen becomes a hunter sheet: level, the four stats, the sign
book (level, XP bar, rank gates, perks), milestones and the hunt journal.

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
- **Inspiration:** Brogue is the main model (small readable tile floors, fog
  of war, every item matters). Its best trick maps onto learning: unknown
  potions and scrolls carry a short code snippet you trace to identify them.
  Slay the Spire for branching between floors; Shattered Pixel Dungeon for the
  clean pixel look; Cataclysm-lite crafting gated by sign rank (not its
  survival depth); a Dwarf Fortress-style hunt journal of your kills; Darkest
  Dungeon's camp upgrades between delves; Hades-style story that advances even
  on a failed run.

## Shared progression

- **Signs:** charged by all three modes (see above).
- **Trophies and materials:** from Dungeon kills and campaign contracts; spent
  at the Merchant on gear, beast oils (bonus damage against one beast type) and
  potions.
- **Hunter level:** XP from every mode; unlocks regions and towns.
- **Familiar places, re-themed:** Homestead is the hunter's camp (rest,
  loadout); Market is the Merchant; PYR is your familiar and mentor.

## Build order

1. **Campaign story pass** (story contracts and longer boards shipped
   2026-10-24 as Phase D1, Blackjack first: 19 contracts in three acts, Act III
   builds an agent that plays it; every project has a story file since D2/D3:
   ten campaigns, 153 contracts, including The Clockwork Arena (Connect Four
   engines) and The Familiar (an AI agent from scratch)): a story arc,
   hunter-voice contract briefs, each contract showing its beast and sign and
   linking to the Codex. The Codex grew to 23 signs on 2026-10-25 (strings,
   exceptions, files and JSON, sets, grids, sorting, references, classes,
   testing, callbacks, agents, recursion, search, simulation), each with a
   beast, five new delve regions, oils and vial readings.
2. **Dungeon as a crawler** (region delves, region beasts and named bosses
   shipped 2026-10-24 as Phase C1; room-grid floors under fog, walk-back
   travel and stairs between floors shipped 2026-10-24 as C3): region
   delves, bestiary mobs weighted to weak signs, floor goals and named bosses,
   plus a polish pass.
3. **Materials and crafting** (drops, banking and elite trinkets shipped
   2026-10-24 as Phase C1; beast oils at the Merchant's alchemy bench shipped
   2026-10-24 as C2, with kit smithing from boss essences and Brogue-style
   identify-by-reading for unmarked vials):
   drops, banking, Merchant recipes.
4. **Signs and stats** (tracking, hunter sheet and codex levels shipped 2026-10-24; Resolve breaks, mechanics and stat effects in Dungeon fights shipped 2026-10-24 as Phase B; Focus multiplies the sign share of the chip, C1): sign XP by use with rank gates, dulling, the four
   stats, Resolve breaks (free mistake, interrupted mechanics) under the iron
   rule, and the hunter sheet. (Sign XP
   and stat tracking in the backend comes first; everything else reads it.)

No new top-level screens until these land.

## Open questions (to brainstorm)

- Hunter level: what does a level give? Talent trees (Combat, Signs, Alchemy)?
- Crafting: which materials, which recipes, how gear changes a fight.
- Campaign stories for the other towns (Detective, Creature Battle, Casino…).
- How campaign bosses use signs mechanically.
- Elite trinket drops (promised in the Dungeon UI, not granted yet).
