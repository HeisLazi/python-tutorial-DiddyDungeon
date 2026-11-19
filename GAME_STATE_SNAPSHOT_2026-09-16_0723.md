# Quest Lab game-state snapshot — 2026-09-16 07:23 +02

Read-only post-acceptance checkpoint. The browser test runtime was stopped and
its disposable workspace removed. The protected canonical cache was not edited
directly; the test's Dungeon start/checkpoint and the bounded no-reward cleanup
were recorded through the canonical state service.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Pushed HEAD before this documentation update:
  `238d4ebed4ac02d8f863a85f8155cb601dd78e0a`
- Working tree still contains only the user's modified `progress.json` and
  untracked Campaign `tutor.py`; neither is staged.
- Canonical cache SHA-256 after the recorded test cleanup:
  `5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`
- Legacy evidence SHA-256 (unchanged/read-only):
  `200f5b8c1c87040dc522dbf6f8397c47c035bd036312601ee731180021e6744c`
- The legacy-report authority remained canonical=true and legacy=false.

## Canonical campaign state

- Revision **5**; Level **2**; **50/100 XP**; **150 lifetime XP**; **55 coins**
- HP **100/100**; potions **2**; streak **1**; Blackjack progress **38%**
- Defeated: **The Empty Table**, **The Dealer's Hand**, **The Count Keeper**
- Active campaign encounter: **The Hitman**, Resolve **8/8**
- First Blood; Training Blade; Apprentice Coat; no trinket; Apprentice Coder
- PYR Tiny Code-Flame, level 1, bond 0; three validated Codex encounter records

## Test-only Dungeon residue

The browser K&M run started one Dungeon checkpoint and saved a 33-byte editor
buffer on the protected cache by mistake. It was then closed through the
internal `dungeon_record_death` state-service action with reason
`ephemeral browser acceptance cleanup; no reward`. The resulting run is dead,
score 0, run coins 0, and has one dead zero-score leaderboard entry. It grants
no Campaign XP/coins, changes no Campaign/Codex/equipment field, and does not
block a fresh run. Revisions 3–5 and their events are intentionally retained as
an auditable custody record rather than removed by direct JSON editing.

## Verification and next gate

- The fresh preflight was GREEN at backend `7371` / frontend `5201`, HEAD
  `238d4eb`, revision 2 before the test mutation, with distinct canonical and
  legacy paths; both PTYs showed `CONNECTED` throughout browser navigation.
- Pure CUA click/scroll/type checks showed the live HUD, Quest Journal, Codex,
  Character, Homestead, Dungeon checkpoint and separate Practice boundary with
  no browser refresh or Playwright.
- Future mutating disposable runs must launch with an explicit isolated local
  state cache (`--use-local-state`/confirmed custody destination) before any
  K&M mutation. A separate workspace by itself is read-only-test evidence only.
- Hosted sync/Supabase, real second-Windows acceptance, Tauri, public and social
  stages remain approval-gated.
