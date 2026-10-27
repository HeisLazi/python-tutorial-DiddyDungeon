# Codex: start here (paste the prompt below as your first message)

```
You are continuing a game-dev task in the repo at /home/lazi/projects/python-tutorial-DiddyDungeon, in the git worktree
/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade on branch feature/tauri-arcade. Work ONLY in that worktree.

Project: DiddyDungeon, a Tauri + React + FastAPI Python-learning game. The "Home" screen is a walkable Godot 4.7 scene (ide/home-godot) embedded as a web export.
I (the previous agent) rebuilt Home as seven one-screen rooms (320x180, pixel-art, lit with 2D lights), each with a 9-step upgrade ladder. Five rooms are done.

READ FIRST, in order: docs/HOME_REBUILD_HANDOFF.md (especially section 3 "the recipe", section 4 designs, section 8 "SAVE POINT"), then docs/HOME_AND_ART.md sections 2 and 5-6.
Study ide/home-godot/scripts/rooms.gd: _pantry() and _gallery() are the exact pattern to copy.

YOUR TASKS, in order, committing after each (plain separate git commands; commit messages end with a Co-Authored-By line for you):
1. Write the War Room: add LADDERS["war_room"], WR_* constants, a match case in Rooms.build(), and _war_room(h, lv) in rooms.gd. All its props are already sliced in tools/home_art/props/
   (names listed in HOME_REBUILD_HANDOFF.md section 8). Station id "map" (label "Plan a Dungeon run"). Targets: tools/home_art/concepts/warroom_base.png and warroom_max.png.
   Wire exits: Armory east -> war_room, War Room west -> armory, War Room east -> den.
2. Build Pyr's Den the same way. The owner will drop its prop sheets in tools/home_art/sheets/props/ (den_*.png, see the sheet list in HOME_REBUILD_HANDOFF.md section 4 and the prompts in this file's sibling message).
   Slice each with tools/home_art/from_props.py (probe the reading order first, see section 3 steps 3-4). Station id "perch" (label "Visit Pyr's perch"). Targets: den_base.png / den_max.png. Exit: west -> war_room.
   If the sheets are not there yet, build the room with the code-drawn pieces and placeholders and mark it clearly, then swap in the sliced props later.
3. Screenshot every level of each new room (sh tools/home_art/shots.sh <room> 0 1 ... N), LOOK at them, fix what is wrong (dark, blocked doorway strip y 112-172, props overlapping the wall).
4. Verify the whole chain in a real browser (HANDOFF section 5): gallery - pantry - library - great_hall - armory - war_room - den, and use every station once (hearth, door, study, armory, training, pantry, trophy, map, perch).
5. Update the Status table and "Next steps" in docs/HOME_REBUILD_HANDOFF.md after every room. Do NOT merge to main or push; stop after the browser check and tell the owner what is ready to merge.

HARD RULES: never edit or commit progress.json; never print or store API keys; use system python3 with Pillow (not the repo .venv) for art scripts; Godot is the flatpak shim `godot` with web export templates installed;
the owner prefers real in-engine scenes with lighting, motion and per-step upgrades (not pasted flat images); keep each ladder step a single visible change.
GDScript gotchas: // is a comment (no integer division), declare types explicitly for values from untyped args, test in Compatibility renderer (shots.sh does).
```
