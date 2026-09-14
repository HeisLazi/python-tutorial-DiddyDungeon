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
- **Quest Journal** — project objective, mobs, boss gate, side quests and daily/weekly goals.
- **Codex** — concepts, Mastery Shields, mob encounter types and discovered weaknesses.
- **Character** — player level, XP, HP, rank, equipment, achievements and PYR bond.
- **Homestead** — owned cosmetics, room identity, trophy space and shop.
- **Settings** — free usability/layout controls plus equipped cosmetic selections.

The right-side AI terminal remains available while moving through these screens.

### 3. The Homestead is progression made visible

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

### 4. Usability is never paywalled

Functional settings are always free:

- panel sizes;
- editor font size;
- terminal size;
- HUD density;
- animation toggle;
- focus modes;
- accessibility options.

Coins only gate cosmetic/fantasy presentation.

### 5. The Codex should foreshadow, not spoil

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
- Forge / Quest / Codex / Character / Homestead / Settings screens;
- persistent layout preferences;
- richer top HUD;
- Codex uses real current skill/mob state;
- Homestead catalog visible;
- functional cosmetic purchase/equip API;
- first theme variants.

## Phase 2 — Quest-aware tutor UX

- Teach Me / Quick Refresher / Test Me entry choice;
- current mob/concept visible to PYR;
- context bridge for active file, selection, terminal tail, git diff and quest state;
- encounter banners and clear celebrations.

## Phase 3 — Living Codex

- encounter records;
- weakness tags from real attempts;
- discovered mob variants;
- boss archive;
- interview history;
- mastery progression animations.

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
- Cosmetics never determine whether the player can learn, code, format, run, debug or access PYR.
- Exact project solutions remain governed by Reference Mode.
- The public activity score remains separate from learning mastery.
- Game UI should celebrate evidence, not manufacture it.
