# Quest Lab game state snapshot — 2026-09-16 02:52 +02:00

## Canonical local state

Read-only projection from the current canonical state service (port 7333):

- revision: `2`
- player: Level `2`, `50 / 100` current XP, `150` lifetime XP, `55` coins
- active encounter: Blackjack / `The Hitman`, Resolve `8 / 8`
- defeated mobs: `The Empty Table`, `The Dealer's Hand`, `The Count Keeper`
- Blackjack project progress: `38%`
- Codex encounter records: `3`
- state events: `2`
- achievement: `First Blood`
- validated equipment: `Apprentice Coat`, `None` trinket, `Apprentice Coder`
- companion: `PYR / Tiny Code-Flame`, level `1`, bond `0`

The service reports the canonical path as
`/home/lazi/projects/python-tutorial-DiddyDungeon/progress.json` and the
quest-workspace `progress.json` as legacy/non-authoritative evidence. The
working-tree `progress.json` and root `tutor.py` remain user-owned dirty files;
neither was edited or staged.

## Runtime identity boundary

The long-lived 5174 Vite process has the current OneDrive checkout as its cwd,
but its transformed `AppV2.jsx` is an older cached bundle (emoji stats and no
`campaignReady` guard). This is the known WSL-mounted-source stale-runtime
case; it was not restarted. The long-lived 5173/7332 runtime is also left
untouched.

A fresh disposable ext4 clone from branch `feature/cloud-sync-desktop` at
`71fdb9e1dedf3aee0474ac7c259b6cc6b420c46e` served the current SVG/loading
source on 5177/7343. Its runtime health showed the expected branch, matching
upstream SHA, canonical state path and non-authoritative legacy path.

## Disposable K&M evidence

Using only the in-app browser accessibility/click surface (no Playwright and
no browser refresh):

1. Initial UI showed `SYNCING` placeholders, then settled to the disposable
   starter campaign without a refresh; shell and AI PTYs both showed
   `CONNECTED`.
2. A canonical verified Battle objective changed revision `0 → 1`; the HUD
   reward presentation showed the objective and Quest Journal showed Resolve
   `2 / 4`.
3. A second verified objective changed revision `1 → 2`; the UI showed
   `MOB DEFEATED The Empty Table +25 XP · +10 Coins`, `NEXT ENCOUNTER The
   Dealer's Hand`, and `ACHIEVEMENT UNLOCKED First Blood`. HUD became
   `25 / 100` XP and `10c`; Journal showed the next mob and the Codex showed
   one defeated encounter record. Character/Homestead reflected the same
   `10c` state in the companion current-branch disposable run.

The disposable tabs and runtimes were closed after the read-only acceptance;
the long-lived user PTYs and runtimes were not restarted.
