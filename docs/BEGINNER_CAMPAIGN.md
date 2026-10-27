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
