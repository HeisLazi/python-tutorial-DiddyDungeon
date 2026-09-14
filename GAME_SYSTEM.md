# Python Quest Lab — Game System

This repo is a real learning system wearing an RPG skin. The mechanics exist to make progress visible and fun without rewarding fake activity.

## Core learning loop

The canonical learning flow is defined in `LEARNING_PROTOCOL.md`:

**Diagnose → Teach → Practice → Teach-back → Forge → Review → Interview → Record**

The important distinction is simple:

- during **Teach / Practice**, PYR may show clear code examples as long as they are unrelated enough that they cannot be pasted into the current project;
- during **Forge**, the player must implement the project requirement from scratch;
- if the player truly cannot bridge the gap, **Reference Mode** may be used with an explicit 50% reward multiplier for the affected milestone.

Struggling, asking questions, needing more explanation, and using unrelated examples do **not** reduce rewards.

---

# XP and levels

Baseline rewards:

- small independent feature: +10 XP;
- useful bug found/fixed with understanding: +15 XP;
- mob / major milestone: +25 XP;
- clear explanation of own code: +10 XP;
- passed concept interview: +25 XP;
- boss clear: +100 XP;
- creativity: +5 / +10 / +20 / up to +30 XP depending on the addition;
- clean clear: branch-defined bonus reward.

Every 100 current XP grants a level. Carry excess XP forward.

`lifetime_xp` never decreases and is used for public progression / friendly competition.

## Assistance multiplier

If PYR enters **Reference Mode** and gives project-specific exact implementation code for a milestone:

- multiply that milestone's XP and coin reward by **0.50**;
- record the assistance;
- mark the milestone guided/assisted;
- required-core Reference Mode removes project Clean Clear eligibility.

A later **Recovery Trial** can recover up to 25% of the original full reward, so an assisted milestone can reach a maximum of 75% of the original reward. The assistance remains part of the historical record.

---

# Creativity and discoveries

Required features prove the curriculum. Creative additions make the project personally interesting and reward design thinking.

Creativity bands:

| Tier | XP | Meaning |
|---|---:|---|
| Wild Spark | +5 | small original polish or useful tweak |
| Embercraft | +10 | meaningful extra feature/rule/QoL improvement |
| Relic Craft | +20 | substantial optional system interacting with existing logic |
| Mythic Discovery | up to +30 | unusually strong original extension requiring planning/debugging/explanation |

PYR may create **hidden rewards** after memorable achievements. They are not announced in advance.

After reveal, any AI-created reward/mechanic must be recorded in `CANON_LEDGER.md`.

- cosmetic/lore/trophy rewards can become `PLAYER-CANON` immediately;
- mechanics affecting XP, coins, shields, streaks or rival scoring must be `PROVISIONAL` until approved;
- rival power does not increase from invented cosmetic rarity.

---

# Streaks

Python Quest Lab intentionally has **two different streaks**.

## Learning streak

Stored in `progress.json` and verified by PYR.

A learning-streak day counts when at least one of these happens:

- real feature/milestone progress;
- a mob clear;
- a bug fixed with understanding;
- a concept interview;
- a meaningful session resulting in code the player can explain.

Failed interviews do **not** break this streak. Struggling does **not** break it. Only missing a meaningful learning day breaks the natural streak.

A `Streak Ward` may protect one missed learning day. Maximum one stored unless canon changes later.

## Dev streak

Stored in `activity.json` and derived from Git commit history.

A Dev-streak day means qualifying code was committed that day. PYR cannot manually award, remove or repair this streak.

Full rules: [`ACTIVITY_SYSTEM.md`](./ACTIVITY_SYSTEM.md).

---

# Mastery Shields

Each tracked concept can earn a shield. A shield represents evidence that the player can explain and use the concept rather than merely recognise it.

## Bronze

Earned after meaningful use in a project plus a passed interview.

Durability: 1 charge.

## Silver

Earned after proving the concept in a second distinct context plus another interview.

Durability: 2 charges.

## Gold

Earned after proving the concept across at least three contexts plus a cold interview.

Durability: 3 charges.

## Cracked shields

If a player who already owns a shield fails a later mastery check, remove one shield charge **instead of damaging HP or the learning streak**.

At zero charges, mark the concept `cracked`. Repair it through a recovery exercise/interview. A Shield Repair Kit can restore a charge only after recovery work is completed.

First-time interviews before a shield exists are diagnostic and deal no damage.

---

# HP

HP is playful pressure, not punishment for not knowing.

Never remove HP for normal learning mistakes, questions, first-time failed interviews, debugging attempts, slow progress or asking for more teaching.

Small narrative HP damage is only for explicit challenge-rule breaks such as repeated blind copy/paste after warnings. HP never blocks learning.

---

# Coins and shop

Coins come from mobs, goals, bosses, learning-streak milestones, debugging and other canon rewards.

Current shop:

| Item | Cost | Effect |
|---|---:|---|
| Potion | 25 | one stronger hint from PYR |
| Map Scroll | 30 | break current problem into 3–5 smaller subproblems |
| Syntax Scroll | 35 | show generic Python syntax using unrelated values |
| Boss Scout | 60 | one non-code boss hint |
| Shield Repair Kit | 80 | restore one shield charge after recovery work |
| Streak Ward | 120 | protect one missed learning day; max one stored |
| Ember Crown | 250 | cosmetic title after two boss clears |

The static dashboard cannot safely write to GitHub by itself. Purchases become requests to PYR, who verifies balance/requirements and updates canonical state.

---

# Goals

The campaign has three goal layers:

- **Daily quests** — small reasons to sit down and start;
- **Weekly quests** — reward consistency and different kinds of learning;
- **Long-term goals** — ranks, shields, boss clears and larger milestones.

Daily quests should fit a normal evening. Weekly quests should reward consistency rather than giant single-session grinds.

---

# Bosses and mobs

Mobs are milestones inside a project. A boss is the final integrated challenge.

A boss counts only when:

1. required behaviour works;
2. the player can explain core logic;
3. a short code interview is passed;
4. assistance/clean-clear status is recorded honestly.

Interview prompts may ask the player to explain code, predict state, identify a bug/edge case, describe a concept, or make a small change without being handed the answer.

---

# Rank ladder

Ranks are long-term milestones, not raw XP levels.

- **F — Apprentice**: starting rank.
- **E — Journeyman**: clear 2 projects and master 3 fundamentals.
- **D — Pathfinder**: clear 4 projects, hold 4 shields and reach a 5-day best learning streak.
- **C — Builder**: clear 6 projects and demonstrate reliable program design.
- **B — Python Adventurer**: clear all foundation projects and pass a mixed fundamentals gauntlet.

Higher ranks arrive only when the curriculum expands into files/JSON, exceptions, modules, testing, OOP, APIs and beyond.

---

# PYR progression

PYR grows with actual learning.

Suggested forms:

- Tiny Code-Flame — start;
- Ember Sprite — first boss clear;
- Runic Familiar — 3 Mastery Shields;
- Forge Wisp — 4 project clears;
- Pyre Guardian — foundation campaign clear.

Bond rises from meaningful sessions, explanations, self-debugging, interviews, creativity and boss victories — not passive chat or commit volume.

---

# Equipment and trophies

Equipment is mostly cosmetic/achievement-driven. It gives the public profile personality without pretending cosmetic gear equals skill.

Examples:

- Loopblade — strong loops interview;
- Function Staff — functions shield;
- Ledger Buckler — dictionaries shield;
- House Token — Blackjack boss trophy;
- Arena Crest — Creature Battle boss trophy.

PYR may invent new player-canon cosmetic gear when earned, but must log it in `CANON_LEDGER.md`.

---

# Dev Activity League

Commit history powers a separate competitive layer documented in [`ACTIVITY_SYSTEM.md`](./ACTIVITY_SYSTEM.md).

Machine-derived metrics include:

- 7-day / 30-day commits;
- active dev days;
- current and longest Dev streak;
- active branches;
- rolling Activity Score.

The Activity Score rewards **consistency over spam**: effective commits are capped per day for scoring, while raw commits remain visible.

Commit activity never directly grants:

- XP;
- coins;
- Mastery Shields;
- concept evidence;
- boss clears;
- Clean Clears.

That keeps the competition useful: one player can be the **most active developer this month** while another can still have stronger proven Python mastery.

---

# Friendly competition / Rival Mode

The campaign is designed to be forkable.

A friend can fork the repo, reset `progress.json`, change `profile.player_id`, set their GitHub username/start timestamp in `activity_config.json`, and use the same canon rules.

Rival comparison can show two score families side by side.

### Learning power

- lifetime XP;
- bosses defeated;
- Mastery Shields;
- learning streak;
- interviews passed;
- clean clears;
- project completion.

### Dev activity

- Activity Score;
- commits 7d / 30d;
- active dev days;
- Dev streak;
- active branches.

Competition should reward **verified learning plus consistent real development**, not hours logged or lines of code.

One-off cosmetic rewards do not affect competitive power.

---

# Public profile rule

`README.md` is the public campaign card. `progress.json` is canonical learning/player state. `activity.json` is machine-derived development activity. `CANON_LEDGER.md` is the public history of custom mechanics/rewards.

The README should show current character progress, active quest, assistance integrity, creativity/discoveries, learning streak, Dev Activity League, shields and boss progress.

PYR refreshes learning-state blocks. The GitHub activity workflow refreshes machine-derived activity blocks.

---

# Canon rule

The exact rules for adding, approving and retiring custom mechanics/rewards live in `CANON_LEDGER.md`.

Do not silently mutate progression or activity-scoring rules. Preserve history so future players and AI tutors can reproduce the same system.
