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

## Follow-up slice — adaptive Dungeon mob identity — 2026-09-17

The next disposable runtime rehydrated the current Dungeon checkpoint with the
patched state service. Browser K&M showed the state-owned current mob banner:
`The Boundary Hunter`, `bug hunt · Input loops and control flow`, `PHASE I`, and
`DIFFICULTY 1`. The selector still exposed no future mob names or questions;
only the issued encounter carried the descriptor. Shell and AI remained
`CONNECTED`, and browser warning/error logs were empty before teardown.
Backend tests cover the descriptor and verdict event (`97/97` total); the
frontend source suite is **39/39**.
