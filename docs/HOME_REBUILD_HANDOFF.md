# Home rebuild: handoff status (read this first)

Written 2026-10-27 for whoever continues (Codex, another Claude, or the owner). Companion to `docs/HOME_AND_ART.md`
(architecture, art history, bridge protocol). This file is the **current state, the recipe, and the exact next steps**.
Update the "Status" and "Next steps" sections after every major step and commit.

## 1. Where things live

- Branch: `feature/tauri-arcade`, worktree `/home/lazi/projects/python-tutorial-DiddyDungeon/.claude/worktrees/tauri-arcade`.
  **Nothing from the room rebuild is merged to main.** Main still has the old single-hall Home (9 stations). Do NOT merge until every
  station has a room (see "Station checklist"). The user's real save is `progress.json` in the main checkout: never edit it; verify its md5
  (`d1522dfd4ad8e1bd70c7c92c37062d00` at last check) is unchanged around any fast-forward.
- Godot project: `ide/home-godot/` (Godot 4.7.2, Compatibility renderer, 320x180 view). Code: `scripts/home.gd` (engine, hunter, bridge, HUD),
  `scripts/rooms.gd` (every room + ladders), `shaders/sway.gdshader`, `shaders/crt.gdshader`.
- Art pipeline: `tools/home_art/` (`make_tiles.py` builds `art/tiles.png`+`tiles_data.gd`; `hall_pieces.py` code-drawn pieces; `from_props.py`
  slices AI prop sheets; `from_sheets.py` is the hunter; `shots.sh` screenshots). Source images are committed: `tools/home_art/concepts/*.png`
  (the user's design targets), `tools/home_art/sheets/props/*.png` (generated prop sheets), sliced results in `tools/home_art/props/*.png`.
- Build the web export: `sh tools/build_home.sh` (writes `ide/frontend/public/home/`, git-ignored). Then `npm --prefix ide/frontend run build`.

## 2. Status

| Room | id | Ladder | Exits | Stations | State |
|---|---|---|---|---|---|
| Great Hall | `great_hall` | 9 steps | W: library, E: armory | hearth, door | DONE (image props) |
| Library | `library` | 9 steps | E: great_hall | study | DONE |
| Hall of Arms | `armory` | 9 steps | W: great_hall | armory, training | DONE (needs east exit to war_room later) |
| Pantry | `pantry` | 8 steps, 238 Embers | E: library (W: gallery, add when the gallery exists) | pantry | DONE (all props sliced; `PN_*` constants; Library has a west exit to it) |
| Trophy Gallery | `gallery` | designed below | E: pantry | trophy | concepts saved only |
| War Room | `war_room` | designed below | W: armory, E: den | map | concepts saved only |
| Pyr's Den | `den` | designed below | W: war_room | perch | concepts saved only |

Topology (a row; each room has only left/right doorways, `_shell(h, marble_from, marble_to, left, right, floor_kind)`):
`gallery - pantry - library - great_hall - armory - war_room - den`. The Great Hall also has the bottom door to the Forge (station `door`).
To wire a room: add `{"to": id, "spawn": Vector2(x, 142)}` to the neighbour's exit dict (spawn = just inside the opposite edge: 30 for a room
entered from its west door, 290 for east). Today the Hall of Arms has no east exit and the Library has no west exit yet.

### Station checklist (all must work before merging to main)
hearth (rest), door (Forge), study (Tutor), armory (Armory panel), training (Tutor sparring), pantry (eat a meal), trophy (Settings > Player Stats),
map (Dungeon), perch (feed Pyr). Station ids and the bridge messages are unchanged from `HOME_AND_ART.md` section 2.

## 3. The recipe for a room (what was done for Library and Hall of Arms; ~1 hour each)

1. Concepts: `tools/home_art/concepts/<room>_base.png` and `_max.png` (the user generates them in Google; flat front wall, floor from above).
2. Prop sheets: 3 per room, generated with Higgsfield `z_image` (0.25 credit each, 16:9). Prompt style that works: "Pixel art prop sprite sheet for
   a gothic castle <room>, front/top-down three-quarter view like Pokemon FireRed and Castlevania Symphony of the Night. Exactly N separate objects,
   evenly spaced on a flat plain grey background, nothing else: first ..., second ... 16-bit, chunky 1px dark outlines, crisp pixels, no text, no floor,
   no ground line, no shadows." Asking for fewer, named objects ("exactly six", "one single") avoids fused props. **Submit ONE job at a time**
   (parallel jobs hit a 429 rate limit). `jobs_wait` then `curl -sL -o tools/home_art/sheets/props/<name>.png <result_url>`.
   Credits: ~4 left after the Pantry (check `balance`); each room costs ~0.75.
3. Probe the reading order: `python3 tools/home_art/from_props.py <sheet> a --out ide/home-godot/props_test` prints the boxes (then `rm -rf` that dir).
4. Slice: `python3 tools/home_art/from_props.py <sheet> name@H name@H - name@H!rows,cols ... --out tools/home_art/props`
   (reading order, `-` skips, `@H` height in px, `!0-50` makes a 2-frame flicker pair `name_0/name_1`, `!68-92,28-70` limits the region and also makes
   `name_out`, `>bg` makes dim/blue variants named `name[:-1]+b/g`: do not reuse names already taken). Fused or odd sheets: regenerate rather than patch.
5. `python3 tools/home_art/make_tiles.py` (loads every PNG in `tools/home_art/props/` over code-drawn pieces; `*_l` gets a mirrored `*_r`).
6. Write the room in `scripts/rooms.gd`: add a `LADDERS["<id>"]` list (name, cost, note), step constants (`PN_*`), a `match` case in `build()`, and
   `_<room>(h, lv)` using `if lv >= STEP` thresholds, `_prop(...)` (shadow + blocker), `h.anim(...)`, `h.add_light`, `h.add_embers`, `h.add_shaft`,
   `h.add_patch`, `h.sway`. Keep the doorway strip y 112-172 free at EVERY level. Add the room's step names to `ladder_sheet` names if you use it.
7. Test: `sh tools/home_art/shots.sh <room> 0 1 2 ... N` writes `ide/home-godot/shot_<room>_l<N>.png` (git-ignored). View them. Then web build + Chrome
   (see 5). Fix, commit.
8. Update this file (Status table) and `docs/HOME_AND_ART.md` if the architecture changed. Commit.

## 4. Designs for the remaining rooms (ladders proposed by the previous agent; costs are Embers, tune later)

Palette and mood come from the concept images; each ladder step adds/changes ONE visible thing; light and ambient ramp with the level.

**Pantry (`pantry`, station `pantry`, concepts `pantry_base/max.png`)** 8 steps (238): 1 Sweep and clean (16: cobwebs, scraps), 2 Light the hearth (20: cold ash
-> burning fire, `hearthp_out` -> `hearthp_*`), 3 Hang the herbs (22: `hang_rack`, `herbs`, red curtains), 4 Stock the shelves (26: empty shelf -> `shelf_stocked`),
5 Fill the barrels and crates (30: `barrel_food`, `crate_veg`, `sacks`), 6 Fix the range (34: cold cauldron `cauldron_p_out` -> `range_pots` with steam particles),
7 Set the table (40: plain table -> table with roast ham and bread), 8 Stoke the feast (50: roaring fire, steam, torches). Layout: big hearth centre-left of the back wall,
arched door right of it, shelves on the right, range/pit on the left, table front right.
**Pantry assets** (all sliced into `tools/home_art/props/`): `hearthp_{0,1,out}`, `range_pots`, `cauldron_p_{0,1,out}`, `shelf_stocked`, `shelf_empty`, `table_roast`, `door_pantry`, `torch_stand_{0,1}`, `window_pantry`, `barrel_food`, `herbs`, `crate_veg`, `hang_rack`, `sacks` (sheets: `pantry_fire`, `pantry_store`, `pantry_table`).

**Trophy Gallery (`gallery`, station `trophy`)** 9 steps (288): 1 Dust and clear (16), 2 Mend the display case (20), 3 Hang the banners (22: torn -> crest),
4 First relics (26: chalice on a plinth), 5 Lay the carpet and ropes (30: red carpet, stanchions), 6 Spotlights (34), 7 Mount the beasts (40: ram, wolf, bull, dragon heads),
8 Glowing relics (46: glowing heart case, claw, greatsword, horn case), 9 Portrait of the hunter (54: gold-framed portrait, stained-glass window and its coloured floor patch).
Prop sheets to generate: plinths/glass cases/relics; mounted heads/portrait frame/banners; carpet/stanchions/crates/stained-glass window. Station: the central plinth.

**War Room (`war_room`, station `map`)** 9 steps (296): 1 Clear (16), 2 Mend the table (20), 3 Light the candles (24), 4 Pin the maps (28), 5 Hang the banners (30),
6 Lay the rug (34), 7 The great map table (42: glowing illuminated map with markers and wax seals), 8 Chandelier (48), 9 Crystal ball and chests (54).
Layout: table centre, bookshelf and globe left, shelves with scrolls and glowing crystal ball right, arched window, wall maps.

**Pyr's Den (`den`, station `perch`)** 8 steps (266): 1 Clear the nook (14), 2 A proper perch (20), 3 Build a nest (24), 4 Light the lamps (28), 5 Open the wall (36: cave opening
onto a sunrise sky and mountains), 6 Vines and glowing flowers (40), 7 Carve the eagle perch (48: ornate blue-gold perch), 8 The phoenix aerie (56: glowing golden nest, drifting embers).
Pyr itself becomes a blue-and-gold fire eagle later (reference `tools/home_art/sheets/pyr_phoenix_reference.png`; 4 stages in `HOME_AND_ART.md` 8c); do the rooms first.

## 5. Testing in a real browser (do this before declaring a room done)

`python3 -m http.server 8765 --directory <worktree>/ide/frontend/public/home` (run in the background), open `http://localhost:8765/index.html` in Chrome, set state with
`window.diddyHomeReceive(JSON.stringify({levels:{great_hall:9, library:9, armory:9}}))`, walk by dispatching `keydown`/`keyup` KeyboardEvents (with `code: 'KeyA'` etc.) on the
canvas and holding for ~1-3 s (a quick tap moves only ~5 px). Stop the server with `pkill -f "[h]ttp.server 8765"` (the bracket stops the pattern killing its own shell).
Watch for: furniture blocking a doorway at some level; props overlapping the wall; the station prompt appearing. The app also still sends the old `tiers` (0..3 per station), which
`Rooms.tier_to_level` spreads over each ladder.

## 6. Gotchas learned the hard way

- The worktree guard refuses complex shell: no heredocs mixed with git, no `$(...)`, no loops running `git` or `godot`, no `sh -c` with computed values; run `git`, `godot`, builds as separate plain commands.
  Edit files with the Write/Edit tools or small `python3 -` scripts. Writing a file you edited by script since your last read fails: write a new filename and `mv`.
- GDScript: `//` starts a comment (not integer division); untyped `h` params return Variant so use explicit types (`var x: Sprite2D = h.bg(...)`).
- Godot web needs the Compatibility renderer (already set); verify in Chrome, not only desktop shots.
- Image-model sheets: they add soft blue shadows (stripped by the slicer), sometimes a ground line (stripped if it spans > 50% of the width; otherwise paint it out), and fuse objects; keep prompts to a few named objects.
- `pkill -f` with a pattern present in its own command kills its own shell: use the `[x]` bracket trick.
- Higgsfield is rate-limited: one job at a time.

## 7. Next steps (in order)

1. (done) Pantry. NOT yet checked in the real browser: do the Chrome walk Library -> Pantry -> Library once.
2. Trophy Gallery (3 sheets), then War Room (+ Hall of Arms east exit), then Pyr's Den. Commit after each.
3. Station and bridge check across all rooms in the real app (`HomeRoom` in `ide/frontend/src/RpgViews.jsx` already forwards `use` events by station id). Update `homeRoomState` to send `levels` if the app should drive rooms directly.
4. Merge: `ExitWorktree keep`, then from the main checkout `git merge --ff-only feature/tauri-arcade` (md5 of `progress.json` before and after), `sh tools/build_home.sh`, `npm --prefix ide/frontend run build`, run the backend tests (`ide/.venv` pytest) and `node --test ide/frontend/src/cloud/` (87 pass / 10 pre-existing failures is the baseline).
5. Pyr's eagle redesign (4 stages), unlockable hunter skins, the three weapon types and the combat stage (`HOME_AND_ART.md` section 8).
