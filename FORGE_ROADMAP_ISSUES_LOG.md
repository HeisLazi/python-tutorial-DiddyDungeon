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
| F-009 | P2 | Concurrency | The challenge is a single process-global slot, so two tabs or overlapping provider submissions can invalidate one another. | Fixed locally in the per-tab isolation slice: opaque session-storage client ids and nonce-bound tab maps now keep pending Battle/Boss/Dungeon challenges independent. Hosted provider authentication and account-scoped storage remain open under F-001/F-010. |
| F-010 | P2 | Local threat model | The loopback API intentionally has no hosted user authentication; another local process can attempt to use a valid challenge while the Forge is open. | Open: retain loopback-only binding and add provider authentication before exposing this beyond the trusted workstation. |
| F-011 | P3 | Payload hardening | Context/verdict request models previously had no field-size limits even though downstream helpers were bounded. | Fixed: request fields now have explicit Pydantic limits plus byte-level validation. |
| F-012 | P2 | Provider context | The first Battle prompt carried the answer and objective metadata but not the bounded code, terminal, git, quest, and encounter projection returned by the context bridge. | Fixed: the provider prompt now includes that bounded current projection and still excludes future encounter prompts/answers. |

### Review result

No additional critical correctness or data-loss issue was found after the
fixes above. F-001 and F-010 remain deliberate trust/security limits; F-009
is now fixed for local multi-tab use; hosted provider authentication and the
two-device mailbox gate still precede Tauri packaging.

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
| F-025 | P2 | Runtime checkout drift | The visible Forge on port 5173 was serving `/home/lazi/projects/python-tutorial-DiddyDungeon` on `feature/quest-lab-ide`, while this work was being developed in the `feature/cloud-sync-desktop` checkout. That made newer Dungeon/Practice/sync changes appear missing and reintroduced the old broad top-stat selector. | Fixed for new launches: the guarded launcher and runtime contract require `feature/cloud-sync-desktop`, upstream freshness and canonical/legacy identity. Open only for already-running legacy processes, which remain a user-approved restart/launch choice; no existing backend or PTY is killed automatically. |
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
| F-033 | P2 | WSL frontend packaging | WSL Vite cannot resolve the Linux Rollup optional package from the shared Windows `node_modules`; this is an environment/dependency-install issue, not a source failure. | Open but bounded: a clean ext4 archive passed WSL `npm ci` and `npm run build`; the launcher now fails early with an actionable Linux Rollup dependency message instead of starting a broken runtime. Never run `npm install`/`npm ci` against the live OneDrive-mounted `ide/frontend/node_modules` from WSL; install Linux dependencies in a disposable WSL checkout instead. |
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
| F-049 | P2 | Clean-install launch proof | The friend distribution path had source-custody/build evidence but no fresh checkout proof that the documented backend/frontend setup launches the Forge with both PTYs and live state projection. | Fixed locally for a clean ext4 WSL checkout: cloned pushed `8f4ec71`, installed `.venv` and frontend dependencies, built 1,344 modules, launched the stable-PTY runtime, and observed a gateway reward reach the HUD without refresh. Windows friend-machine packaging/Tauri remain separate gates. |
| F-050 | P3 | Frontend dependency audit | The locked frontend tree reports two advisories in Monaco's DOMPurify path (one low and one moderate; no high/critical findings). | Decision recorded: retain `monaco-editor` 0.56.0 / DOMPurify 3.4.8 as an accepted low/moderate risk. The 0.53.0 “fix” is rejected because its vendored DOMPurify is older 3.1.7 and merely invisible to npm audit; revisit only when upstream bundles a version above 3.4.12. |
| F-051 | P2 | Cloud write provenance | The security-definer player-state RPC accepted a caller-supplied device UUID without proving that the device belonged to the authenticated account; the client also classified any error message containing “revision” as a conflict. | Fixed locally: migration `20260916000100_player_state_device_ownership.sql` requires an account-owned `devices` row, the fake-cloud regression enforces the same boundary, conflict handling now accepts only SQLSTATE `40001`/HTTP `409`, and the unreachable cloud-revision-zero branch was removed. The migration is committed but intentionally not applied to Supabase in this checkpoint. |
| F-053 | P2 | Disposable K&M state custody | A separate quest workspace does not change the launcher's canonical state path; a mutating browser test can therefore write the protected save unless local custody is explicitly selected. | Fixed in the local test contract: `questlab-km-preflight.ps1 -RequireIsolatedState` now fails closed when the active path is the repository save. Mutating disposable runs must launch with an explicitly confirmed isolated local cache first; the accidental run remains auditable below and no direct JSON reset is permitted. |
| F-054 | P3 | Windows/WSL preflight separator normalization | The first implementation of the isolated-custody comparison used a two-character PowerShell backslash literal, which failed `TrimEnd` and could miss a single separator in normalization. | Fixed locally: the guard uses single-character `\` literals for `TrimEnd`/`Replace`, the launcher contract rejects the old forms, PowerShell parsing passes, and a guarded isolated runtime passes GREEN. |
| F-052 | P2 | Public activity automation boundary | `.github/workflows/sync-activity.yml` is the only CI writer and uses `contents: write` plus `GITHUB_TOKEN` to publish generated public activity. The boundary was not called out in the roadmap/handoff. | Fixed locally: handoff and roadmap now document the narrow `activity.json`/`README.md` output boundary, and the launcher contract suite rejects broader write scopes or player-state references. Keep the token/project permissions minimal and review again before public deployment. |

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

## Verification update — 2026-09-16 — clean-install launch

A fresh ext4 WSL clone of pushed `8f4ec71` followed the onboarding setup:
backend venv requirements, frontend `npm ci`, and Vite production build (1,344
modules). The delegated `ide/quest.py` launch path (the target of the Windows
wrapper) started the backend on 7360 and Vite on 5196 with backend reload
disabled. Browser K&M showed the Forge branch identity,
both shell/AI PTY labels `CONNECTED`, and the expected starter Level 1 state.

While that tab stayed open, a trusted in-process state-service reward advanced
the disposable canonical cache from revision 0 to 1; the HUD changed from
`0 c` to `1 c` on revision polling with no browser refresh. Quest Journal also
loaded normally. The tab, runtime and exact temporary checkout were then
closed/removed. The user save, legacy evidence, long-lived runtimes and hosted
state were not touched.

## Verification update — 2026-09-16 — per-tab PYR challenge isolation

The local challenge boundary no longer relies on one process-global Battle,
Boss or Dungeon slot. The Forge assigns each browser tab an opaque
`sessionStorage` client id; both the React publisher and the direct DOM
enhancement fallback use the same helper, while the gateway keeps separate
expiring challenge maps
and binds provider submissions/verdicts by their server-issued nonce. The old
singular names remain compatibility snapshots for older in-process callers, not
the lookup authority. Invalid/missing client ids fall back to the bounded
default partition, and challenge expiry pruning is retained.

The focused isolation test proved that tab A's Battle submission and Dungeon
submission remain valid after tab B captures a fresh challenge. The full WSL
backend suite then passed 68 tests, the frontend suite passed 31 tests, Python
compilation passed, and the Windows Vite build transformed 1,344 modules.

A disposable current-branch runtime was also checked with browser clicks,
scrolling and typing only (no Playwright): two tabs loaded the same canonical
revision, a trusted state-service reward changed the HUD without refresh, and
both shell and AI PTY labels remained `CONNECTED`. The exact temporary backend,
frontend and state directory were stopped/removed afterward. The user's dirty
`progress.json`, root `tutor.py`, long-lived runtimes and hosted state were not
touched. This closes the local F-009 defect; provider-authenticated hosted
adjudication remains a release gate.

## Decision update — 2026-09-16 — F-050 Monaco sanitizer review

Claude Sonnet reviewed the disposable tarball evidence. The current
`monaco-editor` 0.56.0 package declares DOMPurify 3.4.8 and bundles that same
version into `esm/vs/base/browser/dompurify/dompurify.js`; npm audit's one low
and one moderate advisory therefore describes a real loaded dependency. The
suggested 0.53.0 downgrade is not a security fix: its package metadata omits a
DOMPurify dependency, so npm audit reports zero, but the actual tarball vendors
DOMPurify 3.1.7, older than 3.4.8 and inside the same vulnerable ranges.

Decision: do not adopt 0.53.0, do not run `npm audit fix --force`, and do not
rewrite the lockfile. Retain 0.56.0 as an explicit accepted low/moderate risk
with no high/critical findings. Revisit F-050 only when upstream ships a
Monaco release bundling DOMPurify above 3.4.12 or a separately reviewed
sanitizer patch. The friend bundle must not be described as security-clean
until that upstream/reviewer gate changes.

## Verification update — 2026-09-16 — targeted frontend dependency audit

In the installed frontend tree, `npm audit --json` reported two advisories:
one low and one moderate, both on Monaco's DOMPurify path, with no high or
critical findings. The current direct dependency is `monaco-editor` 0.56.0;
its package carries DOMPurify 3.4.8 and Monaco bundles its sanitizer into the
editor distribution. npm's suggested automatic remediation is the semver-major
downgrade to `monaco-editor` 0.53.0, not a patch-level lock refresh.

No `npm audit fix --force`, unreviewed editor downgrade or lockfile rewrite was
run. The build and test gates remain green on the current 0.56.0 line. F-050
therefore remains open for an explicit Monaco compatibility/security decision
before calling the friend bundle security-clean; this audit did not change the
player save, runtime processes or hosted state.

A clean disposable HEAD archive then pinned `monaco-editor` 0.53.0 without
touching the repository lockfile. Its frontend suite passed all 31 tests, the
Vite build transformed 1,293 modules, and `npm audit --omit=dev` reported zero
vulnerabilities. This makes 0.53.0 a tested candidate, not an adopted change:
the downgrade still needs a reviewer/product decision because the current
editor line is 0.56.0, and npm audit does not inspect Monaco's vendored
sanitizer bundle.

## Review update — 2026-09-16 — Claude Sonnet F-009 follow-up

Claude's read-only review of commits `e8094c2` and `fea726e` found the core
nonce-keyed, lock-protected per-tab maps and TTL pruning internally consistent
across Battle, Boss, Dungeon submission/verdict routes. It confirmed that
`fea726e` is a necessary isolation fix for the direct DOM enhancement fallback,
not cosmetic cleanup. It found no current functional regression.

The review identified two low-severity coverage gaps, now addressed in the
backend suite: Boss-specific cross-tab binding was not asserted, and the
default/legacy compatibility snapshot did not have an explicit round-trip
assertion. The review also noted a bounded, already-known F-010 resource risk:
many unique local client ids can occupy expiring map entries until lazy
pruning; this remains within the loopback-only threat model and is not a
blocking release defect.

Claude could not independently run the WSL backend suite in its sandbox, so
its review did not replace the local test evidence. No files were edited by
Claude.

## Verification update — 2026-09-16 — Boss/default challenge coverage

The new backend regression test issues the default Boss challenge and asserts
its map entry remains the legacy compatibility snapshot, then issues Boss
challenges in tabs A and B and successfully submits/verifies tab A's evidence
after tab B rotates its own challenge. The full WSL backend suite now passes
69 tests; the frontend suite remains 31 tests and the latest Windows Vite build
transforms 1,345 modules. No player save, PTY, or hosted state was touched.

## Verification update — 2026-09-16 — final current-branch K&M projection smoke

A disposable backend/frontend pair on ports 7362/5198 loaded a copy of the
current local canonical save. Using browser clicks and accessibility checks
only (no Playwright), the Forge showed Level 2, 50 / 100 XP, 55 coins, Mob 3
The Hitman at 8 / 8 Resolve, three cleared mobs, the three Codex encounter
records, and `CONNECTED` shell and AI PTYs. A trusted state-service reward then
advanced only the disposable revision; revision polling changed the HUD and
reward queue to 56 coins without refresh. Quest Journal still showed The Hitman
and the three cleared mobs, while Character and Homestead showed the same 56-
coin projection and Codex remained populated. The exact temp state/workspace,
frontend, backend and browser tab were stopped/removed afterward; the user
save, legacy evidence and long-lived runtimes were untouched.

## Verification update — 2026-09-16 — F-033 onboarding contract

The launcher contract suite now asserts that `FRIEND_ONBOARDING.md` directs
friends to install dependencies inside a native Linux/WSL checkout, rerun
`npm ci` there when the Linux Rollup optional package is missing, and use a
Linux filesystem rather than a copied cross-platform `node_modules` tree. The
focused launcher suite passed 7 tests and the full WSL backend suite passed
69 tests. This closes the documentation/regression portion of F-033; the
shared OneDrive environment remains intentionally bounded by the fail-fast
launcher.

## Review update — 2026-09-16 — Claude sync provenance follow-up

Claude Sonnet performed a read-only review of the current sync engine, local
state gateway and Supabase migrations/tests. It found no Milestone C/D scope
drift and confirmed that the bounded projection allowlist is aligned across
the JavaScript engine, Python gateway and SQL validator. Three low-severity
gaps were identified: cloud writes did not bind `source_device_id` to the
authenticated account, conflict detection relied on loose message text, and
one revision-zero push branch was unreachable because the RPC creates its
first row at revision 1.

The provenance migration and frontend fixes were added without signing into
or mutating Supabase. The frontend suite passed 33 tests after adding fake
cloud coverage for foreign-device rejection and strict conflict detection.
The SQL regression now creates account-owned devices and attempts a
cross-account device UUID before the valid CAS write. The real linked SQL
test was deliberately not run because applying or seeding hosted state is
still an explicit Milestone C gate.

Claude's follow-up review of commit `6b301fa` found no correctness bugs. It
confirmed that the replacement RPC retains the bounded validator and grants,
that SQLSTATE `40001`/HTTP `409` are the complete reachable conflict signals,
and that the fake-cloud and SQL regressions match the migration history. The
slice is safe to keep. Live migration application, Postgres SQLSTATE/RLS
execution and two-device acceptance remain intentionally unverified until the
hosted Milestone C approval gate is opened.

## Verification update — 2026-09-16 — hosted migration contract coverage

The unapplied device-ownership migration now has six repository contract
tests. They verify that the security-definer RPC checks `public.devices` and
`auth.uid()` before validation/locking, retains the authenticated-only grant,
and that the executable SQL fixtures exercise the foreign-device rejection,
owned-device CAS write, private cross-account avatar paths, account-private
identity rows and bounded player-state values. These are static/local checks
only; no linked Supabase project was contacted. The focused contract suite
passes 6/6.

The same checkpoint's complete verification is 75 WSL backend tests, 33
frontend tests, Python compilation, `git diff --check`, and a successful
Windows Vite production build covering 1,345 modules. One initial full-suite
run hit a transient websocket cancellation; the immediate rerun passed. Since
the change only adds contract coverage and evidence, the prior disposable
K&M/PTY evidence remains the applicable UI proof.

## Review update — 2026-09-16 — Claude checkpoint plan

Claude Sonnet read the fresh `GAME_STATE_SNAPSHOT_2026-09-16_0206.md`, handoff,
roadmap plan, issue ledger, implementation report and current source in
read-only mode. It found no new local defect and confirmed the ownership
migration matches its documented behavior. It recommends no additional
Dungeon/Codex/Practice mechanics before Milestone C; the remaining local
decision is the explicit F-039 save-custody choice for the tracked
`progress.json`/OneDrive third writer.

The next required evidence is procedural and hosted: apply the committed
device-ownership migration, sign into the same account on two devices or
isolated profiles, exercise offline/reconnect CAS conflict handling and both
explicit conflict resolutions while preserving both PTYs, then perform the
private/offline avatar acceptance for Milestone D. This review does not claim
those gates are complete and no hosted state was changed.

## Verification update — 2026-09-16 — current state snapshot

`GAME_STATE_SNAPSHOT_2026-09-16_0224.md` re-read the canonical save after the
avatar contract slice. It confirms revision 2, Level 2, 50/100 XP, 150 lifetime
XP, 55 coins, three defeated Blackjack mobs, The Hitman at 8/8 Resolve and
three Codex encounter records. The capture is read-only; the dirty
`progress.json` and untracked Campaign `tutor.py` remain user-owned and no
hosted state was contacted.

## K&M verification update — 2026-09-16 02:29 — live projection recheck

Pure in-app-browser accessibility/click navigation on a disposable `5174`
tab (no Playwright and no refresh) showed the current canonical HUD at Level 2,
50/100 XP and 55 coins with visible heart/coin/flame/shield/sword SVG icons.
The same tab showed three defeated mobs plus The Hitman at 8/8 Resolve, three
Codex encounter records, Character at 55 coins and Homestead at a 55-coin
purse. The raw CLI PTY was visibly `CONNECTED`; the previous disposable K&M
run recorded the AI PTY as `CONNECTED` as well.

The first accessibility capture from the already-running development runtime
briefly exposed its old starter bootstrap before the canonical projection
arrived. The next no-refresh capture was correct; this is retained under the
known F-035/F-025 stale-HMR/runtime caveat, and no long-lived process was
restarted.

## Verification update — 2026-09-16 02:37 — legacy fallback HUD hardening

The legacy `App.jsx` path now refuses to render starter values while the
campaign projection is unavailable. During that short window it shows a
`SYNCING`/campaign-state placeholder, gates the dependent activity/banner
values, and uses React-owned monochrome heart/coin/flame/shield/sword SVGs.
This closes the remaining fallback path that could briefly reintroduce the
Level 1 / 0 XP / 0 coin HUD or emoji/nested-pill icons during stale HMR or
runtime startup. It is still fed only by the canonical campaign projection;
no local save path or PTY lifecycle changed.

Regression evidence: frontend tests 33/33 passed and the Windows Vite build
transformed 1,345 modules successfully. Commit `304fe76` is pushed to
`feature/cloud-sync-desktop`. The user-owned `progress.json` and untracked
root `tutor.py` remain unstaged and untouched.

## Runtime evidence correction — 2026-09-16 02:52

The earlier 02:38 disposable-tab capture on `127.0.0.1:5174` is superseded:
source inspection showed that the long-lived WSL-mounted Vite process was
serving an older cached AppV2 transform. It remains useful only as stale-runtime
evidence and is not current-branch UI proof. The branch-aware 5177/7343 run in
the 02:52 entry is the authoritative post-change K&M acceptance.

The active AppV2 HUD now keeps the loading coin placeholder as a bare `—`
instead of `—c`; once the canonical revision is present it renders the
formatted `Nc` value. This closes the remaining loading-only width change in
the stat row. The regression is covered by the 33-test frontend suite and is
committed as `ecffa40`.

## Snapshot and K&M verification update — 2026-09-16 02:52

`GAME_STATE_SNAPSHOT_2026-09-16_0252.md` confirms the canonical local save at
revision 2: Level 2, 50/100 XP, 150 lifetime XP, 55 coins, The Hitman 8/8,
three defeated mobs, 38% Blackjack progress and three Codex encounter records.

The stale-runtime boundary is now explicit: long-lived 5174 runs from the
current OneDrive cwd but serves an older cached AppV2 transform (emoji stat
glyphs and no loading guard). It was not restarted, preserving the user's
runtime/PTYs. A fresh branch-aware ext4 disposable clone at HEAD `71fdb9e`
served the current source on 5177/7343; its health matched
`feature/cloud-sync-desktop` and upstream. Pure K&M clicks, with no refresh and
no Playwright, observed the initial `SYNCING` state, live Resolve reduction,
reward/achievement/next-mob presentation, Journal/Codex updates and connected
shell/AI PTYs. The disposable runtime was then closed.

## Review update — 2026-09-16 03:01 — Claude Sonnet HUD/state review

Claude reviewed HEAD `66e2d37` read-only and found no correctness bugs in the
loading guard, React SVG ownership, `uiPolish.js` skip path, or the branch-aware
K&M sequence. It kept one medium process gap open: stale WSL-mounted Vite
source is honestly disclosed but not automatically detected. Two low notes
were non-blocking (upstream metadata is intentionally fail-open without an
upstream, and the legacy/current coin construction differs cosmetically).

The release recommendation is to keep the local checkpoint green but hold
mainline release for hosted Milestone C and the explicit F-039 custody choice;
Milestone D avatar acceptance and Milestone E Tauri remain ordered after them.

Claude reported many modified files because its WSL Git view exposes
cross-shell line-ending differences. A same-checkout verification confirms
the Windows status is only user-owned `progress.json` plus untracked `tutor.py`;
WSL `git diff --ignore-space-at-eol --stat` also leaves only `progress.json`.
No source was normalized, reverted or staged.

## Verification update — 2026-09-16 03:11 — read-only K&M runtime preflight

`tools/questlab-km-preflight.ps1` now provides a read-only manual gate for the
browser checkpoint. It validates the expected branch/upstream SHA, backend
repository branch/HEAD, one canonical state authority with a distinct
non-authoritative legacy path, current revision and served `AppV2` loading/SVG
markers. It performs only local Git reads and HTTP GETs; static contract
coverage rejects POST/fetch/delete/restart behavior. The known stale
`7333/5174` runtime failed closed because it lacked backend repo HEAD identity.

A fresh ext4 clone at branch `feature/cloud-sync-desktop`, HEAD
`5a051fb84cb2192e5cab42f3bf8e5df14f7c5a32`, passed the gate GREEN on
`7344/5178` (revision 0, then revision 2 after the disposable test mutation).
Pure in-app-browser K&M (no Playwright, no refresh) observed `SYNCING` settling,
Resolve 4/4 → 2/4, a validated mob clear, live HUD XP/coin changes, reward and
achievement notifications, next encounter unlock, Journal/Codex updates,
Character/Homestead projection, and `CONNECTED` shell/AI PTY labels. The
isolated runtime was closed and no long-lived process or user-owned save was
changed.

Focused launcher contracts pass 8/8; the complete WSL backend suite passes
76/76; the preflight PowerShell source parses. F-025/F-035 remain open as a
development-runtime custody/HMR risk, but the new gate prevents stale runtime
evidence from being accepted as current-branch proof. Hosted Milestone C,
F-039 custody approval, Milestone D and Tauri remain blocked by their existing
explicit gates.

## Snapshot/review update — 2026-09-16 03:15 — current game and full roadmap plan

`GAME_STATE_SNAPSHOT_2026-09-16_0315.md` is the current read-only canonical
capture: revision 2, Level 2, 50/100 XP, 150 lifetime XP, 55 coins, 100/100 HP,
three defeated Blackjack mobs, The Hitman at 8/8 Resolve, 38% progress,
three Codex records and First Blood. It preserves the exact equipment,
companion, mastery and evidence-backed fields without inferring unsupported
legacy rewards. The snapshot also records the live authority/legacy paths,
dirty user save/notebook boundary and stale-runtime caveat.

Claude Sonnet completed a second read-only roadmap review. Its detailed
dependency/test/K&M plan is persisted in
`ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0315.md`. The review confirms
that local Slices 0–6 are implemented and that Slice 7 is locally prepared but
still lacks real Windows friend-machine and hosted mailbox evidence. It keeps
the device-ownership migration, F-039 custody, Milestone C two-device sync,
avatar, Tauri, public web and Slice 8 behind explicit gates. No migration,
Supabase write, save edit, runtime restart or PTY reset was performed.

The post-plan regression pass at 03:26 is green: WSL backend 76/76, frontend
33/33 and Windows Vite build successful after transforming 1,345 modules. The
only build note is the pre-existing large-chunk warning. Windows status still
contains only the user-owned `progress.json` and untracked root `tutor.py`;
no semantic source or hosted state changed.

## K&M verification update — 2026-09-16 03:29 — current HEAD

A current-HEAD disposable ext4 clone at
`26ad97b24b8b0e9167d525008a8c660775236db4` passed
`tools/questlab-km-preflight.ps1` on `7345/5179` at revision 0. Pure K&M
observed `SYNCING` settling without refresh, then two validated Battle
mutations at revisions 1 and 2: Resolve 4/4→2/4 with `OBJECTIVE VERIFIED`,
followed by `MOB DEFEATED`, `+25 XP`, `+10 Coins`, `NEXT ENCOUNTER` and
`First Blood`. Journal showed The Dealer's Hand, Codex showed the defeated
encounter, and Character/Homestead showed the same 10 coins. Shell and AI PTYs
remained `CONNECTED`. No Playwright, user-save/legacy edit, hosted write or
long-lived process restart occurred; the disposable runtime was removed.

## Review update — 2026-09-16 03:31 — Claude evidence audit

Claude Sonnet read HEAD `0722036`, the current snapshot, detailed plan,
implementation report and this issue log without editing or mutating anything.
It found the latest K&M evidence, 76 backend/33 frontend/build counts and
canonical-versus-legacy custody boundary internally consistent. It correctly
identified that the disposable revision-2 starter save is not the real
canonical revision-2 restored save, not a contradiction. The only minor gap
was that the current-HEAD K&M runtime had been tested at docs-only parent
`26ad97b`; an exact-tip read-only preflight subsequently passed GREEN at
`0722036` on `7346/5180`, revision 0. The release recommendation remains to
hold hosted work for explicit F-039 custody approval and Milestone C.

## Verification update — 2026-09-16 03:35 — friend bundle custody

The committed-HEAD package smoke was rerun with the dirty player save and
untracked Campaign notebook still present. `tools/questlab-package.ps1` created
the bundle/ZIP from HEAD `4f6a98f`, and inspection confirmed the manifest's
branch/SHA, absence of `tutor.py`, and presence only of committed baseline
`progress.json` plus the committed snapshot/plan. The exact temporary bundle
directory was removed afterward. F-046 remains locally fixed; a real Windows
friend-machine launch, Tauri desktop proof and hosted mailbox acceptance remain
separate gates.

## Verification update — 2026-09-16 03:48 — current-tip Dungeon and Practice

The first disposable run for this pass was rejected as evidence because its
Vite proxy was serving an older disposable backend. It was stopped and
removed. A fresh ext4 clone at current pushed HEAD
`9b7c10f589923708593b20e53d833cf349448ab7` was then launched as one matched
pair on `7348/5182`; the read-only preflight passed GREEN at revision 4.

Pure in-app-browser K&M, with click/scroll/type only and no Playwright or
refresh, verified:

1. Infinite Dungeon opened with no active run, started a fresh loadout, and
   rendered the validated `DUNGEON RUN STARTED` notification.
2. A typed Lists/random-selection answer checkpointed through the state
   gateway. A nonce-bound disposable provider verdict advanced revision 2→3.
   The same tab live-rendered Floor 1 · Room 2, score 10, run coins 5, a new
   question, `LAST RESULT CORRECT`, and a blank `dungeon.py` buffer.
3. Practice selected Lists and opened one Tier 1 multiple-choice session. The
   history count became 1 and the boundary text explicitly said no Campaign
   or Dungeon rewards. Campaign Level/XP/coins stayed 1/0/0 and the Dungeon
   score stayed 10 with 5 run coins.
4. Shell and raw AI PTY indicators remained connected during the visible
   checks; the Codex update process seen in this disposable PTY was stopped
   without touching the long-lived runtimes.

This closes the local K&M evidence gap for the current Dungeon/Practice
source. It does not close hosted F-018, provider-authenticated adjudication,
F-039 custody, or Milestone C; no Supabase write was made. The disposable
runtime was removed after capture.

## Snapshot update — 2026-09-16 03:53

`GAME_STATE_SNAPSHOT_2026-09-16_0353.md` refreshes the read-only campaign
evidence at current pushed HEAD `6e366015275ca231b7e37c485754a09e856154a8`.
The canonical projection remains revision 2 with Level 2, 50/100 XP, 150
lifetime XP, 55 coins, three cleared mobs, The Hitman at 8/8 Resolve, 38%
progress, First Blood and three evidence-backed Codex records. No hosted
transport, migration, legacy-file write or player-save overwrite occurred.

The focused launcher/HUD contract suite is **9/9** after adding a regression
for F-048: broad descendant `.top-stats span` selectors are rejected, the
adventurer selector remains direct-child scoped, and the SVG/value reset plus
direct-child `uiPolish.js` query are required.

The full WSL backend suite is **77/77** after restoring its missing
`httpx2` TestClient dependency, and the frontend suite remains **33/33**.

The current-HEAD friend packaging smoke also passed at `7e1a5e2`: committed
source was archived, `tutor.py` stayed out of the bundle, and the disposable
bundle/ZIP was removed after inspection. F-046 remains locally fixed; hosted
mailbox acceptance, Windows friend-machine launch and Tauri proof remain
separate gates.

The Windows Vite production build remains green at 1,345 transformed modules;
the only output warning is the existing large-chunk advisory.

F-025 evidence is tighter now: `tools/questlab-km-preflight.ps1` compares the
frontend `/api/runtime` proxy to the direct backend for branch, HEAD and both
state paths. A clean ext4 current-branch runtime passed the paired check on
7349/5183. The existing stale 7333/5174 runtime was not restarted; F-025 stays
open until that user-owned runtime is replaced through the normal launcher.

## 2026-09-16 04:10 — stale browser port reproduced

The user-visible browser tab at `http://127.0.0.1:5174/` was inspected with
the allowed in-app browser K&M surface. It rendered the starter Level 1 / 0 XP
shell, showed `Sign in to sync`, and its `/api/runtime` proxy exposed only the
legacy `{shell, python, commands}` health shape. This is the old long-lived
runtime, not the current `feature/cloud-sync-desktop` Forge; it explains the
empty-pill HUD and starter campaign view. The tab was closed after inspection.
No backend, frontend, PTY, canonical save, legacy evidence file, or cloud state
was restarted or edited. Current-branch evidence must use the paired preflight
and a matched runtime launched through `tools/questlab-launch.ps1` (or an
isolated disposable clone).

The exact pushed tip `d97bb2c` then passed the paired preflight on a clean ext4
clone at `7351/5186` (revision 0). Pure in-app-browser K&M showed the current
React SVG heart/coin/flame/shield/sword icons with no nested pills and both PTY
indicators `CONNECTED`. A disposable `record_learning_event` gateway mutation
advanced revision 0→1; the same tab updated its campaign projection without a
refresh and retained the SVG HUD. The disposable clone/runtime was stopped and
removed afterward.

## 2026-09-16 04:24 — Claude audit and runtime guard

Claude Sonnet completed a read-only audit of the fresh snapshot, roadmap plan,
execution plan, handoff, implementation report and issue log. It found no
fabricated Stage 1–4 evidence and confirmed the 77 backend / 33 frontend test
counts against the source. Its only local finding was a wording ambiguity:
cross-shell CRLF/LF noise makes WSL `git status` look broadly dirty even though
the Windows content diff contains only the user save. The snapshot now states
that boundary explicitly.

The bounded code-safe follow-up adds a passive `RUNTIME STALE · use current
launcher` footer warning when the served `/api/runtime` lacks the branch/HEAD/
state-authority contract. This makes an old backend visible in Forge without
restarting PTYs or blocking local play. The frontend source regression passes;
hosted Milestone C, avatar, F-039 custody, Tauri and provider-authenticated
adjudication remain correctly gated and unchanged.

## 2026-09-16 04:35 — current-tip regression rerun

The current pushed tip `0d83bd6` was rechecked after the documentation-only
checkpoint. The first WSL command used the system Python and correctly failed
closed because it has no project FastAPI/Pydantic dependencies; the repository
`.venv/bin/python` rerun passed **77/77** backend tests. The frontend suite
passed **33/33**, Python `compileall` passed, and the Windows Vite production
build passed with 1,345 transformed modules and only the existing large-chunk
warning. No state file, tutor notebook, PTY, listener, or cloud resource was
changed by these checks.

## 2026-09-16 04:40 — fresh snapshot and Claude dependency plan

The read-only snapshot `GAME_STATE_SNAPSHOT_2026-09-16_0438.md` records the
canonical revision-2 campaign: Level 2, 50/100 XP, 150 lifetime XP, 55 coins,
three cleared Blackjack mobs, The Hitman at 8/8 Resolve, First Blood and three
Codex records. It also records the stale long-lived runtime boundary, separate
canonical/legacy hashes, protected dirty `progress.json`/`tutor.py`, and the
current test/build evidence.

Claude Sonnet then performed a second read-only synthesis of the snapshot,
roadmap, handoff, implementation report and issue log. The detailed plan is
versioned at `ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0438.md`. Claude's
key ordering decision is to finish the only non-hosted work first (real
Windows friend launch plus the explicit F-039 save-custody decision), then the
approval-gated hosted two-device sync, hosted avatar, Tauri, public web and
social stages. It found no local code-safe shortcut around those gates and
specifically kept F-001/F-010 provider-authenticated adjudication as a
Milestone-C co-requisite. No file, save, runtime, PTY or hosted resource was
changed during the review.

## 2026-09-16 04:45 — post-plan regression rerun

After committing the fresh snapshot and Claude plan, the project WSL virtualenv
again passed **77/77** backend tests and the frontend suite passed **33/33**.
The custody tests exercised preview-only and explicit opt-in copy paths inside
temporary fixtures; no real save was migrated. The working tree still contains
only the protected `progress.json` modification and untracked `tutor.py`.
The stale long-lived runtime remains untouched.

The current `HEAD` archive was also inspected without creating a bundle or
touching the worktree: 113 committed entries included the baseline
`progress.json` and `FRIEND_ONBOARDING.md`, while the user's untracked
`tutor.py` was absent. This confirms the packager's committed-source custody
boundary at `444fef7`; real second-Windows launch evidence remains open.

## 2026-09-16 04:50 — runtime inventory clarification

Read-only socket/process inspection found the old OneDrive/runtime listeners
on 7332–7334 and 5173–5175, plus a branch-aware disposable backend on 7341
whose authority points at `/tmp/questlab-browser-final/progress.json`. None was
restarted or used as current-user evidence. The paired preflight remains the
required K&M gate because it rejects the legacy health shape and temporary or
mismatched state authority instead of silently trusting a stale tab.

## 2026-09-16 05:06 — Codex evidence projection and current-pair K&M

The Codex projection now searches validated encounter text (mob, concept,
question types, weaknesses and notes), keeps legacy records without an
explicit `page_id` attached to their concept page, and presents validated
weakness/pattern, result/evidence and interview-history sections. React only
renders those state-service fields; it does not calculate rewards, mastery or
Resolve. The source regression was extended for the new search and insight
surface.

The current branch tip `f8634b4` passed the paired current-source preflight on
backend `7354` / frontend `5190` at campaign revision 2. Pure in-app-browser
K&M (no Playwright) searched `legacy`, searched `append`, cleared the filter,
opened Lists & collections, and visibly showed its definition, example,
validated Dealer's Hand result and the new insight headings without a browser
refresh. A Forge screenshot also showed the React SVG heart, coin and streak
icons rendered as icons rather than nested empty pills. The disposable Vite
and backend were stopped afterward; long-lived shell/AI PTYs and both save
files were not restarted or changed. The disposable backend intentionally did
not claim PTY connectivity, so PTY survival remains covered by the prior
paired-runtime evidence rather than this isolated UI run.

## 2026-09-16 05:10 — current game snapshot before local distribution

The fresh read-only snapshot `GAME_STATE_SNAPSHOT_2026-09-16_0510.md` confirms
the same canonical revision-2 campaign after the Codex-only change: Level 2,
50/100 XP, 150 lifetime XP, 55 coins, three cleared Blackjack mobs, The Hitman
at 8/8 Resolve, First Blood and three validated Codex records. The canonical
and legacy hashes remain separately recorded, and only the protected local
`progress.json` plus untracked Campaign `tutor.py` are dirty. The next
implementation stage remains local distribution: a real second-Windows launch
and the explicit F-039 custody decision. Hosted sync, avatar, Tauri, public and
social stages remain approval-gated.

## 2026-09-16 05:11 — local distribution custody and launcher gate

The committed-source package was rebuilt from HEAD `794c1a2`. Its manifest
carried the exact source SHA and the bundle included the committed baseline
`progress.json` while excluding the user's untracked root `tutor.py` and dirty
save bytes. The temporary package was inspected and removed. This preserves
the friend-bundle custody boundary; the Campaign notebook remains local
user-owned data and is not silently distributed.

The guarded Windows launcher was then invoked on disposable ports `7355/5191`.
It printed the branch, upstream, canonical path and stable-PTY mode, warned
about the dirty player save, and failed closed before spawning because the
OneDrive WSL `node_modules` tree lacks Linux Rollup's optional native package.
No listener appeared on either disposable port and Windows status remained
only protected `progress.json` plus untracked `tutor.py`. A clean Linux/WSL
dependency install is still required for the real second-Windows launch gate.

The friend guide now states explicitly that excluding an untracked `tutor.py`
from a committed distribution bundle is a custody safeguard, not removal of
the Campaign Tutor Notebook. The workspace-scoped Campaign endpoint creates
or reads that notebook on first use; Practice remains unable to write it.

## 2026-09-16 05:26 — exact current-tip live progression K&M

The disposable paired preflight was GREEN on backend `7356` and frontend
`5192` at source `c4b08da556f8ccc8f9a5bdf18be452e323e2ed74`, starting at
campaign revision 0. The backend was configured with the current checkout as
the repository/state authority and a separate disposable workspace; the
canonical Windows save and user-owned Campaign `tutor.py` were not involved.

Using only in-app-browser accessibility keyboard/mouse actions (no Playwright
and no browser refresh), the shell PTY issued valid provider-bound context,
submission and verdict requests. The Empty Table Resolve changed from 4/4 to
2/4 live, then a second valid objective cleared it and advanced the disposable
revision 0 to 1 to 2. The HUD immediately showed 25 XP and 10 coins; queued
validated notifications showed the mob defeat, The Dealer's Hand unlock and
First Blood. Quest Journal then showed the cleared mob, The Dealer's Hand at
6/6, progress 12% and weekly progress 1/2. Codex showed 8 indexed records,
the encounter evidence/result entries and no hidden future answers. Character
and Homestead reflected the same live XP/coins and First Blood. Both Forge
terminal and AI PTY remained CONNECTED throughout.

The disposable Vite/backend, clone and mutated starter save were stopped and
removed after the run. This is exact current-tip live-projection evidence; it
does not claim that the user's Level 2 canonical save was modified by the
test. The persistent canonical baseline is recorded in
`GAME_STATE_SNAPSHOT_2026-09-16_0526.md`. Remaining gates are a clean
Linux/WSL dependency install plus a real second-Windows launch; hosted sync,
avatar, Tauri, public and social work remain approval-gated.

## 2026-09-16 05:32 — current pushed-tip regression gates

At pushed HEAD `8cdd15136ead00d40777feb9fca8ed9770d54fe3`, the project WSL
virtualenv passed **77/77** backend tests and Python `compileall -q ide`
passed. The Windows frontend passed **33/33** tests and the production Vite
build transformed **1,345 modules** with only the existing large-chunk
advisory. These were read/build-only checks: the canonical `progress.json`,
untracked Campaign `tutor.py`, long-lived shell/AI PTYs and hosted resources
were not changed. The current K&M evidence remains the disposable exact-tip
run recorded above; no Playwright was used.

## 2026-09-16 05:37 — current ext4 distribution K&M

A fresh ext4 clone of the pushed `e1d8a03` branch installed the backend
virtualenv requirements and frontend dependencies with `npm ci`; its Vite
build transformed **1,345 modules**. The stable-PTY launcher then served the
clone on backend `7357` / frontend `5193`, and the read-only paired preflight
was GREEN at campaign revision 0 with the clone as canonical authority and a
separate workspace legacy path.

Pure in-app-browser keyboard/mouse/type actions (no Playwright and no refresh)
verified the live path. Both terminal surfaces initially showed CONNECTED. A
typed, valid state-service Battle objective changed The Empty Table Resolve
from **4/4 to 2/4** and displayed the validated objective toast. A second
typed, valid objective advanced the disposable revision and immediately
showed **25 XP / 10 coins**, `MOB DEFEATED`, The Dealer's Hand as the next
encounter and First Blood. Without refreshing, Quest Journal showed the next
mob at **6/6**, Codex showed the new encounter record and verified evidence,
Character showed the same XP/coins/achievement, and Homestead showed the live
purse. The disposable runtime, clone and mutated save were stopped and
removed; the canonical Windows save, legacy evidence, Campaign `tutor.py` and
long-lived PTYs were untouched.

The refreshed read-only baseline is `GAME_STATE_SNAPSHOT_2026-09-16_0539.md`.
It records the unchanged canonical revision-2 Level 2 campaign, current
pushed HEAD, separate canonical/legacy hashes, green regression gates and the
clean ext4 K&M evidence without treating disposable state as player progress.

## 2026-09-16 05:40 — current bundle custody recheck

`tools/questlab-package.ps1` packaged pushed HEAD `6629364` into an exact
temporary directory. Inspection confirmed the committed baseline
`progress.json` and `QUESTLAB_BUNDLE.txt` were present while the user's
untracked Campaign `tutor.py` was absent. The manifest repeated the local-first
no-copy rule and WSL `npm ci` onboarding instruction. The exact temporary
bundle directory and ZIP were removed after inspection; the live save and
notebook were not staged or copied.

## 2026-09-16 05:45 — reward authority hardening

Review of the live reward presentation found one frontend fallback that could
have displayed `+100 XP` for a boss event even when the validated state event
did not supply a reward amount. `AppV2` now renders the amount only when
`boss_reward_xp` or `reward_xp` is present in the event; otherwise it shows
the verified boss-clear label without inventing a number. A focused source
regression covers the absence of the old fallback. Backend remained **77/77**,
frontend **34/34**, Python compileall passed and the production build passed
with **1,345 modules**. No save, PTY, hosted resource or Campaign notebook was
changed.

## 2026-09-16 05:47 — post-fix exact-tip K&M

A clean ext4 clone at pushed HEAD `6095aaa` passed paired preflight on backend
`7358` / frontend `5194`. Pure in-app-browser actions only (no Playwright and
no refresh) showed both shell and AI PTYs `CONNECTED`, then a shell-typed valid
state-service Battle objective produced an `OBJECTIVE VERIFIED` toast and live
Resolve **4/4 → 2/4**. The exact current-tip runtime was stopped and its clone
and disposable save removed; canonical Level 2 save and Campaign `tutor.py`
were untouched. The boss reward fallback fix was source-tested; this smoke
confirms the general live projection path remains healthy after it.

## 2026-09-16 06:03 — Claude review and rollback hardening

Claude Opus completed a read-only review of the pushed tree and found no P0 or
P1 issues. It identified two P2 hardening items and one P3 edge case. The
preflight script now checks native Git exit codes and uses `rev-parse
--verify --quiet` so a missing remote ref cannot trigger a null `.Trim()` crash;
the campaign projection now accepts a deliberate lower revision (local reset
or canonical-save restore) after clearing the prior event baseline instead of
polling forever on stale UI; and boss XP is accepted only when the validated
event contains a finite numeric value, never `+0` from an explicit null.
Focused frontend tests are **35/35**, backend **77/77**, PowerShell parsing and
Vite **1,345-module** build pass. Remaining risks are the known behavioral
runtime-harness gap, per-WebSocket PTY loss on a real proxy/HMR drop, and the
approval-gated hosted/Tauri/two-device gates.

## 2026-09-16 06:04 — current-tip K&M after review fixes

A disposable ext4 clone at pushed HEAD `c8dba22` was launched on backend `7359`
and frontend `5195`. Pure in-app-browser keyboard/mouse actions (no Playwright,
no refresh) showed the monochrome heart/coin/streak/shield/boss HUD icons, both
shell and AI PTYs `CONNECTED`, then a shell-typed state-service Battle
submission/verdict changed Resolve **4/4 → 2/4** and added the validated
`OBJECTIVE VERIFIED` reward card. The runtime, clone and disposable workspace
were stopped and removed; canonical `progress.json` and Campaign `tutor.py`
remained untouched.

## 2026-09-16 06:06 — preflight cross-shell hardening

The read-only Git probes now rely on quiet `rev-parse --verify` exit status
without native stderr redirection, avoiding the Windows PowerShell 5.1
`$ErrorActionPreference='Stop'` edge case called out in review. PowerShell
parsing and the focused frontend suite remain green (**35/35**); no runtime,
save or PTY was touched. This is a compatibility hardening of the existing
preflight gate, not a new acceptance claim.

## 2026-09-16 06:08 — snapshot and roadmap fallback plan

The read-only current checkpoint is `GAME_STATE_SNAPSHOT_2026-09-16_0608.md`.
It records pushed HEAD `e0e04a9`, canonical revision 2 / Level 2 / 50 XP / 55
coins, the unchanged canonical SHA-256 and the protected dirty boundary. A new
Claude Sonnet roadmap-planning request was given five minutes and returned no
output; the existing Claude plan plus the explicit fallback execution matrix
in `ROADMAP_EXECUTION_PLAN.md` remain active. No code/runtime/save/PTY change
was made by the timeout.

## 2026-09-16 06:09 — stale runtime audit

Read-only probes found listeners on legacy ports `5173`, `5174`, `7332`,
`7333` and `7334`. Their `/api/runtime` responses expose only shell/Python/
command availability and omit `repo_git`, `expected_branch` and
`state_authority`, so they cannot be accepted as current-branch Forge
evidence. Port `5180` was not listening. The existing processes were not
restarted or killed; F-025/F-031 remain open until the user launches the
guarded current checkout.

## 2026-09-16 06:20 — Windows launcher identity hardening

F-025/F-031 remain open for the already-running legacy processes, but the
guarded launcher itself is now safer on fresh Windows/WSL checkouts. It no
longer calls `.Trim()` on a missing upstream ref; it resolves the branch
upstream with `for-each-ref`, verifies HEAD/upstream hashes with quiet Git
probes and fails closed if either identity cannot be resolved. Launcher
contract tests pass **9/9** and PowerShell parsing passes. No launcher was
started, and no save or PTY was touched.

## 2026-09-16 06:22 — post-launch-fix regression

After the launcher identity fix, the full WSL backend suite passed **77/77**,
the frontend suite passed **35/35**, Python `compileall -q ide` passed, the
launcher contract subset passed **9/9**, PowerShell parsing passed and Vite
built **1,345 modules**. Git identity reads resolved the current branch,
upstream and equal HEAD hashes. This was read/build-only; the canonical save,
legacy evidence, long-lived runtimes and PTYs were untouched.

## 2026-09-16 06:25 — current-tip launcher checkpoint K&M

A fresh ext4 clone at pushed HEAD `55acb0b` installed its WSL virtualenv and
frontend dependencies, then served the stable-PTY runtime on backend `7361`
and frontend `5197`. Pure in-app-browser click/type/scroll actions only (no
Playwright and no refresh) showed the current branch, visible monochrome HUD
icons and both terminal surfaces `CONNECTED`. A shell-typed state-service
Battle context/submission/verdict changed The Empty Table Resolve **4/4 →
2/4**; Quest Journal then showed **2/4** and the validated `OBJECTIVE VERIFIED`
reward card. The clone, runtime and mutated starter save were removed; the
canonical save, legacy evidence, Campaign `tutor.py` and long-lived PTYs were
untouched.

## 2026-09-16 06:30 — narrow Claude roadmap refresh

Claude Sonnet completed a read-only refresh from the existing plan files. It
confirmed that the only locally implementable gap is the real Windows
friend-machine launch; F-039 remains an owner decision, and F-050 is already
an accepted dependency decision. It kept Milestones C–F, hosted Dungeon,
provider authentication and Slice 8 blocked behind their explicit approvals.
It also identified stale mid-document counts/snapshot pointers, which were
corrected in `ROADMAP_EXECUTION_PLAN.md`. No code, save, runtime or PTY was
changed by the review.

## 2026-09-16 06:31 — persistent state snapshot

The read-only continuation checkpoint is recorded in
`GAME_STATE_SNAPSHOT_2026-09-16_0631.md`. It preserves the canonical and
legacy SHA-256 values, the reconciled Level 2 / 50 XP / 55 coin state, the
three cleared mobs and The Hitman 8/8 projection, the three Codex encounter
records, the green 77/35/9/build gates, the current-tip pure K&M evidence and
the remaining Windows/hosted approval gates. No save, runtime or PTY was
changed.

## 2026-09-16 06:37 — OneDrive WSL dependency caveat reproduced

The guarded Windows/WSL launcher was tried on unused ports `7370/5200`. It
failed closed because the OneDrive-mounted checkout contains a Windows
`node_modules` tree without a Linux Rollup optional package. A WSL `npm ci`
and a follow-up `npm install --include=optional` both failed with `EIO`/`ENOENT`
while replacing the mounted `esbuild` tree. No tracked file, save, runtime or
PTY was changed. F-033 remains bounded: install dependencies in a clean Linux
checkout/ext4 clone before launching; do not weaken the native-dependency
preflight or mutate the user's active runtime tree.

## 2026-09-16 06:47 — Claude Sonnet local-slice review

Claude Sonnet completed a read-only review of the current branch, launch
scripts, handoff, roadmap and persistent logs. It found no P0 correctness
issues and confirmed the local slice/authority/revision/event/PTY claims are
coherent. It reiterated three bounded items: F-039 tracked-save custody is
still an explicit owner decision; F-033 must forbid dependency installs in the
live OneDrive WSL tree (the row above now says this directly); and the WSL
checkout has recurring CRLF/LF review noise. The suggested `.gitattributes`
normalisation is deferred because it would rewrite many tracked files while
the protected save and Campaign notebook are dirty; it needs a deliberate
separate change window. Recommendation: proceed only with the local Slice 7
Windows/ext4 launch gate and hold hosted/Tauri/social work behind approvals.

## 2026-09-16 06:50 — current Windows launcher preflight

After restoring the ignored Linux Rollup/esbuild packages from temporary
registry archives (the tracked source was unchanged), the guarded launcher
started the current checkout on `7370/5200` with a distinct disposable quest
workspace. `questlab-km-preflight.ps1` passed GREEN at HEAD
`4f5bbaaa04c2ad2f9f7219f6b210a30c76a1ae4d`, revision 2, and exposed distinct
canonical/legacy paths. Pure K&M navigation (no refresh, no Playwright)
showed Level 2 / 50 XP / 55 coins, The Hitman 8/8, three cleared mobs, three
validated Codex encounter records, visible monochrome HUD SVG icons and both
PTY labels `CONNECTED`. No mutation was issued because this runtime pointed
at the protected canonical save; the earlier disposable current-tip K&M
mutation remains the reward/Resolve evidence. The runtime and workspace were
closed and cleaned; long-lived runtimes and PTYs were untouched.

## 2026-09-16 07:01 — friend onboarding guardrails

Committed and pushed `5f678e7` with a narrow onboarding/test update. New friend
instructions prefer an Ubuntu/ext4 checkout, explicitly prohibit `npm install`
or `npm ci` against the live OneDrive-mounted `ide/frontend/node_modules` from
WSL, and require a separate quest workspace so the preflight can prove distinct
canonical and legacy paths. The launcher contract test covers both statements.
This is documentation/test-only: the protected save and Campaign `tutor.py`
remain dirty but unstaged, and no runtime or PTY was touched.

## 2026-09-16 07:14 — Claude Sonnet roadmap plan

Authenticated Claude Sonnet completed the requested read-only re-audit of the
handoff, current snapshot, roadmap, source and tests. It found no P0/P1
correctness issue. The detailed dependency-ordered plan is persisted in
`ROADMAP_CLAUDE_IMPLEMENTATION_PLAN_2026-09-16_0705.md`. Findings were limited
to precise wording about the internal-only `system` actor, the effective
Campaign `tutor.py` versus Practice boundary, the CI activity writer (F-052),
and the already-documented launcher fetch behavior. Claude recommends Stage A
only until a real second-Windows environment and the explicit F-039 custody
decision are available; hosted sync/avatar, Tauri, public and social work stay
approval-gated.

## 2026-09-16 07:23 — disposable K&M state-custody incident

The fresh browser-only Dungeon check used a separate workspace but (incorrectly)
left the launcher pointed at the protected canonical cache. The state service
therefore recorded a Dungeon start (revision 3), a 33-byte checkpoint (revision
4), and a bounded internal death cleanup (revision 5). No Campaign XP/coins,
mob, Codex, equipment or player counter changed; the cleanup granted no reward.
The resulting dead zero-score run is retained as an auditable event and does
not block a fresh run. F-053 is now tracked: mutating disposable K&M must first
use an explicitly confirmed isolated local cache; workspace separation alone is
not sufficient. No direct JSON edit or destructive reset was used.

## 2026-09-16 07:38 — isolated live-projection acceptance and guard correction

The new `-RequireIsolatedState` preflight initially surfaced a PowerShell
separator bug: `'\\'` was invalid for `TrimEnd` and did not normalize a single
backslash in `Replace`. The guard now uses single-character literals, the
launcher contract asserts both forms, and the PowerShell parser plus the
preflight pass GREEN.

A disposable WSL workspace/local cache was explicitly migrated with
`--use-local-state --confirm-local-state`; the protected canonical save was not
used for mutation. Pure CUA K&M verified revision 5→6 Resolve 8/8→4/8 and
revision 6→7 Hitman defeat, the state-service's +30 XP/+15 coins, Bust Hound
unlock, Codex growth, live HUD/Journal/Character/Homestead projection and
`CONNECTED` shell/AI PTYs without refresh. The disposable runtime and files
were removed. Protected revision 5/hash and user `progress.json`/`tutor.py`
custody remain unchanged. Claude's follow-up CLI review was attempted but hit
its session limit, so this entry carries no new peer-approval claim.

## 2026-09-16 10:14 — isolated Dungeon/Practice savestate checkpoint

The guarded disposable runtime passed `-RequireIsolatedState` on `7373/5203`.
Pure CUA K&M started a fresh Dungeon run, saved a typed checkpoint, and used a
visible shell command to invoke the internal `dungeon_record_verdict` action.
Revision `7 → 8` emitted the validated `+10` score / `+5` run-coin event,
showed the `DUNGEON ROOM CLEARED` feedback card, advanced to Floor 1 Room 2 and
cleared the editor buffer before the next prompt. The Dungeon state remained
separate from Campaign rewards and the shell/AI PTYs stayed connected.

Practice navigation confirmed its no-cost, non-Campaign boundary. The UI guard
blocked a request before a provider was selected. A separate state-service
check then created one `practice_session_started` row and one
`practice_record_attempt` (`reviewed`) at revisions `9` and `10`, with zero XP
and zero coins. Forge rendered both Practice feedback cards and one history
row; Campaign HUD, Dungeon score/run currency and `tutor.py` did not change.

For the savestate proof, the backend/frontend were stopped and relaunched
against the same explicitly approved disposable cache. A fresh browser tab
reopened the active run at Floor 1 Room 2 with score 10, 5 run coins and a
blank editor buffer. Both `/ws/terminal/shell` and `/ws/terminal/ai` were
accepted again. The normal launcher correctly reported `status: conflict` when
asked to migrate the already-diverged local cache, so no implicit merge or
newest-revision selection was used. Full details are in
`GAME_STATE_SNAPSHOT_2026-09-16_1014.md`.

## 2026-09-16 10:44 — Codex/Homestead presentation and launcher module path

The next local polish slice keeps the canonical revision/event architecture
unchanged while making the evidence surfaces easier to read. Codex now shows
service-projected record metrics (indexed records, books with evidence,
encounters, verified results and player field notes), per-page encounter and
recorded-signal summaries, and keeps the existing bounded encounter detail
and note action. Homestead now shows a live-loadout/economy card with level,
XP, campaign armor/trinket, coins and the canonical revision, plus a small
scene badge. Every value is read from the same campaign projection as the
HUD; React does not calculate rewards or unlocks.

The acceptance launch also found that invoking `ide/quest.py` as a script from
the mounted checkout failed during local-state setup because Python did not
include the repository root on `sys.path`. `tools/questlab-launch.ps1` now
executes `PYTHONPATH=. .venv/bin/python -m ide.quest`, and the two handoff
command examples use the same module-safe form. This is a launcher/import
fix only; no save, cloud resource or PTY was changed.

Focused/source checks and the full WSL backend suite passed **78/78**; the
frontend source suite passed **36/36**; Python compilation and PowerShell
preflight parsing passed; and the Windows Vite build transformed **1,345**
modules successfully (existing large-chunk advisory only). A disposable
current-branch runtime with an explicitly migrated local cache showed the
canonical Level 2 / 50 XP / 55 coins projection, visible monochrome HUD
icons, the Codex metrics/evidence view and the Homestead live-loadout card.
Both shell and AI PTY labels remained `CONNECTED`; the disposable runtime
and state roots were stopped and removed afterward. No Playwright was used.

## 2026-09-16 10:50 — Claude Sonnet review of the polish slice

Authenticated Claude Sonnet performed a strictly read-only review of the
current source and checkpoint. It found no P0 or P1 issue and confirmed that
Codex/Homestead render only the safe canonical projection, do not leak hidden
answers or invent rewards, the React-owned icon guard is sound, and the module
launcher invocation is valid. It identified one pre-existing P2 edge case:
entries missing `page_id` used a loose first-word substring fallback that could
mis-shelve a legacy Codex record. The fallback is now exact/prefix-only, with a
source regression assertion. Claude also noted that the frontend tests are
source-regex tripwires rather than rendered-DOM tests; this is a known P3 test
boundary, not a release blocker. Claude did not run tests or browser actions
and did not touch `progress.json`, `tutor.py`, runtimes or PTYs.

## Verification update — 2026-09-16 — end-to-end bug hunt and CachyOS target

The repeatable bug hunt is persisted in `BUG_HUNT_LOG_2026-09-16.md`. Claude
Sonnet and Copilot reviewed the current branch, and the primary agent ran the
browser checkpoint with keyboard/mouse/scroll/type only. The three defects
below were reproduced or confirmed, repaired, and regression-checked; no new
primary-agent K&M defect was scored.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-055 | P2 | PYR context isolation | The context bridge stored the latest PYR context in a process-global slot. A second tab could therefore read the first tab's marker/context through `GET /api/pyr/context`, even though challenge writes were intended to be tab-scoped. | Fixed locally: named clients now have isolated context records, the GET route accepts the opaque `client_id`, and a two-tab regression proves marker A cannot read marker B (or vice versa). |
| F-056 | P2 | PTY command resolution | New PTYs prepended the repository root to `PATH`. A workspace file named `python3`, `git` or `curl` could shadow the real tool and change shell/PYR behavior. | Fixed locally: PTY environments inherit the host `PATH` and append the repository root only for the supported `questlab-state` wrapper. The PATH-order regression passes for both PTY bridges. |
| F-057 | P3 | Release documentation | The implementation report still described Dungeon/Practice as missing while the current branch already contained the local playable slice, which could cause an unnecessary scope rollback or incorrect release decision. | Fixed locally: the report now separates local Dungeon/Practice proof from the still-open hosted persistence gate (F-018). |
| F-058 | P2 | Native Linux distribution | Friend onboarding covered Windows/WSL and ext4 smoke only; the requested CachyOS laptop had no explicit native-Linux install, launch, dependency or PTY acceptance gate. | Open roadmap gate: CachyOS is now an explicit Arch-based target. It is not certified until a clean native Linux checkout passes the install/build/launch, canonical-state, live-projection and shell/AI PTY K&M checks on that laptop. |

The reviewer score was Copilot **2 unique findings / 5 points** and Claude
Sonnet **1 unique finding / 4 points**; the primary K&M pass found **0 new
scored defects**. F-058 is a distribution requirement, not a claim that the
current Windows/WSL evidence certifies CachyOS.

## Verification update — 2026-09-16 — native Linux preflight

The CachyOS gate now has a PowerShell-free, read-only preflight at
`tools/questlab-km-preflight.py`. It performs the same branch/upstream
identity, backend/frontend proxy identity, canonical-versus-legacy authority,
revision and served-AppV2 marker checks as the Windows PowerShell gate. The
`--require-isolated-state` option fails closed when a mutating K&M run points at
the protected repository save. It uses only Git reads and HTTP GETs, so it
cannot write state, call Supabase, restart Forge or touch a PTY.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-059 | P3 | Native Linux preflight | CachyOS and other native Linux installs had no executable preflight equivalent to the Windows/WSL PowerShell gate, leaving identity and state-custody checks undocumented or dependent on a second shell. | Fixed locally: `tools/questlab-km-preflight.py` is cross-platform, its isolation/authority behavior is covered by the launcher contract suite, its `--help` path runs under WSL Python, and the CachyOS onboarding command is documented. Actual CachyOS K&M acceptance remains F-058 and is still open. |

## Verification update — 2026-09-16 — local two-device sync simulator

The local sync boundary now has a repeatable, cloud-free contract exercise at
`tools/questlab-local-sync-sim.py`. It copies the canonical snapshot into two
temporary device caches, uses the real `LocalStateService` for rewards and
cloud projection imports, models a compare-and-swap mailbox, proves both a
stale mailbox push and a stale offline pull return `409`, then performs an
explicit keep-device resolution that records `sync_apply_cloud`. The source
snapshot's SHA-256 is checked before and after; no root or legacy
`progress.json` is written.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-060 | P3 | Local sync confidence | Until now there was no executable local two-device scenario to exercise CAS conflicts, offline divergence and an explicit resolution without touching the protected save. | Fixed locally: the simulator and launcher contract test pass, report the conflict/revisions/final projection as JSON, and are documented for native Linux/WSL. This raises local confidence only; hosted mailbox/auth, real second-device and OneDrive custody gates remain open. |

## Verification update — 2026-09-16 — current committed friend bundle

The existing committed-source packager was smoke-tested at HEAD
`fdb4526a18177094e49a3aff69716c2d0b0f526b` into a disposable Windows temp
directory. The generated `QuestLab-fdb4526` bundle and zip were created
successfully; the packed `progress.json` matched the Git blob at HEAD,
`tutor.py` was absent, and `QUESTLAB_BUNDLE.txt` stated the committed-source
boundary. The package output was removed after inspection. This confirms
F-046's custody guard on the current tip; it does not certify a friend's clean
Windows/CachyOS launch or hosted sync.

## Capability boundary — 2026-09-16

No-input work that remains safe and useful is limited to local deterministic
tests, isolated WSL/ext4 browser K&M, launcher/preflight/package custody,
build/compile checks, and persistent documentation/review. These can verify
state authority, revision/event projection, conflict handling, mode boundaries,
PTY continuity and source custody without touching the protected save.

They cannot prove a real PC/laptop cloud round-trip, authenticated Supabase
RLS, the approved per-device save-custody migration, clean friend-machine
launch, native CachyOS support or Tauri. Those gates remain open by design.
The only upstream change merged in this checkpoint was the public
activity-only commit `cab6b0c`; no cloud seed or legacy `progress.json` edit
was made.

## Verification update — 2026-09-16 — post-merge local regression

At current refs `feature/cloud-sync-desktop` and `main` (`f5e2a41`), the fresh
WSL backend suite passed **81/81**, the frontend suite **36/36**, Python
compilation passed, and Vite built **1,345 modules**. The local two-cache sync
simulator preserved the source digest, rejected stale mailbox/local pulls with
`409`, and recorded the explicit `sync_apply_cloud` resolution. The committed
bundle's packed `progress.json` matched `git rev-parse HEAD:progress.json`,
`tutor.py` was absent, the manifest was present, and temporary output was
removed. This was a no-code/docs/activity checkpoint; no cloud seed, legacy
edit, protected-save write or second-device claim was made.

## Security review update — 2026-09-16 — F-050 sanitizer recheck

DOMPurify `3.4.15` is available, but Monaco `0.56.0` pins and bundles
DOMPurify `3.4.8` inside its own editor module. A temporary nested npm override
was verified in an isolated install: `npm ls` showed `3.4.15` and `npm audit`
showed zero advisories, yet the actual Monaco bundle still contained the
`3.4.8` sanitizer. The override and lockfile change were reverted, and the
working dependency tree was restored to the committed graph. F-050 therefore
remains an explicit accepted low/moderate risk until an upstream Monaco bundle
or separately reviewed patched build replaces the embedded sanitizer. No
package workaround was committed or described as a security fix.
