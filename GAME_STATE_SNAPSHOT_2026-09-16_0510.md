# Quest Lab game-state snapshot — 2026-09-16 05:10 +02

This is a read-only capture of the current local campaign before the next
roadmap stage. No save, legacy file, PTY, listener or hosted resource was
changed while capturing it.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `c5c3535` (`feat: enrich codex evidence projection`)
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

The canonical save and state-event ledger show revision `2`:

- Player: **Lazi**, Level **2**, **50 / 100 XP**, **150 lifetime XP**,
  **55 coins**
- HP: **100 / 100**; potions: **2**
- Project: `01-blackjack`, phase `forge`, progress **38%**
- Cleared mobs: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active encounter: **The Hitman**, **8 / 8 Resolve**, zero verified
  objectives and zero attempts in the current encounter state
- Next locked encounters: The Bust Hound, The House Clerk, The Judge and The
  Rematch Shade
- Achievement: **First Blood** unlocked; no unsupported equipment, mastery,
  shield, companion or boss reward was inferred
- Equipment: Training Blade, Apprentice Coat, None trinket, Apprentice Coder
- Companion: PYR, Tiny Code-Flame, level 1, bond 0
- Homestead equipped set: Forge theme, basic cursor, Forge HUD and charcoal
  terminal
- Codex: three encounter records, one for each cleared mob, each backed by
  `legacy-blackjack-2026-09-14`; attempts, question types, weaknesses and
  mastery remain empty or zero where no evidence exists
- Current quest: `Blackjack — Mob 3: The Hitman (repeatedly choose hit or
  stand).`

The two canonical state events are approved legacy-reconciliation records at
revisions 1 and 2. They mark `reward_history_inferred=false` and record only
the restored fields, three cleared mobs, the Mob 3 unlock, 38% progress,
First Blood and the three Codex records.

## Runtime boundary

Read-only process inspection still finds several long-lived/stale listeners on
7332–7334 and 5173–5175, plus disposable/older 7340 and 7341 processes. They
were not restarted or killed. The paired branch-aware preflight remains the
authoritative gate for current-source browser evidence; a visible old runtime
must not be treated as this checkout's UI.

## Verification boundary

- WSL backend: **77/77** with the project `.venv/bin/python`
- Frontend: **33/33**
- Windows Vite production build: passed; **1,345 modules transformed**, with
  only the existing large-chunk advisory
- Browser policy: pure in-app-browser keyboard/mouse/scroll checks only; no
  Playwright used
- Latest paired K&M checkpoint: current source preflight GREEN on backend
  `7354` / frontend `5190`, revision 2; Codex search and validated insight
  projection were observed without refresh
- Hosted Supabase state, Tauri and social features: intentionally not started
  and remain approval-gated

This snapshot is an evidence baseline for the next local-distribution stage,
not a claim that the hosted roadmap gates are complete.
