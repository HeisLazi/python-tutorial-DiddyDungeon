# Quest Lab state snapshot — 2026-09-16 10:44 +02

## Scope

Read-only checkpoint before the next commit. The protected Windows canonical
save and the untracked Campaign `tutor.py` were inspected but not edited,
staged or reset. Legacy quest-workspace files remain evidence only.

## Canonical local projection

- Canonical path: repository `progress.json` (state-service authority)
- Revision: **5**
- Player: Lazi, Level **2**, **50/100 XP**, lifetime XP **150**, **55 coins**
- HP: **100/100**; streak **1**; potions **2**
- Active project: **Blackjack**, progress **38%**
- Cleared mobs: The Empty Table, The Dealer's Hand, The Count Keeper
- Current encounter: The Hitman, Resolve **8/8**
- Codex encounter records: **3**; unlocked achievement: **First Blood**
- Validated equipment: **Apprentice Coat**; trinket: **None**

Canonical SHA-256: `5618F9DD9AE2FC0724056EA08448E1736479772B59ADA949BEC08B5340FBD6F0`

## Checkpoint changes

- Codex shows safe projection metrics and page-level recorded question/weakness
  signals; existing bounded notes and encounter evidence remain the source.
- Homestead shows a live-loadout/economy summary with Level, XP, armor, trinket,
  coins and canonical revision, plus a small live scene badge.
- `uiPolish.js` now exits before touching `data-react-stat="true"` nodes, so
  revision polling cannot rewrite React-owned SVG stat icons into legacy glyph
  markup or nested pills.
- `tools/questlab-launch.ps1` and handoff examples invoke `ide.quest` as a
  module with `PYTHONPATH=.`; mounted-checkout custody setup no longer fails at
  `import ide`.

## Verification

- WSL backend suite: **78/78** passing.
- Frontend source/runtime suite: **36/36** passing.
- Python `compileall -q ide`: passing.
- PowerShell preflight parser: passing.
- Vite production build: **1,345 modules**, passing with the existing large
  chunk advisory.
- Disposable explicit-local-state Forge at `http://127.0.0.1:5212/` was
  checked using CUA click/scroll/type/screenshot actions only (no Playwright).
  It visibly showed Level 2 / 50 XP / 55 coins, the five monochrome HUD icons,
  Codex evidence metrics, Homestead live-loadout data and both shell/AI panes
  `CONNECTED`. The disposable runtime and state roots were stopped and
  removed afterward.

## Protected boundary and remaining gates

- Working tree intentionally remains dirty only in the user's `progress.json`
  and untracked `tutor.py`; neither is part of this checkpoint commit.
- No Supabase login/seeding or hosted player-state transport was started.
- Real second-Windows friend launch, F-039 save-custody choice,
  provider-authenticated adjudication, hosted Milestone C, Tauri and social
work remain approval-gated.

## Read-only peer review

Claude Sonnet found no P0/P1 issue. Its pre-existing P2 note about loose
Codex page fallback matching was fixed with an exact/prefix concept match and
source-tested. The frontend suite remains a source-regex gate supplemented by
the rendered CUA acceptance; this is a known P3 boundary. Claude did not run
commands or touch the save, notebook, runtimes or PTYs.
