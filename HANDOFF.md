# Quest 07 — Mini Football Manager

## Mission
Build a terminal football manager simulator with a squad, simple transfers and match simulation. This is the largest fundamentals-only project in the campaign.

## Main skills
- lists of dictionaries
- larger state structures
- functions
- loops
- filtering/searching
- random simulation
- economy state
- planning before coding

## Core requirements
- create a squad of players with name, position, rating and value
- show the squad in a readable way
- track club budget
- create a transfer market
- buy a player if budget allows
- prevent invalid purchases
- choose a starting XI or simplified lineup
- simulate a match using team strength plus randomness
- track wins/draws/losses over several matches

Keep the simulation simple first. Do not try to recreate Football Manager.

## Mobs
1. **The Scout** — build player data and display it.
2. **The Accountant** — budget and transfer costs.
3. **The Negotiator** — buy a player and update both squad and market.
4. **The Tactician** — calculate a simple team strength.
5. **The Match Engine** — produce a believable result from strength + randomness.
6. **The Fixture Keeper** — run multiple matches and track results.

## Boss — The Invincibles
Build a short season or cup run where team changes matter. A stronger squad should generally perform better over time without guaranteeing every result.

Then explain to PYR:
- why players are represented the way they are;
- how transfers modify multiple pieces of state;
- how team strength is calculated;
- where randomness enters the match simulation;
- how results are tracked over time;
- what you would refactor if the program doubled in size.

## Optional loot
- injuries
- player form
- formations
- positions affecting team strength
- league table
- selling players
- youth prospects
- simple training upgrades

## Boss-clear bonus
This quest should make the pain of managing lots of dictionaries/lists obvious. After you finish and understand it, you are probably ready to start learning files/JSON and classes in the next campaign.

## PYR rule
Do not design the entire manager architecture for Lazarus. Help him split one feature at a time and keep the first match engine intentionally small.
