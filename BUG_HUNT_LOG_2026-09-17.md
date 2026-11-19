# Quest Lab end-to-end bug hunt — 2026-09-17

This is the persistent bug-hunt ledger for the original Forge redesign
contract. It is stored in the repository rather than a temporary runtime so a
workstation reset does not erase the findings.

## Scope and custody

- Branch: `feature/cloud-sync-desktop`
- Reviewed commit: `ed3452540b644ab22c218cba518fed1197bb542f`
- Protected files: repository `progress.json`, root Campaign `tutor.py`, root
  `dungeon.py`
- Protected save SHA-256 before and after the hunt: `2FD91A49C8B8828E2AC1914275DBCCADA3733188B960AD375B068BD6AB91E0A1`
- Test policy: in-app-browser keyboard/mouse/scroll/type and screenshots only;
  no Playwright, no DOM-driving scripts, isolated disposable state/workspace,
  no restart of pre-existing Forge processes or PTYs
- Scoring: P0=8, P1=5, P2=3, P3=1; +1 for a minimal reproduction; duplicates
  score zero and false positives subtract two

## Baseline and deterministic gates

The disposable runtime used a copied canonical cache and separate workspace on
unused ports (`7397` backend and `5195` frontend). The browser baseline showed
Level 3 / 120 XP / 75 coins, The Hitman at 8/8, three cleared mobs, all five
full-HUD monochrome SVG icons and both shell/AI PTY labels connected. A
synthetic Level 99 workspace `progress.json` was then created; the canonical
campaign projection stayed at Level 3 / 120 XP / 75 coins and the runtime
reported the workspace file as legacy/non-authoritative.

- Focused context bridge: **9/9**
- Full WSL backend suite: **97/97**
- Fresh disposable frontend suite: **37/37**
- Python `compileall`: passed
- Browser policy: no Playwright
- Root save, root `tutor.py` and root `dungeon.py`: not staged, reset or written

The original brief was re-read before this pass. The current local contract is
Hub-first navigation, splash/last-route continuity, chapter silhouettes,
Codex field-library pages and notes, Journal pagination, current shop/loadout,
state-owned Dungeon route selection, and one shared Tutor/Practice `tutor.py`
IDE with selectors. Practice has independent no-reward history but cannot
mutate Campaign/Dungeon progression.

## Findings

### BUG-2026-09-17-001 — P1 — fixed during hunt

- Reviewer: primary
- Surface: Tutor / Practice provider handoff (`ide/frontend/src/AppV2.jsx`,
  `ide/frontend/src/App.jsx`)
- Evidence: clicking AGY/Codex/Claude launched the AI PTY, but `Ask PYR for a
  drill` still stopped with “Launch Codex, Claude, or AGY first” because the
  tab-scoped `sessionStorage` provider marker was never set. The frontend test
  now asserts the marker write, provider read and bounded status message.
- Impact: a learner could open a provider but could not start a bounded drill,
  Battle or Dungeon request from that tab.
- Repair: provider launch records only the selected opaque provider name in
  `sessionStorage`; the PTY remains independently mounted. The follow-up
  K&M attempt then opened the Practice session and exposed the separate
  `tutor.py` context defect recorded below.
- Status: fixed; focused/frontend tests green.
- Score: 6 (P1=5 plus one minimal reproduction point)

### BUG-2026-09-17-002 — P2 — fixed during hunt

- Reviewer: primary
- Surface: Forge file tree / local-state authority (`ide/server/app_v2.py`)
- Evidence: a synthetic workspace `progress.json` appeared in the Forge file
  tree even though generic file access already rejected it and the campaign
  route correctly ignored its Level 99 projection.
- Impact: the visible row could make a legacy evidence file look like a second
  editable save and invite a split-brain edit.
- Repair: `build_tree()` now excludes `progress.json`; the context/tree test
  proves it stays hidden while canonical state remains authoritative.
- Status: fixed; focused/backend tests green.
- Score: 4 (P2=3 plus one minimal reproduction point)

### BUG-2026-09-17-003 — P1 — fixed during hunt

- Reviewer: primary
- Surface: Tutor / Practice PYR context bridge (`ide/server/app_v2.py`)
- Evidence: after the provider handoff was fixed, opening Practice and asking
  for a drill produced a 403 from `POST /api/pyr/context` because the bounded
  bridge treated the shared managed `tutor.py` as forbidden. The dedicated
  Tutor route was valid, but the provider never received the notebook context.
- Impact: the unified learning IDE could not deliver the bounded context that
  prevents answer leakage and supports examples/notes.
- Repair: the bridge permits a bounded read of the managed workspace
  `tutor.py`; generic `/api/file` and format routes still reject it, and all
  writes remain on `/api/tutor`.
- Status: fixed; focused context test now captures `tutor.py` successfully and
  the full backend suite is green.
- Score: 6 (P1=5 plus one minimal reproduction point)

### BUG-2026-09-17-004 — P3 — fixed during hunt

- Reviewer: primary
- Surface: roadmap/release documentation
- Evidence: current documents still said Practice could not write `tutor.py`,
  contradicting the settled product decision that Tutor and Practice share one
  managed notebook/editor with selectors and notes.
- Impact: future implementation/review work could remove the intended shared
  learning surface or reject valid bounded notebook writes.
- Repair: current normative sections in the roadmap, onboarding guide, report
  and issue ledger now state the shared-editor/no-reward contract while keeping
  older historical review entries intact.
- Status: fixed; documentation patch recorded and linked to F-074.
- Score: 1 (P3)

## Primary K&M surface coverage

The disposable Forge was exercised with browser K&M across Hub, Character,
Homestead, Quest Journal, Codex, Tutor/Practice, Infinite Dungeon and Settings.
The run covered the Hub contracts/weekly/chapter cards, full and compact HUD
icons, journal page controls, Codex search and note save, Homestead loadout and
SVG shop cards, Gruvbox Light selection, AI-terminal visibility, Dungeon
selector/rest/market/challenge/checkpoint flow, and Ctrl+Enter running
`tutor.py`. A direct state-service Dungeon verdict returned the next selector
without refresh, cleared the editor for the next room and kept both PTYs
connected. No other new P0/P1 defect was confirmed in those paths.

The first K&M Practice drill attempt intentionally captured BUG-003 before the
bridge repair. After the repair, the same disposable Forge was rehydrated
against the patched backend: clicking AGY then Ask PYR visibly produced
`Practice drill requested from agy`, the backend recorded `POST /api/practice/session`
and `POST /api/pyr/context` as **200 OK**, and both terminal WebSockets stayed
connected. The tree endpoint omitted `progress.json`, while direct generic
`/api/file?path=tutor.py` remained **403**.

## Reviewer scorecard

| Reviewer | Confirmed unique bugs | Weighted points | False positives | Duplicates | Result |
|---|---:|---:|---:|---:|---|
| Primary | 4 | 17 | 0 | 0 | local findings recorded |
| Claude Sonnet | 0 | 0 | 0 | 0 | invoked read-only; no response before bounded CLI timeout |
| Copilot | 0 | 0 | 0 | 0 | unavailable on this workstation |

The primary total is 17 (6 + 4 + 6 + 1). No reviewer claim is made for the
timed-out/unavailable tools.

## Disposable account / transfer recheck — 2026-09-17

A separate disposable Supabase account was used for account-scoped QA. The
profile/device registration succeeded. Two isolated SyncEngine clients both
downloaded the same Storage avatar, and a replacement uploaded by client A
was picked up by client B after the profile `updated_at` reference changed. A
separate temporary Git remote proved the allowlisted file channel transfers
`blackjack.py`, `tutor.py`, `dungeon.py`, and `notes/lists.md`; the target's
`progress.json` and session notes stayed byte-for-byte intact and
`notes/private.txt` was excluded.
Anonymous access to the QA avatar returned HTTP 400 and the profile read
returned HTTP 401, confirming the account-private boundary.

The same authenticated account also reproduced the remaining hosted gate:
the live player-state RPC rejected the source-reviewed campaign projection
with `next_state contains unsupported domains`. This is logged as F-079 in
the roadmap, not silently worked around. The campaign migration remains
source-only until the hosted migration approval gate is satisfied.

The in-app browser again timed out before attaching a tab to the isolated
runtime, so no new browser K&M score is claimed for this account pass. No
Playwright, user-save edit, or existing PTY restart was used.

## Browser attach recheck — exact-tip disposable runtime (F-080)

An exact-tip clean ext4 archive launched successfully on disposable ports
`7462/5262` with an explicitly migrated local cache; the guarded backend and
Vite server both reached ready state. The Codex in-app browser then timed out
waiting for its webview to attach before any click, key, scroll or typing
action. The runtime, temporary checkout and derived cache were stopped/removed,
so this remains an environment limitation and provides no new K&M claim.

## Sync-status copy recheck — 2026-09-17

The signed-in cache detail still described Projects and Codex as local even
after the campaign projection had been added to the shared revision/CAS
transport. This was a P3 release-copy defect (F-081), fixed by naming the
Campaign, Journal and Codex surfaces in `syncEngine.js`; the frontend
regression test now captures the emitted detail. The clean ext4 frontend suite
passed **41/41** and the production build transformed **1,346 modules**.

## Remaining gates

The local contract is not a hosted release claim. Provider-authenticated
adjudication, hosted/player-state two-device sync, explicit real-save custody,
the real CachyOS K&M run, friend-machine launch, Tauri packaging and hosted
social/weekly raids remain open gates. The hunt did not seed Supabase or alter
the protected save and did not reset a pre-existing shell or AI PTY.

## Follow-up slice — Dungeon map/code editor continuity — 2026-09-17

The original Dungeon brief requires a route selector that fades into a
question/editor workspace and returns to the map without losing the checkpoint.
The disposable Forge was exercised with browser K&M only: a challenge route was
chosen, the Code editor tab opened, a disposable `dungeon.py` buffer was typed
and saved through `PUT /api/dungeon/editor`, and Map & route was restored. The
accessibility tree showed the saved checkpoint, the route map and the hidden-
until-issued question boundary; the screenshot showed both tabs and the map.
Both shell and AI PTYs stayed connected and browser warning/error logs were
empty before teardown. This slice did not touch the protected root save or
pre-existing runtimes.

| Slice | Result | Evidence |
|---|---|---|
| Map → challenge → Code editor | passed | K&M showed `dungeon.py · current room buffer`, editable textarea and `Save checkpoint` |
| Checkpoint mutation | passed | Backend logged `PUT /api/dungeon/editor` 200 OK; status changed to `dungeon.py · checkpoint saved` |
| Code editor → Map & route | passed | Map retained Floor 1 / Room 4 and route cells after switching tabs |
| Runtime continuity | passed | shell and AI both showed `CONNECTED`; no PTY reset |
| Browser diagnostics | passed | no warning/error entries before disposable runtime teardown |

## Production build gate — 2026-09-17

The disposable Windows frontend tree built successfully with
`NODE_OPTIONS=--max-old-space-size=8192`: Vite transformed **1,346 modules** and
completed in 46.48 seconds. The default heap and a 4 GB heap both exhausted the
machine during Rollup; this is an environment memory limit, not a source
failure. The generated preview served HTTP 200 before teardown. The in-app
browser attach service did not provide a fresh tab for the preview, so no
production-preview K&M claim is made; the earlier dev-runtime K&M remains the
behavioral evidence.

The cloud-free two-device simulator also passed against the protected-save
digest: it advanced two disposable device revisions, rejected stale mailbox and
local pulls with `409`, applied an explicit `keep-device` resolution, and left
the source digest unchanged.

## Follow-up slice — adaptive Dungeon mob identity — 2026-09-17

The next disposable runtime rehydrated the current Dungeon checkpoint with the
patched state service. Browser K&M showed the state-owned current mob banner:
`The Boundary Hunter`, `bug hunt · Input loops and control flow`, `PHASE I`, and
`DIFFICULTY 1`. The selector still exposed no future mob names or questions;
only the issued encounter carried the descriptor. Shell and AI remained
`CONNECTED`, and browser warning/error logs were empty before teardown.
Backend tests cover the descriptor and verdict event (`97/97` total); the
frontend source suite is **39/39**.

## Native Linux launcher gate — 2026-09-17

The new `tools/questlab-launch.sh` wrapper passed `bash -n`, `--help`, the
launcher contract suite (**14/14**) and the full WSL backend suite (**98/98**).
It refuses an unexpected branch or stale upstream by default, keeps backend
reload disabled for PTY continuity, and forwards workspace/port/local-custody
choices to the module-safe Python launcher. This is tooling evidence only;
the actual CachyOS install and browser K&M run remain the F-058 external gate.

The live Windows OneDrive dependency tree was also rechecked after this slice:
`npm test` cannot resolve `@supabase/supabase-js` because that copied package
has no `package.json`. This is the existing F-033 mounted-dependency issue,
not a source regression; the disposable clean frontend tree remains the
authoritative **39/39** test and 1,346-module build evidence. No `npm install`,
save edit or runtime restart was performed in the live checkout.

## Campaign projection recheck — 2026-09-17

The cross-device projection was re-reviewed against the original report of a
Level/XP HUD arriving without the corresponding Journal/Codex state. The old
allowlist only sent player/equipment/companion/Homestead. This was a confirmed
P1 coherence defect, recorded as F-078: a cloud pull could not restore cleared
mobs, current Resolve, Codex encounter evidence, skills/goals or an active
Dungeon checkpoint.

Repair coverage is source-level and state-service-owned. Python now strips and
validates a bounded `campaign` projection; SyncEngine carries the same shape;
the unapplied SQL migration extends the row constraint and rejects unknown
domains/nested answer-bearing fields. A focused mutation test proved
`sync_apply_cloud` increments the revision/event while restoring project,
Codex and Dungeon data. The current protected save is **9,897 bytes** in the
campaign projection, below the 18,000-byte campaign cap.

No new visual/browser defect was scored in this slice. The live mounted
OneDrive JS dependency failure remains the known F-033 environment gate, and
hosted authenticated PC↔laptop acceptance remains unverified; no Supabase
write, save edit, or PTY restart occurred.

The read-only local sync simulator was extended to assert campaign continuity,
not just purse values. Against the protected save it retained 8 projects, 3
cleared mobs, 3 Codex encounters and the active Dungeon run/editor checkpoint
across both disposable caches, rejected stale mailbox/local revisions with
409, and left the source digest unchanged.

## Codex notes transport recheck — 2026-09-17

The campaign projection recheck found one remaining coherence edge: canonical
player-authored Codex notes (`player_notes`) were present in the local Codex
projection but omitted from the cross-device allowlist. A cloud pull could
therefore restore the encounter while silently dropping the learner's note.
This was scored as a **P1 extension of F-078** and fixed before publication.

The Python validator/source projection, browser SyncEngine, and unapplied
Supabase validator now all allow bounded `player_notes` arrays. The campaign
merge also updates sync-owned mapping fields without deleting local-only
`learning_state.last_teachback`. Regression coverage passed: backend **101/101**,
migration contracts **7/7**, clean frontend **40/40**, Vite **1,346 modules**,
and the protected-save two-device simulator retained the same campaign summary
with an unchanged source digest. No new browser defect was scored; hosted
authenticated sync and real CachyOS K&M remain external gates.

## Hosted-schema failure UX — 2026-09-17

The live RPC's `next_state contains unsupported domains` response previously
appeared as a generic cloud error. F-082 is fixed: SyncEngine now labels the
state `Cloud schema needs migration`, names the required migration, and leaves
the local outbox queued instead of implying data loss. The regression suite
passed **42/42** and the clean build transformed **1,346 modules**.

## Hunt follow-up — signed-in first-frame status copy (F-083)

The disposable-account recheck exposed one more presentation defect: the first
signed-in state said only Campaign fields would sync, then the account-record
callback changed the detail to Campaign, Journal and Codex. This was a status
copy transition, not a PTY or campaign remount, but it contributed to the
reported feeling that the sync UI was jumping. Both signed-in states now share
the same text, and the frontend regression rejects the stale phrase. Clean
frontend verification remains **42/42** with a **1,346-module** build.

## Distribution follow-up — native macOS onboarding (F-084)

The friend-facing guide lacked a native Mac path even though the existing
launcher only needs Python, npm and a local checkout. I added a guarded macOS
setup with a sibling quest workspace, executable-bit repair and stable-PTY
launch. No Mac machine was available for K&M, so this is a documentation fix,
not a native acceptance claim.

## Hunt follow-up — avatar cache custody (F-085)

Static account-flow review found that a signed-in upload wrote both the
account-scoped cache and the unscoped local avatar key. That could expose the
previous account's portrait after sign-out or make a remote removal appear to
fail. The SyncEngine now keeps signed-in caches scoped to the account and only
uses the unscoped key for explicitly anonymous/offline uploads. A regression
also proves a signed-in removal cannot resurrect an unscoped portrait. Clean
frontend verification passed **43/43** with the **1,346-module** build.

## Review follow-up — handoff precision (F-086/F-087)

The implementation was already safe, but the handoff wording was less precise
than the code. It now explicitly rejects caller-supplied `system` actors over
HTTP/CLI and describes Tutor/Practice as one managed `tutor.py`/notes surface
with separate Practice state rather than two notebooks. This was a
documentation-only repair; no save, runtime or PTY was touched.

## Shortcut follow-up — submit while the editor owns focus (F-088)

The original shortcut contract included `Ctrl/Cmd+Shift+Enter` for submitting
the current run to PYR. The legacy enhancement listened during the normal
bubble phase, so Monaco could consume the key event first and insert its own
newline/command while the cursor was inside a Python editor. The capture-phase
shortcut boundary in `AppV2.jsx` now prevents that insertion and clicks the
existing bounded `data-qol-submit` bridge. The fallback clipboard behavior and
provider guard remain unchanged.

Regression evidence: the mounted Forge source test passed **26/26**; a clean
ext4 checkout passed the full frontend suite **44/44** and the production Vite
build. No browser/runtime was restarted, no user PTY was touched, and the
protected save hash remained unchanged.

## Disposable hosted-account creation recheck — 2026-09-17 (F-089)

The requested fresh Codex-owned QA identity could not be created in this pass:
the configured Supabase Auth project returned HTTP **429**
`over_email_send_rate_limit` before returning a user or session. The request
used a newly generated mailbox-backed address; no service/admin key, rate-limit
bypass, or personal account was used. The mailbox was disposable and no
password or token was written to the repository.

This is an external provider gate, not evidence of an application defect. The
previous disposable account QA remains the valid hosted portrait evidence, and
the local equivalents still pass: avatar/account-boundary source coverage,
campaign sync simulator (unchanged protected-save digest), workspace transfer
**7/7**, cloud migration contracts **7/7**, and the mounted Forge regression
suite **26/26**. No user save, source file, or existing PTY was touched.

## Handoff contract recheck — 2026-09-17 (F-090)

`FORGE_V2_HANDOFF.md` had fallen behind the current source: it described
Practice as unable to use the managed `tutor.py` notebook, called Dungeon and
Practice starter-only, and described combat as display-only. The implementation
already has the shared Tutor/Practice notebook boundary, local state-owned
Dungeon loop, Practice history and provider-validated local verdict mutations.
The handoff was aligned with those facts and continues to mark provider auth,
hosted campaign/Dungeon transport and real PC/laptop acceptance as open gates.

## Sign-up quota feedback — 2026-09-17 (F-091)

The real disposable-account attempt exposed a copy/privacy issue rather than
an authority bug: Forge would surface Supabase's raw
`over_email_send_rate_limit` string. `SyncEngine` now maps that bounded error
to “Email delivery is temporarily rate-limited. Try again later; no account was
created.” while retaining the safe error code for diagnostics. The new
regression and clean ext4 frontend suite (**45/45**) pass; no account retry or
provider bypass is performed.

## UI coherence and Dungeon loadout hunt — 2026-09-17 (F-092–F-097)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-092 | P2 | The navigation exposed Practice and Tutor as two destinations even though both use the managed `tutor.py` notebook. | Fixed by removing the Practice rail item and normalizing legacy `practice` route/storage values to `tutor`; the Practice screen remains an internal compatibility path only. |
| F-093 | P1 | Hiding AI with visibility alone left an empty right-hand grid column and made the layout jump between routes. | Fixed with a parked off-canvas AI surface that stays mounted for PTY continuity, plus an explicit non-blocking pop-out toggle on Hub, Codex, Journal, Homestead and Settings. |
| F-094 | P1 | Quest Journal's two-column shell left the Main Quest page compressed against a blank panel. | Fixed with a full-width journal page override while preserving the page-turn controls and the second contracts page. |
| F-095 | P1 | The active Forge campaign file did not show the current enemy Resolve panel when the encounter had no objective list. | Fixed by rendering the state-service encounter and Resolve meter whenever a mob projection exists. |
| F-096 | P2 | Dungeon Run Loadout was display-only; items purchased during a run could not be reviewed or re-equipped. | Fixed with a bounded canonical inventory projection, state-gateway `dungeon_equip_item` mutation and inventory menu. |
| F-097 | P2 | Boot had no fade-out and did not distinguish a long-away return from an initial welcome. | Fixed with an animated splash in/out path and `Welcome back, <username>` after the 20-minute return threshold. |

Verification: clean ext4 frontend **47/47**, Vite production build (**1,346
modules**), mounted Forge source tests **28/28**, and backend syntax/full suite
**101/101**. Browser K&M could not be freshly attached in this environment, so
these findings are source/API/build verified rather than a new live-browser
claim. Existing shell and AI PTYs were not restarted.

## Character, Homestead and Battle workspace follow-up — 2026-09-17 (F-098–F-100)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-098 | P2 | Character/Homestead still inherited the IDE rail/context/AI grid even though they are presentation surfaces that need the same full-width treatment as Hub. | Fixed with a shared wide-surface layout for Hub, Character and Homestead; AI remains mounted but hidden/off-canvas unless explicitly opened. |
| F-099 | P1 | Quest Journal embedded the Battle submission shell inside the Main Quest page, competing with the journal's page layout. | Fixed with a second Journal screen, Battle shell, alongside Journal pages; the state-service encounter and boss gates remain the same. |
| F-100 | P1 | The Journal answer field was a compact sidebar-style textarea, not a comfortable campaign-sized writing surface. | Fixed with a dedicated Battle workspace and large code-friendly answer editor for objective/boss evidence. |

The new Battle screen preserves the bounded provider submission path and never
reveals future questions or answer keys. PTYs and canonical state ownership were
not changed.

## React combat-surface ownership follow-up — 2026-09-17 (F-101)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-101 | P1 | The legacy combat DOM observer still injected a second Battle Shell after the React Journal rendered and could rewrite Character equipment markup on every revision. | Fixed by making React the sole owner of these surfaces; the compatibility observer now only removes stale legacy nodes. |

This was a visual/state-polling coherence bug. It did not mutate canonical
progress, but it made live updates appear to jump and contradicted the new
Journal/Battle screen split.

## Boss phase and trinket trigger hunt — 2026-09-17 (F-102)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-102 | P2 | Boss requirement verification lived only in the short-lived provider challenge, and the documented trinkets had no state-service effect. A refresh could hide a phase already accepted by PYR, while a trinket could be shown without an auditable trigger. | Fixed locally with a canonical `record_boss_requirement` event/projection and bounded Ember Scythe, Guardian Sigil and Phoenix Ember triggers. Hosted auth/schema application remains unverified. |

## Campaign loadout hunt — 2026-09-17 (F-103)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-103 | P2 | Homestead showed the currently equipped campaign gear but did not expose a safe inventory/equip path. A naive browser catalogue would reveal future loot or allow React to invent ownership. | Fixed with a canonical, bounded equipment projection. Only the current legacy value or state-recorded owned IDs reach React; `equip_equipment` is player-authorized, unlocks are trusted internal events, and each real change increments the revision and creates a state event. |

The clean staged frontend suite passed **49/49** and the Vite build transformed
**1,346 modules**. WSL backend discovery passed **105/105**. No protected save,
workspace file, cloud migration or PTY was changed by the verification run.

## Wide-route navigation hunt — 2026-09-17 (F-104)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-104 | P1 | The full-width Hub/Character/Homestead presentation removed the activity rail but did not provide an alternate route bar, leaving Homestead and Hub as navigation dead ends. | Fixed with a compact, horizontally scrollable navigation bar rendered inside the wide surface. It includes Hub, Forge, Tutor, Journal, Codex, Character, Homestead, Dungeon and Settings, with active-route and keyboard-accessible states. |

No canonical state, PTY, cloud transport or personal workspace file was changed.

## Navigation icon consistency hunt — 2026-09-17 (F-105)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-105 | P3 | The ActivityRail still used legacy glyph/emoji values while the new wide route bar used SVG icons, leaving the route chrome inconsistent and vulnerable to another blank-icon regression. | Fixed by routing both navigation surfaces through the same inline monochrome `RouteIcon` map and adding direct SVG sizing/stroke rules. |

Staged frontend tests passed **49/49** and the production build transformed
**1,346 modules**. This was a presentation-only change; canonical state,
cloud transport and PTY lifecycles were untouched.

## React navigation ownership hunt — 2026-09-17 (F-106)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-106 | P2 | The legacy MutationObserver-based icon bridge could rewrite the React ActivityRail after a revision or route render, competing with React and making the icon rail susceptible to layout churn. | Fixed with a `data-react-owned` rail boundary. The legacy enhancer exits for that rail while retaining its compatibility path for older markup. |

Verification: staged frontend tests **50/50**, WSL backend **105/105**, and
Vite production build **1,346 modules**. No canonical save or PTY was touched.

## Friend bundle protection hunt — 2026-09-17 (F-107)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-107 | P2 | `questlab-package.ps1` refused the ordinary learner checkout because untracked `dungeon.py` is protected workspace data, even though the bundle archives `HEAD` and should omit it. | Fixed the dirty-tree allowlist for `dungeon.py` and untracked `notes/`; committed source edits remain fail-closed and the archive still comes only from `git archive HEAD`. |

The launcher contract regression passes. The post-commit package smoke created
`QuestLab-ed8db52` from `git archive HEAD`; `tutor.py`, `dungeon.py` and
`notes/` were absent, and the bundled baseline `progress.json` matched the
`HEAD` blob instead of the dirty local cache.

## Wide-route callback compatibility hunt — 2026-09-17 (F-108)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-108 | P1 | The alternate/legacy `App.jsx` shell rendered the new wide-route bar but did not pass its `setActiveView` callback into `GameScreen`, so Hub/Homestead buttons could look present while leaving the player on the same page. | Fixed by wiring `onNavigate={setActiveView}` through the legacy shell and adding a regression assertion. |

The patch is presentation/navigation-only: no campaign state, cloud transport,
protected learner files or PTY lifecycle changed.

Verification after publication: current-source navigation tests **32/32**,
clean ext4 frontend suite **51/51**, WSL backend suite **105/105**, and a
fresh Vite production build with **1,346 modules transformed**. The Codex
browser still could not attach a fresh tab, so no new live click-through claim
is made here.

## Dungeon inventory cloud projection hunt — 2026-09-17 (F-109)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-109 | P1 | The local Dungeon checkpoint persisted run-earned inventory, but the browser campaign projection and hosted campaign migration omitted `dungeon_run.inventory`; a second device could resume the room while losing its temporary loadout. | Fixed by adding a bounded inventory whitelist to the SyncEngine projection and the source-only SQL validator, with a two-device cloud round-trip regression. |

Verification: clean ext4 frontend tests **51/51**, Vite production build
**1,346 modules**, focused backend/migration tests **51/51**, and the full WSL
backend suite remains **105/105**. The hosted migration is still unapplied by
the Milestone C boundary.

## Wide-route navigation visibility hardening — 2026-09-17 (F-110)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-110 | P2 | The wide Hub/Character/Homestead route bar was present, but its affordance could disappear from context in a long surface or be difficult to identify in a mixed/stale bundle, making the full-width pages feel like dead ends. | Fixed by giving the route frame an explicit active-route marker, keeping the navigation strip sticky and above the surface content, preserving touch-sized targets, and retaining the direct React callback. |

Verification: the current-source Forge runtime suite passes **32/32**. A fresh
browser K&M click-through remains unavailable because no Codex browser tab could
attach in this environment.

## Codex quest/battle merge hunt — 2026-09-17 (F-111)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-111 | P1 | Quest Journal split the active chapter, encounter progress and Battle Shell across a separate route, so the learner had to leave the Codex to understand the current quest or submit the live encounter. | Fixed by normalizing the legacy `quests` route to Codex, moving Active Quest/chapter/encounter context into the Field Library sidebar, and adding Books/Battle Shell tabs with a page-turn surface. Battle Shell story, stats, Resolve and submission props remain state-service sourced; locked chapters and future encounters stay silhouettes. |

Verification: current-source Forge runtime tests **32/32**, clean ext4 frontend
tests **51/51**, and Vite production build **1,346 modules transformed**.
Browser K&M could not be run because the Codex environment had no attachable tab.
Protected learner save/files and both PTY lifecycles were not touched.

## Battle Shell encounter binding hunt — 2026-09-17 (F-112)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-112 | P1 | The new Battle Shell derived its Question Lens from `encounter`, but the component did not receive that projection as a prop. A real tab render would have thrown before showing the page. | Fixed by binding the same canonical encounter projection into the legacy-compatible and Codex Battle Shell call sites, plus a source regression assertion. No fallback reward or question data was invented. |

Verification after the repair: current-source tests **32/32**, clean ext4
frontend tests **51/51**, and Vite production build **1,346 modules transformed**.

## Codex bounded reading workspace hunt — 2026-09-17 (F-113)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-113 | P1 | Codex stacked the library, selected entry, notes and Mastery cards in the global Forge page scroller. The result felt like an unbounded feed instead of a readable field-library/book surface. | Fixed with a bounded Codex shell: the page header/tabs stay fixed, the Active Quest/books index and book detail each own their scroll, and Mastery Signals live inside the selected book pane. The narrow layout falls back to a single controlled column. |

Verification: current-source Forge tests **32/32**, clean ext4 frontend tests
**51/51**, and Vite production build **1,346 modules transformed**. The local
K&M browser attempt was blocked because the Codex Browser webview had no
attachable tab; no visual click-through claim is made.

## Stale Quest Journal command hunt — 2026-09-17 (F-114)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-114 | P2 | The visible command palette still offered “Open Quest Journal” even though the rail and router had moved that surface into Codex. The command could not find a matching rail button and made the merge feel incomplete. | Fixed by removing the stale command and keeping Codex as the single navigation target. The legacy icon alias remains only as a compatibility fallback for old markup. |

Verification: current-source Forge tests **32/32**. No campaign state, PTY or
cloud transport was changed.

## Codex infinite-scroll regression hunt — 2026-09-17 (F-115)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-115 | P1 | The first bounded Codex pass still left Mastery Signals as a permanent page-length tail, and the shell used a flexible column that could grow with book evidence in smaller Forge viewports. | Fixed with explicit Codex grid rows, a compact fixed hero, contained pane overscroll, and an expandable Mastery Signals section. The book index and selected book remain the only scrolling regions on desktop; mobile intentionally falls back to one controlled page. |

Verification: current-source Forge runtime tests **32/32**, clean ext4-style
archive frontend tests **51/51**, and Vite production build **1,346 modules**.
The existing Windows `node_modules` tree still has a locked esbuild binary, so
the clean archive was used for dependency/build proof; protected learner files
and PTYs were not touched.

## Codex book-section overflow hunt — 2026-09-17 (F-116)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-116 | P1 | Even after the bounded shell, the selected concept page still appended examples, evidence, notes and mastery into one long reading column. The result looked like an infinite feed and buried the actual book content. | Fixed by splitting the selected book into Read, Encounters, Notes and Mastery sections. Only one section is visible at a time; the index and book remain bounded panes, and all content remains projection-backed. |

Verification: current-source Forge runtime tests **32/32**. The clean archive
frontend suite/build and browser K&M remain the next publication checks; no
state, learner file or PTY was touched.

## Forge workspace-transfer UI hunt — 2026-09-17 (F-117)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-117 | P1 | The reviewed `questlab-files` source-transfer helper existed only as a CLI workflow, so a learner could not safely inspect or transfer `blackjack.py`, `tutor.py`, `dungeon.py` and notes from Forge itself. | Fixed by adding a Settings panel backed by the existing helper. Push/pull uses explicit confirmation tokens, redacts local paths, previews conflicts, creates a backup before overwrite, and never transfers `progress.json`, PTYs or private logs. |

Verification: focused WSL API tests **10/10** and current-source Forge runtime
tests **32/32**. This remains source-file transfer only; it does not claim
hosted player-state sync.

## Compact Codex outer-scroll regression — 2026-09-17 (F-118)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-118 | P1 | The narrow-window Codex fallback restored `height: auto` and visible outer overflow, so compact Forge windows still behaved like an infinite page even after the desktop pane was bounded. | Fixed by keeping the Codex shell at the Forge viewport height at every width. The narrow layout stacks the index above the book, but only those controlled panes own scroll; the Battle Shell keeps its own bounded scroll. |

Verification: current-source Forge runtime tests **32/32** and CSS regression
assertions reject the old outer-scroll fallback. Browser K&M remains the
environment-gated visual check.

## Account portrait projection hunt — 2026-09-17 (F-119)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-119 | P1 | Avatar sync updated a DOM enhancement listener, but the React-owned ActivityRail/Character surfaces still rendered initials. A signed-in portrait could therefore exist in the account cache while the visible Forge UI stayed stale or was rewritten on a revision render. | Fixed by carrying the validated avatar data URL in the local SyncEngine view state, rendering it directly in React on the rail and Character sheet, and making the legacy enhancer yield to those ownership markers. Account-scoped cache fallback and cloud upload/remove boundaries remain unchanged. |

Verification: current-source Forge runtime tests **32/32**. Real PC/laptop
account portrait round-trip remains the user-owned hosted acceptance gate.

## Codex finite-book navigation hunt — 2026-09-17 (F-120)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-120 | P1 | The Codex pane was bounded, but the selected book still read as a long scroll and had no next/previous book controls. On smaller windows the mobile override could also restore a book-level overflow owner, recreating the reported infinite-scroll feel. | Fixed by making the book page a fixed shell, giving only the active book section a contained scroll, adding previous/next book controls with an explicit position indicator, and animating page turns when the book or section changes. The narrow override now keeps the same bounded ownership. |

Verification: current-source Forge runtime tests **32/32**. Clean archive
frontend tests/build and browser K&M remain the publication checks; no state,
learner file or PTY was touched.

## Stale frontend bundle pairing hunt — 2026-09-17 (F-121)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-121 | P1 | The launcher already exposed backend branch/HEAD health, but a stale Vite frontend could be paired with a newer backend without an explicit frontend/backend identity check. That made an older Codex layout look like a live current build. | Fixed by having the guarded launcher pass the checkout HEAD SHA to Vite, embedding it in the bundle, comparing it with `/api/runtime` in React, exposing diagnostic data attributes, and showing `FRONTEND STALE · restart current launcher` in the footer. Unmarked manual Vite runs retain the existing branch/runtime warning path. |

Verification: current-source Forge runtime tests **33/33** and launcher
contract tests **14/14**. Clean archive frontend tests/build and browser K&M
remain the publication checks; no state, learner file or PTY was touched.

## Codex paper-surface polish hunt — 2026-09-17 (F-122)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-122 | P2 | The finite Codex behavior was correct, but the page still read like a dense dark dashboard: code examples ignored the selected theme, headings stayed monospaced, and the book/index hierarchy lacked a calmer paper surface. | Fixed with scoped Codex-only paper gradients, themed example blocks, clearer inherited display typography, softer page/index hierarchy and restrained book shadows. The finite layout and single contained scroll owner are unchanged. |

Verification: current-source Forge tests **34/34**. Clean archive frontend
tests/build and browser K&M remain the visual publication checks; no state,
learner file or PTY was touched.

## Codex outer-feed regression hunt — 2026-09-17 (F-123)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-123 | P1 | The Codex could still participate in the parent game surface's size calculation, and each book section retained its own vertical overflow. In a compact or stale layout this read as an endless dashboard instead of a finite book with deliberate page controls. | Fixed by making the Forge game surface a bounded positioning context, pinning the Codex shell to that viewport, and removing vertical overflow from book sections. The Field Library index remains the only scrollable book navigation pane; page/section changes stay finite and explicit. |

Verification: current-source Forge runtime tests **35/35**. Clean archive frontend
tests/build and browser K&M remain the visual publication checks; no state,
learner file or PTY was touched.

## Account sync diagnostics hunt — 2026-09-17 (F-124)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-124 | P1 | The account panel only surfaced a broad sync label and queued text. It did not show the local campaign revision or cloud cursor, so a stale Level/XP display could not be distinguished from an unresolved queue, conflict or hosted-schema gate. | Fixed with three read-only diagnostic cells sourced from the existing App revision and SyncEngine state. No write path was added and no player state was inferred. |

Verification: current-source Forge tests **36/36**. Clean archive frontend
tests/build and browser K&M remain publication gates; hosted two-device sync
is still external evidence.

## Workspace transfer verification hunt — 2026-09-17 (F-125)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-125 | P1 | Forge hid the local/remote hashes already produced by the transfer gateway. A player could see “different” but not which file was stale or whether protected changes were excluded before applying a pull. | Fixed with digest prefixes, mismatch feedback, reviewed-edit count and excluded-change count. The preview, confirmation and overwrite gates remain explicit. |

Verification: current-source Forge tests **37/37**. Clean archive frontend
tests/build and browser K&M remain publication gates; actual device round-trip
is still external evidence.

## Codex outer-feed follow-up — 2026-09-17 (F-127)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-127 | P1 | The visible Codex still inherited the generic `game-screen-scroll` wrapper. That left two competing layout contracts: a page-level feed and the finite book grid. Depending on the bundle/window, the result could look like an ugly endless scroll even though the state projection was correct. | Fixed by removing the generic wrapper class from the Codex root, pinning a dedicated shell to the game viewport, containing overscroll, and making the selected book section (plus the Field Library index) the only intentional scroll owners. |

Verification: current-source Forge tests **38/38**. No state, learner file,
PTY or hosted transport changed. Fresh browser K&M remains unavailable because
the Codex in-app browser tab could not attach in this environment.

## Dev HMR terminal retention — 2026-09-17 (F-035)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-035 | P3 | A Vite Fast Refresh could tear down the React terminal effect and close a live WebSocket, making a source edit look like a PTY reset even though the backend process was healthy. | Fixed in source: shell and AI sessions are stored in a browser-global role registry. Component effects only attach/detach xterm consumers; a 2-second grace period closes a session only when no replacement consumer arrives. The state/reconnect path remains role-bound and revision polling is unchanged. |

Verification: current-source Forge tests **39/39**. A clean archive build is
required before publication; fresh browser-HMR K&M is still environment-gated
by F-080 and is not claimed here.

Recheck after implementation: clean archive frontend tests **58/58**, Vite
production build **1,346 modules**, and WSL backend discovery **108/108**. The
local sync simulator returned `ok: true`; the protected source save digest was
identical before and after. These checks do not replace browser-HMR K&M.

## Legacy Codex shell parity — 2026-09-17 (F-129)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-129 | P2 | The Codex viewport boundary only matched the `forge-v2` class, but the compatibility App shell renders the same game surface without that class. That left a stale/legacy shell capable of bringing back the outer feed. | Fixed by scoping the pinned Codex shell to the shared `.game-screen > .codex-screen` contract. Both shells now use the same contained library/book scroll owners. |

Verification: current-source Forge tests **39/39**. The change is presentation
only; clean archive build and fresh browser K&M remain gates.

Recheck: clean archive frontend tests **58/58** and Vite production build
**1,346 modules** passed after the shared-shell selector change. No state,
learner file or PTY was touched.

## Codex finite reading-room follow-up — 2026-09-17 (F-130)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-130 | P1 | The previous outer-feed repair still left the entire Field Library column as a scroll owner. As chapter context and concept books accumulated, that layout could still read as an ugly infinite scroll rather than a finite book with fixed controls. | Fixed in source with an explicit height-bounded Codex grid: header and mode tabs stay fixed, the index is a flex column, only its concept list scrolls, and the selected book section is the sole reading-content scroller. |

Verification: current-source Forge runtime tests **40/40**. Browser K&M remains
the visual publication gate; no state, learner file, PTY or hosted transport was
changed.

## Secondary RPG emoji fallback — 2026-09-17 (F-132)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-132 | P2 | Codex mastery and companion/Homestead surfaces still used emoji glyphs, so their shape, baseline and color changed with the host font even after the HUD SVG repair. | Fixed by rendering shield/flame/book icons through `RouteIcon` and applying explicit monochrome SVG sizing/strokes. |

Verification: current-source Forge runtime tests **42/42**, clean archive
frontend tests **61/61**, Vite build **1,346 modules** and WSL backend tests
**108/108** passed. Visual browser K&M remains unavailable in this environment;
no state, learner file, PTY or hosted transport changed.

## Friend bundle tracked-save leak — 2026-09-17 (F-131)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-131 | P1 | A clean package audit showed `progress.json` in the friend folder and ZIP because it is tracked at `HEAD`; the previous dirty-tree guard only protected uncommitted saves. That could distribute one player's starter/current cache and undermine the single-state authority boundary. | Fixed in source: the packager strips tracked `progress.json`, `tutor.py`, `dungeon.py` and `notes/` from a temporary staging tree, verifies none remain, and updates the onboarding/manifest wording. |

Verification: the pre-fix disposable audit reproduced the leak. Post-fix
`QuestLab-2f5a4fe` folder/ZIP scans returned **NONE** for all protected paths;
the manifest and key onboarding/launcher files were present. Clean archive
frontend tests/build passed **60/60** and **1,346 modules**. The live save and
PTYs were not touched.

## Codex bookshelf and reading-room hierarchy — 2026-09-17 (F-133)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-133 | P1 | The Codex no longer grew the outer Forge page, but its left concept index still behaved like a dense continuous feed and its page selection was visually noisy. A no-result search also rendered the full library again, which made the “infinite scroll” complaint valid. | Fixed with a finite five-book shelf pager, explicit selected-page treatment, a quieter paper/spine reading frame, and monochrome SVG chapter/encounter markers. Search now keeps a real empty result instead of silently reverting to every book. |

Verification: current-source Forge runtime tests **43/43**; clean Linux archive
frontend tests **62/62** and Vite build **1,346 modules**. Browser K&M is still
blocked by the Codex in-app webview attach failure (F-080), so no visual pass
is claimed from automation.

## Character/Homestead icon parity — 2026-09-17 (F-134)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-134 | P2 | Character equipment, achievement badges and Homestead props still mixed in font-dependent symbols with the HUD/Codex SVG icon system, so the same RPG item could shift shape and baseline across hosts. | Fixed by using `RouteIcon` for armor, trinket, character, achievement and Homestead props, adding spark/window paths, and applying explicit monochrome SVG sizing/strokes. |

Verification: current-source Forge runtime tests **44/44**, clean archive
frontend tests **63/63**, and Vite build **1,346 modules** passed. Browser K&M
remains blocked by F-080; no save, learner file, PTY or hosted transport changed.

## Codex fixed-page evidence reader — 2026-09-17 (F-135)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-135 | P1 | Encounter evidence and note targets were all rendered in the selected book body. As the library grew, that could recreate the same endless-feed feel and move the page controls out of view. | Fixed with a viewport-bounded book frame, one deliberate scroll owner for the selected page body, and explicit three-record paging controls shared by Encounter and Notes sections. The canonical projection and selected-record detail remain state-owned. |

Verification: current-source Forge runtime tests **45/45**, clean archive
frontend tests **64/64**, and Vite build **1,346 modules** passed. Browser K&M
remains blocked by F-080; no save, learner file, PTY or hosted transport changed.

## Route/quest/Dungeon SVG marker parity — 2026-09-17 (F-136)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-136 | P2 | Hub chapters, quest objectives, mob paths, boss phases and Dungeon map/room markers still used font glyphs beside the corrected HUD/Codex SVG system. | Fixed with shared `RouteIcon` status markers and explicit SVG sizing/strokes for route, quest and Dungeon surfaces. |

Verification: current-source Forge runtime tests **46/46**, clean archive
frontend tests **65/65**, and Vite build **1,346 modules** passed. Browser K&M
remains blocked by F-080; no save, learner file, PTY or hosted transport changed.

## Codex active-quest rail still felt like an infinite feed — 2026-09-17 (F-137)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-137 | P1 | Eight chapter buttons sat beside the bookshelf in the same left rail. Even with the finite shelf and page body, the active-quest area dominated the Codex and read like another growing scroll column. | Fixed with a native bounded chapter selector and a compact state-owned mob summary. Removed the obsolete chapter-list rules and kept chapter lock/current/completed labels in the selector options. |

Verification: current-source Forge tests **47/47**; clean archive frontend
tests **66/66** and Vite build **1,346 modules**. Browser K&M remains blocked by
F-080; no state, learner file, PTY or hosted transport changed.

## Partial OneDrive frontend dependency cache — 2026-09-17 (F-138)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-138 | P2 | A live Windows/OneDrive dependency tree was only partially installed after an interrupted cross-environment install. Missing Supabase metadata caused two frontend test files to fail import; missing Vite shims/native Rollup metadata blocked the build. | Repaired the local cache from the locked package graph without stopping the existing Forge/PTY runtimes. Added a launcher preflight that checks the required package manifests and native Rollup metadata and reports the correct repair path. |

Verification: Windows frontend tests **66/66**, Windows Vite build **1,346
modules**, focused launcher tests **15/15**, and WSL backend tests **109/109**.
No protected save, learner file or PTY was changed.

## Codex folio overflow follow-up — 2026-09-17 (F-139)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-139 | P1 | The Codex had shelf/record pagers, but the selected book body still exposed a full-height scrollbar. That left the exact “infinite scroll” feel the user reported, especially in compact Forge windows. | Fixed by making each visible book section a bounded folio page, paging mastery records four at a time, and keeping only the small workspace-note box scrollable when its content is long. |

Verification: Windows frontend tests **67/67** and Vite build **1,346 modules**.
No protected save, learner file, PTY or state-service behavior changed. Browser
K&M remains environment-blocked by F-080.

## Hosted campaign migration preflight — 2026-09-17 (F-140)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-140 | P1 | The linked Supabase project still has the older schema. The remote ledger lacks the committed device-ownership and campaign-projection migrations, so hosted campaign writes cannot yet prove Milestone C. | Read-only migration listing and `db push --dry-run --skip-vault` confirmed exactly two pending files: `20260916000100_player_state_device_ownership.sql` and `20260917000100_player_state_campaign_projection.sql`. No migration, seed or player-state write was performed. |

This is a real hosted-state gate, not a local test failure. Approval is required
before applying the two migrations and running authenticated two-device tests.

## Codex folio still inherited the legacy feed height — 2026-09-17 (F-141)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-141 | P1 | The Codex had finite shelf and record controls, but `.codex-library` still carried the old 520px minimum height. That could push the selected book outside the Forge viewport and make the UI feel like an infinite scroll page. | Fixed with a compact field-library header and final `min-height: 0`/`height: 100%` constraints on the tab page, library, index, book page and visible section. The existing pagers remain the only way to move through growing evidence. |

Verification: Windows frontend tests **68/68** and Vite build **1,346 modules**.
No protected save, learner file, PTY or state-service behavior changed. Browser
K&M remains environment-blocked by F-080.

## Raw hosted migration command lacked a fail-closed guard — 2026-09-17 (F-142)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-142 | P1 | The hosted campaign migration was approval-gated, but the documented next step could still be run as a raw `supabase db push`, without proving the remote ledger and dry-run matched the two committed files. | Added `tools/questlab_supabase_migrate.py`. The default run performs only the linked ledger check and dry-run. Unexpected pending migrations or a missing dry-run entry abort. A real push requires the exact `APPLY_QUESTLAB_CAMPAIGN_MIGRATIONS` confirmation token. |

Verification: guarded read-only run **GREEN**, focused tests **5/5**. No
Supabase write, seed, save or PTY change occurred.

## Codex primitive still carried a feed-sized minimum — 2026-09-17 (F-143)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-143 | P1 | The shared `.codex-library` rule still declared `min-height: 620px`. Later overrides normally bounded it, but that stale primitive could win in a compatibility/cascade path and recreate the infinite-scroll layout. | Changed the shared primitive to `min-height: 0` and added a frontend regression assertion for the exact rule plus a guard against 5xx/6xx minimum heights. |

Verification: Windows frontend tests **69/69** and Vite build **1,346 modules**
passed. No protected save, learner file, PTY or hosted state was touched; browser
K&M remains environment-blocked by F-080.

## Strict friend packaging rejected a protected nested checkout — 2026-09-17 (F-144)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-144 | P2 | The packager stopped on the user-owned untracked `/` nested checkout before it could create a friend bundle. Deleting, moving or staging that protected directory was out of scope. | Added exact-path `-IgnoreUntrackedPath`; it validates the path is inside the repo and untracked, while `git archive HEAD` remains the only bundle source. Unknown dirty source still fails closed. |

Initial reproduction was a safe failed package attempt; no bundle or protected
file was written. After the fix, the exact-path package run produced a
134-entry ZIP from `83f302c` with all protected paths absent.

## Fresh ext4 distribution verification — 2026-09-17 (F-033/F-058)

No new defect was found. A disposable WSL ext4 clone installed fresh Python
and frontend dependencies, passed frontend **69/69**, Vite (**1,346 modules**)
and backend **115/115**, then was removed and verified absent. The physical
CachyOS and live K&M/PTY gates remain unverified rather than being inferred
from this clean-filesystem run.

## Native Linux acceptance had no one-shot environment report — 2026-09-17 (F-145)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-145 | P2 | CachyOS acceptance required manually collecting kernel, toolchain, checkout and native dependency identity before the live run. | Added read-only `tools/questlab-native-report.py --strict`; it fails closed on branch/upstream or native dependency mismatch and never writes state. |

The report is a pre-launch evidence aid, not a substitute for the physical
CachyOS live-projection/PTY test. Contract coverage passed **17/17** and a
strict clean-ext4 report returned **GREEN** with native Rollup present; the
temporary clone was removed afterward.

## Codex reader still looked like an infinite dashboard — 2026-09-17 (F-146)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-146 | P1 | The previous height fixes bounded the Codex mathematically, but the UI still carried dense dashboard styling and several competing cascade contracts. The result could look like an ugly infinite scroll even when the shelf and record pagers existed. | Fixed with one final reader contract: a compact Codex header, short Books/Battle Shell tabs, a two-pane fixed folio, a bounded active-quest rail, a five-book shelf with visible page controls, and no outer Codex scroll. Only the small mobile index, code examples and intentionally long note body may scroll. |

Verification: Windows frontend tests **70/70** and Vite build **1,346 modules**
passed. No player state, learner file, PTY or hosted migration was touched.
Fresh browser K&M remains blocked by F-080, so this is not presented as a
device-level visual claim until an attachable Forge tab is available.

## Codex reader chrome still looked assembled from dashboard cards — 2026-09-17 (F-147)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-147 | P2 | The finite Codex structure was correct, but the visual hierarchy still mixed dense metric cards, generic panel backgrounds and dashboard-like book controls. That made the reading room feel less like a usable field guide even after the outer feed was bounded. | Fixed with one final CSS-only reader pass: a quiet paper/ink palette, compact metric strip, clearer shelf spine, readable example blocks and a consistent book surface. The existing finite paging and scroll boundaries remain unchanged. |

Verification: Windows frontend tests **71/71**, Vite build **1,346 modules**,
and supported WSL backend tests **116/116**. Browser K&M remains blocked by
F-080, so this is not presented as a fresh device-level visual claim.

## Legacy Codex primitive retained a feed-sized minimum — 2026-09-17 (F-148)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-148 | P1 | The base `styles.css` fallback still declared `min-height: 520px` for `.codex-library`. The later reader rules normally overrode it, but a compatibility shell or stylesheet-order change could resurrect the old feed-sized Codex. | Fixed by changing the shared base primitive to `min-height: 0` and adding a regression assertion against the legacy 520px rule. |

Verification: Windows frontend tests **71/71** and `git diff --check` pass;
no state, learner file, PTY or hosted migration changed.

## Legacy Codex list fallbacks still owned scroll — 2026-09-17 (F-149)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-149 | P1 | The base Codex stylesheet still gave the paged bookshelf and encounter picker their own `max-height`/`overflow:auto` fallbacks. Those redundant scroll owners could recreate the infinite-feed feel in a compatibility shell. | Fixed by making both base primitives `max-height: none; overflow: visible`; React shelf/record paging remains the only collection navigation, with the intentional note/code scroll owners preserved in the reader layer. |

Verification: Windows frontend tests **72/72**, Vite transforms **1,346
modules**, and the supported WSL backend suite is **116/116**; `git diff
--check` passes. No state, learner file, PTY or hosted migration changed.

## Mobile Codex fallback still capped the bookshelf — 2026-09-17 (F-150)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-150 | P1 | The legacy mobile media query still capped `.codex-page-list` at 180px. Although the foundation stylesheet normally overrode it, a compatibility stylesheet order could reintroduce a second bookshelf scrollbar on narrow windows. | Fixed by making the mobile fallback explicitly `max-height: none; overflow: visible` and extending the source regression guard. |

Verification: Windows frontend tests **72/72**, Vite transforms **1,346
modules**, and `git diff --check` passes; no state, learner file, PTY or
hosted migration changed.

## Hub exposed locked future identities — 2026-09-17 (F-151)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-151 | P1 | Hub, legacy quest context and the compatibility journal rendered names/concepts for locked chapters or encounters. That leaked future campaign identity instead of preserving the silhouette/unknown contract used by Codex and Dungeon. | Fixed by rendering `Unknown chapter`/`Unknown encounter` and generic hidden-until-clear labels for locked projections, with a dashed silhouette treatment. Active and defeated records remain fully named. |

Verification: Windows frontend tests **73/73**, Vite transforms **1,346
modules**, and the supported WSL backend suite is **116/116**; no state,
learner file, PTY or hosted migration changed.

## Splash idle timer refreshed while the app was unattended — 2026-09-17 (F-152)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-152 | P2 | The launch-context effect updated `lastSeenAt` on a 60-second heartbeat, so leaving Forge open and unattended for more than 20 minutes never qualified for the requested returning splash on the next launch. | Fixed by recording last-seen time from real pointer/keyboard activity and mount/dismissal only; the background heartbeat was removed. |

Verification: Windows frontend tests **74/74**, Vite transforms **1,346
modules**, and the supported WSL backend suite is **116/116**; no state,
learner file, PTY or hosted migration changed.

## Codex was still trapped in the narrow editor column — 2026-09-17 (F-153)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-153 | P1 | The Codex folio had bounded internal rules, but it still rendered in the editor-column grid beside the activity/context rails. On ordinary Forge windows that made the book narrow and visually read like an endless dashboard even when collection paging was finite. | Fixed by promoting Codex to the full-width surface route. The active-quest rail stays inside the folio, the shared surface navigation remains available, and a dedicated flex budget prevents the navigation row from pushing the book below the viewport. |

Verification: Windows frontend tests **74/74**, Vite transforms **1,346
modules**, and `git diff --check` pass. No state, learner file, PTY or hosted
migration was changed. Fresh browser K&M remains blocked by F-080.

## Codex still had a competing scroll cascade and no route escape — 2026-09-17 (F-154)

| ID | Severity | Finding | Status |
|---|---|---|---|
| F-154 | P1 | The previous Codex fixes bounded the intended layout, but the stylesheet still contained multiple later height/overflow passes. Depending on cascade order, the selected book could feel like a page-long feed, and Codex was the one wide surface without the shared route-navigation row. | Fixed with a final cascade contract: Codex is pinned to the Forge viewport, the shelf/index stay non-scrolling on desktop, the selected book owns one bounded reading scrollbar, the Battle Shell owns its own bounded scroll when needed, and a compact SVG route-navigation row now sits inside Codex. |

Verification: Windows frontend tests **75/75**, Vite production build **1,346
modules**, supported WSL backend tests **116/116**, and both live Vite sources
(`5181`, `5190`) expose the F-154 CSS through HMR. No player state, learner
file, PTY or hosted migration changed. Fresh browser K&M remains blocked by
F-080.

## Forge-first acceptance pass — 2026-09-18

| ID | Severity | Finding | Status |
|---|---|---|---|
| B-155 | P1 | Forge-file objective submission initially failed even with the correct active campaign file, and the first binding did not expose an explicit file digest. | Fixed: challenge construction now reads `context.active_file.path` and its SHA-256 digest, rechecks the disk at submission time, and rejects unsupported paths, stale digests, or changed contents. |
| B-156 | P1 | The live user launcher on `5173` can display the previous bundle after a source slice is built, making the old Battle Shell appear to remain. | Confirmed runtime-cache/process-group issue, not a current-source regression. Disposable current-source `5198` served the new route/UI. Logged as F-170; managed launcher restart remains an operator action because the existing shell/AI PTYs were intentionally preserved. |
| B-157 | P2 | A projection that mutates a disposable canonical copy must update every surface without a browser refresh, or the UI can silently drift. | Passed: state-service mutation changed Resolve `4/4 → 2/4` and produced a verified-objective toast; a second mutation produced mob-defeat, next-encounter, reward and level-up notifications, HUD `LV 4 / 20 XP / 115c`, and Forge switched to The Dealer's Hand. Codex Encounter folio also recorded the verified browser evidence. |
| B-158 | P2 | Nested HUD icon spans could regress to empty pills when route styles are applied. | Passed current-source visual check: heart, coin, flame, shield and boss/sword monochrome SVGs were visible with DEV/RANK unchanged; direct-child selectors and nested reset rules remained intact. |

Verification: browser keyboard/mouse only (no Playwright) on disposable current-source port `5198`; backend **117/117**, frontend **86/86**, Vite build **1,346 modules**, and `git diff --check` pass. Existing launcher/backend/PTY PIDs were not reset; disposable servers used separate processes and a temporary state copy.

## Current-source UI regression sweep — 2026-09-18

| ID | Severity | Finding | Result |
|---|---|---|---|
| B-159 | P1 | Codex concept heading and definition could be covered by the pager in a short viewport. | Fixed and verified on disposable `5198`; the heading is readable and the selected folio owns the bounded scroll region. |
| B-160 | P1 | Workspace transfer tree opened every folder and a malformed literal-backslash path could mirror a host-root tree. | Fixed with collapsed disclosure controls plus frontend/server filtering and symlink protection; the user-owned malformed directory was not deleted. |
| B-161 | P2 | HUD stat labels did not explain themselves and the wide route row could push navigation off-center. | Fixed with icon-only Hub navigation, centered links, rail/topbar animation, and hover/focus/native-title stat descriptions; SVG icons remain visible. |

Verification: CUA keyboard/mouse only (no Playwright), frontend **87/87**, backend **117/117**, WSL build **1,346 modules**, and `git diff --check` pass. Managed launcher, shell/AI PTYs, canonical state, and hosted state were left untouched.

## Copilot provider sweep — 2026-09-18

| ID | Severity | Finding | Result |
|---|---|---|---|
| B-162 | P2 | GitHub Copilot CLI was installed in WSL but invisible to Forge’s provider controls and runtime capability report. | Fixed and covered: Copilot launch button, command-palette action, provider tracking, runtime detection, and bounded-provider messaging are present; state authority remains unchanged. |

Verification: WSL `copilot --version` returned **1.0.83**; frontend **88/88**, backend **117/117**, WSL build **1,346 modules**, and `git diff --check` pass.

## Boss gate / workspace tree sweep — 2026-09-18

| ID | Severity | Finding | Result |
|---|---|---|---|
| B-163 | P1 | Boss Gate still mixed a requirement picker and duplicate file-submit action into the campaign Forge surface, and did not place the current state-owned goal/damage directly under the Resolve bar. | Fixed: lore, Resolve/max Resolve, current sequential goal, canonical damage, and bounded reward envelope are rendered from the encounter projection; the goal advances only after the validated state-service mutation. The boss gate now has one `Send current goal to PYR` action. |
| B-164 | P2 | Single-file campaign steps showed a noisy full repository tree even though the editor file was the only answer surface. | Fixed: single-file steps show an active-file summary; multifile projects retain collapsed folder disclosure and an explicit Files toggle. |

Verification: CUA browser keyboard/mouse only (no Playwright) on disposable `5198`; no canonical save or PTY reset.

## Boss Gate encounter-card sweep — 2026-09-18

| ID | Severity | Area | Finding | Result |
|---|---|---|---|---|
| B-166 | P1 | Forge encounter UX / layout | The Boss Gate still presented a redundant `Send current goal to PYR` action beside Forge's real `Submit run`, while its state-owned quest, reward context, and damage mechanics were not framed as a playable encounter. The boss-specific width override also made the left sidebar resizer appear broken. | Fixed. Forge now keeps one answer surface: the active file and `Submit run`. The encounter card presents lore, Resolve, a dynamic state-owned current quest, `BOSS / MOB MECHANICS`, and bounded loot-at-stake data. The gateway owns damage/reward outcomes, and the left panel is resizable from 260–430px with a visible separator. |

Verification: CUA keyboard/mouse only (no Playwright) on disposable current-source `5198` at 1280×720; the panel widened from roughly 320px to 400px and remained readable. Frontend **90/90**, targeted backend state/context tests **54/54**, WSL Vite build **1,346 modules**, and `git diff --check` passed. The managed launcher, canonical save, hosted state, shell PTY and AI PTY were not reset; disposable preview sessions were separate.

## Boss Gate vertical presentation pass — 2026-09-18

| ID | Severity | Area | Finding | Result |
|---|---|---|---|---|
| B-167 | P2 | Forge encounter UX | The Boss Gate left unused vertical space below a compressed mechanics strip, so the encounter did not feel like a readable game brief even though all fields technically fit. | Fixed with a flex-based encounter track: multi-line lore, a roomier current quest card, stacked mechanics rows with state-owned outcomes, and a loot footer anchored at the bottom. A short-height rule preserves the compact layout when needed. |

Verification: CUA browser keyboard/mouse only (no Playwright) on disposable `5198` at 1280×960; the full Boss Gate remained visible and readable after the CSS change. Frontend **90/90**, WSL Vite build **1,346 modules**, and `git diff --check` passed. Managed launcher, canonical/hosted state, shell PTY and AI PTY were not reset.

## App-level route menu / Boss Gate visual sweep — 2026-09-18

| ID | Severity | Finding | Result |
|---|---|---|---|
| B-165 | P1 | The Forge Boss Gate used a narrow, capped scroll region. On a real 1280×720 viewport the state-owned action and reward fell below the visible panel when the scrollbar was removed. Non-wide routes also lacked the same top navigation affordance. | Fixed with one app-level centered SVG navigation row, the logo-only Hub control, a wider boss context track, and a compact no-scroll Boss Gate layout. |

Verification: CUA keyboard/mouse only (no Playwright) on disposable `5198`: Forge showed lore, Resolve, current goal/damage, submit action and reward together; Tutor, Dungeon, Codex, Settings and Hub all navigated from the same top menu. Managed launcher, shell/AI PTYs, canonical state and hosted state were untouched.

## Simplified Forge answer surface — B-168 (2026-09-18)

| ID | Severity | Area | Finding | Result |
|---|---|---|---|---|
| B-168 | P1 | Forge / Boss Gate | The encounter sidebar asked the learner to read and submit a separate goal while the editor already had the real campaign answer and `Submit run` action. The result felt like a text wall and made it unclear where to work. | Fixed. The sidebar is now Resolve plus a small pixel PYR companion. A virtual state-owned `quest.md` tab carries only the current lore, goal, mechanics and authorized reward envelope; it is explicitly read-only. The existing toolbar submission sends the active `.py` with the current campaign revision/nonce/digest to the canonical gateway. |

Verification: frontend **90/90**, backend **117/117**, WSL Vite production build (**1,346 modules**), and `git diff --check` pass. CUA keyboard/mouse visual verification on disposable current-source `5198` showed the read-only `quest.md` projection, active `.py` editor, single `Submit run`, Resolve bar and pixel PYR companion. No duplicate objective picker, Battle Shell component, or second submit action remains in Forge; no managed launcher, canonical state, hosted state, shell PTY or AI PTY was restarted.

## Forge sidebar compact-mode sweep — B-169 (2026-09-18)

| ID | Severity | Area | Finding | Result |
|---|---|---|---|---|
| B-169 | P2 | Forge sidebar / editor focus | The full encounter sidebar was useful for reading Resolve/PYR but wasteful while writing; there was no fast way to keep only the two campaign document choices visible. | Fixed with a persistent 76px Forge rail: Python and Markdown SVG file buttons, a full-view restore button, and no Boss Gate/PYR content in compact mode. Full view preserves the existing Resolve layout and enlarges/centers PYR. |

Verification: frontend **91/91**, WSL build **1,346 modules**, and `git diff --check` pass. CUA visual check confirmed the compact rail opens `.py` and `quest.md`, the latter remains read-only, and expanding restores the full Resolve/Boss Gate/PYR view. No managed launcher, state file, hosted state or PTY was changed.

## B-170 — PYR companion felt static and floated too high (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Forge Boss Gate / companion | The PYR badge did not communicate a living companion and remained centered above a large empty lower area in the full encounter track. | Fixed with a small idle float and timed blink, motion-reduction fallbacks, and a lower flex anchor for the full Boss Gate. Compact mode remains deliberately quiet with only file shortcuts. |

Verification: frontend **92/92**, WSL Vite build (**1,346 modules**), and `git diff --check` pass. CUA visual inspection confirmed the full and compact states without mutating player state or resetting managed PTYs.

## B-171 — Boot needed a softer entrance and learning sidebars could not collapse (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Boot / Tutor / Infinite Dungeon | The shell had no explicit boot fade, and the Tutor/Dungeon editor routes always kept their full context sidebar open. | Fixed with a 360ms shell fade-in that respects reduced motion and the animation setting, plus route-aware slim rails and restore controls for Tutor and Infinite Dungeon. |

Verification: frontend **94/94**. CUA visual inspection confirmed both compact routes and their restore actions on disposable `5198`; no state or managed PTY was changed.

## B-172 — Slim-rail restore was too far away (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Compact editor rails | The uncollapse button sat at the bottom of the full-height rail, so recovering from an accidental collapse required an unnecessary reach. | Fixed by keeping the existing compact button size and placing it above the `.py`/`.md` or route-file shortcut(s). |

Verification: frontend **94/94**, WSL Vite production build (**1,346 modules**), and fresh CUA visual inspection on disposable `5198` confirmed the same-sized restore button is now immediately above the active route/file shortcut. No state mutation, managed launcher restart, or PTY reset occurred.

## B-173 — Redundant Dungeon Forge link and invisible Tutor Forge icon (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Route-local navigation | Infinite Dungeon repeated the global Forge link, while Tutor's Forge icon could disappear because nested title SVGs had no explicit size/stroke rule. Forge had no equally quick Tutor shortcut. | Removed the Dungeon duplicate, kept Tutor's return action, added Forge → Tutor, and added shared nested title-icon styling. |

Verification: frontend **94/94**, WSL Vite production build (**1,346 modules**), and fresh CUA visual inspection on disposable `5198` confirmed the three route behaviors. No state mutation, managed launcher restart, or PTY reset occurred.

## B-174 — Homestead route crash (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Homestead | Opening Homestead blanked the app because `GameScreen` referenced an undefined `equipCampaignItem` callback while constructing the loadout surface. | Fixed by adding the callback to `GameScreen` props. The route now renders live loadout, shop and campaign revision content. |

## B-175 — Settings inherited Forge compact state (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Settings / navigation | Collapsing Forge persisted a shared left-panel flag; navigating to Settings then showed the editor rail instead of the complete settings surface. | Fixed by making Settings a wide route in both app layout and `GameScreen`, so the settings page is independent of Forge/Tutor/Dungeon collapse state. |

## B-176 — HUD centre drift (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Top HUD | Space-between flex alignment made the level/XP strip shift left as stat pills and account status changed width. | Fixed with a responsive three-column topbar grid; visual CUA check confirmed the level bar remains centred at the desktop viewport. |

Verification for B-174–B-176: CUA keyboard/mouse only (no Playwright) on disposable `5198`; frontend **95/95**, WSL Vite production build **1,346 modules**, and `git diff --check` pass. No player-state mutation, launcher restart, or managed PTY reset occurred.

## B-177 — Dungeon PYR feedback was too chat-like (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab | The new prototype needed contextual AI feedback without a second terminal, and error submissions needed a fair damage/hint loop rather than a hidden solution or an immediate unexplained reset. | Added compact room-entry/submission event cards, removed any persistent AI surface, applied 18 HP damage to short/error submissions, kept the IDE open for retry while HP remains, and used text-only hints such as checking the line named by the error. |

Verification: `node --check prototypes/infinite-dungeon/src/main.js` and `git diff --check` pass; live CUA checks follow after restarting Vite so the OneDrive/WSL watcher cannot serve stale source.

## B-178 — Dungeon map had no route graph or floor conclusion (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab map | Every room was presented as an independent clickable tile, so there was no route planning, branch risk, or final floor objective. | Replaced the flat tile set with a six-row branching graph, edge lines and visited-path highlighting. Unconnected rooms are disabled; all routes converge on The Count Keeper. A clean boss submission advances to the next floor and resets the map to its start campsite. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` followed connected branches, confirmed disabled off-path nodes, opened the boss room, and confirmed the live Floor 4 transition after a clean boss submission.

## B-179 — Dungeon runs had no starter class identity (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab / run boot | Players entered the map with the same weapon and rules every time, so the proposed class-and-gimmick layer was missing. | Added a pre-run class screen and wired three bounded starter kits into the prototype: Syntax Warden error protection, Resolve Duelist clean-hit bonus, and Route Merchant opening economy. Character displays the active class and remaining passive state. |

Verification: CUA keyboard/mouse only (no Playwright) confirmed class selection, route boot, altered coins/loadout, and Syntax Warden’s first error absorption. Market/campsite expansion remains the next deliberate slice.

## B-180 — Class setup screen diluted the descent moment (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab class gate | Starter-rule copy, the setup paragraph, stretched grid rows, and a low-weighted action made the class choice feel like a form instead of the beginning of a run. | Removed the redundant copy, moved the cards up, enlarged the cards, and made the selected-class `Enter the dungeon` action appear centered beneath them. Added a short phase-in into the map/room screen. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` checked the initial and selected states and clicked through into the dungeon. No live campaign state was touched.

## B-181 — Class selection sat too high (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab class gate | The class choice sat too close to the top of the viewport, weakening the sense of a deliberate run setup. | Centered the full-width class composition in the available page area and kept the original card sizing; mobile still collapses to one column. |

Verification: CUA visual check only (no Playwright) on `5201` confirmed the centered composition and selected CTA.

## B-182 — Dungeon-entry CTA had unnecessary setup copy (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab class gate | `READY TO DESCEND` and the selected-class label made the entry action heavier than necessary. | Reduced the selected state to a single black-and-gold `Enter the dungeon` button and verified the existing phase-in on click. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` confirmed the simplified CTA and dungeon transition.

## B-183 — Class choices lacked an explicit prompt (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab class gate | The heading moved directly into the cards without a small instruction cue. | Added `PICK A CLASS` beneath the heading, pulled it close to the title, and retained breathing room before the class cards. |

Verification: CUA visual check only (no Playwright) on `5201` confirmed the prompt spacing in both unselected and selected states.

## B-184 — Prompt needed more separation from the class picker (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab class gate | `PICK A CLASS` did not have enough breathing room before the cards. | Lifted the prompt toward the heading and increased the gap before the class selection. |

Verification: CUA visual check only (no Playwright) on `5201` confirmed the updated spacing.

## B-185 — Class-to-dungeon fade was too quick (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab run transition | The route appeared almost immediately after pressing Enter, making the descent feel abrupt. | Extended the phase-in to a smoother 0.95s and verified the button still lands on the route cleanly. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` captured the transition mid-fade and confirmed the resulting dungeon screen.

## B-186 — Descent transition still needed more time (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab run transition | The shorter phase-in did not give the dungeon entry enough dramatic weight. | Extended the phase-in to 2.5s and confirmed the route settles cleanly at the end. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` captured both the longer fade and the final route.

## B-187 — Map grid added visual clutter (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab route map | The background grid competed with the route edges and made the branching map harder to parse. | Hid only the background grid for this first visual pass; route edges are intentionally unchanged for comparison. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` confirmed the cleaner map background.

## B-188 — Route edges bled through location cards (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab route map | Disabled nodes used global opacity, so branch lines remained visible through the location surfaces. | Made map nodes opaque and reduced only their inner icon/label opacity, preserving the locked visual state without bleed-through. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` confirmed the cleaned node layering.

## B-189 — Dungeon CTA had a redundant outer box (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab class gate | The entry button was wrapped in a second bordered panel, making the action feel heavier than the rest of the setup. | Removed the outer layer and kept the black/gold `Enter the dungeon` button as the only visible panel. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` confirmed the cleaner entry action.

## B-190 — Enter action needed its own fade-in (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab class gate | The button did not have a distinct entrance motion after class selection. | Added a short delayed button fade/settle animation while preserving the parent CTA animation. |

Verification: CUA visual check only (no Playwright) on `5201` confirmed the selected-state button presentation.

## B-191 — Room economy lacked meaningful campsite and market choices (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab room loop | Campsites were limited to bandage/cook, while markets exposed only two small offers and did not foreground the run purse. | Added five campsite actions, a visible supply strip, a four-item market shelf, live coin purse, and state-backed purchase/preparation feedback. |

Verification: CUA keyboard/mouse only (no Playwright) on `5201` exercised rest, sharpened edge and ration purchase flows and confirmed visible state changes.

## B-192 — Boss route could skip every fight (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Infinite Dungeon design lab map | Every branch converged on the boss, but the prototype did not enforce a minimum cleared fight. | Boss nodes are now unreachable and their challenge button disabled until `clearedFights > 0`; the first branch row contains a normal gate on every route, and the pre-boss row contains only markets/campsite. |

Verification: CUA-only run `?v=27` confirmed a fresh boss is disabled, then confirmed boss access after a normal gate and elite clear plus the final campsite.

## B-193 — Market had no run gear shelf or owned-item handoff (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab market/character | Supplies were visible, but a market could not offer weapons/armor or hand purchased gear into the run loadout. | Each market now deterministically stocks two weapons and two armor pieces; purchase state, coins, owned items, and Character equip controls update together. |

Verification: CUA-only run `?v=27` bought `Market Mnemonic` from the rotating shelf and equipped it from Character without a page refresh.

## B-194 — Risk key did not explain what it revealed (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab mystery room | The route key promised a “safe market” regardless of the unknown room, so players could not understand the actual choice. | The key now reveals a bounded profile preview (elite/quiz/reward/debuff/buff/teleport/discount/armory) without revealing future questions or unsupported rewards. Full risk outcomes remain deferred and documented. |

Verification: CUA-only risk-room inspection on `?v=27` showed the explicit route-key purpose and bounded unknown-room copy; no future question or answer was rendered.

## B-195 — Route map underfilled its panel (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P3 | Infinite Dungeon design lab map | The six-row graph left a large unused area below the boss and made the run feel short. | Added a seventh deep-risk row, moved preparation rooms to row six, and moved the converged boss to row seven while preserving opaque location cards and the fight-gated boss rule. |

Verification: CUA-only visual check on `?v=29` confirmed the longer map fills the panel and still keeps the final row free of gates/elites.

## B-196 — Risk pacing and key semantics were unclear (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab route/risk rooms | The route had consecutive unknown rows, and a route key could be read as the thing that enabled risk-room entry. | Replaced the second risk row with recovery/market choices, added one authored preparation row, renamed the item Vision Scroll, made it expensive/rare, and added an unconditional Enter the risk action. |

Verification: CUA-only run `?v=30` confirmed a zero-scroll risk room still exposes `Enter the risk`, an elite awards a Vision scroll, and a market lists the scroll at `80c`.

## B-197 — Route lanes could be joined and recovery was top-heavy (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab map | Each row offered diagonal cross-links, so the opening choice did not commit the run to a readable route. Most combat was front-loaded while the lower rows repeated camp/market nodes. | Replaced the crossing graph with three independent authored lanes. The first fork now commits the player to one same-column node per row; rows two through six mix gates, elites, fate/risk, camps and markets, and only row seven is the final camp/market preparation row before the boss. | |

Verification: CUA-only map check on `?v=33` selected the middle lane, confirmed one reachable same-lane continuation and no cross-lane edges, and visually confirmed the final-row-only preparation rule.

## B-198 — Hand-balanced room types removed meaningful run luck (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab route generation | Every lane had a preselected mix, so players could not experience genuinely unlucky rows such as three elites in one row. | Each non-final node now rolls independently at run generation. No row or lane quotas are applied; only the final pre-boss row is camp/market. A global no-fight fallback preserves the existing boss-access rule without balancing the route. | |

Verification: Browser-only CUA checks on `?v=35` and `?v=36` showed two different independent room rolls, with the final preparation row constrained to camp/market in both runs.

## B-199 — Dangerous random rows lacked a recovery signal and passive/weapon roles were blurred (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab route/class setup | A run could stack two elites or three normal gates without an authored recovery cue, and class selection visually grouped the passive as a weapon gimmick. | Two-elite and three-gate rows now force a campsite next and a market at the end of that recovery row. Other rows get only the requested right-edge fallback. Class passives are now first-class data independent of starter/equipped weapons and remain active after weapon swaps. | |

Verification: Browser-only CUA on `?v=37` showed the random route with its final preparation row, the two-elite/three-gate recovery copy, and separate `STARTER WEAPON` / `PASSIVE` fields on class selection and Character.

## B-200 — Starter weapons duplicated class passives (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab class/loadout | Lint Lantern, Loopblade and Branch Compass repeated the same text/effect as their class passives. | Starter weapons now carry distinct playstyle-adjacent effects and are evaluated independently: extra bounded hint, elite Resolve bonus, and free risk preview respectively. The class passive persists independently when the weapon changes. | |

Verification: Browser-only CUA on `?v=38` and `?v=39` showed distinct starter-weapon descriptions, `ACTIVE CLASS · PASSIVE`, and Branch Compass equipped as a separate loadout item; `node --check` passed.

## B-201 — Vision Scroll was not a usable loadout item (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab Character/map | A Vision Scroll could be read only from an entered risk room, so the player could not spend a scroll from the run loadout to inspect a different risk on the map. Fights cleared was also mixed into inventory. | Character → Loadout now has a `Use on map` action. While active, every unrevealed risk node becomes selectable regardless of lane/reachability; selecting one consumes one scroll and records that risk in the shared revealed ledger. Character → Stats now owns Fights cleared and boss-gate status, while Inventory stays consumables only. | |

Verification: Browser-only CUA on `http://127.0.0.1:5201/?v=40` cleared an elite to earn one Vision scroll, used it from Character → Loadout, selected an off-route unrevealed risk, confirmed the bounded profile and one-scroll consumption, confirmed the node could not be scouted again, and checked Stats vs Inventory ownership. Static syntax/diff checks pass; room-local scouting also cancels active map-scout state to prevent stale targeting.

## B-202 — Route Merchant Branch Compass had no map-use affordance (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab class/loadout/map | Route Merchant started with Branch Compass equipped, but the weapon could not be used from the loadout. Its free read only appeared after entering a risk room, so the promised starter weapon did nothing during route planning. | Added an equipped-weapon `Read on map` action. It enables any unrevealed risk node without consuming a scroll, spends the one free read for the floor, writes the shared revealed-risk ledger, and exposes a clear active/cancel/spent state. | |

Verification: Browser-only CUA on `http://127.0.0.1:5201/?v=41` selected Route Merchant, used `Read on map` from its equipped Branch Compass, revealed an off-route risk with `0` Vision Scrolls, and confirmed the weapon changed to `Spent` after one read. No campaign save or PTY was touched.

## B-203 — Risk resolution could strand the run after a shop/cache purchase (2026-09-18)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Infinite Dungeon design lab risk room | A resolved armory or discount purchase cleared `activeRisk` on the next click but kept the node in `enteredRisks`; the fallback renderer then showed “Risk entered” with a disabled commit button and no meaningful resolution summary. | Added an explicit resolved-risk card with a single `Leave the room` exit. The room remains recorded and cannot be entered or rewarded twice, while the route can continue normally. | |
| 2 | P2 | Infinite Dungeon design lab map/room identity | A known risk continued to display generic Fate/Risk chrome even after scouting or entry, so a market-like risk did not feel like a market. | Added server-like `roomType` metadata to each bounded profile and a presentation resolver. Revealed/entered profiles now render as Market, Elite Gate, Challenge Gate, Hidden Cache, Risk Shrine, or Folding Corridor while the underlying mystery node remains unchanged for route logic. | |

Verification: Browser-only CUA on the WSL-served prototype reproduced the purchase → exit path, then confirmed the green `RISK RESOLVED` card and route exit. A cache outcome changes the map node and Room Screen to `Hidden Cache` with its own bounded description; discount and armory outcomes present as Market variants. No Forge state, campaign save, Supabase transport, or PTY was touched.

## B-204 — Dungeon memory vanished between runs (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab / Character → Codex | The room prototype reset its whole visible history with each mock run, so a learner could not revisit discovered room types or question lenses. | Added a bounded local-only Codex archive. It records only surfaced rooms and attempted encounters, survives run reset/refresh through `localStorage`, and excludes future questions, answer keys and locked rewards. | |

Verification: Browser-only CUA on the WSL-served prototype showed `1 rooms · 0 encounters`, kept the campsite record after Reset mock run and a browser refresh, then showed `2 rooms · 1 encounters` after a clean elite submission (`The Faultline · BUG HUNT`). Campaign state, Supabase transport and both PTY sessions remain outside the prototype boundary.

## B-205 — Campsite actions were not mutually exclusive and ration/armor prep was underspecified (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab campsite | A player could trigger multiple campsite preparations in one visit, which removed the tradeoff between recovery, max-HP growth, Resolve preparation and defense. Cooking a ration also changed score rather than the requested max-HP ceiling. | Added a shared one-action-per-campsite guard. Ration cooking now consumes one ration for +10 maximum HP only; bandage, rest, sharpen, tonic and armor preparation all spend the same campsite action. | |
| 2 | P2 | Infinite Dungeon design lab combat feedback | There was no small defensive preparation for a player who wanted to trade the campsite action for error protection. | Added `Fortify your armor`: a starting-value 6 HP one-shot brace shown in the campsite supply strip and Character inventory. The next failed normal/risk submission consumes only the absorbed portion and emits a bounded PYR/notice message; syntax-ward full absorption does not waste the brace. | |

Verification: static syntax/diff checks pass. Browser-only CUA confirmed a fresh campsite changed max HP from 78/100 to 78/110 with score unchanged, disabled every other action after cooking, and reported brace absorption on a later short submission without resetting the browser or any PTY.

## B-206 — Ration max-HP increase survived a fresh mock-run reset (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon design lab run lifecycle | `Reset mock run` cleared the route and inventory but left `maxHp` at the prior run's cooked-ration value, so the next run could begin at 78/110 instead of the starter 78/100 baseline. | Added an explicit `maxHp: 100` reset to both the run-start and reset assignments. A cooked ration now affects only the current run. | |

Verification: CUA reproduced the stale 78/110 state before this repair; after restarting the prototype server and starting a clean run, the HUD/campsite showed `HP 78/100`.

## B-207 — Infinite Dungeon editor/combat slice lost learning context and safe file custody (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Infinite Dungeon question room | The challenge surface was a plain textarea with no local completion, no floor-scaled guide, and no clear distinction between previewing progress and committing Resolve. | Reused the bundled Monaco editor/worker, added identifier and Python vocabulary completion, authored guide steps for floors 1–2, partial guidance for floors 3–4, and question-only presentation from floor 5. Typing only updates preview state; verified clean submission commits Resolve/rewards. |
| 2 | P1 | Infinite Dungeon mechanics and file bridge | Bug Hunt/Self-Destruct/Lifesteal/Double Strike behavior was not serializable or reversible, and a connected learner file had no stale-edit or backup guard. | Added explicit mechanic/timer/mutation/reward-lock fields, real hidden-tab-safe timers, bounded Bug Hunt mutations, SHA-256/FNV digest checks, capped localStorage snapshots, timestamped sibling backups, IndexedDB handle restoration, and one restore token that rerolls the mechanic. Unwritable browsers automatically avoid Bug Hunt. |
| 3 | P2 | Infinite Dungeon feedback | PYR was too persistent and combat feedback did not explain the active mechanic or failure cost. | PYR now appears only on room entry, mutation, timer expiry, restore or submission and docks below editor actions. Run HP and Mob Profile show the telegraph, failure consequence and reward lock without displaying answer code. |

Verification: Claude Sonnet read-only review found and the implementation fixed Monaco remount/view-state loss, unused guide validation, uncleared success timers, unbounded backup growth and unsafe Bug Hunt fallback. Prototype tests pass 9/9, WSL build passes, and browser-only CUA on port `5202` confirmed Monaco typing, guide preview (`3 / 6` then `6 / 6`), clean commit, PYR spacing and return to map. No arbitrary Python execution or canonical Forge mutation is included in this design-lab slice.

## B-208 — IDE brief spilled beneath the prototype footer (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon IDE layout | The guide, Mob Profile and project-file card were taller than the fixed IDE row, so the left brief could visually run beneath the footer while the editor stayed full-height. | Made the left challenge brief its own bounded vertical scroll region. The editor and docked PYR card keep their full-height layout, while the footer remains below the row with no overlap. | |

Verification: After restarting the WSL prototype server to pick up the cross-filesystem CSS change, browser-only CUA screenshots showed the left-panel scrollbar, readable Mob Profile/file bridge, docked PYR card and no footer overlap. The focused Self-Destruct editor also displayed its live fuse countdown.

## B-209 — Dungeon editor lacked Forge parity and conflated Run with Submit (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Infinite Dungeon Challenge IDE | The prototype's Monaco instance exposed a plain-looking editor: Python token colours and the suggestion widget were missing because the standalone language/contribution modules were not loaded. | Loaded the bundled Python tokenizer and Monaco suggestion controller, added a Forge-aligned local theme, and classified local identifiers, built-ins and keywords. Typing `tru` now visibly offers the valid `True` literal; no LSP, network AI or answer generator is used. |
| 2 | P1 | Infinite Dungeon combat loop | One `Run & submit` button made a self-check indistinguishable from the state-changing PYR verdict. | Added a visible Local Terminal self-check panel and separate `Run self-check` / `Submit to PYR` actions. Run reports bounded syntax/concept/literal-output previews and never changes HP, Resolve or rewards; Submit remains the only adjudication path. |
| 3 | P2 | Mob mechanics feedback | Mechanics described failure effects but did not tell players whether a safe Run could trigger them. | Added authored `runEffect` metadata to every mechanic and an `ON RUN` Mob Profile field. Lifesteal, Double Strike, Static Ward and Self-Destruct now explicitly telegraph that their combat effect is Submit/expiry-only. |

Verification: `npm test --prefix prototypes/infinite-dungeon` passes 12/12; WSL production build passes (749 modules transformed). Browser-only CUA on `http://172.26.238.39:5202/` visually confirmed Python token colours, the `True` completion popup, a successful local self-check with literal stdout preview, a syntax-error self-check showing `CHECK FAILED · NO DAMAGE`, unchanged `78/100` HP and `6/6` Resolve, and a subsequent clean Submit producing an elite verdict/reward. No canonical Forge, state service, Supabase, Campaign file or PTY was touched.

## B-210 — Infinite Dungeon editor keyboard contract was missing (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Infinite Dungeon Challenge IDE | The Monaco room editor had separate Run and Submit buttons but no campaign-parity keyboard contract, so Ctrl/Cmd+Enter, Ctrl/Cmd+S and Ctrl/Cmd+Shift+Enter could insert editor input or invoke the browser instead of the intended action. | Added capture-phase and Monaco bindings for `Ctrl/Cmd+Enter` → Run self-check, `Ctrl/Cmd+S` → Save draft, and `Ctrl/Cmd+Shift+Enter` → Submit to PYR. Save writes the connected `dungeon.py` only after its digest check, or stores a browser-local draft when no folder is connected; it never adjudicates combat. Added visible shortcut hints and accessible key metadata. | |

Verification: `node --check` passed for the prototype entry/editor, isolated prototype tests pass 12/12, WSL production build passes (749 modules transformed), and the existing frontend suite passes 95/95. Browser-only CUA on `http://172.26.238.39:5202/` pressed each shortcut in the live Monaco editor: Run produced both a valid `PASS · LOCAL PREVIEW` and an invalid `CHECK FAILED · NO DAMAGE` while HP stayed `78/100` and Resolve stayed `6/6`; Save reported `Saved a browser-local dungeon.py draft` without a verdict; Submit produced a PYR verdict, changed the prototype reward state, and returned map control. A desktop screenshot confirmed the three action buttons and compact shortcut labels. No canonical Forge, state service, Supabase, Campaign file or PTY was touched.

## B-211 — Infinite Dungeon duplicated the canonical Codex surface (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Infinite Dungeon Character menu | The isolated Dungeon prototype exposed a local Codex tab and localStorage archive even though learning history belongs to the canonical Campaign Codex. That created a second memory surface before the Dungeon loop was ported. | Removed the prototype Codex tab, archive renderer, record/write helpers and Codex-only styling. Character now keeps only Loadout, Inventory and Stats; room/combat flow remains unchanged. The old browser key is no longer read or written. | |

Verification: Prototype tests pass 12/12, the WSL build passes (749 modules transformed), and browser-only CUA on port 5202 showed Character with exactly `LOADOUT`, `INVENTORY`, and `STATS`; no Codex tab or archive rendered. A desktop screenshot confirmed the remaining Character panel has no empty Codex slot. No canonical Campaign Codex, state service, Supabase or PTY state was changed.

## B-212 — Infinite Dungeon needed a canonical main-game entry point (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Main-game navigation and Dungeon state | The completed Dungeon learning loop only existed in the isolated design lab, so the canonical game had no state-backed route for its class/passive, starter weapon, checkpoint, editor and Run/Submit split. | Ported the bounded vertical slice into the canonical game: Infinite Dungeon is a first-class route, class/passive and starter weapon are server-owned, the run/checkpoint stays in the canonical state gateway, and the room uses the bundled Monaco editor with local completion, Local Terminal self-check, Save checkpoint and separate Submit to PYR. |
| 2 | P2 | Dungeon map projection | The client generated future encounter nodes even when the gateway had not issued a route, making the map look like a second source of truth. | Map now renders only recorded history, the current room and state-issued next choices; unknown future questions remain hidden. |
| 3 | P2 | Duplicate learning surfaces | The isolated prototype Codex was still present at the point of port planning. | Removed the prototype Codex before porting. The canonical Campaign Codex remains the only Codex surface. |

Verification: frontend suite passes 95/95; WSL production build passes (1,346 modules transformed); server files pass `py_compile`; browser-only CUA on the canonical main-game tab confirmed the global route, active Dungeon class/passive/weapon, Monaco editor, Local Terminal, distinct Run/Submit controls, and a map containing only the current state-backed room. The richer prototype-only route/risk/elite/campsite and file-mutation mechanics are not claimed as canonical parity yet.

## B-213 — Canonical Dungeon room drifted from the prototype (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Main-game Dungeon room | Map & route had been ported, but the room card still showed a generic mob/brief and reset was not visible in the first viewport. | The state projection now labels the code-checkpoint encounter `The Count Keeper`; the room card renders the state-owned concept, difficulty and prototype-style handoff copy; and a header-level `Reset run` action is visible on both Room and Challenge IDE views. |

Verification: CUA screenshots of prototype and canonical rooms were compared after a clean frontend/backend restart. The canonical room now shows the aligned mob brief, route lock, editor handoff and visible reset action. Reset was not clicked; no run or campaign state was changed.

## B-214 — Canonical Dungeon port was visually tightened and clipped (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Main-game Infinite Dungeon route | The canonical route had been reinterpreted after the prototype port: class cards were compressed into one row, the map used shorter rows, the route tab strip consumed space, and the app-wide overflow lock clipped lower room/character content. | Restored the prototype class-card hierarchy and selection CTA, the three-column/header/map proportions, correctly aligned eight-row route edges, and prototype room spacing. The canonical-only tab strip is hidden while its state-compatible DOM remains. Dungeon now owns vertical scrolling at the page boundary. |

Verification: frontend suite passes 96/96; WSL production build passes (1,346 modules transformed); static parity checks cover the class hierarchy, map geometry and scroll owner. A live browser/CUA screenshot pass was not available in this turn, so visual certification remains pending on the running `?parity=3` tab.

## B-215 — Codex was visually overbuilt for theory study (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Campaign Codex | The Codex repeated the definition in the page header and folio, surrounded short theory with dashboard chips and heavy nested cards, and offered no obvious next learning action. | Reworked the final Codex cascade into a quiet concept reader: compact concept index, one definition, generic examples, a self-check prompt, explicit encounter/notes/mastery sections, and a direct Tutor handoff. The page remains finite and canonical; React does not invent rewards, answers or future encounters. |
| 2 | P2 | Canonical concept projection | Generic pages had examples and question lenses but no authored, student-readable mistake cues or self-check prompt. | Added bounded `common_mistakes` and `check_prompt` metadata to the state-owned concept projection for the nine generic Python pages. These are transferable theory prompts, not campaign answer keys. |

Verification: frontend tests pass 97/97; state-service tests pass 46/46; WSL build passes. Browser/CUA visual inspection was unavailable for this edit, so desktop and narrow live screenshots are still required before closing the visual bug.

## B-216 — Codex needed a resource-first prototype before another live rewrite (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Codex design flow | The canonical Codex could be changed repeatedly without first testing whether a dictionary/reference layout made theory the primary task. | Added a disposable medium-fidelity coded prototype with concept groups, search, a lesson-first page, secondary encounter evidence, notes, self-check hints and a Tutor handoff. It is isolated from canonical state and persists no player data. |

Verification: syntax check passes and WSL prototype build passes. No live visual claim yet; the prototype should be opened at port 5206 and reviewed before canonical implementation.

## B-217 — Encounter evidence did not earn space in the Codex prototype (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Codex resource prototype | The encounter tab showed a mob name, question lens and cleared status, but no actionable learning context. It competed with the reference material without helping revision. | Removed it from the prototype. Notes and the theory lesson remain first-class. Encounter history is deferred until it can show validated attempts, repeated mistakes and a useful takeaway rather than a combat log. |

Verification: prototype syntax check and WSL build pass; visual review is available on port 5206.

## B-218 — Codex lesson page was longer than necessary (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Codex resource prototype | The lesson blocks were all full-width, so the good reference content felt like a long vertical document. | Added a responsive compact study spread for desktop while preserving the single-column mobile fallback and the same reading order. |

Verification: syntax check, WSL build and HTTP 200 probe pass; live visual review is ready at port 5206.

## B-219 — Tutor needed one bounded practice loop beside the reference (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Tutor/Codex prototype | A reference page alone did not give the learner a clear next step, while an unbounded chat flow could drift into answer-giving. | Added an IDE practice tab with five bounded thinking modes and explicit preview-versus-feedback actions. PYR suggestions are represented as review-queue events; the prototype does not generate or reveal campaign answers. Learners can suggest, pin and dismiss queue items. |

Verification: browser keyboard/mouse flow exercised mode selection, response entry, feedback submission, queue mutation, pin/unpin, dismissal, learner suggestion, and reload persistence. Syntax check and WSL build pass; canonical Forge/state/Supabase/PTY surfaces remain untouched.

## B-220 — Tutor IDE lacked the campaign workbench rhythm (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Tutor IDE prototype | Practice had a single response box and no visible run terminal or AI terminal, so moving from a failed campaign concept into Tutor would feel like a separate product. | Ported the visual IDE pattern into the disposable prototype: real local Monaco editor with Python colours/completions, compact file rail, local self-check terminal, bounded PYR terminal, and explicit save/run/submit controls. Moved the practice-mode selector above the workbench to give the editor more width. |

Verification: browser screenshot and keyboard/mouse checks confirmed the widened editor, practice strip, Monaco rendering, local pass output, and PYR hint flow. Build and syntax checks pass; no canonical state or PTY is touched.

## B-221 — `.md` needed to be a writing notebook, not a second Codex reader (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Tutor `.md` / Codex notes | Clicking `.md` initially showed reference-style content again, and the Codex Notes panel meant two places could appear to own learner notes. | Replaced the `.md` route with a book-like, warm-paper notebook: chapter/type selector, linked concept context, four editable note pages, separate browser-local notebook storage, save feedback, longer folios and 360ms page-turn motion. Removed the Codex Notes tab and left one Open notebook handoff. | |

Verification: CUA opened the `.md` rail button, visually inspected the longer two-page spread, typed and saved a note, and confirmed `Saved to this notebook locally.` The chapter selector changed the linked concept to Lists & collections without exposing duplicate Codex text. No campaign state, Supabase or PTY was touched.

## B-222 — Notebook was exposed as a third top-level page selector (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Tutor navigation | Codex, IDE practice and Notebook were all top-level selectors, so the `.md` file did not feel like the IDE's screen switcher. | Reduced the shell to two selectors. The compact IDE rail now owns `.py`/`.md` screen switching; `.md` opens the writing folio and `.py` returns to tutor.py. The selected file is marked active and Codex routes into the same Notebook screen. | |

Verification: CUA browser inspection confirmed only Codex and IDE practice in the top bar and a working `.py`/`.md` switcher inside the IDE surface.

## B-223 — Notebook needed practical writing formats and overflow behavior (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Tutor notebook folio | Notes used a fixed-height textarea, and learners had no fast way to make bullets, numbered lists or other small note structures. | Added bounded note pages with an inner scrollbar, `*`/`-` to `•` normalization, list continuation on Enter, Bullet/Number/Quote/Code controls, and persisted Lined/Graph/Plain page looks. F-235/B-224 add chapter CRUD, page colors and the slash command palette. | |

Verification: CUA visual checks confirmed long notes scroll inside the folio, bullet conversion works, and Graph paper changes the page texture without leaving the two-selector Tutor flow.

## B-224 — Notebook controls needed authoring parity and bounded scrolling (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Tutor `.md` notebook | Chapters could not be edited, added or removed; page color was fixed; long notes could push the Save page row out of view; and users had no Notion-like slash command palette. | Added browser-local chapter CRUD controls and a chapter editor, five page-color themes, a finite two-page folio with an inner textarea scrollbar and anchored save action, plus a keyboard-friendly `/` menu for headings, lists, to-dos, quotes, code blocks and dividers. | |

Verification: CUA opened the `.md` rail, inspected `+ New`/`Edit`/`Delete`, changed the page color, opened `/`, inserted a heading, and filled the note with 50 lines. The final screenshot showed the inner scrollbar and a visible Save page button without bleed. Canonical Forge/state/Supabase/PTY surfaces were not touched.

## B-225 — Ported Forge folio initially clipped below the fixed shell (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Canonical Forge Tutor/Codex | The first React port rendered the prototype book but its `WideSurfaceFrame` sat inside the fixed game grid, so the lower notebook controls were below the viewport and the frame had no clear scroll owner. | Added a resource-only scroll viewport around the port, allowed the resource surface to grow inside the bounded workspace, and styled its scrollbar. The lower Save page/pager are now reachable without changing the shell, state gateway or PTYs. |

Verification: CUA visual comparison of prototype `:5206` and Forge `:5174`; clicking the live Forge Save page control moved the resource frame to the lower folio, showing the textarea, save status and pager. No Playwright or browser refresh was used for the interaction check.

## B-226 — Tutor `.md` route hid the IDE switcher and output panels (2026-09-19)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Forge Tutor Notebook | Selecting `notes.md` unmounted the compact file rail, so the learner could not return to the IDE from the notebook. The IDE editor height also pushed the local terminal below the useful viewport and left the bounded PYR panel cramped or hard to reach. | Added the same file rail to the notebook screen with a working `tutor.py` return action; reduced the Monaco viewport and reserved a visible local self-check terminal; made PYR messages scroll inside a bounded panel. Removed Codex from the duplicate shared top menu because it is already inside Tutor Notebook. | |

Verification: Fresh CUA at Forge `:5175` visually showed the local terminal and PYR panel together, clicked `notes.md`, and returned via `tutor.py`; no Playwright, state migration, Supabase transport or managed PTY restart was used. Frontend tests **97/97** and production build (**1,346 modules**) pass.

## B-228 — Home room viewpoint corrected to top-down (2026-09-21)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Campaign v1 Home | The modular room pass was initially interpreted as a straight-on interior. That conflicted with the requested Stardew-like overhead room and made the floor feel like a stage instead of a place to expand. | Replaced the room treatment in the isolated prototype with a CSS-built top-down floor plan: wall strip, tiled floor, furniture footprints, rectangular rug, aligned station hotspots, and a top-down Pyr placement. Existing Home actions and data remain intact. |

Verification: CUA desktop screenshot at 1569×958 confirmed the overhead wall/floor split and station alignment. Mobile checks were not part of this PC-only prototype scope. Prototype tests **15/15** and the WSL production build pass.

## B-229 — Home upgrades and achievement plaques (2026-09-21)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P1 | Campaign v1 Home | The top-down room had no authored progression surface for upgrade tokens and no visible record of memorable clears. The visual review also found a weak floor boundary, an ungrounded plant, and a rug that read too much like a panel. | Added five data-driven room upgrades with stat/trinket effects, four milestone achievement plaques, a toggleable wall station/drawer, purchase-state rendering, and deterministic state tests. Strengthened the floor trim, grounded the plant at the right wall, and added a woven rug border/fringe while keeping the room modular and CSS-built. | Fixed / verified |

Verification: Desktop CUA screenshot and interaction check confirmed the drawer, purchase state, HP/token update, and achievement row. Prototype tests **18/18** and WSL production build pass. Mobile checks remain intentionally out of scope for this PC-only prototype.

## B-227 — Codex signals crowded the mistake folio (2026-09-20)

| Point | Severity | Surface | Finding | Result |
|---|---|---|---|---|
| 1 | P2 | Codex Mistakes & signals | The generic question lens shared a two-column row with Common Mistakes, leaving the actual examples cramped and making the signal tags feel like filler. | Moved the validated Practice Signals tags below the mistake examples in a compact full-width strip. | |

Verification: CUA visual inspection confirmed both mistake code examples use the full reader width and the signal tags sit beneath them without a competing column.

## 2026-09-21 — Home port verification note

The Home/Homestead port is a UI/state projection task, not a Bug Hunt
mutation. The prototype source of truth is preserved at
`prototypes/campaign-v1/HOME_PORT_SOURCE_OF_TRUTH.md`; Home actions route through
the canonical state service and do not touch learner challenge files. Any future
Bug Hunt run should use a disposable connected project and remain separate from
this Home parity verification.
