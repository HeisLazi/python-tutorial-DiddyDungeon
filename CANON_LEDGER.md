# Python Quest Lab — Canon Ledger

This is the **source of truth for custom campaign rules, invented rewards, and system changes**.

PYR is allowed to be creative, but the campaign should not slowly mutate into contradictory rules. Anything new that matters is recorded here so the player can see what is canon, what is experimental, and what was retired.

## Ruleset

**Current ruleset:** `1.3.0`

## Source priority

When files disagree, use this order:

1. `CANON_LEDGER.md` — current canon / approved changes
2. `TUTOR_CONTRACT.md` — how PYR must behave
3. `LEARNING_PROTOCOL.md` — teaching, Forge phase, Reference Mode and creativity rules
4. `GAME_SYSTEM.md` — RPG mechanics and progression
5. `ACTIVITY_SYSTEM.md` — Git-derived dev activity and rival scoring rules
6. current branch `HANDOFF.md` — project-specific requirements/rewards
7. `progress.json` — current player state, not a rules document
8. `activity.json` — generated dev-activity state, not a rules document

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
| SYS-014 | Dev Activity is machine-derived from Git history and stored separately from learning progression. | CANON |
| SYS-015 | Commit activity cannot directly grant XP, coins, Mastery Shields, boss clears or concept mastery. | CANON |
| SYS-016 | Activity Score rewards active days/streaks and caps effective commits per day to discourage commit spam. | CANON |
| SYS-017 | Learning streak and Dev streak are separate metrics with separate meanings. | CANON |
| SYS-018 | PYR may read activity stats and celebrate them, but must not manually edit or award machine-derived activity values. | CANON |
| SYS-019 | Quest Lab is a standalone learning system. External courses may supplement it but are never required campaign dependencies or sources of mastery. | CANON |
| SYS-020 | The Forge RPG Shell has first-class Quest Journal, Codex, Character, Homestead and Settings screens around the real editor/terminal workflow. | CANON |
| SYS-021 | Existing campaign coins may be spent on approved cosmetic IDE/Homestead items. Cosmetic ownership gives no XP, hint, shield, streak or rival-score advantage. | CANON |
| SYS-022 | Functional/accessibility IDE settings remain free; only cosmetic presentation may be coin-gated. | CANON |
| SYS-023 | The Codex may foreshadow mob names, concepts and encounter styles but must not reveal hidden exact answers or paste-ready project solutions. | CANON |
| SYS-024 | Cosmetic ownership/equipment is canonical campaign state; device-specific layout preferences are local UI state and do not count as progression. | CANON |

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

## 1.3.0 — Forge RPG Shell & Homestead

- confirmed Quest Lab remains fully standalone from Boot.dev and other external courses;
- added first-class Forge, Quest Journal, Codex, Character, Homestead and Settings destinations;
- approved cosmetic IDE/Homestead purchases using existing campaign coins;
- separated free usability/accessibility settings from coin-gated cosmetics;
- made cosmetic ownership/equipment portable campaign state while keeping panel/layout preferences device-local;
- formalized Codex foreshadowing without hidden-answer or exact-solution spoilers;
- added `RPG_SHELL_PLAN.md` as the implementation roadmap for the living RPG shell.

## 1.2.0 — Dev Activity League

- added machine-derived `activity.json` from Git commit history;
- added separate Learning Streak and Dev Streak meanings;
- added Activity Score with active-day weighting and per-day commit caps;
- added activity automation via GitHub Actions;
- added rival competition fields for commits, active days, streaks and Activity Score;
- explicitly prevented commit volume from granting learning XP/mastery;
- added `ACTIVITY_SYSTEM.md` as the portable/forkable activity rules document.

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
