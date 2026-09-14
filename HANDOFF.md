# Quest 01 — Blackjack

## Mission
Build a terminal Blackjack game without searching for a finished Blackjack implementation.

## Main skills
- lists
- functions
- loops
- conditionals
- totals and game state
- `random`

## Core requirements
- create a deck representation
- deal two cards to player and dealer
- show the player's hand and only one dealer card at first
- player can hit or stand
- dealer follows a simple automatic rule
- detect busts
- compare final totals and declare a winner
- support replaying multiple rounds

Keep the first version simple. You do not need betting, suits or perfect casino rules immediately.

## Mobs
1. **The Dealer's Hand** — generate and deal cards.
2. **The Bust Hound** — calculate totals and detect busts.
3. **The Hitman** — implement repeated hit/stand choices.
4. **The House Clerk** — make dealer turns work automatically.
5. **The Rematch Shade** — support another round cleanly.

## Boss — The House
Handle Aces sensibly enough that an Ace can become 1 instead of 11 when required to avoid an unnecessary bust.

Then explain to PYR:
- how a hand is represented;
- how you calculate its value;
- what controls the player's turn;
- what controls the dealer's turn;
- how you decide the final winner.

## Optional loot
- chips and betting
- win/loss stats for the current session
- Blackjack payout bonus
- ASCII cards
- difficulty options for dealer behaviour

## Constraint
Try to solve this with the fundamentals you already know before adding anything more advanced.

## PYR rule
Hints first. Exact solution code is a last resort and forfeits the clean-clear bonus for that challenge.
