# Lantern Vale Act I: playtest and Tutor priorities

## What was exercised

On 2026-10-28, the five Act I encounters were played in the full app in Chromium, using a disposable save and workspace. The test server used the same local OpenCode configuration as the regular game; no real campaign save was changed. This was an experienced tester following the beginner path, not a study with a new learner and not a measured playtime.

- **The First Spark:** made the folder and file in the terminal, saved and ran a program, edited it, received a PYR code verdict, and answered the generated question.
- **The Nameless Wraith:** wrote and ran variables and an update, recovered from a wrong working directory after a test-server restart, resubmitted, and answered a variable trace.
- **The Whispering Gate:** built name input with a blank fallback and number conversion; PYR graded both changes and a text-versus-number question was answered.
- **The Forked Path:** built and ran north/south/unknown branches. PYR caught an actual indentation error, the corrected program was accepted, and the branch question was answered.
- **The Endless Echo:** built and ran a menu with look, spend, unknown action and quit. The code objectives, elite guard reward and loop question all completed; the next act's Little Lantern became available.

These were actual provider responses, not simulated verdicts. The earlier no-answer result came from the agent's isolated environment using different XDG/OpenCode settings, not proof that the player's PYR was broken.

## Evidence from the run

1. **The teaching target can drift.** First Spark's objective asked the learner to explain the editor, file, terminal and interpreter. The generated question asked which of two print statements runs first. That's a valid prediction exercise, but it did not check the stated goal. The variables and input questions did check relevant concepts.
2. **A question can be ambiguous in context.** The branch question asked what the full snippet prints for west; the snippet also printed a greeting, while the choices contained only the branch's output. A beginner could reasonably be confused even though the intended branch answer was clear.
3. **Feedback can claim unobserved evidence.** The variables exercise asked the learner to change the starting amount and rerun. PYR accepted the code and said the rerun showed a new amount, although the test had only run the original amount. The verifier should distinguish code it can see, terminal output it actually received, and experimentation it cannot establish.
4. **Working-directory state is not obvious.** After the test server restarted, the terminal returned to the workspace root. Running `python game.py` there failed; PYR correctly recognized the missing-file output and suggested checking the directory. A novice needs the current folder and the correct run command made obvious without depending on an error first.
5. **The help route is fragmented.** The battle's “Study this at home” button sends a brief to LearnHarness (or offers a handoff), while the built-in Tutor has its own Contracts, Codex and IDE Practice. The direct, lesson-specific path from a campaign task to a relevant in-app explanation and back is not apparent from the battle screen.
6. **Asking has a reward cost.** The UI says each paid PYR ask reduces XP/coins and two asks remove loot. This existing rule may discourage the questions a true beginner should ask. It is a product choice whether introductory practice should be exempt, rather than a defect inferred from one run.
7. **The elite mechanic did work, but was thin.** Echo Break granted a guard after a verified demonstration. It did not replace the learning objective or finish the fight early. Its value is understandable, but the player has little guidance about why the guard matters or where to see it after earning it.

## Recommended Tutor revamp, in order

1. **One contextual study route:** from the current objective, open the matching in-app concept with a short explanation, runnable generic example, and a clear return to the exact task. Keep LearnHarness as an optional deeper-study handoff.
2. **Teach → predict → try → explain → transfer:** add small guided lessons and checks for each Act I concept. Keep the learner's own code in the Forge and make hints progressively specific rather than revealing the solution.
3. **Align questions with objectives:** pass the exact teaching goal and required skills to the question writer, validate that prompts and answer choices are internally consistent, and offer a retry without HP loss if generation fails. An output question should specify whether it asks for the entire output or one specific line.
4. **Evidence-aware grading:** show what PYR can actually verify; never assert a rerun, input case, or experiment occurred unless captured. Check deterministic properties locally where appropriate, while keeping code review and explanation feedback in PYR. Do not run untrusted code outside the app's existing execution boundary.
5. **Better recovery and onboarding:** show the terminal's current folder and copyable run command, explain tracebacks and indentation in plain language, and retain the learner's place when switching between Tutor and Forge.
6. **Beginner-friendly help and assessment:** decide whether hints in the foundation path should be free; give actionable feedback and a short explanation after wrong answers. Add an optional teach-back or transfer prompt that checks understanding without making AI-generated multiple-choice text the only measure.

Before considering the Tutor complete, test the same route with an actual beginner, check accessibility and model-failure recovery, and review later lessons on functions, data structures, objects and functional programming. Do not treat this single Act I run as evidence of mastery or a reliable hours estimate.
