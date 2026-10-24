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
- **Hunter progression (Phase A):** `progress["hunter"]` (local only, not in
  the cloud projection; syncing it needs a Supabase migration). Signs level by
  use: `_hunter_record` runs on every verified correct answer (Tutor practice,
  Dungeon verdict, campaign objective) and on a cleared bounty (campaign use);
  clean = no earlier miss on that question. Stats grow by question type
  (`HUNTER_STAT_BY_TYPE`); Vitality from the first correct answer each day.
  `hunter_projection` gives levels, rank gates (Tutor drill / 10 clean casts /
  campaign use + teach-back), dulling after 7 days and free stat points (one
  per player level, `POST /api/hunter/stat`). Old saves are seeded once from
  defeated bounties and correct practice. Shown on the Character screen
  (`HunterSheet`), in the Hunter's Codex and on the Dungeon verdict card. The
  iron rule holds: none of it skips or shortens a question.
- **Dungeon fights (Phase B):** a combat room keeps `run["fight"]`: fixed
  question counts (encounter 1, elite 3, boss 5; `DUNGEON_FIGHT_QUESTIONS`),
  Resolve (6/8/12), banked free mistakes (`guards`) and the room mechanic
  (elite Enrage: every 2 answers, counterattacks x2 until broken; boss
  Self-destruct: every 3 answers, 15 HP blast). A correct answer moves
  progress by one and chips Resolve (base, halved after a miss, + Strength - 1
  + sign level // 3); at zero it breaks: +1 free mistake, mechanic reset,
  +3 coins, Resolve refills. Insight adds one answer to mechanic countdowns per
  3 points; Vitality adds 5 max HP per point to a new run. Coins arrive on the
  clear. `last_result.fight` carries the exchange for the verdict card. Campaign
  battles: a mob only falls once every objective is verified.
- **Delves and loot (Phase C1):** `dungeon_start_run` takes `region_id`
  (`DUNGEON_REGIONS`: basics / collections / flow, mirroring the Codex
  `HUNT_REGIONS`). Each fight's concept is then drawn from the region's signs,
  weighted (11 - effective level)^2 and seeded by run seed + question number
  (`_dungeon_next_concept`); `HUNTER_SIGN_CONCEPTS` strings each map to exactly
  one sign. Mobs take the Codex beast name (elite: "Elder ..."; boss: the
  region boss). A cleared fight drops parts into `run["pack"]`
  (1/2/3 + 1 for a fight with no misses, boss + region essence); elites drop
  `DUNGEON_TRINKETS` in order (Warden Sigil: fights start with a free mistake;
  Hunting Bell: +1 mechanic countdown; Whetstone Charm: +1 chip), 10 coins
  once all are owned. Reaching a camp (`choose_room` rest) or finishing banks
  the pack into `progress["hunter"]["materials"]`; death (verdict or
  `dungeon_record_death`) moves it to `run["pack_lost"]`. Focus: every 3
  points multiplies the `sign_level // 3` chip term. Pack, bank and region are
  local only (not in the sync projection). UI: `DelvePicker` on run setup,
  PACK tab in the run menu, camp banked note, verdict loot, hunter sheet Stores.
- **Beast oils (Phase C2):** `HUNTER_OIL_TIERS` (ward / slowing / bane) per
  sign, ids `<sign>-<tier>`. `hunter_craft_oil` (`POST /api/hunter/craft`)
  spends banked parts (+ the sign's region essence for slowing/bane) and
  player coins; tiers need sign rank 0 / 1 / 2. `hunter_projection` carries
  `oil_recipes` and owned `oils` (`progress["hunter"]["oils"]`, local only).
  `dungeon_apply_oil` (`POST /api/dungeon/oil`) works once per fight, only on
  a beast whose sign matches (`encounter.sign_id`): ward +1 free mistake,
  slowing +2 on the mechanic countdown (not on plain encounters), bane +3
  chip per correct answer (`fight["bane"]`). UI: Merchant greeting door
  "Hunter's alchemy" (`AlchemyBench`), `DungeonOils` row under the fight strip.
- **Smithing and identify (Phase C2):** the bench has Oils / Smithing /
  Identify tabs. `hunter_upgrade_kit` (`POST /api/hunter/kit`): `HUNTER_KIT`
  coat (+8 max HP per level at run start, Village Essence), blade (+1 chip,
  Cave Essence), satchel (+1 bandage, Keep Essence); level n costs n essences
  + 40n coins, max 3; levels in `progress["hunter"]["kit"]`. Elites and bosses
  drop an `unmarked-vial`. `hunter_identify_start` deals a snippet from
  `_identify_snippet(sign, seed)` (sign weighted to weak signs, tier 6/3/1
  ward/slowing/bane) into `hunter["identify"]`; `hunter_identify_answer`
  checks it server side. Right: vial -> oil, sign XP (`source="identify"`);
  wrong: answer + why revealed, new snippet, vial kept. `/api/campaign` strips
  `answer`/`answer_text`/`why` from `progress.hunter.identify`
  (`_without_identify_answer`). A test execs every generated snippet to check
  its answer.
- **Grid floors and stairs (Phase C3):** new runs and every floor after a
  boss use `_dungeon_generate_grid(seed, floor, modifier, region_id)`: 12
  rooms carved from a 5x4 grid (seeded growth + 2 loops), start camp on the
  west edge with a fight beside it, boss in the farthest room with a camp next
  to it, 1-3 elites, a market, two fates. Same map dict shape as the lane map
  (bidirectional edges); `run["floor_layout"] = "grid"` and
  `run["floor_modifier"]` (deep/quiet) are top-level run keys. Projection fog
  (`_dungeon_grid_visible`): visited rooms + their doors (two out at Insight
  4) + the boss lair; hidden rooms are not sent. `room_choices` are the
  unvisited doors of the current room (always <= 3); `dungeon_travel`
  (`POST /api/dungeon/travel`) walks back to a visited room and is inert (no
  camp, no banking). Selector on a boss node = boss beaten:
  `_dungeon_route_choices` / `_dungeon_live_choices` offer stairs (Descend,
  Deep: +1 difficulty, +1 elite, +1 part per fight; region delves get Path to
  the next region, open runs a Quiet stair with one more camp). Stairs make
  floor+1 and start at its camp (banks). This also frees old lane-map saves
  that were stuck after the first boss. `run["room"]` now counts rooms
  entered. UI: `DungeonGridMap` (frontier rooms travel-then-enter in one
  click, stairs cards).
- **Story contracts (Phase D1):** authored campaigns live in
  `ide/server/campaigns/<branch>.json` (story, acts, boss_lore/brief,
  entry_file, contracts with act, sign, hunter-voice `contract` and 3-5
  `objectives`); a file there replaces that branch in campaign_bounties.json.
  `_encounter_profile(index, project, mob)` uses a contract's own objectives
  (matched by mob name; max_resolve = total impact) and falls back to the
  generic profiles (`legacy_profile` contracts, e.g. Blackjack Act I, keep
  them). `_extend_campaign` appends new contracts to unfinished boards (save
  keeps only the SQL-allowed mob keys), re-locks an unlocked boss, adds
  `catalog: true` projects, sets entry_file; it runs in `apply()` (and after
  any change, for cloud pulls), persists through the internal
  `campaign_extend` action on server startup, and `/api/campaign` serves
  `campaign_view` plus `campaign_board`. Tests: ide/server/conftest.py keeps
  tests off the shipped story files; test_campaign_content.py opts in and
  checks the schema of every file. UI: the Bounty Office shows the story,
  pages by act and lists each contract's sign, beast and BUILD / FIX /
  PREDICT / EXPLAIN objectives; the Forge battle sidebar lists the current
  contract's objectives.
- **All campaigns authored (Phase D2/D3):** every project has a story file:
  RPS 14, Blackjack 19, Detective 14, Creature Battles 15, Casino 14,
  Dungeon Crawler 15, Gladiator 15, Football Manager 15, plus two catalog
  projects added to existing saves: 08-game-agent "The Clockwork Arena"
  (connect_four.py, 16) and 09-ai-agent "The Familiar" (agent.py, 16; its
  optional LLM brain uses the learner's own key from their environment, the
  game never asks for or stores one). Advanced concepts map to the closest of
  the nine signs; new Codex pages are a follow-up.
- **Submit race fix:** `submitDungeon` waits for any in-flight editor
  checkpoint and saves unsaved edits before capturing PYR context (an autosave
  in between changed the revision and the answer was rejected as stale).
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
