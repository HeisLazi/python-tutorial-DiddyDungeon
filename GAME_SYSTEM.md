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

Earned after:

- using the concept meaningfully in a project; and
- passing a short PYR interview about it.

Durability: 1 charge.

### Silver Shield

Earned after proving the concept in a second distinct context and passing another interview.

Durability: 2 charges.

### Gold Shield

Earned after proving the concept across at least three contexts and passing a cold interview without needing the original code open for every answer.

Durability: 3 charges.

### Cracked shields

If a player who already owns a shield fails a later mastery check, one shield charge breaks **instead of damaging HP or the streak**.

When all charges are gone, the concept becomes `cracked`. Nothing is erased and the streak remains safe. The player repairs the shield by completing a short recovery exercise/interview. A Shield Repair Kit may restore one charge only after that recovery task is completed.

Early interviews taken before a shield has ever been earned do not cause damage; they are diagnostic.

## HP

HP is playful pressure, not a punishment for not knowing something.

Do not remove HP for:

- asking questions;
- making normal mistakes;
- failed first-time interviews;
- debugging attempts;
- taking time to understand.

Small HP damage may be used for deliberate challenge-rule breaks, such as repeatedly blind-copying exact solution code after warnings. HP can never block learning.

## Coins and the shop

Coins are earned from mobs, goals, bosses, streak milestones and good debugging. Shop purchases must never directly buy a solution.

Current shop:

| Item | Cost | Effect |
|---|---:|---|
| Potion | 25 | One stronger hint from PYR |
| Map Scroll | 30 | Break the current problem into 3–5 smaller subproblems |
| Syntax Scroll | 35 | Show generic Python syntax using unrelated values |
| Boss Scout | 60 | One non-code hint about the current boss |
| Shield Repair Kit | 80 | Restore one shield charge after a recovery question |
| Streak Ward | 120 | Protect one missed day; max one stored |
| Ember Crown | 250 | Cosmetic title after two boss clears |

A static dashboard cannot safely write to GitHub by itself. Clicking/buying from the dashboard should produce a purchase request for PYR. PYR verifies the balance and requirements, then updates `progress.json`.

## Goals

The campaign has three goal layers:

- **Daily quests** — small reasons to sit down and start.
- **Weekly quests** — reward consistency and multiple forms of learning.
- **Long-term goals** — ranks, shields, boss clears and larger milestones.

Daily quests should remain achievable in one normal evening. Weekly quests should reward consistency rather than huge single sessions.

## Bosses and mobs

Mobs are milestones inside a project. A boss is the final integrated challenge.

A boss only counts as defeated when:

1. the program meets the branch requirements; and
2. the player passes a short code interview explaining the important logic.

The interview should include some combination of:

- explain what this section does;
- predict what happens for a given input;
- identify a bug or edge case;
- describe how a specific concept is being used;
- make a small change without being given the answer.

## Rank ladder

Ranks are long-term milestones, not raw XP levels.

- **F — Apprentice**: starting rank.
- **E — Journeyman**: clear 2 projects and master 3 fundamentals.
- **D — Pathfinder**: clear 4 projects, hold 4 shields and maintain a 5-day best streak.
- **C — Builder**: clear 6 projects and demonstrate reliable program design.
- **B — Python Adventurer**: clear all foundation projects and pass a mixed fundamentals gauntlet.
- Higher ranks should only be introduced when the curriculum expands into files/JSON, exceptions, modules, testing, OOP and APIs.

## PYR progression

PYR grows with the player's actual learning.

Suggested forms:

- Tiny Code-Flame — starting form
- Ember Sprite — first boss clear
- Runic Familiar — 3 Mastery Shields
- Forge Wisp — 4 project clears
- Pyre Guardian — foundation campaign clear

PYR's bond can rise from meaningful sessions, explanations, self-debugging and boss victories.

## Equipment and trophies

Equipment is mostly cosmetic and achievement-driven. It gives the public profile personality without pretending cosmetic gear equals skill.

Examples:

- Loopblade — strong loops interview
- Function Staff — functions shield
- Ledger Buckler — dictionaries shield
- House Token — Blackjack boss trophy
- Arena Crest — Creature Battle boss trophy

## Friendly competition / rival mode

The campaign is designed to be forkable.

A friend can fork the repo, reset `progress.json`, change `profile.player_id`, and use the same rules. Each player can then add the other's public `progress.json` URL to `rivals.json`.

The dashboard may compare:

- lifetime XP;
- bosses defeated;
- Mastery Shields earned;
- current and longest streak;
- interviews passed;
- clean clears;
- project completion.

Competition should reward **verified learning milestones**, not hours logged or lines of code. The system is friendly and self-reported; the AI tutor is expected to be conservative when awarding progress.

## Public profile rule

`README.md` is the public campaign card. `progress.json` is the canonical state. The README should show the current character, streak, shields, boss clears, active quest and major achievements so visitors can see the learning journey without opening the dashboard.

When PYR updates campaign state, it should also refresh the public stats block in `README.md` if any displayed values changed.
