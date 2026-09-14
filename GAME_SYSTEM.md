# Python Quest Lab — Game System

This repo is a real learning system wearing an RPG skin. The game mechanics exist to make progress visible and fun, not to reward fake activity.

## Core loop

1. Choose a project branch.
2. Read its `HANDOFF.md`.
3. Build the code yourself.
4. Use PYR as a Socratic tutor when stuck.
5. Clear mobs by completing meaningful milestones.
6. Earn XP, coins, items and concept evidence.
7. Face short concept interviews.
8. Earn Mastery Shields when a concept is genuinely understood.
9. Beat the project boss by finishing the build and explaining the core logic.

## XP and levels

Suggested baseline rewards:

- small independent feature: +10 XP
- useful bug found and fixed with understanding: +15 XP
- mob / major milestone: +25 XP
- clear explanation of own code: +10 XP
- passed concept interview: +25 XP
- boss clear: +100 XP
- clean clear with no exact solution code: bonus reward

Every 100 current XP grants a level. `lifetime_xp` never decreases and is used for public progress / friendly competition.

## Streaks

A streak counts **meaningful coding days**, not days where the repo is merely opened.

A day counts when at least one of these happens:

- a real feature or milestone is completed;
- a mob is cleared;
- a bug is fixed with understanding;
- a concept interview is completed;
- a meaningful coding session results in code the player can explain.

Failed interviews do **not** break streaks. Struggling does **not** break streaks. Only missing a day breaks the natural streak.

A `Streak Ward` may protect one missed day. Maximum one may be stored at a time.

## Mastery Shields

Each tracked Python concept can earn its own shield. A shield represents evidence that the player could explain and use the concept rather than merely recognise it.

### Bronze Shield
Earned after meaningful project use + a passed PYR interview. Durability: 1 charge.

### Silver Shield
Earned after proving the concept in a second distinct context + another passed interview. Durability: 2 charges.

### Gold Shield
Earned after at least three contexts + a cold interview. Durability: 3 charges.

If a player who already owns a shield fails a later mastery check, one shield charge breaks **instead of damaging HP or the streak**. At zero charges the concept becomes `cracked` and is repaired through a short recovery task/interview. A Shield Repair Kit can restore a charge only after that recovery work.

Early interviews before a shield exists are diagnostic and do not cause damage.

## HP

HP is playful pressure, not punishment for normal mistakes, questions, debugging or failed first-time interviews. Small HP damage is reserved for deliberate challenge-rule breaks such as repeated blind copy/paste after warnings. HP never blocks learning.

## Coins and shop

Coins come from mobs, goals, bosses, streak milestones and good debugging. Purchases never directly buy solution code.

| Item | Cost | Effect |
|---|---:|---|
| Potion | 25 | One stronger hint from PYR |
| Map Scroll | 30 | Break the problem into 3–5 subproblems |
| Syntax Scroll | 35 | Show generic syntax with unrelated values |
| Boss Scout | 60 | One non-code boss hint |
| Shield Repair Kit | 80 | Restore a charge after recovery work |
| Streak Ward | 120 | Protect one missed day; max one stored |
| Ember Crown | 250 | Cosmetic title after two boss clears |

## Goals

Daily quests help start. Weekly quests reward consistency. Long-term goals unlock ranks, shields, boss clears and larger milestones.

## Bosses and mobs

Mobs are project milestones. A boss only counts when the program meets the requirements **and** the player passes a short code interview explaining core logic, edge cases and reasoning.

## Rank ladder

- **F — Apprentice**: starting rank.
- **E — Journeyman**: clear 2 projects and master 3 fundamentals.
- **D — Pathfinder**: clear 4 projects, hold 4 shields and maintain a 5-day best streak.
- **C — Builder**: clear 6 projects and demonstrate reliable program design.
- **B — Python Adventurer**: clear the foundation campaign and pass a mixed fundamentals gauntlet.

## PYR progression

- Tiny Code-Flame — starting form
- Ember Sprite — first boss clear
- Runic Familiar — 3 Mastery Shields
- Forge Wisp — 4 project clears
- Pyre Guardian — foundation campaign clear

## Friendly competition

A friend can fork the repo, reset `progress.json`, and use the same rules. `rivals.json` can point to public `progress.json` files for comparison. Compete on lifetime XP, bosses, shields, streaks, interviews, clean clears and project completion — not hours or lines of code.

## Public profile

`README.md` is the public campaign card. `progress.json` on `main` is canonical. When PYR updates campaign state, it should refresh the README public stats block if displayed values changed.
