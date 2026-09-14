# Quest 01 — Blackjack

## Mission

Build a complete terminal Blackjack game **yourself** while PYR teaches any rusty concepts before you implement them.

This quest sharpens:

- variables / input-output;
- `if / elif / else`;
- `for` / `while`;
- functions;
- lists;
- dictionaries where useful;
- strings;
- `random`.

Do not search for a finished Blackjack implementation.

---

# How every mob works

Before a mob asks you to use a concept that feels rusty, PYR runs:

**Teach → Practice → Teach-back → Forge**

During teaching, PYR may show examples with things like football squads, spell inventories, shopping lists, dice or other unrelated data.

Once you prove you understand the concept, you enter **Forge phase** and implement the Blackjack version from scratch without a solution sitting in front of you.

If you remain genuinely stuck, you can explicitly choose **Reference Mode**. PYR may then show the smallest exact Blackjack-specific fragment needed, but that mob's XP/coins become **50%**. A later Recovery Trial can raise it to at most 75% of the original reward.

Normal explanations, pseudocode and unrelated examples cost nothing.

---

# First-session win condition

You do not need to finish the whole game tonight.

A strong first session is:

1. get the file running;
2. understand/review lists + random selection with PYR;
3. pass a tiny Teach-back;
4. enter Forge;
5. create the card/hand representation yourself;
6. deal two cards to player and dealer;
7. if energy remains, start hand totals or hit/stand.

---

# Quest map

## Mob 0 — The Empty Table

**Goal:** run the program and print a tiny Blackjack welcome screen.

**Clear:** `python blackjack.py` runs without errors.

This mob is intentionally tiny. It gets you moving.

---

## Mob 1 — The Dealer's Hand

**Concept gate:** lists + `random` + function return values.

PYR should teach/review these first with non-Blackjack examples if needed. Then the examples close and you Forge the real solution.

**Goal:** represent available card values and randomly deal cards into separate player/dealer hands.

Questions to think about:

- What structure makes sense for a hand?
- What should a function that deals one card return?
- Do you need suits yet?

**Clear:** every run can produce two player cards and two dealer cards.

**Base reward:** +25 XP.

---

## Mob 2 — The Count Keeper

**Concept gate:** functions + list traversal / totals.

**Goal:** calculate the value of a hand. Ignore clever Ace handling at first.

Think about:

- should the total be stored or calculated when needed?
- can the same function work for both hands?

**Clear:** both hands display a correct basic total.

**Base reward:** +25 XP.

---

## Mob 3 — The Hitman

**Concept gate:** loops + input + changing list state.

**Goal:** let the player repeatedly choose `hit` or `stand`.

Think about:

- what keeps the turn running?
- what ends the loop?
- what happens immediately after another card is drawn?
- how do you handle invalid input?

**Clear:** player can draw multiple cards or stop.

**Base reward:** +25 XP.

---

## Mob 4 — The Bust Hound

**Concept gate:** conditionals + reusable total logic.

**Goal:** detect totals over 21 and end the appropriate turn.

**Clear:** a player above 21 loses instead of continuing to draw.

**Base reward:** +25 XP.

---

## Mob 5 — The House Clerk

**Concept gate:** reusing loop logic for a different actor.

**Goal:** dealer keeps drawing while total is below 17.

**Clear:** after player stands, dealer completes its own turn automatically.

**Base reward:** +25 XP.

---

## Mob 6 — The Judge

**Concept gate:** ordered conditionals / edge cases.

**Goal:** correctly distinguish player bust, dealer bust, player higher, dealer higher and draw.

**Clear:** normal rounds consistently announce the right result.

**Base reward:** +25 XP.

---

## Mob 7 — The Rematch Shade

**Concept gate:** nested game state / outer-vs-inner loops.

**Goal:** allow another round without manually restarting Python.

Think about what resets each round and which loop controls the whole game.

**Clear:** finish one round and choose to play another cleanly.

**Base reward:** +25 XP.

---

# Boss — The House

The House introduces **Aces**.

Treat an Ace as 11 normally, but if the hand would bust and changing an Ace from 11 to 1 saves it, your game should do so.

PYR should teach any missing underlying concept with unrelated examples first, then make you design/implement the Blackjack algorithm yourself in Forge phase.

Before the boss is defeated, explain:

1. hand representation;
2. card dealing;
3. hand total calculation;
4. player loop;
5. dealer loop;
6. bust detection;
7. winner selection;
8. Ace handling.

Then pass at least one reasoning/debug/edge-case question.

**Boss base reward:** +100 XP + coins + trophy/loot.

A required-core Reference Mode use removes Clean Clear eligibility, but you can still defeat the boss and keep learning.

---

# Creativity — optional loot after the required logic works

Make the game yours.

Possible directions include chips/betting, session stats, face-card labels, ASCII cards, player names, difficulty variants, win streaks, achievements, funny dealer dialogue, custom rules or something PYR never suggested.

PYR can award:

- Wild Spark +5 XP;
- Embercraft +10 XP;
- Relic Craft +20 XP;
- Mythic Discovery up to +30 XP.

PYR may also reveal a hidden cosmetic/trophy/lore reward after a genuinely memorable addition or learning moment. Any revealed custom reward must be logged in `CANON_LEDGER.md`.

Do not chase bonus features before the relevant core game works.

---

# Session rhythm

Work one mob at a time. Commit meaningful checkpoints.

```bash
git add .
git commit -m "clear mob 1 dealer hand"
```

You do not need that exact message.

A 60–90 minute session where you understand your code is better than four hours of copied implementation.

---

# Start

```bash
git fetch --all
git switch 01-blackjack
python blackjack.py
```

Then open `SESSION_NOTES.md`, summon PYR, and begin. PYR should **teach first when needed, then send you into Forge**.
