# Quest Lab game-state snapshot — 2026-09-16 06:25 +02

Read-only checkpoint after the guarded-launcher hardening and current-tip K&M
run. No canonical save, legacy evidence, long-lived runtime, PTY, hosted
resource or Campaign notebook was changed.

## Source and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `825d7408db11fe69d6965554d97d389b69983d67`
- Working tree: only the player's modified `progress.json` and untracked
  Campaign `tutor.py`; neither is staged or bundled.
- Canonical SHA-256:
  `b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce6070`
- Legacy evidence SHA-256:
  `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
- Workspace `progress.json` remains evidence only; the state service is the
  sole local progression authority.

## Canonical campaign state

- Revision **2**; Level **2**; **50/100 XP**; **150 lifetime XP**; **55 coins**
- HP **100/100**; potions **2**; Blackjack progress **38%**
- Cleared: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active: **The Hitman**, Resolve **8/8**
- **First Blood**; Training Blade; Apprentice Coat; no trinket; Apprentice
  Coder; PYR Tiny Code-Flame; 3 Codex encounter records
- Two approved reconciliation events; unsupported mastery/shields, companion
  evolution, interview completion and exact legacy rewards remain un-inferred.

## Verification

- Backend **77/77**, frontend **35/35**, launcher contracts **9/9**,
  `compileall -q ide`, PowerShell parsing and Vite **1,345 modules** all pass.
- A fresh ext4 clone at `55acb0b` ran stable PTYs on backend `7361` / frontend
  `5197`. Pure in-app-browser click/type/scroll actions, without Playwright or
  refresh, showed the current branch, monochrome HUD icons and both PTYs
  `CONNECTED`; a shell-typed state-service verdict changed Resolve **4/4 →
  2/4**, and Quest Journal showed **2/4** plus `OBJECTIVE VERIFIED`.
- The disposable clone/runtime/save were removed afterward.

## Remaining gates

The real second-Windows launch and F-039 custody decision remain open. Hosted
provider-authenticated adjudication, Supabase two-device sync, hosted Dungeon/
avatar, Tauri, public and social stages remain approval-gated; no Supabase
seed/write or public deployment was performed.
