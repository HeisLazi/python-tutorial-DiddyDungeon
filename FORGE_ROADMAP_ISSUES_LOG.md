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
| F-019 | P3 | Product completeness | The current screen has a deterministic starter question and checkpoint controls, but no adaptive generator, rest/market rooms, death UI, leaderboard or Practice history. | Open roadmap work; the missing pieces are documented in `INFINITE_DUNGEON_DESIGN.md` and the Forge handoff. |
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
| F-033 | P2 | WSL frontend packaging | WSL Vite cannot resolve the Linux Rollup optional package from the shared Windows `node_modules`; this is an environment/dependency-install issue, not a source failure. | Open: Windows `npm run build` is green; install Linux dependencies in a disposable WSL checkout before using WSL Vite builds. |
| F-034 | P2 | Secondary review | Claude Code remains unauthenticated in the WSL CLI despite the separate desktop login. | WSL CLI remains open, but an authenticated Claude browser review completed read-only against the current OneDrive checkout/archive. Its findings are recorded below; no external approval claim is made. |
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

The WSL Claude CLI still reports `Not logged in`. After the user re-authenticated
the browser, an authenticated review completed read-only; it is treated as
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

The post-fix automated counts are 55 WSL backend tests, 29 frontend tests and
a green Windows Vite production build. No Playwright was used.
