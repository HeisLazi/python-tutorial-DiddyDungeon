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
| Library | `library` | 9 steps | W: pantry, E: great_hall | study | DONE |
| Hall of Arms | `armory` | 9 steps | W: great_hall, E: war_room | armory, training | DONE (east exit connected; doorway braziers moved clear) |
| Pantry | `pantry` | 8 steps, 238 Embers | W: gallery, E: library | pantry | DONE (browser walk and station event checked) |
| Trophy Gallery | `gallery` | 9 steps, 288 Embers | E: pantry | trophy | DONE (browser walk and station event checked) |
| War Room | `war_room` | 9 steps, 296 Embers | W: armory, E: den | map | DONE (levels 0–9 reviewed; browser walk and station event checked) |
| Pyr's Den | `den` | 9 steps, 266 Embers | W: war_room | perch | DONE (levels 0–9 reviewed; browser walk and station event checked) |

Topology (a row; each room has only left/right doorways, `_shell(h, marble_from, marble_to, left, right, floor_kind)`):
`gallery - pantry - library - great_hall - armory - war_room - den`. The Great Hall also has the bottom door to the Forge (station `door`).
To wire a room: add `{"to": id, "spawn": Vector2(x, 142)}` to the neighbour's exit dict (spawn = just inside the opposite edge: 30 for a room
entered from its west door, 290 for east). The War Room east exit and Den west exit complete the seven-room chain.

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

**Pyr's Den (`den`, station `perch`)** 9 steps (266): 1 Clear the nook (14), 2 A proper perch (20), 3 Build a nest (24), 4 Light the lamps (28), 5 Open the wall (36: cave opening
onto a sunrise sky and mountains), 6 Vines and glowing flowers (40), 7 Carve the eagle perch (48: ornate blue-gold perch), 8 The golden nest (28), 9 The phoenix aerie (28: blue lantern and drifting embers). The original final 56-Ember step is split into two visible upgrades.
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

1. War Room and its Armory exit are built; levels 0–9 have been reviewed in Compatibility screenshots.
2. Pyr's Den is built and levels 0–9 have been reviewed in Compatibility screenshots. The sliced cave arch opening was made transparent so the sunrise behind it is visible; re-slicing that prop requires restoring the opening mask.
3. Done: built the web export and walked the complete room chain in Chromium, using every station and checking its bridge event. See the browser evidence below.
4. The room commits and browser evidence are ready for the owner to review for merging. Do not merge or push as part of this task.
5. Later: Pyr's eagle redesign (4 stages), unlockable hunter skins, the three weapon types and the combat stage (`HOME_AND_ART.md` section 8).


## 7a. Browser evidence (2026-10-27)

- Rebuilt the Godot Web export and the React production bundle. In standalone Chromium with the Compatibility renderer, set all rooms to their maximum levels via `diddyHomeReceive`, walked Gallery → Pantry → Library → Great Hall → Armory → War Room → Den, and walked back Den → War Room → Armory.
- Pressing E emitted a `diddy-home` use event for every station: `hearth`, `door`, `study`, `armory`, `training`, `pantry`, `trophy`, `map`, and `perch`. Browser screenshots are retained in the ignored `ide/home-godot/shot_browser-*.png` files. The only browser console error was a missing favicon in the standalone server.
- This verified the standalone Web scene and bridge messages. It did not execute React-side navigation or backend actions. `homeRoomState` still sends legacy tiers for hearth and armory; per-room ladder purchases and persisted room levels are not wired to the app.

## 8. SAVE POINT (2026-10-27, written when the previous agent ran out of budget): exact state and how to reproduce

This is the earlier historical snapshot. The current status and next steps above supersede its War Room and exit notes.

Everything is committed on `feature/tauri-arcade` except the git-ignored `ide/home-godot/shot_*.png` screenshots. Main is untouched (still the old one-hall Home).

### Done and committed
Engine (`home.gd`, `rooms.gd`), doorways, 5 finished rooms (Great Hall 9 steps, Library 9, Hall of Arms 9, Pantry 8, Trophy Gallery 9), all prop sheets and sliced props for them,
the War Room's props, concept images for all seven rooms, the hunter (Alucard sprite, `from_sheets.py`), docs.
Exits wired: Library W->pantry, Library E->great_hall, Pantry W->gallery, Pantry E->library, Gallery E->pantry, Great Hall W->library, Great Hall E->armory, Armory W->great_hall.
**Not wired**: Armory E -> war_room (give `_armory`'s `_shell` call a right exit `{"to": "war_room", "spawn": Vector2(30, 142)}`), War Room W -> armory, War Room E -> den, Den W -> war_room.

### War Room: props already sliced into `tools/home_art/props/` (use these names in `rooms.gd`)
`table_map_small` (bare table, parchment, candle: base), `table_map_big` (glowing map table with figures: level 7), `stool`, `chair_war`, `crystal_ball`, `chest`, `map_world`, `map_chart`,
`banner_sun` (wide navy banner), `chandelier_war_{0,1}` (`h.anim("chandelier_war", feet)`), `window_war` (moon window), `shelf_war`.
Reusable from earlier rooms: `bookshelf_sparse`, `globe`, `barrel`, `crate`, `rug_crimson`, `scrolls`, `torch_stand_{0,1}`, `cobweb_l/r`, `stain`, `rubble_0/1`, `banner_blue`.
Write `_war_room(h, lv)` like `_pantry`/`_gallery` in `rooms.gd`: add `LADDERS["war_room"]` (the 9 steps in section 4), `WR_*` constants, a `match` case in `build()`,
`_shell(h, -1, -1, <left exit armory>, <right exit den>, "stone")`, and the station `h.station("map", "Plan a Dungeon run", Rect2(...), Vector2(160, 14))` in front of the table.
Targets: `tools/home_art/concepts/warroom_base.png` and `warroom_max.png`.

### Pyr's Den: nothing built; concepts `den_base.png`, `den_max.png` exist
Generate 3 prop sheets (a bare perch + twigs + oil lamp + stone block; an ornate blue-gold eagle perch, a glowing golden feather nest, lanterns, hanging vines with glowing flowers, a cave-opening arch with a sunrise sky;
a rock ledge, cave wall pieces, a torch), slice, write `_den` (ladder in section 4), station `perch` ("Visit Pyr's perch") in front of the perch.

### Reproducing the toolchain on a fresh machine
- Godot 4.7.2 flatpak with a `godot` shim and the Web export templates (`HOME_AND_ART.md` section 9).
- System `python3` with Pillow (not the repo `.venv`).
- Images: the owner has Google AI Pro image models (preferred); the previous agent used Higgsfield `z_image` (free plan, about 3.5 credits left, one job at a time). Otherwise ask the owner to generate each
  sheet using the prompt pattern in section 3 step 2 and save it in `tools/home_art/sheets/props/`.
- No secrets are needed. Never touch `progress.json`; never push to main.

### Remaining checklist to a mergeable state
1. War Room code and exits. 2. Pyr's Den (sheets, code, exits). 3. Walk the whole chain `gallery - pantry - library - great_hall - armory - war_room - den` in Chrome (section 5) and use each station once.
4. Only if the app should drive room levels, update `homeRoomState`/`HomeRoom` in `ide/frontend/src/RpgViews.jsx` (the old 0..3 `tiers` still work). 5. Merge procedure: section 7 step 4.
6. Then: Pyr eagle redesign, unlockable skins, weapons and combat stage (`HOME_AND_ART.md` section 8).


### Pyr's Den props (sheets saved by the owner, ALREADY SLICED into `tools/home_art/props/`; tileset rebuilt)
Sheets: `tools/home_art/sheets/props/den_1.png`, `den_2.png`, `den_3.png`. Piece names for `rooms.gd` (use `h.bg/obj/anim/_prop`):
- Perch and nest (den_1): `perch_bar` (bare wall bar, base), `twigs` (floor litter), `lamp_stone` (oil lamp on a block), `perch_eagle` (ornate blue-gold carved perch: the `perch` station, late levels),
  `nest_gold_{0,1}` (glowing golden nest, 2-frame: `h.anim("nest_gold", feet)`; the max-level centrepiece with embers), `nest_straw` (plain nest, early level).
- Light and nature (den_2): `lantern_warm`, `lantern_blue` (hanging; add a chain with `h.add_chain` and a light), `vine` (hanging, give it `h.sway`), `flowers_den` (glowing flowers on rock), `torch_den_{0,1}` (wall torch, animate), `window_den` (arched moon window).
- Open aerie (den_3): `cave_arch` (77x74 rock arch with a dark hole), `sky_sunrise` (172x92 sunrise and mountains: place it BEHIND the arch on the back wall, i.e. add it with `h.bg` before the arch; the wall tiles must not cover it, so
  either draw the arch area over the wall with the sky first, or skip the wall tiles under it), `ledge` (rock floor slab), `boulder`.
Suggested ladder mapping (section 4): 1 clear (add `twigs` litter at level 0, remove), 2 `perch_bar` -> proper perch, 3 `nest_straw`, 4 lamps (`lamp_stone`, `lantern_warm`), 5 open the wall (`sky_sunrise` + `cave_arch`, window light),
6 vines and `flowers_den`, 7 `perch_eagle`, 8 `nest_gold` with embers and `lantern_blue`. Use warm sunrise light (pink/orange) falling from the arch via `h.add_shaft` and `h.add_light`.

## 9. Room upgrades and Pyr — implementation status (2026-10-27)

- The server has a seven-room ladder catalog in `ide/server/home_rooms.py`, with a contract test against `rooms.gd`. Its 62 steps total 2,028 Embers. The helper projects old hearth/armory visual tiers without spending currency; the old map tier was not persisted by the app.
- Next: wire atomic purchases and cloud projection, then the Home panel and isolated browser verification. The catalog alone does not enable buying upgrades.
- Pyr's four eagle sheets are not present in `tools/home_art/sheets/pyr/`; prepare the loader and exact image prompts after the purchase workflow is complete.
