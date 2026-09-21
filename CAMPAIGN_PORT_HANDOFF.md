# Campaign prototype port handoff

Updated: 2026-09-21  
Branch: `feature/cloud-sync-desktop`  
Remote: `origin/feature/cloud-sync-desktop`

## Read this first

The latest prototype-to-canonical work is **not** a complete campaign port.
The only newly ported campaign prototype surface is **Home / Homestead**.
Market and the merged Forge + Market + Homestead workspace are still next
work. Do not describe the current branch as having the new campaign Market.

## Current checkpoints

- `cbf732c` — `port Home prototype into Forge`
- `85f6b5d` — `fix(home): restore prototype palette tokens` (latest; pushed)

The second commit fixes a visible regression: the Home port used prototype
palette variables (`--violet`, `--gold-soft`, `--panel-soft`, and
`--line-strong`) that canonical Forge did not define. Pyr's DOM node existed,
but its background computed as transparent. Those tokens now live on the
scoped `.homestead-v2` root, matching the prototype palette. Restarting the
managed launcher and checking the canonical Home route showed a visible purple
Pyr sprite.

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

### Existing but not part of this port

- Forge remains the existing editor/terminal surface;
- Tutor Notebook and Codex are earlier canonical work;
- Infinite Dungeon is an earlier separate route and has its own run-only
  market;
- the existing campaign/Bounty Office shell remains separate from Home.

### Not ported yet

- the campaign Market prototype and merchant intro;
- the shared campaign workspace where Forge, Market, and Homestead feel like
  one area;
- Village and its later NPC/grid work.

Do not confuse Infinite Dungeon's run market with the campaign Market. They
use different state boundaries and should not be merged accidentally.

## Truth sources

1. Visual parity: `prototypes/campaign-v1/` (currently the Home prototype at
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
- frontend production Vite build: passed (1,347 modules at the port
  checkpoint);
- desktop visual comparison: prototype and canonical Home inspected with
  browser screenshots;
- canonical Pyr diagnosis: DOM node existed, computed background was
  transparent before `85f6b5d`, then `rgb(189, 143, 215)` after restart;
- canonical Armory action: verified it scrolls to the live loadout;
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

Port the campaign Market prototype, then merge the navigation/state shell so
Forge, Market, and Homestead read as one campaign workspace without remounting
the editor or either PTY.

Before coding that slice:

1. inspect the Market prototype and record its visual/interaction contract;
2. decide the shared shell boundary (route switcher versus one composite
   workspace) from the existing UI, not from a new redesign;
3. keep campaign Market inventory separate from Infinite Dungeon run loot;
4. wire purchases through the canonical state service;
5. run a hostile visual review with Copilot and, when the Claude CLI schema is
   fixed, Claude as the secondary reviewer;
6. screenshot the prototype and canonical Market after every meaningful UI
   adjustment;
7. commit and push in small reviewable checkpoints.

Suggested next commit sequence:

1. `feat(market): port campaign merchant presentation`
2. `feat(campaign): merge forge market and homestead navigation`
3. `test(campaign): certify shared state and route persistence`

## Handoff prompt for the next agent

> Read `CAMPAIGN_PORT_HANDOFF.md`,
> `prototypes/campaign-v1/HOME_PORT_SOURCE_OF_TRUTH.md`, and the current
> `git status` first. Preserve all intentionally dirty player/challenge
> files. The Home port is complete through `85f6b5d`; verify Pyr visually if
> needed, then work only on the campaign Market port. Do not claim the Market
> or merged Forge/Market/Home shell is complete until the prototype and
> canonical screenshots match and the state/action tests pass. Commit and
> push each coherent slice separately.

