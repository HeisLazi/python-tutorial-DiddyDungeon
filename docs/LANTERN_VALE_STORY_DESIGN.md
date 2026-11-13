# Lantern Vale: story and interaction proposal

Status: **design proposal, not implemented**. Complements
`docs/LANTERN_VALE_PROGRESSION_AUDIT.md`; the reward map remains a proposal.
The interactive story direction and that reward map have been set aside in
favour of the simpler current loot rules in `docs/CAMPAIGN_LOOT.md`.

## Current state

The authored campaign introduces Mira, keeper of the road: lanterns have gone
dark, and the learner builds a small Python adventure about carrying light
between places. The 20 contracts teach foundations, collections, objects,
persistence and transfer; four elites have mechanics tied to verified
objectives. The Unwritten King changes a delivery requirement during the boss.
The Bounty Office currently displays the campaign hook and client; encounters
show their learning tasks and combat mechanics. There is little authored
dialogue or visible cause and effect tying these pieces into a developing
story. This is an audit of the authored content, not a claim about a fresh
end-to-end playthrough.

## Narrative premise

The Vale's road-lantern network is failing. Mira and the people who use the
road need a reliable way to record routes, supplies and deliveries. The hunter
helps them investigate the disturbances while building a small **separate
Python program** that models a traveler and their deliveries. That project is
the learner's own creation: changes to its printed output do not automatically
move characters in the game world. Verified learning milestones can unlock
authored story states, but the game must say what was actually verified.

The Unwritten King is a force that traps the Vale in an incomplete, repeating
story. He can change the conditions of a delivery, exposing brittle rules.
Players defeat him by adapting and explaining their project, not by defeating a
real programmer or copying an answer. His motivation and final dialogue need
writing; this is a direction rather than a claim that content exists.

### Cast

- **Mira:** road keeper and the campaign's anchor. Gives context, reacts to
  milestones and presents earned road equipment. She is helpful without
  pretending to verify code she cannot see.
- **Pyr:** the player's guide at Home and contextual help in the Hunt. Offers
  explanations and hints; does not penalize Lantern Vale milestone rewards.
- **The hunter:** the player's character. Dialogue choices express approach or
  ask for information; they do not replace the learner's project decisions.
- **Vale residents:** a small cast (for example, a courier and a workshop
  keeper) should each have a job and a need. Reuse characters so the player
  can see change rather than introducing a new quest giver every contract.

## Four-act story arc

| Act | Story problem and player action | Learning and visible payoff | Proposed equipment connection |
| --- | --- | --- | --- |
| I: First Light | Mira's nearest road lantern has failed. Investigate the gate and the repeating Echo, build the traveler's first working menu, and end the loop. | After verified Echo completion, the first lantern is lit and the route out of the village is visible. Earlier story markers explain why names, input and choices matter. | First Spark: Mira supplies Patchwork and a Trailkeeper Blade. Echo: she gives Pilgrim Leather for the road ahead. |
| II: The Road | A courier cannot reliably reach the next settlement with the right supplies. Gather route information, model inventory and destinations, and confront the Delivery Beast. | A verified delivery restores service on the next road. The player chooses a weapon at Little Lantern and later obtains the other style as specified in the reward map. | Mira grants Wayfarer Brigandine after the Delivery Beast as road gear earned through restoring the route. |
| III: The Workshop | A caravan works only while someone constantly repairs its records. Help the workshop keeper identify failures, organize the program and model independent travelers. | Verified Caravan Repair brings a small caravan back to the road. The workshop is visibly working again. | The keeper gives the Little Beacon Charm as thanks for reliable work; its guard is explained in the loadout. |
| IV: The Living Vale | The road returns but records need to survive a restart, rules must handle changing data, and the King is undoing old paths. Investigate the records and prepare a solution that can adapt. | The Unwritten Road proves a related idea in a different setting; resolving the boss phases restores the road network. Show the world state and the completed project separately. | Act records mark restored milestones. The King's clear grants the proposed Dawnbringer, Crown Fragment and a trophy, after a story explanation of what they are. |

These are proposed story events and rewards, not existing authored content.
The map does not require removing or reordering the existing contracts.
An acknowledgement should refer to actual evidence: if only code was
inspected, do not claim the learner ran or tested it.

## Interactive story markers

Use a compact campaign map or illustrated location panel accessed from the
Bounty Office. Markers represent authored scenes and points of interest,
not another mandatory walk across the Home hub. A marker is available after
the relevant state transition and shows whether it is required, optional or
already visited. Selecting it opens a brief interaction with a clear way back
to the Hunt. Keyboard and pointer access are required.

Types:

1. **Investigate:** inspect an object, see a short observation, and optionally
   ask Mira or Pyr for context. E.g. examine a lantern whose signal repeats.
2. **Make a decision:** select an actual preference with a visible and honest
   consequence. E.g. pick staff or whip at the existing proposed #6 milestone;
   the other is obtained later. A dialogue-only preference may change a line
   or map detail, but must not be marketed as changing the campaign outcome.
3. **Try a small interaction:** operate an illustrated gate/menu, observe the
   result and change the input. It teaches a generic concept without running
   untrusted learner code in the story UI or providing the project solution.
4. **Return and report:** after the server confirms a milestone, visit or
   open a short result scene to see the change, collect a reward already
   granted by the server and choose the next destination. Closing the panel
   cannot lose an entitlement or make the learner redo a cleared task.

Markers should enhance individual contracts without adding mandatory filler.
First implementation should be **one short required interaction** before the
first elite and one optional interaction; let the player reopen, skip or read
again where appropriate. A required story interaction must not gate access to
Codex/help or an already earned item. No missing an optional scene should block
a contract, boss, achievement or learning outcome. Use static illustrated
scenes and existing UI initially; no new large Godot region or extensive
branching narrative until the interaction is shown to be worth the effort.

## Example vertical slice: The Endless Echo

1. **Marker — Mira's broken signal:** inspect a road lantern. Its signal keeps
   repeating even after someone tries to stop it. Mira asks the hunter to look
   for a safe way to end the loop. The player may ask what a loop is or proceed
   to the Hunt; the relevant Codex explanation remains available throughout.
2. **Try it:** an optional small illustrated signal panel has `repeat` and
   `stop` controls. Clicking stop clearly ends the signal; the panel introduces
   the idea, without dictating the learner's Python implementation.
3. **Hunt:** complete the existing menu and Echo Break objectives. The story
   does not alter their verified evidence or the existing fight mechanic.
4. **Return:** after verified clear, show a lit lantern and Mira offering the
   Pilgrim Leather. Present the proposed First Light act record and armour in
   one receipt. The server has already granted the reward; the player chooses
   when to equip it.

This gives the player actions before and after a fight, a consequence to see,
and a reason for the reward. It is not a cutscene that asserts the Python file
physically controlled a lantern.

## Persistence, scope and acceptance

- Campaign state is server-authoritative. Define stable marker IDs and
  available/visited/choice state, bounded sync and conflict rules before coding.
  Use existing verified contract and boss state as the authority for world
  changes; story interactions must never fabricate verification.
- Handle new, in-progress and finished saves without resetting contracts,
  duplicating loot, auto-equipping gear or blocking existing progression.
  When an older save has already cleared the Echo, its lantern can be shown
  lit and the scene can be replayed without presenting a second reward.
- Avoid a hard dependency on new sprite art, audio or AI-generated dialogue.
  Use authored text and current assets for the first slice. Any added reward
  UI and marker are planned work, not existing features.
- Judge the slice by whether a new learner understands who needs help, why
  they are doing the programming task, what changed when they succeeded and
  where to go next. Check that the interactions remain quick, usable by
  keyboard, replayable and easy to leave; observe a real beginner before
  expanding to all four acts. Time and performance targets remain to be
  measured.
