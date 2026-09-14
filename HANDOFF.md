# Quest 03 — Creature Battle Simulator

## Mission
Build a Pokémon-style turn-based battle game using dictionaries and lists before touching classes.

## Main skills
- nested dictionaries
- lists of dictionaries
- functions
- loops
- turn order
- state changes
- `random`

## Core requirements
- create at least 3 creatures
- each creature has name, HP and basic stats
- each creature has multiple moves
- each move has at least damage and accuracy
- player chooses a move each turn
- enemy chooses a move automatically
- misses are possible
- HP updates after attacks
- battle ends when one creature reaches 0 HP
- display readable battle text and remaining HP

## Suggested data shape
Think in terms of a creature dictionary that contains a list of move dictionaries. Work out the exact structure yourself.

## Mobs
1. **Wild Slime** — create one creature and one move.
2. **Feral Fang** — get one full attack to work.
3. **Miss Wisp** — add accuracy/random chance.
4. **Turn Goblin** — make both sides take repeated turns.
5. **Move Keeper** — let the player choose among multiple moves.
6. **Health Reaper** — end the fight correctly at 0 HP.

## Boss — The Arena Champion
Add a small team or roster choice before battle. The player chooses one creature and fights an enemy creature selected from the roster.

Then explain to PYR:
- how a creature is represented;
- how moves are stored;
- how your attack function changes state;
- what controls the battle loop;
- how you avoid negative/invalid HP behaviour.

## Optional loot
- healing move or potion
- status effects
- speed deciding who attacks first
- elemental strengths/weaknesses
- critical hits
- XP after victory

## Constraint
Do not use classes yet. This quest exists partly to let you feel the limits of dictionaries first.

## PYR rule
If Lazarus asks how to model a creature, ask him what information one creature needs and help him design the dictionary from that list. Do not dump a completed combat engine.
