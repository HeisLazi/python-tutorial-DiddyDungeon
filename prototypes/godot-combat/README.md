# Godot sword combat study

Standalone Godot 4.7 scene for evaluating a combat sprite of Tate holding a
sword. It is a visual study; it has no connection to the app or save data.

- **HIT** plays four whole-character sword poses, including the hand and blade.
  **MISS** shows a counterattack. **MODE** switches between a blue projected
  sparring hollow and a solid Dungeon mimic. **RESET** restores demo bars.
- The v2 sheet restores Tate's dark skin, short natural black hair, black and
  gold outfit and white cravat using the Home turnaround as reference.
  `source-art/tate-sword-v2-concept.png` is the generated source;
  `source-art/slice_sword.py` separates and reorders its silhouettes into four
  96×72 cells with a shared baseline. `source-art/tate-sword-v2-sheet.aseprite`
  is the editable LibreSprite sheet. The earlier concept remains for history.
- The character uses complete poses, not a procedural weapon overlay. Four
  frames are still an animation study: further in-between work, a proper
  recovery, and hand-polishing are needed. Magic, whip and greatsword need their
  own complete poses before the combat scene can replace the live version.
- The backdrop, Godot lights, projected grid and actors are separate scene
  elements. The hollow shader applies to Sparring only.

To build the disposable web preview, create `../godot-combat-web`, run
`godot --headless --path prototypes/godot-combat --import`, then
`godot --headless --path prototypes/godot-combat --export-release Web ../godot-combat-web/index.html`.
Serve the export over HTTP. Never use a real save for this prototype.
