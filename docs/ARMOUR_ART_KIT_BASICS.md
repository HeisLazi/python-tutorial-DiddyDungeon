# Basics Village armour art kit — 2026-11-13

> Status: the 36 images were generated and wired on 2026-11-13; see the status block in
> `docs/ARMOUR_ECHOES_PLAN.md`. This kit remains the template for the next region.

Phase 2 of `docs/ARMOUR_ECHOES_PLAN.md`: finished art for the two Basics armour echoes. The art
needs an image generator, which Claude does not have in this session. Everything else (slicing,
wiring, Godot registration, review, tests) can be done by Claude once the source images exist, so
this kit says exactly what to make.

## The two armours (culture-led, Lazi's direction 2026-11-13)

Each set is drawn from a different real tradition and mixed with fantasy. They are *inspired by*
those garments, not copies. Check the real construction before the final pass, per
`docs/ARMOUR_IDEAS.md`, and avoid flattening a region into one costume.

| | Lanternkeeper’s Coat | Wayfarer’s Wardplate |
|---|---|---|
| Run armour | Lantern Coat (uncommon, 18 reduction) | Pilgrim Ward (rare, 25 reduction) |
| Look id | `lanternkeeper` | `wardplate` |
| Inspired by | Japanese workwear: the indigo *noragi* work jacket with white *sashiko* geometric stitching, an *obi* sash, a woven straw *mino* rain cape over the shoulders, and a paper *chōchin* lantern. | East African pastoral dress: a red-and-blue checked *shuka* cloth worn as a cloak, wide circular beaded collars and bands in the Maasai tradition, with hardened hide ward panels. |
| Fantasy twist | The paper lantern holds a small living flame that lights the hem and sleeves amber. | The beadwork glows faintly in ward-sigil patterns where the hide panels meet. |
| Colours | Deep indigo, white stitching, straw gold, amber flame | Red and blue check, white and ochre beads, dark hide |
| Reads at sprite size | Straw-cape shoulders and a bright lantern at the hip | Wide bead collar and a checked cloak edge |

Both must stay clearly different from the existing Pilgrim Leather (green coat), Wayfarer
Brigandine and Patchwork coats. Note: the Pilgrim Ward shop icon is a plain blue coat
(`merchant/blue-coat` in `lanternItemArt.js`) and should be redrawn to match once the sprite exists.

## What each armour needs (18 images, 36 in total)

Same identity as Tate in every image: same face, build and foot baseline; only the outfit changes.
Use an existing finished outfit as the identity and layout reference
(`tools/home_art/sheets/hunter_outfits/pilgrim/` for Home and
`prototypes/godot-combat/source-art/tate-pilgrim-*-concept.png` for combat).

**Home (2 per armour), in `tools/home_art/sheets/hunter_outfits/<look>/`**
- `walk_source.png`, exactly 1536x1024: three rows (front, side, back) of four walk poses, columns
  split at x = 0, 440, 765, 1090, 1536 and rows at y = 0, 340, 660, 1024.
- `turnaround.png`, exactly 2172x724: front, side and back standing poses, split at x = 0-620,
  620-1030, 1030-1510. The build script refuses other sizes.

**Combat (16 per armour), in `prototypes/godot-combat/source-art/`, each 2172x724, four poses, facing
right, transparent background, weapon held in the art**
- Sword: `tate-<look>-sword-concept.png` (idle, windup, strike, recovery),
  `-sword-idle-concept.png`, `-sword-follow-concept.png`, `-sword-hurt-concept.png`.
- For `staff`, `whip`, `greatsword`, `handmagic`, `scythe`, `oil`: `tate-<look>-<style>-concept.png`
  (idle, windup, strike, recovery) and `tate-<look>-<style>-hurt-concept.png` (flinch, recoil,
  stagger, recovery). The staff and handmagic cast pose needs a clear hand or staff tip for the
  projectile start.

## Prompt template (paste with the reference image each time)

> Pixel-art game sprite sheet in a dark Castlevania-inspired style, the same character as the
> reference image (Tate: same face, curly hair, build and foot baseline), now wearing
> **{ARMOUR}**. Right-facing, transparent background, four poses in one row: {POSES}. Weapon: {WEAPON}.
> Keep face, proportions, feet baseline and weapon grip identical across the four poses and with the
> reference. No text, no ground shadow, no glow halo.

`{ARMOUR}` strings:
- **lanternkeeper:** "an indigo cotton Japanese-style work coat (noragi) with white sashiko
  geometric stitching, a wide obi sash, a woven straw rain cape over the shoulders, and a small paper
  lantern with a living amber flame hanging at the hip"
- **wardplate:** "a red-and-blue checked East African shuka cloth cloak over a dark hide ward vest,
  wide circular white-and-ochre beaded collar and arm bands, faintly glowing ward-sigil beadwork"

`{POSES}`: action sheets "idle, windup, strike, recovery"; hurt sheets "flinch, recoil, stagger,
recovery"; sword follow "four follow-through poses". `{WEAPON}`: sword, staff with blue crystal,
whip, greatsword, bare hands casting magic, scythe, or the giant oil bottle (match the reference sheets).
Home: use "front, side and back standing turnaround" and "walk cycle, four poses per facing".

Generate one sheet at a time, re-roll any where the grip, feet or outfit drift, and review at game
scale before sending.

## What Claude does once the images exist

1. Slice with `source-art/slice_animations.py` (add per-pose hip anchors per sheet) and check
   clipping, grip and foot alignment at render scale.
2. Run `tools/home_art/build_hunter_outfits.py` for the Home walk and idle strips (add both ids).
3. Register `lanternkeeper` and `wardplate` in `combat_catalog.gd`, `arena.gd` (skins, suffixes,
   look mapping) and `RpgViews.jsx` / `marketWeaponPreview.js` (preview art), and map the names in
   `hunterEquipment.js` (`lanternkeeper's coat` and `wayfarer's wardplate`).
4. Add preview pages like the existing `*-preview.html`, run the Godot animation and bridge smoke
   tests, rebuild the web export with `sh tools/build_combat.sh`, and add frontend look tests.

## Today’s fallback

Until the art exists, the Lanternkeeper’s Coat uses the generic ember look and the Wayfarer’s Wardplate
the steel look, both palette treatments of Tate’s classic sprite. That is playable but not distinct.
Nothing was changed for phase 2 in code.
