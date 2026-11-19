# Python Quest Lab game-state snapshot

Captured: 2026-09-16 03:15 +02:00  
Branch: `feature/cloud-sync-desktop`  
HEAD/upstream: `82eae1783d4e0dba67d06547f58d4a8b7413b534` (matched)

This is a read-only snapshot of the currently running local canonical state.
It is evidence for the next roadmap planning pass, not a migration or save
edit.

## Canonical authority

- State revision: **2**
- Canonical/cache path: `/home/lazi/projects/python-tutorial-DiddyDungeon/progress.json`
- Legacy evidence path: `/home/lazi/projects/questlab-blackjack/progress.json`
- Canonical path is authoritative; legacy path is present but explicitly
  non-authoritative and approval-gated.
- No Supabase or hosted player-state transport was contacted.

## Player projection

| Field | Current value |
| --- | --- |
| Player | Lazi |
| Level / rank | 2 / F |
| Current XP | 50 / 100 |
| Lifetime XP | 150 |
| Coins | 55 |
| HP | 100 / 100 |
| Potions | 2 |
| Streak | 1 current / 1 longest |
| Sessions | 1 |
| Mob defeats | 3 |
| Achievements | First Blood |

## Active Blackjack campaign

- Project progress: **38%**.
- Cleared: The Empty Table, The Dealer's Hand, The Count Keeper.
- Active encounter: **The Hitman** (Mob 3), available, Resolve **8 / 8**.
- Valid public objectives: `choice_flow` (code checkpoint, Impact 4) and
  `stop_condition` (bug diagnosis, Impact 4).
- Locked future encounters remain hidden; no future answers/questions were
  exposed.
- Daily goals are complete; weekly progress is 3 sessions `1/3`, 2 mobs `2/2`,
  first interview `0/1`.

## Character, companion and Codex

- Equipment: Training Blade, Apprentice Coat, no trinket, Apprentice Coder
  title.
- Companion: PYR, Tiny Code-Flame, level 1, bond 0; next form remains gated on
  the first project boss.
- Codex contains three validated encounter records for the cleared mobs. Each
  record carries the approved legacy evidence ID and a bounded note; attempts,
  exact question types, mastery, shields and interview history were not
  inferred.
- Skills remain at their current learning/locked statuses with no mastery
  shields.

## State-event evidence

Revision 1 records the approved legacy reconciliation of Level 2, 50 current
XP, 150 lifetime XP, 55 coins, three cleared mobs, 38% progress, The Hitman
unlock, First Blood and the three evidence-backed Codex entries. Revision 2
records the later validated daily/session reconciliation. `state_events` has
two entries; reward history was not invented.

## Runtime and custody notes

- Long-lived local listeners remained present on 7332/7333 and 5173/5174 at
  capture; they were not restarted.
- The 7333 health response reports the local shell and configured tools but is
  an older runtime without current repo-identity fields. The read-only
  `tools/questlab-km-preflight.ps1` gate therefore rejects it as acceptance
  evidence until a branch-matched runtime is launched separately.
- Windows Git status remains limited to the user-owned tracked `progress.json`
  and untracked Campaign `tutor.py`; neither was staged, overwritten or
  reconciled during this snapshot.

## Prior live projection evidence

The isolated branch-matched K&M run recorded in the implementation report and
issue log observed `SYNCING` settling without refresh, revision-aware Resolve
change, state-service reward/achievement/next-encounter notifications,
Journal/Codex/Character/Homestead agreement and connected shell/AI PTYs. The
run used no Playwright and its disposable runtime was removed afterward.
