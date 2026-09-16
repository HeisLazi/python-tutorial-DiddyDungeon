# Forge Quest Lab — Claude Sonnet roadmap plan (2026-09-16 07:05 +02)

## Review boundary

Claude Sonnet performed a read-only review of the current handoff, roadmap,
implementation report, issue log, 07:05 game snapshot, source and tests. It
did not edit files, run mutating commands, start or stop runtimes, sign in,
write Supabase, touch Tauri, or change `progress.json`, `tutor.py` or either
PTY. This is a dependency and evidence plan, not authorization for hosted or
destructive work.

## Findings

- **F-R1 (P3 documentation precision):** the public `/api/state/apply`
  envelope accepts only `player` and `pyr`; `system` is internal-only and
  cannot be supplied over HTTP. Documentation should say that clearly rather
  than imply a callable system HTTP actor.
- **F-R2 (P3 documentation precision):** Campaign keeps one gated
  workspace-scoped `tutor.py`; Practice and Dungeon never call that endpoint.
  The effective mode boundary is real, but it is not a second Practice file.
- **F-R3 (P2 boundary documentation):** `.github/workflows/sync-activity.yml`
  is the only CI automation with `contents: write` and `GITHUB_TOKEN`. It
  writes only public `activity.json`/`README.md` to `main`; add that automation
  boundary and keep the token scope minimal in the handoff and issue log.
- **F-R4 (P3 known risk):** the guarded launcher fetches `origin` by default;
  `-AllowStaleCheckout` is the documented offline opt-out. No new defect was
  found.

## Evidence ledger

| Area | Proven locally | Missing evidence/gate |
| --- | --- | --- |
| Canonical state | Sole `REPO_ROOT/progress.json` writer, workspace-file rejection, revisions/events and cheap revision polling | None locally |
| Live RPG projection | One revision poll drives HUD, Character, Homestead, Journal and Codex; no PTY/Monaco remount; validated event-only rewards | Hosted cross-device projection continuity |
| Campaign/Boss/Codex/Homestead | State-service actions, objective Resolve, mob unlocks, Codex records, bounded notes and purchases | Provider-authenticated adjudication (F-001/F-010) |
| Dungeon | Durable `dungeon_run`, question-bound checkpoints, blank rotation, rest/market, death reset and leaderboard | Hosted persistence (F-018) |
| Practice | Independent history/questions and no Campaign/Dungeon/reward/notebook writes | Hosted Practice history |
| Local distribution | Guarded launcher, branch/runtime identity, dependency preflight, committed-HEAD bundle and ext4 proof | Real second-Windows launch; F-039 custody decision |
| Hosted sync/avatar | Bounded allowlists, CAS/conflict policy, outbox, device provenance and avatar validation are implemented and fake-cloud tested | Linked migrations/RLS, real mailbox/two-device and Storage acceptance |
| Tauri/public/social | Explicitly not started by design | Approval-gated implementation and K&M evidence |

## Dependency-ordered execution plan

### Stage A — close local distribution

On a real second Windows machine or isolated profile, run
`tools/questlab-launch.ps1` and prove branch/upstream identity, canonical path,
backend readiness, both PTYs and one no-refresh gateway mutation. Capture PIDs
before and after. Record the explicit F-039 decision to retain the tracked
cache or opt into the already-built per-device custody migration; never use a
timestamp or implicit copy. Add a focused launcher regression only if the
second environment exposes a defect.

### Stage B — hosted two-device sync (Milestone C)

Only after explicit authorization of the linked Supabase project, mailbox and
second device/profile: apply the committed migrations, run linked lint and
profiles/devices/player-state/avatar RLS suites, verify no absolute paths in
hosted rows, exercise an allowlisted update A→B, make B offline, reconnect and
prove both explicit CAS conflict resolutions. Confirm one revision across
HUD/Character/Homestead/Journal/Codex and both PTYs. Keep F-001/F-010 open until
provider-authenticated adjudication is separately proven.

### Stage C — hosted avatar (Milestone D)

After Stage B is green, upload a bounded avatar on A, observe B update without
refresh, verify offline cache, and prove a second account cannot read or write
the private object using the linked Storage RLS suite.

### Stage D — Tauri desktop proof (Milestone E)

After A–D approvals, add a thin Tauri shell around the existing FastAPI sidecar
rather than rewriting the backend. Prove workspace selection, Monaco, Campaign
`tutor.py`, Forge and AI PTYs, one validated mutation, clean close and zero
orphan processes. Evaluate ConPTY/`pywinpty` only if native packaging requires
it.

### Stage E — safe public surface (Milestone F)

With explicit deployment approval, ship only landing, auth, public profile,
download and help routes. Add an allowlist test proving PTY, filesystem,
private-code/notes and AI-credential paths are unreachable. Review the CI
activity writer as part of the public boundary.

### Stage F — social layer (Slice 8)

Last, after sync/avatar/privacy review, add opt-in friends, presence, party
join and hosted leaderboard projections with server authorization, RLS tests
and a two-account K&M privacy run. Keep weekly raid combat and rewards out of
this slice.

## Required review loop

For each stage: read the issue log and contract, add focused tests, run the
full backend/frontend/compile/build gates, launch a branch-matched disposable
runtime, pass the read-only preflight, perform only browser click/scroll/type
K&M (never Playwright or refresh-as-proof), record revisions/events/rewards,
projections and PTY/PID custody, request a read-only peer review, fix concrete
findings, and push a semantic checkpoint. Never stage the protected save or
Campaign notebook.

## Next unblocked slice

Stage A is the only remaining stage without a hosted dependency, but its final
evidence requires a real second Windows environment and the operator's F-039
custody decision. Until those inputs exist, the safe work is local guardrail
tests and documentation; Stages B–F remain approval-gated and must not be
represented as complete.
