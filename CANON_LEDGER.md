# Python Quest Lab — Canon Ledger

This file keeps custom rules, AI-created rewards and campaign changes consistent.

**Current ruleset:** `1.1.0`

## Source priority

1. `CANON_LEDGER.md`
2. `TUTOR_CONTRACT.md`
3. `LEARNING_PROTOCOL.md`
4. `GAME_SYSTEM.md`
5. current branch `HANDOFF.md`
6. canonical `main/progress.json` for player state

## Canon mechanics

- evidence-backed XP/coins only;
- meaningful-day streaks;
- Mastery Shields protect later failed checks before HP;
- bosses require working code plus explanation/interview;
- PYR is a Socratic tutor, not the project coding agent;
- Teach → Practice → Teach-back → Forge → Review → Interview → Record;
- teaching examples may show code but cannot be paste-ready project solutions;
- Reference Mode gives project-specific exact help at 50% milestone XP/coins;
- Recovery Trials can restore up to 25% of the original full reward, max 75% total;
- creativity bonuses use +5 / +10 / +20 / up to +30 XP bands;
- hidden cosmetic/lore/trophy rewards may be invented and become PLAYER-CANON after being logged;
- mechanics changing XP, coins, shields, streaks or rival scoring remain PROVISIONAL until approved;
- cosmetic rarity does not increase rival power.

## Status meanings

- **CANON** — shared universal rule/reward.
- **PLAYER-CANON** — persistent part of one player's campaign story.
- **PROVISIONAL** — proposed, not active as a universal mechanic yet.
- **RETIRED** — kept for history but inactive.

## Discovery Registry

| Date | ID | Name | Type | Trigger | Effect | Status | Notes |
|---|---|---|---|---|---|---|---|
| 2026-09-14 | DISC-000 | PYR, Tiny Code-Flame | Companion | Campaign creation | Starting companion identity | PLAYER-CANON | Evolves through learning milestones |

Entry template:

```text
| YYYY-MM-DD | DISC-### | Name | cosmetic / trophy / mechanic / lore / item | Trigger | Exact effect | PLAYER-CANON / PROVISIONAL / CANON | Notes |
```

PYR chooses the next unused `DISC-###` number when creating a revealed reward.

## Proposed mechanics

| ID | Proposal | Status | Decision notes |
|---|---|---|---|
| — | No pending proposals yet. | — | — |

## Changelog

### 1.1.0
- teach-first learning flow;
- Forge phase;
- Reference Mode 50% reward multiplier;
- Recovery Trials;
- creativity bands;
- hidden reward generation;
- persistent discovery/canon tracking.

### 1.0.0
- projects, mobs, bosses, XP, levels, coins, streaks, shields, interviews, PYR progression, public character sheet and Rival Mode foundation.

Do not delete inconvenient history. Add entries when rules/rewards change so future players and AI tutors can reconstruct what actually became canon.
