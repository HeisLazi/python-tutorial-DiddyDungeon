# Quest Lab game-state snapshot — 2026-09-16 10:14 +02

This checkpoint records the isolated Dungeon/Practice acceptance slice. It is
not a player-save migration and does not change the protected canonical cache.

## Repository and custody

- Branch: `feature/cloud-sync-desktop`
- Code HEAD and `origin/feature/cloud-sync-desktop`:
  `0397e2d71e202b62ffbfb59ae733848f84997241`
- Protected canonical `progress.json` SHA-256 remained
  `5618f9dd9ae2fc0724056ea08448e1736479772b59ada949bec08b5340fbd6f0`.
- Root `tutor.py` and canonical `progress.json` were never staged, overwritten
  or reset. The legacy workspace save was not touched.
- Disposable state root: `/tmp/questlab-dungeon-state-YbYUIA`; disposable
  workspace: `/tmp/questlab-dungeon-workspace-SE5lI5`.

## Pure CUA K&M acceptance

The guarded launcher first ran the stable-PTY stack on backend `7373` and
frontend `5203` with `--use-local-state --confirm-local-state` and the
`-RequireIsolatedState` preflight. No Playwright, browser refresh or direct
JSON edit was used during the live progression checks.

1. The initial isolated Forge projection showed the canonical campaign
   baseline (Level 2, 50/100 XP, 55 coins, The Hitman 8/8, three cleared mobs)
   and connected shell/AI PTYs.
2. A shell command typed through the visible terminal invoked the internal
   state service `dungeon_record_verdict` for run
   `dungeon-08be279fdb3646eaba54f1c37e79c9f7`, question `q1`, with bounded
   evidence `km-dungeon-correct`. Revision `7 → 8` advanced the run to Floor 1
   / Room 2, awarded the service-owned `+10` score and `+5` run coins, and
   reset the editor buffer to blank. Forge displayed the queued
   `DUNGEON ROOM CLEARED` reward card and the new-room question without a
   refresh.
3. Practice navigation showed its explicit no-cost boundary. The no-provider
   button guard produced “Launch Codex, Claude, or AGY first” without creating
   a session. A separate shell-typed gateway check then created a valid
   `practice_session_started` record and `practice_record_attempt` with
   outcome `reviewed`; revisions `8 → 9 → 10` added one history row and
   returned `reward_xp: 0`, `reward_coins: 0`. Campaign level/XP/coins,
   Dungeon score/run currency and `tutor.py` remained unchanged. The UI showed
   `PRACTICE DRILL READY` and `PRACTICE RESULT RECORDED` notifications.

## Restart/savestate proof

The first launcher correctly refused to re-run against a diverged local cache
(`status: conflict`, canonical revision 5 versus disposable revision 10).
For the restart check only, the backend was relaunched directly with the
already-approved disposable `QUESTLAB_STATE_PATH`; the Vite frontend was
restarted on the same ports. A fresh in-app browser tab then reopened the
active run at Floor 1 / Room 2 with score `10`, run coins `5`, the same run ID,
and a blank `dungeon.py` buffer. The backend log accepted both
`/ws/terminal/shell` and `/ws/terminal/ai` connections after the restart.

The resulting disposable cache was stopped and removed after inspection. The
canonical save, legacy evidence, long-lived runtimes and their PTYs were left
untouched.

