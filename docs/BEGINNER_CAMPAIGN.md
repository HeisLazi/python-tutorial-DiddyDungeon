# The Lantern Vale: beginner learning path

The Lantern Vale is a first campaign, available alongside the existing projects rather than replacing or locking them. You build a small terminal adventure in `lantern_vale/`: a traveler explores locations, collects supplies and completes a delivery. There is no external package or framework to install. The same project grows across four acts, so each new concept solves a problem the player has already met.

This is one coherent project rather than several disconnected introductions. It aims to prepare a learner for the next projects, not promise mastery: independent practice, feedback and more projects remain necessary. The Casino applies the same ideas to rules and randomness; Django later applies functions, classes, data, validation and tests in a web framework, which still needs its own HTTP, database and security lessons.

## Teaching contract

Each encounter gives a short explanation, a concrete task, and a check: predict or trace, write and run, debug, explain, or change the program. Examples teach a generic pattern rather than providing the full project solution. Make the expected behavior and at least one edge case explicit. Encourage experiments before submission; show how to undo or correct a mistake. Use the existing Codex pages for reference and PYR for feedback, without requiring a paid provider for reading. A setup check verifies files and the first run locally; the existing grading flow handles later goals and may require PYR or the configured classic tutor.

The game must remain playable at each milestone. Avoid forcing framework knowledge, internet access, databases, GUI toolkits, or advanced functional techniques on a beginner. Show small steps, use deterministic examples for tests, and explain vocabulary on first use. Practice transfers ideas into unfamiliar names and domains instead of testing only memorized game code.

## Route

| Act | Learner outcomes | Project milestone |
| --- | --- | --- |
| 1. First light | Files, running Python, output, variables, strings, input, types, decisions, loops and reading errors. | A traveler can enter a name, choose an action, receive feedback and quit. |
| 2. The road | Functions, arguments and return values, lists, dictionaries, iteration, strings, data validation and tests. | Move between named places, manage inventory and complete a delivery. |
| 3. The workshop | Modules, imports, classes, instances, methods, object state, composition, JSON files and exceptions. | Organize the game across modules, model a traveler and persist a safe save. |
| 4. The living vale | Pure functions and side effects, transformations, comprehensions, callbacks, tests, debugging, refactoring and adapting requirements. | Make rules testable, add new content, and build a small independent transfer exercise. |

Every act revisits earlier concepts. Learners predict a result before running it, modify working code, explain choices, recover from errors, and test normal and boundary inputs. The final transfer task changes the setting and data while preserving the underlying pattern; it is not a copy of an earlier answer.

## Acceptance and integration

- The campaign appears in the existing campaign selection and its first encounter can be opened without resetting a save or replacing the current project.
- Its authored objectives use existing setup and grading types, include explicit file targets where needed, and remain within sync bounds. Existing project progress is preserved.
- Tutor Codex pages give portable explanations, examples, mistakes and self-checks for the foundations, collections, classes, modules, persistence, testing and functional techniques used here. They are reference material, not campaign answer keys.
- Verify campaign schema, ordering and projection, selection on a temporary save, meaningful teaching coverage and Tutor projection. Run backend tests and check the Forge/Tutor in a browser with an isolated save.

## Verification and remaining limitation

The backend suite passes with this campaign and the Codex additions. In an isolated local save, Chromium selected the new campaign while preserving the Blackjack board, created the project directory and file through the Forge terminal, saved and ran the first program, and passed all three local setup checks. The Tutor displayed the expanded Variables and Functions reference pages. The production frontend build passed.

A full graded playthrough is still needed: the configured OpenCode service returned no answer when the browser requested a generated question. The game reported the failure; the local setup checks remain usable. Later explanation/prediction questions and code submissions depend on the existing PYR/classic grading flow. This course is a foundation for later projects, not a substitute for independent practice or Django-specific instruction.

## Encounter map and pacing

This is a planning estimate, not a measured playtime. Allow roughly 30–90 minutes per contract to read, experiment, write, debug and reflect, plus 1–3 hours for the boss: approximately **11–33 hours** in total. Some learners will take longer, especially if Python and the terminal are new. Breaks and optional experiments are not timed by the game. A complete learner playthrough is needed to calibrate these numbers.

| Act | Contracts in order | Act-ending elite and mechanic |
| --- | --- | --- |
| First Light | First Spark (run a file); Nameless Wraith (variables); Whispering Gate (input); Forked Path (branches); Endless Echo (loops). | **Echo Break:** demonstrate a menu that handles an unknown choice and stops correctly to bank one guard for this fight. |
| The Road | Little Lantern (functions); Inventory Drowner (lists); Counting Moth (iteration); Mapkeeper (dictionaries); Delivery Beast (combined state and rules). | **Delivery Proof:** verify success and failure cases to reduce later mistake damage in this fight by 3, to a minimum of 1. |
| The Workshop | Broken Number (exceptions); Test Lantern (assertions); Module Mason (imports); Selfless Golem (instances); Clockwork Caravan (composition). | **Caravan Repair:** demonstrate two independent travelers and invalid movement; later verified goals deal +1 Resolve impact, without skipping goals. |
| The Living Vale | Memory Keeper (JSON); Quiet Flame (pure functions); Transformation Sprite (filter/map); Remembering Shade (callbacks); Unwritten Road (transfer and documentation). | **Open Road:** test a basket against new data to bank two guards for this fight. |

The final boss, **The Unwritten King**, asks for the working project, a code-reading question, the Changing Road twist (a second delivery and boundary tests), and an interview. Completing the twist restores up to 8 HP before the interview. Each elite bonus is tied to a verified objective and only affects that fight; it cannot skip an objective. Boss phase verification is persisted, so its healing cannot be claimed twice by retrying the phase.

## Items and rewards

The campaign has five weapons, five armor pieces, five trinkets, four foods, two tonics and one relic. They use the same equipment effects as other campaigns. A completed contract rolls an eligible campaign item; later contracts give higher-tier gear better odds. Help from PYR uses the existing campaign assistance rules: paid asks reduce XP/coin rewards, and after two such asks the contract drops no loot. The boss awards its relic and one unowned legendary gear item. These are randomized drops, not a guaranteed item at each named contract. The exact effects and prices live in the campaign's `armory` entries.

The encounter mechanics and all four boss phases have been exercised through a complete automated progression using simulated verified results on a temporary save, including drops and boss loot. Chromium was also used to check the elite panel and that the beginner's build objective appears before its explanation. This is not a human playthrough or proof of PYR's grading quality; the OpenCode issue above still needs a working provider to test real grading and calibrate the time estimate.
