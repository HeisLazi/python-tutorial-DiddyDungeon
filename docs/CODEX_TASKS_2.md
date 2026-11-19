# Codex brief 2: wire room upgrades into the app, then Pyr's eagle

Paste the code block as your first message. (Brief 1, `docs/CODEX_START_HERE.md`, built the rooms; it is finished and merged.)

```
You are continuing work on DiddyDungeon (Tauri + React + FastAPI Python-learning game) in the git repo /home/lazi/projects/python-tutorial-DiddyDungeon,
using the worktree /home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade on branch feature/tauri-arcade. Work ONLY in that worktree.
Do not push, do not merge, do not touch main checkout files. Commit with plain separate git commands and NO Co-Authored-By line (the owner asked for commits as themself).

CONTEXT: Home is a walkable Godot scene (ide/home-godot, exported to ide/frontend/public/home/) made of seven rooms, each with a 9-10 step upgrade ladder defined in
ide/home-godot/scripts/rooms.gd (`LADDERS`: name, cost in Embers, note per step; helpers Rooms.max_level / upgrade_name / tier_to_level).
The Godot scene already accepts `levels: {room_id: n}` through window.diddyHomeReceive (see home.gd room_level()) and rebuilds the room with a build flash and a "BUILT: <name>" toast when a level rises.
Room ids: great_hall, library, armory, pantry, gallery, war_room, den. READ docs/HOME_REBUILD_HANDOFF.md and docs/HOME_AND_ART.md (sections 2 and 8) first.
PROBLEM: the React app (ide/frontend/src/RpgViews.jsx: HomeRoom, homeRoomState, useStation; backend ide/server/state.py + app_v2.py) still only sends the OLD per-station tiers
(hearth, armory, map: 0..3), so the new rooms can never be upgraded in the real app. Embers are the existing upgrade currency (README "Economy": ~2,100 Embers to max everything; do not change totals without noting it).

TASK A: make every room's ladder purchasable in the app.
1. Backend: store per-room upgrade level in the save (e.g. progress["home"]["rooms"][room_id] = level, default 0) with a bounded, validated shape; add a purchase action (POST in app_v2.py, logic in state.py)
   that spends the next step's Embers cost (costs come from the ladders: mirror them in Python in ONE place, e.g. ide/server/home_rooms.py, and add a test that the Python table matches the LADDERS in rooms.gd by parsing the .gd file),
   rejects when Embers are short or the room is maxed, and returns the new progress. Migrate the old hearth/armory/map tiers into the matching rooms' levels once (great_hall, armory, war_room) without losing spent Embers or double-charging.
   Include the new field in any cloud-sync projection or allow-list so the existing cloud tests keep passing (the cloud campaign projection has size limits: keep the new data small).
2. Frontend: send `levels` (all seven rooms) to the Godot scene in homeRoomState; when a station is used (hearth, study, armory, pantry, trophy, map, perch), show a small panel (reuse the Armory panel / room-panel styling in v2.css `.home-room-panel`)
   listing that room's ladder: current step, next step name + note + cost, a Buy button (disabled when short of Embers), and the steps already built. After a purchase, resend state so the room rebuilds with the flash.
   Existing station effects (rest at the hearth, eat a meal, open Tutor, etc.) must keep working: offer the upgrade panel alongside them (e.g. a secondary "Upgrade room" button), not instead of them.
3. Tests: backend pytest (ide/server; conftest points the save at a temp copy; NEVER let a test write the real progress.json) and keep `node --test ide/frontend/src/cloud/` at its baseline (87 pass / 10 pre-existing failures).
   Baseline backend: 229 pass; one cloud-sync test (test_launcher_contract local_sync_simulator) fails ONLY because the real save is now large; do not "fix" it by editing the save.
4. Verify in a real browser with the frontend build: npm --prefix ide/frontend run build, sh tools/build_home.sh, then run the app per README / the `run` approach (Vite dev + FastAPI), buy a step in two different rooms and see the room change.
   Test on a COPY of the save, never the real progress.json (md5 d1522dfd4ad8e1bd70c7c92c37062d00 must stay unchanged in the main checkout).
Gotchas: ide/frontend/src/AppV2.jsx and parts of ide/server/app_v2.py use CRLF line endings: edit them with byte-safe scripts (read bytes, replace, write bytes) or you will corrupt the diff.
Commit after each sub-step and update docs/HOME_REBUILD_HANDOFF.md.

TASK B (after A is committed): Pyr becomes a blue-and-gold fire eagle in four stages.
Design (docs/HOME_AND_ART.md 8c): colour identity deep blue plumage, gold/ember edges, flame crest and long ember tail; reference image tools/home_art/sheets/pyr_phoenix_reference.png.
Stages: 1 Ember chick (current flame + beak/eyes), 2 Fledgling, 3 Firehawk, 4 Phoenix eagle (long flame tail, ember trail). Stage comes from Pyr's existing level/progress in the save (find how Pyr level is stored; do not invent a second counter);
the Den room's level may also gate stage 4.
Art pipeline (same as the hunter and props): an image model draws a clean sheet per stage (flat grey background, 4-6 frames: idle, fly/follow, perch, feed), a script cuts it. You cannot generate images; if no sheets exist yet in
tools/home_art/sheets/pyr/, write the exact prompts into docs/HOME_REBUILD_HANDOFF.md (one per stage, "Pixel art sprite sheet, N-frame flying/idle cycle of a small blue and gold fire eagle ... flat plain grey background, crisp pixels ...") and stop Task B
there, telling the owner which images to generate; implement the loader/animation in home.gd so dropping the sliced sheets in works (pyr currently uses tiles pieces pyr_0/pyr_1 in _follow_pyr; add a per-stage sprite sheet and a `pyr_stage` state key).
Slicing: extend tools/home_art/from_sheets.py or from_props.py rather than writing a new pipeline.

FINAL: stop after verification, summarize what is ready, and list anything blocked on the owner. Do NOT merge or push.
```
