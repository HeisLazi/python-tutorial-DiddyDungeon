# Python Quest Lab

A terminal-first Python training campaign where I build small games myself while **PYR**, a Socratic AI companion, teaches concepts, tests understanding, and turns real progress into an RPG character.

The point is not to speedrun eight repos. The point is to make Python fundamentals feel automatic enough that I can move into larger systems with real understanding — while Git history shows whether I am actually showing up and building.

<p align="center">
  <img alt="Level" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.player.level&label=Level&color=blue" />
  <img alt="Lifetime XP" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.player.lifetime_xp&label=Lifetime%20XP&color=orange" />
  <img alt="Learning Streak" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.streak.current&label=Learning%20Streak&color=red" />
  <img alt="Bosses" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.bosses_defeated&label=Bosses&color=purple" />
  <img alt="Mastery Shields" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Fprogress.json&query=%24.stats.mastery_shields_earned&label=Mastery%20Shields&color=brightgreen" />
</p>

<p align="center">
  <img alt="Activity Score" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Factivity.json&query=%24.activity_score&label=Activity%20Score&color=green" />
  <img alt="Dev Streak" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Factivity.json&query=%24.current_streak&label=Dev%20Streak&color=yellowgreen" />
  <img alt="7 Day Commits" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Factivity.json&query=%24.commits_7d&label=Commits%207d&color=informational" />
  <img alt="Active Days" src="https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2FHeisLazi%2Fpython-tutorial-DiddyDungeon%2Fmain%2Factivity.json&query=%24.active_days_30d&label=Active%20Days%2030d&color=success" />
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
| Learning streak | **0 days** — best: 0 |
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

`progress.json` is the canonical learning/player state. PYR refreshes this block only when learning progress is genuinely earned.

## Dev Activity League

<!-- ACTIVITY_STATS_START -->

| Dev activity | Current |
|---|---:|
| Activity score | **130** |
| Commit streak | **3 days** — best: 3 |
| Commits | **229** / 7d · **229** / 30d |
| Active dev days | **3** / 7d · **3** / 30d |
| Active branches (30d) | **11** |
| Last commit day | **2026-09-16** |

`Activity score` is machine-derived from commit history. It rewards active days and streaks, caps effective commits per day, and does **not** grant learning XP or Mastery Shields.

<!-- ACTIVITY_STATS_END -->

This block is maintained by GitHub Actions from `activity.json`, not by PYR. The full scoring/fairness rules live in [`ACTIVITY_SYSTEM.md`](./ACTIVITY_SYSTEM.md).

**Two streaks, two meanings:**

- **Learning Streak** = PYR verified that I learned/built something I can explain.
- **Dev Streak** = Git history proves I committed qualifying work that day.

A high commit count cannot fake mastery, and a high mastery score cannot fake activity.

## The learning loop

For a new or rusty concept the flow is:

**Diagnose → Teach → Practice → Teach-back → Forge → Review → Interview → Record**

During **Teach / Practice**, PYR can show code examples, but the examples must use a different context so they teach the concept without becoming a paste-ready solution for the active game.

Once I show that I understand the idea, I enter **Forge phase** and implement the project requirement from scratch.

If I genuinely cannot bridge the gap, I can explicitly enter **Reference Mode** and see the smallest project-specific exact fragment needed. That milestone then earns **50% XP/coins**. A later Recovery Trial can bring it up to at most **75%**, but the assistance remains part of the record.

Full teaching rules: [`LEARNING_PROTOCOL.md`](./LEARNING_PROTOCOL.md).

## Creativity + hidden discoveries

Required features prove the curriculum. Extra ideas prove creativity.

| Discovery tier | Bonus |
|---|---:|
| Wild Spark | +5 XP |
| Embercraft | +10 XP |
| Relic Craft | +20 XP |
| Mythic Discovery | up to +30 XP |

PYR can surprise me with hidden titles, trophies, gear, lore items, companion variations and other rewards after memorable moments.

New custom rewards/mechanics are recorded in [`CANON_LEDGER.md`](./CANON_LEDGER.md), so another AI — or another player — can reconstruct what actually became canon instead of making up a different ruleset every session.

## Mastery Shields

A concept is not considered mastered because I used it once. I need to **use it in real code and pass an AI interview about it**.

If I later fail a mastery check after earning a shield, a shield charge cracks before HP or my Learning Streak is touched.

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

For now I am deliberately sharpening:

`variables` · `input/output` · `if/elif/else` · `for/while` · `functions` · `lists` · `dictionaries` · `strings` · `random`

Files/JSON, exceptions, modules, testing, classes/OOP and APIs come after the foundation feels natural.

## Rival Mode

The repo is designed to be forked by a friend and run under the same rules.

Each player has two public score families:

| Learning | Development |
|---|---|
| Lifetime XP | Activity Score |
| Bosses | 7d / 30d commits |
| Mastery Shields | Active dev days |
| Interviews | Dev streak |
| Clean Clears | Active branches |
| Project completion | Git activity history |

The dashboard's Rival Board can read both `progress.json` and `activity.json` from each fork. It currently sorts by **Dev Activity** so we can race to be the most consistent builder while still seeing who has stronger demonstrated Python mastery.

The competition intentionally caps effective commits per day. The goal is **more real development days**, not 40 meaningless commits called `update`, `update2`, `update3`.

When a friend joins, their entry in `rivals.json` looks like:

```json
{
  "name": "FriendName",
  "progress_url": "https://raw.githubusercontent.com/OWNER/REPO/main/progress.json",
  "activity_url": "https://raw.githubusercontent.com/OWNER/REPO/main/activity.json"
}
```

## Enter the current quest

```bash
git fetch --all
git switch 01-blackjack
```

Then read `HANDOFF.md`, open `SESSION_NOTES.md`, summon PYR, and let PYR teach the next rusty concept before the Forge task.

## Interactive dashboard

[`index.html`](./index.html) is the richer campaign screen. It reads:

- `progress.json` for character/learning state;
- `activity.json` for real Git activity;
- `rivals.json` for competition.

It shows the quest tree, both streaks, 30-day commit heatmap, active branches, Activity Score, Mastery Shields, goals, shop, achievements and the Rival Board.

## Canon / rules

- [`CANON_LEDGER.md`](./CANON_LEDGER.md) — what is actually canon
- [`TUTOR_CONTRACT.md`](./TUTOR_CONTRACT.md) — how PYR must behave
- [`LEARNING_PROTOCOL.md`](./LEARNING_PROTOCOL.md) — how concepts are taught and forged
- [`GAME_SYSTEM.md`](./GAME_SYSTEM.md) — RPG progression
- [`ACTIVITY_SYSTEM.md`](./ACTIVITY_SYSTEM.md) — commit activity + rival fairness

---

**Rule:** learn with examples, Forge without a solution, commit meaningful checkpoints, record assistance honestly.
