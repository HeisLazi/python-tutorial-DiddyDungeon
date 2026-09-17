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
