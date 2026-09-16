# Quest Lab game-state snapshot — 2026-09-16 07:05 +02

Read-only continuation checkpoint. The canonical save, legacy evidence,
long-lived runtimes and PTYs were not edited, restarted or reset while this
snapshot was collected.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD and origin: `f9ee5124fd3f1f99cd48cafaa8a8fd8b0ca43879`
- Working tree: user-owned modified `progress.json` and untracked Campaign
  `tutor.py`; neither is staged, bundled or changed by this checkpoint.
- Canonical Windows cache:
  `C:\Users\lazar\OneDrive\Documents\ChatGPT\Python Quest Lab\progress.json`
- Canonical SHA-256:
  `b80c89ce3606f626f5b0565ad121f03fb14868d92410933d338f3fbc03ce6070`
- Legacy evidence:
  `/home/lazi/projects/questlab-blackjack/progress.json`
- Legacy SHA-256:
  `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
- The state-service `legacy-report` marks the canonical path authoritative,
  the legacy path non-authoritative, and manual approval required. No merge,
  copy or newest-file heuristic was used.

## Canonical campaign state

- Schema 4 / rules 1.5.0; revision **2**
- Player: **Level 2**, **50/100 XP**, **150 lifetime XP**, **55 coins**
- HP **100/100**; potions **2**; current streak **1**; last active
  `2026-09-14`
- Blackjack progress **38%**
- Defeated: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active next encounter: **The Hitman**, Resolve **8/8**
- Locked after it: The Bust Hound, The House Clerk, The Judge and The Rematch
  Shade
- Achievement: **First Blood**
- Equipment: Training Blade, Apprentice Coat, no trinket, Apprentice Coder
- Companion: PYR Tiny Code-Flame, level 1, bond 0
- Codex: **3** validated encounter records, each backed by the approved legacy
  evidence id; attempts, exact question types, mastery/shields, interview
  completion, companion evolution and unsupported reward history remain
  un-inferred.

## Evidence and roadmap status

- The read-only legacy report matched all supported progression fields. Its only
  differences are the expected legacy schema/rules/revision representation and
  `cleared` versus canonical `defeated` wording.
- Backend **77/77**, frontend **35/35**, launcher contracts **9/9**, Python
  compile, PowerShell parsing and Vite **1,345-module** build are green.
- The latest pure click/scroll/type K&M evidence (06:50) showed Level 2 / 50
  XP / 55 coins, The Hitman 8/8, three cleared mobs, three Codex records,
  visible monochrome HUD SVG icons and both PTY labels `CONNECTED`; no refresh
  and no Playwright were used. The earlier disposable current-tip mutation
  proved live Resolve/reward projection without resetting either PTY.
- Old listeners on ports 5173/5174 and 7332–7334 are pre-existing legacy
  runtimes and remain untouched. No new runtime was started for this snapshot.
- Remaining roadmap gates are the real second-Windows launch, explicit F-039
  save-custody decision, provider-authenticated adjudication, hosted
  Supabase sync/avatar, Tauri packaging and social features. Weekly raid
  combat remains intentionally unimplemented.
