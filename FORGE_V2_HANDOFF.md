# Forge v2 — Test Handoff

Forge v2 is the current Quest Lab IDE test target on `feature/quest-lab-ide`.

## Why v2 exists

The first Forge shell proved the layout, Monaco editor, real PTY terminal, RPG HUD and Homestead direction. It also exposed terminal instability during development.

Two development behaviours were especially risky for a PTY-backed app:

1. React `StrictMode` intentionally mounts/unmounts effects twice in development, which can create and immediately kill duplicate WebSocket/PTTY sessions.
2. Uvicorn `--reload` restarts the backend process whenever watched files change, which necessarily kills every terminal session.

Forge v2 removes both behaviours from the normal launcher.

## Current v2 architecture

- frontend entry: `ide/frontend/src/AppV2.jsx`
- extra v2 styles: `ide/frontend/src/v2.css`
- backend: `ide/server/app_v2.py`
- launcher: `ide/quest.py`
- game screens: `ide/frontend/src/RpgViews.jsx`

Normal launch now starts the backend **without** reload. Use `--reload-backend` only while actively developing backend code and expect terminal reconnects when doing so.

## Terminal changes

Forge and AI now use separate WebSocket/PTTY routes:

- `/ws/terminal/shell`
- `/ws/terminal/ai`

The frontend now:

- shows connection state;
- queues commands sent while reconnecting;
- automatically reconnects a dropped terminal;
- exposes a manual reconnect button;
- preserves the Forge shell while visiting Character / Quest / Codex / Homestead screens;
- resizes the PTY when panels move.

## AI CLI choices

The right terminal now targets the tools actually used in this setup:

- Codex — `codex`
- Claude — `claude`
- AGY — `agy`

Gemini was removed from the quick-launch bar.

`/api/runtime` detects whether each command exists and disables missing quick-launch buttons instead of failing silently.

## Tutor Notebook boundary

`tutor.py` is collaborative scratch space.

The controlled future PYR agent may write examples and exercises there. Required project source such as `blackjack.py` remains read-only to the tutor agent. The raw CLI terminal is intentionally powerful and is not a security sandbox.

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
- animation toggle;
- resizable explorer, terminal and AI panes.

## Next major development block

After v2 survives a real user test:

1. PYR context bridge: selected code, active file, terminal tail, git diff, quest state.
2. Controlled PYR tools: read project source, write only `tutor.py`, update earned campaign state through explicit actions.
3. Teach Me / Quick Refresher / Test Me encounter entry.
4. Living Codex records: attempts, encounter records, weakness tags and interview history.
5. Homestead room expansion: avatar, equipment visuals, trophy shelf, PYR hearth and project trophies.
6. Quest events: mob intros, clear animations, side quests, hidden discoveries and boss presentation.

## PC test procedure

From the platform checkout:

```bash
git pull --ff-only
.venv/bin/python -m pip install -r ide/server/requirements.txt
cd ide/frontend && npm install && cd ../..
.venv/bin/python ide/quest.py --workspace ../questlab-blackjack
```

Test these in order:

1. Forge terminal reaches `connected` and accepts `pwd`, `git status`, and `python3 blackjack.py`.
2. Switch to Character and back to Forge; the shell session should still exist.
3. Resize the bottom terminal and right AI panel.
4. Open Tutor Notebook, edit/save/format/run `tutor.py`.
5. Launch Codex / Claude / AGY from the right terminal if installed.
6. Click through Quest Journal, Codex, Character, Homestead and Settings.
7. Refresh the browser and confirm layout preferences persist.

Report any broken behaviour with the visible connection state plus the launcher-terminal traceback/output when possible.
