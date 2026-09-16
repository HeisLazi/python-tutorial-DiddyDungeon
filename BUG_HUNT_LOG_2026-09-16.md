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

To be filled with the current commit, isolated runtime, deterministic gate
counts, browser surfaces exercised, and reviewer results after the run.

## Findings

No findings recorded yet for this run.

## Reviewer scoreboard

| Reviewer | Confirmed unique bugs | Weighted points | False positives | Duplicates | Result |
|---|---:|---:|---:|---:|---|
| Primary | 0 | 0 | 0 | 0 | pending |
| Claude | 0 | 0 | 0 | 0 | pending |
| Copilot | 0 | 0 | 0 | 0 | pending |

## Open infrastructure gates carried forward

Provider-authenticated adjudication, hosted Dungeon/cross-device state,
explicit real-save custody migration, the OneDrive WSL native-dependency
limitation, and real second-Windows/Tauri proof remain approval-gated until
this hunt produces evidence to change them.
