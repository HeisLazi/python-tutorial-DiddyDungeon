# Forge roadmap issue log

## Campaign v1 homestead hierarchy and merchant lore gate — F-250 (2026-09-20)

The first Home/Market prototype pass was visually useful but the Home title read as a large instruction and the Market greeted the player with a placeholder initial that made the vendor feel unfinished. Refined the isolated prototype only: Home now leads with the shorter `Your homestead.` title and a compact purpose line; the Market presents the vendor as `The Merchant` until a future village lore event sets the serializable `merchantNameKnown` flag, at which point the authored name `Rook` can be revealed. Updated the map summary and transient market events to respect the same gate. No image assets, canonical Forge state, Supabase, progress files, or PTYs were changed.

Verification: browser K&M inspection on `http://127.0.0.1:5207/?home-market-pyr1=final` showed the refreshed Home hierarchy and the Market greeting with `The Merchant`; prototype tests **14/14**, `node --check`, `git diff --check`, and the WSL production build pass. Remaining design work is original pixel-art direction and animation, intentionally not substituted with an unlicensed or low-fidelity placeholder.

## Campaign v1 deterministic pixel-sprite contract — F-251 (2026-09-20)

Generated character PNGs were rejected for this surface because they bake in a static look and make movement/equipment upgrades awkward. Removed the PNGs from the prototype path and replaced the Merchant placeholder with a tiny palette-and-frame renderer in `prototypes/campaign-v1/src/pixelArt.js`; CSS swaps two crisp 16x28 pixel-grid frames (including a blink) for a lightweight idle animation. Added `PIXEL_ART_PIPELINE.md` with a Pixelorama-first workflow and an Aseprite/JSON export contract for future authored assets. No canonical Forge state, Supabase, progress files, or PTYs were changed.

Verification: live browser K&M inspection showed the readable colored Merchant grid and blink frame on the same lore gate and market controls; prototype tests **15/15**, `node --check`, `git diff --check`, and the WSL production build pass.

## Campaign v1 cryptid merchant scene pass — F-252 (2026-09-20)

The first pixel Merchant read as a creature dropped into an unrelated flat green/brown room. Kept the funny cryptid-inspired silhouette, added a more human face/hat treatment, gave him a non-blocking speech bubble, and replaced the room with a lantern-lit pixel bazaar palette and grid texture. The scene still keeps the character frame, counter, nameplate, and future equipment swaps independent. No canonical Forge state, Supabase, progress files, or PTYs were changed.

Verification: live browser K&M inspection showed the new room, speech bubble, readable Merchant, and idle-frame animation at `http://127.0.0.1:5207/?home-market-pyr1=final`; prototype tests **15/15**, `node --check`, `git diff --check`, and the WSL production build pass.

## Campaign v1 reference-guided Merchant sprite refinement — F-253 (2026-09-20)

The cryptid pass still read too much like a teal superhero mascot when compared with the supplied Merchant reference. A Claude design critique identified the highest-leverage gaps: no readable brim/hat separation, a flat face without an asymmetric eye cue, and palette tokens for the monocle/coins that were defined but unused. Refined the isolated, data-driven 16x28 frames only: the Merchant now has a dark broad-brim hat with a small gold pin, warm face highlights with offset eye/glint geometry, textured warm collar, teal coat, and a clustered copper/gold hand accent. The scene remains code-native and swappable; no static PNG or licensed asset was added.

Verification: CUA browser screenshot at `http://127.0.0.1:5207/?home-market-pyr1=final` was visually inspected after each sprite pass. Claude’s final sign-off confirmed the dark hat, warm face, textured collar, asymmetric hand and coin cluster, and explicitly judged the sprite no longer Booster-Gold-like; its last one-pixel eye-position suggestion was applied and rechecked live. Prototype tests **15/15**, `node --check`, `git diff --check`, and the WSL production build pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.


## Campaign v1 homestead and character-led market pass — F-249 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-249 | P1 | Campaign v1 Home and Market | Home still read as a compact station selector and Market opened directly into a generic shelf, so neither surface felt like a place in the learning campaign. There was also no meaningful companion loop for Pyr. | Fixed in the isolated prototype. Home is now a CSS-built interior with clickable Hearth, Armory, Pantry, Study, and Pyr’s perch hotspots; the context panel exposes recovery, loadout, supplies, upgrade tokens, and a clear return to the Bounty Office. Pyr has serializable bond, energy, feeding, training, and evolution state (`Tiny Code-Flame` -> `Emberling` -> `Flarekin`) without inventing combat rewards. Market now opens on a large Merchant greeting scene with purse and `Browse today’s lots`, then transitions to a WoW-inspired but original single-player browser with categories, readable lot rows, selection details, and buy-only actions. The personal name `Rook` stays a later lore unlock. | Fixed / verified |

Verification: CUA loaded the cache-busted prototype at `http://127.0.0.1:5207/?home-market-pyr1=3`, visually inspected Home and Pyr’s activity panel, opened Market’s greeting, entered the lots browser, filtered Trinkets, selected Syntax Ward, and bought it; the purse changed from 84 to 36 and the selected-lot state changed to OWNED. Prototype tests **14/14**, `node --check`, `git diff --check`, and the WSL production build pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.


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
| F-033 | P2 | WSL frontend packaging | WSL Vite cannot resolve the Linux Rollup optional package from the shared Windows `node_modules`; this is an environment/dependency-install issue, not a source failure. | Open only for the unsupported live-OneDrive install path: a fresh ext4 clone now passes `npm ci`, frontend **69/69**, Vite build (**1,346 modules**) and backend **115/115**. The launcher still fails early with an actionable Linux Rollup dependency message on the wrong tree. Never run `npm install`/`npm ci` against the live OneDrive-mounted `ide/frontend/node_modules`; install Linux dependencies in a disposable WSL/native checkout instead. |
| F-034 | P2 | Secondary review | Claude Code was previously unauthenticated in the WSL CLI despite the separate desktop login. | Fixed for this checkpoint: authenticated WSL Claude Code completed a read-only roadmap/source review and returned the next-slice plan. It did not edit files or touch `progress.json`/`tutor.py`; its findings are recorded below and remain secondary review, not approval. |
| F-035 | P3 | Dev HMR lifecycle | Editing the running Vite source caused one disposable-runtime terminal websocket reconnect; normal revision polling/navigation did not remount it. | Fixed in source: terminal sessions now live in a browser-global role registry with a short detach grace period. Fast Refresh rebinds a new xterm view to the existing WebSocket/PTY instead of closing the session. Fresh browser-HMR K&M remains unavailable under F-080, so live visual proof is still external. |

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
| F-050 | P3 | Frontend dependency audit | The locked frontend tree reports two package-level vulnerabilities in Monaco's bundled DOMPurify path (four GHSA advisory records: one low and one moderate package-level result; no high/critical findings). | Decision recorded: retain `monaco-editor` 0.56.0 / DOMPurify 3.4.8 as an accepted low/moderate risk. The 0.53.0 “fix” is rejected because its vendored DOMPurify is older 3.1.7 and merely invisible to npm audit; revisit only when upstream bundles a version above 3.4.12. |
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
| F-058 | P2 | Native Linux distribution | Friend onboarding covered Windows/WSL and ext4 smoke only; the requested CachyOS laptop had no explicit native-Linux install, launch, dependency or PTY acceptance gate. | Open only for the actual CachyOS machine: a fresh ext4 clone passes `npm ci`, frontend **69/69**, Vite build (**1,346 modules**) and backend **115/115**, with cleanup verified. It is not certified until the physical CachyOS checkout also passes install/launch, canonical-state, live-projection and shell/AI PTY K&M checks. |

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

## Verification update — 2026-09-16 — clean ext4 live projection

The current branch was installed and built in a disposable WSL ext4 clone and
launched with an isolated derived state cache on ports `7435/5245`. Native
`npm ci`, backend **81/81**, Python compilation, Vite (**1,345 modules**) and
the PowerShell-free Linux preflight passed. Pure in-app-browser K&M used
click/type/scroll only: the trusted reward path updated HUD, Character and
Homestead live; two verified objectives cleared **The Empty Table**, emitted
validated reward/next-encounter/achievement notifications, advanced Quest
Journal to **The Dealer's Hand 6/6**, and added the defeated encounter with
verified evidence to Codex. All five monochrome SVG icons rendered without
empty nested pills, both PTY labels stayed `CONNECTED`, and the browser
error/warning log was empty. The isolated runtime and files were removed
afterward; the protected save and `tutor.py` were untouched.

This closes no external issue. Real laptop↔PC sync, authenticated hosted
state, native CachyOS certification, friend-machine packaging and Tauri remain
the open gates listed under F-018, F-039, F-050, F-058 and Milestone C.

## Verification update — 2026-09-16 — verified local custody resume

The explicit local-custody path had one restart edge: a cache that was
advanced through the state gateway after migration was later rejected as a
generic conflict. F-061 records that defect. Commit `3def7a3` adds a
gateway-written provenance marker and lets a later local launch resume only
when the reviewed source digest/revision still match and the destination is
strictly advanced. Unmarked or changed-source divergence remains blocked for
review; no newest-file merge was added. Focused tests **21/21**, backend
**84/84**, frontend **36/36**, compile and Vite build passed, and disposable
K&M relaunched the saved Dungeon checkpoint with both PTYs connected.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-061 | P2 | Local custody restart | A valid state-service-advanced per-device cache was rejected on the next explicit local launch, stranding checkpoints after restart. | Fixed locally in `3def7a3` with source-digest/revision provenance validation; real user-save migration and F-039 custody choice remain open. |

## Operational diagnosis — 2026-09-16 — stale Forge endpoint on the PC

The user's visible old Forge was confirmed to be the pre-existing long-lived
`5173 → 7332` pair from `~/projects/python-tutorial-DiddyDungeon`. A second
manual pair exposed a related mismatch: the current-checkout frontend on
`5174` was configured for backend `7333`, but that backend was also running
with the old repository environment. This is the already-tracked F-025/F-031
stale-runtime/checkout choice, not a new source-state split-brain path.

No existing process or PTY was killed. A separate current-tip hybrid was
started for verification with the Windows frontend on `5176` and the current
WSL backend on `7335`. Its runtime report showed branch
`feature/cloud-sync-desktop`, HEAD `d7110b7`, canonical state revision 5,
Level 2 / 50 XP / 55 coins and The Hitman. The in-app browser hydrated the
same projection without a refresh; the protected save digest remained
unchanged. Use the guarded launcher or the printed current-tip URL rather
than reusing a manually paired old port.

The WSL OneDrive frontend dependency guard correctly rejects the mounted
Windows `node_modules` tree when Linux Rollup is absent (F-033); the temporary
hybrid used native Windows Vite plus the WSL backend only to make the current
PC endpoint usable without modifying dependencies or the save.

## Workspace source-transfer slice — 2026-09-17

The player-source problem is separate from campaign-state sync. The canonical
state service can move progression, but a workspace's edited `blackjack.py`,
Campaign `tutor.py` and `dungeon.py` were not transported to the other device;
the committed-source packager also intentionally omitted untracked personal
files. A direct branch push would be unsafe because the workspace branch can
contain `progress.json`, session notes or credentials.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-062 | P2 | Workspace source custody | PC/laptop source files did not have an explicit transfer channel, so a saved campaign could arrive without the code/notebook needed to continue it. | Fixed locally with `questlab-files`: a separate `questlab-files/<project-branch>` ref carries only the UTF-8 allowlist (`blackjack.py`, Campaign `tutor.py`, `dungeon.py`) plus a bounded hash manifest. Push/pull require distinct confirmation tokens; `progress.json`, notes, secrets, Git history and PTYs are excluded. Clean older files update normally; dirty conflicts refuse by default and explicit overwrite creates a backup. Real device round-trip remains user-run evidence. |

Focused transfer tests cover sanitized trees, protected-save preservation,
clean-device updates, dirty-conflict refusal/backup and dirty-file reporting.
The helper is local/Git-backed by design; it does not start Supabase source-file
transport or change the campaign state authority.

## Operational diagnosis — 2026-09-17 — first source bundle published / portrait session

The transfer channel was initially empty because no device had published a
bundle. The current reviewed workspace was then published without touching its
save: `questlab-files/01-blackjack` now points to
`64696bee98228b342404525994122f69af4bbdaf`, and the helper reports matching
hashes for `blackjack.py`, Campaign `tutor.py` and `dungeon.py`. The other
device still needs the explicit pull documented in `WORKSPACE_TRANSFER.md`;
this is intentionally not an automatic branch merge.

The current Forge browser also reports `Sign in to sync`, so it is anonymous.
Portraits are account-private Supabase assets and are not part of Git or the
campaign save. No portrait can appear in that session until the same Quest Lab
account is signed in (or the account's `avatar_path`/Storage migration is
verified). No credentials, avatar data or PTY was changed during this check.

The current-tip runtime is the separately launched `5176` endpoint and reports
`feature/cloud-sync-desktop`; the long-lived `5173` endpoint still serves the
older checkout. Opening the old tab can therefore show both the old UI and an
anonymous/local avatar even when the current branch is healthy. Use the guarded
launcher and its printed URL, then sign in on that origin.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-063 | P2 | Avatar identity visibility | An anonymous Forge session has no account identity from which to download the private portrait, making the rail/Character avatar look unsynced. | Fixed for the hosted QA path: the disposable account registered a profile/device and two isolated clients uploaded, downloaded and replaced the private avatar; anonymous profile/object reads were denied. The remaining gate is the user's own PC/laptop sign-in and portrait round-trip on the corrected runtime. |

## Roadmap UI / learning-surface slice — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-064 | P1 | Tutor/Practice workflow | Practice controls lived beside a separate training form while `tutor.py` was the intended shared learning IDE; the old copy also said Practice never wrote the notebook. | Fixed in the current UI: Tutor Notebook and Practice use the same `tutor.py` editor, server-owned selectors, notes directory and bounded PYR prompt. Practice remains a separate no-reward state-service mode. |
| F-065 | P1 | Live campaign projection | A real verified state mutation needed to reach every RPG surface without a refresh, while stale shell/AI remounts could hide whether the projection was live. | Fixed locally with revision-aware polling and event/reward queue. Isolated K&M acceptance observed Resolve, HUD, Character, Homestead, Journal and Codex changes while both PTYs stayed connected. |
| F-066 | P2 | Homestead / Journal scope | Legacy DOM enhancement injected Future Loot/Trinket Vault into Homestead and Weekly Raids into the Journal, mixing future content into surfaces that should show current loadout and journal pages. | Fixed locally: stale injected nodes are removed and raid planning is shown on the Hub; future loot remains in Codex/validated projections only. |
| F-067 | P2 | Codex learning depth | The previous Codex summary did not expose a usable concept-book view with generic examples, mistakes, validated question lenses and transferable notes. | Fixed locally with field-library pages, encounter evidence, bounded canonical notes and `notes/<concept>.md` workspace notebooks. Exact hidden future answers remain excluded. |
| F-068 | P2 | Launcher continuity | A splash/route transition could obscure whether PTYs were being remounted, and fresh workspaces could open an infrastructure file instead of the player project. | Fixed locally: splash preserves mounted terminals; editor file selection filters infrastructure/tests, prefers `blackjack.py`/campaign/main, and otherwise shows No file selected. |
| F-069 | P2 | Acceptance coverage | Static checks alone did not prove a state-service Battle mutation reached the browser projection. | Closed for local v1 with a disposable-cache, no-refresh K&M test: two validated Hitman objectives produced Resolve 4/8 → 0/0, XP/coins, next encounter, Codex evidence and persistent PTY connections. Real two-device and hosted cloud acceptance remain open. |

The browser evidence above intentionally used a disposable canonical cache. It
must not be read as permission to copy or merge the protected repository save;
the root `progress.json` remains the only local canonical save and legacy
workspace files remain evidence/migration inputs only.

## Infinite Dungeon route selector — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-070 | P1 | Dungeon navigation / checkpoint coherence | The map was decorative and the client inferred the next room from a modulo rule, so the requested choose-room → question → choose-room loop was not state-service-owned. | Fixed locally: `dungeon_choose_room` validates answer-free route choices, the selector reappears after each resolved room, future questions stay hidden until selection, `dungeon.py` blanks on transition, and restart-safe disposable K&M coverage passed. Hosted Dungeon sync and authenticated leaderboard remain later gates. |

## Regression hunt — 2026-09-17 — original Tutor/Practice contract

The original redesign brief was re-read before this hunt. The current local
contract is one managed `tutor.py` Tutor/Practice IDE with selectors and notes;
Practice has independent no-reward history but cannot mutate Campaign/Dungeon
progression. The disposable runtime used separate state/workspace paths and
pure browser K&M (no Playwright). The protected save and user source files
were not staged or written.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-071 | P1 | Tutor/Practice provider handoff | Clicking Codex, Claude or AGY launched the AI PTY but did not persist the tab-scoped provider marker consumed by the bounded Tutor/Practice request path. A subsequent Ask PYR action therefore stopped with the generic “launch first” guard. | Fixed locally in `AppV2.jsx` and legacy `App.jsx`; a frontend source regression test covers the marker, provider read and bounded notice. Minimal K&M reproduction: click AGY, then Ask PYR; after repair a Practice session and bounded prompt were created. |
| F-072 | P2 | Workspace state authority | A legacy/worktree `progress.json` was omitted from direct file access but still appeared in the Forge file tree, making a non-authoritative save look like an editable live project file. | Fixed locally in `build_tree()`; the tree contract now hides `progress.json` and the context bridge test proves it remains non-authoritative. Minimal reproduction: create a synthetic workspace `progress.json` and reload the tree; it no longer appears and canonical projection is unchanged. |
| F-073 | P1 | Tutor/Practice context bridge | After opening the shared Practice/Tutor editor, `POST /api/pyr/context` rejected active `tutor.py` with 403, so the provider prompt could not receive the bounded notebook context even though the dedicated Tutor route was valid. | Fixed locally: the bounded read bridge permits the managed workspace `tutor.py`; generic `/api/file`/format writes still reject it. Focused context tests and the full backend suite pass. Final disposable K&M reproduced the repair: AGY → Ask PYR visibly showed `Practice drill requested from agy`, and the backend logged `/api/pyr/context` **200 OK** while both PTYs stayed connected. |
| F-074 | P3 | Release contract documentation | The roadmap/report/onboarding text still said Practice could not write `tutor.py`, contradicting the settled product decision that Tutor and Practice share one managed notebook/editor. | Fixed locally by aligning the current normative sections with the shared-editor/no-reward contract; historical review entries remain preserved as history. |
| F-075 | P2 | Dungeon editor continuity | The redesign contract called for a usable code-editor tab after choosing a Dungeon room, but the route map previously had no explicit editor surface in the room flow. | Fixed locally: Dungeon now exposes Map & route and Code editor tabs; the editor is enabled only for a state-issued encounter, saves the managed checkpoint through the gateway, clears/rotates with room transitions, and returns to the same map without remounting PTYs. Disposable browser K&M and backend 200 evidence passed. |
| F-076 | P2 | Dungeon encounter identity | Adaptive Dungeon questions were state-owned and progressively scored, but the current room had no explicit custom-mob identity or phase, weakening the evolving-gauntlet presentation and reward feedback. | Fixed locally: the gateway now emits a bounded current-mob descriptor (server-owned name/category, recorded concept focus, difficulty phase) only after a route issues the question; verdict events name the defeated/attacking mob, while selectors keep future rooms hidden. Backend/static gates and fresh disposable K&M passed; the selector exposed no future mob names/questions and both PTYs stayed connected. |

Primary hunt score: **17** (F-071 6 + F-072 4 + F-073 6 + F-074 1). These
were four unique confirmed defects, including one release-documentation defect;
no false positives were scored.

Claude Sonnet was invoked as a read-only reviewer for this checkpoint but did
not return before the bounded CLI wait expired; no Claude finding or score is
claimed. Copilot was not installed on this workstation, so no Copilot finding
or score is claimed. This does not block the local deterministic gates, but it
does mean the reviewer scoreboard is intentionally incomplete for this run.

Evidence for the repair: backend **97/97**, frontend **37/37**, Python
`compileall`, and the disposable browser K&M path all passed. The latest
frontend dependency/build attempt is documented as an environment-only
mounted-tree/Node memory limitation; no source failure is claimed from that
attempt.

## Native Linux launch slice — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-077 | P2 | CachyOS distribution | The branch had a native-Linux setup checklist but no guarded launcher equivalent to the Windows wrapper, leaving branch freshness, workspace identity and stable-PTY expectations to manual shell commands. | Fixed locally with `tools/questlab-launch.sh`; it validates the intended branch/upstream, checks native venv/frontend prerequisites, warns on protected-save dirtiness, forwards explicit workspace/port/custody flags to `python -m ide.quest`, and never enables backend reload. Actual CachyOS installation and K&M acceptance remain open under F-058. |

The wrapper passed `bash -n`, `--help`, the launcher contract suite (**14/14**)
and the full WSL backend suite (**98/98**). No save, workspace source file,
legacy evidence or existing runtime was changed.

## Cloud campaign projection slice — 2026-09-17

The original cross-device symptom was narrower than the player HUD: the
existing cloud projection carried player/equipment/companion/Homestead, but
left projects, cleared mobs, Codex evidence, skills, goals, Practice history
and Dungeon checkpoints on the device that created them. A laptop could
therefore receive Level/XP/coins while its Journal, Codex and Dungeon still
looked like a starter cache.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-078 | P1 | Cross-device campaign coherence | The revision/CAS sync row omitted validated campaign evidence and restart-safe Dungeon state, so a cloud pull could not hydrate Journal/Codex/current encounter or resume a Dungeon checkpoint. | Fixed in source: the local projection, browser SyncEngine and unapplied hosted migration now carry a bounded `campaign` domain. Projects/mobs, Codex results/notes/player-authored notes/mastery evidence, skills/goals/streak/achievements, Practice history and the answer-free current Dungeon checkpoint use the same revision/CAS flow. Unknown fields, future rewards and Dungeon answer keys are rejected; cloud merges retain local-only `learning_state.last_teachback`. Hosted migration, authenticated two-device pull/push and real laptop/PC K&M remain open gates. |

The Codex-note recheck passed WSL backend **101/101**, migration contracts
**7/7**, clean frontend **40/40**, and the **1,346-module** build. The
protected-save simulator retained campaign evidence on both disposable
devices without changing the source digest.

Local proof: state-service focused tests **40/40**, migration contracts **7/7**;
the projection measured **9,897 UTF-8 bytes** for the current protected save,
and the campaign merge increments the canonical revision with a
`sync_apply_cloud` event. The protected save, `tutor.py`, `dungeon.py`, and
existing PTYs were not written or restarted. The mounted Windows frontend
dependency tree still has the known F-033 missing Supabase package metadata;
clean disposable frontend testing remains the required JS/build gate.

## Disposable cloud-account acceptance — 2026-09-17

To exercise account-scoped portrait and workspace behavior without touching a
user account, a separate disposable Supabase QA account was created and used
against isolated Forge runtimes. The account successfully registered a
profile/device, uploaded an avatar, downloaded it from a second isolated
client, and received a replacement avatar through the shared Storage object
and `updated_at` reference polling. The Git-backed workspace transfer also
passed with `blackjack.py`, `tutor.py`, `dungeon.py`, and `notes/lists.md`
matching on the target while `progress.json`, session notes, and an unlisted
private note remained untouched.
Anonymous reads of the QA portrait returned HTTP 400 and the profile endpoint
returned HTTP 401, so the private Storage/RLS boundary also held in this
check.

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-079 | P1 | Hosted campaign sync | The live `save_player_state` RPC still runs the pre-campaign validator. A real authenticated disposable account received `next_state contains unsupported domains` when SyncEngine submitted the now-source-reviewed `campaign` projection, so hosted player/campaign sync cannot yet be claimed. | Confirmed hosted blocker. Apply and verify `20260917000100_player_state_campaign_projection.sql` through the approved Supabase migration path, then repeat authenticated two-device acceptance. No hosted migration was applied in this QA pass. |
| F-080 | P2 | Browser QA surface | The Codex in-app browser could not attach a tab to the isolated disposable Forge URL, so this pass has no fresh browser K&M claim; API/SyncEngine and Git transfer checks are recorded separately. | Environment blocker only; no source defect claimed. Existing no-refresh K&M evidence remains documented from the prior disposable runtime. |

The disposable QA account is not the user's personal account. Its portrait
was left in place for repeatable QA; no password or token is stored in this
repository. The protected save and existing shell/AI PTYs were not touched.

## Sync-status copy recheck — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-081 | P3 | Account status messaging | After the campaign projection landed, the signed-in cache detail still said Projects and Codex remained local, contradicting the shared revision transport and making a healthy implementation look incomplete. | Fixed in `syncEngine.js`; the status now names Campaign, Journal and Codex as gateway-synced surfaces. A regression test covers the emitted status detail. |

The focused frontend suite is now **41/41** and the clean ext4 production build
still transforms **1,346 modules**. The protected save and user notebooks were
not staged or written.

## Hosted-schema failure UX — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-082 | P2 | Cloud sync diagnostics | When an older hosted validator rejected the new campaign projection, Forge only showed a generic cloud error even though the local outbox safely retained the change. | Fixed in `syncEngine.js`: the UI now reports `Cloud schema needs migration`, names the exact campaign migration, and keeps the queued local change visible. A regression test covers the rejection path. |

The clean ext4 frontend suite passed **42/42** and the production build
transformed **1,346 modules** after this repair.

## Signed-in first-frame status copy — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-083 | P3 | Sync-status continuity | The initial signed-in render briefly described only Campaign syncing, then changed to the settled Campaign/Journal/Codex wording after account registration. That copy mismatch made the top sync indicator appear to jump even though no gameplay state was remounted. | Fixed in `syncEngine.js`: the pre-registration and settled signed-in states now use the same gateway-surface description. The regression rejects the stale first-frame phrase; clean frontend tests remain **42/42** and the **1,346-module** build remains green. |

## Native macOS onboarding — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-084 | P2 | Friend distribution | The friend guide covered Windows/WSL and CachyOS but did not give a native macOS path, even though the stable Python/Vite launcher does not require WSL. | Fixed in documentation: `FRIEND_ONBOARDING.md` now provides a Homebrew-optional native macOS setup, sibling workspace, executable-bit and guarded launcher commands. Actual Mac install, K&M live projection and PTY acceptance remain unverified and are not claimed. |

## Avatar cache custody — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-085 | P1 | Account portrait privacy/sync | A signed-in avatar upload also populated the unscoped local avatar key. A later sign-out, account switch or remote removal could therefore display the wrong portrait or resurrect a stale local fallback even though private cloud Storage remained protected. | Fixed in `SyncEngine`: signed-in cache writes/restores are account-scoped, anonymous uploads remain local-only, and a current account with no cloud portrait resolves to an empty state instead of the unscoped fallback. Frontend avatar regressions pass in the clean ext4 suite (**43/43**). |

## Handoff precision review — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-086 | P3 | State-command documentation | The implementation already rejected internal `system` actions over HTTP and CLI, but the handoff did not state the exact public actor boundary, leaving room for a future integrator to treat `system` as a caller-supplied actor. | Fixed in `AGENT_CLOUD_DESKTOP_HANDOFF.md`: HTTP/CLI accept only `player` and `pyr`; `system` is reserved for trusted in-process `apply_internal` calls. |
| F-087 | P3 | Tutor/Practice documentation | The implementation already shared the managed `tutor.py` and notes routes while keeping Practice progression-independent, but the handoff could be read as describing a second Practice notebook or endpoint. | Fixed in the handoff: Tutor and Practice share one managed editor/notebook and dedicated routes; only their sessions/progression boundaries differ. |

## Editor shortcut follow-up — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-088 | P1 | Editor submit shortcut | `Ctrl/Cmd+Shift+Enter` was handled only by the legacy bubble listener, allowing Monaco to consume the event while a Python file had focus. | Fixed in `AppV2.jsx`: the capture-phase shortcut boundary now prevents Monaco insertion and triggers the existing bounded PYR submit bridge. Frontend source coverage passed **26/26**; clean ext4 frontend coverage passed **44/44** and the production build passed. |

| F-089 | P2 | Disposable hosted QA identity | A fresh mailbox-backed Supabase Auth signup for the requested Codex-owned QA account returned HTTP **429 `over_email_send_rate_limit`** before issuing a user/session. | External provider gate. Do not bypass with a service/admin key or rate-limit spoofing; retry after the project email quota recovers. The prior disposable hosted portrait pass plus local account/avatar/file-transfer contracts remain the available evidence. |

| F-090 | P3 | Stale v2 handoff contract | `FORGE_V2_HANDOFF.md` still described Practice as unable to use the managed `tutor.py`, Dungeon/Practice as starter-only and combat as display-only, contradicting the current local state-service implementation. | Fixed in the handoff: shared Tutor/Practice notebook boundary, local Dungeon/Practice loop and provider-validated local verdict outputs are described accurately; hosted/authenticated and real-device gates remain explicit. |

| F-091 | P3 | Sign-up quota feedback | A real disposable signup attempt exposed Supabase's raw `over_email_send_rate_limit` text in the account panel, which was provider jargon and did not tell the learner whether an account had been created. | Fixed in `SyncEngine`: the bounded provider code now becomes a clear retry-later message that explicitly says no account was created; the diagnostic code remains attached and clean ext4 frontend coverage passes **45/45**. |

This is a local editor-flow repair only. Provider-authenticated adjudication and
the hosted campaign migration remain separate Milestone C gates.

## UI coherence and Dungeon inventory slice — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-092 | P2 | Navigation | Practice and Tutor appeared as duplicate tabs for the same managed notebook. | Fixed: Tutor is the only rail destination; legacy `practice` state is normalized to Tutor while Practice progression remains separate behind the shared Tutor surface. |
| F-093 | P1 | AI layout | Hidden AI still occupied a blank grid column and visually covered route content. | Fixed: AI remains mounted but is parked off-canvas, with a route-scoped pop-out toggle and no AI/sidebar on the Hub. |
| F-094 | P1 | Quest Journal layout | Main Quest was constrained to one side of a two-column page with an empty right panel. | Fixed: journal pages now occupy the full available width and keep the visual page-turn/contract page behavior. |
| F-095 | P1 | Campaign combat HUD | Forge's campaign file view did not expose the active enemy Resolve bar for an encounter without objectives. | Fixed: the state-service encounter projection now renders the Resolve meter and mob identity in the Forge battle sidebar. |
| F-096 | P2 | Infinite Dungeon loadout | Run Loadout had no inventory selection path, so purchased gear could not be re-equipped. | Fixed through the canonical state gateway with bounded run inventory, `/api/dungeon/equip`, and an inventory menu. |
| F-097 | P2 | Launch UX | The boot screen lacked a fade-out and a named return greeting after a long absence. | Fixed with first-launch/20-minute return detection, fade-in/fade-out animation and username-based welcome copy. |

Clean ext4 frontend verification is **47/47** with a **1,346-module** Vite
build; mounted Forge source coverage is **28/28** and the WSL backend suite is
**101/101**. Fresh browser K&M remains an environment gate because the Codex
in-app browser could not attach a tab in this pass. No protected save,
`tutor.py`, `dungeon.py` or existing PTY was touched.

## Character/Homestead and Battle workspace follow-up — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-098 | P2 | Wide presentation surfaces | Character and Homestead still inherited the split IDE/sidebar layout instead of using the Hub's full-width presentation surface. | Fixed with a shared `wide-mode` for Hub, Character and Homestead; their route-specific game screens now fill the workspace and the AI stays parked unless opened. |
| F-099 | P1 | Quest Journal navigation | The Battle shell was embedded in the Main Quest page, making the journal page feel like a form rather than a journal. | Fixed with Journal pages and Battle shell as two in-journal screens, analogous to the Dungeon map/code tabs. |
| F-100 | P1 | Campaign answer workspace | Battle answers used a small sidebar textarea that did not feel like the normal campaign/Tutor writing surface. | Fixed with a dedicated Battle workspace card and larger code-friendly editor textarea while retaining the existing validated submission boundary. |

Fresh ext4 frontend tests/build and the WSL backend suite remain the required
verification gates for this slice; no cloud transport or PTY lifecycle was
widened.

## React combat-surface ownership follow-up — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-101 | P1 | Journal / Character rendering | The legacy `combatShell.js` mutation pass still appended a second Battle Shell after the React Journal and could replace the React equipment list. Revision polling therefore made the page jump or show duplicate combat UI even though the canonical state was unchanged. | Fixed: React remains the sole owner of Character, Homestead and Journal/Battle surfaces. The compatibility module now only removes stale legacy nodes and never injects or rewrites current React markup. |

The source regression covers the no-injection contract; the mounted Forge suite,
clean ext4 frontend suite and production build remain required gates. No PTY,
canonical save or cloud transport was changed.

## Boss phase and trinket trigger slice — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-102 | P2 | Combat progression | Boss validation had only an in-memory provider checklist, so a verified phase did not appear in the canonical revision/event stream; the documented trinket effects were presentation-only. | Fixed locally: `record_boss_requirement` persists only the bounded phase/evidence metadata, the projection exposes the current safe phase without prompts, and Ember Scythe, Guardian Sigil and Phoenix Ember effects are applied by the state service with auditable event fields. The React Battle screen renders the phase track and reward queue presents triggers. Hosted migration/application and provider-authenticated adjudication remain gates. |

The cloud projection/migration allowlist carries the bounded boss-validation
record for the next approved hosted-schema rollout; no hosted migration was
applied in this pass.

Verification: WSL backend discovery **103/103**, clean ext4 frontend **48/48**,
and Vite production build (**1,346 modules**). Browser K&M remains unavailable
in this environment because the Codex browser tab could not attach.

## Campaign loadout projection — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-103 | P2 | Campaign equipment | Homestead could display the current armor/trinket but had no state-owned inventory or safe way to equip validated campaign gear. A UI-only selector would also risk exposing future loot or inventing rewards. | Fixed with a bounded `equipment_projection`, a player-only `equip_equipment` mutation, and a trusted `record_equipment_unlock` event. Homestead now shows only canonical owned/current items, records equips in the revision/event stream, and explicitly keeps future loot hidden. Cloud projection carries bounded owned IDs for the next approved hosted rollout; no unsupported item is unlocked automatically. |

Verification for this slice: WSL backend discovery **105/105**, clean Windows
staging frontend tests **49/49**, and Vite production build (**1,346 modules**).
The protected `progress.json`, `tutor.py` and `dungeon.py` files remain outside
the commit, and no PTY was restarted. Browser K&M and hosted migration remain
external gates.

## Wide-route navigation recovery — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-104 | P1 | Navigation | Hub, Character and Homestead correctly became full-width, but removing the activity rail without a replacement left those routes as dead ends: a player could enter Homestead and have no visible way to reach Forge, Journal, Codex or Dungeon. | Fixed with a compact `Wide route navigation` bar inside every full-width route. It keeps the AI/IDE layout out of the presentation surface, marks the active destination, supports keyboard focus, and routes every destination through the existing `setActiveView` state without remounting PTYs. |

Verification for this repair: staged frontend tests **49/49** and Vite
production build **1,346 modules**. Browser K&M remains unavailable in the
current Codex environment, so no fresh click-through claim is made here.

## Navigation icon consistency — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-105 | P3 | Navigation polish | The recovered wide-route bar used SVG icons, but the persistent ActivityRail still rendered legacy glyph/emoji values. That made navigation look inconsistent and could reintroduce the empty-glyph regression. | Fixed: both the ActivityRail and wide-route bar now share the inline monochrome `RouteIcon` set; nested controls keep direct SVG sizing and color rules. |

Verification for this polish pass: staged frontend tests **49/49** and Vite
production build **1,346 modules**. No state, PTY or cloud transport behavior
changed.

## React navigation ownership — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-106 | P2 | Navigation stability | The legacy icon enhancement observer could still rewrite the React-owned ActivityRail after route/revision renders. The replacement was SVG, but it competed with React ownership and could cause visible icon/layout churn. | Fixed: the React rail declares its ownership boundary and the legacy bridge yields to it; legacy replacement remains available only for older non-React markup. |

Verification for this repair: staged frontend tests **50/50**, WSL backend
tests **105/105**, and Vite production build **1,346 modules**. No save,
cloud transport or PTY lifecycle changed.

## Friend bundle protection for Dungeon workspace files — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-107 | P2 | Distribution | The source-only friend packager allowed the dirty canonical save and `tutor.py`, but rejected an untracked protected `dungeon.py`, preventing packaging from a normal learner checkout. | Fixed: `progress.json`, `tutor.py`, `dungeon.py` and untracked `notes/` are treated as protected workspace data, never archived; committed source changes still fail closed. |

Verification: the launcher contract test passes. The post-commit package
smoke produced `QuestLab-ed8db52` from `git archive HEAD`; `tutor.py`,
`dungeon.py` and `notes/` were absent, and the bundled baseline
`progress.json` matched the `HEAD` blob rather than the dirty local cache.

## Wide-route callback compatibility — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-108 | P1 | Navigation | The alternate legacy `App.jsx` shell rendered the wide Hub/Character/Homestead route bar without passing its view callback into `GameScreen`, leaving the controls visible but inert in that shell. | Fixed by wiring `onNavigate={setActiveView}` through the legacy shell and covering the callback contract with a frontend regression test. |

Verification after publication: current-source navigation tests **32/32**,
clean ext4 frontend tests **51/51**, WSL backend tests **105/105**, and a
fresh Vite production build with **1,346 modules transformed**. The Codex
browser could not attach a fresh tab, so no new live click-through claim is
made here.

## Dungeon inventory cloud projection — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-109 | P1 | Cross-device Dungeon state | The local Dungeon checkpoint persisted run-earned inventory, but the browser campaign projection and hosted campaign migration omitted `dungeon_run.inventory`; a second device could resume the room while losing its temporary loadout. | Fixed with a bounded inventory whitelist in the SyncEngine projection, matching source-only SQL validation, and a two-device cloud round-trip regression. The hosted migration is still unapplied by the Milestone C boundary. |

Verification: clean ext4 frontend tests **51/51**, Vite production build **1,346 modules**, focused backend/migration tests **51/51**, and the full WSL backend suite remains **105/105**. No protected learner file was changed.

## Wide-route navigation visibility hardening — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-110 | P2 | Navigation affordance | The route bar for full-width Hub/Character/Homestead surfaces was implemented, but it could lose context during a long surface or appear ambiguous when an older bundle was still running, so the player could feel stranded. | Fixed with an explicit `data-wide-route` marker, a sticky route strip above the scroll surface, touch-sized targets and a regression assertion. The React `setActiveView` callback remains the sole route writer. |

Verification: current-source Forge runtime suite **32/32**. Fresh browser K&M
remains an external gate because the Codex browser could not attach a tab.

## Quest Journal folded into Codex — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-111 | P1 | Codex / campaign navigation | Active quest context and the Battle Shell lived on a separate Quest Journal route, while Codex held the learning library. This split made the current chapter, encounter story, stats and submission flow harder to follow and left stale `quests` route state possible. | Fixed: the legacy `quests` value normalizes to `codex`; Codex now owns the Active Quest/chapter/encounter sidebar, and a tabbed Books/Battle Shell surface provides journal-like page turns. Battle Shell renders validated story, boss/mob details, Resolve/objective state and existing submit callbacks without calculating rewards or revealing locked encounters. |

Verification: current-source tests **32/32**, clean ext4 frontend tests **51/51**,
and Vite production build **1,346 modules**. Browser K&M remains an external
gate because no Codex browser tab was attachable.

## Battle Shell encounter prop binding — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-112 | P1 | Battle Shell runtime | The tab rendered a Question Lens from `encounter`, but the new `QuestBattleScreen` signature omitted that prop. This was invisible to static tests until a render, where the tab would fail with an undefined reference. | Fixed by passing the canonical encounter projection through both Battle Shell call sites and asserting the binding in the Forge runtime suite. |

Verification: current-source **32/32**, clean ext4 frontend **51/51**, Vite
build **1,346 modules**. No state, save, PTY or hosted transport was changed.

## Codex bounded reading workspace — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-113 | P1 | Codex presentation | The Codex library, evidence, notes and mastery were all siblings in the global page scroll, producing the reported infinite-scroll feeling and making the actual book content visually secondary. | Fixed: Codex now fills the Forge viewport as a bounded workstation. The header and Books/Battle Shell tabs stay in place; the left Field Library/Active Quest index and right book page scroll independently; Mastery Signals are contained in the selected book pane. Mobile uses a single controlled column rather than forcing a cramped two-pane layout. |

Verification: current-source **32/32**, clean ext4 frontend **51/51**, Vite
build **1,346 modules**. Browser K&M remains an external gate because the local
Codex webview could not attach.

## Stale Quest Journal command — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-114 | P2 | Navigation / command palette | The command palette retained an `Open Quest Journal` action after Quest Journal stopped being a rail route. It had no matching button and undermined the single-Codex navigation contract. | Fixed by removing the stale action; Codex is now the only command/rail destination for the field-library and Battle Shell surfaces. |

Verification: current-source Forge suite **32/32**. Protected learner files,
canonical state, PTYs and cloud transport were untouched.

## Codex infinite-scroll cleanup — 2026-09-17

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-115 | P1 | Codex presentation | The bounded Codex still felt like an infinite page because the mastery grid was always appended to the reading surface and the outer flex column could grow as evidence accumulated. | Fixed with explicit three-row Codex layout, compact hero/header, contained index/book scrolling, overscroll boundaries and an expandable Mastery Signals section. Mobile keeps a deliberate single-column scroll fallback. |

Verification: current-source Forge suite **32/32**, clean archive frontend
suite **51/51**, and Vite production build **1,346 modules**. The Windows
working tree still has a locked esbuild process, but canonical state, learner
files, PTYs and hosted transport were not changed.

## Codex book-section overflow — F-116

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-116 | P1 | Codex presentation | The bounded book pane still read as an infinite scroll because definitions, encounter evidence, notebook content and mastery were all shown in one selected-page column. | Fixed with projection-backed Read, Encounters, Notes and Mastery sections. The active section is switched in-place, while the library index and reading pane remain bounded and the Battle Shell stays a separate Codex tab. |

Verification: current-source Forge tests **32/32**. Clean archive build and
browser K&M remain publication gates.

## Settings workspace transfer bridge — F-117

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-117 | P1 | Cross-device source files | The allowlisted `questlab-files` source transfer helper was CLI-only, leaving no safe Forge UI for reviewing or moving learner-authored project files. | Fixed with a Settings panel for status, push, pull preview and confirmed pull. It transfers only `blackjack.py`, `tutor.py`, `dungeon.py` and `notes/*.md`; progress state, PTYs and private logs stay local and canonical. |

Verification: focused WSL API tests **10/10** and current-source Forge tests
**32/32**. Hosted player-state transport remains a separate approval gate.

## Compact Codex outer-scroll regression — F-118

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-118 | P1 | Codex presentation | The narrow-window fallback restored an auto-sized Codex page and visible outer overflow, recreating the reported infinite-scroll behavior in compact Forge windows. | Fixed: the Codex shell remains viewport-bounded at every width. The narrow layout stacks the Field Library above the book while keeping each pane as its own scroll owner; Battle Shell remains separately bounded. |

Verification: current-source Forge tests **32/32**, with a regression rejecting
the old `height: auto` outer-scroll rule. Browser K&M remains environment-gated.

## Account portrait projection — F-119

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-119 | P1 | Avatar / identity | Cloud/avatar events were handled by a legacy DOM enhancer while React-owned rail and Character nodes continued to render initials, allowing a valid signed-in portrait to look stale or be overwritten during campaign polling. | Fixed: SyncEngine view state now carries the validated data URL in memory; ActivityRail and Character render it directly, while the enhancer yields to `data-react-avatar` ownership markers. Account-scoped caching, private storage and anonymous fallback boundaries remain intact. |

Verification: current-source Forge tests **32/32**. The user's real PC/laptop
portrait round-trip remains the hosted acceptance gate.

## Codex finite-book navigation — F-120

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-120 | P1 | Codex presentation | The Codex reading pane still felt like an infinite scroll and lacked book navigation; a compact override could restore a page-level scroll owner. | Fixed with a fixed-height book shell, a single contained scroll owner for the active section, explicit Previous/Next book controls, a BOOK n / total indicator, and page-turn animation keyed to book/section changes. |

Verification: current-source Forge tests **32/32**. Clean archive frontend
tests/build and browser K&M remain publication gates.

## Stale frontend bundle pairing — F-121

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-121 | P1 | Runtime identity | Branch/HEAD health was reported by the backend, but the launcher did not stamp the Vite bundle with the same checkout revision. An older frontend could therefore render the old Codex UI while the backend looked healthy. | Fixed: `ide.quest` exports `QUESTLAB_BUILD_SHA`, Vite embeds it, React compares it with `/api/runtime.repo_git.head_sha`, and the footer/data attributes expose an explicit frontend-stale warning. Manual unmarked Vite runs keep the existing runtime/branch checks. |

Verification: current-source Forge tests **33/33** and launcher contract tests
**14/14**. Clean archive frontend tests/build and browser K&M remain gates.

## Codex paper-surface polish — F-122

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-122 | P2 | Codex presentation | The new finite book prevented the reported infinite-scroll failure, but the surface still looked like a dense dark dashboard and example blocks ignored light/theme selection. | Fixed with a scoped paper/library treatment, inherited display typography, themed readable example blocks and clearer index/page hierarchy. No projection, scroll ownership or reward behavior changed. |

Verification: current-source Forge tests **34/34**. Clean archive frontend
tests/build and browser K&M remain visual publication gates.

## Codex outer-feed regression — F-123

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-123 | P1 | Codex presentation | The finite Codex still allowed the parent game surface and active book sections to behave like vertical feeds in compact/stale layouts, undermining the requested page-turn experience. | Fixed with a bounded `.game-screen` positioning context, an absolute viewport-pinned Codex shell, and `overflow: hidden` on book sections. The Field Library index is the deliberate scroll owner; book navigation uses Previous/Next and section tabs. |

Verification: current-source Forge tests **35/35**. Clean archive frontend
tests/build and browser K&M remain visual publication gates.

## Revision diagnostics in Account settings — F-124

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-124 | P1 | Cross-device sync UX | A signed-in player could see a generic Synced/Syncing label without a visible local campaign revision, cloud cursor or queue count. When a laptop stayed on an older level, the UI offered too little evidence to distinguish a stale frontend, a pending queue, a conflict or an unapplied hosted schema. | Fixed with a read-only Account diagnostics row showing the canonical local campaign revision, cloud cursor and queued mutation count. It reuses the existing state service and SyncEngine values; it does not reconcile, overwrite or invent player state. | Open hosted two-device acceptance remains required. |

Verification: current-source Forge tests **36/36**. Clean archive frontend
tests/build and browser K&M remain visual publication gates.

## Source-transfer hash visibility — F-125

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-125 | P1 | Cross-device source files | The transfer gateway already compared local and remote SHA-256 values, but Forge only rendered a generic tracked/different label. A player could not verify which file was stale or whether protected changes were excluded before applying a pull. | Fixed with read-only allowlisted-file digests, local/remote mismatch text, reviewed-edit count and excluded-change count. Push/pull confirmation and overwrite gates are unchanged. | Actual laptop/PC round-trip remains external acceptance. |

Verification: current-source Forge tests **37/37**. Clean archive frontend
tests/build and browser K&M remain visual publication gates.

## Local sync simulator recheck — F-126

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-126 | P2 | Offline/local sync | The local two-device contract needed a current-tip recheck after the Account and workspace-transfer slices so their diagnostics could not be mistaken for hosted mailbox proof. | Verified with tools/questlab-local-sync-sim.py --source progress.json: isolated device caches exchanged the bounded campaign projection, detected mailbox and local revision conflicts, completed an explicit keep-device resolution, preserved campaign/Codex/Dungeon fields, and left the source save digest unchanged. Hosted Supabase sync remains unproven. | Local simulator green; real account/device acceptance open. |

Verification: source digest before/after matched; no canonical or legacy save
write occurred. This is local compare-and-swap evidence only, not a hosted
Milestone C acceptance claim.

## Codex shell still inheriting the generic feed — F-127

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-127 | P1 | Codex presentation | The Codex root still carried the generic `game-screen-scroll` class. In a stale or compact bundle that generic height/overflow contract could compete with the bounded book grid, producing the reported infinite-page feel and making scroll ownership unclear. | Fixed by giving Codex its own viewport-pinned shell, removing the generic feed class, containing overscroll, and restoring one internal scroll owner for the selected book section plus the Field Library index. Battle Shell remains its own bounded tab. |

Verification: current-source Forge tests **38/38**. The change is presentation-only;
canonical state, revision polling, rewards, notes, learner files and PTYs were not
touched. Browser K&M remains the publication visual gate in this environment.

## Legacy shell Codex boundary parity — F-129

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-129 | P2 | Codex presentation | The bounded Codex selector was scoped to `.forge-v2`, while the compatibility `App.jsx` shell uses the shared `.game-screen` without that class. A stale/legacy shell could therefore miss the viewport-pinned boundary and regress to the old feed behavior. | Fixed by moving the positioning and overflow contract to the shared `.game-screen > .codex-screen` boundary. Current AppV2 and the legacy compatibility shell now receive the same finite-book containment. |

Verification: current-source Forge tests **39/39**. Clean archive build and
browser K&M remain publication gates; no state, learner file or PTY changed.

Recheck: clean archive frontend tests **58/58** and Vite production build
**1,346 modules** passed after the selector scope change. Browser K&M remains
the only missing visual proof for this slice.

## Codex finite reading-room follow-up — F-130

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-130 | P1 | Codex presentation | The outer feed boundary was fixed, but the Field Library index still owned the whole column's overflow. With the paper header, chapter/mob context and book list all sharing that scroll owner, the Codex could still feel like an ugly endless feed instead of a finite reading surface. | Fixed in source by making the game surface and Codex shell explicit height-bounded grids, keeping the header and tab strip fixed, making the index a flex column, and limiting index scroll to the concept book list. The reading section remains the single content scroller; page buttons and section tabs stay visible. |

Verification: current-source Forge tests **40/40**. This is a presentation-only
repair; state authority, revision polling, rewards, learner files and PTYs were
not touched. Clean archive build and fresh browser K&M remain publication gates.

## Secondary RPG emoji fallback — F-132

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-132 | P2 | Codex/Homestead presentation | The bounded Codex still had emoji glyphs in mastery and companion surfaces while the HUD/navigation used monochrome SVGs. Glyph metrics and color varied by OS/font, making the book surface look like a mixed legacy dashboard. | Fixed in source with SVG shield/flame/book icons and shared stroke sizing for mastery, companion and Homestead hearth surfaces. No state or reward semantics changed. |

Verification: current-source Forge tests **42/42**; clean archive frontend
tests **61/61**, Vite build **1,346 modules**, and WSL backend tests **108/108**
passed. Browser K&M remains the visual publication gate; no save, learner file,
PTY or hosted transport changed.

## Friend bundle tracked-save leak — F-131

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-131 | P1 | Distribution custody | The friend packager correctly archived `HEAD` and excluded uncommitted files, but `progress.json` is tracked in the repository. A package audit therefore found the committed baseline save inside both the folder and ZIP, contradicting the onboarding promise that player state never travels with the source bundle. | Fixed by removing `progress.json`, `tutor.py`, `dungeon.py` and `notes/` from the temporary archive staging tree and failing closed if any protected path remains. The live checkout/save is never touched; the manifest and onboarding text now state the exclusion. |

Verification: disposable package audit before the fix reproduced the tracked
`progress.json` leak. Post-fix package `QuestLab-2f5a4fe` contained no protected
save/notebook paths in either its folder or ZIP, while the manifest and key
onboarding/launcher files remained present. Clean archive frontend tests/build
passed **60/60** and **1,346 modules**. No user save, PTY or hosted state was
changed.

## Codex bookshelf and reading-room hierarchy — F-133

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-133 | P1 | Codex presentation | The bounded Codex still read as a dense stack of cards: the whole concept list could become a continuous scroll, the active page was hard to locate, and chapter/mob markers used mixed text glyphs. Search with no matches also fell back to the complete book list. | Fixed with a paged five-book shelf, explicit shelf controls, a calmer paper/spine hierarchy, SVG chapter/encounter markers, and strict search results that can genuinely be empty. The state projection, note gateway, reward source, battle tab and PTY lifecycle are unchanged. |

Verification: current-source Forge runtime tests pass **43/43**; clean Linux
archive frontend tests pass **62/62** and Vite transforms **1,346 modules**.
Browser K&M remains unavailable in this environment (F-080), so this slice is
not presented as a visual-device acceptance claim.

## Character/Homestead SVG icon parity — F-134

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-134 | P2 | RPG presentation | Character equipment, achievement badges and Homestead scene props still used font-dependent symbols while the HUD and Codex had moved to the shared monochrome SVG language. | Fixed by routing armor, trinket, character, achievement and Homestead props through `RouteIcon`, adding the missing spark/window paths, and applying explicit 24px-grid sizing/strokes. No state, reward, revision, learner-file or PTY behavior changed. |

Verification: current-source Forge runtime tests pass **44/44**; clean Linux
archive frontend tests pass **63/63** and Vite transforms **1,346 modules**.
Browser K&M remains unavailable in this environment (F-080), so visual-device
acceptance is still open.

## Codex fixed-page evidence reader — F-135

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-135 | P1 | Codex presentation | Even with the finite bookshelf, a growing encounter/notes collection could make the selected book body feel like another endless scroll and push the useful page controls away. | Fixed with a viewport-bounded book frame, a single deliberate scroll owner for the selected page body, and explicit three-record page controls for Encounter and Notes sections. The active record, definition/example page and canonical note gateway remain unchanged; no evidence is hidden from the state projection. |

Verification: current-source Forge runtime tests pass **45/45**; clean Linux
archive frontend tests pass **64/64** and Vite transforms **1,346 modules**.
Browser K&M remains unavailable in this environment (F-080), so visual-device
acceptance is still open.

## Route/quest/Dungeon SVG marker parity — F-136

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-136 | P2 | RPG presentation | Hub chapters, quest objectives, mob paths, boss phases and Dungeon map/room markers still depended on font glyphs, so icons could shift or disappear independently of the fixed HUD/Codex SVGs. | Fixed by routing those status markers and return controls through `RouteIcon` (`check`, `target`, `lock`, `plus`, `flame`, `shield`, `spark`) with explicit SVG sizing/strokes. Visible labels and state-owned statuses remain unchanged. |

Verification: current-source Forge runtime tests pass **46/46**; clean Linux
archive frontend tests pass **65/65** and Vite transforms **1,346 modules**.
Browser K&M remains unavailable in this environment (F-080), so visual-device
acceptance is still open.

## Codex compact active-quest rail — F-137

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-137 | P1 | Codex presentation | The active quest sidebar rendered every chapter as a stacked button list beside the bookshelf, consuming the finite rail and recreating the crowded/infinite-feed feel as chapters accumulated. | Fixed with a bounded native chapter selector, preserving unlocked/locked status and selected chapter state while leaving the current mob summary and finite bookshelf visible. The obsolete chapter-list CSS was removed so the legacy stack cannot return accidentally. |

Verification: current-source Forge runtime tests pass **47/47**. The clean
Linux archive passed **66/66** frontend tests and the Vite build transformed
**1,346 modules**. Browser K&M remains unavailable in this environment (F-080),
so visual-device acceptance is still open.

## Partial OneDrive frontend dependency cache — F-138

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-138 | P2 | Windows/WSL distribution | The live OneDrive `node_modules` tree had been left partially installed: Supabase package metadata and Vite shims were missing, and the Rollup optional package lacked its manifest. Windows frontend tests failed to import and `npm run build` could not start, even though clean Linux archives remained healthy. | Fixed in the local dependency cache without touching source, saves or running PTY processes. The launcher now performs a read-only manifest preflight for Vite, Supabase, Functions and native Rollup metadata, failing with an actionable environment-specific message instead of an opaque ESM/Rollup error. The supported WSL path still requires native dependencies in a clean Linux filesystem; do not run WSL installs against the live OneDrive tree. |

Verification: Windows frontend tests **66/66**, Windows Vite build **1,346
modules**, focused launcher tests **15/15**, and WSL backend suite **109/109**.
Browser K&M remains blocked by F-080; no protected save, learner file or PTY
was changed.

## Codex folio overflow follow-up — F-139

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-139 | P1 | Codex presentation | The bookshelf and encounter paging were present, but the selected book still owned a full-height vertical scrollbar. On a small Forge window that made the Codex read like an infinite feed and hid the page/section controls behind scroll. | Fixed with a final folio rule: the visible book section is a bounded, non-scrolling page; encounter/notes targets and mastery records are explicitly paged, and only a bounded workspace-note box may scroll when a learner note is genuinely long. No state, reward, sync, learner-file or PTY behavior changed. |

Verification: Windows frontend tests **67/67** and Vite build **1,346 modules**
passed. Browser K&M remains blocked by F-080, so this is not presented as a
visual-device acceptance claim.

## Hosted campaign migration preflight — F-140

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-140 | P1 | Hosted sync / Milestone C | The linked Supabase project is reachable, but its remote migration ledger is missing the committed device-ownership and campaign-projection migrations. A campaign save would therefore still be rejected by the older hosted validator. | Verified read-only: `supabase migration list --linked` shows local-only `20260916000100` and `20260917000100`; `supabase db push --linked --dry-run --skip-vault` proposes exactly those two files. No hosted write or seed was performed. Applying them remains an explicit approval gate before authenticated two-device acceptance. |

Evidence was captured against linked project `ajnxexxcqfbozszwpjpk` on the current
tip. Local state, learner files, PTYs and account data were not changed.

## Codex legacy feed height — F-141

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-141 | P1 | Codex presentation | The new folio controls still inherited the legacy `.codex-library { min-height: 520px; }` rule. On compact Forge windows that forced the book frame beyond the viewport and brought back the visual feel of an infinite scrolling document. | Fixed with a compact Codex hero and final viewport constraints: the tab page, library, index, book page and visible section now share a bounded flex budget, while the shelf/record/mastery pagers remain the only navigation for growing collections. No state, reward, sync, learner-file or PTY behavior changed. |

Verification: Windows frontend tests **68/68** and Vite build **1,346 modules**
passed. Browser K&M remains blocked by F-080, so this is not presented as a
visual-device acceptance claim.

## Hosted migration write guard — F-142

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-142 | P1 | Hosted sync / Milestone C | The exact hosted campaign migration plan was known, but the next operator step was still a raw Supabase command. That left room for an accidental write, an unexpected pending migration or a dry-run mismatch. | Fixed with `tools/questlab_supabase_migrate.py`: it verifies the linked ledger contains exactly the two committed campaign migrations, verifies a dry-run proposes both, and refuses any real push without `--apply --confirm APPLY_QUESTLAB_CAMPAIGN_MIGRATIONS`. The default command is read-only and never touches the player save. |

Verification: the guarded default run returned **MIGRATION GUARD: GREEN** against
linked project `ajnxexxcqfbozszwpjpk`; focused guard tests pass **5/5**. No hosted
migration or seed was applied. Authenticated two-device acceptance remains open.

## Codex shared height primitive retained a feed-sized minimum — F-143

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-143 | P1 | Codex presentation | The final folio constraints were bounded, but the shared `.codex-library` primitive still declared a legacy 620px minimum. A compatibility shell or a reordered stylesheet could therefore reintroduce a feed-sized Codex before the viewport rules ran. | Fixed at the primitive: `.codex-library` now starts with `min-height: 0`; the viewport-pinned Codex remains the sole height owner. Added a source regression assertion so the legacy 5xx/6xx minimum cannot return. No state, reward, sync, learner-file or PTY behavior changed. |

Verification: Windows frontend tests **69/69** and Vite build **1,346 modules**
passed. Browser K&M remains environment-blocked by F-080.

## Native Linux acceptance lacked a single pre-launch environment report — F-145

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-145 | P2 | CachyOS distribution | The native launcher and live K&M preflight existed, but a physical CachyOS run still needed separate manual commands to capture kernel, toolchain, checkout and native Rollup identity before launch. | Fixed locally with read-only `tools/questlab-native-report.py --strict`. It checks the expected branch/upstream, Python/Node/npm availability, executable launcher/state CLI, required frontend manifests and a native Linux Rollup package. It never installs, fetches, writes a report, calls Supabase or touches player state. Physical CachyOS K&M/PTY acceptance remains F-058. |

Verification: source contract coverage passed **17/17**; a strict clean-ext4
report returned **GREEN** with Linux kernel `6.18.33.1-microsoft-standard-WSL2`,
Python `3.14.4`, Node `v26.7.0`, npm `11.19.0` and
`rollup-linux-x64-gnu`. The temp clone was removed and verified absent. The
live OneDrive tree is intentionally not a native Linux target.

## Friend packager blocked by a protected nested checkout — F-144

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-144 | P2 | Distribution custody | The strict friend packager refused a checkout containing the user-owned untracked nested `/` directory, even though the bundle is built from committed `HEAD` and would never archive that directory. Removing or staging the protected directory was not acceptable. | Fixed with an explicit `-IgnoreUntrackedPath` option. Each ignored path must exist inside the repository, be untracked, and be named exactly; no blanket dirty-source bypass exists. The archive still comes only from `HEAD`, then strips player-owned save/notebook paths. |

Verification: launcher-contract coverage passes **16/16**. The packager was
run with the exact protected directory and created a 134-entry ZIP from
`83f302c`; `progress.json`, `tutor.py`, `dungeon.py`, `notes/` and `/` were
absent from the archive.

## Codex reader still looked like an infinite dashboard — F-146

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-146 | P1 | Codex presentation | The earlier folio patches removed the large minimum heights, but the Codex still inherited dense dashboard styling and several competing overflow rules. That made the actual fixed shelf/book controls feel like an infinite scroll surface. | Fixed with a final reader contract in `foundation.css`: a compact Codex hero, short Books/Battle Shell tabs, a two-pane fixed-height folio, bounded active-quest rail and explicit shelf/record/mastery paging. The Codex root and Books page cannot grow with evidence; only small mobile/index, code-example and long-note bodies may scroll. |

Verification: Windows frontend tests **70/70** and Vite build **1,346 modules**
passed. No player state, learner file, PTY or hosted migration changed. Browser
K&M remains blocked by F-080.

## Codex reader chrome still looked assembled from dashboard cards — F-147

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-147 | P2 | Codex presentation | The bounded folio removed the unbounded feed, but the visual hierarchy still mixed metric cards, generic panel surfaces and dashboard-like controls. The Codex did not yet feel like a readable field guide. | Fixed with a CSS-only reader pass: compact metric strip, quiet paper/ink surface, clearer shelf spine, calmer active-page treatment and highlighted example blocks. Paging and state-service boundaries are unchanged. |

Verification: Windows frontend tests **71/71**, Vite build **1,346 modules**,
and supported WSL backend tests **116/116**. Browser K&M remains blocked by
F-080; no player state, learner file, PTY or hosted migration changed.

## Legacy Codex primitive retained a feed-sized minimum — F-148

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-148 | P1 | Codex presentation | The base `styles.css` fallback still declared `min-height: 520px` for `.codex-library`. A compatibility shell or stylesheet-order change could therefore resurrect the old infinite-feed feel even though the reader layer was bounded. | Fixed by changing the shared base primitive to `min-height: 0` and guarding the exact legacy declaration in the frontend source suite. |

Verification: Windows frontend tests **71/71** and `git diff --check` pass. No
state, learner file, PTY or hosted migration changed; browser K&M remains
blocked by F-080.

## Legacy Codex list fallbacks still owned scroll — F-149

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-149 | P1 | Codex presentation | The base Codex stylesheet still assigned `max-height` and `overflow:auto` to the already-paged bookshelf and encounter picker. Those fallback scroll owners could recreate the infinite-feed feel in a compatibility shell. | Fixed by setting both base primitives to `max-height: none; overflow: visible`; React shelf/record paging remains authoritative, while only intentional code-example and long-note bodies scroll. |

Verification: Windows frontend source tests are **72/72**, Vite transforms
**1,346 modules**, and the supported WSL backend suite is **116/116**; no
state, learner file, PTY or hosted migration changed. Browser K&M remains
blocked by F-080.

## Mobile Codex fallback still capped the bookshelf — F-150

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-150 | P1 | Codex presentation | The legacy mobile media query still capped the paged bookshelf at 180px, leaving a compatibility-order path to a second narrow-window scrollbar. | Fixed by setting the mobile fallback to `max-height: none; overflow: visible` and guarding the stale cap in the frontend source suite. |

Verification: Windows frontend source tests are **72/72**, Vite transforms
**1,346 modules**, and `git diff --check` passes; no state, learner file, PTY
or hosted migration changed. Browser K&M remains blocked by F-080.

## Hub exposed locked future identities — F-151

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-151 | P1 | Hub / Journal presentation | Hub, legacy quest context and the compatibility journal rendered names/concepts for locked chapters or encounters, leaking future campaign identity instead of preserving the silhouette/unknown contract. | Fixed by hiding locked names behind `Unknown chapter`/`Unknown encounter`, using generic hidden-until-clear labels, and adding a dashed locked-silhouette treatment. |

Verification: Windows frontend source tests are **73/73**, Vite transforms
**1,346 modules**, and the WSL backend suite is **116/116**; no state,
learner file, PTY or hosted migration changed. Browser K&M remains blocked by
F-080.

## Splash idle timer refreshed while the app was unattended — F-152

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-152 | P2 | Launch continuity | A 60-second launch-context heartbeat kept refreshing `lastSeenAt`, so an unattended Forge session could never trigger the requested returning splash after 20 minutes away. | Fixed by recording activity only from real pointer/keyboard use plus mount/dismissal; the heartbeat is gone. |

Verification: Windows frontend source tests are **74/74**, Vite transforms
**1,346 modules**, and the WSL backend suite is **116/116**; no state,
learner file, PTY or hosted migration changed. Browser K&M remains blocked by
F-080.

## Codex was still trapped in the narrow editor column — F-153

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-153 | P1 | Codex presentation | The folio's internal height contract was bounded, but Codex still occupied the editor-column grid beside the activity/context rails. That left the reading surface cramped and made the finite UI feel like the reported infinite-scroll dashboard. | Fixed by treating Codex as a full-width surface route alongside Hub, Character and Homestead. The active-quest rail remains inside the Codex, wide navigation remains available, and a direct flex rule gives the folio the viewport left after navigation. |

Verification: Windows frontend source tests **74/74**, Vite transforms **1,346
modules**, and `git diff --check` pass. Browser K&M remains blocked by F-080;
no state, learner file, PTY or hosted migration changed.

## Codex still had a competing scroll cascade and no route escape — F-154

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-154 | P1 | Codex presentation/navigation | The previous Codex fixes were mathematically bounded, but the stylesheet still contained several competing height and overflow passes. A cascade/viewport combination could make the selected book feel like an infinite feed, and Codex was the one wide surface that did not render the shared route-navigation row. | Fixed with a final viewport contract: the Codex root is pinned and clipped, the desktop shelf/index are paged and non-scrolling, the selected book owns one bounded reading surface, Battle Shell scrolls only inside its own panel, and Codex now renders the compact shared SVG route navigation. |

Verification: Windows frontend tests **75/75**, Vite production build **1,346
modules**, supported WSL backend tests **116/116**, and live source checks on
ports `5181` and `5190` confirm the F-154 CSS is served by HMR. No player
state, learner file, PTY or hosted migration changed. Browser K&M remains
blocked by F-080.

## Codex typography still read like a dashboard — F-155

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-155 | P2 | Codex presentation | The bounded Codex reader no longer grew as an outer feed, but its headings and prose still inherited the dense monospace dashboard treatment. The result was technically finite yet visually tiring for the requested book/field-guide experience. | Fixed with a presentation-only typography layer: readable book-face headings and prose, monospace evidence/code, calmer rectangular section controls and smooth movement inside the existing single reading surface. No new scroll owner or state projection was introduced. |

Verification: Windows frontend tests **76/76**, Vite production build **1,346
modules**, and live HMR source checks on ports `5181` and `5190` confirm the
F-155 CSS is served. No player state, learner file, PTY or hosted migration
changed. Browser K&M remains blocked by F-080.

## Portrait transport state was invisible in Account settings — F-156

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-156 | P2 | Avatar / sync UX | The signed-in Account panel showed campaign revision and cloud cursor, but not the validated portrait transport state. When a portrait was cached, unavailable, uploading or removed, the learner had no local explanation for what the Character rail could display. | Fixed by rendering the SyncEngine avatar projection beside the account diagnostics. The panel reports only the state/source returned by the gateway (`PRIVATE CLOUD`, `CACHED CLOUD`, `LOCAL`, or the bounded transport status); it does not claim a remote portrait when none is available. |

Verification: Windows frontend tests **77/77**, Vite production build **1,346
modules**, and live HMR source checks on ports `5181` and `5190` confirm the
F-156 Account UI is served. No player state, learner file, PTY or hosted
migration changed. Browser K&M remains blocked by F-080.

## Codex still felt like an infinite-scroll dashboard — F-157

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-157 | P1 | Codex presentation | Live use still exposed the selected book as a long scrolling document despite the outer viewport being clipped. The separate mode-tab row also made the folio feel like stacked dashboard panels instead of a page-turning library. | Fixed with a final compact folio pass: Books/Battle Shell tabs share the header row, the desktop reader frame has no page-length scroll owner, shelf and encounter lists remain React-paged, and only bounded narrow-device/code/note fallbacks can scroll. |

Verification: Windows frontend tests **78/78**, Vite production build
**1,346 modules**, and live HMR checks on ports `5181` and `5190` serve the
F-157 cascade. Browser K&M remains blocked by F-080, so this is not a fresh
device-level visual claim. No player state, learner file, PTY or hosted
migration changed.

## More-specific Codex overflow rule still won — F-158

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-158 | P1 | Codex presentation | The F-157 desktop intent was correct, but an earlier higher-specificity viewport rule still won in the final cascade and restored `overflow-y: auto` on the selected book. That left a visible document scrollbar and preserved the exact infinite-scroll feel the reader was meant to remove. | Fixed with a final selector matching the viewport rule: desktop book sections are flex-bounded and clipped, the read grid is height-budgeted, and only the narrow one-column fallback may scroll. |

Verification: Windows frontend tests **79/79**, Vite production build
**1,346 modules**, and live source checks on `5181` and `5195` confirm the
F-158 selector is served. The backend was restored on the configured `7341`
port for the active Vite session; `/api/runtime` and `/api/campaign` now return
200 with canonical revision `18` (level 3, 120 XP, 75 coins, Blackjack 38%,
The Hitman 8/8). Browser K&M remains blocked by F-080, so no fresh visual
device claim is made. No player state, learner file or PTY was changed.

## Manual Vite launches hid stale checkout identity — F-159

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-159 | P1 | Launcher / stale UI diagnostics | The managed launcher embedded the checkout SHA, but a developer who started Vite directly with `npm run dev` received an unmarked frontend. That path could not warn when the browser was serving a different checkout, recreating the reported “old UI” symptom. | Fixed by making Vite derive the current repository HEAD when `QUESTLAB_BUILD_SHA` is absent, with a bounded `git` call and an empty fallback when Git is unavailable. The explicit launcher marker still wins. |

Verification: Windows frontend tests **80/80** and the Vite production build
**1,346 modules** pass. The fallback is diagnostic-only; it does not restart
PTYs, change state custody or infer a second save. Browser K&M remains blocked
by F-080.

## Current-SHA native Linux distribution recheck — F-160

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-160 | P2 | Native Linux distribution | The previous ext4/native-Linux evidence predates the final Codex/runtime-identity commits, so it did not prove the current published branch was installable with native Rollup. | Rechecked in a disposable ext4 clone at `0e9b307c6a8e5882e70cf9a8dbe39a2cde1a0f12`: branch/upstream match, zero dirty paths, native Rollup present, backend **116/116**, frontend **80/80**, and Vite build **1,346 modules**. Physical CachyOS install/K&M/PTY acceptance remains open under F-058. |

The live OneDrive WSL tree continues to fail the native report by design because
its shared Windows `node_modules` lacks the Linux Rollup package; no dependency
install was attempted there.

## Codex was mounted as a page inside the Forge grid — F-161

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-161 | P1 | Codex presentation | Codex was the only wide RPG surface mounted directly in the generic Forge grid. Its internal route navigation then relied on an absolute-positioned overflow cascade, making the reader feel like an infinite page inside a page and duplicating the navigation treatment. | Fixed in `4c8a279`: Codex now mounts in the shared bounded wide-surface frame, the frame owns navigation, and the book/battle regions receive an explicit finite viewport budget. The React shelf and record pagers remain the content navigation authority; only the narrow fallback and deliberately long code/note bodies scroll. |

Verification: frontend tests **81/81** and Vite production build **1,346
modules** pass. Browser K&M remains blocked by F-080, so no fresh visual device
claim is made from this environment.

## Legacy Journal Battle Shell dropped state-owned objective progress — F-162

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-162 | P1 | Quest Journal / Battle Shell | The Codex Battle Shell received the canonical `completedObjectives` projection, but the legacy Quest Journal Battle Shell did not. Its Resolve/objective panel could therefore show an empty or stale objective count while the state service and Codex were current. | Fixed in `19b6da5`: both Battle Shell entry points pass the validated completed-objective projection into the shared `QuestBattleScreen`; a source regression test asserts the two bindings and state-owned count calculation. |

Verification: frontend tests **82/82**, Vite production build **1,346
modules**, and `git diff --check` pass. No player state, legacy save, or PTY was
changed. Browser K&M remains blocked by F-080.

## Current published SHA native Linux recheck — F-163

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-163 | P2 | Native Linux distribution | The ext4 distribution evidence needed to be refreshed after the published merge at `1782e97`, rather than relying on an older source tip. | Rechecked in a disposable ext4 clone of `feature/cloud-sync-desktop` at `1782e97`: native Rollup `rollup-linux-x64-gnu`, backend **116/116**, frontend **82/82**, and Vite **1,346 modules** all pass. The report's one dirty path is only the disposable `.venv` symlink used to reuse the test runtime; tracked source is clean. This is WSL/ext4 evidence, not physical CachyOS or browser K&M certification. |

## Hosted campaign migration is ready for approval — F-164

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-164 | P1 | Hosted campaign sync | The hosted validator still needs the committed device-ownership and campaign-projection migrations before a signed-in campaign projection can be accepted. | Read-only guard rechecked successfully: the linked ledger has exactly the two expected pending migrations and the dry-run proposes both. No hosted write, seed, player-state mutation or auth bypass was performed. Applying remains an explicit approval gate before authenticated two-device acceptance. |

## Native virtualenv symlink looked like dirty source — F-165

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-165 | P3 | Native distribution / packaging | The repository ignored `.venv/` directories but not a `.venv` symlink. A disposable native report that reused an existing venv therefore reported one dirty path even though no source file changed. | Fixed by using exact-name `.venv` and `venv` ignore patterns, which cover directories and symlinks. `git check-ignore` and frontend **82/82** pass; protected saves and package boundaries are unchanged. |

## Healthy canonical-root runtime was shown as stale — F-166

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-166 | P1 | Runtime identity / boot UX | The canonical-root Forge intentionally has one local authority, so `/api/runtime` returns `legacy_path: null` and `legacy_authoritative: false`. React nevertheless required a truthy legacy path and could label a healthy launch `RUNTIME STALE · use current launcher`. Separately, the shared WSL OneDrive checkout could not boot while its Windows `node_modules` lacked native Linux Rollup. | Fixed the runtime contract to require explicit authority flags and accept `legacy_path: null` as the valid one-authority shape while rejecting omitted/malformed values. Repaired the ignored dependency tree with WSL `npm ci --include=optional`; the guarded launcher now reaches Vite/backend startup. |

Verification: WSL launcher smoke served `/` **200**, `/api/runtime` **200** and
`/api/campaign` **200** on backend `7331`; runtime reported branch
`feature/cloud-sync-desktop`, HEAD `d6a0c370`, canonical authority true and
legacy authority false. Frontend tests **82/82** pass. No save, learner file,
PTY or hosted state changed. Browser K&M remains blocked by F-080.

## Forge rendered a black screen on initial terminal state — F-167

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-167 | P0 | Boot / React runtime | `TerminalPane` rendered its reconnect control with `onClick={connect}`, but no `connect` binding existed. The initial `connecting` state evaluated that JSX and crashed React before the Forge could paint, even though Vite and the API were healthy. The legacy Quest Journal also passed an undefined `completedObjectives` binding into its Battle Shell. | Fixed with one `reconnectTerminal` session handler shared by the imperative ref and reconnect button, plus a state-owned completed-objectives binding in `QuestJournal`. Added source regression tests for both crash paths. |

Verification: the launcher was restarted cleanly so Vite served the patched source;
the live Forge now renders the Forge shell, campaign HUD, Mob 3 `The Hitman`,
enemy Resolve `8/8`, editor and both connected PTYs in the CUA browser without
a refresh after the initial reload. Frontend tests **84/84** pass. No player
state, learner file, legacy save, hosted state or protected PTY was changed.

## Forge-first RPG surface cleanup — F-168 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-168 | P1 | Forge / campaign projection / RPG surfaces | The campaign answer flow still had a competing Battle Shell answer surface, Codex journaling/feed UI, and thin Character/Settings routes. The encounter projection also lacked a bounded current-mob brief, human-readable objective metadata, and an explicit reward envelope for the UI to render. | Fixed. Forge is now the only campaign answer surface and submits the active `.py` file with revision/nonce/digest context. The state-owned projection exposes only the current mob, objective, question type, Impact, Resolve, lore/brief, and authorized current reward envelope; future prompts/answers/loot remain hidden. Codex is finite folio/book/notes navigation, Character is a progress cockpit, Settings has no duplicate Homestead Loadout, and Tutor presents the structured contract while retaining raw CLI as an advanced path. |

Verification: backend **117/117**, frontend **86/86**, Vite production build (**1,346 modules**) and `git diff --check` pass. Browser K&M on disposable current-source port `5198` verified exact navigation order, Forge lore/objective/reward/Resolve, no Battle Shell or answer textarea, Codex folios/Notes, Character cockpit, Settings cleanup, Tutor contract, Dungeon map/editor, visible SVG HUD icons, and live state polling without a refresh. No real save, legacy evidence, hosted state, or launcher PTY was changed.

## Forge source binding used the wrong context key — F-169 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-169 | P1 | Forge submission / state-service boundary | A valid Forge-file submission could be rejected with `409` because the verdict challenge read `context.active_path`, while the context bridge stores the active file under `context.active_file.path`; the first implementation also left the file digest implicit. | Fixed by deriving the challenge path and SHA-256 file digest from the state-owned `active_file`. The validator now accepts only that normalized active `.py` path, rechecks the current on-disk digest, rejects `tutor.py`/`dungeon.py`, and requires submitted contents to match the captured digest. Added regression coverage for stale paths, stale digests, changed disks, and the accepted binding. |

## Existing launcher still serves its pre-slice bundle — F-170 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-170 | P1 | Runtime distribution / operator handoff | The already-running user launcher on `5173` retains its pre-slice Vite module graph and still shows the old Battle Shell until that managed launcher is restarted. Restarting it during acceptance would have torn down the shared launcher process group and violated the no-PTY-reset boundary. | Open operator action: restart the managed current launcher when a PTY-preserving maintenance window is available. The current source/build is verified independently on disposable `5198`, and the stale surface is explicitly labelled `FRONTEND STALE · restart current launcher`; no source or canonical state regression was found. |

## Forge surface polish follow-up — F-171–F-173 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-171 | P2 | Navigation / HUD | Wide-route navigation still duplicated Quest Hub as a text destination, the centered topbar treatment was not guaranteed, and the compact HUD exposed an opaque `DEV` label instead of explaining the stat values. | Fixed by making the Forge logo the sole Hub control, filtering Hub from destination links, centering the wide route row with a rail/topbar entrance animation, and adding hover/focus/native-title descriptions for HP, gold, streak, shields, bosses and activity. |
| F-172 | P1 | Codex layout | A legacy flex/grid cascade could shrink the selected concept heading so its definition/summary sat underneath the book pager, especially in a short viewport. | Fixed with explicit Codex folio rows (heading, pager, section tabs, bounded body), visible multi-line definitions, and a short-height fallback that gives the selected book its own scroll owner. |
| F-173 | P1 | Workspace tree / Codex readability | The tree opened every directory by default and a literal `\\` transfer directory mirrored a host filesystem root into the file list. The new definition/examples/mistakes markup also lacked a clear visual card hierarchy. | Fixed by filtering malformed root paths in React and the state server, skipping symlink traversal and cache noise, starting folders collapsed with per-folder/all-folder disclosure controls, and styling the three folios as definition, example and validated-signal cards. |

Verification: frontend **87/87**, backend **117/117**, WSL Vite production build **1,346 modules**, and `git diff --check` pass. Browser K&M checks on disposable current-source `5198` showed a fully readable Codex heading, working folder expand/collapse, no mirrored `\\` root, centered icon-only Hub navigation, and SVG HUD icons with stat titles. The managed launcher and both PTYs were not restarted; no canonical save, legacy evidence or hosted state was changed.

## GitHub Copilot CLI provider — F-174 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-174 | P2 | AI provider bridge | Copilot CLI was installed in WSL but was not exposed in Forge runtime detection, the AI panel, command palette, or provider tracking, so it could not be used for bounded campaign/tutor adjudication. | Fixed. Runtime now reports `commands.copilot`, the panel and legacy surface can launch `copilot`, command palette/tracking include it, and provider prompts name it. Copilot remains an advisory raw CLI; rewards, verdicts and progression still require the canonical state-service gateway. |

Verification: `copilot --version` resolved to GitHub Copilot CLI **1.0.83** in WSL; frontend **88/88**, backend **117/117**, WSL Vite build **1,346 modules**, and `git diff --check` pass. No state mutation, Supabase change, launcher restart or PTY reset was performed.

## Boss gate and single-file Forge follow-up — F-175 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-175 | P1 | Forge boss gate / workspace tree | The boss gate did not present the state-owned lore, Resolve bar, current damage goal and bounded reward envelope cleanly, while a requirement picker duplicated the Forge submission surface. Single-file campaign steps also exposed an unnecessary full workspace tree. | Fixed. The canonical encounter projection now supplies lore/brief, Resolve/max Resolve, the current sequential goal with state-owned damage, and the current reward envelope. Forge shows the current goal immediately below Resolve with `Send current goal to PYR`; the picker and duplicate boss-file submission are gone. The tree is hidden for single-file projects and remains collapsible/opt-in for multifile projects. |

Verification: CUA browser smoke on disposable source port `5198` showed the boss lore, 12/12 Resolve, current `Required behaviour` goal with 4 Resolve damage, reward envelope, no requirement select, and the single-file `blackjack.py` summary. Frontend **90/90**, backend **117/117**, WSL Vite production build **1,346 modules**, and `git diff --check` pass. No state mutation, launcher restart, or managed shell/AI PTY reset was performed.

## App-level navigation and Boss Gate fit — F-176 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-176 | P1 | Forge layout / route navigation | Forge, Tutor, Dungeon and Settings still depended on the narrow vertical ActivityRail while the logo-led route menu existed only inside wide screens. The Boss Gate was capped at 48% height with its own scrollbar; removing that cap without resizing the surface clipped the submit action and reward envelope below the viewport. | Fixed by promoting the existing SVG route menu to one app-level top navigation row, keeping the logo as the sole Quest Hub control, removing the duplicated vertical rail and nested wide-route menu, widening the active boss context track, and using a compact full-height Boss Gate layout with no internal scroll. The current lore, Resolve, state-owned goal/action and bounded reward remain visible together. |

Verification: CUA keyboard/mouse only (no Playwright) on disposable current-source `5198` at the 1280×720 viewport. Forge showed the complete Boss Gate including `12/12` Resolve, current `Required behaviour` with `4 Resolve damage`, `Send current goal to PYR`, and `+100 XP · +0 Coins` without a panel scrollbar. Tutor, Infinite Dungeon, Codex, Settings and Quest Hub were each opened through the same centered top menu; Hub remained the logo-only control. Frontend **90/90** and WSL Vite production build are the remaining final checks for this slice; managed launcher, canonical save, shell/AI PTYs and hosted state were not changed.

## Encounter card / resize correction — F-177 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-177 | P1 | Forge encounter UX / layout | The previous Boss Gate still treated the side panel like a submission form: `Send current goal to PYR` duplicated the Forge `Submit run` surface, the card did not explain how clean runs/bugs affect damage, and the Boss Gate width override made the left resizer appear broken. | Fixed. The panel is now an encounter card: lore and Resolve first, a state-owned `CURRENT QUEST`, a compact `BOSS / MOB MECHANICS` projection, and bounded `LOOT AT STAKE`. The redundant boss action is gone; the current Forge file remains the answer surface. Mechanics are projected by the gateway (failed runs do not apply Resolve, provider verdicts remain authoritative, verified goals apply canonical Impact). The left panel is user-resizable from 260–430px with a visible separator affordance and no Boss Gate width override. |

Verification: frontend **90/90**, backend **54/54** targeted state/context tests, WSL Vite production build **1,346 modules**, and CUA keyboard/mouse visual checks on disposable `5198` at 1280×720. Dragging the separator widened the panel from ~320px to ~400px; the full lore, Resolve, current quest, mechanics and loot card remained readable. Managed launcher, canonical save and hosted state were not changed.

## Boss Gate vertical hierarchy — F-178 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-178 | P2 | Forge encounter presentation | The full-height Boss Gate technically fit, but its content stayed compressed at the top, leaving unused space and making the mechanics read like a tiny status strip rather than a playable encounter brief. | Fixed. The Boss Gate now uses the available vertical track: lore gets readable multi-line room, the current quest has a stronger card hierarchy, mechanics become three readable state-owned rows, and the loot envelope anchors the bottom. A short-height media rule keeps the same information compact on smaller desktop windows. |

Verification: CUA keyboard/mouse visual check on disposable current-source `5198` at 1280×960 showed the Boss Gate filling the encounter track with lore, Resolve, current quest, three readable mechanics cards, and loot visible together. Frontend **90/90**, WSL Vite build **1,346 modules**, and `git diff --check` passed. No player state, launcher, hosted state, or managed PTY changed.

## Forge encounter surface simplification — F-179 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-179 | P1 | Forge answer flow / encounter sidebar | The Boss Gate had become a text barrier: its quest, mechanics, reward copy and a second provider action competed with the actual Forge editor and `Submit run` control. This made the campaign answer path unclear and duplicated state-owned information. | Fixed. Forge now keeps only the Resolve projection and a small pixel PYR companion in the sidebar. The state-owned current quest, lore/brief, mechanics and bounded reward envelope are available through a selectable virtual `quest.md` read-only document tab. The single Forge toolbar `Submit run` routes to the canonical campaign submission (mob objective or boss goal), preserving nonce, revision, active-file digest and state-service verdict authority. |

Verification: frontend **90/90**, backend **117/117**, WSL Vite production build (**1,346 modules**), and `git diff --check` pass. CUA keyboard/mouse visual verification on disposable current-source `5198` showed the `quest.md` projection rendered read-only with current lore/goal/mechanics/loot, the active `.py` returned to the single answer surface, and the Boss Gate sidebar reduced to Resolve plus the pixel PYR companion. The managed launcher, canonical save, hosted state and both PTY sessions remain untouched.

## Forge sidebar compact mode — F-180 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-180 | P2 | Forge layout / file navigation | The Forge context panel consumed the full left column even when the learner only needed to switch between the active campaign `.py` and the state-owned `quest.md`. The encounter Resolve/PYR block also felt undersized in the remaining full-view space. | Fixed. Forge now has a persistent compact mode with `.py` and `.md` icon shortcuts plus an expand control. Compact mode removes the Resolve/Boss Gate and PYR content while keeping the editor grid stable; full mode remains drawable/resizable and gives PYR a larger centered presentation below Resolve. |

Verification: frontend **91/91**, WSL Vite production build (**1,346 modules**), and `git diff --check` pass. CUA keyboard/mouse on disposable `5198` verified compact `.py`/`.md` switching, read-only `quest.md`, the expand action, and the restored full Resolve/PYR view. Managed launcher, canonical save, hosted state and both PTYs were untouched.

## PYR companion motion pass — F-181 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-181 | P2 | Forge companion / encounter hierarchy | PYR was a static pixel badge and sat too high in the full Boss Gate track, so the companion did not feel alive and the large lower portion of the encounter panel felt unused. | Fixed. PYR now has a restrained idle float and occasional blink using compositor-friendly transforms, with `prefers-reduced-motion` and the app's `no-animations` setting disabling motion. The full Boss Gate flex track anchors PYR lower with breathing room; compact Forge intentionally omits the companion. |

Verification: frontend **92/92**, WSL Vite production build (**1,346 modules**), and `git diff --check` pass. CUA keyboard/mouse visual check on disposable current-source `5198` showed the full Boss Gate with Resolve and PYR placed near the lower edge, while compact mode showed only the `.py`/`.md` rail and expand control. Managed launcher, canonical save, hosted state and both PTYs were untouched.

## Boot fade and learning-surface collapse — F-182 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-182 | P2 | Boot / Tutor / Infinite Dungeon layout | The boot shell appeared without an explicit entrance transition, and Tutor/Dungeon had no way to reclaim the left context column while writing in their editors. | Fixed. The app shell now fades in over 360ms with reduced-motion and the existing animation preference disabling it. Tutor and Infinite Dungeon now expose the same slim/restore sidebar control as Forge; compact mode keeps the active `tutor.py` or `dungeon.py` identity visible while giving the editor the reclaimed width. |

Verification: frontend **94/94**, WSL Vite production build (**1,346 modules**), and CUA keyboard/mouse visual checks on disposable current-source `5198` showed Tutor and Dungeon compact rails plus their restore buttons with the editor surface widened. No campaign mutation, managed launcher restart, or PTY reset was performed.

## Slim-rail restore affordance — F-183 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-183 | P2 | Forge / Tutor / Dungeon compact rail | The restore control was anchored at the bottom of the slim rail, making an accidental collapse unnecessarily hard to reverse. | Fixed. The restore button keeps its compact dimensions and now sits above the active file/mode shortcut(s) with the same 8px separation across all three editor surfaces. |

Verification: frontend **94/94**, WSL Vite production build (**1,346 modules**), and `git diff --check` pass. A fresh CUA keyboard/mouse visual check on disposable current-source `5198` showed the Dungeon compact rail with the same-sized restore button above the `RUN` shortcut instead of at the bottom. The shared rail styling applies to Forge and Tutor as well; managed launcher, canonical save, hosted state and both PTY sessions were untouched.

## Route shortcut cleanup and Tutor icon visibility — F-184 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-184 | P2 | Forge / Tutor / Infinite Dungeon navigation | Infinite Dungeon duplicated the global Forge navigation with a route-local Forge button, while Tutor's route-local Forge icon had no nested SVG sizing/style and could render invisible. Forge also lacked a fast route-local Tutor action. | Fixed. Dungeon now keeps only its sidebar-collapse control; Tutor keeps its Forge shortcut; Forge exposes an `Open Tutor Notebook` icon action. Shared panel-title action rules now size and color nested route SVGs consistently. |

Verification: frontend **94/94**, WSL Vite production build (**1,346 modules**), and `git diff --check` pass. CUA keyboard/mouse visual inspection on disposable current-source `5198` showed the Tutor Forge icon visibly in its title row, Forge's Tutor shortcut visibly in the active-file row, and no Forge shortcut in the Dungeon title row. No campaign mutation, managed launcher restart, or PTY reset occurred.

## HUD alignment, Homestead recovery and Settings isolation — F-185/F-186 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-185 | P2 | Top HUD | The level/title/XP strip was positioned by a space-between flex row, so the central campaign status drifted as the brand and right stat pills changed width. | Fixed with a three-track topbar grid that keeps the level/XP group on the viewport centre line while preserving responsive compact breakpoints. |
| F-186 | P1 | Homestead / Settings routing | Homestead rendered a black screen because `GameScreen` passed `equipCampaignItem` without destructuring it. Settings also inherited the persistent Forge collapsed-sidebar state, leaving only a slim rail after a Forge collapse. | Fixed by wiring the callback into `GameScreen` and treating Settings as a wide surface/route so it always renders its full account, editor and accessibility controls independently of Forge rail state. |

Verification: frontend **95/95**, WSL Vite production build **1,346 modules**, and `git diff --check` pass. CUA keyboard/mouse checks on disposable current-source `5198` showed Homestead content and no runtime crash, the Forge level/XP group visually centered, and Settings still full-width after collapsing Forge. Managed launcher, canonical state, hosted state and both PTYs were not changed.

## Infinite Dungeon design-lab AI loop — F-187 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-187 | P2 | Infinite Dungeon prototype / challenge feedback | The isolated dungeon needed PYR to speak only at room entry or after a code submission, without a second terminal. Submission errors also needed to deal run damage while preserving a learner-led retry loop instead of revealing an answer. | Fixed in the local design lab. PYR now renders as a dismissible event card only on those two triggers; bad attempts deal 18 run HP, keep the IDE open while HP remains, and return a text-only diagnostic hint. The run ends at 0 HP; no code snippet or answer is inserted. |

Verification: source syntax check and `git diff --check` pass. Browser verification is being completed against the restarted local prototype at `http://127.0.0.1:5201/`; no canonical state, Supabase transport, launcher, or PTY was changed.

## Branching dungeon route and floor boss — F-188 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-188 | P2 | Infinite Dungeon design lab / map route | The first map exposed unrelated rooms as if they were all selectable, so it did not yet create the intended route-plotting game loop or a meaningful floor conclusion. | Fixed in the isolated prototype. The map is now a six-row branching graph with highlighted edges, only connected child rooms enabled, visited path context, and one converged Floor Boss destination. A clean boss submission increments the floor, grants prototype-only boss rewards, and starts the next route at a fresh campsite. |

Verification: CUA keyboard/mouse visual testing on `http://127.0.0.1:5201/?v=4` traversed a branch, showed locked non-connected nodes, reached the converged Count Keeper boss, and visibly advanced Floor 3 to Floor 4 after submission. No campaign state, Supabase transport, launcher, or PTY was touched.

## Dungeon class selection and starter gimmicks — F-189 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-189 | P2 | Infinite Dungeon design lab / run setup | A new run opened directly on the map, so there was no meaningful starter identity or bounded class choice before route planning. | Fixed in the prototype. Runs now open on a class setup surface with three starter choices: Syntax Warden (absorbs the first error hit each floor), Resolve Duelist (+2 Resolve damage on clean submissions), and Route Merchant (+20 coins and one ration). The selected weapon/passive is visible in Character after entering the map. |

Verification: CUA keyboard/mouse testing on `http://127.0.0.1:5201/?v=5` selected Route Merchant and confirmed the altered purse/loadout, then selected Syntax Warden and confirmed its first short submission left HP unchanged while showing a text-only hint. No live campaign state was touched.

## Class setup presentation pass — F-190 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-190 | P2 | Infinite Dungeon design lab / run setup | The class gate still carried setup-rule copy, oversized empty grid rows, and a bottom-weighted enter action. The intended choice moment was visually diluted before the route began. | Fixed in the isolated prototype. Removed the starter-rule block and explanatory paragraph, lifted and enlarged the class cards, added a centered `READY TO DESCEND` CTA that appears only after a class is selected, and added a short phase-in when the dungeon route opens. |

Verification: CUA keyboard/mouse visual testing on `http://127.0.0.1:5201/?v=9` confirmed the exact “So how you wanna play it.” heading, no starter-rule block, compact upper composition, centered selected-class CTA, and a visible class-to-map phase transition. No campaign state, Supabase transport, launcher, or PTY was touched.

## Centered class grouping — F-191 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-191 | P3 | Infinite Dungeon design lab / run setup | The class choices sat too close to the top of the page, so the selection moment did not feel centered. | Fixed in the isolated prototype by centering the full-width class composition in the available page area while restoring the original card widths and preserving the single-column mobile layout. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=12` confirms the full-width class cards and selected CTA sit in the center of the page.

## Minimal dungeon-entry CTA and transition — F-192 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-192 | P3 | Infinite Dungeon design lab / run setup | The selected-state CTA carried an extra readiness label and a bright filled treatment that competed with the class cards. | Fixed in the isolated prototype. The CTA now contains only `Enter the dungeon`, uses a black surface with gold text, and keeps the short phase-in into the dungeon screen. |

Verification: CUA keyboard/mouse check on `http://127.0.0.1:5201/?v=13` confirmed the simplified black/gold CTA and click-through into the dungeon route. No campaign state, Supabase transport, launcher, or PTY was touched.

## Class prompt hierarchy — F-193 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-193 | P3 | Infinite Dungeon design lab / run setup | The class cards had no small instruction line, leaving the relationship between the heading and the choices implicit. | Fixed in the isolated prototype with a compact `PICK A CLASS` line directly below the heading and a deliberate gap before the cards. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=15` confirmed the heading, prompt, cards, and simplified CTA hierarchy.

## Class prompt spacing refinement — F-194 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-194 | P3 | Infinite Dungeon design lab / run setup | `PICK A CLASS` sat too close to the card picker after the initial prompt pass. | Fixed by lifting the prompt slightly toward the heading and adding more space before the cards. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=16` confirms the refined heading/prompt/card rhythm.

## Longer dungeon-entry fade — F-195 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-195 | P3 | Infinite Dungeon design lab / run transition | The class-to-dungeon transition was too brief to feel intentional. | Extended the route-entry phase from 0.66s to 0.95s and kept the state cleanup aligned at 1s. |

Verification: CUA keyboard/mouse check on `http://127.0.0.1:5201/?v=17` captured the dungeon in its mid-fade state and confirmed it settles into the route afterward.

## Long-form dungeon-entry fade — F-196 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-196 | P3 | Infinite Dungeon design lab / run transition | The 0.95s fade was still shorter than the intended descent beat. | Extended the class-to-dungeon fade to 2.5s and aligned cleanup at 2.6s. |

Verification: CUA visual testing on `http://127.0.0.1:5201/?v=19` captured the pronounced mid-fade and a settled dungeon screen after the transition.

## Route map background de-clutter pass — F-197 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-197 | P3 | Infinite Dungeon design lab / map route | The map’s background grid competed with the branching route lines and made the map feel visually clustered. | Fixed in the isolated prototype by hiding the background grid overlay for this review pass. Route edges remain unchanged so the next visual decision can be made against a cleaner backdrop. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=21` confirmed the map without background grid lines. No campaign state, Supabase transport, launcher, or PTY was touched.

## Opaque route locations — F-198 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-198 | P3 | Infinite Dungeon design lab / map route | Disabled location cards inherited global button opacity, allowing route edges to bleed through the actual locations. | Fixed in the isolated prototype by giving map nodes opaque backgrounds while keeping locked icons and labels visually subdued. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=22` confirms route edges stop visually at the location cards.

## Single-layer dungeon CTA — F-199 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-199 | P3 | Infinite Dungeon design lab / run setup | The `Enter the dungeon` button sat inside an extra bordered panel, adding a redundant visual layer. | Fixed in the isolated prototype by removing the outer CTA border/background and keeping only the black/gold text button. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=23` confirms the single-layer CTA.

## CTA button fade-in — F-200 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-200 | P3 | Infinite Dungeon design lab / run setup | The simplified entry button appeared without its own entrance motion after a class was selected. | Fixed in the isolated prototype with a short button-level fade/settle animation layered inside the existing CTA transition. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=24` confirmed the black/gold button fades in with the selected state.

## Market and campsite room upgrades — F-201 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-201 | P2 | Infinite Dungeon design lab / room economy | Campsites had only two small actions and markets had two narrow offers without a visible purse or meaningful preparation loop. | Fixed in the isolated prototype. Campsites now offer bandage, rest, ration, sharpened-edge and tonic actions with visible supplies. Markets now show live coins/inventory and four larger purchasable offers. Purchases and preparation actions update the run state and Character inventory. |

Verification: CUA keyboard/mouse visual testing on `http://127.0.0.1:5201/?v=25` opened campsite and market rooms, used rest/sharpen, purchased a ration, and confirmed HP, coins and inventory updates. No campaign state, Supabase transport, launcher, or PTY was touched.

## Market gear, fight-gated boss route, and reward ownership — F-202 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-202 | P2 | Infinite Dungeon design lab / route economy | The branching map could reach the converged boss without proving a fight, and markets had no rotating weapons/armor or explicit elite/boss reward ownership. | Fixed in the isolated prototype. The left branch now contains a normal gate, the boss stays disabled until one fight is cleared, the final row is only market/campsite preparation, markets stock two deterministic weapons plus two armor pieces, normal gates award coins only, elites award coins plus a trinket, and bosses award coins plus their trinket/weapon/armor set. Character loadout can equip owned drops. | |

Verification: CUA keyboard/mouse only (no Playwright) on `http://127.0.0.1:5201/?v=27` selected a class, cleared a normal gate, cleared an elite and received `Map Thread`, opened the market and bought `Market Mnemonic`, reached the preparation-only final row, and defeated the boss to receive `Ledger Charm`, `Count Cleaver`, and `Keeper Mail`. Boss remained disabled on a fresh floor until the first fight was cleared.

## Longer descent map — F-204 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-204 | P3 | Infinite Dungeon design lab / map readability | The six-row route left unused vertical space in the map panel and made the descent feel too short. | Fixed in the isolated prototype with a seventh deep-risk row. The final preparation row remains market/campsite-only and the converged boss is now the seventh destination row. |

Verification: CUA visual check on `http://127.0.0.1:5201/?v=29` confirmed the seven-row map fills the left panel cleanly without restoring background grid lines.

## Authored eight-row route and vision scroll scouting — F-205 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-205 | P2 | Infinite Dungeon design lab / risk pacing | Two consecutive unknown rows made the route feel like repeated risk without enough recovery space, and the route key sounded like an entry gate. | Fixed in the isolated prototype. The map is now a fixed authored eight-row route with one risk row, recovery/market rows, and a preparation row before the boss. Route Key is now an expensive Vision Scroll: elites can drop one and markets can sell one. It previews one risk profile but never gates entry; an explicit Enter the risk action is always available. | |

Verification: CUA keyboard/mouse only (no Playwright) on `http://127.0.0.1:5201/?v=30` confirmed the eight-row authored topology, entered the risk with zero scrolls, confirmed the entry button was enabled, cleared an elite for a Vision scroll, and saw the market sell the scroll for `80c`.

## Deferred persistent Codex and full risk-room rules — F-203 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-203 | P2 | Infinite Dungeon design lab / long-term learning memory | The design now needs across-run room/mob/question memory and a complete risk-room outcome system (fight, quiz, reward, non-lethal debuff, buff, teleport, discount stall, one-buy armory). | Parked deliberately in the roadmap. Route keys now reveal only a bounded risk profile; no future question or unsupported reward is exposed until the complete rules are designed and tested together. | |

## Committed three-lane pacing — F-206 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-206 | P2 | Infinite Dungeon design lab / route pacing | The route topology allowed players to drift between lanes and concentrated most combat at the top, followed by repeated camp/market rows before the boss. The first choice did not feel like a meaningful path commitment. | Reworked the fixed eight-row map into three independent authored lanes. Each lane now mixes challenge gates, elites, fate/risk rooms, campsites and markets before the final approach; only the final pre-boss row is camp/market preparation. No route edges cross lanes, and the map copy/footer explicitly explain the commitment. | |

Verification: CUA keyboard/mouse check on `http://127.0.0.1:5201/?v=33` selected the middle lane, showed exactly one reachable same-lane Gate I, and visually confirmed that only row seven contains camp/market preparation nodes before the boss.

## Independent room rolls — F-207 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-207 | P2 | Infinite Dungeon design lab / route generation | The three lanes were readable, but hand-balancing room types made every run feel authored toward a target distribution. The player explicitly wanted real luck, including a full row of elites, without per-row or per-lane quotas. | Room types now roll independently for every non-final node at run start and after each boss clear. The topology and lane commitment stay fixed; the final pre-boss row is the only forced camp/market row. A single global safety check adds one challenge gate only if a rare roll produced no fight or elite anywhere, preserving boss reachability without balancing the lanes. | |

Verification: Browser-only CUA checks on `http://127.0.0.1:5201/?v=35` and `?v=36` showed two different fresh room rolls while the final row stayed camp/market-only. The live map copy exposes the independent-roll rule and the existing boss safety gate remains intact.

## Recovery after dangerous rows and class passive separation — F-208 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-208 | P2 | Infinite Dungeon design lab / route pacing and classes | Purely independent rolls could stack two elites or three normal gates without a readable recovery signal, and the class cards described the passive as if it were part of the starter weapon. | Added a light recovery rule: a row with two elites or three gates forces a campsite on the next row and makes that recovery row end in a market. Other rows only repair a missing recovery type at their right edge (market present but no camp → camp; neither present → market). Class data now stores a separate passive; equipping a new weapon leaves the active class passive untouched and the UI states that explicitly. | |

Verification: Browser-only CUA on `?v=37` showed the recovery rule copy, random row types, passive labels on all class cards, and an active Character header reading `ACTIVE CLASS · PASSIVE`; the starter weapon remains a separate loadout item.

## Distinct starter weapon effects — F-209 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-209 | P2 | Infinite Dungeon design lab / class loadout | Starter weapon text duplicated each class passive, making weapon swaps feel meaningless. | Split the three starter weapons into adjacent but distinct effects: Lint Lantern grants one second bounded hint on a failed submission, Loopblade adds +1 Resolve damage against elite gates, and Branch Compass grants one free risk-profile reveal per floor. The active class passive remains stored and evaluated separately from `state.equipped.weapon`, including after weapon swaps. | |

Verification: Browser-only CUA on `?v=38` and `?v=39` showed separate weapon/passive cards, Route Merchant’s Branch Compass equipped in Character, and the active class passive remaining visible independently.

## Loadout vision-scroll scouting and run-stat ownership — F-210 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-210 | P2 | Infinite Dungeon design lab / loadout and map scouting | Vision Scrolls were only exposed as room-local inventory and could not reveal an unrevealed risk elsewhere on the route; `Fights cleared` was presented as if it were an inventory item. | Fixed in the isolated prototype. Character → Loadout now exposes Vision Scroll as a run item with `Use on map`; scouting enables any unrevealed risk node on the map, including off-route nodes, consumes exactly one scroll, shares the same revealed-risk ledger as room-local scouting, and never reveals future questions or answers. Fights cleared and boss-gate status now live under Character → Stats. | |

Verification: Browser-only CUA on `http://127.0.0.1:5201/?v=40` cleared a live elite, confirmed `Vision scroll · 1 left` in Character → Loadout, activated `Use on map`, selected an off-route unrevealed Fate/Risk node, and saw its bounded profile appear while the scroll count became `0`. The same node then reported `scouted`/disabled; Character → Stats showed `Fights cleared 1` and `Boss gate OPEN`, while Character → Inventory listed only consumable supplies. Room-local reveal cancels any active map-scout state in code.

## Branch Compass map action — F-211 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-211 | P2 | Infinite Dungeon design lab / Route Merchant loadout | The Route Merchant’s Branch Compass was described as a free risk read, but the only visible interaction existed after entering a risk room. The starter weapon appeared equipped yet was effectively inert on the route map. | Fixed in the isolated prototype. An equipped Branch Compass now exposes `Read on map` from Character → Loadout. It enables any unrevealed risk node, including off-route nodes, consumes no Vision Scroll, records the same revealed-risk ledger, and is spent once per floor. The map note and PYR event identify whether the active read came from the Compass or a Scroll. | |

Verification: Browser-only CUA on `http://127.0.0.1:5201/?v=41` selected Route Merchant, confirmed the equipped Branch Compass exposed `Read on map`, activated it from Character → Loadout, selected an off-route unrevealed Fate/Risk node, and saw the bounded profile appear without a scroll. The loadout then showed `Spent`, the same node reported `scouted`/disabled, and the PYR event identified the free floor read.

## Risk-room outcome state machine and identity reveal — F-212 (2026-09-18)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-212 | P2 | Infinite Dungeon design lab / Room Screen | Fate/Risk nodes only had a telegraph and an entry button. Entering one did not provide a bounded outcome loop, and the UI kept showing a generic Fate/Risk identity after its profile was known. | Fixed in the isolated prototype. Committed risks now move through explicit `open → challenge/shop → resolved` states. Elite and quiz risks use the existing IDE submission surface with risk-specific damage and text-only hints; cache, hex, blessing, teleport, discount stall, and armory outcomes apply bounded prototype values and produce a PYR event before route control returns. A revealed/entered profile now changes the visible node/room identity (for example, discount/armory → Market, elite → Elite Gate, quiz → Challenge Gate, cache/shrine/corridor → named bounded room). |
| F-213 | P2 | Infinite Dungeon design lab / risk exit | Leaving a resolved shop/cache could clear the active outcome while leaving the node marked entered, which rendered a dead “Risk entered” card with no valid route exit. | Fixed with a resolved-risk presentation and `Leave the room` route exit. A resolved risk cannot be entered or rewarded twice. |

Verification: Browser-only CUA on the WSL-served prototype opened an elite, cleared it for a trinket and Vision Scroll, entered a risk, opened a bounded armory, bought one weapon, entered a second cache risk, received `+30 coins · +1 bandage · +40 score`, and confirmed the resolved card returned to route control without a refresh. The cache visibly changed the room panel from Fate/Risk to Hidden Cache. `node --check prototypes/infinite-dungeon/src/main.js` passed. The state-machine edge checklist is: hidden node (optional scout) → committed open outcome → one resolver or IDE challenge → resolved outcome → one route exit; duplicate purchase/reward and future-question leakage remain blocked by state guards.

## Local Dungeon Codex memory — F-214 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-214 | P2 | Infinite Dungeon design lab / learning memory | A run could show room outcomes, but the prototype forgot discovered rooms and question lenses as soon as the player reset the run, making the dungeon feel disposable instead of cumulative. | Fixed locally. Character → Codex now stores a bounded local archive in `localStorage`, recording only discovered/entered rooms and attempted challenge mobs/question types with validated outcomes. Resetting a run leaves this archive intact; no Campaign, Supabase, or PTY state is involved. |

Verification: Browser-only CUA on the WSL-served prototype opened Character → Codex and recorded `Campsite`. After Reset mock run and a fresh run it remained and incremented to `3 visits`; after browser refresh it remained again. A clean elite submission added `The Faultline · BUG HUNT · CLEARED` with Resolve and loot text. The archive has explicit future-data boundaries: no hidden questions, answer keys or locked rewards are projected.

## One-action campsite preparation and armor brace — F-215 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-215 | P2 | Infinite Dungeon design lab / campsite economy | Campsites let several recovery/preparation actions fire during one visit, the ration still awarded score, and there was no small defensive preparation to soften a failed submission. | Fixed locally. Every campsite now records one shared `camp` action key and disables the other preparations immediately. Cooking a ration consumes it for +10 maximum HP only (no score); `Fortify your armor` grants a starting-value 6 HP one-shot brace that is consumed by the next failed submission and is reported in the PYR event/notice. The brace resets at a new run or floor, and its status is visible in the campsite supply strip and Character inventory. | |

Verification: `node --check prototypes/infinite-dungeon/src/main.js` and `git diff --check` pass. Browser-only CUA confirmed a fresh campsite, the one-action lock with disabled alternatives, ration max-HP behavior, armor-brace readiness, and a failed submission showing the bounded brace absorption.

Starting-value test plan: 6 HP is deliberately a small first tuning value. After five failed-submission playtests, increase by 2 if the brace is not meaningful; decrease by 2 if it trivializes a failure.

## Ration max-HP state leaked into a fresh mock run — F-216 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-216 | P2 | Infinite Dungeon design lab / run reset | After cooking a ration, `Reset mock run` restored the class screen but did not restore `maxHp`, so a new run could inherit the previous run's max-HP ceiling. | Fixed by resetting `maxHp` to 100 in both `startRun()` and `resetRun()`. A new run now starts at the bounded 78/100 prototype baseline; the max-HP increase remains scoped to the current run. | |

Verification: Browser-only CUA reproduced the stale 78/110 state before the repair, then a clean server reload and run-start check showed the baseline 78/100. No canonical campaign state was involved.

## Infinite Dungeon editor and combat-learning slice — F-217 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-217 | P1 | Infinite Dungeon design lab / editor bridge and encounter learning | The room prototype used a textarea, gave the same presentation at every floor, had no authored mechanic state, and could not safely connect a real `dungeon.py` for reversible bug-hunt play. | Replaced the room editor with the locally bundled Monaco stack and local identifier completion; added floor-scaled guide inference/validation, preview-only Resolve, Run HP and Mob Profile panels, bounded authored mechanics, real-time Self-Destruct, reversible Bug Hunt mutations, digest mismatch blocking, bounded browser/sibling backups, one-token restore with mechanic reroll, and a docked non-blocking PYR event. File handles persist through IndexedDB when the browser supports structured cloning, while disconnected/unsupported browsers stay in memory and never simulate a file mutation. | |

Verification: Prototype tests (`npm test --prefix prototypes/infinite-dungeon`) pass 9/9; WSL production build passes (711 modules transformed). Browser-only CUA on `http://172.26.238.39:5202/` visually inspected the Monaco room, guide, Resolve preview, Run HP, Mob Profile and docked PYR; typing showed preview progress and a clean submission committed Resolve and returned to the map without refresh. Claude Sonnet’s read-only review was incorporated: Monaco view state is preserved, guide validation is used on submit, mechanic clocks clear on success, backups are capped, and Bug Hunt falls back when no writable file is connected. Arbitrary Python execution remains intentionally deferred for this isolated prototype; no Campaign, `progress.json`, Supabase, or PTY state was touched.

## IDE brief containment — F-218 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-218 | P2 | Infinite Dungeon design lab / visual layout | The long learning brief could spill past the fixed IDE row and sit behind the prototype footer, making the lower Mob Profile/file bridge hard to read. | Added a bounded internal scroll owner to the left challenge brief. The editor/PYR column remains full-height and the footer no longer overlaps encounter details. | |

Verification: Browser-only CUA visual pass after a WSL server restart showed the left brief scrollbar, readable Mob Profile and project bridge, docked PYR spacing, and a live Self-Destruct countdown after editor focus.

## Infinite Dungeon Run/Submit split and Forge editor parity — F-219 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-219 | P1 | Infinite Dungeon design lab / Monaco and combat loop | The isolated room editor did not look or behave like Forge: Python colours/completions were absent, there was no visible output surface, and the single Run & submit control blurred safe experimentation with a state-changing verdict. | Fixed in the prototype only. The editor now loads the same bundled Python tokenizer and Monaco suggestion controller, uses the Forge-aligned dark theme, and offers local identifier/keyword completion (`true` suggests valid `True`). A Local Terminal self-check panel reports bounded syntax, concept and literal-output previews. `Run self-check` never changes HP/Resolve/rewards; `Submit to PYR` alone invokes the existing encounter mechanics and reward path. Mob profiles now show explicit `ON RUN` behavior for each authored mechanic. | |

Verification: Prototype tests pass 12/12; WSL build passes with the Python contribution and suggestion controller bundled locally. Browser-only CUA verified syntax colours, the visible `True` completion popup, a passing self-check output, a syntax-error self-check marked `NO DAMAGE` with HP/Resolve unchanged, and a later clean Submit that changed the prototype run state. Canonical Forge/state/Supabase/PTY boundaries remain untouched.

## Infinite Dungeon keyboard parity — F-220 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-220 | P1 | Infinite Dungeon design-lab editor controls | The isolated Monaco room editor had Run and Submit buttons but no campaign-parity Ctrl/Cmd keyboard contract. Ctrl/Cmd+S could invoke the browser page save and Enter combinations were not guaranteed to reach the intended action. | Fixed locally. Monaco plus a capture-phase browser bridge now map `Ctrl/Cmd+Enter` to safe Run self-check, `Ctrl/Cmd+S` to Save draft, and `Ctrl/Cmd+Shift+Enter` to Submit to PYR. Save writes the connected `dungeon.py` after digest validation or stores a browser-local draft when disconnected; it never changes combat state. Buttons expose visible hints and `aria-keyshortcuts`. | |

Verification: Prototype tests pass 12/12; `node --check` passes; WSL production build passes (749 modules transformed); existing frontend suite passes 95/95. Browser-only CUA on port 5202 pressed all three shortcuts in Monaco: Run showed both a valid preview and an invalid `CHECK FAILED · NO DAMAGE` state with HP/Resolve unchanged, Save showed the browser-local draft notice, and Submit emitted a PYR verdict and returned map control. A desktop screenshot confirmed the action bar remains compact and readable. No canonical Forge/state/Supabase/PTY boundary was changed.

## Infinite Dungeon Codex boundary cleanup — F-221 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-221 | P2 | Infinite Dungeon design-lab Character surface | The prototype created a second local Codex archive and tab while the canonical Campaign Codex already owns learning history. | Fixed locally before port planning. Removed the local archive persistence/recording code, Codex renderer and styles. Character now exposes only Loadout, Inventory and Stats; the legacy browser key is no longer read or written. | |

Verification: Prototype tests pass 12/12; WSL build passes (749 modules transformed); browser-only CUA confirmed exactly three Character tabs and no Codex archive after a clean run. The canonical Campaign Codex and all state/cloud/PTy boundaries remain untouched.

## Infinite Dungeon canonical port — F-222 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-222 | P1 | Main-game Dungeon route and state custody | Infinite Dungeon was complete only as an isolated prototype, while the main game still lacked a canonical route for its class choice, starter loadout, checkpoint, editor and combat-safe Run/Submit workflow. | Ported the bounded vertical slice into the main game. The route is first-class after Tutor, class/passive/starter weapon/checkpoint data comes from the state gateway, the room uses bundled Monaco with local completion and Python styling, and Run self-check is visibly separate from Submit to PYR. |
| F-222-map | P2 | Main-game Dungeon map | Client-created future nodes could imply rooms that the state service had not issued. | Map now shows recorded history, the current room and only state-issued next choices; no future question or loot identities are invented in React. |
| F-222-codex | P2 | Prototype boundary | A local Codex copy in the prototype would have duplicated the canonical Campaign Codex after porting. | Removed Codex from the prototype before porting. Character keeps Loadout, Inventory and Stats; canonical Codex remains global. |

Verification: frontend suite passes 95/95; WSL production build passes (1,346 modules transformed); `ide/server/state.py` and `ide/server/app_v2.py` pass `py_compile`; browser-only CUA verified the canonical Dungeon route, Monaco/editor actions and state-backed map. Richer route/risk/elite/campsite and real file-mutation mechanics remain a separate state-service port slice.

## Infinite Dungeon room parity and reset affordance — F-223 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-223 | P1 | Main-game Dungeon room screen | The canonical room had the right map shell but still used a generic encounter identity/brief, and reset was only reachable below the visible room viewport. | Fixed. The room now uses the state-owned prototype-aligned mob identity and concept/difficulty brief, keeps the single Forge-style Challenge IDE handoff, and exposes one visible `Reset run` control in the Dungeon run header. Reset still goes through `/api/dungeon/reset`, discards only the active Dungeon checkpoint, and leaves Campaign progress untouched. | |

Verification: state-service tests pass 46/46; frontend suite passes 95/95; WSL production build passes (1,346 modules transformed). Browser-only CUA compared the prototype and canonical room screens at desktop size, then verified the canonical Room screen and Challenge IDE visually: state-owned `The Count Keeper` is visible, the room brief matches the prototype flow, and `Reset run` is visible without scrolling. No reset was invoked during verification, so the active local run remained intact.

## One-command Quest Lab startup — F-224 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-224 | P2 | Local distribution / startup UX | Starting Forge required remembering the nested WSL launcher path, and an HTML page cannot safely spawn the backend/frontend processes. | Fixed locally. Added root-level `start-questlab.cmd` (double-click/Windows terminal), `start-questlab.ps1` (PowerShell options) and `start-questlab.sh` (WSL/native Linux). All delegate to the existing guarded launcher, so branch, canonical state, dependency, freshness and stable-PTY checks remain in one source of truth. | |

Verification: PowerShell and shell syntax checks pass; `git diff --check` reports no whitespace errors. No additional server was started during this launcher check, so existing PTYs and player state were not disturbed.

## Infinite Dungeon canonical prototype parity and page scroll — F-225 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-225 | P1 | Main-game Dungeon route / visual port | The first canonical port had been visually tightened and wrapped in a tab strip, so its class selection, map height, room spacing and character surface no longer matched the approved Infinite Dungeon prototype. The app-wide `game-screen` overflow lock also clipped the lower route content. | Fixed locally. The canonical route now uses the prototype's class-card hierarchy and phase-in CTA, restores its header/three-column proportions, eight-row map geometry, room illustration scale and action spacing, hides the canonical-only tab strip, and lets the Dungeon route own a bounded vertical scroll. State-gateway actions, reset, Monaco, and PTY boundaries remain unchanged. |

Verification: frontend suite passes 96/96; WSL production build passes (1,346 modules transformed). Static parity tests cover the prototype card hierarchy, map proportions and route scroll owner. A browser/CUA screenshot pass was not available in this turn, so live visual confirmation remains pending before calling the port visually certified.

## Codex lesson-reader simplification — F-226 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-226 | P2 | Codex / theory learning surface | Codex had accumulated a dense hero dashboard, repeated definition copy, decorative nested cards and several competing reading controls. The result felt like an odd feed instead of a student-facing concept lesson. | Simplified the reader around one path: choose a concept, read the core definition, inspect a generic example, answer a state-safe self-check, then review validated encounters or write notes. The hero now exposes only useful concept/encounter/check/note counts; the index is a quiet concept list; the selected page uses restrained tabs and one bounded reading surface. Added authored state-owned common-mistake cues and check prompts for the generic Python concepts, with an explicit `Open Tutor` handoff that never reveals campaign answers. Encounter evidence, notes, mastery, revision polling, state custody, Supabase and PTYs are unchanged. |

Verification: frontend suite passes 97/97; WSL production build passes (1,346 modules transformed); canonical state-service suite passes 46/46 and verifies projected common-mistake/check metadata without leaking answer fields. Full backend discovery remains red in three pre-existing Dungeon context-bridge expectations (starter inventory/nonce), unrelated to Codex. Browser/CUA visual certification was not available in this turn and remains the next live check.

## Codex resource-first information architecture prototype — F-227 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-227 | P2 | Codex design exploration | The live Codex needed a learning-index-first direction before another canonical UI rewrite. Encounter history should support the lesson, not compete with it. | Added an isolated disposable prototype at `prototypes/codex-resource`: a searchable concept dictionary grouped by topic, a default Learn page ordered as definition → mental model → generic example → common mistakes → self-check, and secondary Encounter evidence/Notes views. The prototype uses sample data and browser-local notes only; no campaign, state service, Supabase or PTY boundary is touched. |

Verification: `node --check src/main.js` passes; WSL prototype build passes (4 modules transformed). Windows build was not used because the existing Windows checkout is missing the optional Rollup native package; the WSL build is the valid local build path. Live browser visual review remains the next step before choosing the canonical port.

## Codex encounter-history de-emphasis — F-228 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-228 | P2 | Codex resource prototype | The first prototype treated Encounter evidence as a peer tab, but a mob name, lens and cleared status did not help a learner study the concept. | Removed the encounter tab and combat-log sample data from the prototype. The resource flow now stays focused on theory and notes. Past mobs can return later only as useful learning history with validated question type, repeated mistake, attempts and takeaway fields. The canonical Codex was not changed by this prototype iteration. |

Verification: prototype syntax check and WSL build pass; live browser review is ready at port 5206.

## Codex compact study spread — F-229 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-229 | P2 | Codex resource prototype / desktop layout | The resource-first design was readable but made the learner scroll through several full-width lesson blocks before reaching the self-check. | Added a desktop two-column study spread: definition/mental model on the left, example and mistakes on the right, and the self-check as one closing row. Narrow screens retain the single-column reading order. Notes remain spacious on their own page. |

Verification: prototype syntax check passes, WSL build passes, and the prototype server returns HTTP 200 at port 5206. Live screenshot review remains available for the next user check.

## Tutor Codex-first shell and review queue — F-230 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-230 | P2 | Tutor learning flow | Codex needed to be the first Tutor surface, with practice modes and a review loop available without returning to the campaign shell. | Added a Tutor shell to the isolated prototype: Codex is the default tab, IDE practice is the second tab, and practice offers Predict output, Trace variables, Find a bug, Explain the idea, and Tiny transfer challenge. A browser-local review queue supports learner suggestions, pin/unpin, dismiss, and PYR-style suggestions after a short practice submission. No canonical state or campaign files are changed. |

Verification: browser keyboard/mouse checks on port 5206 confirmed tab switching, all practice-mode controls, short-response PYR queue suggestion, pin/unpin, dismiss, learner suggestion, and queue persistence after reload. `node --check src/main.js` and the WSL production build pass.

## Tutor `.md` notebook folio — F-232 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-232 | P2 | Tutor notebook / note-taking | The `.md` file rail opened a surface that could be mistaken for another Codex reader, while Codex's Notes panel duplicated the same job. The learner asked for a real notebook for writing, linked to a concept/chapter and animated like a book. | Fixed in the isolated prototype. `.md` now opens a warm paper folio with a chapter selector (Fundamentals, Data, Control flow, Functions, Review notes), linked concept buttons, four writing pages (Notes, Questions, Examples, Next practice), local save controls, longer vertical pages and a 360ms interruptible page-turn animation with reduced-motion fallback. Codex no longer renders its Notes panel; it offers one explicit Open notebook handoff instead. Notebook notes use a separate browser-local key and do not mutate Codex, campaign state, Supabase or PTYs. | |

Verification: CUA browser checks opened `.md` from the compact IDE rail, captured the live warm-paper spread, observed the page mid-turn and after it settled, changed the chapter to Data, typed a learner note and verified the local save status. `node --check`, WSL production build and `git diff --check` pass.

## Campaign-parity Tutor IDE surface — F-231 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-231 | P2 | Tutor prototype / IDE parity | The first Tutor pass had a good lesson layout but did not feel like the campaign IDE: there was no local terminal, AI terminal, or compact file dock. | Added a Monaco-backed `tutor.py` workbench, local self-check terminal, bounded PYR terminal, compact `.py`/`.md` rail, save/run/submit actions, and campaign-aligned shortcut labels. The five practice modes now sit in a strip above the workbench so the editor owns the left side. |

Verification: desktop browser inspection confirmed syntax-coloured Monaco editing, compact rail, mode strip, local terminal output, PYR hint messages, and sidebar expand/collapse. Prototype syntax check and WSL production build pass; canonical Forge/state/Supabase/PTY surfaces remain untouched.

## Two-level Tutor navigation and `.md` screen switcher — F-233 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-233 | P2 | Tutor navigation | The shell exposed Codex, IDE practice and Notebook as three competing top selectors, even though the learner wanted `.md` to switch screens inside IDE practice. | Fixed in the isolated prototype. Top navigation now has only Codex and IDE practice. The compact `.py`/`.md` rail stays visible for the IDE surface; `.py` opens the editor and `.md` opens the writing notebook, with the active file visibly selected. | |

Verification: CUA opened `.md` from the IDE rail and confirmed the notebook rendered beside the compact rail while IDE practice remained the active top-level tab. Codex's explicit Open notebook handoff follows the same two-level path.

## Notebook formatting, scroll and page looks — F-234 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-234 | P2 | Tutor notebook authoring | Long notes had a fixed editor height and no quick writing formats, so a learner could outgrow the folio or be forced to type every list marker manually. | Fixed in the isolated prototype. `*`/`-` lines normalize to visible bullets and Enter continues bullet/number lists. A small toolbar inserts bullet, numbered, quote and indented-code lines, and local page-look choices were added. The later F-235 pass bounds the writing area inside the folio and keeps Save page visible. | |

Verification: CUA typed a markdown-style `*` line and confirmed `•`, exercised the numbered format control, entered long lines and observed the note scrollbar, then selected Graph paper and visually confirmed the grid texture. F-235 records the final bounded-folio correction.

## Tutor notebook authoring controls and bounded folio — F-235 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-235 | P2 | Tutor notebook chapters / writing surface | The notebook chapter list was fixed, page color was not learner-selectable, and long textarea content could visually run into the Save page action or make the outer page grow. Markdown-style commands were also limited to a small toolbar. | Fixed in the isolated prototype. Chapters are browser-local editable records with `+ New`, `Edit`, and `Delete` controls; page color supports Warm cream, Soft sky, Quiet sage, Faded lilac and Sand; the two-page folio has a finite height with an inner note scrollbar and an anchored Save page row. A filtered `/` block menu adds headings, lists, to-dos, quotes, code blocks and dividers with keyboard navigation. No canonical state, Supabase or PTY boundary changed. | |

Verification: CUA inspected the chapter form, page-color selector and slash menu, inserted a heading, and typed 50 long lines. The final screenshot showed the note scrollbar inside the folio with Save page still visible and no text bleed. `node --check`, WSL production build, HTTP 200 and `git diff --check` pass.

## Forge resource-first Tutor/Codex port — F-236 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-236 | P1 | Forge Tutor/Codex parity | The resource-first Tutor prototype lived outside Forge, so the canonical app still exposed the older Tutor/Codex surfaces and the `.md` folio could be cut off by the fixed Forge grid. | Ported the prototype's Codex folios, IDE practice workbench, local completion, terminal/PYR guidance, compact `.py`/`.md` rail, chapter/page controls, colors and slash menu into the canonical React route. The resource wrapper now owns the bounded page scroll and styled scrollbar. Canonical revision polling, state gateway, Supabase boundary and PTY mounts remain unchanged; browser-local notebook preferences remain local until a notes schema is approved. |

Verification: CUA screenshots compared prototype `:5206` with Forge `:5174`. The Forge surface visibly contains the same reference folios and notebook controls; focusing the lower Save page control scrolls the resource frame to reveal the complete folio. WSL frontend tests (97/97) and production build pass.

## Tutor IDE file rail and terminal visibility — F-237 (2026-09-19)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-237 | P1 | Tutor `.md` / IDE workspace | Opening `notes.md` removed the compact file rail, leaving no obvious route back to `tutor.py`. The reduced Forge IDE also let its local terminal and bounded PYR panel fall below the useful viewport. Codex remained duplicated in the shared top navigation even though it is a folio inside Tutor Notebook. | Fixed by retaining the `.py`/`.md` rail on the notebook route, making `tutor.py` a direct IDE switcher, tightening the Monaco workbench height, reserving a visible local terminal output region, and making the PYR panel a bounded scroll region. Codex remains directly addressable for legacy links but is removed from the duplicate top-level navigation. | |

Verification: Fresh CUA at `http://127.0.0.1:5175/` opened Tutor IDE, visually showed the local terminal and PYR panel together in the bounded workspace, clicked `notes.md`, and returned with `tutor.py`. The shared top menu showed Tutor Notebook but no duplicate Codex item. Frontend tests **97/97**, production build (**1,346 modules**), and `git diff --check` pass.

## Codex folio examples, encounter excerpts and signal placement — F-238 (2026-09-20)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-238 | P2 | Codex learning folios | Definitions repeated a usage prompt, common mistakes had no concrete examples, validated encounters did not surface learner-authored code, and Practice Signals consumed half of the mistake page. | Fixed. Examples now keep one `CHECK YOURSELF` prompt; each common mistake has a server-authored example; validated Forge clears can retain a bounded code excerpt; Practice Signals is a compact full-width strip below the mistakes. | |

Verification: CUA inspected Definition, Examples and Mistakes & signals at `http://127.0.0.1:5175/`. The live folio showed one prompt, full-width mistake examples and the Practice Signals strip. Legacy encounter records without a captured snippet remain explicitly marked as unavailable. No answer keys or future prompts are exposed.

## Campaign v1 guard-break prototype — F-239 (2026-09-20)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-239 | P1 | Campaign v1 encounter layout | The first design pass placed the bounty/objective information beside the AI surface, which made the two-terminal learning layout ambiguous and pushed the combat context away from the active Forge file. | Fixed in the isolated Campaign v1 design lab. Bounty, weakness signal, objective context, and mob profile now live in the left panel; the center remains the Forge editor plus local self-check terminal; the right panel remains the non-blocking PYR AI terminal. Guard Break is visibly distinct from the mandatory correct Finisher submission. |

Verification: CUA keyboard/mouse inspection at `http://127.0.0.1:5207/` confirmed the three-column layout, Guard 10/10 → STUNNED 0/10 transition, safe submission window, PYR event update, and validated Finisher/reward screen. Prototype tests **7/7** pass and the WSL production build passes. The prototype does not touch canonical Forge state, Supabase, progress files, or PTYs.

## Campaign v1 kit, terminal, camp and market pass — F-240 (2026-09-20)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-240 | P1 | Campaign v1 preparation and encounter context | The left encounter rail had unused space and did not show the player’s equipped kit or usable supplies. Home and Market still read as generic card stacks rather than places in the campaign world, and the AI surface did not read like a terminal output stream. | Fixed in the isolated prototype. The left rail now shows armor, trinket, bandages, and Ember tonic actions; the center self-check and right PYR surfaces use terminal-style prompts/output; Home is a selectable camp-house scene; Market is an auction-house scene with Rook and gated daily lots. The tonic and bandage behavior is serializable in prototype state and covered by tests. | |

Verification: Prototype tests **8/8** pass and the WSL production build passes. Static source/build checks confirm the new surfaces compile. CUA visual verification was attempted against the user-visible localhost tab, but that browser session continued serving its older cached prototype bundle despite the local Vite server exposing the updated source; a fresh visual pass is still required once the browser is pointed at the current process. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 provider picker and terminal parity — F-241 (2026-09-20)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-241 | P2 | Campaign v1 AI/local terminals | The prototype's right-hand AI surface had event output but no quick way to choose which assistant should act as PYR, while the local self-check and AI output did not share the screenshot's terminal hierarchy. | Fixed in the isolated prototype. The encounter now keeps Forge's local self-check terminal in the center and a tall PYR / AI terminal on the right with Codex, Claude, AGY, Copilot, Clear, and Reconnect controls. The selected provider is shown in the prompt and current-event label; the prototype deliberately labels the stream as local design-lab output rather than claiming a live provider connection. Home's station menu and Market's category/rarity shelves remain intact. | |

Verification: CUA loaded the restarted prototype, entered a bounty, visually inspected the three-column terminal composition, selected Claude, and confirmed the right header/prompt/current-event changed to Claude while the Forge terminal stayed connected. Prototype tests **9/9** pass; WSL production build passes. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 encounter helper readability — F-242 (2026-09-20)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-242 | P2 | Campaign v1 Forge guidance | The `RUN VS SUBMIT` explanation and the design-lab validator description were styled like tiny metadata, making the distinction between self-check, validation, and Guard-break simulation hard to read. | Fixed in the isolated prototype. Learner-facing helper copy now uses stronger contrast, 12px Run/Submit text, 11px validator text, and more generous line height while preserving the compact buttons and editor proportions. | |

Verification: CUA screenshot at the current 1280×960 browser viewport shows both explanations readable without clipping or pushing the local terminal out of view. Prototype tests **9/9**, WSL production build, and `git diff --check` pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 bounded raw-terminal contract — F-243 (2026-09-20)

| ID | Severity | Area | Finding | Status |
|---|---|---|---|---|
| F-243 | P1 | Campaign v1 terminal trust and hierarchy | The prototype used hand-written terminal cards with a blinking PYR cursor, one shared event presentation, and no learner-facing local command path. The provider row could also consume the flexible grid track and push AI scrollback to the bottom of the rail. | Fixed in the isolated prototype. Self-check and PYR now render through one bounded raw-terminal contract with capped per-channel scrollback, connection status, provider-specific streams, Clear, Reconnect, and a real bounded self-check input (`help`, `run`, `clear`, `reconnect`). PYR is explicitly output-only with a static status cursor; it never implies unsandboxed provider input. The provider row has a dedicated grid track so scrollback stays top-aligned. | |

## Campaign v1 full-width workbench and shortcut rail pass — F-244 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-244 | P1 | Campaign v1 Forge workbench | The encounter was constrained by the old 1440px centered shell; adjustable rails had dead space and the right rail’s width controls collided with its connection badge. The local bottom pane carried explanatory footer copy, while Run/Save/Submit were squeezed into the old action-row area and feedback toasts covered terminal output. | Fixed in the isolated prototype. Encounter/map shells now fill the device with a small readable inset; left bounty and right PYR rails retain collapse, drag, and +/- width controls with reserved header space; Forge renders Save, Run, and Submit as a dedicated non-wrapping top toolbar group (Python badge removed); the local pane is terminal-only output/prompt; encounter feedback is centered above the IDE instead of covering scrollback. Keyboard contract remains Shift+Enter or Ctrl/Cmd+Enter = Run, Shift/Ctrl/Cmd+S = Save, Ctrl/Cmd+Shift+Enter = Submit, and Shift+Alt+F = format preview. CUA visual verification on the live port-5207 tab confirmed full-width rendering, aligned toolbar buttons, spaced right controls, both rail collapses, terminal output after Run/Save, and unchanged prototype HP/coins. | Fixed / verified |

Verification: CUA loaded the cache-busted `http://127.0.0.1:5207/?terminal-layout-v2=20260920&cache=terminal7` surface, confirmed the readable Self-check and PYR headings, selected Claude, ran `help`, exercised Clear and Reconnect, ran the self-check button, and submitted a failing attempt. HP fell from 84 to 76 only on Submit; the terminal output recorded the validator result. Prototype tests **9/9**, `node --check`, and the WSL production build pass. Windows build remains blocked by the pre-existing missing optional `@rollup/rollup-win32-x64-msvc` package; no canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 bounty board progression slice — F-245 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-245 | P1 | Campaign v1 Bounty Office | The office was a flat contract list with no visible prerequisite chain, while the project-map rail carried board-like content that did not belong there. Village tasks were mixed into the office even though village work is planned as its own future board. The map rail also had no collapse control. | Fixed in the isolated prototype. Bounty Office now owns the board: Count Keeper is open, House Ledger is locked behind Count Keeper, and Dealer’s Hand is locked behind House Ledger. Locked cards remain inspectable and show an explicit `Complete X to unlock` message with a disabled CTA; the state layer prevents bypassing the prerequisite. The project-map rail is back to POIs/progress context, has a persisted collapse/expand control, and the office no longer exposes Village Tasks; a small Village Board · Next marker preserves the future scope. | Fixed / verified |

Verification: CUA opened `http://127.0.0.1:5207/?bounty-board-v1=20260920-office4`, visually inspected the horizontal BOUNTY BOARD and posted marks, selected House Ledger, and confirmed the prerequisite text plus disabled lock CTA. CUA collapsed and re-expanded the project-map rail. Prototype tests **10/10**, `node --check`, and WSL production build pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 pinned bounty-board presentation — F-246 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-246 | P1 | Campaign v1 Bounty Office | The progression row read like another compact list instead of a bounty board, locked entries revealed too much structure, the old posted-mark list duplicated the board, and the PYR status toast sat over bottom-right content. The office heading was also limited by the generic narrow title width. | Replaced the board row with three selectable pinned notice cards. Open marks show a large SVG icon, reward/warning signal, short description, and title; locked marks show a muted silhouette, `UNKNOWN`, and only the prerequisite reveal message. Removed the duplicate posted-mark list so the selected bounty’s detailed brief is the only detail panel. Moved the PYR status toast to the top context area and widened only the office heading to a readable two-line treatment. | Fixed / verified |

Verification: CUA visually inspected `http://127.0.0.1:5207/?bounty-board-v1=20260920-posters3`, selected an unlocked poster, selected a locked silhouette, confirmed the detail panel/disabled prerequisite CTA changed correctly, and confirmed the PYR event moved to the top. Prototype tests **10/10**, `node --check`, and WSL production build pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 scalable bounty backlog — F-247 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-247 | P1 | Campaign v1 Bounty Office | Three posters were enough to demonstrate the board interaction, but not enough to make a learning project feel expandable. Repeating concepts such as loops, conditions, and functions need several distinct practice contracts before a larger project such as a football manager can be represented. | Expanded the data-driven main board to nine pinned bounties: three examples each for Loops and accumulators, Conditions and filtering, and Functions and return values. Each entry has its own task brief, weakness, mechanic, reward signal, icon, and prerequisite. The poster surface keeps the reference-board treatment (icon or locked silhouette, reward/warning, short copy, title) and now uses a bounded internal scroll area so the selected main bounty description remains below without turning the page into an endless wall. The prerequisite helpers and locked-state UI continue to prevent future work from being revealed or taken early; Village tasks remain on the future Village board. | Fixed / verified |

Verification: CUA loaded the restarted cache-busted prototype at `http://127.0.0.1:5207/?bounty-board-v1=scale2`, visually inspected the nine-poster board and its internal scroll, confirmed the selected bounty detail remains below, and selected a locked Loop Rehearsal to verify the disabled prerequisite CTA and PYR message. Prototype tests **11/11**, `node --check`, and the WSL production build pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 pinned notice boards and threat sizing — F-248 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-248 | P1 | Campaign v1 Bounty Office | The expanded backlog still read as one long card grid. It did not yet resemble a physical board with notices pinned at varied angles, and there was no way to keep a larger project’s posters from becoming a cluttered wall. Small mobs, elites, and bosses also had no visual scale language. | Reworked the office into switchable wood-backed notice boards. Each board holds at most seven pinned posters; the current data is split into two boards (six Chapter 01–02 notices and three Chapter 03 notices). Stable authored offsets/rotations create the loose reference-board placement without reshuffling on every click. Posters now carry `mob`, `elite`, or `boss` size tiers; elites and bosses occupy visibly taller notices, while open notices show the threat label and locked notices retain only their silhouette. Previous/Next Board controls flip the surface and select that board’s first notice, while the full selected bounty brief remains underneath. | Fixed / verified |

Verification: CUA loaded `http://127.0.0.1:5207/?bounty-board-v1=boards5`, inspected the wood-backed first board, flipped to Board 2, confirmed the three pinned notices and larger boss-sized first poster, and confirmed the detail panel changed to The Dealer’s Hand below the board. Prototype tests **12/12**, `node --check`, and the WSL production build pass. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 Merchant pixel sheet and counter occlusion — F-254 (2026-09-20)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-254 | P2 | Campaign v1 Market merchant | The first Merchant sprite read as a flat placeholder and sat in front of the counter. Its proportions were not a stable animation contract, the face lacked readable pixel shading, and the lower body competed with the furniture instead of being a character behind the stall. | Rebuilt the Merchant as a hand-authored 3-frame 24×32 palette sheet with bounded row/overlap validation, blink and coin-lift frames, warm face shading, pale mantle, teal robe, and a visible pouch/coin cue. The counter now owns the occlusion layer, so the lower body is hidden while the readable upper silhouette remains. CSS uses integer-step frame timing, fixed cell grids, overflow containment, and a bottom clip to prevent frame bleed. | Fixed / verified |

Verification: hostile Claude design gates reviewed the source contract and a fresh CUA screenshot. Gate 1 and Gate 2 rejected the earlier versions for lantern clearance, flat face color, and hidden commerce cues; Gate 3 passed after the 24×32 rebuild and counter layering. Prototype tests **15/15**, `node --check`, `git diff --check`, and the WSL production build pass. The live Market screenshot confirms the Merchant sits behind the table with the lantern clear and the pouch/coin cue above the counter. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 Home top-down room pass — F-255 (2026-09-21)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-255 | P1 | Campaign v1 Home | The first modular Home room still read like a straight-on stage: the floor treatment was too shallow, the central rug was elliptical, and the station props did not establish a clear overhead floor plan. The user clarified that this prototype is PC-only and the intended viewpoint is genuinely top-down, Stardew-like. | Reworked only the isolated prototype's room layer into a top-down floor plan. A wall strip and tiled floor are now CSS-built; the window, trophy shelf, armory chest, hearth, pantry cabinet, desk, plant, upgrade niche, rug, and Pyr each retain their own DOM/CSS footprint so future upgrades can replace one station without replacing a static image. Hotspots remain the existing stateful controls, aligned to the corresponding props; the Home actions, context panel, loadout, and progress data are unchanged. | Fixed / verified |

Verification: CUA visually inspected the live PC viewport at 1569×958 after a cache-busted reload. The screenshot shows the top-down wall/floor split, readable station placement, and unobstructed Pyr. Prototype tests **15/15**, `node --check`, `git diff --check`, and the WSL production build pass. Mobile viewport testing was intentionally excluded because this prototype is PC-only. No canonical Forge state, Supabase, progress files, or PTYs were touched.

## Campaign v1 Home room progression and achievement layer — F-256 (2026-09-21)

| ID | Priority | Surface | Finding | Resolution / evidence | Status |
|---|---|---|---|---|---|
| F-256 | P1 | Campaign v1 Home | Home needed a reason to grow beyond a static room: the learner had upgrade tokens but no authored homestead stations to spend them on, and memorable clears had no visible history. | Added a state-driven Room upgrades drawer with five authored builds: Reinforced Hearth (MAX HP +10), Warding Loom (failed-submission retaliation −2), Breaker Workbench (Guard Break impact +1), Siphon Basin (Guard Break heal +4), and Field Kitchen (meal heal +5). Added four read-only achievement plaques—First Mark, Clean Slate, Guardbreaker, and Dealer Down—whose unlocks are driven by campaign milestones rather than another currency. The room niche opens/closes the drawer and the first purchase visibly updates HP, max HP, tokens, and the built state. | Fixed / verified |

Verification: Desktop CUA visual checks at the live PC viewport confirmed the five cards, four plaques, scrollable page, and no overlap with the room. Building Reinforced Hearth changed `84/100` to `94/110`, consumed one token, and marked the card `BUILT · ACTIVE`. Prototype tests **18/18**, `node --check`, and the WSL production build pass. No canonical Forge/state/Supabase/PTY surfaces were touched.

## B-230 — Home prototype port parity and state bridge (2026-09-21)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Forge Homestead | The isolated top-down Home prototype had five room upgrades, four authored plaques, and live Hearth/Pantry/Pyr actions, but the first canonical port left some controls decorative and approximated plaque/Pyr state from loose counters. | Ported the room composition and drawer into canonical Forge, wired the Home action endpoint, normalized Pyr to authored bond thresholds/energy, made Armory browse reach the live loadout, and tightened plaque predicates to structured contracts/mobs with a narrow legacy fallback. | Fixed / published |

Verification: desktop CUA comparison against `prototypes/campaign-v1/?home-upgrades-v1=20260921b`; canonical state tests **49/49**; frontend Vite production build **1,347 modules**. Copilot performed two hostile read-only passes; all HIGH findings were repaired. Claude prototype critique passed its final visual gate; the canonical Claude CLI retry was blocked by an invalid global tool schema and is recorded rather than claimed as completed. `progress.json` and disposable challenge files were excluded from the published commit.
