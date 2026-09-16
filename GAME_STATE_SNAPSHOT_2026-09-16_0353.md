# Python Quest Lab game-state snapshot

Captured: 2026-09-16 03:53 +02:00  
Branch: `feature/cloud-sync-desktop`  
HEAD/upstream: `6e366015275ca231b7e37c485754a09e856154a8` (matched)

This is a read-only capture of the running local campaign projection. It is
evidence for the roadmap audit, not a save migration or state edit.

## Canonical authority

- State revision: **2**.
- Canonical/cache path: `/home/lazi/projects/python-tutorial-DiddyDungeon/progress.json`.
- Legacy evidence path: `/home/lazi/projects/questlab-blackjack/progress.json`.
- The canonical path is the only active local authority; the legacy path is
  evidence-only and remains approval-gated.
- No Supabase or hosted player-state transport was contacted.

## Player and Blackjack projection

| Field | Current value |
| --- | --- |
| Player / title | Lazi / Apprentice Coder |
| Level / rank | 2 / F |
| Current XP | 50 / 100 |
| Lifetime XP | 150 |
| Coins | 55 |
| HP / max HP | 100 / 100 |
| Potions | 2 |
| Streak | 1 current / 1 longest |
| Sessions | 1 |
| Project progress | 38% |
| Achievements | First Blood |

- Cleared: The Empty Table, The Dealer's Hand, The Count Keeper.
- Active encounter: The Hitman (Mob 3), Resolve **8 / 8**.
- Locked future encounters and their questions remain undisclosed.

## Character, companion and Codex

- Equipment: Training Blade, Apprentice Coat, no trinket, Apprentice Coder
  title.
- Companion: PYR, Tiny Code-Flame, level 1, bond 0; Ember Sprite remains gated
  on the first project boss.
- Codex contains three evidence-backed encounter records for the cleared
  Blackjack mobs. Unsupported exact attempts, question types, mastery,
  shields, interview completion and reward history were not inferred.
- Skills remain at their recorded learning/locked statuses; no mastery shield
  is claimed.

## Event evidence

The canonical `state_events` list contains two approved
`reconcile_legacy_progress` events at revisions 1 and 2. They record the
validated Level 2/XP/coin restoration, three mob clears, 38% project progress,
The Hitman unlock, First Blood, three Codex records and the daily/weekly
reconciliation. `reward_history_inferred` is false for both events.

## Runtime and custody notes

- Long-lived listeners on 7332/7333 and 5173/5174 remained present and were
  not restarted for this capture.
- The 7333/5174 runtime is older and lacks the branch/HEAD identity fields;
  `tools/questlab-km-preflight.ps1` correctly rejects it as current-branch
  acceptance evidence. Current-tip K&M evidence was captured separately on a
  disposable matched runtime and removed afterward.
- Windows Git status still contains only the user's dirty tracked
  `progress.json` and untracked Campaign `tutor.py`; neither was staged or
  overwritten.
