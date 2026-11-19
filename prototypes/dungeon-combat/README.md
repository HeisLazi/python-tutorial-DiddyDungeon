# Dungeon combat: sidebar prototype

This is a standalone, disposable visual prototype. It does not connect to the game, evaluate Python, or change save data. Select an answer and submit to see a correct or incorrect turn; switch the example weapon to see how it appears with the hunter. The compact arena replaces the `Your HP` card inside the existing left question sidebar, while the answer workspace remains on the right.

The arena and wraith were generated with the built-in image generation tool. The arena prompt requested an empty 1990s gothic castle crypt fighting-game background, with dark indigo stone, red drapes, warm torchlight, a flat foreground, no characters or UI. The final transparent wraith was regenerated from Lazi’s Castlevania references and the existing hunter sprite: a left-facing spectral knight, limited purple and charcoal palette, pale skull and teal eyes, deliberately chunky pixels; the source is retained alongside the 40-pixel prototype asset. Tate uses the project's existing Home hunter sheet; weapon overlays and all motion are temporary prototype artwork.

Future slice: port a simulated version to Tutor sparring, replacing the WHAT YOU’RE SPARRING panel; do this after the Infinite Dungeon combat implementation is approved.

The current crypt concept was generated using the actual Home screenshot and Home concept as references: it aims for the same stone palette and warm lighting, with a deeper side-view crypt and a clear fighting floor. The source and 320×180 preview are retained in `assets`. The earlier atlas-composed crypt, caves and archive are retained for comparison but are not presented as finished designs. Enemy sizes are illustrative and use the same placeholder wraith; real mobs and bosses should receive distinct original designs. None of this is connected to game state.

## Requested follow-on order

1. Implement approved combat inside the Infinite Dungeon question sidebar, driven by real verdicts, run HP, enemy Resolve, equipped weapon, floor and region. Use distinct original enemies, with silhouette and proportions inspired by the supplied Castlevania monster and boss reference sheets; size varies by creature. Select the arena backdrop from the actual map region/floor, not these demo controls.
2. After that, port a hollow/simulated version to sparring, replacing the `WHAT YOU’RE SPARRING` section without changing real Dungeon HP or rewards.
3. After sparring, redesign Tate specifically for combat and revisit the Dungeon classes: magic, sword and whip starts; consider a fourth class with a large two-handed sword. Show the actual class weapon in combat, give weapon types distinct attack visuals, and represent trinket/level boosts on the character. Class effects, balance and upgrade rules need design and playtesting; the current demo’s sword/spear/dagger switch is temporary and does not define the classes.
