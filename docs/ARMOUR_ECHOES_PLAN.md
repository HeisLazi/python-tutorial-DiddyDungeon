# Armour echoes plan — 2026-11-12

Goal: put armour into the Legacy Journal, so the Journal holds weapons, trinkets **and** armour,
and add the distinct armour art that goes with it. Context: roadmap step 3 in
`docs/online/ONLINE_SECTION_COMPLETION_PLAN.md`; findings in `docs/JOURNAL_AUDIT_2026-11-12.md`.
## Status (2026-11-13)

**Later Basics art slice (2026-11-13): in progress, not complete.** The Lanternkeeper has
sixteen generated source candidates: sword action, idle, follow-through and hurt, and staff, whip,
greatsword, hand-magic, scythe and oil action and hurt. They were compared with Pilgrim references and checked as 72px slices; the hip lantern
and straw cape lose definition at game scale and need an in-game art pass. A first hurt candidate
clipped its sword and was replaced; a first follow-through candidate had alpha haze and was
replaced. The Home turnaround and walk sources have also been built and checked as 38px review
strips; the walk source has low-alpha background haze removed by the existing builder threshold.
These candidates are not registered or exported. A temporary frame review is at
`prototypes/godot-combat/lanternkeeper-candidate-preview.html`. Wardplate, equipment art, mobs,
in-game checks and an isolated playthrough remain outstanding. The existing
ember/steel palette fallbacks remain temporary.

Wardplate has all sixteen combat source candidates, checked as 72px slices, plus Home turnaround and
walk candidates checked as 38px strips. They are unregistered and require in-game review. Its checked wrap and bead collar draw on Maasai
shuka and beadwork, while the hide ward panels are fantasy. Construction references: the
[Warsaw Ethnographic Museum](https://ethnomuseum.pl/awad-interwencja-11/),
[Powerhouse Museum](https://collection.powerhouse.com.au/object/367331),
[Cologne Museum of East Asian Art](https://www.museum-fuer-ostasiatische-kunst.de/BORO), and
[Ehime Prefectural Museum of History and Culture](https://i-rekihaku.jp/research/monogatari/article/156.html).

The Basics checklist now has an explicit six-reward/source test. Targeted Journal, armour and
delve tests passed (28), the frontend suite passed (120), and the existing Godot animation smoke
passed against an isolated copy, including a candidate skin validation and look-selection check;
visual timing and projectile origin still need in-game review. The full Python suite
in a copy without a user save or Git metadata reported 439 passed and 16 failed; the original
plan records 13 baseline failures, so the copy's additional failures are not yet classified.

**Phase 1 is implemented in the working tree** (not committed, not deployed). Art, the online
check and the boss 4 to 8 perks are still to do.

- `CAMPAIGN_ARMOUR_ECHOES` in `ide/server/state.py` adds two armour echoes, built into
  `CAMPAIGN_DELVE_GEAR` (now 42 echoes): Lanternkeeper’s Coat (from Lantern Coat, uncommon, 18 damage
  reduction) and Wayfarer’s Wardplate (from Pilgrim Ward, rare, 25). The names are suggestions waiting
  for Lazi's confirmation. Adding another region is one row in that table.
- `_dungeon_journal_prove_gear` runs at a boss clear. An echo unlocks only if the run holds the item
  and has it equipped; a regional armour counts only at its own region's boss; the class starter
  weapon never counts. It only reports echoes that are new, so repeats show nothing.
- The seven shop weapons now earn their echoes at any boss this way, so the audit's "never
  unlocked" item is closed. The Journal checklist says "Prove it · win … wearing/wielding …" and the
  "Legacy rewards" group is now "Any region".
- The boss loot card lists each proven echo (`loot.journal_proofs`).
- Tests: `ide/server/test_armour_echoes.py` (10), plus updates to the checklist and delve gear tests.
  A mutation check (rule removed) made 4 of them fail.
- Server suite on 2026-11-13: 13 failures, all of which also fail with this work removed (checked in a
  scratch copy): campaign content and boss-phase tests, a regional-gear count test that the forged
  armour list pushes from 44 to 48, and two online tests (shop 503, loser currency).
- The test-unlocks sandbox (`QUESTLAB_TEST_UNLOCKS=1`) gives every shop item, so it can earn echoes,
  exactly as it can already earn signature-weapon and trinket echoes; it runs against a separate
  save, so no change was made.
- Not done: a real run (buy, equip, win the Basics boss) in the app, and the online friendly-duel
  check for armour echoes (phase 3).

**Phase 2 (art) is done and wired, but not committed or deployed (2026-11-13).** Claude has no image
generator, so Codex generated the 36 source sheets from the kit's prompts (Argon kept separate
copies). Claude sliced and wired them:
- Combat: 32 sheets in `prototypes/godot-combat/art/` (`tate-lanternkeeper-*`, `tate-wardplate-*`),
  skins `lanternkeeper` and `wardplate` in `combat_catalog.gd` and `arena.gd`, web export rebuilt.
- Home: 6 walk and idle strips in `ide/home-godot/art/`, registered in `home.gd`.
- Frontend and server: look detection in `hunterEquipment.js`, previews in `marketWeaponPreview.js`
  and `RpgViews.jsx`, the allowed looks in `hunterGroups.js` and `online/presence.py`, static previews
  and preview sheets under `public/campaign-art/`.
- Fixes found in review: the Wardplate's fine beadwork produced white speckle under nearest-neighbour
  scaling, so both builders area-average that look (`shrink()`); its walk source had stray shadow and
  sliver pixels, which were cleared (original kept outside the repo).
- Checked: Godot `animation_smoke` passes, `validate_skin` passes for both looks in
  `live_bridge_smoke`, the real combat export renders both looks (sword and staff seen), frontend
  look and preview tests pass.
- Not done: the other weapon styles and the Home scene were not eyeballed in the running app; no
  `graveblade` variants exist for these two looks (excluded like Norse); the Pilgrim Ward shop icon is
  still the old blue coat; `live_bridge_smoke` already fails its Harvest check
  (`tate-harvest-oil` vs the `harvest-scout` file prefix), which this work did not touch.

**Phase 4 (boss 4 to 8 perks) is implemented in the working tree (2026-11-13), not committed or
deployed.** `JOURNAL_BOSS_PERKS` in `ide/server/state.py` gives, for the 4th to 8th distinct boss
cleared: +10 starting run coins, +1 vision scroll, +1 heal charge, +1 ration, +1 ember tonic, and the
title "Master Delver" at eight. They are applied at run start (`_dungeon_start_run`), shown as tiles
and a ladder on the Journal screen, reported on the boss loot card (`loot.journal_perk`), and
tested in `ide/server/test_journal_perks.py` (7) and the Journal screen test. The values are my
proposals and stay one line each to tune. They are not stored in the save (the Journal still holds
echo ids and cleared bosses only), so no schema or cloud change was needed. Not yet tried in a real
run.

Original plan follows.

## Decisions (Lazi, 2026-11-12)

| Question | Decision |
|---|---|
| How is an armour echo earned? | **Prove it in battle.** Win a boss while wearing the armour; the Journal records a permanent echo. |
| Bonuses after the third boss? | **Small perks for bosses 4 to 8.** |
| Which art first? | **Region boss sets**, one distinct silhouette per Dungeon region. |
| First slice? | **One region end to end: Basics Village.** |

## What exists today (checked in the code)

- **Run armour is bought, not dropped.** The Dungeon market sells 14 armour pieces for run coins:
  11 tied to a region and 3 generic (Ember Ward, Field Jacket, Syntax Cuirass). Elites drop
  trinkets and bosses drop signature weapons, so there is currently no armour source for the
  Journal to hook into.
- **The Journal's 40 echoes** are built in `state.py` (`CAMPAIGN_DELVE_GEAR`) from run items:
  15 weapons (8 boss signature weapons plus 7 market weapons) and 25 elite trinkets. An echo's id
  is `campaign-<run item id>`, tier is fixed (weapons epic, trinkets rare), and it carries
  `mode_eligibility: [campaign, sparring, pvp]`.
- **Correction to the audit:** the seven "legacy" weapon echoes are the seven weapons sold in the
  market (Syntax Sabre, Loopblade, Aether Staff, Pathfinder Whip, Iron Greatsword, Grave Scythe,
  Runic Casting). They are not orphaned data; no rule unlocks them. The rule below fixes that too.
- **Forged armour is a separate, real route.** Four recipes exist (Lanternbound Coat, Drowned Mail,
  Flowkeeper Plate, and a Norse Mail), made at the Hunter's Still from banked region materials, and
  claimable free from a camp stash in a run. That is permanent gear flowing into runs; echoes flow
  the other way. The two stay separate.
- **The run knows what you wear.** The server-owned run `loadout` holds the equipped weapon,
  armour and trinket by name, and the boss branch of `_dungeon_award_loot` already records boss
  clears and Journal unlocks idempotently.
- **PvP.** Friendly duels include any item whose `mode_eligibility` has `pvp`; armour turns into
  a guard bonus of `min(5, reduction // 10)`. Ranked uses a small reviewed list (`RANKED_GEAR`).
- **Cloud.** The Journal stores echo ids only (limit 128, now 40), so about 14 more ids fit
  easily and no schema change is expected.
- **Art cost.** One finished armour is about 20 images: combat sheets for seven weapon styles
  (an action and a hurt sheet each, plus sword idle and follow) and Home front, side, back and
  walk sheets. Fourteen pieces is roughly 280 images, so art, not code, sets the schedule.
  Of 46 armour names only 7 have their own art today.

## The rule: "prove it in battle"

When a boss is cleared (the existing boss branch), look at the run's equipped gear:

- **Armour echo.** If the equipped armour is a run armour for that boss's region, or a generic
  one, unlock its echo. A region armour only counts at its own region's boss; a generic armour
  counts at any boss.
- **Weapon echo (fixes the seven market weapons).** If the equipped weapon is a market weapon,
  unlock its echo at any boss.
- Server-authoritative and idempotent, using the existing `_dungeon_journal_unlock`. The loot card
  already says "Legacy Journal unlocked X".
- Open detail: three market weapons are also the class starter weapons (Aether Staff, Loopblade,
  Pathfinder Whip). Recommended: starter weapons do not count, so the echo rewards buying and
  using the item. This needs a "bought this run" marker on run inventory entries, to be checked
  when implementing.

## Data and balance (proposals for review)

- Add `armor` echoes to the generated list from the 14 market armour pieces, same id pattern
  (`campaign-dungeon-lantern-coat`), `source: 'legacy-journal'`, `mode_eligibility` campaign,
  sparring and pvp.
- Tier by what the piece cost in the run: under 60 common, 60 to 99 uncommon, 100 to 149 rare,
  150 to 199 epic, 200 and over legendary. That gives Ember Ward common; Field Jacket, Syntax
  Cuirass and Lantern Coat uncommon; Pilgrim Ward, Diver's Mail, Shellguard, Keeper Plate and
  Inkwoven Robe rare; Bullhide, Clockwork Mail, Oracle Mantle and Hollow Carapace epic; Last
  Light Vest legendary.
- Effect: campaign `reduction`, taken from the existing armour ladder (common 10 to 12, uncommon
  18 to 20, rare 20 to 30, epic 20 to 35, legendary 45 to 50). Run-only effects such as
  `damage_flat` do not carry over, as with trinkets.
- Names: echoes get campaign-forged names, as the weapons did ("Oathkeeper Sabre"). Names for the
  Basics pair are for Lazi to approve (see below).
- Ranked: echoes are friendly-only to start. Adding any to `RANKED_GEAR` is a separate balance
  decision.
- Journal screen: the checklist already lists slot and tier; update the "how to earn" text for
  armour to "Win a boss wearing &lt;item&gt;" (region armour: "Win &lt;boss&gt; wearing &lt;item&gt;").

## Bonuses for bosses 4 to 8 (proposal)

Keep what exists (+5 starting HP per boss to +15, and a bandage at three) and add one small,
capped, run-only perk per further boss, for Lazi to tune:

| Boss | Proposed perk |
|---|---|
| 4th | +10 starting run coins |
| 5th | +1 vision scroll |
| 6th | +1 heal charge |
| 7th | +1 ration |
| 8th | +1 tonic (and a Journal title) |

Implementation: extend `_dungeon_journal_projection` bonuses and the run start that already reads
`starting_hp` and `starting_bandages`; show the extra tiles in the Journal; add tests. Rule of
thumb: perks together stay a small fraction of a run's economy so later runs do not become
automatic.

## Delivery phases

1. **Rule and data for Basics, plus the seven market weapons.** Server rule, two Basics armour
   echoes (Lantern Coat, Pilgrim Ward), the weapon rule, projection text, tests. Exit check: a test
   run that buys, equips and clears the Basics boss unlocks exactly the expected echoes once; a
   repeat or a non-matching armour unlocks nothing.
2. **Basics armour art.** Two finished armours (about 40 images): Home sheets, seven weapon styles,
   previews, the look mapping in `hunterEquipment.js`, the Godot combat catalogue and Home art.
   Reviewed at game scale for feet, grip, alpha edges and silhouette before import.
3. **Online check.** Echoes appear in the friendly loadout catalogue with the right guard bonus
   and stay out of ranked.
4. **Bonuses for bosses 4 to 8.**
5. **Scale to the other regions in waves.** Cheapest first: the Spire reuses the existing Oracle
   Mantle art. Then Collections (2), Hollow (2), Flow, Archive, Labyrinth, Workshop, and the three
   generic pieces. Rule and data can land for all regions early, with fallback art replaced
   region by region.
6. **Verify end to end** in a real run and across two devices, then rebuild installers.

## Art brief template (one per region set)

For each set: the region and boss theme; silhouette idea that reads at sprite size; palette and
motifs; how the lower and higher tier of the same region visibly progress; weapon-specific poses
needed; and the checklist (grip, feet baseline, alpha edges, crop, in-game scale). Historical
research (Norse, Roman, East African) from `docs/ARMOUR_IDEAS.md` feeds later sets and the forged
route; the existing Norse Mail recipe is the first example.

## Risks

- **Mixed app versions.** A Journal that holds an echo id an older build does not know is rejected
  whole by the local campaign validation (`_validate_campaign_projection`), though the cloud side only
  checks the id's format. Every device (PC, laptop, VM, friends) must update before the new ids can
  appear in a synced Journal, or validation should drop unknown ids instead of raising. Decide before
  shipping the next installer.
- Until art exists, an armour echo falls back to palette art by name (Lanternkeeper’s Coat uses the
  ember look, Wayfarer’s Wardplate the steel look), so it is playable but not distinct.

- Art volume is the long pole; fallback palette art must stay clearly marked as temporary.
- Balance: armour echoes add guard in friendly PvP; keep them out of ranked until reviewed.
- The generic armours are cheap, so their echoes are easy; keep them low tier.
- Equipping only for the boss fight is possible (that is the rule); it still costs run coins.

## Needs Lazi

- Approve names for the Basics pair. Suggested: Lantern Coat becomes "Lanternkeeper's Coat" and
  Pilgrim Ward becomes "Wayfarer's Wardplate"; alternatives welcome.
- Confirm that starter-class weapons do not count for the weapon echoes.
- Confirm echoes stay out of ranked for now.
- Review the proposed tier thresholds and the boss 4 to 8 perks.
