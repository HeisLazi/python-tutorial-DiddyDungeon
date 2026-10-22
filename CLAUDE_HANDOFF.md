# Handoff — Python Quest Lab (Diddy Dungeon)

Updated: 2026-10-22 · branch `feature/tauri-arcade` (fast-forwarded into
`feature/cloud-sync-desktop`).

## Where things stand

- **Desktop app:** Tauri window that runs its own backend
  (`ide/quest.py --app`, one port serving `dist/` + API + PTY websockets).
  Launcher entry "Diddy Dungeon" / `quest-lab`. See `docs/DESKTOP_APP.md`.
- **UI:** retro pixel arcade theme (`ide/frontend/src/arcade.css`) is the
  default; other themes stay in Settings. Merchant keeps its scene, sprite
  and layout, with surfaces that follow the theme.
- **Settings:** sectioned (`SettingsScreen` in `RpgViews.jsx`,
  `settings.css`): Appearance, Editor & Terminal, AI Tutor, Account & Sync,
  Project Files, About.
- **PYR on OpenCode:** `ide/server/ai_tutor.py` + `/api/ai/*`. Grades
  battle/boss/dungeon/practice submissions through the existing verdict
  gateway, writes Dungeon questions, picks Tutor lenses, answers Ask PYR.
  See `docs/AI_TUTOR.md`.
- **Campaign progression:** a boss clear completes the project and opens the
  next unfinished one (wrapping back to skipped ones), seeding its 8-bounty
  board from `ide/server/campaign_bounties.json` (built from each branch's
  HANDOFF.md) and its `entry_file`.
- **PYR mode:** OpenCode (default, built-in Forge chat panel) or Classic
  (raw terminal + CLI harnesses). Auto model = `opencode-go/beam-free` first.
- **Gameplay fixes:** The House accepts verdicts when a synced save lost
  `boss_status`; Dungeon elite/boss rooms can be submitted; multiline
  (AI-written) Dungeon questions pass cloud-sync validation.

## Gotchas

- The machine has ~7 GB RAM: build with the capped scripts
  (`NODE_OPTIONS=--max-old-space-size=1536`, `CARGO_BUILD_JOBS=2`), one
  browser at a time.
- OpenCode resolves its project dir from `$PWD`; subprocesses must set it
  (see `ai_tutor._run`). The background service caches per-directory
  config, hence the hashed `pyr-agent-<hash>` scratch directory.
- OpenCode's own free tier (`opencode/…`) rejects custom agents, so those
  models are hidden; `opencode-go/beam-free` (via OpenCode Go) works and is
  Auto's first choice.
- 9 frontend source-regex tests (`npm test`) were already failing before
  this work (they predate it, from commit ccdac84); they are not fixed.

## Next steps

- Tune the generated bounty boards in `campaign_bounties.json` as each
  project is played (entry files are guesses: rps.py, detective.py,
  battle.py, casino.py, crawler.py, gladiator.py, football_manager.py).
- Sign-in: the HUD pill now opens Settings; if the Supabase form itself
  fails, capture the message it shows.
- VS Code companion (sidebar HUD + full game in an editor tab).

## Verify

- Backend: `.venv/bin/python -m pytest -q`
- Frontend: `cd ide/frontend && npm test && npm run build`
- App: `quest-lab`, then Settings → AI Tutor → Test
