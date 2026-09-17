# Quest Lab game-state snapshot — 2026-09-16 06:05 +02

Read-only baseline after the authenticated Claude review, rollback hardening,
and exact-tip browser check. No canonical save, legacy evidence file, PTY,
hosted resource or Campaign notebook was changed by these checks.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `a71fe4113971865a504ec9bcb56f3d9cb4905b38`
- Code-fix ancestor: `c8dba226829d81d56e89d24dab4ed03325ef0e28`
- Working-tree boundary: only the user-owned `progress.json` is modified and
  the user-owned root `tutor.py` is untracked; neither is staged or replaced.
- Canonical local save:
  `C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
- Canonical SHA-256:
  `b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce6070`
- Legacy evidence only: `/home/lazi/projects/questlab-blackjack/progress.json`
- Legacy SHA-256:
  `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
- The legacy file remains read-only evidence and is not authoritative.

## Canonical campaign state

Canonical revision remains **2**:

- Level **2**, **50 / 100 XP**, **150 lifetime XP**, **55 coins**
- HP **100 / 100**, potions **2**
- Blackjack project progress **38%**
- Cleared: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active: **The Hitman**, **8 / 8 Resolve**, no current objectives verified
- Achievement: **First Blood**
- Equipment: Training Blade, Apprentice Coat, no trinket, Apprentice Coder
- Companion: PYR, Tiny Code-Flame, level 1, bond 0
- Codex: **3** validated encounter records; unsupported mastery, shield,
  companion and reward history were not inferred
- State-event ledger: **2** approved legacy-reconciliation events

## Current verification evidence

- Backend: **77/77** WSL tests; Python `compileall -q ide` passed
- Frontend: **35/35** tests; Windows Vite build transformed **1,345 modules**
- PowerShell K&M preflight source parses after native-Git exit handling was
  hardened for missing remote refs.
- Authenticated Claude Opus read-only review found no P0/P1 issues. Its two
  P2 findings and one P3 reward edge case are fixed and logged.
- A clean ext4 clone at pushed code tip `c8dba22` ran on disposable ports
  `7359/5195`. Pure in-app-browser K&M (no Playwright, no refresh) showed the
  monochrome heart/coin/streak/shield/boss icons, both shell and AI PTYs
  `CONNECTED`, and a validated Battle verdict changed Resolve **4/4 → 2/4**
  with an `OBJECTIVE VERIFIED` reward card.
- Disposable clone, runtime and mutated starter save were removed afterward.

## Remaining gates

- Real second-Windows friend-machine launch is still required; clean ext4 is
  not a substitute for that gate.
- F-039 save-custody migration remains opt-in and has not touched the player's
  tracked cache.
- Hosted provider-authenticated sync/avatar, Tauri, public web and social
  stages remain approval-gated; no Supabase seed or write was made.
