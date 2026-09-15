# Infinite Dungeon and Practice Mode

Status: approved product direction, local state foundation next.

## Modes

Quest Lab has three separate learning surfaces:

| Mode | State boundary | Purpose |
| --- | --- | --- |
| Campaign | Existing canonical campaign state | Permanent Blackjack progression, equipment, Codex, normal encounters and the collaborative `tutor.py` notebook. Tutor is a dedicated Campaign surface, not a normal project file. |
| Infinite Dungeon | A run-scoped `dungeon_run` projection in the canonical state service | Fresh loadout each run, endless rooms, adaptive questions, run score and run-only currency. An active run survives a Forge/browser/workstation restart and is cleared only by a recorded death or explicit run completion. |
| Practice | Separate non-competitive practice session | Unlimited concept selection and AI help without Dungeon difficulty, leaderboard or Campaign reward mutation. Practice may record bounded learning evidence, but it never becomes a Dungeon run. |

## Dungeon save contract

The state service owns the active run. A run checkpoint includes:

- run ID and deterministic seed;
- floor/room position and room type;
- the current question ID, type, concept and difficulty;
- the run loadout, HP, heals, run currency and score;
- the current `dungeon.py` editor buffer.

`dungeon.py` is a controlled projection/cache, not a second save authority. The
Forge reads and writes its content through the state gateway. A restart restores
the last committed checkpoint and editor buffer. A new question rotates the
question ID and writes an empty editor buffer before the next prompt is shown,
so tips or solutions from the previous room cannot leak forward. A death marks
the run terminal, clears the run buffer and requires a fresh starter loadout.

Autosave is bounded/debounced and reports the last committed checkpoint. An
unsaved buffer is not promised across a hard power loss; the last gateway
checkpoint is the durable guarantee.

Each checkpoint is bound to the question ID that was current when the edit was
captured. If a question rotates while a debounced save is in flight, the state
service rejects that stale write with a conflict response; it cannot repopulate
the new room with an old answer or tip.

## Adaptive question contract

The generator may propose a current question, but the state service validates
the public schema and owns difficulty, Impact, damage, score and reward bands.
Only the current question is projected to React/provider context. Hidden answer
keys and future rooms remain outside the public projection. Every answer binds
to the run revision, question ID, nonce, digest and evidence ID before a
provider verdict can mutate the run.

Supported question types include true/false, multiple choice, short explanation,
code tracing, output prediction, bug hunting and refactoring. A custom mob is
named for the weak concept it tests; a boss combines several different types
instead of inventing arbitrary rewards.

Difficulty rises from validated evidence (weak concepts recur, demonstrated
mastery unlocks harder variants) with bounded recovery questions after misses.
For comparable competition, a daily seed can later produce a hosted leaderboard;
local-only scores remain provisional until provider authentication exists.

## Room loop

An initial local vertical slice should support:

`start run -> encounter question -> answer/verdict -> rest -> market -> next room -> finish/death`

Rest rooms heal through state-service choices. Market purchases spend run-only
currency. Permanent Campaign equipment is not copied into the run, and run
items do not silently alter the Campaign loadout.

## Practice mode

Practice starts independently from Campaign and Dungeon. The player chooses one
or more concepts, difficulty and question types, then receives the same bounded
context/AI assistance pattern used by Campaign. It can be used indefinitely,
does not expose or create `tutor.py`, and does not appear on the Dungeon
leaderboard. A dedicated in-memory editor or controlled `practice.py` buffer
may be added later if useful; it must not become a repository save.

## State/event outline

Planned canonical events are:

- `dungeon_run_started`
- `dungeon_checkpoint_saved`
- `dungeon_question_issued`
- `dungeon_question_rotated`
- `dungeon_answer_submitted`
- `dungeon_verdict_recorded`
- `dungeon_rest_used`
- `dungeon_market_purchase`
- `dungeon_run_finished`
- `dungeon_run_died`
- `practice_session_started`
- `practice_attempt_recorded`

React renders these validated projections and events. It does not calculate
rewards or independently advance a room.

## Delivery order

1. Add the local run checkpoint/restore/blank-on-rotation contract.
2. Add a small Dungeon screen and controlled `dungeon.py` projection.
3. Add three deterministic question renderers (true/false, multiple choice and
   code checkpoint), then provider-bound verdicts.
4. Add adaptive concept selection, custom mobs and multi-phase bosses.
5. Add rest, market, score and local provisional leaderboard.
6. Add independent Practice mode.
7. Revisit authenticated hosted scores and cross-device Dungeon sync after the
   existing provider-auth and two-device gates are closed.

No full Supabase player-state transport is implied by this design.
