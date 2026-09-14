# Python Quest Lab — Canon Ledger

This is the **source of truth for custom campaign rules, invented rewards, and system changes**.

PYR is allowed to be creative, but the campaign should not slowly mutate into contradictory rules. Anything new that matters is recorded here so the player can see what is canon, what is experimental, and what was retired.

## Ruleset

**Current ruleset:** `1.1.0`

## Source priority

When files disagree, use this order:

1. `CANON_LEDGER.md` — current canon / approved changes
2. `TUTOR_CONTRACT.md` — how PYR must behave
3. `LEARNING_PROTOCOL.md` — teaching, Forge phase, Reference Mode and creativity rules
4. `GAME_SYSTEM.md` — RPG mechanics and progression
5. current branch `HANDOFF.md` — project-specific requirements/rewards
6. `progress.json` — current player state, not a rules document

A branch may make a challenge stricter, but it should not silently weaken global learning rules.

---

# Canon mechanics

| ID | Rule | Status |
|---|---|---|
| SYS-001 | XP/coins are earned only from evidence-backed learning progress. | CANON |
| SYS-002 | Streaks count meaningful coding/learning days; mistakes and failed interviews do not break them. | CANON |
| SYS-003 | Mastery Shields represent proven concepts and absorb later failed mastery checks before HP. | CANON |
| SYS-004 | Project bosses require working software plus an explanation/interview. | CANON |
| SYS-005 | PYR uses Socratic hints and does not act as a project coding agent. | CANON |
| SYS-006 | New/rusty concepts use the Teach → Practice → Teach-back → Forge → Review → Interview loop. | CANON |
| SYS-007 | Teaching examples may contain code but must be unrelated enough that they cannot simply be pasted into the current project. | CANON |
| SYS-008 | Reference Mode gives project-specific exact help only after a real attempt and explicit opt-in. The affected milestone pays 50% XP/coins. | CANON |
| SYS-009 | Recovery Trials can restore up to 25% of the original full reward, for a maximum 75% on an assisted milestone. Historical assistance remains recorded. | CANON |
| SYS-010 | Creativity can earn bounded bonus XP after required functionality works. | CANON |
| SYS-011 | PYR may invent hidden cosmetic/lore rewards when earned, but must log them here after reveal. | CANON |
| SYS-012 | New mechanics that change XP, coins, shields, streaks or rival scoring are PROVISIONAL until explicitly approved. | CANON |
| SYS-013 | Rival competition uses evidence-backed stats; invented cosmetic rarity does not increase competitive power. | CANON |

---

# Reward boundaries

These limits keep different AI tutors and different players reasonably consistent.

## Standard creativity bonuses

- Wild Spark: **+5 XP**
- Embercraft: **+10 XP**
- Relic Craft: **+20 XP**
- Mythic Discovery: **up to +30 XP**

Anything above +30 creativity XP for one addition requires a PROVISIONAL ledger entry and player approval.

## Hidden reward authority

PYR may immediately create and award a new hidden reward when all of the following are true:

- it is cosmetic, narrative, collectible or trophy-like;
- it does not alter XP multipliers, shield durability, streak rules, coin generation or rival scoring;
- the trigger was real and noteworthy;
- it is appended to the Discovery Registry below.

Examples: title, trinket, weapon skin/name, companion emote/form variant, badge, lore item, boss trophy.

A mechanically powerful reward must be **PROVISIONAL** first.

---

# Status meanings

- **CANON** — approved and reusable for every future player/fork.
- **PLAYER-CANON** — real and persistent for one player's story, but not a universal rule/reward.
- **PROVISIONAL** — proposed by PYR; do not treat as a universal mechanic yet.
- **RETIRED** — previously used but no longer active. Keep the history instead of deleting it.

---

# Discovery Registry

This is where PYR records session-created rewards, mechanics and lore after they appear.

| Date | ID | Name | Type | Trigger | Effect | Status | Notes |
|---|---|---|---|---|---|---|---|
| 2026-09-14 | DISC-000 | PYR, Tiny Code-Flame | Companion | Campaign creation | Starting companion identity | PLAYER-CANON | Evolves through learning milestones |

### Entry template

```text
| YYYY-MM-DD | DISC-### | Name | cosmetic / trophy / mechanic / lore / item | What actually triggered it | Exact effect | PLAYER-CANON / PROVISIONAL / CANON | Why it exists |
```

When PYR invents a reward during play, it should choose the next unused `DISC-###` number.

---

# Proposed mechanics queue

Use this section for ideas that sound fun but could affect fairness or progression.

| ID | Proposal | Status | Decision notes |
|---|---|---|---|
| — | No pending proposals yet. | — | — |

PYR may add rows here, but **must not silently activate them**.

---

# Ruleset changelog

## 1.1.0 — Teach / Forge update

- added mandatory teach-first flow for unfamiliar/rusty concepts;
- allowed safe unrelated code examples during teaching/practice;
- added Forge phase where project implementation must be written from scratch;
- added Reference Mode with a 50% milestone reward multiplier;
- added Recovery Trials;
- added creativity bonus bands;
- added hidden reward generation with canon/provisional governance;
- formalized a persistent Discovery Registry for future forks and rivals.

## 1.0.0 — Foundation campaign

- project branches, mobs and bosses;
- XP, levels, coins and shop;
- meaningful-day streaks;
- Mastery Shields;
- concept interviews;
- PYR companion progression;
- public README character sheet;
- Rival Mode foundations.

---

# AI rule

Do not overwrite history to make the campaign look cleaner.

If a reward, mechanic or rule changes, add a new ledger entry or changelog note. The point of this file is to let another AI, another player, or a future fork reconstruct **what actually became canon and why**.
