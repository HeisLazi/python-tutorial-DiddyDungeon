# Quest 06 — Turn-based Gladiator Game

## Mission
Build a terminal arena game where the player fights increasingly dangerous gladiators, earns rewards and chooses upgrades between fights.

## Main skills
- reusable functions
- dictionaries
- lists
- turn-based state
- progression
- simple balancing
- combining combat and economy systems

## Core requirements
- player has HP, attack and one secondary stat
- generate or choose opponents with different strengths
- player chooses between at least 3 combat actions
- opponents use simple behaviour rules
- wins reward coins or XP
- between fights, choose an upgrade or buy an item
- difficulty increases over a run
- losing ends the run

## Mobs
1. **Arena Recruit** — one full duel.
2. **Shield Bearer** — add defence or blocking.
3. **Bloodletter** — add a stronger/riskier attack.
4. **Bookmaker** — rewards and upgrades between fights.
5. **Veteran** — opponent variety and simple behaviour.
6. **Champion's Guard** — scaling difficulty.

## Boss — The Unbound
Create a final champion with a recognisable mechanic rather than merely huge HP. Examples: changing stance, healing once, countering a repeated move, or becoming stronger below half HP.

Then explain to PYR:
- how combat actions alter state;
- how enemy behaviour is chosen;
- how progression affects later fights;
- how the boss mechanic differs from normal opponents;
- which repeated behaviours you moved into functions and why.

## Optional loot
- weapons with trade-offs
- injuries
- temporary buffs
- arena rankings
- three-fight tournaments
- different gladiator archetypes

## PYR rule
Encourage Lazarus to design the combat rules on paper or in comments before coding complicated mechanics. Ask questions about state and turn order instead of giving the implementation.
