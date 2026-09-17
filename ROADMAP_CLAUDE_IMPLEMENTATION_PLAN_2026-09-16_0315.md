# Forge Quest Lab — Claude roadmap implementation and verification plan

**Review date:** 2026-09-16  
**Reviewer:** Claude Sonnet (read-only review)  
**Applied checkpoint:** `feature/cloud-sync-desktop` at
`82eae1783d4e0dba67d06547f58d4a8b7413b534`  
**State snapshot:** `GAME_STATE_SNAPSHOT_2026-09-16_0315.md`, canonical revision 2

Claude read the snapshot, roadmap, handoff, implementation report and issue
ledger in read-only mode. It did not edit files, mutate state, run migrations,
restart a runtime or touch either PTY. This document turns that review into a
dependency-ordered execution and evidence plan; it is not a claim that every
gate is complete.

## Non-negotiable invariants

1. `LocalStateService` remains the only progression writer. The repository
   canonical cache is authoritative; the quest workspace `progress.json` is
   legacy evidence only.
2. Every meaningful mutation increments the canonical revision and appends a
   bounded `state_events` entry. React checks the cheap revision endpoint and
   reloads projections only when the revision changes.
3. Campaign keeps its collaborative `tutor.py`. Practice is a separate,
   unlimited learning mode and cannot write Campaign, Dungeon, rewards, HP,
   Resolve or `tutor.py`.
4. The state service decides rewards, Impact, Resolve, HP, unlocks, mastery and
   combat outcomes. React renders validated state/events and never recomputes
   progression.
5. PTYs are long-lived. Browser acceptance is pure accessibility/K&M
   click, scroll and typing with **no Playwright**, no refresh as a substitute
   for polling, and no PTY reset/remount.
6. Hidden future questions and answers never reach the browser, Codex or a
   provider context.
7. Never stage, overwrite, merge or delete the user's dirty `progress.json` or
   untracked root `tutor.py` without a separately approved custody action.

## Current status from the snapshot and issue ledger

| Area | Status | Evidence / remaining gate |
| --- | --- | --- |
| Slices 0–4: gateway, campaign/boss, Codex, Character/Homestead | Implemented locally | 76 backend tests, 33 frontend tests, build and branch-aware K&M evidence |
| Slice 5: Infinite Dungeon | Implemented locally | Durable local run, rooms, rest/market, death reset and leaderboard are tested/K&M; hosted persistence is F-018 |
| Slice 6: Practice | Implemented locally | Independent mixed-question sessions and provider-validated history; mode-boundary tests/K&M are green |
| Slice 7: local distribution | Mostly implemented | Launcher, runtime identity, onboarding, packaging and ext4 clean-install proof; real Windows friend-machine and hosted mailbox remain |
| F-025/F-035 | Open dev/runtime risk | Stale mounted Vite/HMR is disclosed; read-only preflight rejects stale evidence but does not kill existing PTYs |
| F-033 | Bounded open risk | Shared OneDrive `node_modules` is unsafe for WSL; native Linux/WSL install and fail-fast launcher are required |
| F-039 | Explicit approval gate | Tracked canonical `progress.json` plus OneDrive third writer; custody migration is opt-in only |
| Milestone C | Not accepted | Hosted two-device player-state acceptance and unapplied device-ownership migration remain |
| Milestone D | Code boundary present, live proof missing | Hosted avatar upload/download, offline cache and cross-account denial remain |
| Milestone E | Not started | Tauri proof is explicitly after A–D |
| Milestone F | Not started | Safe public/Vercel surface is deferred until exposure review |
| Slice 8 social layer | Intentionally last | Presence, friends, raids and hosted leaderboard wait for authenticated sync/privacy gates |

## Ordered implementation and verification stages

### Stage 0 — Snapshot, plan and review ledger

**Status: complete for this checkpoint.** Preserve the snapshot, current branch
and remote SHA, canonical revision/authority, runtime ports, dirty-file
boundary, test counts and browser policy before every later slice. Keep this
plan and the issue ledger in the repository, never in a temporary directory.

**Evidence:** read-only endpoint/CLI state capture, `git status`, runtime socket
inspection, Claude review text, and a dedicated commit. No save mutation or
restart is part of this stage.

### Stage 1 — Local authority and live projection regression gate

**Status: implemented; rerun after any backend/frontend mutation.**

**Automated tests:**

- direct workspace-file edits do not alter canonical revision, events, HUD or
  cloud projection;
- actor scope rejects player/PYR calls to system-only mutations;
- revision polling reloads projections without remounting Monaco, Forge PTY or
  AI PTY;
- validated rewards, Resolve reduction, next-mob unlock, Codex creation and
  Homestead coin changes come only from gateway mutation results;
- stale revisions/conflicts fail closed;
- `test_launcher_contract.py` keeps the read-only K&M preflight free of POST,
  fetch, deletion and restart behavior.

**K&M stage:** start a disposable branch-matched runtime, run
`tools/questlab-km-preflight.ps1`, capture initial `SYNCING` → ready text, apply
one valid state-service objective, and observe HUD/Character/Homestead changes
without refresh. Open Journal and Codex and confirm the same revision/event
projection. Record Resolve before/after, reward text, next encounter and both
PTY labels. Close only the disposable runtime; leave long-lived PTYs intact.

**Green checkpoint:** focused tests → full WSL backend/frontend suites → Python
compile → Windows Vite build → K&M → read-only Claude/second review → commit;
never stage user save/notebook files.

### Stage 2 — Campaign, boss, Codex and Homestead completion gate

**Status: local mechanics implemented and locally verified.** Keep these
regressions permanently green:

- a correct objective applies only its predefined Impact and immediately
  reduces Resolve;
- an incorrect verified action applies only canonical counterattack/HP;
- a mob clear emits validated XP/coins, unlocks only the next allowed mob and
  creates/updates its Codex record;
- a boss clear rejects missing behaviour/explanation/interview evidence and
  derives rewards server-side;
- notes are bounded/sanitized and cannot write arbitrary JSON or reveal future
  answers;
- insufficient-fund purchases/equips fail, while a valid purchase updates the
  same revision consumed by HUD, Character and Homestead.

**K&M stage:** with an active mob, submit one visible verified objective and
observe Resolve decrease; complete the mob and observe reward queue, next
encounter, Journal, Codex, Character and Homestead without refresh. Keep a
separate boss proof behind the provider-auth boundary; do not reveal future
boss prompts.

### Stage 3 — Infinite Dungeon and Practice local gate

**Status: local mechanics implemented; hosted persistence is F-018.**

Dungeon automated coverage must include fresh starter loadout, durable floor/
room/question/editor checkpoint, stale-question rejection, blank editor on
every rotation, provider-bound verdicts, progressive code/bug-hunt/true-false
rooms, adaptive recorded-weakness focus, REST heal rules, MARKET purchase,
death/new-run reset, local leaderboard, no Campaign rewards, and no hidden
answer leakage.

Practice automated coverage must include concept selection, mixed question
types, bounded sessions, optional AI help, attempts/results/history, and hard
rejection of Campaign/Dungeon/`tutor.py`/HP/Resolve/reward writes.

**K&M stage:** click Infinite Dungeon, type and checkpoint an answer, observe a
blank editor after rotation, exercise REST/MARKET, bank or die, and start a
fresh run. Separately use Practice repeatedly with a selected concept and
confirm Campaign/Dungeon HUD and `tutor.py` do not change. Record room, score,
run coins, reset behavior and connected PTYs.

### Stage 4 — Local distribution, runtime drift and dependency gate

Keep the guarded launcher branch/upstream refusal, runtime identity, native
WSL dependency instructions, package manifest and ext4 clean-install proof.
Add only bounded regressions for deliberately stale checkout/runtime health and
the documented Rollup remediation. Do not attempt to solve OneDrive's
third-writer problem with timestamp merges.

**K&M stage:** package committed HEAD only, install in a clean ext4/WSL root,
run the launcher, pass the preflight, verify starter/canonical identity,
connected shell/AI PTYs, a gateway reward and exclusion of dirty save/notebook
bytes from the package. A real Windows friend-machine launch remains a later
acceptance requirement, not implied by an ext4 smoke test.

### Stage 5 — Milestone C: hosted two-device player-state acceptance

**Hard gate; not run without explicit approval.** First apply and prove the
committed device-ownership migration against the intended Quest Lab Supabase
project. Run linked SQL/RLS tests only after authorization; do not touch any
other project and do not claim local fixtures are hosted evidence.

**Required hosted K&M sequence (two real devices or genuinely isolated signed-
in profiles, click/scroll/type only):**

1. Sign into the same account on A and B; verify private profile/device rows
   contain no absolute filesystem paths.
2. Change one allowed field on A through normal UI and observe local
   `local → syncing → synced` status.
3. Observe B receive it without a manual refresh.
4. Take B offline, make an allowed local change, and keep Forge usable.
5. Reconnect B; verify compare-and-swap conflict handling, never newest-
   timestamp merging or silent overwrite.
6. Resolve one conflict with **Use cloud copy** and another with **Keep this
   device**, recording both revisions and final projections.
7. Confirm HUD/Character/Homestead/Journal/Codex remain coherent and both PTYs
   stay connected throughout.
8. Record timestamps, status transitions, conflict summaries, revision values,
   and the exact issue/report evidence.

**Automated gate:** rerun fake-cloud sync-engine tests and linked RLS tests;
add only regressions exposed by the real run. Keep synced scope bounded to the
approved identity/progression, HP, equipment, companion and Homestead fields.

### Stage 6 — Milestone D: hosted avatar acceptance

Only after Stage 5 is green: upload a bounded valid avatar on A, observe B
receive it, take B offline and confirm cached display, then prove a second
account cannot read/write the private object. Record upload, cross-device,
offline-cache and RLS-denial evidence. Do not expose private paths.

### Stage 7 — Milestone E: Tauri desktop proof

Only after A–D are stable. Add a thin Tauri shell around the existing FastAPI
sidecar; do not rewrite the backend in Rust or add multiplayer. Add tests for
sidecar start/readiness/stop, selected workspace, clean shutdown/reaping of
backend and both PTY children, and zero orphan processes. K&M must launch the
desktop window, preserve Monaco/Forge/AI/Campaign `tutor.py`, and prove process
cleanup after close using before/after PID evidence.

### Stage 8 — Milestone F: safe web/Vercel surface

Only after explicit public-infrastructure approval. Keep the surface limited to
landing/auth/public-profile/download/help. Add a route/asset allowlist test
proving PTY, filesystem, private code, notes and AI credentials are unreachable.
K&M the deployed pages and verify public fields only; do not publish by
inference from local tests.

### Stage 9 — Slice 8 hosted social layer

Last, after sync/avatar/privacy review. Add opt-in friends, presence, party
join and hosted leaderboard projections with server-side authorization and
validated events. Add RLS tests proving User A cannot read/write User B's
presence/party rows and a two-account K&M privacy run. Do not add raid rewards
or client-trusted competition state.

## Review and checkpoint loop

For each implementation slice:

1. Read its handoff/design and open issue entries.
2. Add focused tests with the change.
3. Run focused tests, the full WSL backend/frontend suites, Python compile and
   Windows production build as applicable.
4. Launch a disposable branch-matched runtime and run the read-only preflight.
5. Perform manual K&M only: accessibility state, click, scroll and typing;
   no Playwright, refresh or PTY reset.
6. Record before/after revision, validated event/reward text, visible surface
   agreement, PTY labels, process custody and failures in the issue log/report.
7. Request Claude Sonnet and any available second reviewer in read-only mode;
   fix concrete findings, then commit/push semantic files only.

## Immediate next action

The local snapshot/plan/preflight gates are green. The next *code-safe* work is
limited to any newly observed local regression in Stages 1–4; no broad gameplay
rewrite is justified by the current evidence. The next hosted action would be
Stage 5's device-ownership migration and two-device acceptance, but it remains
blocked pending explicit authorization to write the linked Supabase project and
the operator's custody decision for F-039. Do not sign in, migrate the real
save, seed Supabase, start Tauri or begin Slice 8 implicitly.
