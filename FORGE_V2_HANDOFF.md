# Forge v2 — Test Handoff

Forge v2 is the current Quest Lab IDE test target on `feature/quest-lab-ide`.

## Current architecture

- frontend entry: `ide/frontend/src/AppV2.jsx`
- game screens: `ide/frontend/src/RpgViews.jsx`
- QOL/personalization overlays: `forgeEnhancements.js`, `uiPolish.js`, `commandPalette.js`
- combat shell overlay: `combatShell.js`
- backend: `ide/server/app_v2.py`
- launcher: `ide/quest.py`

Normal launch starts the backend without reload so PTY sessions are not destroyed during ordinary use.

## Terminal stability

Forge and AI use separate WebSocket/PTY routes:

- `/ws/terminal/shell`
- `/ws/terminal/ai`

The frontend:

- shows connection state;
- queues commands sent while reconnecting;
- automatically reconnects a dropped terminal;
- exposes a manual reconnect button;
- preserves the Forge shell while visiting Character / Quest / Codex / Homestead screens;
- resizes the PTY when panels move.

The launcher also detects occupied frontend/backend ports and chooses free ports instead of crashing. WSL browser launching targets the Windows browser when available.

## AI CLI choices

The right terminal targets:

- Codex — `codex`
- Claude — `claude`
- AGY — `agy`

`/api/runtime` detects whether each command exists and disables missing launch buttons.

## Tutor Notebook boundary

`tutor.py` is collaborative scratch space.

The controlled future PYR agent may write examples/exercises there. Required project source such as `blackjack.py` remains read-only to the tutor agent. The raw CLI terminal is intentionally powerful and is not a security sandbox.

## QOL currently implemented

- `Ctrl+S` save;
- `Ctrl+Enter` run current Python file;
- `Ctrl+Shift+Enter` submit recent run context to the launched AI;
- `Shift+Alt+F` format;
- `Ctrl+\`` focus Forge terminal;
- `Ctrl+Shift+\`` focus AI terminal;
- `Ctrl+Shift+P` command palette;
- resizable explorer / terminal / AI panes;
- persistent panel/font/HUD preferences;
- custom character portrait stored locally in the browser;
- vector UI icon pass instead of OS emoji icons.

## RPG Shell currently implemented

- Forge editor and normal terminal;
- independent AI terminal;
- Tutor Notebook;
- Quest Journal;
- Codex;
- Character sheet;
- Homestead scene + cosmetic catalog;
- cosmetic buy/equip backend;
- themes / cursor / HUD / terminal cosmetic slots;
- persistent local layout sizes;
- editor and terminal font settings;
- HUD density;
- animation toggle.

## Combat foundation — Slice 1

Ruleset `1.4.0` now makes the simplified combat direction canonical:

- normal coding/learning is Safe Mode and cannot hurt HP;
- deliberate submitted Battle actions may counterattack only after an incorrect/incomplete verdict;
- verified work deals **Impact** against enemy **Resolve**;
- there is no mechanical weapon-damage slot;
- armor is percentage-based Battle damage reduction;
- the starter Apprentice Coat is 10% reduction;
- trinkets hold special effects and may visually be weapons such as scythes/swords/staffs;
- Downed never locks the player out of learning;
- weekly raids are future shared software-project bosses using predefined objective Impact.

The current UI slice adds:

- Character gear display reduced to Armor / Trinket / Title;
- armor percentage shown directly;
- Safe/Battle doctrine card;
- Quest Journal Battle Shell with encounter Resolve, Threat, armor and trinket info;
- Impact bands for small answers, checkpoints and major objectives;
- a future Weekly Raid gate preview;
- Homestead Trinket Vault concepts including Ember Scythe, Phoenix Ember, Seer's Lens and Bond of Embers.

**Important:** this slice is deliberately display-only. `Submit Run` does not yet mutate HP/Resolve. State changes wait for controlled PYR adjudication so the game never damages the player based on an unverified terminal result.

Canonical combat details live in `COMBAT_SYSTEM.md`.

## Next implementation block

1. PYR context bridge: active file, selection, terminal tail, git diff, quest/mob state.
2. Controlled PYR verdict path for Battle submissions.
3. Persistent Resolve / armor calculation / HP / combat log.
4. Teach Me / Quick Refresher / Test Me encounter entry.
5. Living Codex records: attempts, weakness tags and interview history.
6. Boss phase presentation and trinket triggers.
7. Later: shared weekly raid transport/state and party objectives.

## PC test procedure

From the platform checkout:

```bash
git pull --ff-only
.venv/bin/python ide/quest.py --workspace ../questlab-blackjack
```

Test:

1. Forge terminal reaches `connected` and accepts `pwd`, `git status`, and `python3 blackjack.py`.
2. `Ctrl+S`, `Ctrl+Enter`, `Ctrl+Shift+P` and `Ctrl+Shift+Enter` behave sensibly.
3. Character portrait upload works and persists after refresh.
4. Character page shows Armor / Trinket / Title, not a mechanical weapon slot.
5. Quest Journal shows the Battle Shell and Weekly Raid preview.
6. Homestead shows the Trinket Vault concepts.
7. Switch between game screens and Forge; PTY sessions remain alive.
8. Resize panels and refresh; layout preferences persist.

Report broken behaviour with a screenshot and the visible launcher/terminal output when useful.

## Current test boundary

This remains a local-runtime test build. The combat shell intentionally stops before automatic verdicts/state mutation. The next high-value engineering step is the controlled PYR context/verdict bridge, not more fake front-end combat state.
