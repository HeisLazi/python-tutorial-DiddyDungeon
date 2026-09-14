# Quest 05 — Dungeon Crawler + RPG Shop

## Mission
Build a terminal dungeon crawler where each room can become a fight, reward, shop or event. This is where the smaller systems start connecting.

## Main skills
- functions
- lists and dictionaries
- loops
- random encounters
- inventory state
- economy state
- combining multiple systems

## Core requirements
- player has HP, attack, gold and potions
- generate enemies with different stats
- player can attack, heal or try to run
- enemies act after the player's turn when appropriate
- victories award gold
- rooms/floors increase as the run continues
- every few rooms, enter a shop
- shop can sell at least potions and one permanent upgrade
- every 5 rooms, fight a boss
- death ends the run and prints a final score

## Shop requirement
The text-based RPG shop belongs inside this project rather than being a separate branch. It should feel like a real subsystem:

- show items and prices
- verify the player can afford a purchase
- update gold
- update player/inventory state
- let the player leave without buying

## Mobs
1. **Tunnel Rat** — make one enemy fight work.
2. **Potion Leech** — healing and inventory quantities.
3. **Gold Goblin** — rewards after victory.
4. **Merchant Shade** — build the shop loop.
5. **Floor Stalker** — random rooms and progression.
6. **Mini-Boss** — tougher encounter every few rooms.

## Boss — The Dungeon Core
Reach a complete playable loop of:

`room → encounter → reward → shop/progression → boss → continue/death`

Then explain to PYR:
- how player state survives across rooms;
- how enemies are generated;
- how inventory changes;
- how the shop modifies the same player state;
- how the game decides when a boss appears.

## Optional loot
- weapons
- armour
- rare shop inventory
- treasure rooms
- enemy abilities
- difficulty scaling
- score / best run

## Constraint
Do not redesign this into a giant RPG. Finish the terminal loop first.

## PYR rule
When the code gets messy, help Lazarus identify repeated behaviour that might deserve a function. Do not prematurely introduce classes.
