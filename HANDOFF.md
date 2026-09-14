# Quest 02 — Guess Who / Detective Game

## Mission
Build a terminal detective game where the player identifies a suspect by asking questions and narrowing a list of people.

## Main skills
- dictionaries
- lists of dictionaries
- loops
- conditionals
- filtering data
- functions
- strings

## Core requirements
- create several suspects as dictionaries
- give each suspect multiple traits
- let the player ask from a set of questions
- filter possible suspects after each answer
- show how many suspects remain
- let the player make a final accusation
- win if the accusation is correct
- lose after too many wrong guesses/questions

## Mobs
1. **The Lineup** — build suspect data.
2. **The Interrogator** — ask and process one useful question.
3. **The Vanishing Crowd** — filter suspects correctly.
4. **The False Lead** — handle questions that eliminate nobody or everybody.
5. **The Accuser** — implement the final guess.

## Boss — The False Alibi
Randomly choose the culprit at the start and make the full investigation playable without revealing them.

Then explain to PYR:
- why a list of dictionaries fits the problem;
- how your filtering works;
- how the culprit is stored;
- how the game knows when the player wins or loses.

## Optional loot
- clues that cost coins/questions
- difficulty levels with more suspects
- suspect biographies
- limited interrogation turns
- a murder-mystery skin instead of classic Guess Who

## PYR rule
Do not hand Lazarus a filtering solution immediately. Ask him what information he has before and after a question, then help him reason toward the transformation.
