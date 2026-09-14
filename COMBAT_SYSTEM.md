# Quest Lab Combat System

**Status:** CANON foundation, implementation rolling out in slices.

Combat exists to make real learning progress feel like an RPG battle. It does not replace correctness, project requirements, interviews, or mastery evidence.

## Core loop

```text
Learn / build / debug safely
        ↓
Choose to submit a Battle action
        ↓
PYR verifies the submitted checkpoint
        ↓
Correct / complete      Incorrect / incomplete
        ↓                         ↓
Deal Impact             Enemy counterattacks
        ↓                         ↓
Reduce Resolve          Armor reduces HP loss
```

Normal coding is safe. Combat only happens when the player deliberately submits an answer/checkpoint as a Battle action.

---

## Safe mode

These never deal HP damage:

- Teach;
- Practice;
- Quick Refresher;
- ordinary Forge coding;
- syntax errors;
- runtime errors;
- debugging attempts;
- asking for help;
- needing reteaching.

The player should be able to experiment aggressively without being punished for learning.

---

## Battle mode

Battle mode is used for deliberate submissions such as:

- Test Me;
- mob questions;
- concept interviews;
- submitted code checkpoints;
- boss phases;
- optional challenge encounters;
- future weekly raid objectives.

Entering Battle mode must be visible. A failure cannot silently damage the player.

---

# Offense: Impact

Quest Lab has **no weapon damage stat**.

The player deals **Impact** by completing verified learning/project objectives.

Impact is objective-based, not line-count based and not commit-count based.

Typical values:

| Verified action | Suggested Impact |
|---|---:|
| small prediction / concept check | 1 |
| clear explanation / bug diagnosis | 2 |
| independent code checkpoint | 3–4 |
| difficult cold interview answer | 3 |
| major project objective | 4–8 |
| boss/raid milestone | predefined phase value |

The exact Impact available should be shown **before** a Battle submission when practical.

Impact only applies after PYR verifies the evidence. A trinket may add bounded combat-only bonus Impact, but it cannot make incorrect work count as correct.

---

# Enemy health: Resolve

Enemies use **Resolve** rather than HP.

Resolve represents how much verified work/understanding remains before the encounter is defeated.

Example:

```text
THE COUNT KEEPER
Resolve 9 / 9

Trace the hand total       2 Impact
Implement total logic      4 Impact
Explain the loop           3 Impact
```

Completing all three verified objectives removes all 9 Resolve.

Reducing Resolve to zero does not bypass any required project functionality or final interview.

---

# Defense: Armor

Armor is the only normal defensive equipment slot.

Armor reduces HP damage from an **incorrect submitted Battle action** by a percentage.

Suggested progression:

| Tier | Damage reduction |
|---|---:|
| Starter | 10% |
| Uncommon | 20% |
| Rare | 30% |
| Epic | 40% |
| Elite | 50% |
| Legendary | 60% |

Damage uses:

```text
damage_taken = ceil(raw_damage × (1 - armor_reduction))
```

Example:

```text
Enemy counterattack       20 HP
Elite armor               -50%
Final damage              10 HP
```

Armor never changes whether an answer is correct.

The starter **Apprentice Coat** is a Starter armor piece with **10% reduction**.

---

# Trinkets

Trinkets are the special-effect slot.

A trinket can visually be almost anything — charm, ring, mask, scythe, sword, staff, relic, book, mechanical device — but it is mechanically a **trinket**, not a weapon stat slot.

This lets Quest Lab have dramatic equipment without needing a traditional attack-stat system.

Examples for future loot:

### Ember Scythe

A weapon-shaped trinket.

Proposed effect: first verified Battle objective of an encounter deals +1 **bonus Impact**.

### Phoenix Ember

Proposed effect: once per day, when the player would become Downed, revive at 1 HP.

### Seer's Lens

Proposed effect: reveal the concept category of one hidden encounter.

### Guardian Sigil

Proposed effect: negate one boss/raid counterattack per project or raid.

### Bond of Embers

Future multiplayer trinket.

Proposed effect: once per weekly raid, revive one downed teammate.

Combat bonus Impact from trinkets must be tracked separately from evidence-backed Learning Power when competitive comparisons matter.

---

# Counterattacks and HP

Enemies only counterattack after an incorrect/incomplete **submitted Battle action**.

Suggested raw damage by threat:

| Threat | Raw damage |
|---|---:|
| I | 5–8 |
| II | 10–14 |
| III | 15–20 |
| IV | 20–28 |
| Boss | explicitly shown per phase |
| Weekly Raid | explicitly shown per mechanic |

Before a risky submission, the interface should show the raw hit and estimated post-armor damage whenever the encounter rules allow it.

Repeated wrong guesses should not create an HP death spiral. PYR should move the player back toward Teach/Practice when it detects that understanding is missing.

---

# Downed state

0 HP means **Downed**, not locked out of Quest Lab.

A downed player can still return to learning.

Recovery options may include:

- leave Battle mode and return to Teach;
- complete a recovery challenge;
- use a revive trinket/item;
- future party revive during raids.

Being revived never erases a failed interview or manufactures mastery evidence.

Exact HP recovery pacing remains open for tuning.

---

# Weekly raid foundation

Weekly bosses are shared software projects represented as raid encounters.

A raid has a large Resolve pool split across predefined objectives.

Example:

```text
THE NULL WYRM
Party Resolve: 120

Core Python system        25 Impact
Validation / edge cases   20 Impact
Tests / debugging         20 Impact
UI / presentation         20 Impact
Integration               20 Impact
Party review              15 Impact
```

Each objective awards its Impact once after verification.

Raid Impact must not be based on:

- raw commit count;
- lines of code;
- file count;
- time spent;
- meaningless task splitting.

A difficult 20-line integration task may be worth more Impact than hundreds of lines of low-risk code.

## Raid contribution

The UI may show individual verified contribution for fun, but the primary result is the **party clear**.

Where trinkets add combat-only bonus Impact, the raid should distinguish:

```text
Verified Impact   = objective contribution
Bonus Impact      = trinket / encounter modifier
```

Competitive learning comparisons should use evidence-backed contribution, not bonus Impact.

## Raid mechanics can teach collaboration

Boss mechanics may encode real engineering practices.

Examples:

- **Memory Leech** — an objective grants no Impact until another party member reviews it;
- **Spaghetti King** — refactor objectives carry major Resolve value;
- **Race Condition** — players work on branches and the final phase requires successful integration;
- **Null Wyrm** — validation/edge-case objectives are mandatory before the final phase.

This lets the game teach code review, Git collaboration, testing, integration, debugging and architecture through encounter design.

---

# Fairness boundary

Combat and gear may change presentation, survivability and combat pacing.

They must never:

- mark incorrect code as correct;
- skip required project features;
- skip an interview;
- create Mastery Shield evidence;
- fabricate a Clean Clear;
- erase Reference Mode history;
- alter Git Dev Activity;
- make cosmetic rarity count as learning mastery.

Quest Lab is still a learning system first. Combat wraps evidence; it does not replace evidence.

---

# Implementation slices

## Slice 1 — Battle shell

- Character page shows armor reduction and trinket effect;
- Quest page shows current encounter Resolve / Impact doctrine;
- Safe vs Battle state is visible;
- no automatic verdicts yet.

## Slice 2 — Controlled PYR adjudication

- Submit Run produces an explicit pending Battle submission;
- PYR receives active file, run output, quest state and requirements;
- PYR can return verified success / needs-work verdict;
- only this controlled verdict may alter Resolve/HP;
- project source remains read-only to PYR; examples go to `tutor.py`.

## Slice 3 — Stateful combat

- persistent Resolve;
- armor calculation;
- HP / Downed flow;
- combat log;
- trinket triggers;
- encounter clear animation.

## Slice 4 — bosses

- multi-phase project bosses;
- boss-specific mechanics;
- final interview phase;
- boss trophies / loot.

## Slice 5 — weekly raids

- party identity;
- shared raid state;
- task claims;
- verified objective contribution;
- raid mechanics;
- party clear + loot;
- friend/rival profile integration.
