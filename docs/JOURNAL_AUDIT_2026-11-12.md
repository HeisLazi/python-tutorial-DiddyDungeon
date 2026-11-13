# Legacy Journal audit — 2026-11-12

Scope: what the Journal does today, what was checked, what is missing, and a proposed fix
order. Read-only audit; no Journal code was changed. Roadmap context: step 3 in
`docs/online/ONLINE_SECTION_COMPLETION_PLAN.md` (Journal first, with the in-progress weapons and
armour as its content, then the co-op raid).

## Update — fixes applied the same day

Done:
- **Failing tests triaged and fixed (9).** All were stale test setups, not game bugs: the loader now
  pads a project back to its canonical mobs (an integrity guard), the Silver Reels campaign has 20
  mobs and its entry file is `silver_reels/casino.py`, mob lore now comes from the campaign file,
  revisiting the start camp reopens it as a rest room (it is paid, so not a free heal), and the
  legacy-reconciliation test no longer seeds a hand-written `current_quest`, which the loader
  derives. The migration test now finds its migration by name. `test_state_service`: 91 of 91 when this was written; on 2026-11-13 it is 85 of 91 with or without the 2026-11-13 echo work (boss-phase and campaign-content tests, from other uncommitted changes in this tree, not looked into).
- **Journal screen rebuilt.** The projection now carries a full checklist, per-region progress and
  totals; the screen shows every echo and boss (earned or not), how each is earned, and the modes
  an earned echo works in. The setup page has a shortcut under the heading, the rule text no
  longer mentions armour, and the milestone no longer says "fully unlocked" after three bosses.
  Server and UI tests added (`test_journal_checklist.py`, `DungeonLegacyJournal.test.js`).

Update 2026-11-13 (later): bonuses now continue past three bosses (item 4 closed); see
`ARMOUR_ECHOES_PLAN.md`.

Update 2026-11-13: the "prove it in battle" rule is implemented (see `ARMOUR_ECHOES_PLAN.md`
status): the seven shop-weapon echoes now unlock and two Basics armour echoes exist. The "Legacy
reward" label is gone from the screen.

Still open:
- No armour in the Journal (item 1), the seven never-unlocked market-weapon echoes (item 2, labelled
  "Legacy reward" on screen; the armour plan's rule unlocks them) and bonuses stopping at three bosses (item 4).
- Test and UI debt found while fixing the 16 frontend tests (see "Frontend tests" below).
- Not verified: earning an echo in a real run, and cross-device save and restore.

## Frontend tests (16 fixed, 1 real bug found)

`src/cloud/forgeRuntime.test.js` had 16 failing source-text tests; all failed at HEAD too. Checked
assertion by assertion (about 28 broken ones; most of each test still passed):
- **One real bug, fixed in code.** The bounty board's mob mapper in `RpgViews.jsx` checked only
  `'defeated'`, so a legacy `'cleared'` mob would show as locked with a plain star, although the
  server treats `'cleared'` as finished. It now uses `isMobDefeated()`.
- **Stale copy and structure, tests updated.** The product now says Hunt (was Forge) and
  Hunter's Study (was Tutor Notebook); the route list is Campaign, Hunter's Study, Infinite Dungeon,
  Colosseum, Codex, Settings (Character and Homestead were merged into Campaign, and the test now
  forbids them returning); view normalisation also redirects the retired pages; the boss sidebar
  is wider (380px); the active-file prompt wording changed.
- **Removed UI.** The PYR pet in the Forge sidebar, the homestead live-status block and the old
  loadout panel are gone from the JSX; those dead assertions were dropped. The pet's CSS
  (`.pyr-sidebar-companion`, `.pyr-eye`, `pyr-float`, `pyr-blink`) is still in `foundation.css`
  and `v2.css` and can be retired.
- **Glyph rules scoped.** The three "no text glyph icons" checks banned glyphs across the whole
  file. They now apply to the live components they were written for (Character screen, Dungeon
  maps, Journal, navigation). A mutation check confirmed a reintroduced glyph fails the test.
  The new Journal rows use the shared SVG check; one stray ⚔ was removed from the boss heading.

Known glyph debt, not fixed (a design and art job, not a test fix): the classic Homestead fallback
scene (window, shelf, chest and pet props), the achievement catalogue (`HOME_ACHIEVEMENTS`), the
campaign route cards and market stock, and bounty-board entry icons still use text glyphs.

## How it works today

- Elites drop a run-only trinket and bosses drop a run-only signature weapon. A matching
  **permanent armory echo** is recorded through `Journal` (`state.py`: `_dungeon_journal_unlock`)
  and added to the campaign armory, so it is usable outside the Dungeon.
- There are **40 echoes**: 15 weapons (epic) and 25 trinkets (rare), four per region (five in
  the hollow) plus seven with no region. Eight regions, one boss each.
- Boss clears are recorded once per region and give capped future-run bonuses: +5 starting HP per
  boss (max +15) and +1 bandage once three bosses are cleared.
- Shown in: the Dungeon setup screen, the in-run JOURNAL tab, and the Home Journal door.
- Ownership/eligibility is server-side (`online/ownership.py`, `online/loadouts.py`): echoes are
  explicitly usable in campaign, sparring and PvP; raw run pickups are not.

## Checked and working

- Server projection and API: a throwaway save seeded with two boss clears and three echoes
  returned the right bonuses (+10 HP), boss names and echo list from `/api/dungeon`.
- The real app showed that data correctly on the Dungeon setup screen (throwaway save only).
- Passing suites: delve gear, armory, regional gear, Dungeon weapons, Dungeon vision, online
  ownership (43 of 44 in that run; the one failure is a stale migration-order assertion).

## Not working or missing

1. **No armour in the Journal.** None of the 40 echoes is armour. The 13 Infinite Dungeon armour
   pieces (Ember Ward, Field Jacket, Syntax Cuirass, … Last Light Vest) are run-only, and no
   Journal reward converts one. The armory has 31 armour items, but only 7 of the 46 distinct
   armour names have their own art (the three campaign outfits, Oracle Mantle, Patchwork Travel
   Coat, Pilgrim Leather, Wayfarer Brigandine); the other 39 use shared palette art
   (`prototypes/godot-combat/SKIN_WORKFLOW.md`, "Armour art backlog").
2. **Seven weapon echoes are never unlocked.** Correction made later the same day: they are the
   seven weapons sold in the Dungeon market (Syntax Sabre, Loopblade, Aether Staff, Pathfinder
   Whip, Iron Greatsword, Grave Scythe, Runic Casting). Nothing grants their echo, because only elite
   trinkets and boss signature weapons trigger a Journal unlock. The armour plan's "prove it in
   battle" rule fixes both (`docs/ARMOUR_ECHOES_PLAN.md`).
3. **The Journal screen is hard to use.** It sits below the class cards on the setup page and
   lists only what is already earned: no checklist of the 40 echoes or 8 bosses, no per-region
   progress, and no sign of which modes an echo works in. Its rule text mentions "forged armour
   … camp stash", which is not a Journal reward. "Next milestone" says everything is unlocked
   after three bosses while the header still reads "x / 8".
4. **Boss bonuses stop at three.** Bosses four to eight add a record and an echo but nothing
   mechanical.
5. **Nearby failing tests (existing, not caused by this audit).** `test_state_service`: 4
   failures and 4 errors, none named for the Journal. Two touch Dungeon flow: revisiting the
   start camp now opens a rest room where the test expects an inert selector (probably a stale
   test; it matches the wish that camps stay interactable) and a boss-gate progression test.
   `test_cloud_migrations`: one test assumes a specific migration is the newest.

Related mechanic worth knowing: **forged armour** (four recipes made at the Hunter's Still from
banked region materials) can be claimed free from a camp stash in a run. The Journal panel used to
say so; that line was removed because forged armour is not a Journal reward, but the mechanic is
real and is the reverse route to echoes (permanent gear into a run, versus run gear into the
Journal).

## Not verified

- Earning an echo by actually playing an elite or boss fight in a real run (the check above used
  a seeded save).
- Saving and restoring the Journal across two devices or after a cloud sync.
- Whether any armour (not just weapons and trinkets) should be a Journal reward: a design call.

## Proposed order

1. Triage the failing Dungeon and campaign tests as stale versus real, and update or fix them.
2. Make the Journal screen useful: its own entry point, a full checklist of echoes and bosses
   (locked and earned), corrected copy, and the modes each echo works in.
3. Unlock the seven market-weapon echoes with the same "prove it in battle" rule as armour.
4. Add armour to the Journal: choose the source (elite or boss per region), then author the
   armour with the combat art workflow, distinct silhouettes first, per
   `docs/ARMOUR_IDEAS.md` and the SKIN_WORKFLOW backlog.
5. Verify earn, claim, restart and cross-device restore end to end in a real client.

## Decisions needed from Lazi

- Should armour come from elites, bosses, or both, and how many sets per region?
- Should bonuses continue past three boss clears?
- Which armour art goes first (suggested: one set per region boss, or the historical sets).
