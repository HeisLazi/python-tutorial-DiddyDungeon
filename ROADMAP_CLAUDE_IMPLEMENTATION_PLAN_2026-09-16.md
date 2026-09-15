# Forge Quest Lab — Claude roadmap implementation plan

**Review date:** 2026-09-16  
**Reviewer:** Claude Sonnet (read-only)  
**Working branch:** `feature/cloud-sync-desktop`  
**Source checkpoint:** `4a494b5`  
**Input evidence:** `AGENT_CLOUD_DESKTOP_HANDOFF.md`,
`ROADMAP_EXECUTION_PLAN.md`, `FORGE_ROADMAP_ISSUES_LOG.md`,
`CLOUD_DESKTOP_IMPLEMENTATION_REPORT.md`,
`GAME_STATE_SNAPSHOT_2026-09-16_0134.md`, `INFINITE_DUNGEON_DESIGN.md`,
and the current backend/frontend source and tests.

Claude performed this pass read-only: no files were edited, no mutating
commands were run, and no Playwright was used. This plan is a dependency- and
evidence-ordered execution record, not a claim that every roadmap gate is
complete.

## Non-negotiable invariants

1. `LocalStateService` in `ide/server/state.py` is the only progression writer;
   the repository-root canonical cache is authoritative and workspace
   `progress.json` is legacy evidence only.
2. Every meaningful mutation increments the canonical revision and appends a
   bounded `state_events` record. React checks the cheap revision endpoint and
   reloads projections only on revision change.
3. Campaign keeps its collaborative `tutor.py`; Practice is a separate mode
   and cannot write Campaign, Dungeon, rewards, HP, Resolve or `tutor.py`.
4. Rewards, Impact, Resolve, HP, unlocks, mastery and combat outcomes are
   validated by the state service. React renders validated state/events and
   never invents progression.
5. PTY sessions remain long-lived. Browser acceptance is mouse/click,
   scroll and typing only; Playwright is prohibited.
6. Hidden future questions and answers never reach the browser, Codex or
   provider context.

## Open issues and their disposition

| ID | Priority | Current disposition | Required action |
|---|---:|---|---|
| F-001 | P1 | Provider identity is not authenticated. | Keep as a hosted/provider-auth release gate; do not pretend a local AI verdict is proof. Close only with provider-authenticated adjudication. |
| F-010 | P2 | Loopback API has no hosted user authentication. | Keep strict loopback binding. Close only with provider/account authentication; do not weaken local boundaries. |
| F-018 | P2 | Dungeon persistence/leaderboard are not in hosted player state. | Add only after Milestone C two-device state acceptance. |
| F-025/F-031 | P2 | A legacy 5173 runtime can serve a stale checkout. | Do not kill existing PTYs automatically. Use the guarded launcher and health/branch diagnostics for new launches; a restart choice remains with the user. |
| F-033 | P2 | Shared OneDrive Windows dependencies are unsafe for WSL. | Keep the fail-fast launcher and onboarding instruction to run `npm ci` in a native Linux/WSL checkout. No source workaround is needed. |
| F-035 | P3 | HMR can reconnect a disposable terminal during edits. | Treat as a development-loop caveat; use the built/started runtime for acceptance. |
| F-039 | P2 | Tracked `progress.json` plus OneDrive is a third writer. | Keep custody migration explicit and opt-in; never move or merge the player's save silently. |
| F-050 | P3 | Monaco 0.56.0 reports one low and one moderate DOMPurIFY advisory. | Decision recorded: retain 0.56.0 as accepted risk; reject 0.53.0 because its vendored DOMPurIFY is older 3.1.7 and only invisible to npm audit. Revisit when upstream bundles >3.4.12 or a reviewed patch is available. |

These are not all bugs to “fix” locally. F-001, F-010, F-018, F-039 and the
hosted portions of F-025 are approval/acceptance gates. No social, hosted
Dungeon, public web or Tauri work should leapfrog them.

## Recommended execution order

### Stage 0 — Snapshot, plan and review ledger

**Status:** completed for this checkpoint.

- Preserve `GAME_STATE_SNAPSHOT_2026-09-16_0134.md` and the persistent issue
  log before changing code.
- Record branch, remote HEAD, canonical revision/state, runtime PIDs/ports,
  dirty player files, test counts and the exact browser policy.
- Obtain a read-only Claude plan/review, then convert it into this file.
- Commit the snapshot/plan separately from implementation slices.

**Tests/evidence:** read-only JSON/state inspection, `git status`, runtime
socket/PID inspection, and issue-log links. No state mutation or restart.

### Stage 1 — Re-run the local authority and projection gates

**Status:** implemented and verified; re-run after every later backend change.

**Source/test areas:** `ide/server/state.py`, `ide/server/app_v2.py`,
`ide/server/test_state_service.py`, `test_progress.py`,
`test_context_bridge.py`, `ide/frontend/src/AppV2.jsx`, `RpgViews.jsx`,
`syncEngine.js` and their tests.

**Automated tests:**

- workspace-file edits do not change canonical revision, events, HUD or cloud
  projection;
- actor scope rejects player/PYR attempts to call system-only mutations;
- revision/event polling reloads projections without remounting Monaco or
  either PTY;
- rewards, Resolve, mob unlocks, Codex records and Homestead coins come only
  from gateway mutation results;
- stale revisions/conflicts fail closed.

**K&M gate:** start a disposable current-branch runtime from a copied save;
observe the initial Level/XP/coins/mob, trigger one trusted state-service
reward, and confirm the HUD, Character and Homestead change without refresh.
Open Quest Journal and Codex and confirm their revision/projection agrees;
assert shell and AI PTYs remain `CONNECTED`. Log before/after AX-visible text,
runtime branch and exact disposable paths.

**Checkpoint:** focused tests → full WSL backend/frontend suites → Python
compile → Windows production build → K&M smoke → Claude/self review →
`system:` or `test:` commit. Never stage `progress.json` or root `tutor.py`.

### Stage 2 — Campaign/Boss/Codex/Homestead completion gate

**Status:** local mechanics done/verified.

**Source/test areas:** canonical encounter/objective/boss-clear handlers in
`state.py`; challenge routes in `app_v2.py`; Quest Journal, Codex, Character
and Homestead projections in `RpgViews.jsx`.

**Required regression coverage:**

- a correct objective applies predefined Impact and reduces Resolve;
- an incorrect verified action applies only canonical counterattack/HP;
- a mob clear emits validated XP/coins, unlocks only the next allowed mob and
  creates/updates its Codex encounter;
- boss clear rejects fewer than all required behaviour/explanation/interview
  evidence records and derives rewards server-side;
- notes are bounded/sanitized, cannot write arbitrary JSON paths and never
  expose future answers;
- equipment purchases/equips reject insufficient funds and update the same
  revision as the HUD/Homestead projection.

**K&M gate:** with an active mob, submit a visible verified objective, observe
Resolve decrease; complete the mob; observe reward queue, next encounter and
Codex growth with no refresh. Visit Character/Homestead and confirm the same
revision. Keep both PTYs alive. Boss K&M is separate: verify all three
evidence types before the gate clears; never display hidden future prompts.

No additional local mechanic should be added unless a new defect appears;
these gates are already recorded as passing in the current issue log.

### Stage 3 — Infinite Dungeon and Practice local gate

**Status:** local mechanics done/verified; hosted persistence deliberately
gated by F-018.

**Dungeon tests:** fresh starter loadout; durable checkpoint/restart; stale
question rejection; blank editor on every rotation; provider-bound verdict;
progressive code/bug-hunt/true-false rooms; adaptive focus from recorded
weakness; REST heal rules; MARKET purchase/equip; death/new-run reset; local
leaderboard; no Campaign rewards or hidden answer leakage.

**Practice tests:** concept selection, mixed question types, bounded sessions,
optional AI help, attempts/results/history; explicitly reject Campaign,
Dungeon, `tutor.py`, HP, Resolve and reward writes.

**K&M gate:** click Infinite Dungeon, type/checkpoint an answer, verify a blank
editor after rotation, reach REST/MARKET, purchase, bank or die, and repeat a
new run. Separately use Practice repeatedly with a selected concept and
confirm the Campaign/Dungeon HUD does not change. Record room, score, run
coins, and PTY connection evidence.

### Stage 4 — Local distribution and F-050 decision

**F-033 documentation:** confirm `FRIEND_ONBOARDING.md` tells friends to use a
native Linux/WSL checkout and run `npm ci` there, never reuse OneDrive's
Windows `node_modules`. Keep the guarded launcher fail-fast behavior.

**F-050 decision record:**

1. The baseline `npm audit --omit=dev`, frontend suite and build were captured
   for Monaco 0.56.0.
2. A disposable 0.53.0 archive passed tests/build and reported zero audit
   findings, but tarball inspection found its inline DOMPurIFY at 3.1.7; this
   is a metadata blind spot, not a fix.
3. Claude recommended and the branch recorded retaining 0.56.0 as an explicit
   low/moderate accepted risk. Never run `npm audit fix --force` or downgrade
   the editor merely to make the scan quiet.
4. Reopen this gate only for an upstream Monaco bundle above 3.4.12 or a
   separately reviewed sanitizer patch, then rerun frontend/build/K&M editor
   acceptance before changing the lockfile.

**Distribution K&M gate:** use the committed-HEAD-only package, clean ext4
install and guarded launcher. Confirm branch identity, Level/XP/coins, both
`CONNECTED` PTYs, live gateway reward and no dirty save/notebook bytes in the
bundle. This is local proof only, not Windows installer/Tauri proof.

### Stage 5 — Milestone C: hosted two-device player-state acceptance

**Gate:** requires the account owner's mailbox confirmation and a second real
device or genuinely isolated signed-in profile. Do not start Dungeon hosted
transport or social work before this passes.

**Dependencies/source:** existing `syncEngine.js` boundary, auth/profile/device
surface, `supabase/migrations/20260915000100..300_player_state*.sql`, RLS tests
and conflict UI. Keep synced scope bounded to identity/progression, HP/max HP,
armor/trinket/title, companion and Homestead ownership/equipped cosmetics.

**Eight-step acceptance:**

1. Sign into the same account on Device A and B; verify profile/device rows
   are private and no absolute filesystem path is stored.
2. Change an allowed field on A; observe local projection and `syncing` then
   `synced` status.
3. Observe B receive the newer state without a full browser refresh where the
   poll contract permits it.
4. Take B offline, make an allowed local change, and confirm Forge remains
   usable with local status.
5. Reconnect B; verify compare-and-swap conflict handling, never newest-
   timestamp merge or silent overwrite.
6. Resolve one conflict with **Use cloud copy** and a separate run with
   **Keep this device**; record revisions and final projections.
7. Confirm both PTY sessions remain connected throughout.
8. Capture status/revision/AX evidence in the issue log and implementation
   report.

**Automated tests:** current fake-cloud engine/RLS tests remain required; add
   only the regression exposed by the real two-device run. Do not expand the
   synced domain until this gate is green.

### Stage 6 — Milestone D: hosted avatar acceptance

Run after C using the same two-device setup. Upload a bounded valid avatar on
A, verify B receives it, take B offline and verify the cached avatar remains,
then confirm a second account cannot read/write the private object. Log RLS
denial and offline-cache evidence. Do not expose private avatar paths.

### Stage 7 — Milestone E: Tauri desktop proof

Start only after A–D hosted acceptance is stable. Add a bounded `src-tauri/`
shell that manages the existing FastAPI sidecar; do not rewrite the backend in
Rust and do not add multiplayer here.

**Tests:** sidecar start/readiness/stop, clean shutdown of backend and both
PTY children, selected workspace, local Monaco workers, Campaign `tutor.py`,
and zero orphan processes after window close.

**K&M gate:** launch the desktop window, type in Monaco and Tutor, verify Forge
and AI PTYs, close the window, then inspect the process list. Record screenshots
and before/after PIDs. Any lifecycle leak blocks the milestone.

### Stage 8 — Milestone F: safe web/Vercel surface

Only after auth/profile foundations and explicit approval to provision public
infrastructure. Implement only landing/auth/public-profile/download/help
surfaces. Add an automated route/asset audit proving no PTY, filesystem or AI
credential route is reachable. K&M the deployed pages and confirm no terminal
or file-editing surface exists. Do not publish without explicit approval.

### Stage 9 — Hosted social layer / Slice 8

Last, after C/D, privacy review and the public-surface boundary. Add opt-in
friends/presence/weekly raids/leaderboards with server-side authorization and
validated events. Do not scaffold raid mechanics early. A named privacy
reviewer other than the implementing agent must sign off.

## Per-stage evidence and review loop

For every implementation stage:

1. Read the relevant handoff/design/issue entry.
2. Add or update focused tests with the implementation.
3. Run focused tests, full WSL backend/frontend suites, Python compilation and
   Windows Vite build as applicable.
4. Run a disposable K&M test with click/scroll/type only; do not refresh as a
   substitute for live polling and never reset/remount either PTY.
5. Record the before/after state, revision, event/reward text, PTY labels,
   process custody and any failure in `FORGE_ROADMAP_ISSUES_LOG.md` and the
   implementation report.
6. Request Claude/Sonnet and, when available, a second reviewer (z.ai or
   OpenCode) in read-only mode; resolve concrete findings before the green
   checkpoint.
7. Commit semantic files frequently, push, and verify remote HEAD. Never stage
   the user's dirty `progress.json` or untracked Campaign `tutor.py`.

## Definition of done

- **Slices 0–6:** canonical authority, validated event/reward projection,
  live HUD/Character/Homestead/Journal/Codex, Campaign Tutor separation,
  Dungeon/Practice local loops and K&M evidence all green.
- **Slice 7 local:** F-033 onboarding/launcher contract green and F-050
  dependency choice explicitly recorded; friend clean-install proof green.
- **Milestone C:** real two-device authenticated sync/conflict acceptance,
  including both explicit conflict resolutions and PTY survival.
- **Milestone D:** cross-device/private/offline avatar proof.
- **Milestone E:** desktop window with Monaco, both PTYs, Tutor, sidecar and
  clean shutdown with no orphan processes.
- **Milestone F:** deployed safe web surface with route audit excluding PTY,
  filesystem and AI credentials.
- **Slice 8:** authenticated multi-user tests and named privacy sign-off.

The current checkpoint satisfies the first local blocks but is not yet a
complete roadmap release: the hosted two-device acceptance is the critical
next external gate, and F-050 remains an explicit local compatibility choice.
