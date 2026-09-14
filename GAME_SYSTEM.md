# Python Quest Lab — Game System

This campaign is a real learning system wearing an RPG skin.

The canonical learning flow is in `LEARNING_PROTOCOL.md`:

**Diagnose → Teach → Practice → Teach-back → Forge → Review → Interview → Record**

During Teach/Practice, PYR may show unrelated examples. During Forge, the player implements the active project requirement from scratch.

## XP

Baseline:
- small feature +10 XP;
- understood bug fix +15 XP;
- mob +25 XP;
- explanation +10 XP;
- interview +25 XP;
- boss +100 XP;
- creativity +5 / +10 / +20 / up to +30 XP.

Every 100 current XP grants a level. `lifetime_xp` never decreases.

## Reference Mode

Project-specific exact help is allowed only after a real attempt and explicit opt-in.

- affected milestone XP/coins × 0.50;
- milestone is recorded assisted;
- required-core Reference Mode removes Clean Clear eligibility;
- a Recovery Trial may later restore 25% of the original full reward, max 75% total;
- historical assistance stays recorded.

Normal teaching, pseudocode and unrelated syntax examples carry no penalty.

## Creativity

Extra ideas beyond required functionality can earn:
- Wild Spark +5 XP;
- Embercraft +10 XP;
- Relic Craft +20 XP;
- Mythic Discovery up to +30 XP.

PYR may invent hidden cosmetic/lore/trophy rewards after they are earned. Revealed rewards must be logged in `CANON_LEDGER.md`. New mechanics affecting competitive progression remain PROVISIONAL until approved.

## Streaks

Only meaningful coding/learning days count. Struggling, wrong answers and failed interviews do not break streaks. A Streak Ward can protect one missed day.

## Mastery Shields

Bronze: meaningful use + interview, 1 charge.
Silver: second distinct context + interview, 2 charges.
Gold: at least three contexts + cold interview, 3 charges.

A later failed check breaks shield charges before HP/streak. At zero charges the concept is cracked until recovery work repairs it.

## HP

Normal learning never costs HP. Small narrative damage is reserved for explicit challenge-rule breaks like repeated blind copy/paste after warnings.

## Shop

| Item | Cost | Effect |
|---|---:|---|
| Potion | 25 | stronger hint |
| Map Scroll | 30 | break problem into subproblems |
| Syntax Scroll | 35 | unrelated generic syntax |
| Boss Scout | 60 | non-code boss hint |
| Shield Repair Kit | 80 | repair charge after recovery work |
| Streak Ward | 120 | protect one missed day |
| Ember Crown | 250 | cosmetic title after two boss clears |

## Bosses

A boss requires working behaviour plus a short explanation/reasoning interview. Assistance and Clean Clear status must be recorded honestly.

## Ranks

- F Apprentice — start
- E Journeyman — clear 2 projects + master 3 fundamentals
- D Pathfinder — clear 4 projects + 4 shields + 5-day best streak
- C Builder — clear 6 projects + reliable program design
- B Python Adventurer — clear foundation campaign + mixed fundamentals gauntlet

## PYR forms

Tiny Code-Flame → Ember Sprite → Runic Familiar → Forge Wisp → Pyre Guardian

## Rival Mode

Compete on evidence-backed stats: lifetime XP, bosses, shields, streaks, interviews, clean clears and project completion. Cosmetic loot does not inflate rival power.

## Canon

`main/progress.json` = canonical player state.

`CANON_LEDGER.md` = custom reward/mechanic history.

Do not silently mutate progression rules.
