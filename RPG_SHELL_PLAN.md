# Forge RPG Shell & Homestead Plan

## Vision

Quest Lab should feel like a small coding RPG that happens to contain a serious editor, not a normal IDE with XP glued to the top.

The coding loop stays the authority:

**Diagnose → Teach → Practice → Teach-back → Forge → Review → Interview → Record**

The RPG shell makes that loop visible, memorable, collectible, and personal without weakening it.

---

## Product pillars

### 1. Forge stays a real IDE

The center of the product remains Monaco + a real shell + an independent AI terminal. Game UI should never make ordinary coding harder.

### 2. The RPG has places, not just numbers

The IDE gains an activity rail with destinations:

- **Forge** — files, editor, terminal and Run/Pretty controls.
- **Tutor Notebook** — a shared `tutor.py` scratchpad where PYR can place safe examples, drills and experiments.
- **Quest Journal** — project objective, mobs, boss gate, side quests and daily/weekly goals.
- **Codex** — concepts, Mastery Shields, mob encounter types and discovered weaknesses.
- **Character** — player level, XP, HP, rank, equipment, achievements and PYR bond.
- **Homestead** — owned cosmetics, room identity, trophy space and shop.
- **Settings** — free usability/layout controls plus equipped cosmetic selections.

The right-side AI terminal remains available while moving through these screens.

### 3. Tutor Notebook is collaborative, project code is not

Every quest workspace gets a dedicated **`tutor.py`**.

`tutor.py` is a collaborative teaching surface:

- PYR may create/edit it with unrelated examples, drills, visual printouts, tiny experiments and debugging demonstrations;
- the player may freely edit/run it too;
- examples must remain transfer-resistant and obey the normal teaching contract;
- PYR can replace old examples when the lesson changes;
- it is never part of the required project implementation or used as evidence that the player wrote the real solution.

The player's real project source is different:

- the integrated PYR tutor must treat project `.py` files such as `blackjack.py` as **read-only**;
- PYR may inspect them for tutoring/review, but must not write, patch, format, rename or auto-fix them;
- only the player edits required project source during normal learning;
- exact project-specific code remains governed by Reference Mode, and even Reference Mode should present the smallest necessary fragment rather than silently inserting it.

This boundary should be enforced technically for the future integrated tutor by exposing only a dedicated `tutor.py` write API. A raw local shell/third-party CLI is inherently powerful and cannot be considered the trusted tutoring boundary.

### 4. The Homestead is progression made visible

Coins can buy cosmetic IDE upgrades and decorations. The player's coding environment slowly becomes *their place*.

Examples:

- visual themes;
- cursor effects;
- HUD frames;
- terminal skins;
- future character outfits;
- future PYR hearth/companion decorations;
- trophies earned from bosses/achievements.

Cosmetics never grant XP multipliers, easier interviews, stronger hints, extra shields or rival-score advantages.

### 5. Usability is never paywalled

Functional settings are always free:

- panel sizes;
- editor font size;
- terminal size;
- HUD density;
- animation toggle;
- focus modes;
- accessibility options.

Coins only gate cosmetic/fantasy presentation.

### 6. The Codex should foreshadow, not spoil

The Codex can reveal mob names, concepts, encounter styles and whether they are locked/available/defeated.

It should **not** reveal exact future interview answers or paste-ready project code. Exact hidden encounters remain hidden until reached.

---

# Shell layout

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ PYTHON QUEST LAB      LV / XP BAR      HP      COINS      STREAK      RANK │
├────┬─────────────┬──────────────────────────────────────┬────────────────────┤
│ 🔥 │ context     │                                      │ PYR / AI TERMINAL  │
│ 📁 │ sidebar     │          FORGE / GAME SCREEN         │                    │
│ 🧪 │             │                                      │                    │
│ ⚔  │             │                                      │                    │
│ 📖 │             │                                      │                    │
│ 👤 │             │                                      │                    │
│ 🏠 │             │                                      │                    │
│ ⚙  │             ├──────────────────────────────────────┤                    │
│    │             │ terminal (Forge view only)           │                    │
└────┴─────────────┴──────────────────────────────────────┴────────────────────┘
```

The activity rail is always visible. The center switches between the editor and game screens. The AI terminal remains independent on the right.

---

# Screen designs

## Forge

- file explorer;
- Monaco editor;
- Save / Pretty / Run;
- normal PTY terminal;
- draggable explorer / terminal / AI splitters;
- current branch + dirty count;
- persistent layout.

## Tutor Notebook

- opens `tutor.py` in a dedicated collaborative editor;
- Run Tutor button executes only `tutor.py`;
- clear visual badge that this is **safe scratch space, not project source**;
- PYR can write here through a dedicated controlled API;
- player can edit the same file between tutor turns;
- later: snapshots/history so useful examples can be pinned into the Codex;
- later: “send this example to Tutor Notebook” from PYR chat.

The notebook should default to a short header explaining the boundary. If a workspace does not have `tutor.py`, Quest Lab creates it automatically.

## Quest Journal

Shows the active project as a chapter.

For Blackjack:

- Main Quest: clear Blackjack;
- current mob;
- mob ladder;
- boss: The House;
- Clean Clear eligibility;
- daily and weekly goals;
- future side/hidden quests.

A later version may read richer objective text directly from the branch `HANDOFF.md`.

## Codex

Two collections:

1. **Concept Codex** — skill name, concept, evidence, interview passes, shield tier/charges.
2. **Encounter Codex** — project mobs, encounter style and discovered state.

Future additions:

- win/loss record per mob family;
- first encounter date;
- common mistake/weakness tags;
- mastered encounter variants;
- boss archive.

## Character

Shows:

- name/title/rank/level;
- HP and XP bars;
- coins/streak/bosses/clean clears;
- equipment slots;
- achievements;
- PYR form, level, bond and next evolution;
- future avatar/paper-doll representation.

## Homestead

Phase 1:

- owned cosmetic collection;
- equipped cosmetics;
- shop catalog;
- buy/equip actions;
- player's coin balance.

Future room layers:

- desk/workbench;
- trophy shelf;
- wardrobe;
- PYR hearth;
- wall trophies from projects;
- collectible lore objects;
- seasonal/event decorations.

## Settings

Free settings:

- explorer width;
- AI width;
- terminal height;
- editor font size;
- HUD density;
- animations;
- reset layout.

Cosmetic selection comes from owned Homestead items.

---

# Trusted tutor write boundary

The integrated PYR tutor should not receive a generic workspace-write tool.

Allowed write surface:

```text
GET  /api/tutor
PUT  /api/tutor
```

Those routes always resolve to `QUESTLAB_WORKSPACE/tutor.py`; callers cannot supply another path.

Project review may use read-only endpoints/context for files like `blackjack.py`, but project writes remain player-controlled.

The normal Forge editor still lets the **player** save any workspace file. The restriction applies to the integrated tutor agent's toolset, not to the human.

Third-party CLIs launched in the raw AI terminal have normal local-user shell power, so they cannot be honestly described as technically sandboxed. Until the in-app controlled PYR adapter exists, they should be treated as manual tools and instructed to respect the tutor contract.

---

# Homestead economy

## Starter cosmetics

Every player starts with:

- Ember Forge theme;
- Basic cursor;
- Forge HUD;
- Charcoal terminal.

## Initial purchasable catalog

| ID | Item | Slot | Price | Purpose |
|---|---|---:|---:|---|
| `theme-deep-forest` | Deep Forest | theme | 120c | moss/forest palette |
| `theme-void-scholar` | Void Scholar | theme | 250c | dark violet scholar palette |
| `theme-ancient-archive` | Ancient Archive | theme | 300c | parchment/gold archive palette |
| `cursor-golden-spark` | Golden Spark | cursor | 80c | cosmetic cursor accent |
| `hud-adventurer` | Adventurer HUD | hud | 150c | stronger RPG framing |
| `terminal-emberglass` | Emberglass Terminal | terminal | 180c | warmer terminal surface |

Purchases spend existing campaign coins. They grant no learning or competitive power.

---

# Persistence model

## Canonical campaign state

`progress.json` stores:

- owned cosmetics;
- equipped cosmetic IDs;
- purchase history;
- catalog metadata used by the Homestead.

This makes purchases portable across clones/forks once committed/pushed.

## Workspace teaching state

`tutor.py` lives in the active quest workspace. It is deliberately separate from canonical player progression so examples can change freely without pretending to be mastery evidence.

## Local IDE preferences

Browser `localStorage` stores device-specific usability preferences:

- panel sizes;
- font size;
- HUD density;
- animation toggle.

Those preferences are not gameplay progression and should not create Git noise.

---

# Delivery roadmap

## Phase 1 — RPG Shell Foundation

- activity rail;
- Forge / Tutor / Quest / Codex / Character / Homestead / Settings screens;
- persistent layout preferences;
- richer top HUD;
- Codex uses real current skill/mob state;
- Homestead catalog visible;
- functional cosmetic purchase/equip API;
- first theme variants;
- dedicated `tutor.py` read/write API and Tutor Notebook surface.

## Phase 2 — Quest-aware tutor UX

- Teach Me / Quick Refresher / Test Me entry choice;
- current mob/concept visible to PYR;
- context bridge for active file, selection, terminal tail, git diff and quest state;
- controlled PYR toolset: read project, write only `tutor.py`;
- encounter banners and clear celebrations.

## Phase 3 — Living Codex

- encounter records;
- weakness tags from real attempts;
- discovered mob variants;
- boss archive;
- interview history;
- mastery progression animations;
- pin useful Tutor Notebook examples into concept entries.

## Phase 4 — Homestead becomes a place

- character avatar/paper doll;
- visible equipment;
- room scene;
- trophy shelf populated by actual achievements;
- PYR hearth and evolution visuals;
- decorative purchases rendered in the room.

## Phase 5 — Project/world polish

- each project gets its own chapter art direction;
- project-specific mob silhouettes/portraits;
- side quests and hidden discoveries;
- boss-intro / boss-clear scenes;
- friend/rival visits or profile comparisons without competitive stat inflation.

---

# Non-negotiables

- Quest Lab remains fully usable without Boot.dev or any external course.
- The integrated PYR tutor can write `tutor.py`; required project source stays read-only to PYR.
- Cosmetics never determine whether the player can learn, code, format, run, debug or access PYR.
- Exact project solutions remain governed by Reference Mode.
- The public activity score remains separate from learning mastery.
- Game UI should celebrate evidence, not manufacture it.
