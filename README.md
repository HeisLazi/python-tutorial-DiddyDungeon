# Python Quest Lab

A terminal-first Python training campaign where I build small games myself while **PYR**, a Socratic AI companion, teaches concepts, tests understanding, and turns real progress into an RPG character.

The point is not to speedrun eight repos. The point is to make Python fundamentals feel automatic enough that I can move into larger systems with real understanding.

<p align="center">
  <img alt="Level" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.player.level&label=Level&color=blue" />
  <img alt="Lifetime XP" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.player.lifetime_xp&label=Lifetime%20XP&color=orange" />
  <img alt="Streak" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.streak.current&label=Day%20Streak&color=red" />
  <img alt="Bosses" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.bosses_defeated&label=Bosses&color=purple" />
  <img alt="Mastery Shields" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.mastery_shields_earned&label=Mastery%20Shields&color=brightgreen" />
  <img alt="Reference Mode" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.reference_mode_uses&label=Reference%20Mode&color=yellow" />
  <img alt="Discoveries" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.discoveries_unlocked&label=Discoveries&color=blueviolet" />
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
| Reference Mode uses | **0** — Clean Clear still eligible |
| Creativity bonuses | **0** |
| Hidden discoveries revealed | **0** |
| Learning phase | **TEACH** — Lists and random selection |
| Companion | **PYR — Tiny Code-Flame, Lv. 1** |
| Current quest | **Blackjack — learn the next concept, prove understanding, then Forge it from scratch.** |

**Equipped:** Training Blade · Apprentice Coat · no trinket yet

**Next major goals:** first Teach-back → first mob → first concept interview → first Mastery Shield → first hidden discovery → defeat **The House** → evolve PYR into an **Ember Sprite**.

<!-- PUBLIC_STATS_END -->

`progress.json` is the canonical player state. PYR refreshes this public block when displayed stats change, while the badges above read directly from the live JSON.

## The learning loop

PYR is allowed to **teach me properly before I build**.

For a new or rusty concept the flow is:

**Diagnose → Teach → Practice → Teach-back → Forge → Review → Interview → Record**

During **Teach / Practice**, PYR can show code examples, but the examples must use a different context so they teach the concept without becoming a paste-ready solution for the active game.

Once I show that I understand the idea, I enter **Forge phase** and implement the project requirement from scratch.

If I genuinely cannot bridge the gap, I can explicitly enter **Reference Mode** and see the smallest project-specific exact fragment needed. That milestone then earns **50% XP/coins**. A later Recovery Trial can bring it up to at most **75%**, but the assistance stays part of the record.

Full teaching rules: [`LEARNING_PROTOCOL.md`](./LEARNING_PROTOCOL.md).

## How the RPG works

Real coding progress becomes game progress. Features, self-debugging, code explanations, mobs and bosses earn XP and coins. Coins buy hint tools and cosmetics — never finished solutions.

The deeper systems live in [`GAME_SYSTEM.md`](./GAME_SYSTEM.md), including:

- daily / weekly / long-term quests;
- meaningful-day coding streaks;
- Mastery Shields for concepts I can genuinely use and explain;
- Bronze → Silver → Gold shield progression;
- failed later mastery checks cracking shields instead of deleting my streak;
- HP, inventory, equipment, achievements and boss trophies;
- a coin shop with Potions, Map Scrolls, Syntax Scrolls, Streak Wards and more;
- PYR evolutions tied to actual learning milestones;
- creativity bonuses and hidden discoveries;
- Rival Mode for friends using the same evidence-based rules.

## Creativity + hidden discoveries

Required features prove the curriculum. Extra ideas prove creativity.

If I independently add useful/fun features beyond the brief, PYR can award bounded creativity XP:

| Discovery tier | Bonus |
|---|---:|
| Wild Spark | +5 XP |
| Embercraft | +10 XP |
| Relic Craft | +20 XP |
| Mythic Discovery | up to +30 XP |

PYR can also surprise me with **hidden titles, trophies, gear, lore items, companion variations and other rewards** after memorable moments.

The important part: PYR cannot just make the rules up differently every week.

Every new reward/mechanic is tracked in [`CANON_LEDGER.md`](./CANON_LEDGER.md). Cosmetics can become player-canon immediately; anything that changes XP, coins, shields, streaks or rival scoring stays **PROVISIONAL** until approved.

That means when somebody forks this campaign later, they can see exactly what became canon and why.

## Mastery Shields

A concept is not considered mastered because I used it once.

To earn a shield I need to **use the concept in real code and pass an AI interview about it**. Later interviews can test whether the knowledge stuck. If I fail one after earning a shield, a shield charge cracks before HP is touched. The streak is never punished for getting an answer wrong.

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

Then read `HANDOFF.md`, open `SESSION_NOTES.md`, summon PYR, and let PYR **teach first** before the first real Forge task.

## PYR — the AI companion

Any AI helping on this repo must follow [`TUTOR_CONTRACT.md`](./TUTOR_CONTRACT.md).

PYR teaches first, then protects the build phase. During Forge, the hint ladder is:

1. ask a useful question;
2. identify the concept;
3. offer pseudocode;
4. show unrelated generic syntax;
5. offer explicit Reference Mode if I remain blocked.

**PYR teaches me. Then I build it.**

## Rival Mode

The system is built so a friend can fork it, reset the campaign and compete using the same canon rules. `rivals.json` can hold public `progress.json` URLs and the dashboard can compare lifetime XP, bosses, shields, streaks, interviews, clean clears and project completion.

Cosmetic hidden loot is for personality and does not inflate competitive power.

## Interactive dashboard

The richer character screen is [`index.html`](./index.html). It reads `progress.json` and shows the quest tree, stats, shields, goals, shop, achievements and companion progression. Deploying `main` as a static site turns it into the live campaign dashboard.

---

**Rule:** learn with examples, Forge without a solution, record assistance honestly.


## Dev Activity League

<!-- ACTIVITY_STATS_START -->

| Dev activity | Current |
|---|---:|
| Activity score | **70** |
| Commit streak | **1 days** — best: 1 |
| Commits | **50** / 7d · **50** / 30d |
| Active dev days | **1** / 7d · **1** / 30d |
| Active branches (30d) | **10** |
| Last commit day | **2026-09-14** |

`Activity score` is machine-derived from commit history. It rewards active days and streaks, caps effective commits per day, and does **not** grant learning XP or Mastery Shields.

<!-- ACTIVITY_STATS_END -->
