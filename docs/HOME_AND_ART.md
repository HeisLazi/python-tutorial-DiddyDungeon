# Home, art pipeline and handoff

Everything about the walkable **Home** (a Godot scene embedded in the app), the code-drawn
art, the hunter skins, how it was built and tested, the gotchas, and what comes next.
Written so another agent (or you in a month) can pick it up cold.

**Current status of the room rebuild and the exact next steps: `docs/HOME_REBUILD_HANDOFF.md` (read it first).**

Last updated 2026-10-27 (new Alucard hunter from AI sheets). Start with "Quick start", then "How it fits together".

---

> **Current update:** The playable home now consists of the Great Hall and Pyr's Den. The hall has separate gear, hunter and trophy areas, no benches or banquet furniture, and a clear route to the hearth and den. The eighth hall upgrade now decorates the trophy alcove. Home uses an unarmed 32px hunter in 38×38 cells from `tools/home_art/assets/hunter_v3`, built from the source turnaround and walk sheet by `tools/home_art/build_hunter_v3.py`. The old room-chain, follower behavior and 48×46 hunter descriptions below are historical. Pyr roams independently in the den; the main hall hosts the practical character stations.

## 1. Quick start

```sh
tools/build_home.sh                     # regenerate the tiles, copy the hunter sheets, export the Godot web build to ide/frontend/public/home/
npm --prefix ide/frontend run build     # rebuild the app (copies public/ into dist/)
tools/home_art/shots.sh                 # screenshots of the room at several spots (ide/home-godot/shot_*.png)
python3 tools/home_art/from_sheets.py tools/home_art/sheets tools/home_art/assets/hunter 40   # re-cut the hunter from the source sheets
python3 tools/home_art/make_tiles.py    # regenerate only the tileset
```

Needs: Godot 4.7.2 (flatpak shim `godot`), its **Web export templates** (see section 9), system
`python3` with Pillow (the repo `.venv` does NOT have Pillow; use system python for art),
Blender 5.2 only for the optional 3D renderer.

The web build is **git-ignored** (`ide/frontend/public/home/`). The app falls back to the classic
Home panel when the build is missing, so a fresh clone still works.

## 2. How it fits together

```
React app (ide/frontend)                       Godot web build (ide/home-godot)
  RpgViews.jsx  HomeRoom  ──iframe /home/──►    scripts/home.gd   (draws + walks, no rules)
     │  window.diddyHomeReceive(json) ───────►     state: hp, embers, fire_lit, crt, look, tiers, toast
     │◄── window.parent.postMessage ────────────   {source:"diddy-home", type:"ready"|"use", station}
  performHomesteadAction, onNavigate, Armory panel
```

- **The app owns every rule.** Godot only draws and walks. It never reads the save, never calls the
  backend. It sends `use` events; the app decides what happens (HP, items, navigation).
- **State in** (`HomeRoom` in `RpgViews.jsx`, `homeRoomState`): `hp`, `max_hp`, `embers` (the existing
  `homestead.upgrade_tokens`), `fire_lit` (did you code today: `activity_log.days[today]`), `crt`
  (scanlines on/off), `look` (hunter skin), `tiers`/`max_tiers` per station (gold pips; derived from
  `homestead.room_upgrades`), and an optional `toast` string shown in the room.
- **Events out**: `{source:"diddy-home", type:"ready"}` once Godot booted, then
  `{type:"use", station:"<id>"}` when the hunter presses E at a station. The React side checks
  `event.origin` and `event.source` (same origin, the iframe's window).
- **Sizing**: the room is 240x160 (GBA). Godot scales by whole *device* pixels, so the React frame is
  sized from `devicePixelRatio` and the window height to the largest exact multiple. If you change
  zoom handling, keep that or you get black bars / blurry pixels.
- **Keyboard**: Godot tracks WASD/arrows from key *events* (not polling) and every tap moves ~5 px, so
  even very short presses work. E / Space / Enter / Z uses a station.

### Stations (`_station(...)` in `home.gd`, handled in `HomeRoom.useStation`)

| id | Where | What E does (app side) |
|---|---|---|
| `hearth` | back wall, centre | `homestead_action recover` (full HP) |
| `armory` | back wall, left of centre | opens the real Armory panel as an overlay |
| `trophy` | back wall, far left | Settings > Player Stats (activity graph, records) |
| `pantry` | back wall, right (cauldron below) | `homestead_action meal` (+HP, needs a packed meal) |
| `study` | left floor, desk | Tutor Notebook |
| `training` | left-bottom, rune ring + dummy | Tutor Notebook, Sparring surface (set via `sessionStorage questlab.tutor.surface`) |
| `map` | right floor, table | Infinite Dungeon |
| `perch` | right-bottom | `homestead_action feed_pyr` (needs a packed meal) |
| `door` | bottom centre | the Forge |

Errors from the server ("No meals are packed") are shown as the toast.

## 3. Repo map

- `ide/home-godot/` the Godot project. `scripts/home.gd` (everything), `shaders/crt.gdshader`,
  `art/` (generated PNGs + `tiles_data.gd`, font), `export_presets.cfg` (preset "Web", single-threaded).
- `tools/home_art/make_tiles.py` the hall: tiles, objects, stations. Writes `tiles.png`, `tiles.json`,
  `tiles_data.gd` (a `TilesData.REGIONS` dictionary so exports never need a loose JSON).
- `tools/home_art/from_sheets.py` cuts the hunter out of the AI-generated sheets in `tools/home_art/sheets/`
  into `tools/home_art/assets/hunter/hunter_{front,side,back}.png` (committed; `build_home.sh` copies them into
  `ide/home-godot/art/`). `sheets/` holds the source art: `front_idle.png`, `side_walk.png`, `back_walk.png`
  (8-frame strips on grey), plus `actions.png` (crouch/jump/dash/slash) and `walk_hires.png` (big walk) for later.
- `tools/home_art/make_hunter.py`, `rig_hunter.py`, `alucard.py`, `pixlib.py`, `from_reference.py` are the
  **superseded** hand-drawn and cut-and-patch attempts (kept for history; see section 5).
- `tools/home_art/hunter_blender.py` a headless Blender turnaround renderer (see "what failed").
- `tools/home_art/shots.sh` screenshot harness. `tools/build_home.sh` full build.
- `ide/frontend/src/RpgViews.jsx` `HomeRoom`, `homeRoomState`, `useHomeBuild` (+ `v2.css` `.home-room*`).

## 4. The art

**Style**: GBA era (Pokemon FireRed overworld) + Castlevania mood. 16x16 tiles, 1px dark outline,
flat 3-4 tone shading, a fixed palette (app indigo, crimson, gold, ember). Retro-fied in Godot with the
CRT shader (scanline per game pixel, faint RGB mask, vignette; never bends or blurs).
Everything is drawn **in code** (`Sprite.rect/hline/disc/outline`) so it is reproducible and tweakable.

**The hall** (`make_tiles.py`): marble checker floor, stone-block wall + plinth, crimson carpet runner,
pointed-arch hearth (3 frames: fire 0/1 and `fire_out` for a cold hearth), stained-glass windows,
banners, sconces, pillars, candelabras, braziers, armour statues, urns, chest, bookshelves, the
station pieces (trophy case, weapon rack, study desk, cauldron, dummy, rune ring, pantry shelves, perch),
Pyr (2 flame frames), moonbeams. Animated pieces are `name_0` / `name_1`; `home.gd` toggles them.
To add a piece: write a function returning a `Sprite`, add it to `pieces` in `build()`, run the script,
place it in `_build_room()` with `_piece(...)` (top-left) or `_piece(..., true)` (bottom-centre).

**The hunter** is an Alucard-style vampire hunter (the owner's pick: "alucard should be our base hunter
design"): black coat with gold trim, crimson-lined cape, white cravat, tall boots, a sword at the hip, a
**black afro**, **deep umber skin**, and a flat, featureless face (features at this size read as floaty
eyes). It is **one sprite per facing**, 48x46 px frames (the character is 40 px tall, feet on the bottom row),
in `hunter_front.png` (down), `hunter_side.png` (left; right is the same sheet flipped) and
`hunter_back.png` (up). Each sheet is 12 frames in a row: **8 walk frames** (cols 0-7, `WALK_FPS` 10) then
**4 idle frames** (cols 8-11, `IDLE_FPS` 1.6, a breathing bob; the side idle uses the frame with the feet
together so he does not look stuck mid-stride). The cape and sword motion is baked into the walk frames.
`home.gd` `_refresh_hunter()` picks the texture by facing, flips for right, and the column by state.

How it was made (this is the process that finally worked, see "what failed"): see **"How the hunter was
made"** below. To change him, change the sheets and re-run `from_sheets.py`; the room code does not change.

**Skins**: the old palette looks (dracula, alucard, belmont) were removed with the layered hunter; the owner
wants skins as **unlockable cosmetics, reworked**, each a distinct look (not a palette swap): e.g. the
Dracula-gown look from the concept art, a Belmont, bosses. Do them the same way: generate one sheet set
per skin, run it through `from_sheets.py` into its own folder, and load by name in `home.gd` (the app
already sends `state.look`; `HUNTER_LOOKS` in `RpgViews.jsx` has one entry, so the Look button is hidden).

**How the hunter was made**

1. **Design reference.** A real image model draws the design; the sprite is never hand-pixelled. The first
   reference was a Higgsfield `z_image` turnaround (prompt: "Pixel art game character sprite sheet, a gothic
   vampire hunter in a long black coat with gold trim and a crimson-lined cape, tall collar, white cravat,
   long wavy dark hair, umber brown skin, small goatee, tall black boots with silver cuffs, 16-bit Castlevania
   Symphony of the Night style, front view, side view and back view in a row, flat plain background, crisp
   pixels"). The owner then generated cleaner sheets with their own image models (Google), in the style of
   the Grimoire-of-Souls roster sprites, with an afro and a sword.
2. **Sheets.** What works is three strips of **8 frames each on a flat grey background**, same character:
   front idle, side walk (facing left), back walk. Example prompt: "Pixel art sprite sheet, 8-frame side-view
   walk cycle of a gothic vampire hunter facing left, dark umber skin, round black afro, long black coat with
   gold trim, crimson-lined cape, white cravat, tall black boots, sword at the hip, Castlevania Symphony of
   the Night style, clean crisp pixels, flat plain grey background, even spacing, same character in every
   frame." Save them as `tools/home_art/sheets/{front_idle,side_walk,back_walk}.png`.
3. **`from_sheets.py`.** Slices the frames into equal cells (side frames touch, so no gap finding), removes the
   background, drops stray fragments of neighbouring frames (cape tips), **fills the cape's hollow interior**
   (it is the same grey as the background, so it was deleted: found by flood-filling the outside and filling
   what is enclosed), scales each sheet to one height, anchors the feet, lifts contrast and colour, quantizes
   all three sheets to **one 56-colour palette**, flattens the face, blackens the hair, recolours the skin to
   umber, and adds the idle loop.
4. **Godot** loads the three PNGs; nothing else knows about the art.

**Reference direction** (from the owner): FireRed overworld for tiles/feel, the Gen-5 trainer sheet layout
for animation sets, Castlevania (Dracula concept art, Alucard, Trevor) for the character. The references
are for form and craft, not characters; the theme stays our dark arcade monster-hunter world.

## 5. What was tried and what failed (so nobody repeats it)

1. **Blender 3D to 16x24 / 16x32 pixels**: a box-model hunter rendered from a 3/4 camera and shrunk to
   sprite size gave dark mush (no readable face, wrong proportions). Hand-placed pixels in code win at
   this size. Blender is kept for big pieces (portraits, props, future animated attack frames at larger
   scale then cleaned up). `hunter_blender.py` is a working headless renderer; note Blender is a flatpak
   and cannot see relative paths: pass absolute paths under your home dir.
2. **Locs** were first attempted; at 24x40 they blur. The owner asked for an **afro or waves**; the afro
   (rounded mass with curl-texture dots) reads far better.
3. **Too-dark cloak on a dark floor** made the hunter a murky silhouette. Lift the value (cool slate
   cloak, bright folds) and keep crimson and gold punchy.
4. **Integer scaling**: Godot scales in physical pixels; at browser zoom 125% a 720 px CSS frame showed
   2.4x with bars. Size the frame from `devicePixelRatio` (done).
5. **Hand-pixelled sprites** (`alucard.py`, `pixlib.py`) came out boxy and nothing like the references.
6. **Cutting one AI turnaround into animated layers** (`from_reference.py` + `rig_hunter.py`): the front
   view worked (clean source), but the AI **side view was noisy** (a 4 px face, a hidden skeleton, hair and
   coat classes mixed), so the rig produced a flat wedge head, a stilt-legged walk and a speckled coat.
   Patching it procedurally (drawn side head, arm and legs) was brute force and still looked wrong. Lesson:
   get a **clean source image per view** (a real side walk strip), and only post-process it.
7. **Quantizing to a small palette** merged skin into hair and dropped the gold trim; use ~56 colours after a
   contrast/colour lift. **Median-cut on a dark sheet** biases to the dominant dark tones.
8. The AI sheets had **the cape the same grey as the background** (fill enclosed hollows) and **eyes that moved
   between frames** (flatten the face).
9. Godot `const` resources cannot be modified: the font's `antialiasing` is set at runtime on a `var`.

## 6. Testing notes (for agents with a browser tool)

- The browser tool's synthetic key presses have no `code`, so Godot's web build ignores them. Drive the
  game by dispatching real-looking events into the canvas:
  `canvas.dispatchEvent(new KeyboardEvent('keydown',{key:'w',code:'KeyW',keyCode:87,bubbles:true}))`.
  Hold by delaying the matching `keyup`. The script runs asynchronously: wait, then screenshot.
- The JS tool does not show return values; `console.log('TAG ...')` and read it with the console tool.
- Godot `print()` in the web build goes to `console.log`.
- Screenshots of the room without a browser: `tools/home_art/shots.sh` (Godot window + `--shot`).
  The flatpak sandbox cannot write into hidden folders (`~/.claude`): write under the repo.
- Open Home through the project map card ("Home"), not by URL.

## 7. Process and repo gotchas (learned the hard way)

- Work happens in the worktree `.claude/worktrees/tauri-arcade` (branch `feature/tauri-arcade`); the main
  checkout is fast-forwarded after each verified commit (check `progress.json` md5 unchanged: it is the
  owner's real save). Never push to main, never force-push.
- The worktree guard rejects complex shell (loops, `$(...)` with git, heredocs). Put scripts in files.
- `ide/frontend/src/AppV2.jsx` and parts of `ide/server/app_v2.py` have **CRLF** line endings. Edit
  with byte-safe scripts (read bytes, replace, write bytes) or the diff explodes. `keep_endings.py`-style
  restoration was used once; prefer exact-match replaces.
- Tests must never write the real save: `ide/server/conftest.py` points `app_v2.PROGRESS_PATH` at a temp copy.
- Frontend tests: `node --test ide/frontend/src/cloud/` (baseline 87 pass / 10 pre-existing failures).
  Backend: `.venv/bin/python -m pytest -q ide/server/` (229 pass).
- Anything that spends the owner's model credits must be an explicit click; never read AI auth files.

## 8. Roadmap and designs (agreed direction, not built)

### 8a. Weapons: three playstyles; trinkets stay the build options (owner confirmed: "yes i love this")

Replace the long list of weapons with **three weapon types**, each a playstyle, each with tiers/looks:

| Type | Playstyle | Idea for the mechanic (to confirm) |
|---|---|---|
| **Whip** (chain whip) | steady, reach, combos | each consecutive clean objective adds a combo step (extra Resolve damage and Guard Break coins); a miss resets it |
| **Sword** (Alucard-style) | precision, burst | first objective of a bounty deals extra; an all-clean fight crits the finisher |
| **Magic** | utility, information | spells with a small per-fight charge: reveal a hint with no reward penalty, reveal a boss weakness, ward one wrong answer |

**Trinkets** remain the actual build choices layered on top (reduction, guards, XP/coin bonus, loot luck,
revive, Aid). Existing weapon items map onto the three types as tiers. This needs a data change in the
campaign armory files and `_gear_effects`; do it together with the combat stage below.

### 8b. Combat stage (animated attacks)

The bottom-left panel where Pyr sits during the Forge and Infinite Dungeon questions becomes a small
**battle stage**: the hunter (current look and weapon) vs the mob. A correct answer plays the weapon's
attack animation (whip lash, sword slash, spell cast) and hit reaction; a miss plays the counterattack;
Guard Break, ward and loot get their own short effects. Pyr moves to the stage edge. The hunter layers
are one sprite per facing now with the **sword baked into every frame**, so the whip and magic weapons need
their own sheets (or a sword-less base plus a weapon layer). `tools/home_art/sheets/actions.png` already has
crouch, jump, dash and slash frames to build attacks from. Generate them the same way as the walk sheets.

### 8b2. The Home rebuild: rooms, lighting and the "great room" checklist (2026-10-27)

Home is being rebuilt as **seven one-screen rooms** (plan in 8c). The engine and the Great Hall are done on
`feature/tauri-arcade` (not merged until every station has a room: the old 9-station hall is gone there).

- **View 320x180**, 16 px tiles, top-down 3/4 (back wall of 4 rows, floor below), the hunter 40 px tall.
  The concepts in `tools/home_art/concepts/` are isometric or oblique; they are targets for content, palette and
  light only. Do not try to reproduce their camera (the hunter only has front/side/back sprites).
- **Engine** (`ide/home-godot/scripts/home.gd` + `rooms.gd`): `Rooms.build(h, id, tier)` builds a room from the tileset;
  `go_room()` fades between rooms; the room **rebuilds itself when the app sends a new tier**. Helpers on `h`:
  `tile/bg/obj/anim`, `block`, `station`, `door`, `add_light` (banded `PointLight2D` + flicker), `set_ambient`
  (`CanvasModulate`), `add_embers` (`CPUParticles2D`), `add_shaft` (additive beam), `add_patch` (coloured light on the
  floor), `add_shadow` (contact shadow), `add_tint` (flat rectangle, wall-base shadow), `add_chain`, `sway` (cloth shader).
  Test flags: `--room=great_hall --tier=0..3 --pos=x,y --face=up --shot=file.png`; `tools/home_art/shots.sh <room> <tiers>`.
  The shots use the Compatibility renderer, the same as the web export. **Verify in the real web build in Chrome too**
  (serve `ide/frontend/public/home` with `python3 -m http.server`, then send state with
  `window.diddyHomeReceive(JSON.stringify({tiers:{hearth:3}}))`); hold keys by dispatching `keydown`/`keyup` with a `code`.
- **Great-room checklist** (every room follows it; it is also at the top of `rooms.gd`):
  1. Tier 0 is a believable neglected room, max is the concept: change props, light and motion between tiers.
  2. Depth: a contact shadow under every prop, a shadow along the wall base, columns and trim on the wall.
  3. Light tells the story: warm pools, cold window beams, coloured glass patches on the floor, a reflection on polished floors.
  4. Life: flames and lights flicker, embers and dust drift, cloth sways.
  5. Wear and clutter at the start, polish at the top; nothing symmetrical by accident.
  6. Scale: doors ~48 px, tables ~24 px, hearth ~56 px next to the 40 px hunter.
- **Where the art comes from.** The code-drawn pieces (`hall_pieces.py`, `make_tiles.py`) are clean but simple. The
  quality jump for hero props is the same as for the hunter: an image model draws them, a script cuts them.
  **Prop sheets:** one image of separate props on a flat plain grey background, top-down 3/4 camera, same palette
  (indigo stone, crimson, gold, ember, navy and white marble). Then
  `python3 tools/home_art/from_props.py sheet.png hearth_b_0@56 hearth_b_1@56 ... --out tools/home_art/props`
  (names in reading order, `@N` = height in px). `make_tiles.py` loads every PNG in `tools/home_art/props/` over the
  code-drawn piece with the same name, so the room code does not change. Animated props are `name_0`, `name_1`.
  Example prompt: "Pixel art prop sprite sheet for a gothic castle great hall, top-down three-quarter view like
  Pokemon FireRed and Castlevania, separate objects with clear gaps on a flat plain grey background: a stone
  fireplace with a small fire, the same fireplace with a big fire, an ornate gold-trimmed fireplace with blue fire,
  an iron chandelier with six candles, a suit of armour on a plinth, a long banquet table with a crimson cloth and
  goblets, four high-backed crimson chairs, wooden benches, a gold urn, wall torches, crest banners, a stained-glass
  window, an oak door and a carved gold door. 16-bit, chunky 1px dark outlines, crisp pixels, no text, no shadows on
  the floor."

#### Rooms built so far (all on `feature/tauri-arcade`, not merged: Pantry, Trophy Gallery, War Room and Pyr's Den do not exist yet, so their stations are missing)

| Room | Ladder (`rooms.gd` `LADDERS`) | Exits | Stations | Props from |
|---|---|---|---|---|
| Great Hall (`great_hall`) | 9 steps, 344 Embers | west to the Library, east to the Hall of Arms | hearth, door (Forge) | `hall_fire_decor`, `hall_furniture`, `hall_wall_clean` |
| Library (`library`) | 9 steps, 296 Embers | east to the Great Hall | study | `lib_furniture`, `lib_decor`, `lib_wall` |
| Hall of Arms (`armory`) | 9 steps, 300 Embers | west to the Great Hall | armory, training | `arms_racks`, `arms_rings`, `arms_wall` |

Doorways: `_shell(h, marble_from, marble_to, left_exit, right_exit, floor_kind)` takes `{"to": room, "spawn": feet position in that room}` for
each side and leaves a gap in the wall at y 112-172 (`DOOR_Y`, `DOOR_H`). Keep that strip free of furniture at every level (the max-level banquet
once blocked the east door). Each room's step constants are `GH_*`, `LB_*`, `HA_*`. Sheets are 0.25 credit each; the three sheets per room took about
five minutes; Higgsfield rate-limits parallel jobs, so submit one at a time.

#### The Great Hall's image-sourced props (how they were made)

Three Higgsfield `z_image` prop sheets (0.25 credit each; Google image models are better if you have them) were saved in
`tools/home_art/sheets/props/` (`hall_fire_decor.png`, `hall_furniture.png`, `hall_wall_clean.png`; the wall sheet had stray
planks and a block painted out by hand because they glued the gold door to a plank). `from_props.py` strips the model's cast
shadows and ground line, and `make_tiles.py` loads the results from `tools/home_art/props/` over the code-drawn pieces. To
regenerate (names are in reading order, `-` skips a prop, `@N` is the height in px):

```sh
python3 tools/home_art/from_props.py tools/home_art/sheets/props/hall_wall_clean.png window_glass@40 window_plain@40 banner_crest@36 door_wood@52 door_gold@52 pillar_g@50 --out tools/home_art/props
python3 tools/home_art/from_props.py tools/home_art/sheets/props/hall_fire_decor.png "hearthm@66!62-88,28-70>bg" chandelier@40!0-50 knight@48 - torch@28!0-50 urn_gold@24 --out tools/home_art/props
python3 tools/home_art/from_props.py tools/home_art/sheets/props/hall_furniture.png - - chair_l@24 - - table_small@20 bench@14 - barrel@20 crate@20 --out tools/home_art/props
python3 tools/home_art/make_tiles.py
```

One fireplace serves every level: `!62-88,28-70` shifts the fire region 1 px for a 2-frame flicker and makes a cold `_out` frame;
`>bg` derives a dim (`hearthb`, levels 0-3) and a blue (`hearthg`, level 12) version. Still code-drawn: the banquet table
(it merged with a chair on its sheet), broken benches, torn banner, stone pillar, floor and wall tiles, rubble and other dressing.
Lessons: ask for ONE row of well-spaced props per sheet and split themes across several sheets; the model likes to add a
ground line and soft shadows (the slicer removes them); animated props need a flicker pair made from one image.

### 8c. Home next

- More stations are placed; give each real depth: Pantry (cook/stock meals), Study desk (spend Embers on
  study upgrades, LearnHarness), Training ring (sparring rewards), Trophy wall (relics on the wall as
  passives, boss relics), Pyr's perch (Pyr's stages and abilities).
- **Ember upgrade tracks** per station with the economy target below; pre-run **loadout** pick
  (relic + Aid + boon); day/night and a hearth that dies without activity (`fire_lit` exists).
- **Redesign (owner request, plan agreed in chat): compact Home, seven one-screen rooms.** View 320x180
  (20x11 tiles; the 40 px hunter is too big for 240x160), doors that fade-cut between rooms, Pyr follows.
  Locked rooms start boarded up and cost Embers to open (Great Hall, Library and Hall of Arms open from the
  start). The bridge and stations are unchanged. Draw order: Great Hall, Library, Hall of Arms, then Pantry,
  Trophy Gallery, War Room, Pyr's Den. Design each room as a concept image first (image model), then build tiles
  to match; do not draw furniture blind.

  Layout:
  ```
                   [Trophy Gallery]
                          |
  [Library] --- [GREAT HALL] --- [Hall of Arms]
                          |             |
     [Pantry] ---- [door: Forge]    [War Room]
                          |
                    [Pyr's Den]
  ```

  **Upgrades are a ladder of small steps, not four jumps.** Every room has 9-10 levels (0 = neglected base, max = the
  concept); each purchase adds or changes ONE visible thing, has a name and an Ember cost, and plays a flash plus a
  "BUILT: <name>" toast. The Great Hall's ladder (the template) lives in `rooms.gd` `LADDERS` (cost total 344 Embers,
  a proposal to tune against the ~2,100 total across seven rooms): Clear and mend the hall (18), Rebuild the hearth + second
  torch (30), Hang crest banners (20), Lay the crimson runner (24), Reglaze the windows (28), Floor
  the hall in marble (68), Hang the chandelier (44), Set the banquet (52), The grand finish (60). (Owner call: "mend the
  benches" and "light a second torch" are not steps of their own; they were folded into the first two.) Build a room as
  `_room(h, lv)` with named thresholds (`GH_*` constants), and ramp light and ambient with `lv`.
  Test every step: `tools/home_art/shots.sh great_hall 0 1 2 ... 10`. The app can send `levels: {great_hall: n}`; the older
  `tiers` (0..3 per station) still work, spread over the room's levels. The table below is the milestone view (base, a few
  steps in, max), not the full ladder:

  | Room (station) | Base | Tier 1 | Tier 2 | Max |
  |---|---|---|---|---|
  | **Great Hall** (hearth) | bare stone, a small fire, one torch, cold draughts | carpet runner, two sconces, banners | chandelier, stained glass, a warm hearth glow | grand hall: tall arches, gold-trimmed carpet, a roaring blue-gold hearth, moonbeams, floating embers |
  | **Library** (study desk) | a desk, one shelf, a stub candle | full shelves, a lectern, a reading lamp | rolling ladder, globe, rugs, a second floor of books | tower library: glowing tomes, floating pages, a skylight, a brass orrery |
  | **Hall of Arms** (armory, training) | a bare rack, one wooden dummy, a dirt ring | proper weapon wall, a stone ring, banners | trophy shields, spotlit weapons, iron dummies | a champion's hall: runed ring that glows, enchanted weapons floating on stands, battle standards |
  | **Pantry** (meals) | a crate and a pot over a fire | shelves, hanging herbs, a barrel | a long table, a proper cauldron, stocked shelves | a feast kitchen: steaming pots, hanging meats and garlic, a roaring range |
  | **Trophy Gallery** (trophy wall) | an empty case and bare plinths | cases with first relics, a window | spotlights, a carpet, more plinths | a museum of your runs: boss relics glowing, a mosaic floor, a gold-framed portrait of the hunter |
  | **War Room** (map table) | a bare table, a rolled map | pinned maps, a lamp | a carved table with markers, a window onto the night | a living map: lit dungeon sites, wax seals, moving markers, a chandelier |
  | **Pyr's Den** (feed Pyr) | a bare perch and a few twigs | a nest and a lamp | a rock aerie, a moonlit window | a mountain aerie: crag, clouds, sunrise glow, drifting embers (like the phoenix reference) |

- **Pyr becomes a fire eagle (owner pick: the blue-and-gold phoenix eagle in
  `tools/home_art/sheets/pyr_phoenix_reference.png`).** Colour identity: deep blue plumage, gold/ember edges,
  a flame crest and a long ember tail. Four stages, each a new sprite set (idle, fly-follow, perch, feed):
  1. **Ember chick**: the current flame with a tiny beak and eyes, hops.
  2. **Fledgling**: small blue-gold wings, short tail, a flame crest tuft, flaps to follow.
  3. **Firehawk**: full eagle, ember-edged wings, glowing eyes, glides beside the hunter.
  4. **Phoenix eagle** (max): the reference: huge wings, a long flame tail, leaves a trail of embers; the Den
     becomes its aerie. Stage is tied to Pyr's level and to Den tier; each stage can unlock a free-ask/aid.
  Make each stage with the same image-model process (clean sheet, then a script), not hand-drawn.
- Skins as unlockable cosmetics; a skin picker in Settings; weapon shown on the walking sprite.
- A bigger hall built in Tiled; castle wings per campaign.

### 8d. Economy target (from the README)

Maxing every upgrade: ~2,100 Embers total at ~10 Embers per cleared floor; 30-40 h newer coder, ~20 h OK
player, ~15 h experienced, under 5 h speedrunner (300 wpm). The Dungeon should log playtime and floors per
run so this can be tuned.

### 8e. Dungeon (parked)

Per-location mini maps (mountains, ocean monuments, abandoned cities), unseen depth layers, rewards for
exploring over boss-rushing, boss weaknesses discovered from small mobs (a concrete silly edge, e.g.
double damage for two turns for striking a swollen ankle, remembered in the Codex).

## 9. Godot web export templates

Installed once at `~/.var/app/org.godotengine.Godot/data/godot/export_templates/4.7.2.stable/`
(`web_release.zip`, `web_debug.zip`, `web_nothreads_*.zip`, `version.txt`; ~41 MB). They came from
`Godot_v4.7.2-stable_export_templates.tpz` (1.28 GB, official godot-builds release); only the web files
were extracted and the download deleted. The preset uses **single-threaded** web export, so no special
HTTP headers are needed. Re-install the same way if the templates disappear.

## 10. Open questions for the owner

1. The three weapon mechanics above (whip combo / sword burst / magic utility): confirm or change.
2. Skins: answered: unlockable cosmetics, reworked as distinct looks. What unlocks each one?
3. Hunter art: the coat is nearly black on the dark floor; want a lighter coat, a rim light, or a lighter floor?
4. Station depth order: which of Pantry / Study / Training / Trophy / Perch first?
