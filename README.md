# Python Quest Lab

A terminal-first Python training repo built to sharpen fundamentals through small games instead of tutorials.

The rule is simple: **build the project yourself, use AI as a Socratic tutor, and only move on when you can explain your own code.**

## Current training scope

Stay mostly inside the fundamentals until they feel automatic:

- variables and input/output
- `if / elif / else`
- `for` and `while` loops
- functions
- lists
- dictionaries
- strings
- `random`

Do **not** rush into classes, APIs, databases, frameworks, or agent-written code. Those come later.

## The campaign

Each project lives on its own branch. Switch to a branch, read its `HANDOFF.md`, then build the project there.

| Order | Branch | Project | Main skill focus | Suggested time |
|---|---|---|---|---|
| 0 | `00-rps-tournament` | Rock Paper Scissors Tournament | loops, conditionals, score state | 1 evening |
| 1 | `01-blackjack` | Blackjack | lists, functions, game state | 1–2 days |
| 2 | `02-detective-game` | Guess Who / Detective Game | dictionaries, filtering, branching | 1–2 days |
| 3 | `03-pokemon-battle` | Pokémon-style Battle Simulator | nested lists/dictionaries, turn logic | 2–3 days |
| 4 | `04-casino-slots` | Casino / Slots | random, probability thinking, economy state | 1–2 days |
| 5 | `05-dungeon-crawler` | Dungeon Crawler + RPG Shop | inventory, encounters, shops, connected systems | 2–3 days |
| 6 | `06-gladiator-arena` | Turn-based Gladiator Game | combat systems, reusable functions, state | 2–3 days |
| 7 | `07-football-manager` | Mini Football Manager | larger datasets, simulation, interacting systems | 3+ days |

The order is a recommendation, not a prison. If one sounds fun tonight, play that branch.

---

# The meta-RPG

Your coding progress is also a text RPG.

You begin as:

```text
LAZI — APPRENTICE CODER
Level: 1
XP: 0 / 100
HP: 100 / 100
Coins: 0
Potions: 2

Companion: PYR
A tiny code-flame that grows as you learn.
```

**PYR** is the AI tutor. PYR is not allowed to build the game for you. Its job is to question, hint, explain, challenge and track your progress while staying in character.

### Progression

- Small feature completed: **+10 XP**
- Major milestone / mob defeated: **+25 XP**
- Boss defeated: **+100 XP**
- Explain your own code correctly: **+10 XP**
- Find and fix a bug yourself: **+15 XP**
- Complete a project without solution code from AI: **bonus loot**

Every 100 XP = level up. The tutor can award coins and items narratively as you work.

### Items

- **Potion** — one stronger hint without losing boss rewards.
- **Map Scroll** — tutor breaks the current problem into smaller subproblems.
- **Syntax Scroll** — tutor may show generic Python syntax unrelated to the exact solution.
- **Phoenix Feather** — tutor may show one tiny unrelated example when you are completely stuck.
- **Boss Key** — earned by completing all required project milestones; unlocks the final challenge.

### Skill unlocks

Your character and PYR gain abilities when concepts become reliable:

- **Ember** — basic conditionals
- **Firebolt** — functions
- **Chain Flame** — loops
- **Inventory Sight** — lists
- **Runic Memory** — dictionaries
- **Inferno** — combining multiple systems cleanly
- **Tactician** — designing a larger program before coding it

The names are just flavour. The real unlock is being able to use the concept without needing the answer shown to you.

---

# AI tutor contract

When using ChatGPT, Claude, Gemini, Codex, or another AI on these branches, tell it to read the branch `HANDOFF.md` first.

The tutor must use a **Socratic hint ladder**:

1. Ask a question that helps you notice the problem.
2. Point to the Python concept involved.
3. Give pseudocode, not Python.
4. Show generic syntax only if needed.
5. Show solution code only if you explicitly abandon the challenge after multiple attempts.

The tutor should ask you to explain important code back in your own words before marking a boss as defeated.

**Never paste the project into an AI and ask it to finish it.** This repo exists specifically so you can become the person who understands the implementation.

---

# How to play

```bash
git fetch --all
git branch -a
git switch 01-blackjack
```

Then:

1. Read `HANDOFF.md`.
2. Create your Python file(s).
3. Build the smallest working version first.
4. Run it constantly.
5. Commit after meaningful milestones.
6. Ask the tutor for hints, not implementations.
7. Beat the branch boss.
8. Move to the next project when you can explain what you built.

## Ground rule

**Google syntax. Do not Google project solutions.**

Good search: `python random item from list`

Bad search: `blackjack game python source code`

---

## Why this repo exists

The goal is not to collect eight finished games. The goal is to make loops, functions, lists, dictionaries, branching and program state feel natural enough that the next layer of Python — files/JSON, exceptions, modules, classes and larger applications — has a solid foundation underneath it.

Have fun. Break things. Fix them. Make PYR earn its upgrades too.
