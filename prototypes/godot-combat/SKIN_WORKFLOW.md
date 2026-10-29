# Combat skin workflow

This prototype separates shared combat styles/timings from each hunter's sprite sheets in `combat_catalog.gd`. Tate is the only shipped skin; registering a skin does not create artwork. The existing sheets include the weapon in each pose, so every new skin needs its own weapon-specific art, rather than attaching an arbitrary weapon to Tate's arm.

1. Prepare right-facing, transparent sprite sheets for `sword`, `staff`, `whip`, `greatsword`, and `handmagic`. Each sheet has exactly four equal horizontal cells, 72 pixels high. A style's sheets must have the same cell width and align its feet consistently. The sprite offset positions the foot anchor; Tate uses `(13, 0)` for 96px sword cells and `(19, 0)` for 128px cells. Tune the offset to the new art.
2. Supply `action` and `hurt` textures and an `offset` for each style. The staff and handmagic styles also require `cast_origin`, a `Vector2` relative to the hunter root where the projectile begins (Tate uses `(42, -52)`). Align it with the hand or staff tip in the casting pose. Action poses 0–3 are idle, windup, strike, recovery; hurt poses 0–3 are flinch, recoil, stagger, recovery. Sword additionally uses an `idle` sheet and a `follow` sheet (poses 0–3 are the follow-through). `idle_frames` is an optional nonempty list of frame indices 0–3; without it the first pose bobs. Supply an `idle` texture for any style if its idle frames live elsewhere.
3. Create a skin dictionary shaped like `tate()` in `combat_catalog.gd`, with a unique `id`, display `name`, and `styles` keyed by style IDs. Load/import all textures and call `register_skin(skin)`, then `select_skin(id)` when no turn is running. Registration rejects missing styles, missing textures, mismatched sheet sizes, and invalid idle frames, so unsupported combinations cannot silently use another character's art. The preview currently has no skin-picker UI or live-game integration.
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

Load that definition from the scene or a future skin picker, check `register_skin(preload("res://skins/aria.gd").definition())`, and then call `select_skin("aria")`. Adjust offsets and origins to the new art; these example values are Tate's, not universal measurements.

## Verification and current scope

The 2026-10-29 checks cover all five Tate styles, attack/hurt texture selection
with a second test skin, selection before scene startup, custom casting origins,
incomplete skin rejection, and both environment modes. Chromium checks cover
the simulated arena, restored dungeon lighting, hit and miss. The second skin
is a test fixture, not an additional finished character.

Build the browser preview from the worktree root:

```sh
godot --headless --path prototypes/godot-combat --import
godot --headless --path prototypes/godot-combat --script res://tests/animation_smoke.gd
godot --headless --path prototypes/godot-combat --export-release Web ../godot-combat-web/index.html
```

The local preview server uses port 17532. The simulation backdrop belongs to
sparring; the crypt, torches and amber lighting belong to dungeon mode. Live
game integration and a player-facing skin picker remain separate work.
