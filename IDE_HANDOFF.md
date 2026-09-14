# Quest Lab IDE — Handoff

This branch starts the local browser IDE version of Python Quest Lab.

The public dashboard still lives on `main`. The IDE is **local-first**: your browser talks only to a FastAPI server bound to `127.0.0.1`, and that server is allowed to access one chosen quest workspace.

## Milestone 1 — implemented on this branch

The first usable slice contains:

- RPG / character stats loaded from `progress.json` and `activity.json`;
- Monaco editor (the editor core used by VS Code);
- file explorer scoped to one workspace;
- save + `Ctrl+S`;
- create-file flow;
- a **real PTY terminal** through xterm.js;
- Run button for the current Python file;
- current git branch / dirty-file count;
- quick terminal launch buttons for `codex`, `claude`, and `gemini` if those CLIs are installed;
- path sandboxing so the editor API cannot browse outside the selected workspace.

The terminal is intentionally real. Anything you type there runs with your local user permissions, just like opening your normal terminal. Keep the server bound to localhost.

---

# One-time setup

From the repo checkout containing this branch:

```bash
git switch feature/quest-lab-ide

python -m venv .venv
source .venv/bin/activate
pip install -r ide/server/requirements.txt

cd ide/frontend
npm install
cd ../..
```

## Recommended quest workspace: git worktree

The IDE platform and the project branch should not fight over the same checkout. Keep the IDE branch in this folder, then put the quest you are coding in a worktree next to it.

For Blackjack:

```bash
git fetch --all
git worktree add ../questlab-blackjack 01-blackjack
```

If that worktree already exists, skip the command and use its existing path.

Then launch:

```bash
source .venv/bin/activate
python ide/quest.py --workspace ../questlab-blackjack
```

Quest Lab opens at:

```text
http://127.0.0.1:5173
```

The editor and terminal now operate inside `../questlab-blackjack`, while character/activity state is read from this platform checkout.

---

# Normal session flow

1. Start Quest Lab with the worktree for the project you want to train on.
2. Open `HANDOFF.md` / `SESSION_NOTES.md` in the editor.
3. Let PYR teach the next rusty concept.
4. Enter Forge phase and code in Monaco.
5. Press **Run**, or use the terminal for fully interactive programs.
6. Launch your AI CLI inside the built-in terminal when needed:

```bash
codex
# or
claude
# or
gemini
```

7. Use normal git commands in the same terminal:

```bash
git status
git add .
git commit -m "clear blackjack mob 1"
```

Because the terminal's working directory is the quest worktree, those commits land on the quest branch.

---

# Current architecture

```text
Browser — http://127.0.0.1:5173
│
├─ React + Vite
├─ Monaco editor
├─ xterm.js
└─ RPG HUD
      │
      │ /api + /ws
      ▼
FastAPI — http://127.0.0.1:7331
│
├─ safe file read/write
├─ git status / branch info
├─ progress/activity reader
└─ PTY shell
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

The **terminal is different**: it is intentionally a real shell. It has the same permissions as the user who launched Quest Lab. Do not expose port `7331` or the Vite dev server to untrusted networks.

---

# Next milestones

## Milestone 2 — PYR context bridge

Give PYR structured context without copy/paste:

- active file;
- selected code;
- terminal error/output;
- git diff;
- current quest/mob/concept;
- assistance mode / Clean Clear state.

The AI must still follow `TUTOR_CONTRACT.md` and `LEARNING_PROTOCOL.md`.

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
