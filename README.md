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

**Equipped:** Apprentice Coat · no trinket yet

**Next major goals:** first Teach-back → first mob → first concept interview → first Mastery Shield → first hidden discovery → defeat **The House** → evolve PYR into an **Ember Sprite**.

<!-- PUBLIC_STATS_END -->

Before signed-in cloud sync, `progress.json` is the canonical local learning/player state. After signed-in cloud sync, Supabase is synchronized account/game-state authority and `progress.json` is the local/offline cache/device working copy. PYR refreshes this block only through the local state/sync service when learning progress is genuinely earned.

## Dev Activity League

<!-- ACTIVITY_STATS_START -->

| Dev activity | Current |
|---|---:|
| Activity score | **152** |
| Commit streak | **4 days** — best: 4 |
| Commits | **396** / 7d · **396** / 30d |
| Active dev days | **4** / 7d · **4** / 30d |
| Active branches (30d) | **13** |
| Last commit day | **2026-09-17** |

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
| 1 | `01-blackjack` | Blackjack | lists, functions, game state | The House |
| 2 | `04-casino-slots` | The Silver Reels (`silver_reels/`) | random, probability, modules, tests, README | Ekse Ouens P Diddy |
| 3 | `05-dungeon-crawler` | The Deep Crawler (`deep_crawler/`) | packages, classes, files/JSON, connected systems | Die Tozza van Zamalek |

Next up: a Django campaign (The Guild Hall), then the backend projects (The Courier, The Vault) and the AI projects. The retired campaigns (RPS, Detective, Creature Battle, Gladiator, Football Manager, Game Agent, AI Familiar) are kept in `ide/server/campaigns_archive/` and no longer load.

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

## Where the game is now (2026-10-26)

DiddyDungeon is a Tauri desktop app (FastAPI backend in `ide/server/`, React/Vite frontend in `ide/frontend/`) with a pixel-arcade look. It is a monster-hunter RPG for learning to be a complete programmer: bugs are beasts, concepts are signs.

- **Campaigns** (see the table above): Blackjack, The Silver Reels, The Deep Crawler. Each has 18-22 bounties in four acts, a boss gauntlet, and a real project folder (`silver_reels/`, `deep_crawler/`). A bounty opens like real development: make the folder and file in the terminal, run it, press **Check**. The game verifies setup steps on disk (free, no PYR call); code is graded by PYR.
- **Forge**: Monaco editor, terminal, an editor-style **explorer** (New file / New folder, delete to a recoverable trash, files made in the terminal appear on their own, game files only). Run `cd`s into the file's own folder first.
- **PYR** (OpenCode) grades work and gives hints. Asking PYR in a fight costs that fight's rewards: 20% off XP and coins per ask (floor 40%), no loot from the 2nd ask.
- **Aid**: one-time loot, not trinkets. PYR's Favour/Blessing = free asks; Ward Shield/Aegis of Patience = block a wrong answer's damage. Armed from the Armory's Aid tab; dropped by bounties and bosses, sold by the Merchant.
- **Tutor Notebook**: Codex, Bestiary, Signs, sparring, IDE practice. It remembers where you were until you close the app.
- **Settings → Player Stats**: a GitHub-style activity graph (lines of code, answers, mobs, floors, bosses) and lifetime records (mobs, bosses, Dungeon runs survived, highest floor, ...). Local only.
- **LearnHarness bridge**: send a concept home to study, and see what you studied (read-only).
- **Infinite Dungeon**: grid floors, camps, elites, floor bosses and a leaderboard.

Next campaigns, in order: The Guild Hall (Django), then The Courier and The Vault (backend), Forge Your Own Model and The Oracle (AI). A VS Code companion extension is an open idea.

## Roadmap: Home overhaul (next)

Home ("the Homestead": rest, loadout, upgrades, Market, Bounty Office) works but is a menu with a picture. The goal is a place that is fun to be in and play around in, and that makes you want to open the app.

Ideas to settle together before building:

1. **A real 2D room/town you walk around**, not a list of cards: stations (Armory, Hearth, Pantry, Study desk, Pyr's perch, Market stall, Bounty board) you move to and use. A Godot 4 scene exported to the web (HTML5) and embedded in the app, or a canvas/Pixi scene in React fed by the same state. Decide which; Godot is better for animation, a React canvas is lighter and easier to wire to the save.
2. **Art pipeline with the installed tools** (all present on this machine via flatpak shims in `~/.local/bin`): Blender renders low-poly characters and props to pixel-art spritesheets (turntables/idle/walk); Tiled builds the room map; LibreSprite/Pixelorama for hand-cleaning pixels; Material Maker for floor/wall textures; Godot for scenes, animation and tilemaps. The `gamedev` MCP tools (`blender_render_turnaround`, `spritesheet_tool`, `tiled_map_tool`, `godot_scaffold_2d`) automate the repetitive parts.
3. **Living character**: the paper-doll avatar (skin, hair, outfit, gear) rendered as a walking sprite that shows equipped weapon/armour; Pyr the companion follows and reacts (hints, level-ups, streaks).
4. **Things to do at home**: cook/eat (food and tonics), train at the dummy (sparring), study desk (LearnHarness, Tutor), trophy wall (achievements, boss relics, the activity graph on the wall), a notice board with the next bounty.
5. **Day/night and streaks**: the room reflects your streak and time of day; a lit hearth when you coded today.
6. **Keep it fast**: one heavy process at a time on this 14 GB machine; assets are static PNG spritesheets, no runtime 3D.

### Art direction (set 2026-10-26)

- **Look:** Game Boy Advance, Pokemon FireRed/LeafGreen era, with Zelda: A Link to the Past/Minish Cap overworld feel. Top-down, 16x16 tiles, chunky outlined sprites with flat 3-4 tone shading, grass tufts, fences, bushes, flower beds, wooden floors with plank lines. Reference: FireRed town screenshot (tile style) and Gen 5 trainer sprite sheets (the character sheet layout: 4-direction walk, run, idle, bike/ride, throw/cast poses, plus a large portrait per character).
- **Retro-fy on top:** scanlines, slight CRT curve/vignette and a soft phosphor glow as a toggleable post effect (a Settings option, default on in Home), limited palette per scene, 2x or 3x integer scaling, no smoothing.
- **Characters:** same sheet format as the references (walk cycle in 4 directions, idle, a "cast/point" pose and a portrait), but moulded to our world: the hunter (the paper-doll avatar: skin, hair, outfit, accent), Pyr the code-flame companion, the Merchant, Auditor Pell and the campaign bosses as portraits. Hunter gear shows on the sprite (weapon, armour, trinket glow). The theme stays dark-arcade monster-hunter; the references are for *form and craft*, not for characters or costumes.
- **Pipeline:** Blender models a low-poly character and props once, renders 4 directions x walk/idle frames at tiny size, a palette-reduce pass makes them match, LibreSprite/Pixelorama hand-clean, Tiled builds rooms, Godot or a canvas scene plays them. One sprite sheet per character, one tileset per zone.

### Room upgrades: Home as a Hades-style base (proposal)

The Homestead becomes a base that grows between runs, like the House of Hades: upgrades are permanent, bought with a meta currency, and most of them make the Infinite Dungeon and the campaign feel better.

- **Two currencies:** *coins* (cosmetics, Market) and *Embers* (the existing upgrade tokens; earned from Dungeon floors, bosses and clean clears). Upgrades cost Embers, so playing the roguelike funds the base and the base makes the next run stronger.
- **Stations, each with a track of tiers** (a station is a spot in the room you walk to):
  - **Hearth** (rest): max HP, heal between floors, a "warm start" (begin a run with a free ward).
  - **Armory rack:** more loadout slots, gear repair-free swaps, +loot luck, Aid storage cap (free asks, wards).
  - **Pantry / Kitchen:** stronger food and tonics, carry more, one meal that lasts a whole run.
  - **Study desk:** LearnHarness and Tutor hooks; unlock "hint lanterns" that cost less PYR reward; sign XP boosts.
  - **Training dummy / sparring ring:** sparring rewards, practice a mob you already beat for Embers.
  - **Map table:** Dungeon route intel (see risk on stairs, reveal a room type, choose a start region, reroll a floor once).
  - **Trophy wall:** achievements, boss relics, the activity graph; relics on the wall give small passives.
  - **Pyr's perch:** companion stages and abilities (a free hint per floor, a warning before a trap).
- **Pre-run "loadout" step** (like choosing a Keepsake/Weapon in Hades): before a Dungeon run pick one relic from the wall, one Aid item, and a starting boon the base unlocked.
- **Rules to keep it honest:** upgrades never write your code or reduce what you must write; they change HP, loot, information and convenience. Costs scale per tier; some tiers need a campaign milestone (clear a boss to unlock a station).
- **State:** stays in `homestead.room_upgrades` and `upgrade_tokens` (already synced); the five current upgrades (Reinforced Hearth, Warding Loom, Breaker Workbench, Siphon Basin, Field Kitchen) become tier 1 of the stations above. Dungeon runs read `upgrade_effects`.

### Decisions (2026-10-26)

- **Engine: embedded Godot.** Home is a Godot 4 scene exported to the web (HTML5, single-threaded export so it needs no special headers) and embedded in the Forge app as an iframe on the same origin. The React app stays the source of truth: it passes the save (hunter look, gear, upgrades, Embers, streak) into the scene and the scene sends back "use station" events (open Armory, rest, buy upgrade, start run). No game rules live in Godot; it draws and walks.
- **First slice:** one room (Tiled map, FireRed-style tiles), a walking hunter from a Blender-made sheet, three working stations (Hearth, Armory rack, Map table), Pyr following, scanlines/CRT toggle. Everything else in this README stays parked until this feels good.
- **Blocker to start the web build:** Godot's web export templates are not installed and must be downloaded (needs the user's OK).

### Home first slice: built (2026-10-26)

The walkable Home exists and runs inside the app: `ide/home-godot` (Godot 4.7, 240x160 GBA resolution) embedded as an iframe on Home. One room with a Hearth (rest, +HP), the Armory rack (opens the real Armory panel), a Map table (to the Dungeon), a door (to the Forge), tier pips per station, a walking hunter with Pyr following, and a scanline/vignette shader you can toggle. The app sends the save's HP, Embers, upgrade tiers and "coded today" (a lit or cold hearth); Godot reports "use this station". "Classic home" stays one click away, and is the fallback when the web build is absent.

- **Build it:** `tools/build_home.sh` regenerates the art (`tools/home_art/make_tiles.py`, `make_hunter.py`) and exports the web build to `ide/frontend/public/home/` (git-ignored), then rebuild the frontend. It needs Godot 4.7.2 and its Web export templates (`web_nothreads_release.zip` and friends in `~/.var/app/org.godotengine.Godot/data/godot/export_templates/4.7.2.stable/`).
- **Art:** the room is now a gothic castle hall (Castlevania mood in the GBA look): a polished marble checker floor, stone-block walls with a plinth, a crimson carpet runner from the great door to the pointed-arch hearth, stained-glass windows with moonbeams, banners, candelabras, braziers, pillars, armour statues. Tiles and objects are drawn in code with a fixed palette (`tools/home_art/make_tiles.py`). The 16x32 hunter is a vampire hunter in the Trevor Belmont mould (black high-collared cloak lined crimson, dark tunic with a grey-green belt band, torn red tabard, gold-and-steel bracers, sword scabbard, chain whip, black boots) that keeps the avatar's umber skin, locs and goatee. He is hand-placed pixels (`make_hunter.py`): a Blender 3D render shrunk to 16 px turned to mush, so Blender is kept for big pieces (portraits, props; `hunter_blender.py`).
- **Test it:** `tools/home_art/shots.sh` saves screenshots of the room at a few spots.
- **Next for Home:** more stations (Pantry, Study desk, Training ring, Trophy wall, Pyr's perch), the Ember upgrade tracks and costs from the economy table, the pre-run loadout pick, day/night, the avatar's look on the walking sprite, and a Tiled-built bigger map.

### Upgrade economy target

Maxing every upgrade should be a real grind in Infinite Dungeon playtime:

| Player | Time to max |
|---|---|
| Newer / slower coder | 30-40 h |
| OK player | about 20 h |
| Experienced coder | about 15 h |
| Speedrunner (300 wpm, no thinking) | under 5 h |

Because faster players clear more floors per hour but earn the same Embers per floor, the time ratio falls out of floors per hour (roughly 6 / 10 / 14 / 42 floors an hour). With about 10 Embers per cleared floor on average (more on boss floors, a little more for clean clears), the **total cost of every upgrade is about 2,100 Embers** (35 h x 6 floors x 10). Per-tier costs are built from that budget and tuned with real data: the Dungeon will record playtime and floors per run so these numbers can be corrected after the first playtests. Speed is capped by wrong answers and by the fact that floors still need correct answers, so rushing cannot beat knowing the material.

### Roadmap (parked until the Home slice is done)

1. **Dungeon locations with their own maps.** Each place in the Infinite Dungeon gets a mini location map and a theme: mountains, ocean monuments, abandoned cities, and more. Different zones, different tilesets and mobs, chosen at the Map table.
2. **Depth as layers.** Each floor is a layer deeper into the location. It is not shown as a number; the art, lighting, mobs and music just get deeper and darker.
3. **Reward exploration, not boss rushing.** Small mobs and side rooms teach you about the boss (lore, then **weaknesses**) and pay coins and loot for the shop.
4. **Weaknesses.** A weakness you discover about a boss is a small, silly, concrete edge: it lowers the boss's Resolve, or acts like a trinket for the fight (for example double damage for the first two turns because you struck its swollen ankle). Discovered once, remembered in the Codex, usable on every later fight with that boss.
5. Campaign and tooling roadmap (Guild Hall, Courier, Vault, AI projects, a VS Code companion) is unchanged.

Open questions: exact Ember sources per floor and boss; how much of the avatar customisation moves into the room.

Asset and tool notes live in `docs/` when the work starts.

## Play it

Quest Lab is a desktop app with a retro pixel arcade look: open **Diddy
Dungeon** from the app launcher (or run `quest-lab`). PYR, the tutor, runs on
your own OpenCode install to grade work, write Infinite Dungeon questions
and give hints.

- [`docs/DESKTOP_APP.md`](docs/DESKTOP_APP.md): launch, install, how the app works, troubleshooting
- [`docs/AI_TUTOR.md`](docs/AI_TUTOR.md): setting up PYR on OpenCode and its safety rails

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
