# Godot combat animation study

Standalone Godot 4.7 scene for evaluating Tate's sword combat and the two
prototype opponents. It has no connection to the application or save data.

- **HIT** plays Tate's sword attack and the enemy's recoil. **MISS** plays the
  enemy attack and Tate's recoil. **MODE** switches between a blue projected
  sparring hollow and a solid Dungeon mimic. **RESET** restores demo bars.
- Tate, the hollow and the mimic each use complete sprite poses for idle,
  attacking and taking a hit. Tate's attack combines the wind-up sheet and a
  follow-through sheet; idle frames cannot interrupt an active turn. The
  character retains Tate's dark skin, textured black hair and black-and-gold
  Home outfit. The blue shader applies only to the sparring hollow.
- `source-art/` holds the generated concepts and reproducible slicing scripts.
  The sources were guided by the user's references and the project's existing
  character art. Each runtime sheet uses four 96×72 cells. The v2 Tate sheet
  also has an editable LibreSprite document.
- This is still an animation study. Frame-to-frame polish, additional enemies,
  magic, whip and greatsword poses, and integration into the real game remain.

To build the disposable web preview, create `../godot-combat-web`, run
`godot --headless --path prototypes/godot-combat --import`, then
`godot --headless --path prototypes/godot-combat --export-release Web ../godot-combat-web/index.html`.
Serve the export over HTTP. Never use a real save for this prototype.

Run the state-transition smoke check with
`godot --headless --path prototypes/godot-combat --script res://tests/animation_smoke.gd`.
