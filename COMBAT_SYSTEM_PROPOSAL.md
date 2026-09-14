# Quest Lab Combat System — PROVISIONAL Design v2

This file is a design proposal only. Nothing here changes XP, HP, gear power, mastery, streaks, rivals, rewards, or weekly raids until it is explicitly approved and added to the Canon Ledger.

## Design goal

Combat should make learning feel alive without turning Quest Lab into a damage-calculation simulator.

The simplified direction is:

- **no weapon slot**;
- **armor = percentage damage reduction**;
- **trinket = special utility/effect slot**;
- **offense comes from verified project progress**, not equipped attack stats;
- normal coding mistakes remain safe;
- battle damage only happens when the player knowingly submits an answer/checkpoint during an encounter;
- future weekly bosses can use shared project progress as a party attack against one boss.

The point is to make building software feel like fighting the enemy, not to bolt a separate RPG combat game on top of coding.

---

# 1. Safe learning vs encounter submissions

## Safe learning state

Used during:

- Teach;
- Practice;
- Quick Refresher;
- normal debugging;
- ordinary Forge implementation;
- experimenting in `tutor.py`;
- syntax/runtime errors before the player chooses to submit.

These cause **zero HP damage**.

## Encounter state

Used during:

- Test Me;
- concept interviews;
- mob checkpoints;
- boss checkpoints;
- future weekly raid objectives;
- optional challenge encounters.

Damage is only considered when the player deliberately presses something equivalent to:

```text
Submit Answer
Submit Run
Submit Checkpoint
```

and PYR judges that submitted encounter answer/checkpoint as wrong or failed.

This makes the risk explicit. Merely trying code never hurts the character.

---

# 2. Armor: simple percentage protection

Armor has one mechanical value:

```text
Damage Reduction %
```

No defense stat, no armor points, no hidden formula.

Suggested tiers:

| Tier | Example reduction |
|---|---:|
| starter / worn | 10% |
| uncommon | 20% |
| rare | 30% |
| epic | 40% |
| elite | 50% |
| legendary ceiling | 60% |

The proposed normal cap is **60%** so even the strongest armor cannot remove all consequence from a failed battle submission.

Formula:

```text
raw encounter damage × (1 - armor reduction) = HP damage taken
```

Round to the nearest whole HP, with a minimum of 1 HP if an encounter was meant to deal damage.

Example:

```text
Boss hit                    20 HP
Elite armor reduction       50%
--------------------------------
Damage taken                10 HP
```

The UI should show this before the player submits:

```text
Failure damage: 20
Armor: -50%
You would take: 10 HP
```

Armor never changes whether an answer is correct and never manufactures mastery evidence.

---

# 3. Trinkets: the interesting gear slot

Trinkets stay because they can create memorable RPG effects without needing a large stat system.

Good trinket categories:

### Survival

- revive once per day at 1 HP;
- survive one lethal boss hit at 1 HP;
- reduce one encounter's damage to zero once per project;

### Information

- reveal the concept family of one hidden mob;
- reveal one boss phase category;
- reveal whether the next checkpoint is explanation / debugging / implementation;

### Tutor interaction

- one extra Tutor Notebook hint token;
- one stronger non-Reference-Mode hint;
- preserve one attempt before PYR drops the encounter back into Teach mode;

### Combo / raid utility

- preserve one combo after a failed submission;
- grant a one-time party shield during a weekly boss;
- revive one downed teammate in a raid;

### XP effects — not yet approved

Straight XP multipliers remain dangerous for rival fairness.

If XP trinkets ever exist, boosted XP must be separated from evidence-backed **Learning Power**, or rival scoring must ignore the boosted portion.

Do not implement XP multipliers before that accounting exists.

---

# 4. Offense: Project Impact instead of weapon damage

The player does **not** deal damage by owning a sword or rolling attack numbers.

The player attacks by completing verified learning/project work.

The combat term is **Impact**.

A mob or boss has **Resolve**. Verified work removes Resolve.

Example:

```text
THE COUNT KEEPER
Resolve: 12

Checkpoint: explain why a hand is stored as a list
Reward on success: 2 Impact

Checkpoint: implement hand-total logic independently
Reward on success: 5 Impact

Checkpoint: pass the cold review question
Reward on success: 5 Impact
```

Complete all three successfully:

```text
12 Resolve → 0
Mob defeated
```

This means "attacking" is literally progressing through the real challenge.

---

# 5. Impact values are assigned before the work

To prevent gaming the system, PYR should not decide damage *after* seeing how much code was written.

Every encounter/checkpoint receives an Impact value when it is created.

Suggested starting scale:

| Verified contribution | Suggested Impact |
|---|---:|
| small concept / prediction checkpoint | 1–2 |
| explanation / bug diagnosis | 2–3 |
| independent small feature | 3–5 |
| meaningful project feature | 5–8 |
| integration / difficult milestone | 8–12 |
| boss interview phase | 5–10 |

Impact is earned only when the checkpoint is actually accepted.

Commit count, line count and AI-generated volume do not create Impact.

Reference Mode can still reduce learning rewards exactly as the normal campaign rules require; it should not suddenly become a way to farm boss damage either. Assisted checkpoints can have reduced or zero raid contribution depending on the final raid rules.

---

# 6. Individual mobs

A normal mob is a small set of checkpoints with a total Resolve amount.

Example:

```text
THE BUST HOUND
Resolve: 9
Threat: II
Raw failure hit: 8 HP

[ ] Predict what happens when total > 21       2 Impact
[ ] Implement bust detection independently     4 Impact
[ ] Explain the condition back to PYR           3 Impact
```

When a submitted battle checkpoint is wrong:

```text
Raw hit: 8
Rare armor: -30%
Damage taken: 6 HP
```

PYR should then decide whether the player is still ready for another encounter submission or should return to Teach/Practice.

Repeated wrong guesses should not become an HP-farming death spiral.

---

# 7. Bosses

Project bosses are larger Resolve pools split into phases.

Example:

```text
THE HOUSE
Total Resolve: 40

Phase 1 — Rules of the Table       10
Phase 2 — Dealer Behaviour          10
Phase 3 — Ace Logic                 10
Phase 4 — Final Code Interview      10
```

The code itself remains the battle.

Finishing a required phase removes its assigned Resolve.

A boss reaching 0 Resolve still does not bypass the normal Boss Rule: required software behaviour, interview, assistance audit and Clean Clear eligibility must all be verified.

---

# 8. Weekly co-op bosses / raids

This is the long-term multiplayer direction.

A weekly boss should be a **shared mini-project or engineering challenge** that several players can join.

The boss has a large shared Resolve pool.

Example:

```text
THE NULL WYRM — WEEKLY RAID
Party: 4 players
Resolve: 120
Ends: Sunday

Frontend objective        20 Impact
Core Python feature       25 Impact
Validation / edge cases   20 Impact
Tests / debugging         20 Impact
Integration               20 Impact
Party code review         15 Impact
```

Players do not repeatedly answer trivia to attack it.

They defeat it by actually working on the raid project.

Each objective is assigned an Impact value **before** implementation. Once the contribution is reviewed and accepted, that Impact comes off the shared boss Resolve.

This naturally supports friends with different strengths without requiring RPG classes.

---

# 9. Raid contribution and fairness

Each accepted contribution should create an evidence event, conceptually like:

```json
{
  "player": "Lazi",
  "objective": "input-validation",
  "impact": 12,
  "evidence": "accepted checkpoint / PR / interview",
  "assistance": "clean"
}
```

The shared raid result can show:

```text
Boss Resolve: 120 → 0

Lazi        34 Impact
Friend A    31 Impact
Friend B    28 Impact
Friend C    27 Impact
```

But contribution should not become a toxic damage leaderboard.

The main reward is the **party clear**. Individual Impact exists for transparency, contribution history and optional titles/achievements.

Anti-farming rules:

- no Impact from raw commit count;
- no Impact from line count;
- no repeated trivial task farming;
- one objective cannot be claimed twice;
- objective values are locked before implementation;
- AI assistance level is recorded;
- required review/evidence must pass before Impact is granted.

---

# 10. Boss counterattacks in raids

The boss can fight back without requiring a complicated combat loop.

Possible triggers:

### Failed submitted checkpoint

The player who submitted takes the displayed raw hit after armor mitigation.

### Raid phase mechanic

A boss phase may have a party-wide event such as:

```text
Integration phase failed
Boss pulse: 12 raw damage to every active party member
```

Each player's armor applies individually.

### Time pressure

Missing a weekly phase deadline could trigger a narrative boss action or reduce an optional bonus, but should not erase genuine learning progress.

The raid should never damage players because someone simply made a normal coding mistake before submitting.

---

# 11. Downed and revival

At 0 HP the player becomes **Downed**, not locked out of Quest Lab.

Possible actions:

```text
Recovery challenge
Return to Teach mode
Use revive trinket
Receive a teammate revive in a raid
```

A downed player can continue learning. They simply cannot make another Battle-state submission until recovered/revived.

This gives revive trinkets real value without weapon stats or complex combat maths.

---

# 12. Why this is preferable to weapon damage

This design keeps the RPG loop aligned with coding:

```text
Learn something
→ build something
→ submit a real checkpoint
→ verified success creates Impact
→ boss loses Resolve
```

Instead of:

```text
Learn something
→ answer correctly
→ calculate weapon attack + crit + enemy defense + random roll
```

Armor and trinkets still make the character build matter, while offense stays directly tied to actual programming progress.

---

# 13. Visibility rules

No hidden combat maths.

Before submitting a battle checkpoint, show:

```text
Checkpoint Impact on success
Enemy raw damage on failure
Armor reduction
Actual HP at risk
Trinket effect, if relevant
Boss/mob Resolve remaining
```

After submission, log exactly what happened.

Example:

```text
Checkpoint accepted
Independent bust detection     +4 Impact
The Bust Hound                 9 → 5 Resolve
```

or:

```text
Checkpoint failed
Raw enemy hit                  8
Rare armor                    -30%
Lazi loses                     6 HP
```

---

# 14. Proposed equipment model

Mechanical character equipment becomes:

```text
Armor      — percentage Battle-state damage reduction
Trinket    — special conditional effect
Title      — cosmetic / achievement identity
```

The old weapon slot should be removed from the mechanical design.

Future character cosmetics may still visually show swords, staffs, tools or trophies, but they do not create attack stats.

---

# 15. Recommended implementation order

1. Keep normal learning completely safe.
2. Add explicit Encounter / Submit state.
3. Add displayed raw failure damage.
4. Add percentage-based armor mitigation.
5. Add combat log and Downed state.
6. Add basic trinket hooks, starting with one revive-style and one information-style effect.
7. Add Impact/Resolve to individual mobs and project bosses.
8. Build raid data model and shared Resolve only after single-player Impact is stable.
9. Prototype one manual weekly co-op boss with fixed objectives and preassigned Impact values.
10. Only after that consider party mechanics, special raid trinkets, seasonal bosses and friend leaderboards.

---

# Open decisions before canon

The following still need player approval/testing before implementation:

- exact armor tier percentages;
- whether minimum encounter damage should always be 1 HP;
- whether failed submitted mob answers always deal damage or some encounter types remain non-damaging;
- whether assisted checkpoints can contribute partial raid Impact or zero raid Impact;
- how often HP naturally restores;
- whether weekly boss participation requires a minimum contribution to earn the raid trophy/reward;
- whether individual Impact should affect rewards or remain informational only.
