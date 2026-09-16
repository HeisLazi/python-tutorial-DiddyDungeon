# Quest Lab end-to-end bug hunt — 2026-09-16

This is the persistent bug-hunt ledger. It is intentionally outside temporary
runtime directories so a workstation reset does not erase findings.

## Scope and custody

- Branch: `feature/cloud-sync-desktop`
- Protected files: repository `progress.json` and root Campaign `tutor.py`
- Legacy/workspace evidence: read-only and non-authoritative
- Test policy: browser K&M only; no Playwright; disposable isolated state and
  unused ports; no restart/reset of existing shell or AI PTYs
- Scoring: P0=8, P1=5, P2=3, P3=1; +1 minimal reproduction; −2 false positive;
  duplicates score 0

## Baseline

The hunt ran on `feature/cloud-sync-desktop` at
`c107d84835d9f7eeebd7f8501c17ea057b616727`. The local origin ref was still
`3736df6`, so the read-only preflight used `-AllowStaleCheckout`; no pull,
reset, rebase or force push was performed.

- Disposable WSL runtime: backend `7395`, frontend `5215`
- Disposable workspace: `/tmp/questlab-e2e-ws-20260916-2`
- Disposable state root: `/tmp/questlab-e2e-state-20260916-2`
- Preflight: GREEN with `-RequireIsolatedState`; canonical cache was a
  custody-approved copy at revision 5, while the workspace `progress.json`
  was reported as legacy/non-authoritative.
- Protected repository `progress.json` remained SHA-256
  `5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`.
  Root `tutor.py` remained user-owned and untracked; neither was staged or
  written.
- Deterministic gates: backend **79/79**, frontend **36/36**, Python
  `compileall`, PowerShell preflight parse, and Vite **1,345-module** build
  all passed.
- Browser policy: pure in-app-browser click/scroll/type/screenshot K&M only;
  no Playwright. Settings, Tutor Notebook, Practice, Quest Journal, Codex,
  Character, Homestead, Infinite Dungeon, campaign verdict/reward, context
  isolation and stray-save custody paths were exercised.
- Baseline Forge after hydration visibly showed Level 2, 50/100 XP, 55
  coins, Mob 3 `The Hitman`, SVG heart/coin/flame/shield/sword icons and both
  shell/AI PTYs `CONNECTED`.

## Findings

### BUG-2026-09-16-001 — P2 — fixed

- Reporter: Copilot (read-only source review)
- Surface: PYR context bridge (`ide/server/app_v2.py`)
- Problem: context input was stored in one process-global singleton, so a
  tab-A GET could receive tab-B's active file/selection/terminal context.
- Reproduction: POST context with selection `marker-A`, POST another with
  `marker-B`, then GET each tab; before the fix the later singleton value was
  returned for both.
- Repair: named client payloads now live in `PYR_CONTEXT_INPUTS`; GET accepts
  `client_id` and reads only that partition. The legacy singleton remains
  only for default-client compatibility.
- Evidence: new `test_context_reads_are_isolated_per_tab`; visible shell probe
  printed `CTX marker-A marker-B` on the patched runtime.
- Score: 4 (P2=3 plus one minimal reproduction point).

### BUG-2026-09-16-002 — P3 — fixed

- Reporter: Copilot (read-only documentation review)
- Surface: `CLOUD_DESKTOP_IMPLEMENTATION_REPORT.md`
- Problem: an earlier Known Limitations paragraph called Dungeon and Practice
  unfinished even though later sections documented the completed local slice,
  creating contradictory release guidance.
- Repair: wording now distinguishes the locally implemented/proven Dungeon and
  Practice slices from the still-gated hosted/provider work.
- Score: 1 (P3).

### BUG-2026-09-16-003 — P2 — fixed

- Reporter: Claude **Sonnet** (read-only source review)
- Surface: `ide/server/app_v2.py` and `ide/server/app.py` PTY environment setup
- Problem: prepending the editable repository root to `PATH` allowed a file
  named `python3`, `git`, `curl`, or similar to shadow the inherited command.
- Repair: inherited `PATH` is retained first and the repository root is
  appended; `questlab-state` remains discoverable without changing normal
  command resolution. A regression assertion checks the repository path is
  the final PATH entry.
- Score: 4 (P2=3 plus one minimal reproduction point).

### Primary K&M result — no new scored defects

The full path completed without a new reproducible UI or behavior defect. The
previous nested stat-pill regression stayed fixed: the 1280×720 screenshot
showed all five monochrome SVG icons with no empty nested pills. Revision
polling kept the HUD, Journal, Codex and Character projections coherent after
state-service mutations; browser console warnings/errors were empty. Hidden
future encounter details remained hidden as designed and were not scored.

## Reviewer scoreboard

| Reviewer | Confirmed unique bugs | Weighted points | False positives | Duplicates | Result |
|---|---:|---:|---:|---:|---|
| Primary | 0 | 0 | 0 | 0 | — |
| Claude Sonnet | 1 | 4 | 0 | 0 | second |
| Copilot | 2 | 5 | 0 | 0 | winner |

Copilot wins on weighted points (5) and unique findings (2); Claude Sonnet
scored 4 on one unique finding. Both reviews were read-only and ran without
touching the protected save, notebook, runtimes or PTYs.

## Live acceptance evidence

- A visible Forge shell submitted two valid state-service objective verdicts
  on the disposable cache. Toasts showed `OBJECTIVE VERIFIED`, then
  `MOB DEFEATED The Hitman +30 XP · +15 Coins` and `NEXT ENCOUNTER The Bust
  Hound Unlocked by the verified clear`; no browser refresh occurred.
- HUD changed live from 50 XP / 55 coins to 80 XP / 70 coins. Quest Journal
  changed to four cleared mobs, current `The Bust Hound` at `7 / 7` Resolve
  and 50% project progress. Codex showed encounter records for the prior
  mobs and the newly recorded validated result. Character showed the same
  level/XP/coins and validated `First Blood`; no unsupported equipment,
  mastery or companion rewards were invented.
- Earlier in the same disposable hunt, Settings, Tutor save/run/format,
  Practice no-provider guard, Dungeon start/checkpoint/bank/restart,
  Homestead purchase/equip and live reward notifications were exercised.
- After writing a synthetic Level 99/999-coins file to the disposable
  workspace `progress.json`, the HUD stayed Level 2 / 70 coins. The visible
  `questlab-state authority` report showed `canonical_authoritative: true`,
  `legacy_authoritative: false`, and `legacy_requires_approval: true`.
- Both shell and AI PTYs remained `CONNECTED` throughout the actions; no
  reconnect or PTY reset was used.

## Open infrastructure gates carried forward

Provider-authenticated adjudication, hosted Dungeon/cross-device state,
explicit real-save custody migration, the OneDrive WSL native-dependency
limitation, and real second-Windows/Tauri proof remain approval-gated until
this hunt produces evidence to change them.

## Follow-up milestone — 2026-09-16 — native Linux preflight and K&M smoke

The native Linux preflight milestone ran from commit
`4801fd93a04e0a7cf0650be1e60313f6a65cceea` on disposable ports `7415/5225`
with workspace `/tmp/questlab-km-linux-ws-20260916-a` and state root
`/tmp/questlab-km-linux-state-20260916-a`. The Python preflight returned
**GREEN** before and after mutation at revisions 5 and 7, confirmed the
current branch/HEAD, distinct canonical/legacy paths and isolated custody, and
used only Git reads and HTTP GETs.

Pure in-app-browser K&M then opened Forge and visited Forge, Character, Quest
Journal, Codex, Homestead, Campaign Tutor, Infinite Dungeon, Practice and
Settings. A visible shell PTY recorded one learning event and one trusted
state-service reward; without a browser refresh the reward toast appeared,
HUD coins changed 55 → 56, Character showed Level 2 / 51 XP / 56 coins,
Journal retained The Hitman at 8/8, Codex retained three encounter books and
Homestead showed canonical revision 7 / 56 coins. Shell and AI labels remained
`CONNECTED`, and the browser error/warning log was empty. The five SVG HUD
icons remained visible with no nested pills.

The first direct test command used system `python3` from the quest workspace
and failed to import the backend's optional `fastapi` dependency; this was a
test-harness command mistake, not an app path or state mutation. The supported
`questlab-state` wrapper and the absolute project virtualenv command succeeded;
it was not scored as a product bug. Disposable runtime, cache and workspace
were stopped and removed; protected user files and existing PTYs were not
touched.

## Follow-up milestone — 2026-09-16 — local sync simulator and current-tip K&M

The local two-device simulator was exercised from pushed commit
`322d5ffc144f0c06d7528a3bb83b31e657c1c517` with the protected repository save
as a read-only source. Two temporary `LocalStateService` caches and an
in-memory compare-and-swap mailbox produced cloud revisions `1 → 3`; both a
stale mailbox push and the offline stale pull were rejected with `409`, and an
explicit keep-device resolution emitted `sync_apply_cloud`. The source digest stayed
`5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0` before
and after. The contract test and CLI both passed; no finding was scored.

A fresh isolated runtime on backend `7425` / frontend `5235` passed the native
Linux preflight at revision 5, then pure in-app-browser click/scroll/type K&M
recorded a visible learning event (revision 6) and trusted state-service
reward (revision 7). Without refresh, the reward toast showed `+1 XP · +1
Coins`, the HUD changed to Level 2 / 51 XP / 56 coins, Character and
Homestead showed the same projection, Quest Journal retained three cleared
mobs with The Hitman at `8 / 8`, and Codex retained three encounter books.
Both shell and AI PTY labels stayed `CONNECTED`; all five monochrome SVG icons
remained visible. The isolated cache, runtime and browser tab were removed
afterward; the protected save and root `tutor.py` were untouched.

The first shell probe placed the global `--backend-port` option after its
subcommand and argparse rejected it; the corrected command succeeded. This
was a test-harness usage error, did not mutate state, and was not scored as a
product bug. No new primary K&M defect was confirmed.
