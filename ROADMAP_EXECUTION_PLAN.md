# Forge roadmap execution plan

Status: local roadmap slices 0–6 implemented and verified; guarded Windows and
native-Linux friend launchers/health foundations added; CachyOS native-Linux
support is an explicit open distribution gate; hosted distribution/social
slices remain explicitly gated — 2026-09-17

Claude Sonnet review was previously attempted from WSL while the configured
CLI returned `Not logged in · Please run /login`. The current checkpoint has
now completed an authenticated WSL Claude read-only review against the current
checkout/archive; its findings are recorded in the issue log and are not
treated as approval. This
plan remains the primary implementation/review record.

The current local checkpoint includes the playable Dungeon question/verdict
loop, adaptive evidence-grounded focus, rest/market rooms, local leaderboard,
the unified `tutor.py` Tutor/Practice learning IDE with selectors and notes,
validated Practice history, Codex library projection and runtime checkout
diagnostics. Practice remains a separate no-reward state-service mode, but it
uses the same controlled `tutor.py` notebook/editor rather than a second
training form or a second notebook.

The latest authenticated Claude Sonnet dependency plan is persisted in
`ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0705.md`. It adds the CI/public
activity-writer boundary to the review surface and confirms that hosted,
desktop, public and social stages remain approval-gated.

## Non-negotiable invariants

1. `LocalStateService` is the only progression writer. The backend anchors the
   canonical path to `REPO_ROOT/progress.json`; a workspace `progress.json` is
   legacy evidence and never a second save.
2. Every meaningful mutation increments the canonical revision and appends a
   bounded `state_events` record. React polls the cheap revision endpoint and
   reloads the full projection only when it changes.
3. Campaign Tutor and Practice share one controlled `tutor.py` editor/notebook,
   server-owned concept/type/difficulty selectors and the workspace notes
   channel. Practice is still a separate provider-assisted state-service mode:
   it may save teaching code/notes through the dedicated Tutor/notes routes,
   but it cannot mutate Campaign/Dungeon rewards, HP, Resolve, equipment,
   combat or run state.
4. Rewards, Impact, Resolve, HP, unlocks, mastery and combat outcomes come from
   validated state-service results. React only renders them.
5. PTY sessions are long-lived. Browser checks use keyboard/mouse/scroll/type
   automation only; Playwright is prohibited.
6. Hidden future questions/answers are never sent to the browser, Codex, or
   provider context.
7. A mutating disposable K&M check must pass
   `questlab-km-preflight.ps1 -RequireIsolatedState` against an explicitly
   confirmed local cache before any browser mutation; workspace separation alone
   is not a state-custody boundary.

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
  optional AI help, attempts and validated history above the shared `tutor.py`
  editor/notebook. Keep concept notes as bounded `notes/<concept>.md` files.
- Explicitly reject Campaign/Dungeon reward, HP, Resolve, equipment, combat and
  run-state mutations from Practice. Tutor/notes writes remain controlled,
  bounded learning-workspace writes rather than player progression writes.
- Gate: mode-boundary tests and K&M repeat-use flow.

### Slice 7 — friend-ready local distribution

- Fix launcher/runtime checkout drift (F-025) without silently killing current
  PTYs; provide a clear intended-checkout launch command and health screen.
- Provide a guarded Windows/WSL launcher and onboarding contract that refuses a
  stale branch by default, injects the canonical platform state path and keeps
  backend reload disabled for stable PTYs.
- Add a native Linux distribution matrix with CachyOS as the first explicitly
  requested desktop target. Keep the checkout and dependencies on a native
  Linux filesystem, preserve the executable `questlab-state` gateway and prove
  both PTYs plus live revision projection on the actual laptop before calling
  the distro supported (F-058).
- Finish local/offline sync conflict UX and account-scoped storage boundaries;
  do not seed Supabase until provider-authenticated state acceptance passes.
- Package a Windows desktop build/installer and a documented friend onboarding
  path. Sharing is opt-in and exposes stats/progression, never code/private
  notes.
- Gate: two-device mailbox acceptance, clean install/launch, K&M smoke test.

### CachyOS native Linux target — new distribution gate (F-058)

CachyOS is an Arch-based rolling-release target for the user's laptop. The
existing WSL/ext4 evidence does not certify it, and this gate must remain open
until it is run on the real machine. The target acceptance is:

- clone the reviewed branch into a native Linux filesystem (for example
  `~/projects/python-tutorial-DiddyDungeon`), never a `/mnt/c` or OneDrive
  mount used as a live dependency tree;
- install the distro-provided Git, Python/venv, Node.js and npm toolchain, then
  create `.venv`, install `ide/server/requirements.txt`, and run `npm ci` in
  `ide/frontend` so Rollup uses native Linux optional packages;
- launch with the module-safe `PYTHONPATH=. .venv/bin/python -m ide.quest`
  command and a separate quest workspace; keep backend reload disabled so
  shell/AI PTYs remain stable;
- verify `questlab-state runtime`, `authority` and `campaign` report one
  canonical state path, then use browser K&M to prove live HUD/Journal/Codex/
  Character/Homestead projection, save authority and both connected PTYs;
- record the CachyOS kernel/package versions, ports, test counts and any
  native dependency remediation in the issue log before changing F-058 to
  **Verified**. No Supabase seed or hosted-state claim is part of this gate.

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
- Slice 6 is implemented as a separate no-reward Practice mode with mixed
  question types, bounded sessions and provider-validated history above the
  shared `tutor.py` editor/notebook. It can save bounded teaching code and
  concept notes through dedicated routes, but never writes Campaign, Dungeon,
  rewards, HP, Resolve, equipment, combat or run state.
- Slice 7 has local launcher/runtime identity, a guarded Windows/WSL launcher,
  friend onboarding instructions and offline sync boundaries. A reproducible
  committed-source bundle is available through `tools/questlab-package.ps1`,
  and a fresh ext4 clone/install/launch smoke is now verified (F-049). Hosted
  two-device mailbox acceptance, a Windows friend-machine launch and the Tauri
  desktop proof remain open. The old 5173 process is not killed automatically.
- Slice 8 (hosted friends/presence/raids) remains last and is intentionally not
  seeded or claimed complete.

Latest gates: 77 WSL backend tests, 35 frontend tests, Windows Vite build, and
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
recorded in `GAME_STATE_SNAPSHOT_2026-09-16_0631.md` (with earlier baselines
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
| B. Campaign/Boss/Codex/Homestead | state-service encounter/boss/equipment actions; React renders only returned events; Campaign Tutor and Practice share the managed `tutor.py` IDE/notes boundary | objective impact/Resolve, mob clear/unlock/Codex, boss evidence completeness, bounded notes, purchase/equip conflicts | verified objective, mob clear, next encounter, Codex growth and coin/equipment projection with no refresh | **Green locally**; provider-authenticated trust still open |
| C. Dungeon/Practice | canonical Dungeon checkpoint/run state plus independent Practice session/history above the shared `tutor.py` editor; no Campaign/Dungeon rewards, HP, Resolve, equipment, combat or run-state writes | restart/checkpoint, stale question, blank rotation, room/economy/death, mixed Practice and no-cross-mode writes | start run, type/checkpoint, rotate, REST/MARKET, purchase/bank or die; separately repeat Practice and shared-notebook save; record PTY continuity | **Green locally**; hosted persistence is F-018 |
| D. Local distribution | `tools/questlab-launch.ps1`, `questlab-package.ps1`, onboarding and preflight; committed HEAD only | launcher/package custody, dependency preflight, branch/runtime identity, clean install, CachyOS native-Linux matrix | clean WSL/ext4 launch and gateway reward; real Windows second-machine and CachyOS laptop launches still required | **Ext4 green; Windows + CachyOS gates open** |
| E. Hosted sync/avatar | existing auth/profile/device, bounded `syncEngine.js`, SQL migrations/RLS and avatar boundary; no broad state transport | linked migrations/RLS, CAS conflicts, offline outbox, account/device privacy, avatar storage denials | two signed-in devices, offline/reconnect/conflict choices, live projections and PTYs | **Approval required**; do not seed Supabase |
| F. Desktop/public/social | thin Tauri sidecar, safe public allowlist, then friends/presence/raids | child-process cleanup, route allowlist, RLS/privacy and two-account tests | desktop close/PID proof, deployed public routes, two-account privacy run | **Blocked by E and explicit infrastructure approval** |

Every stage ends with focused tests, full applicable regression, snapshot and
issue-log entry, a semantic commit/push, and a K&M run using only click,
scroll, typing and observation. No stage may stage `progress.json` or root
`tutor.py`, infer rewards in React, reveal future questions, or reset a PTY.

## Latest evidence checkpoint — 2026-09-16 06:25

`GAME_STATE_SNAPSHOT_2026-09-16_0625.md` supersedes the 06:08 snapshot for
current-state reporting. The pushed branch is `825d740`; launcher contracts
and the full **77/77 backend / 35/35 frontend / 1,345-module build** gates are
green. A fresh ext4 current-tip runtime passed pure K&M on `7361/5197`: the
monochrome HUD icons were visible, both PTYs stayed connected, and a validated
state-service verdict changed Resolve **4/4 → 2/4** without refresh. This
closes the local launcher checkpoint; the real Windows, hosted and approval
gates listed above remain open.

## Current checkpoint — 2026-09-16 07:01

The pushed branch is now `5f678e7` after a documentation-only onboarding
guardrail slice. Friend setup prefers a Linux/ext4 checkout, explicitly forbids
running `npm install` or `npm ci` against the live OneDrive-mounted frontend
dependency tree from WSL, and requires a separate quest workspace so canonical
and legacy paths remain provably distinct. The full 77/77 backend, 35/35
frontend, 9/9 launcher-contract, compile and 1,345-module build gates remain
green. The latest pure K&M runtime evidence is still the 06:50 Windows
preflight checkpoint; no runtime, save, or PTY was started or changed for this
docs-only commit. Protected `progress.json` and Campaign `tutor.py` remain
untouched and unstaged. F-039 custody, the real second-machine launch,
provider-authenticated adjudication, hosted sync/Supabase, Tauri and social
work remain gated as listed above.

## Current checkpoint — 2026-09-16 07:38

The custody guard is now executable on Windows: `-RequireIsolatedState` uses
correct single-character separator literals and the launcher contract covers
the fail-closed comparison. A disposable `--use-local-state` runtime passed
the guarded preflight and pure CUA K&M verified live revision/event projection
across HUD, Journal, Codex, Character and Homestead while both PTYs stayed
connected. The protected canonical save remained revision 5 and was not
mutated by this acceptance. The local authority/projection slice is green;
the real second-Windows launch, F-039 custody decision and all hosted/Tauri/
public/social gates remain open.

## Current checkpoint — 2026-09-16 10:14

The local Dungeon/Practice slice is now browser-certified on a disposable
cache. A state-service Dungeon verdict advanced the run, emitted the validated
score/run-coin event and reset the editor buffer before the next question;
Practice created independent reviewed history with zero Campaign/Dungeon
rewards. After a runtime restart, Forge resumed the active Dungeon checkpoint
at the same room with a blank buffer, and the backend accepted both shell and
AI PTYs again. The canonical save stayed revision 5 and the legacy evidence
was untouched. This closes the local C-slice proof; F-018 hosted persistence,
the real second-Windows launch and F-039 custody decision remain open before
Milestone C.

## Current checkpoint — 2026-09-16 10:44

The Codex/Homestead presentation slice is complete locally. Codex now exposes
service-projected library/evidence metrics and page-level recorded signals;
Homestead shows a canonical live-loadout/economy summary with revision, level,
XP, armor, trinket and coins. The legacy icon bridge explicitly skips
React-owned stat nodes so revision polling cannot recreate nested pills.

The friend launcher now runs the package as `PYTHONPATH=. .venv/bin/python -m
ide.quest`, fixing the mounted-checkout import failure found during the
disposable custody launch. Handoff examples match the module-safe command.

Gates are green at **78 backend / 36 frontend / 1,345-module Vite build**;
compileall and PowerShell preflight parsing pass. Pure CUA K&M on an explicitly
isolated disposable cache showed the new Codex/Homestead surfaces, visible
monochrome HUD icons and both `CONNECTED` PTYs. The protected save and
Campaign `tutor.py` remain untouched. The real second-Windows launch,
F-039 save-custody choice, provider-authenticated adjudication and hosted
Milestone C remain approval-gated.

Claude Sonnet's 10:50 read-only follow-up found no P0/P1 issue. A pre-existing
Codex fallback that could loosely shelve entries without `page_id` was
tightened to an exact/prefix concept match and source-tested. The review also
records the known P3 boundary that frontend checks are source-regex tripwires,
not a replacement for rendered-DOM/K&M evidence.

## Current checkpoint — 2026-09-16 — bug-hunt closure and CachyOS planning

The persistent bug hunt found and fixed F-055 (cross-tab PYR context reads),
F-056 (repository-root PTY `PATH` shadowing) and F-057 (stale Dungeon/Practice
release wording). Copilot scored two unique defects / five points; Claude
Sonnet scored one / four; the primary K&M pass scored zero new defects. Full
reproduction and repair evidence is in `BUG_HUNT_LOG_2026-09-16.md` and the
issue log.

F-058 adds the requested CachyOS native-Linux distribution gate. Native
checkout/dependency installation, launch, one canonical state path, live
projection and shell/AI PTY continuity must be proven on the actual CachyOS
laptop before the distro is marked supported. Until then, WSL/ext4 is the only
Linux evidence and no hosted/Supabase state work is implied.

F-059 is now closed locally: `tools/questlab-km-preflight.py` provides a
PowerShell-free equivalent for native Linux, including the fail-closed
isolated-state check. Its contract test and `--help` invocation pass. This
removes a tooling gap but does not change F-058's requirement for real
CachyOS-machine evidence. A disposable WSL K&M smoke on `7415/5225` then
passed the native preflight at revisions 5 and 7 and visited all RPG/learning
surfaces; the reward toast, live projection, five SVG icons and both connected
PTY labels remained healthy without refresh. Those results are local tooling
evidence, not CachyOS certification.

## Current checkpoint — 2026-09-16 — local sync simulator

F-060 is closed locally: `tools/questlab-local-sync-sim.py` and its contract
test run the real `LocalStateService` through two disposable device caches,
exercise mailbox CAS revisions, reject an offline stale pull with `409`, and
apply an explicit keep-device resolution that emits `sync_apply_cloud`. The
canonical save remains byte-for-byte unchanged. This closes a local confidence
gap only; hosted/authenticated mailbox sync, OneDrive custody, a clean Windows
friend machine and the actual CachyOS laptop remain required gates before
Milestone C/public distribution.

The current deterministic gates are **81/81 backend**, **36/36 frontend**,
Python compilation and a **1,345-module Vite build**. The latest disposable
CUA K&M checkpoint used an isolated cache, kept both PTYs connected and showed
the validated reward projection live without a browser refresh. Protected
player files remain unstaged.

The current committed-source friend bundle was also smoke-tested at pushed
HEAD `fdb4526`: the packager produced a directory and zip whose `progress.json`
matched the Git blob, omitted the untracked Campaign `tutor.py`, and left no
temp output. This closes the current local package-custody check; friend
Windows/CachyOS launch and hosted sync remain external gates.

## No-input execution boundary — 2026-09-16

At the current local checkpoint, the primary agent can keep running bounded
unit/contract tests, disposable isolated-cache WSL/ext4 K&M checks, launcher
and package-custody preflights, build/compile gates, and documentation/review
updates without user input. Those checks strengthen local confidence but
cannot substitute for a real second-device cloud round-trip. Authenticated
Supabase/RLS acceptance, the explicit F-039 save-custody choice, clean friend
machine launch, actual CachyOS K&M certification, Tauri packaging and hosted
Milestone C remain external gates. The public activity-only tip merged during
this checkpoint is `cab6b0c`; no cloud seed or protected player-file edit was
performed.

## Post-merge regression gate — 2026-09-16

The public activity fast-forward and documentation commit were followed by a
fresh local regression: backend **81/81**, frontend **36/36**, Python
`compileall`, and the **1,345-module** Vite build passed. The two-cache local
sync simulator again preserved the source digest, rejected stale mailbox and
local pulls with `409`, and recorded explicit `sync_apply_cloud` resolution.
The committed-source bundle at `f5e2a4119f9555e72d7b13d300bb91d00b91a773`
matched the `HEAD:progress.json` Git blob, omitted `tutor.py`, and left no
temporary output. These are local checks only; no second-device, cloud seed,
or protected-save mutation was performed.

## Clean ext4 live-projection gate — 2026-09-16

A disposable native Linux checkout passed `npm ci`, the backend **81/81**
suite, Python compilation, the **1,345-module** Vite build and the
PowerShell-free isolated-state preflight. In-app-browser keyboard/mouse
testing then used the visible Forge shell to apply one trusted reward and two
verified Battle objectives. Without refresh, HUD/Character/Homestead reflected
the new revision, Quest Journal advanced from **The Empty Table** to **The
Dealer's Hand (6/6)**, Codex recorded the defeated encounter and evidence,
and reward notifications displayed the service-returned XP/coins, next
encounter and First Blood. The five SVG icons remained visible and shell/AI
PTY labels stayed `CONNECTED`; browser error/warning logs were empty.

The runtime, browser tab, workspace and derived cache were removed after the
check. This strengthens the local gate only; it cannot replace real
PC↔laptop cloud sync, Supabase/RLS, CachyOS, friend-machine or Tauri proof.

## Current checkpoint — 2026-09-16 — custody resume hardening

Commit `3def7a3` closes the restart edge found in the disposable K&M hunt:
after an approved state-gateway migration, a later explicit local launch can
resume a cache only when its gateway-written source digest/revision marker
still matches and the destination revision is strictly advanced. Changed,
unmarked or ambiguous divergence remains a conflict. The protected repository
save and root `tutor.py` were not staged or written.

Evidence is green for focused custody tests (**21/21**), the full WSL backend
suite (**84/84**), frontend (**36/36**), Python compilation and the Vite
**1,345-module** build. A disposable runtime relaunched the saved Dungeon
Floor 1 / Room 1 checkpoint, restored its editor buffer and kept shell/AI PTY
labels connected. This is local provenance evidence only; F-039's real save
custody choice, hosted/authenticated two-device sync, clean friend launch and
CachyOS/Tauri gates remain external.

## Operational checkpoint — 2026-09-16 — PC stale endpoint diagnosis

The PC's visible `5173` endpoint was an older long-lived checkout and the
manual `5174` frontend was paired with an old backend port. This is the
existing F-025/F-031 runtime-choice boundary, not a second authoritative save.
Existing processes and PTYs were left running. A temporary current-tip hybrid
on `5176/7335` verified branch `feature/cloud-sync-desktop`, HEAD `d7110b7`,
revision 5 and the Level 2 / 50 XP / 55 coin projection without refresh. The
mounted OneDrive WSL Rollup guard remains intentional; clean ext4 dependencies
are still the supported all-WSL launch path.

## Current checkpoint — 2026-09-17 — explicit workspace source transfer

F-062 is closed locally. `questlab-files` provides a separate, explicit
Git-backed transfer ref for the player-authored source needed on another
device. Its tree is limited to `blackjack.py`, Campaign `tutor.py` and
`dungeon.py` plus a bounded SHA-256 manifest; it never pushes the workspace
branch wholesale, reads or writes `progress.json`, or carries session notes,
secrets, Git history or PTY state. Pull previews first, updates a clean older
file without friction, and refuses dirty conflicts unless the player opts in
to an overwrite after a temporary backup is created.

The implementation and focused tests live in `ide/workspace_transfer.py`,
`ide/server/test_workspace_transfer.py`, `questlab-files` and
`WORKSPACE_TRANSFER.md`. The full backend suite and Python compilation pass.
This is not a hosted source-file channel and does not claim a PC↔laptop
round-trip until the player runs the explicit push on the edited device and
pull/verification on the other one. Campaign and Practice share the managed
`tutor.py` editor/notebook; Practice remains a separate no-reward state-service
mode and cannot mutate Campaign/Dungeon progression.

## Current checkpoint — 2026-09-17 — original product contract re-aligned

The original Forge redesign brief is now the normative product contract for
the local slices: splash/last-route continuity, Hub-first navigation, chapter
silhouettes, Codex field-library pages with bounded notes, paper Journal
pagination, a shared SVG shop/loadout, the grid Dungeon route selector and the
unified Tutor/Practice `tutor.py` IDE. Historical entries above preserve the
earlier review wording, but the current Tutor/Practice rule is the one in the
invariants and Slice 6: one managed notebook/editor, separate no-reward
Practice state, and no Campaign/Dungeon progression writes from Practice.

The 2026-09-17 isolated browser K&M hunt found and repaired three local
regressions before this checkpoint was accepted: provider launch did not set the
tab-scoped provider handoff; a legacy workspace `progress.json` was visible in
the Forge file tree; and the bounded PYR context bridge rejected the shared
`tutor.py` file after a Practice session opened. Focused regression coverage,
the full backend suite (**97/97**), frontend suite (**37/37**) and Python
compilation are green. The persistent details are in
`BUG_HUNT_LOG_2026-09-17.md` and `FORGE_ROADMAP_ISSUES_LOG.md` (F-071–F-074).

The protected repository save, root `tutor.py`, root `dungeon.py`, active user
processes and PTYs were not staged, overwritten or reset. Hosted player-state,
real PC↔laptop sync, account/avatar acceptance, the actual CachyOS run,
friend-machine packaging and Tauri remain external gates; this checkpoint does
not seed Supabase or claim those gates complete.

## Cloud campaign projection checkpoint — 2026-09-17

The original cloud slice moved only HUD-level player fields. That left a
second device with the right Level/XP/coins but a starter Journal, Codex and
Dungeon. The next source slice keeps the same state-service authority and
revision/CAS protocol while adding one bounded `campaign` projection containing
validated project/mob progress, Codex encounter evidence, skills, goals,
achievements, Practice history and the restart-safe answer-free Dungeon
checkpoint. Local event logs, profile data, catalogs and arbitrary workspace
JSON remain excluded.

The Python gateway validates and merges this domain through
`sync_apply_cloud`, so a successful pull increments the canonical revision and
records an auditable state event. The browser SyncEngine now sends the same
projection in outbox/pull/conflict paths. The hosted SQL migration is committed
but deliberately unapplied; authenticated two-device and Supabase/RLS tests
remain Milestone C gates. Current local contracts: state service **40/40**,
migration contracts **7/7**, and the protected projection is **9,897 bytes**.

The follow-up Codex-note pass now transports both canonical `notes` and
player-authored `player_notes` through the same bounded projection and retains
local-only `learning_state.last_teachback` during cloud merges. Backend
verification is **101/101**, clean frontend **40/40**, and the production build
transforms **1,346 modules**. This remains source/simulator evidence only until
the hosted migration is deliberately applied and a real authenticated
PC↔laptop acceptance run is captured.

## Current checkpoint — 2026-09-17 — disposable account and status-copy recheck

The disposable-account acceptance verified profile/device registration, private
avatar upload/download/replacement across two isolated SyncEngine clients,
anonymous avatar/profile denial, and the explicit Git-backed transfer of
`blackjack.py`, `tutor.py`, `dungeon.py` and bounded concept notes without
touching `progress.json` or private session files. The account is a QA-only
identity, not the player's personal account.

The live hosted `save_player_state` RPC still rejected the source-reviewed
campaign projection with `next_state contains unsupported domains`; this is
F-079 and means the campaign migration remains unapplied. No hosted migration
was run without approval. The in-app browser also failed to attach a fresh
tab to the isolated runtime (F-080), so no new K&M claim is made for this
account pass.

One stale signed-in status message was corrected (F-081) so it names Campaign,
Journal and Codex as shared gateway surfaces. Fresh local gates are backend
**101/101**, frontend **41/41**, Python compilation, and a clean ext4 Vite
build transforming **1,346 modules**. Protected `progress.json`, root
`tutor.py`, root `dungeon.py` and existing PTYs remain untouched.

The hosted-validator failure path now distinguishes an outdated campaign
schema from a generic sync error: Forge names the required migration and keeps
the local outbox queued. The repair is covered by frontend **42/42** and the
same **1,346-module** clean build; it does not apply or bypass Supabase SQL.

The follow-up status-copy review also closed F-083 locally: the initial
signed-in frame and the settled account state now name the same Campaign,
Journal and Codex gateway surfaces, so the status text does not change merely
because account registration completed. This is a presentation repair only;
hosted migration and real two-device acceptance remain approval-gated.

The friend-distribution review also closed the documentation gap F-084: native
macOS setup now has the same branch, sibling-workspace, executable-bit and
stable-launch instructions as the Linux path. The actual Mac machine still
needs its own install/K&M/PTY acceptance before being called certified.

The avatar recheck also closed F-085 locally: signed-in portrait caches are now
account-scoped and cannot fall back to an unrelated unscoped image after a
remote removal or account transition. Anonymous/offline portraits remain
available locally. This hardens the Milestone D privacy boundary but does not
change the hosted migration gate.

The handoff precision review also closed F-086/F-087: it now states that the
public state command accepts only `player`/`pyr`, while `system` is internal
only, and that Tutor/Practice share one managed `tutor.py`/notes surface with
separate no-reward Practice state. This is documentation alignment; no runtime
authority was widened.

## Current checkpoint — 2026-09-17 — frontend bundle identity

F-121 closes the remaining local ambiguity behind the recurring “old UI”
symptom. `ide.quest` now passes the checkout HEAD SHA to Vite; the React shell
compares the embedded marker with the backend runtime HEAD and visibly warns
when the frontend is stale. This is a diagnostic/launch hardening slice only:
it does not restart PTYs, change state custody or alter hosted gates.

Current-source Forge tests are **33/33** and launcher contract tests **14/14**.

## Current checkpoint — 2026-09-17 — Codex paper surface

F-122 keeps the finite Codex book readable and visually intentional instead of
leaving a dense dashboard behind the scroll repair. The index/page hierarchy,
display typography and example blocks are now theme-aware and paper-like while
the fixed shell and one contained section scroll owner remain unchanged.

Current-source Forge tests are **34/34**. Clean archive frontend tests/build
and browser K&M remain visual publication checks; no state, learner file, PTY
or hosted transport changed.

## Current checkpoint — 2026-09-17 — Codex outer-feed boundary

F-123 repairs the remaining finite-book presentation regression. The Codex is
now pinned to the bounded Forge game surface, and active book sections cannot
turn the screen into an endless vertical feed. Only the Field Library index
retains a contained navigation scroll; the reading surface is advanced with
explicit book/section controls.

Current-source Forge tests are **35/35**. Clean archive frontend tests/build
and browser K&M remain visual publication checks; no state, learner file, PTY
or hosted transport changed.

## Current checkpoint — 2026-09-17 — account revision diagnostics

F-124 makes signed-in sync state inspectable in Settings without adding a
second authority. Account shows the local campaign revision rendered by Forge,
the cloud cursor retained by SyncEngine and queued projection count. This is a
diagnostic and UX slice only; hosted schema application, reconciliation and
real PC/laptop acceptance remain gated.

Current-source Forge tests are **36/36**. Clean archive frontend tests/build
and browser K&M remain visual publication checks.

## Current checkpoint — 2026-09-17 — source transfer verification

F-125 closes the visibility gap in the reviewed workspace-file channel.
Settings now displays allowlisted-file digest prefixes, local/remote mismatch
state and excluded-change counts before a player chooses a pull or overwrite.
The Git transfer ref and canonical state authority are unchanged.

Current-source Forge tests are **37/37**. Clean archive frontend tests/build
and browser K&M remain visual publication checks; device round-trip evidence
is still required.

## Current checkpoint — 2026-09-17 — local sync simulator recheck

F-126 re-ran the disposable two-device local sync contract at the current
branch tip. Push, pull, stale-mailbox detection, local-revision conflict and
explicit keep-device resolution all passed while the source save digest stayed
unchanged. This strengthens the local/offline gate without claiming hosted
Supabase acceptance.

## Current checkpoint — 2026-09-17 — Codex viewport shell follow-up

F-127 removes the final generic feed contract from the Codex root. The Codex
now owns a viewport-pinned shell, contains overscroll, and gives scroll only to
the Field Library index and the selected book section. The outer Forge surface
does not grow as encounter evidence or notes accumulate; Battle Shell remains a
separate bounded tab. This is a presentation repair only and does not widen
state authority or cloud scope.

Current-source Forge tests are **38/38**. Browser K&M remains a publication
visual gate because the local Codex browser tab could not attach.

## Current checkpoint — 2026-09-17 — dev HMR PTY retention

The F-035 dev-only lifecycle risk is fixed in source. Shell and AI terminal
WebSockets now live in a browser-global role registry rather than in a React
effect; Fast Refresh detaches and rebinds the xterm consumer within a bounded
grace period. A real abandoned component still cleans up, while normal source
edits no longer intentionally close the PTY link. This does not change the
canonical state gateway or the revision/event projection.

Current-source Forge tests are **39/39**. Clean archive build and browser-HMR
K&M remain the verification gates; F-080 blocks the latter in this environment.

The clean archive recheck passed **58/58** frontend tests and a Vite production
build transforming **1,346 modules**. WSL backend discovery passed **108/108**;
the protected local sync simulator returned `ok: true` with an unchanged source
digest and preserved Campaign/Codex/Dungeon fields. This is local evidence only;
browser-HMR K&M and hosted two-device acceptance remain external gates.

## Current checkpoint — 2026-09-17 — legacy Codex shell parity

F-129 moves the Codex viewport boundary to the shared game-surface contract so
the compatibility `App.jsx` shell cannot reintroduce the outer feed simply by
omitting the `forge-v2` class. Current AppV2 and legacy routes now share the
same pinned shell and contained scroll owners. This is a presentation-only
repair.

Current-source Forge tests remain **39/39**; clean archive build and browser
K&M are the remaining publication checks for this small CSS scope.

The clean archive recheck passed **58/58** frontend tests and a Vite build
transforming **1,346 modules**. Browser K&M remains the sole missing visual
evidence for this presentation-only repair.

## Current checkpoint — 2026-09-17 — Codex finite reading room

F-130 tightens the presentation after the outer-feed and legacy-shell repairs.
The game surface and Codex root now have an explicit height-bounded grid; the
header and mode tabs remain fixed; the Field Library index is a flex column
whose only overflow is its concept-book list; and the selected book section is
the only reading-content scroller. The Codex therefore remains a finite book
surface even as chapter context, encounter evidence and notes grow. No state,
sync, reward, learner-file or PTY contract changed.

Current-source Forge tests are **40/40**. Clean archive build and browser K&M
remain the publication visual gates; the hosted and real-device milestones are
unchanged.

## Current checkpoint — 2026-09-17 — friend bundle custody repair

The distribution audit found and fixed F-131: because `progress.json` is tracked,
`git archive HEAD` could put a player save in the friend folder/ZIP despite the
dirty-tree guard. The packager now strips and verifies the save, Tutor/Dungeon
notebooks and `notes/` in temporary staging before output, and onboarding no
longer describes a committed baseline save as part of the bundle. This keeps
player state behind the canonical gateway and does not alter the live checkout,
PTYs or hosted scope.

Post-fix package `QuestLab-2f5a4fe` folder/ZIP scans returned no protected save
or notebook paths, while the manifest and key onboarding/launcher files were
present. Clean archive frontend tests/build passed **60/60** and **1,346
modules**. Real friend-machine installation remains a separate acceptance gate.

## Current checkpoint — 2026-09-17 — secondary RPG icon cleanup

F-132 removes the remaining emoji fallback from Codex mastery and companion/
Homestead presentation. These surfaces now use explicit monochrome SVG shield,
flame and book icons, keeping metrics stable across Windows/Linux fonts while
leaving state authority, rewards and PTY behavior unchanged.

Current-source Forge tests are **42/42**; clean archive frontend tests/build
passed **61/61** and **1,346 modules**, and WSL backend discovery passed
**108/108**. Browser K&M remains the visual gate; hosted/device milestones are
unchanged.

## Current checkpoint — 2026-09-17 — Codex bookshelf hierarchy

F-133 responds to the remaining Codex presentation complaint. The concept
index is now a finite five-book shelf with explicit paging, so it cannot turn
into an endless list. The selected book has a quieter paper/spine hierarchy,
chapter and encounter markers use SVGs, and unmatched searches remain empty
instead of falling back to the entire library. The canonical projection,
state-service note writes, Battle Shell, revision polling and PTY lifecycles
remain unchanged.

Current-source Forge tests are **43/43**. Clean Linux archive frontend tests
pass **62/62** and the Vite build transforms **1,346 modules**. Browser K&M is
still the open visual gate because the in-app webview cannot attach (F-080).

## Current checkpoint — 2026-09-17 — Character/Homestead SVG icon parity

F-134 completes the local RPG icon-language cleanup left after the Codex/HUD
work. Character armor/trinket/title badges, achievement markers and Homestead
window/desk/shelf props now render through the shared monochrome `RouteIcon`
paths with explicit 24px-grid sizing. The slice does not touch state authority,
reward events, revision polling, learner files or PTY sessions.

Current-source Forge tests are **44/44**. Clean Linux archive frontend tests
pass **63/63** and the Vite build transforms **1,346 modules**. Browser K&M
remains the visual publication gate (F-080); hosted sync and real-device
acceptance remain separate roadmap gates.

## Current checkpoint — 2026-09-17 — Codex fixed-page evidence reader

F-135 closes the remaining finite-reader gap after the bookshelf work. The
selected Codex book body is viewport-bounded and no longer grows the generic
Forge page; Encounter and Notes sections page their targets three at a time,
while the selected page body is the only deliberate scroll owner for long
definitions or learner notes. Definitions, examples, active encounter detail
and canonical note writes remain available without changing state authority,
revision polling, learner files or PTY sessions.

Current-source Forge tests are **45/45**. Clean Linux archive frontend tests
pass **64/64** and the Vite build transforms **1,346 modules**. Browser K&M
remains the visual publication gate (F-080); hosted sync and real-device
acceptance remain separate roadmap gates.

## Current checkpoint — 2026-09-17 — Route/quest/Dungeon SVG marker parity

F-136 finishes the local status-icon consistency pass. Font-dependent symbols
were removed from Hub chapters, quest objectives/mob paths, boss phases and
Dungeon map/room markers; `RouteIcon` now supplies their monochrome paths with
explicit sizing. Labels and state-owned status semantics remain intact.

Current-source Forge tests are **46/46**. Clean Linux archive frontend tests
pass **65/65** and the Vite build transforms **1,346 modules**. Browser K&M
remains the visual publication gate (F-080); hosted sync and real-device
acceptance remain separate roadmap gates.

## Current checkpoint — 2026-09-17 — Codex compact active-quest rail

F-137 removes the last stacked chapter rail from the Codex reading room. The
active chapter is selected through a bounded native selector with state-owned
locked/current/complete labels; the current encounter summary remains visible,
while the bookshelf stays paged and the selected book keeps its bounded reader.
The obsolete chapter-list CSS is gone, preventing the old infinite-feed shape
from returning through a legacy rule. This is presentation-only: state-service
authority, reward events, revision polling, learner files and PTY lifecycles
remain unchanged.

Current-source Forge tests are **47/47**. Clean Linux archive frontend tests
pass **66/66** and the Vite build transforms **1,346 modules**. Browser K&M
remains the visual publication gate (F-080); hosted sync and real-device
acceptance remain separate roadmap gates.

## Current checkpoint — 2026-09-17 — frontend dependency preflight

F-138 caught a partial Windows/OneDrive `node_modules` tree that made Supabase
imports and the Vite build fail after a cross-environment install. The local
cache was repaired from the lockfile without stopping the existing Forge or
PTY processes. The launcher now checks the Vite, Supabase, Functions and native
Rollup package manifests before starting and gives a platform-specific repair
message. WSL installs against the live OneDrive tree remain unsupported; clean
Linux dependency installs are the distribution path.

Windows frontend tests are **66/66**, the Windows Vite build transforms
**1,346 modules**, focused launcher tests are **15/15**, and WSL backend tests
are **109/109**. Browser K&M remains the visual gate (F-080); hosted sync and
real-device acceptance remain separate roadmap gates.

## Current checkpoint — 2026-09-17 — Codex folio overflow repair

F-139 closes the remaining visible Codex complaint after the bookshelf and
active-quest compaction work. The selected concept is now rendered as one
bounded folio page instead of a full-height reading scrollbar. Encounter/Notes
targets and mastery records use explicit pagers; only an individual long
workspace note can scroll inside its own small note box. This remains a
presentation-only slice and does not change state authority, revision polling,
rewards, sync, learner files or PTYs.

Windows frontend tests are **67/67** and the Vite build transforms **1,346
modules**. Browser K&M remains the visual publication gate (F-080), while
hosted/device milestones remain unchanged.

## Current checkpoint — 2026-09-17 — hosted migration preflight

F-140 rechecked the linked Supabase project read-only. The remote ledger is
missing the committed device-ownership and campaign-projection migrations
(`20260916000100` and `20260917000100`); the Supabase dry-run proposes exactly
those two files. No hosted write or seed was performed. The next Milestone C
step is explicit approval to apply those migrations, followed by authenticated
two-device live-projection and PTY-preservation acceptance. Local Forge remains
green, but this hosted gate is not complete.

## Current checkpoint — 2026-09-17 — Codex compact folio viewport

F-141 removed the remaining legacy 520px Codex library height that could push
the selected book beyond the Forge viewport. The Codex hero is shorter and the
books/battle tab page, library, index, book and visible section now share one
bounded flex budget. Growing collections continue through explicit shelf,
record and mastery pagers rather than a page-length scroll feed.

Windows frontend tests are **68/68** and the Vite build transforms **1,346
modules**. This is a presentation-only repair; browser K&M (F-080), hosted
migrations and real-device acceptance remain open.

## Current checkpoint — 2026-09-17 — guarded hosted migration preflight

F-142 adds a fail-closed operator boundary for the pending Milestone C schema.
`tools/questlab_supabase_migrate.py` verifies that the linked ledger has exactly
the two committed campaign migrations, verifies the dry-run, and requires the
explicit `--apply --confirm APPLY_QUESTLAB_CAMPAIGN_MIGRATIONS` token before a
real push. The default invocation is read-only and does not seed or write
player state.

The guard returned **MIGRATION GUARD: GREEN** and its focused tests pass **5/5**.
Applying the migration, authenticated two-device projection and PTY acceptance
remain approval-gated.

## Current checkpoint — 2026-09-17 — Codex primitive height cleanup

F-143 removes the stale 620px minimum from the shared `.codex-library`
primitive. The viewport-pinned Codex now owns its height from the first matching
rule, reducing compatibility-shell cascade risk while retaining the finite
bookshelf, encounter/notes and mastery pagers. A frontend source assertion
guards the primitive against any future 5xx/6xx feed-sized minimum. Windows
frontend tests **69/69** and the Vite build (**1,346 modules**) pass. No state,
sync, learner-file or PTY behavior changed; visual K&M (F-080) remains the
relevant unverified check.

## Current checkpoint — 2026-09-17 — protected-path friend packaging

F-144 closes a distribution edge case exposed by the current protected
checkout: the friend packager stopped on a user-owned untracked nested
directory before archiving committed source. `tools/questlab-package.ps1` now
accepts an exact `-IgnoreUntrackedPath` only after validating that the path is
inside the checkout and untracked. The package still comes exclusively from
`HEAD`, strips `progress.json`, `tutor.py`, `dungeon.py` and `notes/`, and has no
blanket dirty-source bypass. Launcher-contract coverage is **16/16**; a
post-commit run created a 134-entry ZIP from `83f302c` with every protected
path absent and the nested directory untouched.

## Current checkpoint — 2026-09-17 — fresh ext4 distribution verification

The published branch was cloned into a disposable WSL ext4 directory outside
OneDrive. Fresh Python and frontend dependencies were installed with the
native Linux toolchain; frontend tests **69/69**, Vite (**1,346 modules**) and
backend tests **115/115** passed. The temporary checkout was removed and its
absence verified. This strengthens F-033/F-058 distribution evidence without
claiming the real CachyOS laptop, live projection K&M or physical PTY gate.

## Current checkpoint — 2026-09-17 — native Linux pre-launch report

F-145 adds `tools/questlab-native-report.py --strict`, a read-only one-shot
report for the physical CachyOS acceptance. It checks platform/kernel,
toolchain versions, expected branch/upstream, executable launcher/state CLI,
frontend manifests and native Rollup presence before Forge launch. It does not
install, fetch, write a report, call Supabase or touch player state. Actual
CachyOS live projection, K&M and PTY acceptance remain F-058 gates.

The strict report proof is green on a clean ext4 clone (native Rollup present;
launcher-contract coverage **17/17**) and the temporary clone was removed.

## Current checkpoint — 2026-09-17 — Codex reader contract

F-146 consolidates the Codex presentation after the remaining “ugly infinite
scroll” complaint. The surface now has a compact header, short Books/Battle
Shell tabs and a fixed two-pane folio. The left rail is bounded, the shelf is
five books at a time, and record/mastery collections use explicit pagers. The
Codex root and Books tab do not own an outer vertical scrollbar; only small
mobile/index, code-example and intentionally long note bodies can scroll.

Windows frontend tests are **70/70** and Vite transforms **1,346 modules**.
This is a local presentation repair. Browser K&M (F-080), hosted migration,
physical CachyOS and two-device acceptance remain open.

## Current checkpoint — 2026-09-17 — Codex reader visual hierarchy

F-147 adds a field-guide treatment on top of the bounded Codex reader: a
compact metric strip, quiet paper/ink reading surface, clearer bookshelf
spine and more legible highlighted example blocks. This remains
presentation-only; the canonical projection, reward events, notes gateway,
revision polling and PTY lifecycle are untouched.

Windows frontend tests are **71/71**, Vite transforms **1,346 modules**, and
the supported WSL backend suite is **116/116**. Browser K&M (F-080), hosted
migration, physical CachyOS and two-device acceptance remain open.

## Current checkpoint — 2026-09-17 — Codex fallback scroll cleanup

F-149 removes the last base stylesheet scroll owners from the Codex bookshelf
and encounter picker (`max-height: none; overflow: visible`). React's bounded
book/record/mastery paging remains authoritative; code examples and long note
bodies retain only their intentional local scroll. Windows frontend source
tests are **72/72** and the Vite production build remains green. Browser K&M
acceptance (F-080) is still open because the local CUA browser could not attach
to the live port in this session.

F-150 removes the remaining mobile `max-height: 180px` bookshelf fallback;
narrow Codex windows now use the same explicit React paging contract.

F-151 also hides locked future chapter/encounter identities in Hub and legacy
Journal contexts, preserving the no-future-question/answer disclosure rule
while leaving active and defeated records state-owned and visible.

F-152 fixes launch continuity by removing the `lastSeenAt` background heartbeat;
only actual user activity and explicit splash dismissal refresh the idle marker.
