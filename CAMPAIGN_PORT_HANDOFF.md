# Campaign prototype port handoff

Updated: 2026-09-21  
Branch: `feature/cloud-sync-desktop`  
Remote: `origin/feature/cloud-sync-desktop`

## Read this first

The prototype-to-canonical work now has a merged **Campaign** surface. It
replaces the separate top-level Forge, Character, and Homestead destinations
with one campaign workspace containing the Home, Market, and Bounty Office
points of interest. Forge remains available as the internal coding screen
opened from a selected bounty; it is no longer a top-level campaign tab.

## Current checkpoints

- `3c93e02` — `feat(campaign): port merged map home market office surface`
- `51bf0c1` — `fix(campaign): keep merchant sprite frames bounded`
- `3b26ce3` — `fix(campaign): show merchant frame on first paint` (latest;
  pushed)
- `bb13076` — `fix(campaign): redirect legacy home routes` (latest; pushed)

The merchant fixes preserve the prototype's bounded 24x32 pixel frames and
make the first frame visible immediately. The previous animation began with
all frames hidden, which made the live Market scene look like an empty counter.
The Home palette/Pyr repair from `85f6b5d` remains part of the port history.

## What is canonical now

### Home / Homestead (ported)

The canonical route is `activeView === 'homestead'` in
`ide/frontend/src/RpgViews.jsx`. It includes:

- the top-down room shell and selectable stations from the prototype;
- Hearth, Armory, Pantry, Study, Pyr's perch, and the room-upgrade niche;
- five authored room upgrades and four achievement plaques;
- live Armor / Trinket loadout projection;
- state-backed recover, bandage, meal, feed-Pyr, train-Pyr, token, purchase,
  equip, and room-upgrade actions;
- authored Pyr stages, bond meter, energy, and training disclaimer;
- Armory's `Browse loadout` action scrolling to the live loadout instead of
  being a dead navigation action.

Source files:

- `ide/frontend/src/RpgViews.jsx` — Home view and actions;
- `ide/frontend/src/homestead.css` — scoped Home room styling and palette;
- `ide/server/state.py` — canonical Home state/actions/catalog;
- `ide/server/app_v2.py` — Home action endpoints;
- `prototypes/campaign-v1/HOME_PORT_SOURCE_OF_TRUTH.md` — visual and behavior
  contract; treat the prototype as visual authority and state service as
  gameplay authority.

### Campaign workspace (ported)

The canonical `activeView === 'hub'` route is now `CampaignSurface` in
`ide/frontend/src/RpgViews.jsx`. It owns:

- the collapsible project-map rail;
- Home / Homestead, including the existing state-backed stations and Pyr;
- the prototype-style Market merchant intro and browse-lots screen;
- the prototype-style Bounty Office poster board;
- an internal Study-this-work handoff into the existing Forge editor.

The visible top navigation now exposes Campaign, Tutor Notebook, Infinite
Dungeon, and Settings. Character and Homestead are not separate destinations.
Infinite Dungeon remains a separate run mode and its run-only market is not
merged into Campaign Market. Village and later NPC/grid work are still future
work.

Do not confuse Infinite Dungeon's run market with the campaign Market. They
use different state boundaries and should not be merged accidentally.

## Truth sources

1. Visual parity: `prototypes/campaign-v1/` (Home/Market/Office prototype at
   `http://127.0.0.1:5207/?home-upgrades-v1=20260921b` when its prototype
   server is running).
2. Canonical state and rewards: `ide/server/state.py` and its validated API.
3. Canonical screen wiring: `ide/frontend/src/RpgViews.jsx` and
   `ide/frontend/src/AppV2.jsx`.
4. Port contract: `prototypes/campaign-v1/HOME_PORT_SOURCE_OF_TRUTH.md`.

When prototype and canonical behavior disagree, preserve the prototype's
visual language but use the state service for mutations, rewards, HP, coins,
equipment, Pyr progression, and achievement predicates.

## Resume commands

From this checkout:

```bash
git switch feature/cloud-sync-desktop
git pull --ff-only origin feature/cloud-sync-desktop
./start-questlab.ps1 -NoBrowser
```

Linux/WSL:

```bash
git switch feature/cloud-sync-desktop
git pull --ff-only origin feature/cloud-sync-desktop
./tools/questlab-launch.sh --no-browser
```

Use the Local URL printed by the launcher. The launcher may move from the
requested default port when another Forge/Vite process is already running.

For the visual prototype:

```bash
./tools/campaign-v1-prototype.sh
```

## Verification already completed

- prototype state tests: 18/18;
- backend state tests: 49/49 on the relevant WSL suite;
- frontend production Vite build: passed (1,349 modules after the merged
  Campaign surface);
- desktop visual comparison: prototype and canonical Home inspected with
  browser screenshots;
- canonical Pyr diagnosis: DOM node existed, computed background was
  transparent before `85f6b5d`, then `rgb(189, 143, 215)` after restart;
- canonical Armory action: verified it scrolls to the live loadout;
- merged Campaign desktop screenshots: verified Market merchant visibility,
  Market lots, Home/Pyr DOM presence, Bounty Office posters, and the internal
  Study-this-work handoff into Forge;
- merchant sprite runtime check: bounded 24x32 frames rendered without an
  exception; first frame computed visible after launcher restart;
- two hostile Copilot review passes completed before the final token fix;
- Claude prototype design gate passed. Claude's canonical CLI review was not
  completed because the CLI environment exposed a malformed tool schema;
  do not claim a successful Claude canonical review.

Always do another visual check after a UI edit, at the desktop viewport used
for this PC-only surface. Do not use mobile screenshots as acceptance evidence
unless the user explicitly asks for responsive work.

## Working-tree safety

At handoff time these paths are intentionally local/uncommitted and must be
preserved:

- `progress.json` (player state);
- `blackjack.py`, `dungeon.py`, and `tutor.py` (challenge files);
- `prototypes/codex-resource/`;
- `prototypes/infinite-dungeon/`;
- `tools/infinite-dungeon-prototype.sh`;
- the existing oddly named Unicode directory.

Do not reset, clean, or commit those paths unless the user explicitly asks.
Stage only the files belonging to the current slice. Make a small commit
after each coherent repair, push it, then record the commit here or in the
roadmap before starting the next slice.

## Next implementation slice

The visual port is intentionally ahead of full campaign coherence. The next
bounded slice is to connect Market purchases/equipment to the canonical state
service and certify route persistence without changing the prototype layout.
Keep Campaign Market inventory separate from Infinite Dungeon run loot. Then
add any deeper Home/Market/Village progression as its own small, reviewable
slice.

## Handoff prompt for the next agent

> Read `CAMPAIGN_PORT_HANDOFF.md`, the prototype source-of-truth files, and
> the current `git status` first. Preserve all intentionally dirty
> player/challenge files. The merged Campaign visual port is complete through
> `bb13076`: Campaign replaces the separate Forge/Character/Homestead
> destinations, while Study-this-work opens the internal Forge editor. Do not
> redesign the surface while wiring state. Commit and push each coherent slice
> separately, and perform a desktop screenshot check after each UI change.
