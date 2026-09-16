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
