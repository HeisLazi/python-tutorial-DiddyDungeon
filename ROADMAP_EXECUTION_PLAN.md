# Forge roadmap execution plan

Status: local roadmap slices 0–6 implemented and verified; friend-ready
launcher/health foundation added; hosted distribution/social slices remain
explicitly gated — 2026-09-16

Claude Sonnet review was previously attempted from WSL while the configured
CLI returned `Not logged in · Please run /login`. The current checkpoint has
now completed an authenticated WSL Claude read-only review against the current
checkout/archive; its findings are recorded in the issue log and are not
treated as approval. This
plan remains the primary implementation/review record.

The current local checkpoint includes the playable Dungeon question/verdict
loop, adaptive evidence-grounded focus, rest/market rooms, local leaderboard,
independent Practice sessions/validated history, Codex library projection and
runtime checkout diagnostics. The Campaign Tutor Notebook remains part of the
Campaign surface; it was not removed or merged into Practice.

## Non-negotiable invariants

1. `LocalStateService` is the only progression writer. The backend anchors the
   canonical path to `REPO_ROOT/progress.json`; a workspace `progress.json` is
   legacy evidence and never a second save.
2. Every meaningful mutation increments the canonical revision and appends a
   bounded `state_events` record. React polls the cheap revision endpoint and
   reloads the full projection only when it changes.
3. Campaign keeps its collaborative Tutor Notebook (`tutor.py`). Practice is a
   separate provider-assisted mode and cannot write Campaign, Dungeon, or
   `tutor.py` state.
4. Rewards, Impact, Resolve, HP, unlocks, mastery and combat outcomes come from
   validated state-service results. React only renders them.
5. PTY sessions are long-lived. Browser checks use keyboard/mouse/scroll/type
   automation only; Playwright is prohibited.
6. Hidden future questions/answers are never sent to the browser, Codex, or
   provider context.

## Dependency-ordered slices and gates

### Slice 0 — baseline and authority (current)

- Preserve `GAME_STATE_SNAPSHOT_2026-09-15.md` and the persistent issue log.
- Add an explicit terminal-safe state command path and diagnostics so PYR never
  infers storage from its cwd.
- Add tests proving a direct workspace-file edit cannot change canonical
  revision, state events, HUD projection or cloud sync payload.
- Gate: backend/frontend suites green; canonical and workspace hashes are shown
  separately; existing shell/AI PTYs remain connected.

### Slice 1 — Campaign encounter completion

- Final mob clear opens a boss gate, without pretending the boss was defeated.
- Internal `record_boss_clear` accepts only bounded behaviour, explanation and
  interview evidence IDs; the service derives +100 XP, Housebreaker, Clean
  Clear eligibility and PYR evolution.
- Quest Journal renders mob completion, boss requirements and later victory
  projection without exposing future prompts.
- Gate: state-service mutation tests, event/reward queue tests and K&M flow.

### Slice 2 — boss interview and project progression

- Add provider-bound boss challenge/verdict tokens, replay protection and
  evidence-backed interview history.
- Record boss clear only after required behaviour, explanation and interview
  are all present; update long-term goals and the next-project chooser.
- Gate: negative verdict/replay tests, Codex/Character/Journal live projection,
  PTY survival.

### Slice 3 — Codex library

- Extend the canonical Codex schema with concept pages, definitions, generic
  examples, player notes, encountered question types, mob observations,
  attempts/results, weaknesses and interview/mastery history.
- Add bounded note editing through a named state action; never accept arbitrary
  JSON paths or provider-invented mastery.
- Render a searchable book/page layout from the projection.
- Gate: schema limits, sanitisation, no hidden answer leakage, K&M navigation
  and note persistence.

### Slice 4 — Homestead and economy polish

- Keep purchases/equipment behind the state service and show coins immediately
  from the same campaign revision.
- Add canonical validated armour/trinket unlock records only when evidence
  exists; do not infer legacy equipment.
- Replace placeholder presentation with a stable scene, loadout summary and
  purchase feedback that does not remount PTYs.
- Gate: purchase/equip/insufficient-funds tests, live HUD/Homestead checks.

### Slice 5 — Infinite Dungeon playable loop

- Preserve fresh starter loadout, durable run checkpoint, blank editor per
  question and reset-on-death semantics.
- Add state-service-owned question issue, answer/verdict, room transitions,
  rest/heal, market purchases, adaptive/custom mob generation from recorded
  weakness evidence, progressive difficulty and bounded rewards.
- Store run score, floor, room, completion/death summary and a local leaderboard
  projection. No Campaign rewards are granted by Practice or unverified text.
- Gate: restart/death/stale-question tests; K&M full run with typing; no PTY
  reset; no future answer leakage.

### Slice 6 — Practice mode history

- Add independent practice sessions, concept selection, mixed question types,
  optional AI help, attempts and validated history.
- Explicitly reject Campaign/Dungeon reward, HP, Resolve, `tutor.py` and cloud
  player-state mutations from Practice.
- Gate: mode-boundary tests and K&M repeat-use flow.

### Slice 7 — friend-ready local distribution

- Fix launcher/runtime checkout drift (F-025) without silently killing current
  PTYs; provide a clear intended-checkout launch command and health screen.
- Provide a guarded Windows/WSL launcher and onboarding contract that refuses a
  stale branch by default, injects the canonical platform state path and keeps
  backend reload disabled for stable PTYs.
- Finish local/offline sync conflict UX and account-scoped storage boundaries;
  do not seed Supabase until provider-authenticated state acceptance passes.
- Package a Windows desktop build/installer and a documented friend onboarding
  path. Sharing is opt-in and exposes stats/progression, never code/private
  notes.
- Gate: two-device mailbox acceptance, clean install/launch, K&M smoke test.

### Slice 8 — hosted social layer (last)

- After authentication and sync gates: opt-in rivals, friend presence, shared
  weekly raids and hosted leaderboard projections.
- Keep server-side authorization and event validation; local browser state is
  never trusted as a reward authority.
- Gate: authenticated multi-user tests and explicit privacy review.

## Per-slice review protocol

1. Read the current issue log and relevant contract before editing.
2. Add tests before or with the implementation.
3. Run focused tests, then the full WSL backend/frontend suites and Windows
   production build.
4. Run a browser K&M checkpoint: click/scroll/type only, capture before/after
   visible state, and assert shell/AI connection labels and process identity.
5. Record failures and reviewer findings in `FORGE_ROADMAP_ISSUES_LOG.md`.
6. Commit only semantic files (never user `progress.json` or root `tutor.py`),
   request Claude/Z.ai review when authenticated, fix findings, rerun gates,
   then push the green checkpoint.

## Current risks

- Local provider verdicts remain a trusted workstation boundary (F-001/F-010);
  local Battle/Boss/Dungeon challenge storage is now tab-scoped (F-009), but
  hosted release still must add provider authentication and account scoping.
- A tracked `progress.json` is still the offline canonical cache, so a branch
  switch or destructive Git operation can overwrite a live save unless the
  player backs it up. Moving that custody to an ignored per-device path is an
  explicit migration choice and remains open; this pass does not touch the
  player's save.
- OneDrive currently replicates the checkout, `.git`, dependencies and local
  save. It is an environmental third writer outside the state gateway; move
  the checkout or exclude those directories before trusting a two-device
  acceptance result.
- Existing legacy saves do not prove equipment, mastery or exact question
  history. Reconciliation must continue to report unsupported fields rather
  than invent them.

## Current checkpoint — 2026-09-16

- Slices 0–4 are implemented through the canonical state gateway, including
  campaign/boss validation, live revision polling, Codex pages/notes and
  Homestead purchases/equipment.
- Slice 5 is locally playable: fresh starter loadout, checkpointed
  `dungeon.py`, provider-routed unauthenticated verdict bridge,
  blank-on-rotation, adaptive recorded-
  weakness focus, progressive room types, rest/market, death reset and local
  leaderboard. It intentionally does not grant Campaign rewards or use hosted
  leaderboard transport.
- Slice 6 is implemented as an independent Practice mode with mixed question
  types, bounded sessions and provider-validated history. It never writes
  Campaign, Dungeon, rewards, HP, Resolve or `tutor.py`.
- Slice 7 has local launcher/runtime identity, a guarded Windows/WSL launcher,
  friend onboarding instructions and offline sync boundaries. A reproducible
  committed-source bundle is available through `tools/questlab-package.ps1`,
  and a fresh ext4 clone/install/launch smoke is now verified (F-049). Hosted
  two-device mailbox acceptance, a Windows friend-machine launch and the Tauri
  desktop proof remain open. The old 5173 process is not killed automatically.
- Slice 8 (hosted friends/presence/raids) remains last and is intentionally not
  seeded or claimed complete.

Latest gates: 77 WSL backend tests, 33 frontend tests, Windows Vite build, and
manual browser K&M acceptance on an isolated current-branch runtime. The
frontend count includes source tripwires as well as behavioural sync tests. No
Playwright was used.

The read-only `tools/questlab-km-preflight.ps1` gate now runs before manual K&M
evidence. It rejects a stale/mismatched runtime and requires the current
branch/HEAD, canonical authority and served SVG/loading markers without
fetching, mutating state or restarting PTYs. The 2026-09-16 isolated run
passed this gate at the current code tip `c4b08da` (the pushed HEAD is now
documentation-only `e1d8a03`) on disposable ports `7356/5192` and captured
revision-aware Resolve, reward/Journal/Codex projection and both connected
PTYs without a refresh.

The current snapshot and Claude Sonnet's detailed dependency/test/K&M plan are
recorded in `GAME_STATE_SNAPSHOT_2026-09-16_0605.md` (with the 05:39 baseline
preserved) and `ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0438.md`. The next hosted gate
is device-ownership migration plus real two-device acceptance; it remains
approval-gated. No local code-safe regression is justified by the current
evidence, and no Supabase, Tauri or Slice 8 work should leapfrog that gate.

The 05:26 exact-tip run was disposable: its starter save advanced through a
valid state-service objective, the HUD changed to 25 XP/10 coins, the Journal
unlocked The Dealer's Hand, Codex/Character/Homestead reflected the same
revision, and both PTYs stayed connected. The disposable clone and mutated
save were removed; the user's Level 2 canonical save and Campaign `tutor.py`
were not touched.

The 04:20 snapshot is refreshed in `GAME_STATE_SNAPSHOT_2026-09-16_0420.md`.
Claude Sonnet's 04:24 read-only audit found the local Stages 1–4 evidence
consistent and confirmed the numeric test counts against the source. Its only
local finding was the known WSL CRLF/LF status-noise ambiguity, now stated
explicitly in the snapshot. The bounded follow-up at `ea8f878` adds a passive
`RUNTIME STALE · use current launcher` footer when `/api/runtime` lacks the
branch/HEAD/state-authority contract. An exact-tip ext4 pair at `7352/5187`
passed preflight and pure K&M showed connected PTYs, visible SVG HUD icons and
revision-aware UI update without refresh; the disposable runtime was removed.

The local Slice 5 loop is also covered by the 2026-09-16 isolated K&M run
recorded in `FORGE_ROADMAP_ISSUES_LOG.md` and
`CLOUD_DESKTOP_IMPLEMENTATION_REPORT.md`: provider verdict, blank-on-rotation,
progressive rooms, market purchase, run banking and leaderboard were observed
without a browser refresh. Hosted Dungeon persistence remains F-018. For the
Milestone A–F cloud gates and their approval boundaries, see
`AGENT_CLOUD_DESKTOP_HANDOFF.md` and the implementation report; this plan is
the local-slice execution record.

A fresh ext4 archive also passed WSL `npm ci` plus `npm run build` (1,344
modules). The remaining F-033 packaging risk is limited to the shared OneDrive
`node_modules` tree; friends should install dependencies inside their Linux
checkout rather than reuse a Windows tree. The guarded launcher now detects a
missing native Rollup optional package under WSL and exits before spawning a
broken runtime with that remediation, without touching the save or PTYs.

The current local Slice 7 checkpoint also exposes a read-only custody preview
(`questlab-state custody`) and has a two-root disposable isolation proof. These
do not migrate the tracked save or claim hosted sync; F-039 remains approval-
gated and the next migration command must stay opt-in.

The opt-in gateway and launcher halves are now present as
`questlab-state custody-migrate` and `-MigrateLocalState`. They require a
reviewed source revision plus `MIGRATE_LOCAL_STATE`, derive the destination
from the opaque checkout namespace, copy atomically and keep the canonical
revision/events unchanged. The default launcher still remains on the tracked
cache; real-save approval and clean two-device acceptance remain open.

The latest checkpoint adds upstream freshness to `/api/runtime` and the footer,
removes the legacy combat shell's duplicate campaign poll (React now owns the
single revision timer), preserves the Linux executable bit on `questlab-state`,
and partitions browser sync metadata by an opaque checkout namespace before
cloud auth restoration. Existing legacy metadata is not merged or deleted;
normal revision/conflict handling remains the authority for any new checkout.

The 04:38 snapshot and 04:40 Claude plan were committed at `70997d3`. A
post-plan full regression at 04:45 passed 77 backend tests and 33 frontend
tests. The current committed archive was inspected at `c1911a0`: it contains
the baseline save and onboarding guide but not the user's untracked `tutor.py`.
Only documentation changed after the exact code tip used for the latest pure
K&M run, so that browser evidence remains applicable; a real second-Windows
launch and F-039 custody choice are still open.

## Current checkpoint — 2026-09-16 06:04

The 06:04 evidence run was on `3ae4d6c` (code fix `c8dba22`, followed by the
review and K&M evidence commit); subsequent docs and preflight hardening are
now pushed through `3ba37c3`. The authenticated Claude Opus read-only review found
no P0/P1 issues; its P2 preflight null-ref and lower-revision projection
findings, plus the explicit-null boss-reward edge case, are fixed. The current
regression counts are **77 backend / 35 frontend**, PowerShell preflight parse
pass and a **1,345-module** Vite build. A disposable exact-tip K&M run showed
the monochrome HUD icons, both connected PTYs and live Resolve **4/4 → 2/4**
after a state-service verdict without refresh. The Windows save and Campaign
`tutor.py` remain protected dirty user data. Hosted two-device sync, F-039
custody approval, provider-authenticated adjudication, Tauri packaging and
Slice 8 social work remain gated and were not started.

## Fallback execution matrix — 2026-09-16 06:08

The fresh Claude roadmap-planning request was allowed five minutes and returned
no output, so this matrix is the primary agent's explicit fallback plan. It
does not weaken any approval gate.

| Stage | Implementation boundary | Required tests | Pure K&M acceptance | Status/gate |
|---|---|---|---|---|
| A. Local authority/projection | `ide/server/state.py`, `app_v2.py`, `AppV2.jsx`, `RpgViews.jsx`, `syncEngine.js`; one canonical save, revision polling and validated events | workspace-file isolation, revision/event polling, reward authority, stale revision handling; full backend/frontend/build gates | disposable current-branch runtime; trigger one gateway mutation; HUD, Journal, Codex, Character, Homestead agree without refresh; shell/AI remain connected | **Green locally**; keep regression gates running |
| B. Campaign/Boss/Codex/Homestead | state-service encounter/boss/equipment actions; React renders only returned events; Campaign Tutor remains `tutor.py`, Practice stays separate | objective impact/Resolve, mob clear/unlock/Codex, boss evidence completeness, bounded notes, purchase/equip conflicts | verified objective, mob clear, next encounter, Codex growth and coin/equipment projection with no refresh | **Green locally**; provider-authenticated trust still open |
| C. Dungeon/Practice | canonical Dungeon checkpoint/run state and independent Practice session/history; no Campaign rewards or notebook writes | restart/checkpoint, stale question, blank rotation, room/economy/death, mixed Practice and no-cross-mode writes | start run, type/checkpoint, rotate, REST/MARKET, purchase/bank or die; separately repeat Practice; record PTY continuity | **Green locally**; hosted persistence is F-018 |
| D. Local distribution | `tools/questlab-launch.ps1`, `questlab-package.ps1`, onboarding and preflight; committed HEAD only | launcher/package custody, dependency preflight, branch/runtime identity, clean install | clean WSL/ext4 launch and gateway reward; real Windows second-machine launch still required | **Ext4 green; Windows gate open** |
| E. Hosted sync/avatar | existing auth/profile/device, bounded `syncEngine.js`, SQL migrations/RLS and avatar boundary; no broad state transport | linked migrations/RLS, CAS conflicts, offline outbox, account/device privacy, avatar storage denials | two signed-in devices, offline/reconnect/conflict choices, live projections and PTYs | **Approval required**; do not seed Supabase |
| F. Desktop/public/social | thin Tauri sidecar, safe public allowlist, then friends/presence/raids | child-process cleanup, route allowlist, RLS/privacy and two-account tests | desktop close/PID proof, deployed public routes, two-account privacy run | **Blocked by E and explicit infrastructure approval** |

Every stage ends with focused tests, full applicable regression, snapshot and
issue-log entry, a semantic commit/push, and a K&M run using only click,
scroll, typing and observation. No stage may stage `progress.json` or root
`tutor.py`, infer rewards in React, reveal future questions, or reset a PTY.
