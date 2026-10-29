# Godot combat scene prototype

Standalone 320×180 Godot 4.7 scene for evaluating a combat-specific Tate, an
articulated arm with weapon attachment, and a simulated sparring environment.
It is not connected to the app, a real encounter, or save data.

- **HIT / MISS** play an illustrative attack or retaliation and update demo bars.
- **WEAPON** cycles sword, magic staff, whip and greatsword; each has a different
  rigged action. **MODE** switches between a blue projected sparring hollow and
  a solid Dungeon mimic. **RESET** restores the demo bars.
- The background, torch sprites, Godot lights, projected grid, characters and
  arm are separate scene elements. The hollow shader affects Sparring only.
- Tate is an original image-generated combat concept using the supplied style
  reference. His body currently uses one idle frame with a procedural arm; this
  is a rig prototype, not a finished set of hand-drawn attack frames. Weapon
  art, two-handed poses, hit timing, accessibility and game integration need
  further design before this replaces the live combat scene.

To build the disposable web preview, create `../godot-combat-web`, run
`godot --headless --path prototypes/godot-combat --import`, then
`godot --headless --path prototypes/godot-combat --export-release Web ../godot-combat-web/index.html`.
Serve the export over HTTP. Never use a real save for this prototype.
