# Forge game snapshot — 2026-09-15

This is a persistent baseline for the full-roadmap pass. It records what was
confirmed before the next implementation slice, what is deliberately still
open, and which worktree/runtime is serving the visible app.

## Source baseline

- Branch: `feature/cloud-sync-desktop`
- Local and remote HEAD at snapshot time: `ddb7fed2eff7c10bea385a76083725f84b34579b`
- Canonical checkout: `/mnt/c/Users/lazar/OneDrive/Documents/ChatGPT/Python Quest Lab`
- The checkout contains user-owned working-tree state in `progress.json` and an
  untracked root `tutor.py`. Neither is to be staged, overwritten, or treated
  as disposable test data.
- No Supabase seed, sign-in flow, legacy `progress.json`, or Lazi OS files were
  touched for this snapshot.

## State observed (read-only)

The canonical working-tree save currently contains the previously reconciled
Blackjack evidence: Level 2, 50 current XP, 150 lifetime XP, 55 coins, and
three defeated mobs. The next active mob is The Hitman. This is an observation,
not a new mutation in this snapshot.

## Runtime map

The visible long-lived Forge remains the user's existing runtime on port 5173:

- frontend: `/home/lazi/projects/python-tutorial-DiddyDungeon` on
  `feature/quest-lab-ide`, port 5173;
- backend: port 7332;
- shell and AI PTYs: existing sessions (PIDs 111021/111022 and their terminal
  children) retained.

The current `feature/cloud-sync-desktop` checkout is available separately for
verification on port 5174/backend 7333. Disposable browser test runtimes may
also exist, but they are not player state authorities.

## Confirmed surfaces at baseline

- controlled local state gateway and revision-aware campaign polling;
- live HUD, Character, Homestead, Quest Journal and Codex projections;
- queued state-service reward/event notifications;
- Campaign Tutor Notebook (`tutor.py`) kept separate from the independent
  Practice mode;
- Battle submission/verdict boundary with canonical Resolve, HP, Codex attempt
  and mob-clear mutations;
- Infinite Dungeon checkpoint foundation with controlled `dungeon.py`
  projection, blank-on-question-rotation and reset-on-death rules;
- monochrome SVG top-stat icons, with direct-child stat-pill selectors;
- local cosmetic purchase/equip flow and account-scoped sync scaffolding.

The prior verification record reports 39 WSL backend tests, 24 frontend source
tests, a passing Windows Vite build, and a manual browser K&M check showing
live revision updates while both PTYs stayed connected. Those claims are the
baseline evidence and will be rerun at milestone checkpoints.

## Known open gates

- the visible launcher/runtime still points at the older checkout (roadmap
  issue F-025), so the latest branch UI is not automatically what port 5173
  serves;
- provider-authenticated Battle adjudication, hosted sync acceptance, and
  multi-tab challenge isolation remain release gates;
- Dungeon question/verdict generation, rest/market rooms, death UI, scoring,
  leaderboard and Practice history are not yet complete;
- next-project selection, boss interview/clear flow, Codex library depth,
  Homestead presentation, friend onboarding and hosted multiplayer remain
  roadmap work.

## Unverified draft in the worktree

The next campaign slice has been drafted but not yet tested or committed:
finishing the mob sequence opens a state-service-owned boss gate, and the
internal `record_boss_clear` command requires separate behaviour, explanation
and interview evidence before awarding the documented +100 XP boss reward.
This draft is intentionally not represented as a completed boss clear.

## Safety boundary

All progression writes must continue through the canonical state service. A
legacy/workspace `progress.json` is evidence only, never a second save. Browser
verification must use keyboard/mouse automation only; Playwright is excluded.

