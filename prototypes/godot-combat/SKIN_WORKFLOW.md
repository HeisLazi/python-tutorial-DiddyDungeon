# Combat skin workflow

This prototype separates shared combat styles/timings from each hunter's sprite sheets in `combat_catalog.gd`. Tate has three equipment-driven outfits: Ivory Revel, Gravebound Warden and Harvest Revenant. Registering a skin does not create artwork. The existing sheets include the weapon in each pose, so every new skin needs its own weapon-specific art, rather than attaching an arbitrary weapon to Tate's arm.

1. Prepare right-facing, transparent sprite sheets for `sword`, `staff`, `whip`, `greatsword`, `handmagic`, `scythe`, and `oil`. Each sheet has exactly four equal horizontal cells, 72 pixels high. A style's sheets must have the same cell width and align its feet consistently. The sprite offset positions the foot anchor; Tate uses `(13, 0)` for 96px sword cells and `(19, 0)` for 128px cells. Tune the offset to the new art.
2. Supply `action` and `hurt` textures and an `offset` for each style. The staff and handmagic styles also require `cast_origin`, a `Vector2` relative to the hunter root where the projectile begins (Tate uses `(42, -52)`). Align it with the hand or staff tip in the casting pose. Action poses 0–3 are idle, windup, strike, recovery; hurt poses 0–3 are flinch, recoil, stagger, recovery. Sword additionally uses an `idle` sheet and a `follow` sheet (poses 0–3 are the follow-through). `idle_frames` is an optional nonempty list of frame indices 0–3; without it the first pose bobs. Supply an `idle` texture for any style if its idle frames live elsewhere.
3. Create a skin dictionary shaped like `tate()` in `combat_catalog.gd`, with a unique `id`, display `name`, and `styles` keyed by style IDs. Load/import all textures and call `register_skin(skin)`, then `select_skin(id)` when no turn is running. Registration rejects missing styles, missing textures, mismatched sheet sizes, and invalid idle frames, so unsupported combinations cannot silently use another character's art. The game selects these outfits from equipped armour; there is no separate skin picker.
4. Review every style's idle, hit, and miss in both modes at actual render scale, checking grip, clipping and foot alignment. Run `godot --headless --path prototypes/godot-combat --script res://tests/animation_smoke.gd` after importing the project.

Styles currently share fixed frame order, attack timing, movement, and spell effects. A skin that needs a materially different animation choreography will require extending the style controller rather than changing only the artwork.

For a new character, start with an identity reference and create complete poses of that character with each weapon baked into the art. Keep the same silhouette, face, outfit, foot baseline and grip across sheets. If using the existing concept-sheet pipeline, add the new source names, per-pose hip anchors, cell width and top position to `source-art/slice_animations.py`, then run it with system `python3` and Pillow. Inspect the resulting sheets for clipping and alignment; generated poses still need art review.

For example, after creating and importing the actual new artwork, a local `res://skins/aria.gd` could return a skin definition like this (the paths are illustrative and must point to that character's own files):

```gdscript
extends RefCounted

static func definition() -> Dictionary:
    return {"id": "aria", "name": "ARIA", "styles": {
        "sword": {"idle": preload("res://art/aria-sword-idle.png"), "action": preload("res://art/aria-sword-action.png"), "follow": preload("res://art/aria-sword-follow.png"), "hurt": preload("res://art/aria-sword-hurt.png"), "offset": Vector2(13, 0), "idle_frames": [0, 1, 2, 3, 2, 1]},
        "staff": {"action": preload("res://art/aria-staff-action.png"), "hurt": preload("res://art/aria-staff-hurt.png"), "offset": Vector2(19, 0), "cast_origin": Vector2(42, -52)},
        "whip": {"action": preload("res://art/aria-whip-action.png"), "hurt": preload("res://art/aria-whip-hurt.png"), "offset": Vector2(19, 0)},
        "greatsword": {"action": preload("res://art/aria-greatsword-action.png"), "hurt": preload("res://art/aria-greatsword-hurt.png"), "offset": Vector2(19, 0)},
        "handmagic": {"action": preload("res://art/aria-handmagic-action.png"), "hurt": preload("res://art/aria-handmagic-hurt.png"), "offset": Vector2(19, 0), "cast_origin": Vector2(42, -52)},
    }}
```

Load that definition from the scene or the equipment bridge, check `register_skin(preload("res://skins/aria.gd").definition())`, and then call `select_skin("aria")`. Adjust offsets and origins to the new art; these example values are Tate's, not universal measurements.

## Verification and current scope

The live bridge smoke test validates all seven styles for the three equipment outfits, checks their distinct action and hurt sheets, and verifies charm and companion switching. The animation smoke test covers attack and hurt timing, skin registration, custom casting origins, and both environment modes. Review idle, attack and hurt at actual render scale when replacing art; a valid sheet can still have a poor grip or clipped blade.

Build the browser preview from the worktree root:

```sh
godot --headless --path prototypes/godot-combat --import
godot --headless --path prototypes/godot-combat --script res://tests/animation_smoke.gd
godot --headless --path prototypes/godot-combat --export-release Web ../godot-combat-web/index.html
```

The local preview server uses port 17532. The simulation backdrop belongs to
sparring; the crypt, torches and amber lighting belong to dungeon mode. The game uses the scene in both Dungeon and Sparring, with combat state owned by the app. A player-facing skin picker and new finished skins remain separate work.

For the game export, run `sh tools/build_combat.sh` from the worktree root.
Dungeon derives the visual style from the equipped weapon in the state-service catalog. New runs start with a staff, sword or whip; the market also sells a greatsword and hand casting. Sparring follows the equipped Home armory weapon; its projected combat_style selects the animation. The Merchant sells campaign weapons and the outfit pieces; item effects and set bonuses are resolved by the state service. Weapons without authored styles use an explicitly labelled empty-handed placeholder. Weapon styles control animation; item effects and set bonuses are calculated separately. Legacy lantern and compass remain valid and use the sword fallback until they receive matching art. Non-Mimic dungeon enemy art remains static pending dedicated animated sprites.

The three outfit definitions each provide action and hurt sheets for all seven
weapon styles; sword also has its own idle and follow-through. The outfit
catalog uses the naming convention `tate-<outfit>-<style>[-hurt]-sheet.png`.
The export includes all resources so these dynamically loaded textures are
available in the browser. The sliced source concepts remain in `source-art/`;
scythe recovery cells use separately authored full-blade poses. Regenerate only
selected sheets with `python3 source-art/slice_animations.py <sheet names>`.

This covers the three new campaign outfits. Other armour still uses a palette
treatment, and weapons of the same style share weapon artwork. Home has its own
38px directional walk and idle sheets for the three outfits, generated from
`tools/home_art/sheets/hunter_outfits` by `python3 tools/home_art/build_hunter_outfits.py`.
The three new set trinkets have separate wearable sprites; other trinkets
remain equipped without a wearable sprite until their own art is available.

## Armour art backlog

Each equipped armour should ultimately have a recognisable design in both Home
and combat. Related tiers may share materials and motifs, but should visibly
progress in silhouette and detail. Until their own sheets are authored, the
classic sprite and palette families are temporary fallbacks. Maintain Tate's
identity and the game's Castlevania-inspired pixel art across the sets.

The current catalogues contain 46 distinct armour names, including the three
complete outfits above, Oracle Mantle, Patchwork Travel Coat, Pilgrim Leather and Wayfarer Brigandine. The remaining 39 are listed here so future work is
tracked per item rather than mistaking a shared palette for finished art:

- Lantern Vale progression: Lanternscale Vest, First Light Plate.
- Blackjack progression: Dealer's Waistcoat, Velvet Felt Jacket, Pit Boss Coat,
  Gilded Lapel Armour, The High Roller's Mail.
- Casino Slots progression: Doorman's Livery, Silver Sequin Vest, Auditor's
  Waistcoat, Vault Guard Plate, The Fortune Mail.
- Dungeon Crawler progression: Canvas Mining Smock, Riveted Leather, Deepvein
  Brigandine, Lamp-Lit Lamellar, The Core-Forged Plate.
- Legacy equipment: Apprentice Coat, Leather Guard, Runic Mail, Emberplate,
  Guardian Aegis, Mythril Archive Plate, Debugger Plate, Ledgerguard Coat,
  Emberweave Mantle.
- Infinite Dungeon: Ember Ward, Field Jacket, Syntax Cuirass, Lantern Coat,
  Pilgrim Ward, Diver’s Mail, Shellguard, Keeper Plate, Inkwoven Robe, Bullhide,
  Clockwork Mail, Hollow Carapace, Last Light Vest.

A completed armour needs directional Home walk and idle art and complete
weapon-specific combat idle, attack, recovery and hurt poses. Inspect grips,
clipping, proportions and motion in game before marking one complete. Oracle
Mantle, Patchwork Travel Coat, Pilgrim Leather and Wayfarer Brigandine have their own Home and
seven-style combat art. Their interactive previews are `oracle-preview.html`,
`patchwork-preview.html`, `pilgrim-preview.html` and `wayfarer-preview.html` in this directory.

## Held weapons

A weapon can be drawn onto a weapon-less hunter sheet, instead of being baked into every sheet. This is how each Quest Lab weapon gets its own look in combat.

The weapon is drawn into the base sheet once, in memory (`HELD.compose` in `held_weapon.gd`), so the hunter and the weapon are a single texture. It was first a second sprite kept in step with the body by a `RenderingServer.frame_pre_draw` hook; that worked on desktop but fell out of step in the web build, where the blade hung in the air mid-swing, and headless tests cannot see it. Never add a second sprite that has to mirror the body's frame.

- `art/held/base-<skin>-<style>-<idle|action|follow|hurt>-sheet.png`: the hunter sheet with the blade and crossguard removed. The glove and grip stay.
- `art/held/<item id>-<skin>-<style>-<sheet>.png`: that weapon only, same pixel size and cell layout as its base, transparent elsewhere. `HELD.apply` blends it into the base sheet (an `ImageTexture` named `<item id>-<skin>-<style>-<sheet>`, cached), so it animates, flips and tints with the hunter. Generators clip nothing: `draw_overlay(..., fit=True)` shrinks a raised weapon until it sits inside the 72px cell.
- `weaponId` reaches the arena from Sparring and campaign encounters (the equipped item id), Infinite Dungeon runs (the server adds `loadout.weapon_id`; `dungeon-x` ids use the `campaign-dungeon-x` strips) and online duels (`weaponId`, plus `rivalWeaponId` for the opponent, composed onto the rival's own sheet). The online raid boss fight uses a fixed loadout; `OnlineRaid` takes an optional `playerWeaponId` for the day its screen is mounted (nothing renders it in this branch), until then it keeps the baked sword.
- A held weapon is used only when the game sends `weaponId` (the item id), the skin and style have bases, and the weapon has a strip for every base sheet. Otherwise the baked sheet is used. Variants with their own baked art (`dawn-lantern`, `graveblade`) and bare hands never get one.
- Coverage today (all in `art/held/`):
  - `sword` (11 weapons) and `greatsword` (12): the whole weapon is redrawn, on all 12 outfits, by `source-art/held_weapons.py`. The generator detects the blade by colour, borrows Tate's geometry for the two pale outfits (Ivory, Merchant Oracle) with one hand-measured frame in `MANUAL_BLADE`, and the Gravebound Greatblade keeps its own baked variant.
  - `scythe` (5): a whole scythe, shaft and head, drawn separately on the hero's *sword* poses by `source-art/held_polearms.py`. The sword bases are already weapon-less, so the scythe is laid along each frame's blade axis exactly like a sword, with the hand partway along the shaft. The 96px sword cells are padded to the scythe's 128px cells. It replaced a head swap on the baked pole (the pole runs through the hands and could not be erased, so a blade sat on the wrong stick). A baked blade left in a sword base now shows as a second weapon under the scythe, so keep every outfit's sword base truly weapon-less (Norse's strike frames once were not: `MANUAL_BLADE` in `held_weapons.py`).
  - `staff` (6, spears included), all 12 outfits: only the head (point, crystal) is swapped on the baked pole, by `source-art/held_heads.py`. It still has the pole problem the scythe had.
  - `handmagic` (5): `source-art/held_hands.py` draws the focus, chakram, sceptre or tome small at the cast spark in the windup and strike frames; the item is conjured for the cast.
  - `whip` (3 of 4): `source-art/held_whips.py` keeps the baked lash and adds a small signature piece (rake comb, oathchain links and weight, barb) at the far tip of the strike frame, found as the right-most opaque pixel so no colour matching is needed. A lash has no rigid axis to redraw along, and recolouring it by colour does not hold across outfits (it hit cloth on Wardplate). The Hunter's Whip is the plain lash and keeps the baked art. Wardplate's lash is not stretched out far enough to find a tip, so its strip is empty and it shows the plain lash.
  - `oil` is not covered: the Oil of Doom is the one baked bottle that already is its own icon.
  - A weapon with a baked variant (Gravebound Greatblade, Dawn Lantern) uses that art on the outfits that have it (`_baked_variant` in `arena.gd` checks the variant sheets differ from the plain style's) and its overlay everywhere else. The Gravebound Greatblade has strips for all 13 outfit entries; the Dawn Lantern has no overlay strips yet.
  - Regenerate a style with `python3 source-art/held_weapons.py --style sword|greatsword`, `held_polearms.py` (scythes), `held_heads.py --style staff` or `held_hands.py`, then re-import, because Godot serves stale textures until `godot --headless --import` has run.
- `source-art/held_weapons.py` builds the bases by detecting the blade in each pose and erasing it, then bakes every sword-style weapon's strips from its 128px icon. It never overwrites a strip that exists: drop in a hand-made strip with the same file name for a hero weapon, or pass `--force --only <item id>` after an icon changes.
- Screenshot a pose with a weapon: `godot --path prototypes/godot-combat -- --shot=<absolute path inside the project> --pose=2 --weapon=bj-the-house-cutter --look=wardplate` (flatpak Godot cannot write outside the project).
- Test: `godot --headless --path prototypes/godot-combat --script res://tests/held_weapon_smoke.gd`.

- Look at the real thing after any change to the art or the arena: `godot --path prototypes/godot-combat --script res://tests/overlay_motion_probe.gd -- --style=scythe --weapon=hunter-sparring-scythe` plays a real attack in a window and saves frames to `res://shots/` (needs a display; the headless smoke tests cannot see rendering). In the web build, load `/combat/index.html?embed=1`, send payloads to `window.diddyCombatReceive(JSON.stringify({...}))` and take screenshots mid-swing.

## Recoloured armour looks

Every armour in the Home armory needs a look of its own, but only 13 outfits have bespoke combat sheets. The other
23 armours are **recolours**: the silhouette of the closest outfit with a different palette.

- `source-art/looks_data.py` is the table: each look id, its parent outfit and its colour-band rules. `python3 source-art/looks.py [--only id,id] [--sheet]` regenerates the combat sheets (`art/tate-<look>-<style>...-sheet.png`), the weapon-less bases (`art/held/base-<look>-...`) and the Market preview sheets, then writes `looks_registry.gd`. Run `godot --headless --path prototypes/godot-combat --import` afterwards. `--sheet` writes `shots/looks-preview.png` for review.
- The recolour works by colour band (`rot` rotates or sets a hue, `tint` gives colour to neutral cloth) so the painted shading survives. It never touches the hero's skin and hair (found by position from Tate's weapon-less sheets) and leaves a baked weapon's own pixels alone.
- `looks_registry.gd` maps each look to its parent. A look draws held weapons from the parent's strips (`HELD.strip_for`), composed onto the look's own base, so a weapon keeps its own colours. It has no baked Graveblade or Dawn Lantern sheets; the Gravebound Greatblade is held instead.
- `ide/frontend/src/hunterEquipment.js` (`ARMOUR_LOOKS`) maps each armour name to its look and to the outfit Home shows (Home only has art for the original outfits). `held_weapon_smoke.gd` checks every look, and `hunterEquipment.test.js` fails if two armours ever share a look.
- To add an armour: give it an effect (`docs/ARMOUR_IDENTITIES.md`), a row in `looks_data.py`, a row in `ARMOUR_LOOKS`, and an icon. To give a look truly new silhouettes, draw a bespoke outfit instead (the first sections of this file).
