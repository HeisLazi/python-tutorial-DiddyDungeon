# Quest 01 — Blackjack

## Mission

Build a complete terminal Blackjack game **yourself** using the Python fundamentals you already know.

This quest is not about learning fancy Python. It is about making your existing knowledge stop feeling foggy:

- variables
- input/output
- `if / elif / else`
- `for` / `while`
- functions
- lists
- dictionaries where useful
- strings
- `random`

**Do not search for a finished Blackjack implementation. Do not ask PYR to write the game.**

---

# Tonight's win condition

A successful first session does **not** require the entire finished game.

Your minimum victory tonight is:

1. create a deck representation;
2. deal two cards to the player and dealer;
3. display the player's cards and only one dealer card;
4. calculate a normal hand total;
5. get a basic `hit` / `stand` loop working.

If you reach that point and can explain the logic, the session counts as a win.

---

# Quest map

## Mob 0 — The Empty Table

**Goal:** get the program running and print a tiny Blackjack welcome screen.

No game logic yet. Just prove your file runs and you know where you're starting.

**Clear condition:** you can run `python blackjack.py` without errors.

---

## Mob 1 — The Dealer's Hand

**Goal:** represent the available card values and randomly deal cards into separate player/dealer hands.

Think about:

- What Python structure makes sense for a hand?
- What should a function that deals one card *return*?
- Do you actually need suits for this version?

**Clear condition:** every run can produce two player cards and two dealer cards.

**Reward:** +25 XP

---

## Mob 2 — The Count Keeper

**Goal:** calculate the value of a hand.

Start simple. Ignore clever Ace handling at first.

Think about:

- Does the total belong in a variable or should a function calculate it when needed?
- Can the same function work for both the player and dealer?

**Clear condition:** both hands can display a correct basic total.

**Reward:** +25 XP

---

## Mob 3 — The Hitman

**Goal:** let the player repeatedly choose `hit` or `stand`.

Think about:

- What keeps a player's turn running?
- What event ends that loop?
- What should happen immediately after drawing another card?
- How will you stop invalid input from breaking the flow?

**Clear condition:** the player can draw multiple cards or choose to stop.

**Reward:** +25 XP

---

## Mob 4 — The Bust Hound

**Goal:** detect when a hand goes above 21 and end the appropriate turn.

Do not overcomplicate it.

**Clear condition:** a player who exceeds 21 loses the round instead of continuing to draw.

**Reward:** +25 XP

---

## Mob 5 — The House Clerk

**Goal:** automate the dealer's turn with one simple rule:

> Dealer keeps drawing while the dealer total is below 17.

Think about how similar this is to the player's repeated-turn logic.

**Clear condition:** once the player stands, the dealer finishes its own turn automatically.

**Reward:** +25 XP

---

## Mob 6 — The Judge

**Goal:** compare the final player/dealer totals and declare the correct outcome.

Your game needs to distinguish at least:

- player bust;
- dealer bust;
- player higher;
- dealer higher;
- draw.

**Clear condition:** normal rounds consistently announce the correct result.

**Reward:** +25 XP

---

## Mob 7 — The Rematch Shade

**Goal:** allow another round without restarting Python manually.

Think about:

- Which variables need to reset each round?
- Which loop should control the whole game versus one player's turn?

**Clear condition:** you can finish one round and choose to play another cleanly.

**Reward:** +25 XP

---

# Boss — The House

The House introduces **Aces**.

Treat an Ace as 11 normally, but if the hand would bust and changing an Ace from 11 to 1 saves the hand, the game should do so.

PYR must not hand you the algorithm immediately.

Before the boss counts as defeated, explain to PYR in your own words:

1. how a hand is represented;
2. how cards are dealt;
3. how hand totals are calculated;
4. what controls the player's loop;
5. what controls the dealer's loop;
6. how bust detection works;
7. how the winner is selected;
8. how your Ace logic works.

**Boss reward:** +100 XP, bonus coins, and a clean-clear item if no exact solution code was used.

---

# Optional loot — only after the boss

Do not touch these until the core game works.

- chips and betting;
- win/loss tracking;
- Blackjack payout bonus;
- face-card labels (`J`, `Q`, `K`);
- ASCII cards;
- player name;
- session statistics;
- difficulty variants;
- better input validation.

The purpose of optional loot is to keep coding fun after the fundamentals are already working.

---

# PYR rules for this branch

PYR must follow `TUTOR_CONTRACT.md`.

When you are stuck, PYR uses this order:

1. ask a question;
2. point at the relevant concept;
3. give pseudocode;
4. show generic syntax unrelated to the exact Blackjack solution;
5. only show exact solution code if you explicitly abandon that challenge.

If you paste an error, PYR should first help you interpret the error rather than immediately rewriting your code.

If your code works, PYR should occasionally ask **why** it works before awarding the mob clear.

---

# Recommended session rhythm

Work one mob at a time.

After each clear:

```bash
git add .
git commit -m "clear mob 1 dealer hand"
```

You do not have to use that exact commit message. The important part is making small checkpoints so you can see the project grow.

If you get mentally cooked, stop after a mob. A 60–90 minute session where you actually understood what you wrote is better than four hours of copied code.

---

# Start command

From the repository:

```bash
git fetch --all
git switch 01-blackjack
python blackjack.py
```

Then open `SESSION_NOTES.md`, summon PYR with the prompt in that file, and start with **Mob 0 — The Empty Table**.
