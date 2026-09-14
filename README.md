# Python Quest Lab

A terminal-first Python training campaign where I build small games myself while **PYR**, a Socratic AI companion, helps without writing the project for me.

The point is not to speedrun eight repos. The point is to make Python fundamentals feel automatic enough that I can move into larger systems with real understanding.

<p align="center">
  <img alt="Level" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.player.level&label=Level&color=blue" />
  <img alt="Lifetime XP" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.player.lifetime_xp&label=Lifetime%20XP&color=orange" />
  <img alt="Streak" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.streak.current&label=Day%20Streak&color=red" />
  <img alt="Bosses" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.bosses_defeated&label=Bosses&color=purple" />
  <img alt="Mastery Shields" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.mastery_shields_earned&label=Mastery%20Shields&color=brightgreen" />
</p>

## Public character sheet

<!-- PUBLIC_STATS_START -->

| Stat | Current |
|---|---|
| Character | **Lazi — Apprentice Coder** |
| Rank | **F — Apprentice** |
| Level | **1** |
| XP | **0 / 100** — 0 lifetime XP |
| HP | **100 / 100** |
| Coins | **0** |
| Coding streak | **0 days** — best: 0 |
| Mastery Shields | **0** |
| Bosses defeated | **0 / 8** |
| Mobs defeated | **0** |
| Concept interviews | **0 passed / 0 failed** |
| Clean clears | **0** |
| Companion | **PYR — Tiny Code-Flame, Lv. 1** |
| Current quest | **Blackjack — enter The Empty Table and get the first terminal output running.** |

**Equipped:** Training Blade · Apprentice Coat · no trinket yet

**Next major goals:** first mob → first concept interview → first Mastery Shield → defeat **The House** → evolve PYR into an **Ember Sprite**.

<!-- PUBLIC_STATS_END -->

`progress.json` is the canonical campaign state. PYR updates this public block whenever displayed stats change, while the badges above read directly from the live JSON.

## How the RPG works

Real coding progress becomes game progress. Features, self-debugging, code explanations, mobs and bosses earn XP and coins. Coins buy hint tools and cosmetics — never finished solutions.

The deeper systems live in [`GAME_SYSTEM.md`](./GAME_SYSTEM.md), including:

- **daily / weekly / long-term quests**;
- **coding streaks** based on meaningful work, not just opening the repo;
- **Mastery Shields** for concepts I can genuinely use and explain;
- Bronze → Silver → Gold shield progression;
- failed later mastery checks cracking shields instead of deleting my streak;
- HP, inventory, equipment, achievements and boss trophies;
- a coin shop with Potions, Map Scrolls, Syntax Scrolls, Streak Wards and more;
- PYR evolutions tied to actual learning milestones;
- **Rival Mode** so friends can fork the campaign and compare verified progress.

## Mastery Shields

A concept is not considered mastered because I used it once.

To earn a shield I need to **use the concept in real code and pass an AI interview about it**. Later interviews can test whether the knowledge stuck. If I fail one after earning a shield, a shield charge cracks before HP is touched. The streak is never punished for getting an answer wrong.

Current foundation concepts:

| RPG Skill | Python concept | Shield |
|---|---|---|
| Ember | Conditionals | None yet |
| Chain Flame | Loops | None yet |
| Firebolt | Functions | None yet |
| Inventory Sight | Lists | None yet |
| Runic Memory | Dictionaries | None yet |
| Inferno | Combining systems | Locked |
| Tactician | Program design | Locked |

## Campaign tree

Every project lives on its own branch and has a `HANDOFF.md` containing mobs, requirements, optional loot and a final boss.

| Order | Branch | Project | Focus | Boss |
|---|---|---|---|---|
| 0 | `00-rps-tournament` | Rock Paper Scissors Tournament | loops, conditionals, score state | The Pattern Warden |
| 1 | `01-blackjack` | **Blackjack — ACTIVE** | lists, functions, game state | **The House** |
| 2 | `02-detective-game` | Guess Who / Detective Game | dictionaries, filtering, branching | The False Alibi |
| 3 | `03-pokemon-battle` | Creature Battle Simulator | nested lists/dictionaries, turn logic | The Arena Champion |
| 4 | `04-casino-slots` | Casino / Slots | random, probability, economy state | Lady Luck |
| 5 | `05-dungeon-crawler` | Dungeon Crawler + RPG Shop | inventory, encounters, connected systems | The Dungeon Core |
| 6 | `06-gladiator-arena` | Turn-based Gladiator Game | combat systems, reusable functions | The Unbound |
| 7 | `07-football-manager` | Mini Football Manager | larger datasets and simulation | The Invincibles |

## Current training scope

For now I am deliberately sharpening:

`variables` · `input/output` · `if/elif/else` · `for/while` · `functions` · `lists` · `dictionaries` · `strings` · `random`

Files/JSON, exceptions, modules, testing, classes/OOP and APIs come after the foundation feels natural.

## Enter the current quest

```bash
git fetch --all
git switch 01-blackjack
```

Then read `HANDOFF.md`, open `blackjack.py`, and start from the smallest working version.

## PYR — the AI companion

Any AI helping on this repo must follow [`TUTOR_CONTRACT.md`](./TUTOR_CONTRACT.md).

PYR's hint ladder is:

1. ask a useful question;
2. identify the concept;
3. offer pseudocode;
4. show unrelated generic syntax;
5. only reveal exact solution code if I explicitly abandon that challenge.

**PYR helps me think. PYR does not build the project for me.**

## Rival Mode

The system is built so a friend can fork it, reset the campaign and compete using the same rules. `rivals.json` will hold public `progress.json` URLs and the dashboard can compare things such as lifetime XP, boss clears, shields, streaks and clean clears.

The goal is friendly competition around **learning evidence**, not who can generate the most code.

## Interactive dashboard

The richer character screen is [`index.html`](./index.html). It reads `progress.json` and shows the quest tree, stats, shields, goals, shop, achievements and companion progression. Deploying `main` as a static site turns it into the live campaign dashboard.

---

**Rule:** Google syntax. Do not Google finished project solutions.
