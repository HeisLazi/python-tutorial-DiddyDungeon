# Quest Lab game-state snapshot — 2026-09-16 02:24 +02:00

This is a read-only snapshot of the current working-tree save. It does not
change `progress.json`, reconcile legacy files, or contact Supabase.

## Authority and custody

- Branch: `feature/cloud-sync-desktop`
- Remote HEAD at capture: `569481e` (`test: cover private avatar migration contracts`)
- Canonical local authority: platform checkout `progress.json` through the
  LocalStateService/state gateway
- Canonical revision: `2`
- Save updated at: `2026-09-15T08:55:40.868291+02:00`
- Legacy/workspace save: non-authoritative evidence only
- Working-tree boundary: `progress.json` is user-owned and dirty; Campaign
  `tutor.py` is user-owned and untracked; neither is staged or modified here

## Player projection

| Field | Value |
| --- | --- |
| Level | 2 |
| Current XP | 50 / 100 |
| Lifetime XP | 150 |
| Coins | 55 |
| HP | 100 / 100 |
| Blackjack progress | 38% |
| Defeated Blackjack mobs | The Empty Table; The Dealer's Hand; The Count Keeper |
| Active encounter | The Hitman |
| Current Resolve | 8 / 8 |
| Codex encounter records | 3 |
| State-service events | 2 reconciliation events |
| Unlocked achievements | First Blood |

## Encounter and progression boundary

The Hitman is available with a clean starter encounter state: zero completed
objectives, zero attempts and no question types recorded yet. The Bust Hound
and later encounters remain locked. The canonical equipment remains Apprentice
Coat / None / Apprentice Coder; PYR remains Tiny Code-Flame level 1 with bond
0. No unsupported equipment, mastery, shield, companion or interview rewards
were inferred.

## Verification context

- Local contract suite: 6/6 focused tests passed, including private avatar,
  identity-RLS and bounded player-state coverage.
- Full WSL backend suite: 75 tests passed.
- Frontend suite: 33 tests passed.
- Windows Vite production build: 1,345 modules transformed successfully.
- Prior disposable K&M evidence remains green for live HUD, Resolve, mob
  unlock, Codex, Homestead, Tutor/Practice separation and connected shell/AI
  PTYs; no Playwright was used.
- Hosted Milestone C/D, save-custody approval, Tauri, public-safe web and
  hosted social stages remain gated and unexecuted.
