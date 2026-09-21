# START HERE — Python Quest Lab

You are not here to speedrun Python. You are here to make the basics feel automatic.

## Start Quest Lab

From the repository root on Windows, run or double-click:

```powershell
.\start-questlab.cmd
```

That starts the guarded WSL backend and frontend and opens Forge in your
browser. From WSL, use the matching shortcut:

```bash
bash ./start-questlab.sh
```

The shortcuts keep the normal branch, canonical-state, dependency and stable
PTY checks. Add `-NoBrowser` when you want to open the printed URL yourself.
If you are intentionally working from an offline or locally ahead checkout,
add `-AllowStaleCheckout`; do not use that switch to hide an unexpected
checkout mismatch.

## Your current level

You already know the idea of loops, functions, lists and dictionaries, but recall is shaky. That means the right move is repetition through small projects, not piling advanced concepts on top.

For this campaign, your job is to get comfortable writing and debugging code from memory.

## How a session works

1. Open the interactive dashboard (`index.html` when hosted, or the deployed site).
2. Pick the project that sounds fun.
3. Switch to its branch.
4. Read that branch's `HANDOFF.md` before writing code.
5. Create the smallest working version first.
6. Run your program constantly.
7. Ask PYR for hints when stuck.
8. Commit meaningful milestones.
9. Beat the project's boss by finishing the required features and explaining your code.
10. Let PYR update your campaign progress honestly.

## Recommended order

The roadmap is designed to gradually increase the amount of state you need to manage:

`RPS → Blackjack → Detective → Creature Battle → Casino → Dungeon → Gladiator → Football Manager`

But fun matters. If you really want to build Pokémon-style combat tonight, do it. The roadmap is guidance, not homework.

## What you are allowed to use

Use Python itself, your terminal, a text editor/IDE, the standard library, documentation, and syntax searches.

Good searches:

- `python random choice list`
- `python dictionary get value`
- `python while loop syntax`
- `python sum list`

Avoid searches that hand you the architecture or finished answer:

- `python blackjack full code`
- `pokemon battle simulator github python`
- `dungeon crawler source code`

## AI rule

Tell any AI tutor:

> Read `TUTOR_CONTRACT.md`, the local `progress.json` cache (or synchronized state supplied by the local sync service after sign-in), and the current branch `HANDOFF.md`. Act as PYR. Use the Socratic hint ladder. Do not write the project for me.

The AI may explain concepts, ask questions, give pseudocode, review your code
and request campaign updates through the local state/sync service. It should
not become your implementation engine or write a cloud-authoritative snapshot.

## When to move on from fundamentals

You are ready for the next layer when you can build most of these without constantly checking how to write a loop/function/list/dictionary.

Then the next campaign can introduce:

- files and JSON
- exceptions
- modules
- classes / OOP
- testing
- APIs

Those will make much more sense once you have repeatedly felt the pain they solve.

## One-day vs multi-day projects

Finishing one project a day is cool when it happens. It is not the objective.

A clean 2–3 day build that you understand is better than eight one-night projects mostly written by an AI.

The win condition is simple: **you wrote it, you debugged it, and you can explain it.**
