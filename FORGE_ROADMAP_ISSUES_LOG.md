# Forge roadmap issue log

This is the persistent review log for the local Forge roadmap. Keep findings
here rather than in a disposable test directory so a workstation reset does
not erase the review trail.

## Review — 2026-09-15

Scope: the bounded PYR context bridge (`21dbae7`), challenged verdict boundary
(`4331bff`), Codex attempt recording (`b48997e`), and the follow-up Battle
submission worktree changes. Review lens: security, correctness, resource
limits, concurrency, and regression coverage.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-001 | P1 | Verdict trust | The raw local AI terminal can still choose `correct` or `incorrect`; the server cannot prove which model produced the decision. The new submission/digest binding prevents changing the submitted answer, but provider identity remains a local trust boundary. | Open until a provider-authenticated adjudicator exists; explicitly documented, never presented as proof by itself. |
| F-002 | P1 | Context privacy | A selected secret-looking file could previously be forwarded in the PYR context. | Fixed: secret-looking paths are rejected by the context bridge. |
| F-003 | P1 | Resource limits | `bounded_file` previously read the complete file before truncating it, defeating the intended memory bound. | Fixed: the bridge reads only the bounded prefix and reports the actual file size. |
| F-004 | P2 | Portability | Git output used text decoding delegated to the host locale; non-UTF-8 output could turn a context request into a 500. | Fixed: subprocess output is decoded as UTF-8 with replacement. |
| F-005 | P2 | Rule authority | The verdict route selected raw counterattack damage instead of asking the state service to derive it. | Fixed: encounter-index damage is canonicalized in `state.py`; the route passes only the index. |
| F-006 | P2 | Submission integrity | A verdict was previously bound only to revision/mob, so a caller could claim an unrelated answer/evidence. | Fixed: one pending submission binds objective, answer digest and server-issued evidence ID; replay/mismatch fails closed. |
| F-007 | P2 | Player flow | The UI previously had no way to submit a Battle answer to the selected provider. | Fixed: Quest Journal now offers an optional answer form and sends a bounded adjudication prompt; no progression occurs until the provider calls the verdict boundary. |
| F-008 | P3 | Lifecycle | Monaco cursor-selection subscriptions were not explicitly disposed when the Forge unmounted. | Fixed: AppV2 disposes the current selection listener on unmount. |
| F-009 | P2 | Concurrency | The challenge is a single process-global slot, so two tabs or overlapping provider submissions can invalidate one another. | Open: acceptable for the current single-player local runtime; replace with account/tab-scoped challenge storage before multi-user or hosted use. |
| F-010 | P2 | Local threat model | The loopback API intentionally has no hosted user authentication; another local process can attempt to use a valid challenge while the Forge is open. | Open: retain loopback-only binding and add provider authentication before exposing this beyond the trusted workstation. |
| F-011 | P3 | Payload hardening | Context/verdict request models previously had no field-size limits even though downstream helpers were bounded. | Fixed: request fields now have explicit Pydantic limits plus byte-level validation. |
| F-012 | P2 | Provider context | The first Battle prompt carried the answer and objective metadata but not the bounded code, terminal, git, quest, and encounter projection returned by the context bridge. | Fixed: the provider prompt now includes that bounded current projection and still excludes future encounter prompts/answers. |

### Review result

No additional critical correctness or data-loss issue was found after the
fixes above. F-001, F-009 and F-010 are deliberate trust/concurrency limits,
not hidden completion claims. They remain release gates for a hosted/provider-
authenticated Battle flow and are tracked alongside the existing two-device
mailbox acceptance gate before Tauri packaging.

### Verification recorded with this review

- WSL backend unit suite: 34 tests passing.
- Frontend source/runtime suite: 22 tests passing after the Battle form
  assertions.
- Windows Vite production build: passed after the final frontend changes.
- Existing personal `progress.json` and `tutor.py` are out of scope and must
  remain unstaged.

## Review — 2026-09-15 — Dungeon and Practice foundation

Scope: the first Infinite Dungeon save-state/projection slice and the separate
Practice surface. Review lens: authority, restart behavior, question isolation,
player-facing mode boundaries, and failure behavior.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-013 | P2 | Dungeon authority | A writable workspace `dungeon.py` could otherwise become a second run save and drift from the campaign cache. | Fixed: the active run and editor buffer live in canonical state; the file is an atomic projection, hidden from the tree, and direct file reads/writes are rejected. |
| F-014 | P2 | Question isolation | Reusing one editor buffer across generated questions could carry an old answer or provider tip into a new room. | Fixed: validated question rotation clears the canonical buffer and emits `editor_reset`; the projection and PYR context expose only the current question. |
| F-015 | P2 | Restart durability | A browser/workstation restart could lose the active Dungeon room or current answer if it existed only in React/Monaco state. | Fixed for committed checkpoints: floor, room, question, loadout and editor content are restored from the state service. An edit made after the last checkpoint is not promised across a hard power loss. |
| F-016 | P2 | Run lifecycle | A dead run could accidentally be resumed or have its starter loadout mutated in place. | Fixed: death is a terminal state that clears the question/buffer; starting again creates a new run ID and fresh starter loadout while preserving the summary. |
| F-017 | P2 | Mode boundary | Practice assistance could accidentally grant Campaign/Dungeon rewards or become a hidden Dungeon variant. | Fixed at the UI/provider contract: Practice is an independent unlimited request surface and explicitly forbids verdicts, rewards, HP, Dungeon score and `tutor.py`; Campaign retains a dedicated Tutor Notebook surface for collaborative scratch work. Persistent Practice evidence remains future work. |
| F-018 | P2 | Cloud scope | The local Dungeon checkpoint is not yet part of the hosted player-state projection. | Open by design: generation, verdict progression, rooms, scoring, leaderboard state and cross-device Dungeon resume wait until the provider-auth and hosted-state gates are closed. |
| F-019 | P3 | Product completeness | The current screen has a deterministic starter question and checkpoint controls, but no adaptive generator, rest/market rooms, death UI, leaderboard or Practice history. | Fixed locally: the current-branch state service and Forge now cover adaptive recorded-weakness focus, progressive rooms, rest/market, death reset, local leaderboard and the independent Practice surface; isolated K&M acceptance is recorded below. Hosted Dungeon state/leaderboards remain F-018. |
| F-020 | P2 | Checkpoint race | A delayed autosave from the previous Dungeon question could overwrite the newly rotated room buffer. | Fixed: every checkpoint carries the current `question_id`; stale or mismatched saves fail closed with HTTP 409. |
| F-021 | P2 | Projection resilience | Campaign polling could fail if the disk `dungeon.py` projection was malformed or could drift until a dedicated Dungeon request ran. | Fixed: campaign polling materializes the controlled projection and falls back to a safe invalid/empty projection without taking down the campaign HUD. |
| F-022 | P2 | Editor responsiveness | Autosave reused the global busy flag and could overwrite edits that arrived while a save was in flight. | Fixed: Dungeon uses a dedicated saving flag and content ref; a save only clears dirty state when the captured content is still current. |
| F-023 | P3 | Notebook write boundary | `tutor.py` could be reached through generic file routes and bypass the controlled teaching boundary. | Fixed: the Campaign Tutor Notebook uses the dedicated `/api/tutor` surface; direct file read/write/format routes reject `tutor.py`, while Practice remains a separate no-file mode. |
| F-024 | P3 | PTY protocol/lifecycle | Unknown JSON envelopes could be typed into the shell, and closing the PTY master before reaping made descriptor reuse possible. | Fixed: both terminal bridges ignore unknown control envelopes and reap the child before closing the master descriptor. |
| F-025 | P2 | Runtime checkout drift | The visible Forge on port 5173 was serving `/home/lazi/projects/python-tutorial-DiddyDungeon` on `feature/quest-lab-ide`, while this work was being developed in the `feature/cloud-sync-desktop` checkout. That made newer Dungeon/Practice/sync changes appear missing and reintroduced the old broad top-stat selector. | Open until the launcher points at the intended checkout. The active runtime's frontend-only CSS/icon polish was patched in place without restarting its backend or either PTY; the canonical branch remains separately verified on port 5174. |
| F-026 | P2 | Campaign completion authority | Clearing the final mob previously left the project without a visible boss gate, and there was no state-service command that could record the required integrated behaviour, explanation and interview before boss rewards. | Fixed in the current slice: final mob clear opens `boss_status=available`; internal `record_boss_clear` derives the documented +100 XP, project/boss counters, achievements and companion evolution from bounded evidence IDs. The action remains internal until provider-authenticated boss adjudication is added. |
| F-027 | P2 | PTY state routing | PTYs run in the quest workspace, so `python -m ide.state_cli` could fail to import and raw `progress.json` edits could silently land in the non-authoritative workspace copy without changing the live HUD or revision. | Fixed for the supported command path: PTY environments now expose the repo package, backend port, canonical/legacy paths and a `questlab-state` wrapper. Direct workspace-file edits remain intentionally non-authoritative and are covered by tests; PYR must use named gateway commands. |

### Full-roadmap execution review — 2026-09-15

The approved defaults are recorded in `ROADMAP_EXECUTION_PLAN.md`: boss
validation requires behaviour/explanation/interview evidence; Dungeon is
local-first before hosted leaderboard transport; friend sharing is opt-in and
does not expose code/private notes; AI custom mobs use recorded weakness
evidence and state-service validation; Campaign Tutor and Practice remain
separate; current PTYs are not reset during development.

Claude Sonnet was attempted as the chief reviewer from WSL, but its configured
CLI returned `Not logged in · Please run /login` even after the user reported a
separate Claude login. No Claude approval is claimed. The primary agent is the
fallback reviewer until a successful read-only review is available.

### Dungeon foundation verification

- WSL state-service tests cover restart restoration, active-run protection,
  hidden-question-field rejection, rotation blanking and death/new-run reset.
- Context-bridge tests prove `/api/pyr/context` receives the canonical
  `dungeon.py` projection, while direct `/api/file` access is denied.
- Frontend tests cover the separate Dungeon/Practice routes; the production
  Vite build remains green.

### Dungeon hardening verification — 2026-09-15

- WSL backend suite: 39 tests passed, including stale-question checkpoint
  rejection, malformed-projection campaign recovery and legacy `tutor.py` route
  rejection; terminal protocol/lifecycle behavior was exercised in the live
  browser PTY check.
- Frontend source/runtime suite: 24 tests passed; Windows Vite production build
  passed.
- Manual Forge acceptance used only the browser K&M automation surface (no
  Playwright) against a disposable isolated state copy. Revision polling
  updated the HUD from Level 2 / 50 XP / 55 coins to Level 2 / 55 XP / 62
  coins after a validated reward, Quest Journal Resolve changed from 8/8 to
  4/8 after a validated Mob 3 objective, and Codex gained the observed Hitman
  encounter record. Character and Homestead reflected the same canonical
  projection; shell and AI PTYs stayed `CONNECTED` through a backend restart
  and checkpoint save.
- The top HUD heart, coin, flame, shield and sword SVGs were visually checked
  before their values; DEV/RANK stayed unchanged and no nested stat pills were
  present.
- The test copy was isolated under `/tmp/questlab-browser-manual`; the real
  campaign save, legacy evidence files, user PTYs and Supabase state were not
  touched.

## Verification update — 2026-09-15 — local playable loops and runtime identity

This entry supersedes the earlier “foundation” status for the local roadmap
slices. It records the current `feature/cloud-sync-desktop` checkout and a
fresh disposable runtime at `http://127.0.0.1:5181/`; the existing 5173/5174
processes and their PTYs were not restarted.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-028 | P2 | Dungeon provider boundary | Dungeon answers needed a validated, question-bound provider verdict before score, run coins, damage or room rotation. | Fixed: nonce/submission/digest binding and internal `dungeon_record_verdict` now decide all run effects; React only renders the returned event. |
| F-029 | P2 | Practice history | Practice requests had no durable, bounded attempt history. | Fixed: independent sessions and provider-validated attempts are stored through the state service with zero Campaign/Dungeon rewards and no raw answer/prompt persistence. |
| F-030 | P2 | Dungeon progression | The local loop lacked adaptive focus, room transitions, rest/market actions and a bounded leaderboard. | Fixed locally: adaptive focus uses only recorded Codex weakness/incorrect-result evidence; encounters, rest, market, death, banked runs and leaderboard summaries are canonical and answer-free. Hosted transport remains gated. |
| F-031 | P2 | Runtime checkout | An older long-lived 5173 process can still show a different checkout if it was started before the launcher fix. | Fixed for new launches: `ide/quest.py` exports the expected branch and `/api/runtime` exposes workspace/repo/canonical paths plus branch mismatch health. Existing 5173 is intentionally left running and remains a user restart/launch choice. |
| F-032 | P3 | Codex usability | The Codex needed a searchable book/page projection with encounter records and bounded player notes. | Fixed: source/route tests and K&M verified search, concept pages, validated encounter records, and a live saved field note (`CODEX NOTE SAVED`) on the disposable copy. |
| F-033 | P2 | WSL frontend packaging | WSL Vite cannot resolve the Linux Rollup optional package from the shared Windows `node_modules`; this is an environment/dependency-install issue, not a source failure. | Open but bounded: a clean ext4 archive passed WSL `npm ci` and `npm run build`; the launcher now fails early with an actionable Linux Rollup dependency message instead of starting a broken runtime. Install Linux dependencies in a disposable WSL checkout rather than reusing the shared OneDrive tree. |
| F-034 | P2 | Secondary review | Claude Code was previously unauthenticated in the WSL CLI despite the separate desktop login. | Fixed for this checkpoint: authenticated WSL Claude Code completed a read-only roadmap/source review and returned the next-slice plan. It did not edit files or touch `progress.json`/`tutor.py`; its findings are recorded below and remain secondary review, not approval. |
| F-035 | P3 | Dev HMR lifecycle | Editing the running Vite source caused one disposable-runtime terminal websocket reconnect; normal revision polling/navigation did not remount it. | Open dev-only limitation: use the built/started runtime for the acceptance gate. The user's existing PTYs were never restarted; the current disposable children remained stable after HMR settled. |

### Current K&M acceptance evidence

- No Playwright was used. Browser checks used click/scroll/type automation only.
- Initial HUD on the disposable current-branch runtime showed Level 2, 50/100
  XP, 55 coins, visible heart/coin/flame/shield/sword SVG icons, unchanged
  DEV/RANK, and `CHECKOUT feature/cloud-sync-desktop`.
- Quest Journal showed The Empty Table, The Dealer's Hand and The Count Keeper
  defeated; The Hitman was the current Mob 3 with Resolve 8/8 and 38% project
  progress.
- Codex search for `lists` opened the Lists & collections page and the
  validated The Dealer's Hand encounter record without revealing future
  prompts or answers. Character showed the same Level 2/50 XP/55 coins and
  validated Apprentice Coat/First Blood projection.
- Infinite Dungeon start, checkpoint save, provider-gated answer submission,
  banked run and local leaderboard were exercised. A second run started by a
  typed `curl` state-gateway command appeared in the Dungeon view after the
  next revision poll, proving external canonical mutations are observed
  without a browser refresh.
- A typed compare-and-swap sync projection changed the disposable HUD coins
  from 55 to 54; the HUD reflected the new value after the next ~1 second
  revision poll with no refresh. This was a temporary test mutation only.
- Shell and AI PTY surfaces remained `CONNECTED` throughout the navigation and
  external mutation checks. The real canonical save, legacy evidence and
  existing user PTYs were not modified; only the disposable `/tmp` state was
  mutated.
- Read-only process inspection after the checks still showed the disposable
  backend PID `137579` with its two PTY child shells `137684` and `137958`;
  neither terminal was remounted or reset.

### Latest automated gate counts

- WSL backend: 47 tests passed.
- Frontend source/runtime: 29 tests passed.
- Windows Vite production build: passed (existing large-chunk warning only).

## Verification update — 2026-09-15 — friend-ready launcher foundation

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-036 | P2 | Friend launch/runtime identity | A friend could start a different checkout or accidentally use a workspace save unless launch instructions made the authority and branch boundary explicit. | Fixed locally: `tools/questlab-launch.ps1` validates the intended branch by default, converts Windows paths to WSL, delegates to the stable `ide/quest.py` launcher and prints canonical/workspace identity. `FRIEND_ONBOARDING.md` documents setup, read-only `questlab-state runtime`, offline mode and the no-copy save rule. Clean-install and two-device acceptance remain open. |

The earlier WSL Claude CLI attempt reported `Not logged in`. The current
checkpoint has a successful authenticated WSL read-only review; it remains
secondary findings rather than approval.

## Verification update — 2026-09-15 — custody/freshness review follow-up

Claude's authenticated browser review confirmed the engineering boundaries but
flagged custody risks that remain deliberately open: the tracked canonical
`progress.json` can be overwritten by a destructive Git operation, OneDrive
replicates the checkout/save outside the state gateway, and local verdict tokens
are provider-routed rather than provider-authenticated. No save was moved,
untracked or overwritten in response; those choices require an explicit player
migration decision.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-037 | P2 | Runtime freshness | Two checkouts can share `feature/cloud-sync-desktop` while one is behind upstream; a branch-name-only guard cannot distinguish them. | Fixed locally: `/api/runtime` reports HEAD/upstream SHA and ahead/behind counts, the footer shows `CHECKOUT STALE`, and `tools/questlab-launch.ps1` refreshes upstream and refuses stale launch unless `-AllowStaleCheckout` is explicit. |
| F-038 | P2 | Linux onboarding | `questlab-state` was mode `100644` in a clean ext4 clone, so a friend could receive `Permission denied`. | Fixed: committed executable mode `100755`; onboarding includes a one-time chmod recovery for filesystems that strip modes. |
| F-039 | P2 | Offline save custody | The tracked `progress.json` remains a live cache and OneDrive remains a third filesystem replicator. | Open by design: do not touch the player's save or move the checkout silently. Requires an approved ignored per-device save migration and a non-OneDrive clean-install/two-device test. |
| F-040 | P2 | Duplicate projection polling | The legacy DOM combat shell and React both polled the campaign revision every second, duplicating full fetch/git work and contributing to sync churn. | Fixed: `combatShell.js` now consumes React's `questlab:campaign-updated` event only; source test asserts no second revision timer/fetch. |

The post-fix automated counts are 56 WSL backend tests, 30 frontend tests and
a green Windows Vite production build. No Playwright was used.

## Verification update — 2026-09-15 — checkout-scoped sync metadata

The next local Slice 7 boundary is now implemented without changing canonical
save custody or starting hosted player-state transport.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-041 | P2 | Same-origin checkout mailbox | Device IDs, labels, cloud cursors and offline outboxes were keyed by user/browser storage alone. Two local checkouts sharing a browser origin could therefore reuse recoverable sync metadata even though their state-service caches were separate. | Fixed locally: `/api/runtime`, `/api/campaign` and the cheap revision probe expose an opaque SHA-derived checkout namespace; AppV2 resolves it before cloud auth restoration; `SyncEngine` partitions device IDs, labels, cursors and outboxes by that namespace. Raw filesystem paths never enter device rows or cloud payloads. |

The namespace change deliberately does not merge or delete pre-existing
legacy metadata. If the runtime cannot provide its identity, the engine keeps
the old unscoped keys as a compatibility fallback; once an identity is known,
the new checkout starts with its own mailbox and ordinary revision/conflict
rules decide whether a local or cloud projection may be applied. This avoids
silently attributing one checkout's offline writes to another.

Focused and full gates for this slice: 56 WSL backend tests, 30 frontend tests,
targeted Python compilation and a green Windows Vite production build. A
fresh browser K&M run against a newly started disposable runtime then passed:
the UI booted with the opaque checkout namespace, showed Level 2 / 55 XP / 62
coins and all five monochrome SVG stat icons, and a typed compare-and-swap
state-service mutation changed the HUD and Character to 63 coins without a
refresh. Quest Journal stayed on Mob 3 The Hitman and Codex retained the
validated encounter records; both shell and AI panes remained `CONNECTED`.
The disposable backend/frontend were stopped afterward; the existing
5173/5174 PTYs and live saves were not restarted.

## Verification update — 2026-09-15 — clean Linux frontend install

F-033 was narrowed with a clean-filesystem check. A fresh `git archive` of the
current branch was extracted under `/tmp/questlab-clean-linux`; `npm ci` in the
WSL checkout installed 84 packages, and `npm run build` completed with 1,344
modules transformed. The earlier failure is therefore specific to the shared
OneDrive `node_modules` tree missing the Linux Rollup optional package, not a
source/build failure. The OneDrive environment still needs a disposable Linux
dependency install (or a documented cleanup) before the Windows launcher can
be called clean-install verified; no dependency directory in the player's
checkout was replaced.

## Verification update — 2026-09-15 — campaign loading guard

The live current-branch tab briefly exposed the cost of a stale or miswired
frontend/backend pair: while `/api/campaign` was unavailable, the React shell
rendered believable starter defaults (Level 1, zero XP and zero coins). That
could be mistaken for lost progress even though the canonical save was intact.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-042 | P2 | Loading-state integrity | A missing campaign projection fell through to starter-looking HUD, character and game-screen defaults. | Fixed locally: HUD/quest banner use an explicit `SYNCING` state, RPG screens wait for the canonical projection, the context panel explains the wait, and Settings remains reachable. No progression write or PTY lifecycle is involved. |

Focused/frontend gates for this slice: 31 frontend tests, 56 WSL backend
tests, and a green Windows Vite build (1,344 modules). The live K&M tab then
settled on the canonical Level 2 / 50 XP / 55 coins projection with both PTYs
still `CONNECTED`; no browser refresh or save mutation was used.

## Review — 2026-09-15 — Claude read-only roadmap pass

Claude Code was available again and reviewed the handoff, roadmap, issue log,
implementation report and current source/tests without editing files or touching
`progress.json`/`tutor.py`. Its recommendation is to close the remaining local
Slice 7 boundary before starting Milestone C hosted player-state transport:

- keep Supabase migrations, seeding and new cloud tables out of the next slice;
- prepare an explicit, per-device local-save custody migration keyed by the
  existing opaque checkout namespace, with copy-once/idempotent behavior and a
  visible migration status;
- prove clean ext4 install plus two isolated checkout/device launches, including
  independent state paths and no cross-talk;
- retain the existing provider-authentication gates F-001/F-009/F-010 and do
  not claim hosted Dungeon or social readiness.

This is a plan/review finding, not approval to migrate the player's live save.
The current tracked canonical cache remains untouched until an explicit custody
choice is made; implementation work must use disposable fixtures and an opt-in
boundary.

## Verification update — 2026-09-15 — read-only custody preview

The first safe implementation slice of Claude's custody recommendation is now
in place. The state service exposes `/api/state/custody` and includes the same
bounded report in `/api/runtime`; `questlab-state custody` reads that report
through the localhost gateway. It derives an opaque per-device destination,
reports source/destination revisions and exact digests, and distinguishes
`approval-required`, `already-local`, `conflict`, `current` and
`no-source-found` without selecting a newest file.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-043 | P2 | Custody migration safety | The roadmap needed a way to inspect the proposed per-device destination without accidentally moving or merging the live save. | Fixed locally: the read-only preview and the separately invoked gateway migration are copy-once, revision-stable and conflict-safe. The real player's migration and default-launch switch remain explicitly approval-gated. |

The new endpoint/CLI and existing state-authority tests pass in the WSL suite
(58 backend tests, 31 frontend tests);
the live canonical save and workspace legacy file were not touched and remain
outside the write path.

## Verification update — 2026-09-15 — isolated local-device proof

Two disposable ext4 state roots were launched from the clean Linux checkout.
The custody preview returned different opaque namespaces (`checkout-ca575e…`
and `checkout-84f01e…`) and separate canonical paths. A typed state-service
projection mutation advanced device A from revision 0 to 1 while device B
remained at revision 0; neither workspace contained a second `progress.json`.
The mutation was disposable and both backends were stopped afterward.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-044 | P2 | Two-device local isolation | Slice 7 needed evidence that separate local roots do not share a save before hosted sync is attempted. | Verified locally with two disposable state services and K&M on the clean runtime. This proves isolation only; hosted mailbox synchronization and real save-custody migration remain open. |

| F-046 | P2 | Friend bundle custody | A friend-facing bundle could accidentally be made from the dirty OneDrive working tree, carrying the player's uncommitted save or Campaign `tutor.py` into distribution. | Fixed locally: `tools/questlab-package.ps1` archives committed `HEAD` only, refuses unrelated dirty source files, emits a manifest/zip, and leaves the live save and untracked tutor notebook out. Clean-install launch and Tauri desktop proof remain separate gates. |
| F-047 | P2 | Live RPG projection acceptance | The shared revision/event architecture needed a fresh end-to-end K&M proof that rewards, Resolve, mob unlocks, Codex, Homestead economy, Tutor and Practice all stay coherent without a refresh. | Fixed locally: the disposable current-branch runtime passed the campaign reward/Resolve/mob-clear/Codex/Homestead/Tutor/Practice sequence below with both PTYs connected. Hosted transport remains gated by F-018/Milestone C. |
| F-048 | P3 | HUD sync layout stability | Revision polling and the initial campaign load could change stat text widths while nested icon/value spans participated in the pill layout, making the top bar visibly jump even after the SVG ownership fix. | Fixed locally: direct stat pills now reserve a compact minimum width/height, keep their value on one line, and reserve the SVG/value slots. Nested spans remain unstyled as pills; compact/adventurer selectors stay direct-child scoped. |

## Verification update — 2026-09-15 — WSL launcher dependency preflight

The guarded launcher now checks for a native `@rollup/rollup-linux-*` optional
package when it is running under WSL. If the shared OneDrive dependency tree
was installed on Windows, it exits before spawning either the backend or the
frontend and explains that `npm ci` must run inside the WSL checkout (or a
clean Linux filesystem). This is a fail-fast guard only: it does not mutate
`node_modules`, the canonical save, or any existing PTY.

The updated contract test covers both a missing package and a native package
using isolated temporary trees. The full gate is now 59 WSL backend tests, 31
frontend tests, a green Windows Vite production build (1,344 modules), and
successful Python compilation. No Playwright was used.

A real WSL invocation from the shared OneDrive checkout produced the same
fail-fast message and exited before attempting the disposable ports requested
for that check; no backend/frontend process was spawned by the guard.

## Verification update — 2026-09-15 — opt-in custody gateway

The bounded migration half of Slice 7 is now implemented behind
`POST /api/state/custody/migrate` and `questlab-state custody-migrate`. The
caller must provide the reviewed source revision and the exact
`MIGRATE_LOCAL_STATE` confirmation token; the server derives the destination
from the configured opaque checkout namespace and accepts no arbitrary path.
The gateway copies the canonical bytes atomically, writes a local custody
marker, preserves the source revision/events, and returns `already-local` on
an identical retry. Symlinks, divergent destinations, stale revisions,
workspace/legacy destinations and missing markers fail closed. No real save
was migrated in this checkpoint.

Temporary-fixture tests cover route authorization, copy-once/idempotent
retries, marker integrity, revision races and symlink rejection. The full WSL
backend suite is now 66 tests; the frontend suite remains 31 tests and the
Windows Vite build remains green. Launcher opt-in and the real-save approval
gate remain open; hosted Supabase transport is unchanged.

## Verification update — 2026-09-15 — stale runtime replay

A click/scroll/type-only replay against the isolated current-branch runtime
settled on Level 2 / 50 XP / 55 coins, The Hitman at 8/8, three cleared mobs,
three Codex encounter records, 55 Homestead coins, visible heart/coin/flame/
shield/boss SVG icons and `CONNECTED` shell/AI panes. The pre-existing 5174
tab still showed its old starter/no-branch projection, so it was deliberately
left running; this is the already logged F-025/F-031 stale-runtime choice,
not a live-save reset. New launches must use the guarded launcher after the
WSL dependency preflight passes.

## Verification update — 2026-09-15 — launcher custody opt-in

The guarded Windows wrapper now exposes `-MigrateLocalState`, which passes
`--use-local-state` to `ide/quest.py`. The launcher prints the gateway preview,
requires the exact `MIGRATE_LOCAL_STATE` token interactively (or an explicit
non-interactive confirmation flag), and switches the state path only for that
launch. A missing confirmation exits before backend/frontend startup. Fixture
tests proved both refusal-without-copy and confirmed copy/switch behavior; the
canonical revision and source bytes remain unchanged.

## Verification update — 2026-09-15 — React-owned HUD stat icons

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-045 | P2 | HUD icon lifecycle | Forge v2 still emitted emoji stat glyphs and depended on the DOM polish observer to replace them. A revision rerender could briefly recreate the glyph nodes and let the broad descendant styling regress into empty nested pills. | Fixed: AppV2 now renders the heart, coin, flame, shield and sword as monochrome SVG children; `uiPolish.js` skips React-owned stat values. The existing legacy fallback remains for the older surface. |

The frontend suite remains 31 tests and the Windows Vite build transforms 1,344
modules. A click-only K&M browser check on a disposable current-branch tab
showed Level 2 / 50 XP / 55 coins with all five SVG icons visible, then kept
the icons visible after navigating to Codex. The disposable frontend proxy's
terminal reconnect state was not used as PTY evidence; the managed connected
PTY acceptance remains the prior checkpoint.

## Verification update — 2026-09-16 — isolated Infinite Dungeon K&M acceptance

The current-branch Dungeon loop was exercised in a disposable backend/save
with browser clicks, scrolling and typing only (no Playwright). The campaign
projection loaded at Level 2 / 50 XP / 55 coins. Selecting `lists` and entering
the Dungeon produced the fresh starter loadout (Apprentice Coat, no trinket,
one heal and zero run coins) and a `DUNGEON RUN STARTED` event. A checkpointed
code answer was submitted through the visible provider bridge; the disposable
state service then recorded a validated verdict and the browser updated live
to the next room with `+10 score`, `+5 run coins`, a blank editor and the next
question. Three further validated room transitions covered code, bug-hunt and
true/false questions, with the blank buffer recreated on each rotation.

The run then reached a REST room, a MARKET room and a later encounter without
refreshing. The full-health REST action was correctly disabled in this run;
the rest/heal mutation remains covered by the backend suite. Buying a Field
Ration produced the visible `-12 run coins` purchase event, leaving 13 run
coins. Banking the run produced `RUN BANKED 50 score` and a local leaderboard
entry (`#1 · lists 50 F1 · complete`). The K&M session and its disposable
processes were stopped and removed afterward; no user save, long-lived PTY or
hosted state was touched. This closes the local product-completeness finding;
hosted Dungeon persistence and cross-device leaderboards remain intentionally
open under F-018/Milestone C.

## Review — 2026-09-16 — Claude roadmap/source pass

Claude Code read the roadmap, handoff, Dungeon design, issue log and current
source in read-only mode. It confirmed that the React-owned HUD icons and the
Dungeon contracts are source-backed, while noting that it did not run tests or
browser checks. It identifies real hosted two-device Supabase acceptance as
the primary remaining Milestone C blocker and keeps provider trust findings
F-001/F-009/F-010 open. It recommends no expansion of Dungeon/Codex into
hosted player-state until that gate is closed. Its suggestion to make custody
migration the default was not adopted: explicit opt-in and no silent save
movement are safety requirements. The roadmap and Milestone A–F handoff are
now cross-linked in the execution plan/report rather than treated as one
combined approval.

## Verification update — 2026-09-16 — reproducible friend bundle

The new `tools/questlab-package.ps1` contract was exercised from the dirty
working tree. It refused an uncommitted source fixture, then succeeded after
the semantic commit using `git archive HEAD`, producing a folder and ZIP with
the branch/commit manifest and `FRIEND_ONBOARDING.md`. The package contained
the committed baseline `progress.json` from `HEAD`, but did not contain the
untracked root `tutor.py` or any uncommitted player-state bytes. The temporary
bundle was removed afterward. This is distribution-custody evidence, not a
claim that a Windows installer or Tauri desktop window has been proven.

## Verification update — 2026-09-16 — live RPG projection and mode boundaries

Using the clean ext4 frontend and a disposable copy of the reconciled save, a
browser K&M run (click, scroll and type only; no Playwright) loaded Level 2 /
50 XP / 55 coins, The Hitman at 8/8 Resolve and both terminal panes
`CONNECTED`. Codex navigation showed the searchable book/page projection;
typing and saving a field note produced `CODEX NOTE SAVED`. A validated
state-service learning reward on the disposable cache changed the HUD and
Homestead purse to 105 coins without refresh. Clicking the enabled Golden
Spark purchase then showed `NEW ITEM`, 25 coins and an Equip action; equipping
it updated the Homestead projection live.

The Campaign Tutor Notebook remained a distinct `tutor.py` surface, while the
Practice destination exposed its independent concept/question controls and
explicit no-Campaign-cost boundary. In Quest Journal, a validated
`choice_flow` objective changed The Hitman from 8/8 to 4/8 Resolve and emitted
`OBJECTIVE VERIFIED`. A second validated `stop_condition` objective immediately
showed `MOB DEFEATED`, `+30 XP`, `+15 Coins`, The Bust Hound unlocked, and a
second Codex encounter observation with two recorded question types. Further
disposable objective mutations cleared the remaining mobs; the browser showed
level-up feedback and `BOSS GATE UNLOCKED The House` with all three bounded
requirements, without revealing future prompts or answers.

The browser never refreshed and neither PTY was remounted. The temporary
backend/frontend and state copy were stopped and removed after the check; the
user's canonical `progress.json`, legacy evidence, root `tutor.py`, existing
runtime processes and hosted state were not touched.

## Verification update — 2026-09-16 — HUD sync layout stability

The top-stat stability patch stayed within the existing SVG/React boundary. It
adds a fixed compact slot for each direct HUD stat pill and explicit icon/value
flex sizing, without restoring emoji or changing the revision/event source.
The WSL frontend suite passed all 31 tests, the full WSL backend suite passed
67 tests, and the Windows Vite build passed with 1,344 modules transformed.
This is a source/build contract check; the
existing disposable K&M projection run remains the live evidence for icons,
rewards and PTY preservation.
