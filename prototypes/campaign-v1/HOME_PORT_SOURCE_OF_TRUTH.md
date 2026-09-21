# Campaign Home · Port source of truth

This prototype is the visual and interaction authority for the Home/Homestead
port into Forge. The canonical app may supply different progression data, but
it must preserve this composition and interaction model before adding new
surface area.

## Capture

- Prototype route: `http://127.0.0.1:5207/?home-upgrades-v1=20260921b`
- Desktop only. Compare at the same desktop viewport as Forge; do not use a
  mobile breakpoint as the acceptance view.
- The Home screen is a genuinely top-down room. It is not a straight-on stage
  or static PNG:
  every station is a selectable DOM control and the upgrade drawer is a real
  stateful panel.

## Required landmarks

1. Heading: `HOME · HOMESTEAD`, `Your homestead.` and the recovery/preparation
   sentence.
2. A large modular room scene with a continuous shell, visible floor boundary,
   woven rug, clear door, window, shelf, chest/armory, plant, pantry, hearth,
   study desk, and Pyr at the lower middle behind the room activity lane.
3. Five selectable hotspots: Hearth, Armory, Pantry, Study desk, Pyr's perch.
4. A `ROOM UPGRADES` niche in the room. Opening it reveals five upgrade cards
   and four achievement plaques without replacing or hiding the room.
5. Upgrade card order and copy are authored in
   `prototypes/campaign-v1/src/campaignState.js` (`ROOM_UPGRADES`).
6. Plaque order and copy are authored in the same file (`HOME_ACHIEVEMENTS`).
7. Status strip and Armor/trinket loadout remain below the room; the room is
   the visual focus, not a short banner.

## Interaction acceptance

- Clicking a hotspot changes the context card without navigating away.
- Clicking `ROOM UPGRADES` toggles the drawer and preserves the room above it.
- A build button consumes the authored token cost exactly once, changes to
  `BUILT · ACTIVE`, and updates the status strip.
- A locked achievement renders as `HIDDEN PLAQUE`; unlocked plaques are
  read-only proof of play.
- Hearth `Recover fully` and `Eat a meal`, Pantry `Use bandage` and `Eat a
  meal`, and Pyr `Feed Pyr` and `Train with Pyr` are real state actions. They
  remain disabled only when their authored resource/HP precondition is false.
- Pyr is projected from the authored stage table: Tiny Code-Flame at bond 0,
  Emberling at bond 3, and Flarekin at bond 6. The context card shows the next
  threshold, bond bar, training energy, and companion-milestone disclaimer.
- `Browse loadout` must reach the live loadout section (or a real equipment
  destination); a button that merely reselects Home is a parity bug.
- The prototype's room and drawer are the reference when comparing the Forge
  port. Any deviation is a parity bug, not a redesign opportunity.

## Visual rules

- Forge-inspired charcoal, moss, ember-gold and violet accents.
- Scene shell must read as a room: top and side walls, a distinct floor plane,
  grounded props, high-contrast door, and a rug with visible weave/fringe.
- Keep labels readable at the desktop capture size. Do not substitute tiny
  microcopy for the primary interaction affordances.
- Keep the room upgrade drawer width, card order, and plaque grouping aligned
  with the prototype before changing copy or adding more upgrades.

## Parity checklist

- [x] Same heading hierarchy and desktop spacing.
- [x] Same room landmarks and station positions.
- [x] Same five upgrade cards, costs, effects, and order.
- [x] Same four achievement plaques and locked/unlocked treatment.
- [x] Same drawer open/close behavior.
- [x] Same status/loadout placement below the room.
- [x] Claude hostile critique has no BLOCKER/HIGH parity findings for the
  prototype review; the later canonical CLI pass was attempted but blocked by
  a malformed global tool schema.
- [x] Copilot read-only review completed; its high-severity interaction and
  plaque findings were repaired, with remaining compatibility notes addressed
  by the authored projections above.

## Port verification contract · 2026-09-21

The prototype remains the visual authority; the Forge shell, navigation, and
canonical state service remain authoritative for the live game. The port keeps
the room DOM/CSS composition and adds a bounded bridge for Home actions:

| Prototype behavior | Forge projection/action |
|---|---|
| Hearth recovery | `POST /api/homestead/action` with `recover` |
| Hearth meal | `meal` with the authored meal-heal delta |
| Pantry bandage | `bandage` with HP/resource preconditions |
| Pyr feed/train | `feed_pyr` / `train_pyr` with bond, energy, and stage evolution |
| Room upgrades | `homestead_room_upgrade` with exact token costs and one-time ownership |
| Plaques | Authored contract/mob predicates; aggregate counters are legacy fallback only when no structured evidence exists |
| Armory browse | Scrolls to the live `Armor and trinkets` loadout section |

Canonical sync may not yet expose every prototype field (for example legacy
companion energy), so the frontend uses bounded defaults while the backend
action bridge persists values. No action writes `progress.json` directly from
the browser, and the port does not alter the challenge file or campaign answer
contract.

Review record: desktop CUA comparison at the prototype and Forge Home routes;
prototype tests 18/18; canonical state tests 49/49; frontend Vite production
build passed. The working tree was published to the shared branch without
`progress.json` or disposable challenge files.
