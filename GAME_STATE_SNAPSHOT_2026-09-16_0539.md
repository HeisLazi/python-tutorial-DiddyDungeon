# Quest Lab game-state snapshot — 2026-09-16 05:39 +02

Read-only baseline captured after the current pushed-tip regression and clean
ext4 distribution K&M checks. No canonical save, legacy evidence file, PTY,
hosted resource or user-owned notebook was changed by the checks.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `0dbb7ff287758bfb0dae33cfa4d41ff305e87bc0`
- Working-tree boundary: only the user-owned `progress.json` is modified and
  the user-owned root `tutor.py` is untracked; neither is staged or replaced.
- Canonical local save:
  `C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
- Canonical SHA-256: `b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce6070`
- Legacy evidence only: `/home/lazi/projects/questlab-blackjack/progress.json`
- Legacy SHA-256: `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
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
- Frontend: **33/33** tests; Windows Vite build transformed **1,345 modules**
- Clean ext4 clone of this branch installed with `npm ci`, built successfully,
  passed paired preflight, and served stable PTYs on disposable `7357/5193`.
- Pure in-app-browser K&M (no Playwright, no refresh) observed typed valid
  state-service requests reduce Resolve **4/4 → 2/4**, then update HUD to
  **25 XP / 10 coins**, show mob defeat/next encounter/First Blood feedback,
  update Journal to The Dealer's Hand **6/6**, add a Codex encounter record,
  and keep Character, Homestead, shell PTY and AI PTY coherent.
- Disposable clone, runtime and mutated starter save were removed afterward.

## Remaining gates

- Real second-Windows friend-machine launch is still required; clean ext4 is
  not a substitute for that gate.
- F-039 save-custody migration remains opt-in and has not touched the player's
  tracked cache.
- Hosted provider-authenticated sync/avatar, Tauri, public web and social
  stages remain approval-gated; no Supabase seed or write was made.
