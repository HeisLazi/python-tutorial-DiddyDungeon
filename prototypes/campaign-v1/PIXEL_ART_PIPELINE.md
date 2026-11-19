# Campaign v1 pixel-art pipeline

The prototype does not treat a generated PNG as the character. The Merchant currently renders from two tiny frame arrays in `src/pixelArt.js`. That keeps palette, collision footprint, movement, equipment swaps, and idle animation independent from the market layout.

The browser bridge is deliberately code-native for this slice: each frame is a strict 24x32 palette grid rendered as crisp DOM cells, with CSS frame timing for idle animation. That gives us a fast review loop today and leaves room to swap in exported frames later without changing the scene, nameplate, lore gate, or interaction hotspots.

## Recommended authoring tool

Use [Pixelorama](https://pixelorama.org/) as the default free/open-source authoring tool. Its animation workflow supports frame-by-frame drawing, onion skinning, frame tags, and spritesheet export. Keep the editable project file, not only the exported PNG.

If we choose a paid production tool later, [Aseprite](https://www.aseprite.org/docs/sprite-sheet/) is the cleanest pipeline: keep the `.aseprite` source, tag animations (`idle`, `walk`, `talk`, `trade`), and export a nearest-neighbour sheet plus JSON atlas. Its CLI can export both sheet and data files for repeatable builds.

## Import contract

1. Draw on a fixed logical canvas (the current Merchant contract is 24x32; use 32x48 only when a larger silhouette genuinely needs it).
2. Keep every frame the same canvas size and anchor point.
3. Export transparent RGBA, nearest-neighbour, with no baked background or UI.
4. Put the sheet/atlas and metadata under the prototype asset folder; the UI consumes animation names, never hard-coded frame coordinates.
5. Validate frame dimensions, alpha, and a small palette before wiring a new character into Home or Market.

## Import checklist for the next slice

- Author `idle`, `blink`, `talk`, and `trade` tags in Pixelorama (or Aseprite).
- Export only transparent frame data; never bake the counter, lantern, nameplate, or scene background into the character.
- Convert the exported frames into the same palette-grid contract, or add a small importer that reads the tagged sheet/atlas and emits frame metadata for `pixelArt.js`.
- Review the result in the prototype at 100% and a narrow viewport before moving the asset into Forge.

This lets us replace the current hand-authored Merchant frames with tool-authored frames without changing the market screen, lore gate, or movement/animation hooks.
