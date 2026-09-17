# Forge v2 — Current Test Handoff

Forge v2 is the current Quest Lab IDE test target on
`feature/cloud-sync-desktop`.

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

## Tutor Notebook boundary (Campaign + Practice)

`tutor.py` is one managed collaborative notebook shared by the Campaign Tutor
and Practice surfaces. The player may edit, format and run it, and the
controlled tutor endpoint may write bounded teaching examples there only when
the learner explicitly asks. Practice has its own unlimited, no-reward
sessions/history and concept notes, but it uses the same notebook/editor and
cannot write Campaign/Dungeon rewards, HP, Resolve, equipment, combat or run
state.

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
- custom character portrait with an account-scoped private cloud asset when
  signed in, plus a bounded local/offline fallback;
- vector UI icon pass instead of OS emoji icons.

## RPG Shell currently implemented

- Forge editor and normal terminal;
- independent AI terminal;
- Campaign Tutor Notebook endpoint (dedicated destination; hidden from the normal project file tree);
- Quest Journal;
- Codex;
- Character sheet;
- Homestead scene + cosmetic catalog;
- Infinite Dungeon checkpoint screen;
- independent Practice screen;
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

**Important:** React never invents combat changes. `Submit Run` binds the
player evidence, the selected provider returns a validated verdict, and the
state service derives HP/Resolve/Impact/rewards before returning the event that
the UI renders. Provider authentication remains an external release gate.

Canonical combat details live in `COMBAT_SYSTEM.md`.

## Next implementation block

1. **Implemented:** PYR context bridge at `GET/POST /api/pyr/context` captures
   active file, selected code, terminal tail, bounded git diff, and the current
   quest/mob/concept plus assistance/Clean Clear state. It is read-only and
   excludes player-state/secret-looking files.
2. **Local Battle flow implemented:** `POST /api/pyr/battle-submission` binds a
   bounded player answer to the current objective, digest and server-issued
   evidence ID without persisting the answer. The Quest Journal sends that
   submission to the selected local AI terminal. `POST /api/pyr/verdict` then
   requires the matching submission tokens and delegates to the internal state
   service; callers cannot provide Impact, rewards, HP or counterattack values.
   Provider authentication remains a hosted-release gate.
3. **Local Dungeon loop implemented:** `dungeon_run` is a canonical run-scoped
   checkpoint. `POST /api/dungeon/start`, `PUT /api/dungeon/editor` and
   `GET /api/dungeon` restore floor/room/question/editor state after a
   restart. The state service owns the map selector, adaptive current mob,
   provider-gated verdict, rest/market rooms, local leaderboard and death
   reset. `dungeon.py` is a controlled projection; internal question rotation
   blanks it. Hosted Dungeon transport/leaderboards remain behind Milestone C.
4. **Campaign completion gate implemented:** clearing the final mob marks the
   mob sequence complete and exposes a boss gate. Trusted game code can record
   a boss clear only with separate behaviour, explanation and interview
   evidence IDs; the service derives the +100 XP reward, counters, achievements
   and first-boss companion evolution. The UI never treats a mob clear as a
   boss victory or reveals future interview prompts.
5. **PTY state routing hardened:** terminal environments expose the canonical
   repo package/path and `questlab-state` wrapper while retaining the quest
   workspace cwd. Raw workspace `progress.json` edits remain legacy and
   non-authoritative.
6. Persistent Resolve / armor calculation / HP / combat log are state-service
   outputs of the validated local verdict path.
7. Teach Me / Quick Refresher / Test Me remain provider-driven encounter
   choices; future exact questions are never revealed by the projection.
8. **Implemented locally:** Living Codex records retain bounded encounter
   attempts, question types, weakness tags, verified/incorrect results,
   interview history, mastery evidence and player-authored notes when the state
   service records them. Provider authentication and hosted projection remain
   external gates.
9. Dungeon question generation, rest/market rooms, score, death reset,
   checkpoint resume and local run completion are implemented. Hosted Dungeon
   sync/leaderboards remain deferred.
10. Independent Practice history and provider-validated learning evidence are
    implemented locally with zero Campaign/Dungeon rewards.
11. **Implemented locally:** Boss phase presentation and trinket triggers. The
    canonical state service records bounded boss requirement phases and owns
    Ember Scythe, Guardian Sigil and Phoenix Ember effects; hosted rollout and
    provider-authenticated adjudication remain gated.
12. Later: shared weekly raid transport/state and party objectives.

## PC test procedure

From the platform checkout:

```bash
git pull --ff-only
PYTHONPATH=. .venv/bin/python -m ide.quest --workspace ../questlab-blackjack
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

This remains a local-runtime test build. The combat shell waits for the
selected provider to adjudicate a submitted answer; the state service then
owns Resolve/HP/reward/Codex mutations and React renders the returned event.
The context, answer-binding and challenged-verdict halves of the bridge are
implemented and tested. The local Dungeon/Practice loops, checkpoints,
adaptive rooms, rest/market, death reset, leaderboard and Practice history are
implemented; provider authentication, hosted campaign migration, hosted
Dungeon transport and real PC/laptop acceptance remain deliberately
unclaimed.
