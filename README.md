# Python Quest Lab

A terminal-first Python training campaign built around small games, an RPG progression layer, and a Socratic AI tutor named **PYR**.

> GitHub README files cannot run JavaScript, so the actual interactive campaign home is [`index.html`](./index.html). Deploy the `main` branch as a static site on Vercel/GitHub Pages and that becomes the live dashboard. The AI tutor updates [`progress.json`](./progress.json); the dashboard reads that state automatically.

## Start here

Read [`START_HERE.md`](./START_HERE.md) before your first session.

Any AI helping with the projects must read [`TUTOR_CONTRACT.md`](./TUTOR_CONTRACT.md). The core rule is simple:

**PYR helps you think. PYR does not build the project for you.**

## Campaign structure

Every project has its own branch and its own `HANDOFF.md`.

| Order | Branch | Project | Main focus |
|---|---|---|---|
| 0 | `00-rps-tournament` | Rock Paper Scissors Tournament | loops, conditionals, score state |
| 1 | `01-blackjack` | Blackjack | lists, functions, game state |
| 2 | `02-detective-game` | Guess Who / Detective Game | dictionaries, filtering, branching |
| 3 | `03-pokemon-battle` | Creature Battle Simulator | nested lists/dictionaries, turn logic |
| 4 | `04-casino-slots` | Casino / Slots | random, probability thinking, economy state |
| 5 | `05-dungeon-crawler` | Dungeon Crawler + RPG Shop | inventory, encounters, shops, connected systems |
| 6 | `06-gladiator-arena` | Turn-based Gladiator Game | combat systems, reusable functions, state |
| 7 | `07-football-manager` | Mini Football Manager | larger datasets, simulation, interacting systems |

The order is recommended, not mandatory. Pick what sounds fun enough that you actually sit down and code it.

## How to enter a quest

```bash
git fetch --all
git switch 01-blackjack
```

Then read that branch's `HANDOFF.md` and start from an empty Python file.

## Current training scope

The campaign deliberately stays around:

- variables and terminal input/output
- conditionals
- `for` / `while` loops
- functions
- lists
- dictionaries
- strings
- `random`

The goal is to make these automatic before moving into files/JSON, exceptions, modules, testing, classes/OOP and APIs.

## The RPG layer

You start as **Lazi — Apprentice Coder** with PYR as a tiny code-flame companion. Real coding milestones award XP, coins, items and skill unlocks. Bosses only count as defeated when the project works **and** you can explain the important logic yourself.

The live campaign state is stored in [`progress.json`](./progress.json), not hardcoded into the dashboard.

## AI tutor workflow

From the dashboard, select a project and press **Copy PYR session prompt**. Paste that into ChatGPT, Claude, Gemini or another repo-aware assistant.

The tutor should:

1. read `TUTOR_CONTRACT.md`;
2. read `progress.json`;
3. read the current branch `HANDOFF.md`;
4. use questions → concept hint → pseudocode → generic syntax before exact code;
5. update `progress.json` only when genuine progress happened.

## Ground rule

**Google syntax. Do not Google finished project solutions.**

Good: `python random item from list`

Bad: `blackjack game python full code`

The win condition is not eight pretty repositories. It is being able to sit down, write the code, debug it and explain what it does.
