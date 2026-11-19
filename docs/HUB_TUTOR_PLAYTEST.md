# Home and Tutor redesign: playtest notes

These observations come from an agent-driven Chromium playthrough with a disposable save and workspace, not from a study with a new learner.

## What changed

- The Great Hall now has separate gear and hunter areas, a roped trophy alcove, and an open route to the hearth and Pyr’s door. Benches and banquet furniture were removed; the existing eighth hall upgrade now decorates the trophy alcove. Saved levels and upgrade prices are unchanged.

- Hearth rest costs 1 coin per 10 missing HP, rounded up. If the player cannot afford full recovery, emergency rest brings them to 30% HP for free. Boss fights begin explicitly; retreat resets their phases, and lessons and bestiary stay available while practice and sparring are locked.

- Home stations open pixel-styled screens inside the game frame, with a zoom transition and a return to the room. The trophy station displays named defeated campaign bosses from saved project records; Dungeon boss names are not yet retained. The hearth separates resting from room improvements, and Pyr has feeding and training controls. The redundant Forge door has been removed; the main Forge navigation remains.

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
- The Home hunter uses a revised unarmed black-and-gold pixel-art turnaround and a four-pose walk cycle in each direction; the right side mirrors the left. The combat hunter is unchanged. The source remains AI-generated and has not had frame-by-frame manual Pixelorama polish.

## Hunter artwork source

The Home hunter turnaround and walk sheet were generated with the built-in image-generation tool from the supplied Alucard and gothic pixel-art references. Prompt: original dark-skinned gothic hunter with a short black afro, ivory cravat, black coat and cape, charcoal armour, antique gold trim, tall boots, no weapon; consistent front, side and back RPG views with a four-pose walk cycle, crisp limited-palette pixel art on neutral grey. The source images live in `tools/home_art/sheets/hunter_v3/`; `python3 tools/home_art/build_hunter_v3.py` cuts and aligns the 38×38 game frames.

## Boss and hearth playtest

With a disposable save, Chromium entered a boss, visited Lessons and Bestiary, confirmed practice and sparring stayed locked after reload, and chose both stay and retreat. A trusted test phase reduced Resolve from 15 to 10; after retreat and starting again it returned to 15. A 40/100 HP rest cost 6 coins, and a zero-coin emergency rest raised 10/100 HP to 30/100. Direct recovery and practice requests during the fight returned 409. The phase verdict was injected by the test service, not graded by PYR; the full boss fight still needs learner playtesting.

## Great Hall layout playtest

In a disposable browser save, walked to the hearth, hunter, gear and trophy stations and opened each screen, then walked through Pyr’s door and back. Godot reachability checks passed for every hall and den upgrade level. Compatibility screenshots were reviewed across the hall ladder. These are agent-driven checks, not a new-player usability study.
