# Quest Lab game-state snapshot — 2026-09-16 04:38 +02

This is a read-only capture before the next roadmap slice. It records the
canonical local save, the non-authoritative legacy evidence, and the runtime
boundary. No save, legacy file, PTY or hosted resource was changed while
capturing it.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD: `61c6ebf` (`docs: record current regression gates`)
- Windows content status: only the user-owned `progress.json` is modified and
  the user-owned root `tutor.py` is untracked. Neither is staged or overwritten.
- Canonical local save: `C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
- Canonical SHA-256 at capture: `b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce6070`
- Legacy evidence only: `/home/lazi/projects/questlab-blackjack/progress.json`
- Legacy SHA-256 at capture: `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
- The legacy file was read only; it was not copied, merged, deleted or made
  authoritative.

## Canonical campaign projection

The canonical `progress.json` and its state-event ledger show revision `2`:

- Player: **Lazi**, Level **2**, **50 / 100 XP**, **150 lifetime XP**, **55 coins**
- HP: **100 / 100**; potions: **2**
- Project: `01-blackjack`, phase `forge`, progress **38%**
- Cleared mobs: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active encounter: **The Hitman** (Mob 3), **8 / 8 Resolve**, zero verified
  objectives and zero attempts recorded in the canonical encounter state
- Next locked encounters: The Bust Hound, The House Clerk, The Judge and The
  Rematch Shade
- Achievement: **First Blood** unlocked; no unsupported equipment, mastery,
  shield, companion or boss reward was inferred
- Equipment: Training Blade, Apprentice Coat, None trinket, Apprentice Coder
- Companion: PYR, Tiny Code-Flame, level 1, bond 0
- Homestead equipped set: Forge theme, basic cursor, Forge HUD and charcoal
  terminal
- Codex: three encounter records, one for each cleared mob, each backed by
  `legacy-blackjack-2026-09-14`; attempts/question types/weaknesses/mastery
  remain zero or empty where no evidence exists
- Last session: cleared Mob 0, Mob 1 and Mob 2 cleanly; approaching Mob 3

The two canonical state events are approved legacy reconciliation records at
revisions 1 and 2. They explicitly mark `reward_history_inferred=false` and
record the restored fields, the three cleared mobs, the Mob 3 unlock, 38%
project progress, First Blood and the three Codex records.

## Runtime boundary

The long-lived process tree includes the Forge supervisor (`ide/quest.py`, PID
111021), its backend (PID 111022 on port 7332) and its Vite child (PID 111035
on port 5173). These processes were not restarted. The backend's `/api/runtime`
still returns the old `{shell, python, commands}` health shape and
`/api/state/revision` is unavailable there; the visible 5174 browser proxy is
therefore stale-runtime evidence rather than proof of the current branch UI.
The branch-aware paired preflight and pure K&M evidence remain the authoritative
current-branch browser checks; the latest exact-tip code check was the isolated
`ea8f878` runtime, followed only by documentation commits.

## Verification boundary

- WSL backend: **77/77** with the project `.venv/bin/python`
- Frontend: **33/33**
- Python `compileall`: passed
- Windows Vite production build: passed; 1,345 modules transformed and only
  the existing large-chunk advisory
- Browser policy: pure in-app-browser keyboard/mouse/scroll checks only; no
  Playwright used
- Hosted Supabase state, Tauri and social features: intentionally not started
  and require their previously documented approval gates

This snapshot is an evidence baseline for the next implementation/review
stage, not a claim that the hosted roadmap gates are complete.
