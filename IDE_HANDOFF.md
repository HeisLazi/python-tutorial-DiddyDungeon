# Quest Lab IDE — Handoff

This branch starts the local browser IDE version of Python Quest Lab.

The public dashboard still lives on `main`. The IDE is **local-first**: your browser talks only to a FastAPI server bound to `127.0.0.1`, and that server is allowed to access one chosen quest workspace.

## Milestone 1 — implemented on this branch

The first usable slice now contains:

- RPG / character stats loaded from the local `progress.json` cache (or
  synchronized state through the local sync service after sign-in) and
  `activity.json`;
- Monaco editor (the editor core used by VS Code);
- file explorer scoped to one workspace;
- save + `Ctrl+S`;
- create-file flow;
- **Pretty / Format Document** support:
  - Python uses **Ruff formatter**;
  - JS/TS/JSON/CSS/HTML/Markdown/YAML uses **Prettier**;
  - `Shift+Alt+F` matches the familiar VS Code format-document shortcut;
- two independent real PTY terminals through xterm.js:
  - normal workspace shell below the editor;
  - dedicated AI CLI terminal on the right;
- quick AI-terminal launch buttons for `codex`, `claude`, and `gemini` if those CLIs are installed;
- draggable VS Code-style panel dividers for explorer width, AI width and terminal height;
- Run button for the current Python file;
- current git branch / dirty-file count;
- path sandboxing so the editor API cannot browse outside the selected workspace.

The terminals are intentionally real. Anything you type there runs with your local user permissions, just like opening your normal terminal. Keep the server bound to localhost.

---

# One-time setup

From the repo checkout containing this branch:

```bash
git switch feature/quest-lab-ide

python3 -m venv .venv
.venv/bin/python -m pip install -r ide/server/requirements.txt

cd ide/frontend
npm install
cd ../..
```

The `npm install` step installs the IDE frontend plus Prettier. The Python requirements install FastAPI/Uvicorn/Pydantic plus Ruff for Python formatting.

## Recommended quest workspace: git worktree

The IDE platform and the project branch should not fight over the same checkout. Keep the IDE branch in this folder, then put the quest you are coding in a worktree next to it.

For Blackjack:

```bash
git fetch --all
git branch blackjack-workspace origin/01-blackjack
git worktree add ../questlab-blackjack blackjack-workspace
```

If that worktree already exists, skip those commands and use its existing path.

Then launch:

```bash
.venv/bin/python ide/quest.py --workspace ../questlab-blackjack
```

Quest Lab opens at:

```text
http://127.0.0.1:5173
```

The editor and terminals now operate inside `../questlab-blackjack`, while character/activity state is read from this platform checkout.

---

# Layout

```text
┌─────────────┬───────────────────────────────┬──────────────────────┐
│ FILES       │ EDITOR                        │ PYR / AI TERMINAL    │
│             │                               │                      │
│ resizable   │ Monaco                        │ Codex / Claude /     │
│             │                               │ Gemini CLI           │
│             ├───────────────────────────────┤                      │
│             │ NORMAL TERMINAL               │                      │
│             │ shell / run / git             │                      │
└─────────────┴───────────────────────────────┴──────────────────────┘
```

Drag the dividers between Files ↔ Editor, Editor ↔ AI, and Editor ↔ Terminal to resize them like an IDE.

The two terminal sessions are independent. Running Codex in the AI pane no longer steals the terminal you use for Python, Git, `pwd`, tests, etc.

---

# Normal session flow

1. Start Quest Lab with the worktree for the project you want to train on.
2. Open `HANDOFF.md` / `SESSION_NOTES.md` in the editor.
3. Use the right AI terminal for Codex / Claude / Gemini.
4. Let PYR teach the next rusty concept.
5. Enter Forge phase and code in Monaco.
6. Use **Pretty** / `Shift+Alt+F` when you want the current document formatted.
7. Press **Run**, or use the bottom terminal for fully interactive programs.
8. Use normal git commands in the bottom terminal:

```bash
git status
git add .
git commit -m "clear blackjack mob 1"
```

Because the terminals' working directory is the quest worktree, those commands act on the quest branch.

---

# Formatting vs VS Code extensions

Monaco is the editor core used by VS Code, but it is **not the VS Code extension host**. Normal `.vsix` extensions cannot simply be installed into this app.

For the formatter behaviour we want, Quest Lab integrates the underlying tools directly:

- `Ruff format` for Python;
- `Prettier` for web/text formats.

This gives the same practical "format my document" workflow without pulling the full VS Code extension runtime into Quest Lab.

If we eventually need arbitrary VS Code extensions, that becomes a different architecture choice such as embedding `code-server` / OpenVSCode Server rather than extending Monaco manually.

---

# Current architecture

```text
Browser — http://127.0.0.1:5173
│
├─ React + Vite
├─ Monaco editor
├─ xterm.js × 2
├─ resizable layout
└─ RPG HUD
      │
      │ /api + /ws
      ▼
FastAPI — http://127.0.0.1:7331
│
├─ safe file read/write
├─ format endpoint (Ruff / Prettier)
├─ git status / branch info
├─ progress/activity reader
└─ PTY shell per terminal connection
      │
      ▼
Selected quest worktree
```

The platform checkout (`QUESTLAB_REPO_ROOT`) and coding workspace (`QUESTLAB_WORKSPACE`) are deliberately separate.

---

# Security boundaries

The browser itself never receives arbitrary filesystem access.

The FastAPI server:

- binds to `127.0.0.1`;
- resolves every editor path underneath `QUESTLAB_WORKSPACE`;
- rejects `../` escapes;
- ignores `.git`, `node_modules`, virtual environments and build folders in the tree;
- limits editor reads/writes to UTF-8 text files under 2 MB.

The **terminals are different**: they are intentionally real shells. They have the same permissions as the user who launched Quest Lab. Do not expose port `7331` or the Vite dev server to untrusted networks.

---

# Next milestones

## Milestone 2 — PYR context bridge (implemented)

The local Forge now exposes a bounded, read-only context bridge at
`GET/POST /api/pyr/context`. The editor publishes the current selection and
the Submit Run enhancement captures the terminal tail through that bridge.
The response includes:

- active file;
- selected code;
- terminal error/output;
- git diff;
- current quest/mob/concept;
- assistance mode / Clean Clear state.

State files and secret-looking paths are excluded from git context, payloads are
bounded and ANSI-cleaned, and the bridge never mutates campaign state. The AI
must still follow `TUTOR_CONTRACT.md` and `LEARNING_PROTOCOL.md`; any reward or
combat mutation remains behind the controlled state service.

## Milestone 3 — in-app PYR chat

Add a provider adapter rather than hardcoding one vendor. Candidate adapters:

- local Ollama;
- OpenAI-compatible endpoints;
- Gemini API;
- CLI bridge where appropriate.

The chat should support Teach / Practice / Forge / Reference Mode explicitly and record any assistance penalties.

## Milestone 4 — quest/worktree manager

Let the UI create/open worktrees itself so choosing **Blackjack** from the quest tree automatically opens that branch's workspace.

## Milestone 5 — game feedback inside the IDE

- mob-clear overlays;
- XP/coin animations;
- shield cracking/repair visuals;
- hidden reward reveals;
- commit checkpoints;
- Rival Board / Dev Activity panels inside the IDE.

---

# Non-goal

This is not trying to become all of VS Code.

The target is the smallest environment needed for this campaign:

**Files · Editor · Terminal · PYR · Git · Quests · Character**

If a feature does not improve that loop, it probably does not belong in the first versions.
