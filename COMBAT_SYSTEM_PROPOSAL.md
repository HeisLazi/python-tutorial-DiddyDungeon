# Quest Lab Combat System — PROVISIONAL Design

This file is a design proposal only. Nothing here changes XP, HP, gear power, mastery, streaks, rivals, or rewards until it is explicitly approved and added to the Canon Ledger.

## Design goal

Combat should make learning feel alive without turning normal mistakes into punishment or letting gear replace understanding.

The player should always know:

- how much damage an enemy can deal;
- how much damage their current successful action can deal;
- what their weapon, armor and trinket are doing;
- why damage happened;
- what is required to actually clear the learning objective.

No hidden damage formulas.

---

# Two learning states

## Safe learning state

Used during:

- Teach;
- Practice;
- Quick Refresher;
- normal debugging;
- ordinary Forge implementation.

Normal mistakes, syntax errors, runtime errors, asking for help and needing reteaching cause **zero HP damage**.

## Battle state

Entered intentionally during:

- Test Me;
- concept interviews;
- mob challenges;
- boss phases;
- optional challenge encounters.

Only Battle state can deal combat damage.

This keeps the game meaningful without making learning anxiety-driven.

---

# Encounter information

Before a battle starts, the HUD should show something like:

```text
THE COUNT KEEPER
Threat: II
Enemy Resolve: 6
Enemy Attack: 4

Lazi
HP: 82 / 100
Weapon: Training Blade   +1 on successful attacks
Armor: Apprentice Coat   Guard 1
Trinket: None

Current action
Explain the list traversal correctly
Potential damage: 2 + weapon bonus
Failure damage: 4 - armor guard
```

Damage should be deterministic unless an item explicitly states that it contains randomness.

---

# Enemy health: Resolve

Enemies use **Resolve** instead of ordinary HP.

Resolve represents how much understanding/work is still needed to defeat the encounter.

Suggested starting values:

| Encounter | Resolve |
|---|---:|
| tiny diagnostic mob | 2–3 |
| normal mob | 4–6 |
| hard mob | 7–9 |
| project boss phase | 8–12 |
| full late-game boss | multiple phases |

A mob reaching 0 Resolve does not automatically grant mastery. Required Forge work/interviews still have to be completed.

---

# Player attacks

Successful learning actions deal damage.

Suggested base values:

| Successful action | Base damage |
|---|---:|
| prediction / small concept answer | 1 |
| clear explanation / bug diagnosis | 2 |
| independent code checkpoint | 3 |
| difficult cold interview answer | 3 |
| major Forge milestone | phase clear rather than raw damage |

Weapons can modify successful attacks, but **a weapon can never turn an incorrect answer into a correct one**.

Example:

```text
Correct explanation     2
Training Blade bonus   +1
--------------------------
Damage dealt            3
```

---

# Enemy attacks and player damage

An enemy can attack after a failed Battle-state action.

Suggested base attack ranges:

| Threat | Damage |
|---|---:|
| I | 2–3 |
| II | 4 |
| III | 5–6 |
| IV | 7–8 |
| Boss | clearly shown per phase |

Normal coding bugs are not enemy attacks.

A failed Test Me / interview response can trigger one enemy turn, but repeated guessing should not create a death spiral. The tutor should switch back toward teaching when the player clearly needs explanation.

---

# Gear roles

## Weapons

Weapons increase **damage after successful learning actions**.

Examples:

- Training Blade: +1 damage on a successful attack;
- Debugger's Knife: +1 extra damage when the player correctly diagnoses a bug;
- Runic Staff: bonus only during concept/explanation encounters.

Weapons never lower the evidence needed for a clear.

## Armor

Armor reduces incoming Battle-state damage.

Examples:

- Apprentice Coat: reduce the first incoming hit in an encounter by 1;
- Iron Mantle: flat Guard 1;
- Scholar Plate: larger reduction during interview encounters, but no help during Forge coding.

Armor never changes whether an answer counts as correct.

## Trinkets

Trinkets are the weird/special slot.

Possible future effects:

- one daily revive at 1 HP;
- reveal the concept category of one hidden encounter;
- preserve a combo after one failed attack;
- add an extra Tutor Notebook hint token;
- convert one boss hit into Guard once per project;
- late-game XP effects only if they do not corrupt competitive Learning Power.

### XP-boost warning

A straight official-XP multiplier would make rival comparisons unfair. If XP-boost trinkets are ever added, either:

1. boosted XP must be tracked separately from evidence-backed Learning Power; or
2. rival scoring must ignore the boosted portion.

Do not activate XP multipliers until that separation exists.

---

# Downed / revive state

Reaching 0 HP should never lock the player out of learning.

Proposed behaviour:

```text
HP reaches 0
→ character becomes Downed
→ current battle pauses
→ choose Recovery / Teach / item revive
```

Possible recovery paths:

- complete a small recovery explanation;
- use a revive trinket/item;
- leave Battle state and return to Teach mode;
- recover naturally before the next encounter.

A revive does not erase a failed interview or manufacture mastery evidence.

---

# Combo / critical system

Potential late addition:

- consecutive successful Battle actions build Combo;
- Combo may increase visual attack intensity or add small capped damage;
- a mistake resets Combo but does not damage the learning streak;
- critical hits should come from demonstrated reasoning, not random luck.

Example:

```text
3 correct reasoning actions in a row
→ Focused Strike
→ +1 combat damage
```

This rewards consistency without replacing correctness.

---

# Visibility rules

The player should see the math before committing an action.

Every encounter card should expose:

```text
Enemy Resolve
Enemy attack damage
Your weapon bonus
Your armor guard
Your trinket effect
Current action damage
Failure damage
```

The combat log should explain each result:

```text
Correct bug diagnosis      +2 attack
Training Blade             +1
The Bust Hound loses        3 Resolve

Failed cold prediction
Enemy attack                4
Apprentice Coat            -1
Lazi loses                  3 HP
```

---

# Fairness boundary

Gear can change the **RPG combat presentation and survivability**.

Gear must never:

- mark incorrect code correct;
- skip required project functionality;
- skip a boss interview;
- create Mastery Shield evidence;
- change Git Dev Activity;
- fabricate a Clean Clear;
- hide Reference Mode assistance.

Combat is a layer around learning evidence, not a replacement for it.

---

# Recommended implementation order

1. Battle HUD with visible Resolve / attack / Guard values.
2. Test Me encounter that can deal HP damage.
3. Weapon and armor effects with no XP multipliers.
4. Combat log.
5. Downed / recovery flow.
6. Trinket utility effects.
7. Multi-phase bosses.
8. Only then evaluate revive items and separated adventure-XP bonuses.
