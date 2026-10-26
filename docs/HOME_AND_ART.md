# Home, art pipeline and handoff

Everything about the walkable **Home** (a Godot scene embedded in the app), the code-drawn
art, the hunter skins, how it was built and tested, the gotchas, and what comes next.
Written so another agent (or you in a month) can pick it up cold.

Last updated 2026-10-27. Start with "Quick start", then "How it fits together".

---

## 1. Quick start

```sh
tools/build_home.sh                     # regenerate art, export the Godot web build to ide/frontend/public/home/
npm --prefix ide/frontend run build     # rebuild the app (copies public/ into dist/)
tools/home_art/shots.sh                 # screenshots of the room at several spots (ide/home-godot/shot_*.png)
python3 tools/home_art/make_hunter.py   # regenerate only the hunter layers
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
- `tools/home_art/make_hunter.py` the layered hunter and its skins.
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

**The hunter** (`make_hunter.py`): **24x40** frames in **three layers** so cloth moves independently:

- `cape` behind the body (drawn in front when facing up); 4 sway frames; keeps breathing when idle.
- `body` head, afro, collar, torso, arms, legs, boots; walk = stand, step A, stand, step B.
- `gown` the long coat skirt over the legs; swings against the step.

Sheets: rows are down, left, right, up (right = mirror of left); `hunter_<look>_{body,gown,cape}.png`.
In Godot the layer order is the child order of the `Hunter` node (cape moved to the end when facing up;
**do not use negative `z_index`**, it draws under the floor).

**Looks (skins)**: palette + a few switches on one cut: `dracula` (crimson lining and sash, default),
`alucard` (gold trim, silver lining, white cravat, leather belt), `belmont` (grey-green tunic and band,
red tabard). Add one by adding a dict to `LOOKS` and preloading its three PNGs in `home.gd` `LOOKS`.
The app picks one (button in the room bar, `localStorage questlab.hunterLook`; could move to Settings
or become unlockable cosmetics). The avatar's own traits stay in all looks: umber skin, an afro, a goatee.
Different cuts per skin (not just palette) are possible later by branching in the draw functions.

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
5. Godot `const` resources cannot be modified: the font's `antialiasing` is set at runtime on a `var`.

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

### 8a. Weapons: three playstyles; trinkets stay the build options (proposal, owner idea)

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
are already split (cape / body / gown), so attack frames can add a `weapon` layer and an `arms` override.
Draw at 24x40 or render bigger in Blender and clean up.

### 8c. Home next

- More stations are placed; give each real depth: Pantry (cook/stock meals), Study desk (spend Embers on
  study upgrades, LearnHarness), Training ring (sparring rewards), Trophy wall (relics on the wall as
  passives, boss relics), Pyr's perch (Pyr's stages and abilities).
- **Ember upgrade tracks** per station with the economy target below; pre-run **loadout** pick
  (relic + Aid + boon); day/night and a hearth that dies without activity (`fire_lit` exists).
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
2. Skins: should looks be unlockable cosmetics (earned) or always selectable?
3. Hunter art: anything to change after playing (bigger sprite, a sword in hand, lighter coat)?
4. Station depth order: which of Pantry / Study / Training / Trophy / Perch first?
