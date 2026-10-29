# Godot sword combat study

Standalone Godot 4.7 scene for evaluating a redesigned Tate and a sword held in
his hand. It is a visual study; it has no connection to the app or save data.

- **HIT** plays three whole-character sword poses, including the hand and blade.
  **MISS** shows a counterattack. **MODE** switches between a blue projected
  sparring hollow and a solid Dungeon mimic. **RESET** restores demo bars.
- `source-art/tate-sword-concept.png` contains the original generated concept,
  guided by the supplied Alucard and character references. The fourth pose is
  not used because its sword faces backward. `source-art/slice_sword.py` uses
  the first three connected silhouettes to produce the consistent 96×72 cell
  sheet. `source-art/tate-sword-sheet.aseprite` is an editable LibreSprite sheet.
- The character uses complete poses, not a separate procedural weapon overlay.
  Three frames are a rough animation study; in-between drawings and polish are
  still needed. Magic, whip and greatsword are not included in this revision;
  they need their own complete poses rather than the previous crude rig.
- The backdrop, Godot lights, projected grid and actors are scene elements. The
  hollow shader applies to Sparring only.

To build the disposable web preview, create `../godot-combat-web`, run
`godot --headless --path prototypes/godot-combat --import`, then
`godot --headless --path prototypes/godot-combat --export-release Web ../godot-combat-web/index.html`.
Serve the export over HTTP. Never use a real save for this prototype.
