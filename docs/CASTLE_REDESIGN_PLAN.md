# Castle redesign direction

Status: design proposal, not implemented. The current playable Home is still the seven-room east–west chain. This plan preserves the unfinished Tutor rebuild as separate work.

## Goal

Make Home feel like a place with a legible floor plan, inspired by the spatial readability of Pokémon FireRed while retaining DiddyDungeon's gothic castle and Pyr. The map must describe the doors the player can actually walk through. Do not copy Pokémon's artwork or branding.

## Proposed ground floor

```text
       Gallery                 War Room ─── Pyr's Den
          │                        │
       Library ─── Great Hall ─── Hall of Arms
          │
        Pantry
```

- Great Hall remains the starting point and the Forge exit. Its hearth remains usable.
- Library and Hall of Arms flank the hall. The Gallery and Pantry branch north and south of the Library. The War Room branches north of the Hall of Arms; Pyr's Den connects to its east.
- The diagram describes room relationships and cardinal directions, not exact corridor lengths. Every connection must work in both directions and have a clearly visible entrance in both rooms.
- Preserve the existing station IDs, upgrade levels, upgrade ladders, save format, action handlers, Pyr following, and player-selected cosmetics. Rearranging rooms must not spend resources or reset progression.

## Visual direction

Use a consistent overhead RPG perspective for walls, floors, furniture, doors and the hunter. Maintain the castle's cool stone, warm firelight, crimson fabrics and gold accents. Scale the character and furniture together so the player can read more of the space at once. The existing 320×180 room viewport can be retained if the new art and collisions fit it; don't shrink only the character or zoom out over artwork that was designed for a different perspective.

The compact top-right map should be a small floor plan: room shapes, their connecting doors, an obvious current-room marker, and visually distinguishable directly connected rooms. Expand it for readable room names and destinations. It should never imply a connection that the actual level does not provide. Keep it keyboard accessible and avoid obscuring the active doorway or station prompt.

The hunter needs a coherent four-direction idle/walk set in the same scale and perspective as the new rooms. Use the existing Alucard-inspired identity, afro and dark skin as a starting point, and keep the home sprite free of the sword. Produce and inspect a turnaround and animation in context before replacing the current sheets. Do not assume existing combat sprites or weapon displays should change.

## Implementation order

1. Establish one authoritative floor-plan graph shared by the Godot build and the React map, including directional exits, destination spawn positions and room labels. Validate that every edge has a reciprocal edge and that all rooms are reachable. Keep station IDs and save data unchanged.
2. Prototype the Great Hall and Library in the chosen perspective with a working doorway and hunter turnaround. Test movement, collision, scale, legibility and Pyr in the actual browser before committing to the other rooms. Include at least one vertical doorway in the prototype.
3. Rebuild the remaining rooms around their stations and all existing upgrade stages. Check that each stage leaves doors and station interaction areas reachable. Use actual engine elements and preserve the existing lighting and motion where suitable.
4. Replace the existing linear HUD with the floor-plan map driven by the same graph. Verify its current-room marker and connected rooms after each transition. Make sure the expanded map works at narrow window sizes and can be dismissed with the keyboard.
5. Run the full room graph in the embedded web build with an isolated test save. Exercise all stations, upgrades, exits and return routes. Check base and maximum upgrade visuals, plus every intermediate upgrade for reachability. Verify reload, resize and focus behavior, and inspect screenshots in Chromium.

## Known constraints from the existing implementation

- `rooms.gd` builds 320×180 rooms from a shared shell with side-wall exits; its wall and floor blockers assume those exits. North/south transitions require new geometry, collision and spawn logic, not just a map change.
- The room builders place furniture, lighting and upgrade-dependent objects against the current walls. Each needs a deliberate new arrangement; a doorway cut through a wall or furniture is not sufficient.
- `home.gd` owns movement and broadcasts the current room to the parent; React owns game actions and save state. Keep that boundary.
- `homeDirectory.js` and the current map are arranged in a linear list. Replace that assumption when the level graph changes; retain the present truthful map until then.
- The current hunter uses three 48×46 sprite sheets with a mirrored side, 8 walking frames and 4 idle frames. A replacement needs equivalent directional coverage and matching foot anchors, and must work with Pyr's follower placement.
- The web export is generated and ignored; rebuild both the Godot export and frontend in the actual app checkout when the implementation is integrated.
