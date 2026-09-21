# Forge Quest Lab — Claude roadmap plan (2026-09-16 04:40 +02)

## Review boundary

Claude Sonnet performed a read-only synthesis of the current game snapshot,
roadmap, handoff, implementation report and issue log. It did not edit files,
run tests, mutate saves, sign in, write Supabase, start Tauri, restart a
runtime or touch either PTY. This plan is an implementation and evidence
ordering document, not approval for any hosted or destructive operation.

The current baseline is recorded in
`GAME_STATE_SNAPSHOT_2026-09-16_0438.md`. Local Slices 0–6 and the local
distribution foundation are implemented; later work must not blur fake-cloud
unit evidence into real hosted acceptance.

## Invariants for every remaining slice

1. `LocalStateService` is the only progression writer. The repository
   canonical save is authoritative locally; workspace `progress.json` remains
   legacy evidence only.
2. Meaningful mutations increment the canonical revision and append bounded
   `state_events`; React polls the cheap revision first and reloads the full
   projection only after a change.
3. Campaign keeps `tutor.py`. Practice remains an independent mode and cannot
   write Campaign, Dungeon, rewards, HP, Resolve or the Campaign notebook.
4. The state service decides rewards, Impact, Resolve, HP, unlocks, mastery and
   combat outcomes. React renders validated state/events only.
5. PTYs are long-lived. Browser acceptance is pure keyboard/mouse/scroll/type
   interaction through the browser; Playwright and refresh-as-verification are
   prohibited.
6. Hidden future questions and answers never reach the browser, Codex or
   provider context.
7. Never stage, overwrite, merge or delete the user's dirty `progress.json`
   or untracked root `tutor.py` without a separately approved custody action.
8. No Supabase migration/seed/sign-in, Tauri work, public deployment or social
   work is authorized by this plan.

## Current evidence split

| Area | Current status | Missing evidence or gate |
| --- | --- | --- |
| Slices 0–4 | Local gateway, campaign/boss, Codex, Character and Homestead are implemented and covered by 77 backend tests, 33 frontend tests, build and K&M | None locally; hosted verdict trust remains open |
| Slice 5 | Dungeon loop, durable checkpoint, blank editor, rest/market, death reset and local leaderboard are implemented and K&M verified | Hosted persistence F-018 |
| Slice 6 | Independent Practice sessions, mixed questions, optional help and validated history are implemented and K&M verified | No hosted cross-device history proof |
| Slice 7 local | Guarded launcher, runtime identity, package manifest, ext4 install proof and custody preview/migrate code exist | Real Windows friend-machine launch and F-039 custody choice |
| Milestones A–B | Schema, RLS and fake-cloud boundaries are committed and unit-tested | Never applied or tested against the linked Supabase project |
| Milestone C | Sync/CAS/device-provenance code is committed and fake-cloud tested | Real migration, linked RLS and two-device mailbox acceptance |
| Milestone D | Avatar validation/cache/storage boundary is committed | Real Storage upload, cross-device/offline and cross-account denial |
| Milestone E | Not started by design | Tauri sidecar, ConPTY/Windows PTY and clean shutdown proof |
| Milestone F | Not started by design | Public allowlist surface and deployment approval |
| Slice 8 | Not started by design | Friends/presence/privacy and two-account hosted proof |

## Dependency-ordered execution stages

### Stage A — close local distribution

This is the only remaining stage with no hosted dependency.

1. On a real second Windows machine or isolated Windows profile, run
   `tools/questlab-launch.ps1` from the intended checkout and prove branch,
   upstream SHA, canonical state path, backend readiness and both PTYs.
2. Record the F-039 operator decision: keep tracked `progress.json` as the
   offline cache, or explicitly approve the already-built opt-in
   `custody-migrate` path to an ignored per-device cache. Never choose by
   timestamp and never migrate implicitly.
3. If the Windows run exposes a defect, add a focused contract test before
   changing the launcher. Otherwise retain the current 9/9 launcher/HUD
   contract suite.

K&M acceptance: launch on the second Windows environment, observe the
branch-aware health contract, load Forge, submit one visible verified
objective, observe Resolve/reward projection without refresh, and keep shell and
AI labels `CONNECTED` throughout. Capture PIDs before and after. Do not kill
the existing stale 5174/7332 runtime as part of this work.

### Stage B — Milestone C hosted two-device acceptance

This is a hard approval gate. Before any write, the operator must explicitly
authorize the linked Quest Lab Supabase project and provide a real mailbox and
second device/profile.

1. Apply the committed profiles/devices, player-state, bounds and
   device-ownership migrations only to the intended project.
2. Run `supabase db lint --linked` and the executable profile/device,
   player-state and avatar-storage RLS suites against the real database.
3. Verify that hosted rows contain account/device identifiers only, never
   absolute filesystem paths.
4. On device A, change one allowlisted field and observe `local → syncing →
   synced`; on B observe the update without a refresh.
5. Take B offline, make an allowlisted change, reconnect and prove CAS conflict
   handling. Resolve one conflict with “Use cloud copy” and one with “Keep this
   device”; record revisions and final projections. Timestamp merging is not
   allowed.
6. Confirm HUD, Character, Homestead, Journal and Codex agree on the same
   revision and both PTYs survive every transition.

Automated evidence is the existing fake-cloud sync suite plus the linked SQL
suites. A real run must record timestamps, status transitions, conflict
summaries, revisions and account/device privacy observations. No local fixture
is a substitute for this gate.

F-001/F-010 provider-authenticated adjudication is a co-requisite: hosted
progress must not be presented as trustworthy while local AI-terminal verdicts
remain an unauthenticated trusted caller.

### Stage C — Milestone D hosted avatar

Only after Stage B is green, upload a bounded valid avatar on A, observe B
receive it without refresh, take B offline and confirm cached display, then
prove a second account cannot read or write the private object. Record actual
Storage calls and RLS denials; do not infer them from code or fixtures.

### Stage D — Milestone E Tauri desktop proof

Only after A–D are approved complete, add a thin Tauri shell around the
existing FastAPI sidecar. Test sidecar start/readiness/stop, workspace
selection, Monaco, Forge PTY, AI PTY, Campaign `tutor.py`, clean close and zero
orphan processes. Evaluate `pywinpty`/ConPTY only if native Windows packaging
requires it; do not rewrite the backend in Rust or add multiplayer.

K&M must launch the desktop window, type through the editor and both terminals,
perform one validated local state mutation, close the window and prove child
processes are reaped.

### Stage E — Milestone F safe public surface

After desktop proof, and only with explicit public-infrastructure approval,
ship only landing, auth, public-profile, download and help routes. Add an
allowlist test that proves PTY endpoints, filesystem APIs, private code/notes
and AI credentials are unreachable. K&M the deployed pages and reject guessed
private paths; do not publish by inference from local tests.

### Stage F — Slice 8 social layer

Last, after sync/avatar/privacy review: add opt-in friends, presence, party
join and hosted leaderboard projections with server-side authorization and
validated events. Add RLS tests and a two-account K&M privacy run. Keep raid
combat/rewards out of this slice until a separate design and authority review.

## Review loop for every stage

1. Read the current issue log and relevant contract.
2. Add focused tests with each implementation change.
3. Run focused tests, the full WSL backend/frontend suites, Python compile and
   the Windows production build as applicable.
4. Launch a branch-matched disposable runtime and pass the read-only
   `tools/questlab-km-preflight.ps1` gate.
5. Perform K&M only: click, scroll, type and observe; never refresh to stand in
   for polling and never reset a PTY.
6. Record before/after revision, validated event/reward text, all player-facing
   projections, PTY labels and process custody in
   `FORGE_ROADMAP_ISSUES_LOG.md` and
   `CLOUD_DESKTOP_IMPLEMENTATION_REPORT.md`.
7. Request read-only Claude/second-reviewer review, fix concrete findings,
   commit semantic files only, and push a green checkpoint.

## Explicit stop conditions

The current work can proceed through local Stage A only if a second Windows
environment is available. Stage B requires explicit Supabase authorization,
Stage C depends on B, Stage D depends on A–D, Stage E requires public
deployment approval, and Stage F requires all earlier privacy gates. Until
those approvals/evidence exist, claiming the full roadmap complete would be
unsupported.
