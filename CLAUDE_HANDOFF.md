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
- **Avatar:** pixel paper-doll (`ide/frontend/src/avatarSprite.js`, layers:
  body/hair/outfit/armor/trinket/weapon). Appearance lives in
  `equipment.avatar` (options in `state.AVATAR_OPTIONS`, `POST /api/avatar`,
  synced). Shown in Home (click → Character screen) and the Dungeon "You"
  card. New armor/trinkets need a colour in `ARMOR_COLORS`/`TRINKET_COLORS`.
- **Tate Buti:** the one playable character. `CHARACTER_LOOK` in
  `avatarSprite.js` locks dark skin (`deep`) and the hood on every render, so
  skin and hair are not offered on the Character screen (old saves still
  load; their hair is simply hidden). The Character screen shows a 48x48
  hooded portrait (`portraitSprite.js`) beside the gear sprite. Hand-drawn
  hairstyle art (`portraitHair.js`, cheek/shoulder lengths) is kept but unused.
- **Dungeon room brief:** `DungeonQuestionBrief` (question, answer-layout
  sample, difficulty, enemy Resolve, you). Zen mode spans the editor full width.
- **Dungeon verdicts:** every graded answer pops `DungeonVerdictCard` (keyed
  on `last_result.evidence_id`, so CLI-posted verdicts show too). A miss keeps
  the attempt in dungeon.py; a clear sends you to the route map. PYR reasons
  are cleaned in `ai_tutor._reason` because the verdict gateway rejects
  `/ \ :` and control characters (that 422 used to swallow correct answers).
- **Campaign selector:** Project Map → "Switch ▾" opens `CampaignSelector`;
  `POST /api/campaign/select` → `select_campaign` makes any unfinished,
  unlocked project active and leaves the old one `available` with its board
  intact (`_open_project` is shared with the boss-clear advance).
- **Nav:** Home · Forge · Tutor Notebook · Infinite Dungeon in the centre
  (`SurfaceNavigation`); Settings is the `.hud-settings` gear at the end of
  the top-right HUD.
- **Hunter's Codex (Tutor):** Tutor Notebook opens on `HunterCodex`
  (RpgViews.jsx, `hunterCodex.css`): Contracts (notice board), Bestiary and
  Signs tabs beside Codex and IDE practice. Bugs are beasts and concepts are
  signs (`HUNT_BEASTS`, one per codex page; regions Basics Village /
  Collection Caves / Flow Keep). Status and sign charge come only from saved
  evidence (`huntEvidence`: correct practice, cleared encounters, skill
  evidence); "hunting" = the bounty's concept. A contract's hunt: study
  (opens the Codex page, remembered per device in localStorage), prepare
  (a correct warm-up drill), hunt (a correct bug drill at difficulty 2+).
  No campaign rewards are promised or granted here. Design canvas:
  https://claude.ai/artifact/XY3oVEpdnkS5FvtyHJaQ8n (boards D, E, F).
- **Pop-ups:** render through `ShellPortal` (into `.app-shell`, wrapper is
  `display: contents` and carries the surface's theme class) so panel
  stacking contexts can't hide them under the nav.
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
