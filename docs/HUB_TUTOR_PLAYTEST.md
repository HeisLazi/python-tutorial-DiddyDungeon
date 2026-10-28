# Home and Tutor redesign: playtest notes

These observations come from an agent-driven Chromium playthrough with a disposable save and workspace, not from a study with a new learner.

## What changed

- Home stations now open full-window screens with a zoom transition and a return to the room. The hearth separates resting from room improvements, and Pyr has feeding and training controls. The redundant Forge door has been removed; the main Forge navigation remains.

- Home has one Great Hall for the hearth, equipment, hunter stats and permanent bonuses, and trophies. A labelled, visible door leads to Pyr's Den. Pyr moves independently in the den and can be approached for care. The map reflects the two walkable rooms. A dismissible guide explains what Home is for, and Shift speeds movement.
- Five formerly walkable rooms are no longer connected. Their saved cosmetic upgrade levels are retained; they are not displayed in the new two-room layout. No save migration, refund, or automatic spending is performed.
- Lessons and the former Codex have one searchable topic page. Deeper reference examples, mistakes and validated encounter notes remain available inside each topic. A Forge bounty can open its relevant concept and return to the same task. Contracts remain in the Bounty Office.
- Practice has a topic and activity selector. Multiple choice and true/false use the main workspace; reading and writing exercises use code editors. Ten foundational topics have authored lessons and local checks. Other topics use their existing reference material and do not yet have authored multiple-choice/true/false checks.
- Sparring keeps clickable rounds and adds a PYR-written code round in an isolated scratch editor. PYR reviews the answer without running it or changing campaign files; failure to obtain a verdict leaves the round available to retry.

## Evidence

- The old seven-room build required several transitions to reach activities that already had navigation buttons. A keyboard walk from the hall to the library took about 2.7 seconds, and walking onward into the gallery another roughly 2.6 seconds, excluding searching or reading. Those are single agent measurements, not player averages.
- In the two-room build, Chromium walked from the hall to the den and back through the actual doorway. The map updated in each room. A separate Chromium pass opened equipment and hunter upgrades from the hall, and spent a stat point on the isolated save.
- Chromium verified concept selection, true/false feedback, the merged reference, and the link from a bounty to the matching lesson and back. A real PYR sparring session generated a coding question and reviewed an incomplete submission; a deterministic browser check verified edited code was sent and rendered feedback. Backend tests cover a valid submission, provider failure and retry, wrong route, and replay rejection.
- Godot reachability checks cover each hall/den upgrade level from each entrance and starting point. Compatibility-rendered screenshots were reviewed for the base and upgraded hall, and for front/side hunter views.

## Still to validate

- Have a new player try the hall without instructions and check whether the physical station affordances and door are clear. The starter den remains deliberately sparse until upgraded.
- Expand the remaining reference-only concepts into authored checks and have an actual beginner test the teaching sequence. More practice formats and AI output still need pedagogical review.
- Test a complete sparring bout with a learner writing code. The scratch answer is currently reviewed, not executed, and is not saved on leaving the bout.
- The generated hunter was cut and previewed in-game; detailed frame-by-frame art polish in Pixelorama is still outstanding. The old combat hunter is unchanged.
