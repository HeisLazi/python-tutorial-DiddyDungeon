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
