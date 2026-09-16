# Quest Lab game-state snapshot — 2026-09-16 05:26 +02

This is a read-only campaign and verification baseline captured after the
exact current-tip browser acceptance run. The disposable test clone was
stopped and removed afterward; the user's canonical save, legacy evidence,
long-lived PTYs and stale runtimes were not changed.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `c4b08da556f8ccc8f9a5bdf18be452e323e2ed74`
- Windows content status: only the user-owned `progress.json` is modified and
  the user-owned root `tutor.py` is untracked. Neither was staged or
  overwritten.
- Canonical local save:
  `C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
- Canonical SHA-256 at capture:
  `b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce6070`
- Legacy evidence only: `/home/lazi/projects/questlab-blackjack/progress.json`
- Legacy SHA-256 at capture:
  `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
- The legacy file was read only; it was not copied, merged, deleted or made
  authoritative.

## Canonical campaign projection

The canonical save and state-event ledger remain at revision `2`:

- Player: **Lazi**, Level **2**, **50 / 100 XP**, **150 lifetime XP**,
  **55 coins**
- HP: **100 / 100**; potions: **2**
- Project: `01-blackjack`, phase `forge`, progress **38%**
- Cleared mobs: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active encounter: **The Hitman**, **8 / 8 Resolve**, zero verified
  objectives and zero attempts in the current encounter state
- Achievement: **First Blood** unlocked
- Equipment: Training Blade, Apprentice Coat, None trinket, Apprentice Coder
- Companion: PYR, Tiny Code-Flame, level 1, bond 0
- Codex: three encounter records, one for each cleared mob, backed by
  `legacy-blackjack-2026-09-14`; no unsupported mastery, shield, companion or
  reward history was inferred.

## Exact current-tip K&M evidence

The paired preflight was GREEN on disposable backend `7356` and frontend
`5192` at revision `0`, using source `c4b08da`. With only in-app-browser
accessibility keyboard/mouse actions (no Playwright and no browser refresh),
shell-typed valid state-service requests produced:

1. The Empty Table Resolve changed **4 / 4 → 2 / 4** and the HUD remained
   live while both Forge terminal and AI PTY showed **CONNECTED**.
2. The next valid objective cleared The Empty Table, advancing the disposable
   test revision **0 → 1 → 2**. The live HUD showed **25 XP / 10 coins** and
   queued validated notifications for the mob defeat, next encounter unlock
   (The Dealer's Hand) and First Blood.
3. Without refreshing, Quest Journal showed the cleared mob, The Dealer's Hand
   at **6 / 6**, project progress **12%**, and weekly progress **1 / 2**.
4. Codex showed **8 records indexed**, the encounter result/evidence entries
   and no hidden future answers. Character showed the same live XP/coins and
   First Blood; Homestead showed the live purse and disabled purchases because
   the disposable balance was only 10 coins.

The mutated disposable save was not the canonical save and was removed with
its temporary clone/runtime. This proves the live projection path without
claiming that the real Level 2 save was changed by the test.

## Verification boundary

- WSL backend: **77/77**; frontend: **33/33**; production build: passed
- Browser policy: pure in-app-browser keyboard/mouse/scroll checks only; no
  Playwright used
- Long-lived shell and AI PTYs: retained; no PTY reset
- Hosted Supabase state, Tauri and social features: intentionally not started
  and remain approval-gated
- Remaining local-distribution gate: clean Linux/WSL dependency install and a
  real second-Windows launch; the OneDrive checkout still fails closed on
  missing Linux Rollup optional dependencies.

