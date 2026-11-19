# Lantern Vale progression audit and proposed reward map

Status: **design proposal, not implemented**. Audit of the worktree on 2026-11-05.
This document covers the beginner campaign only. Infinite Dungeon remains a
separate run-based system with its own classes, random encounters and loot.
The fixed per-contract reward proposal below was superseded by the simpler
campaign loot rules documented in `docs/CAMPAIGN_LOOT.md`.

## Findings from the current implementation

1. Lantern Vale has 20 ordered contracts in four acts and a final boss. Its
   objectives progress from creating and running a file to functions,
   collections, classes, persistence and transfer. The contract after the one
   defeated is made available; the boss becomes available after contract 20.
   Source: `ide/server/campaigns/00-lantern-vale.json` and
   `LocalStateService._finish_mob` in `ide/server/state.py`.
2. The authored campaign armory contains five weapons, five armour pieces,
   five trinkets, four foods, two tonics and one relic. Most armour is a
   strictly increasing damage-reduction number (10, 18, 26, 35, 45%). That is
   a progression ladder, not five meaningfully different equipment decisions.
3. Ordinary contract loot is rolled from non-legendary campaign gear and
   consumables, weighted by depth and luck; owned permanent items are skipped.
   Elites first try a deterministic pick from an unowned regional Dungeon
   trinket pool, then fall back to the campaign roll. Consequently none of the
   campaign armour milestones below are currently guaranteed. A separate aid
   roll has a 30% chance when eligible.
4. Each paid PYR ask reduces fight XP and coins by 20 percentage points, to a
   40% floor; at two paid asks both contract loot rolls are suppressed. This is
   a poor fit for a beginner campaign where asking for help is part of learning.
   Free-ask charges are an exception. See `_record_pyr_assist` and
   `_finish_mob`.
5. The boss grants its campaign relic and one randomly selected unowned
   legendary gear piece, potentially a separately selected campaign Dungeon
   weapon, plus PYR's Blessing. Dawnbringer is therefore not a guaranteed boss
   reward. Market stock can also sell eligible campaign gear before a planned
   milestone: common/uncommon items open when the campaign starts, while rare
   stock requires half the contracts or completion. Existing Hunter-style and
   fashion gear has its own shop path.
6. `equipment.armor` and `equipment.trinket` store equipped names; campaign
   weapon ownership and selection use `hunter.armory` IDs. Legacy equipment
   has a separate owned list. Equipment effects, early guard breaks, Home,
   Hunt and Sparring therefore need to be considered together. Bonus impact
   cannot end a campaign fight while required objectives remain: the guard
   breaks instead and the remaining objectives still need verification.
7. Existing class choices are for Infinite Dungeon runs. The campaign already
   has equipment and weapon-style selection; it has no equivalent campaign
   class contract. Current Dungeon runs retain their own starter gear and
   class passives.
8. An experienced tester played Act I with actual provider responses; the
   prior playtest found question alignment and evidence problems, fragmented
   study navigation and the potential cost of asking for help. It is not a
   beginner study or a verified full-campaign playthrough. See
   `docs/LANTERN_ACT1_PLAYTEST.md`. The published 11–33 hour range in
   `docs/BEGINNER_CAMPAIGN.md` is a planning estimate, not measured time.

## Design rules

- A verified contract clear earns the named milestone reward regardless of
  PYR assistance. Explanations, Codex use, retries and wrong answers cannot
  erase it. Do not grant a reward merely for asking: the authored objectives
  still need to be verified. Proposed for Lantern Vale: paid PYR asks also do
  not reduce its base XP or coins. This is a campaign-scoped change, not a
  change to other campaigns or Dungeon.
- Preserve the existing base XP/coin schedule initially; evaluate rewards and
  economy against a real beginner playthrough before changing numbers. No
  promise of a measured completion time or balance is made here.
- Use **three core armour appearances**: Patchwork Travel Coat, Pilgrim
  Leather and Wayfarer Brigandine. Their art is already authored. Pause
  Lanternscale Vest and First Light Plate for new-player progression, retaining
  their IDs, ownership and functionality for existing players.
- Starter gear and the milestone weapon styles must be obtainable without
  buying random stock. Show where the next reward comes from and let the
  player equip it at Home. Do not auto-replace an existing equipped item.
- Keep every verified objective mandatory. Gear can cushion mistakes or alter
  fight tempo but never answer, skip an objective or make one kind of learning
  activity the obvious farming choice.
- Do not introduce a permanent Campaign class in this slice. The equipped
  weapon determines its animation style; the player can change loadout outside
  a fight. Dungeon's class-per-run selection stays unchanged.

## Reward cadence and recognition

Players should feel progress throughout the campaign, especially when their
first successful steps are unfamiliar. Avoid manufacturing urgency with daily
streak pressure, random reward animations, escalating effects or rewards for
opening the app. The pacing below is a design hypothesis, not measured time.

- **Every verified contract:** show one short, specific acknowledgement of
  what the learner built or demonstrated, their existing XP/coins, and a clear
  route back to the project or onward. Prefer one compact result panel over
  several separate popups. Don't claim evidence of a run or experiment that
  was not actually observed.
- **Early steps:** equipment, useful supplies and a first elite milestone give
  tangible rewards close together, so a beginner sees their hunter grow.
- **Later steps:** retain a meaningful reward at every act-ending elite and
  occasional supplies between them. Contracts may become more involved as
  concepts combine, but do not pad tasks or slow rewards artificially. Keep
  acknowledging each completed contract even when gear milestones are spaced
  further apart.
- **Act milestones:** award one modest record for each act-ending elite, based
  on the same server-verified clear: *First Light*, *The Road*, *The Workshop*
  and *The Living Vale*. A compact progression page or existing Home display
  may show these records; they are proposed additions, not existing trophies.
  They acknowledge completed work, not mastery of Python.
- **Boss:** award a visible Unwritten King trophy and a short summary of the
  project completed, alongside the named gear and relic. The trophy is a
  proposed bespoke boss-clear record; check the existing trophy projection
  before designing new storage or art. It is not a generic achievement redirect.
- **Learning access:** never lock Codex explanations, essential help,
  accessibility, or recovery behind rewards. A summary can link to the next
  relevant material; it must not present basic learning access as a prize.

Avoid stacking multiple spectacle moments on a single clear: combine an act
record with its equipment in one receipt, and keep acknowledgement dismissible.
No timer, streak, paid assistance or prior failed attempts affects milestone
eligibility. Existing item effects and supplies still need balance review.

## Proposed reward map

Every row retains its normal verified clear and base XP/coins and receives the
small completion acknowledgement above. “No gear” means no additional
permanent equipment. Fixed consumable quantities are a balance hypothesis;
do not add random replacement loot to fill gaps.

| # | Contract / concept | Proposed reward beyond base XP and coins |
| --- | --- | --- |
| 1 | The First Spark — setup and first run | Grant `lv-01` Trailkeeper Blade and `lv-06` Patchwork Travel Coat on verified clear; introduce Prepare and equip. For an existing loadout, add only missing owned IDs and never switch equipment automatically. |
| 2 | The Nameless Wraith — variables | Grant one `lv-16` Traveler Bread; acknowledge the working variable and show the next milestone. Preserve the player's current equipment. |
| 3 | The Whispering Gate — input | Grant `lv-11` Amber Seed; introduce the trinket slot and explain its existing XP effect. |
| 4 | The Forked Path — branches | Grant one `lv-16` Traveler Bread; explain when and where healing is available. |
| 5 | The Endless Echo — loops, elite | Grant `lv-07` Pilgrim Leather and the proposed First Light act record in one receipt. Keep the existing Echo Break in-fight guard; this milestone is separate and does not replace objectives. |
| 6 | The Little Lantern — functions | Offer a **one-time free choice** of Hunter's Staff (`hunter-sparring-staff`) or Hunter's Whip (`hunter-sparring-whip`). Explain each weapon's actual current effect and animation. The choice must be recorded and recoverable if the panel is closed. |
| 7 | The Inventory Drowner — lists | Grant one Traveler Bread and acknowledge the inventory the learner built. |
| 8 | The Counting Moth — iteration | Grant one Traveler Bread. |
| 9 | The Mapkeeper — dictionaries | No gear. |
| 10 | The Delivery Beast — combined rules, elite | Grant `lv-08` Wayfarer Brigandine and the proposed The Road act record. Keep Delivery Proof's in-fight mechanic. |
| 11 | The Broken Number — exceptions | Grant the **other** staff/whip from the choice at #6. If the player already owns either or both, grant only missing ownership; if #6 was unresolved, surface that choice first and do not silently choose. |
| 12 | The Test Lantern — assertions | Grant one Traveler Bread; acknowledge the verified test work without inferring unobserved runs. |
| 13 | The Module Mason — modules | Grant one `lv-20` Lantern Dew Tonic. Its current 45 HP effect needs economy and max-HP review before shipping. |
| 14 | The Selfless Golem — instances | No gear. |
| 15 | The Clockwork Caravan — composition, elite | Grant `lv-13` Little Beacon Charm and the proposed The Workshop act record; explain the charm's current one starting guard and how it competes with Amber Seed for the trinket slot. Keep Caravan Repair's in-fight mechanic. |
| 16 | The Memory Keeper — JSON | Grant one Traveler Bread; acknowledge the verified persistence work. |
| 17 | The Quiet Flame — pure functions | Grant one Traveler Bread. |
| 18 | The Transformation Sprite — transformations | No gear. |
| 19 | The Remembering Shade — callbacks | No gear. |
| 20 | The Unwritten Road — transfer, elite | Grant one Lantern Dew Tonic and the proposed The Living Vale act record; keep Open Road's existing in-fight mechanic. Make clear the boss still requires all of its own phases. |
| Boss | The Unwritten King — working project, explanation, changed requirements and interview | Guarantee `lv-05` Dawnbringer, `lv-22` Unwritten Crown Fragment and a proposed Unwritten King trophy after all required boss phases. Show exactly what was earned and where it can be equipped or displayed. Preserve PYR's Blessing only if its campaign transition purpose is made clear. |

The map proposes seven breads and two tonics: at their current listed values
that is up to 230 HP of healing before caps or waste. This is a substantial
economy change relative to randomized drops and must be tuned against actual
damage, existing rest rules and the boss; do not simply stack it on top of the
old random supplies. Recognition records are not additional combat bonuses.

This deliberately uses two named trinkets and three core armour pieces. The
starter sword, staff and whip are three distinct weapon styles; Dawnbringer is
proposed as a capstone sword. Its current catalogue entry has no combat-style
mapping, so implementation must explicitly assign a suitable authored sword
animation and ensure its appearance matches. The staff and whip presently have different effects, and the
sword's code-checkpoint bonus is format-specific. **Review those effects before
shipping**: their intended differences must not penalize a learner for the type
of task the campaign requires. The Dawnbringer numbers and the armour's current
10/18/26% reductions are existing values, not approved balance targets. A
boss reward earned at the end of a campaign also needs a useful next destination;
do not claim it improves a fight already completed.

## Market and loot changes required to implement the proposal

1. Add a campaign-owned milestone definition keyed by stable campaign branch,
   contract identity and item ID; boss reward uses its own boss-clear identity.
   Resolve the fixed reward in the same server-side state mutation as the
   verified clear. Do not make frontend receipt or animation the authority.
2. For Lantern Vale only, bypass the generic random contract gear and aid
   rolls; award the listed items/consumables instead. Scope the PYR exception
   to the same campaign. Other campaign pools and Infinite Dungeon logic keep
   their current rules. Any later optional random loot needs an explicit
   separate design and must not duplicate or replace the milestones.
3. Remove planned milestone gear from Lantern Vale's new-player merchant
   stock until earned; purchase must also be rejected server-side, not merely
   hidden. At #6, the unchosen free choice cannot be bought early. Keep useful
   optional supplies separate and review the global Hunter-style shop so it
   cannot bypass the two named weapon milestones. Clearly indicate sources.
4. Make the #6 selection persistent across closing the panel and restarting;
   defer the #11 other-style grant until a selection exists. Grant ownership
   once, without replacing the selected or equipped weapon. If one style was
   already owned, a choice cannot destroy or duplicate it; show what happens.
5. Review whether weapon names, art and animation really match their styles.
   The current catalogue includes a hammer and spear without corresponding
   dedicated animation styles; do not offer them as if such animations exist.
6. Treat named effects above as a proposed reward map, not a balance sign-off.
   Compare damage, guard, HP, heal supply, reward pace and player choices at
   each act and the boss. A guaranteed path must not depend on spending coins.

## Existing saves and implementation boundaries

- Never remove or rename owned IDs, equipped names, weapon IDs, loot, coins,
  XP, trophies, achievements or Dungeon run state. Never automatically equip
  a newly granted milestone item. Old lantern armour remains usable, including
  `lv-09` and `lv-10`, even if it stops dropping for new campaign progress.
- Write a versioned, idempotent entitlement ledger or equivalent server-owned
  reconciliation. For a previously cleared milestone, identify the contract by
  stable campaign identity and award each missing permanent entitlement once;
  preserve any already owned item. Avoid re-granting consumable stacks or
  retroactively altering XP/coins. Handle a completed boss and the unselected
  #6 choice explicitly. Repeated loads, duplicate verification, sync and
  interrupted migrations must not duplicate, lose or overwrite equipment.
- Reconstruct the four act records and boss trophy from verified clear state
  where possible, without replaying a backlog of reward popups. Existing saves
  receive no retroactive bread or tonic stacks. Final storage and reconciliation
  rules must cover these proposed records as well as equipment ownership.
- Campaign gear ownership is currently local while parts of campaign state
  sync. A future implementation must specify where the milestone ledger lives,
  its sync limits and conflict rules before writing migrations. Do not infer
  ownership from an unrelated campaign or from the displayed name alone.
- Do not edit `progress.json` by hand. Develop and exercise any migration with
  disposable saves, including newly started, midway, completed, duplicate
  owned, already equipped, unresolved-choice and synced states. User save
  migration is a separate implementation step, not performed by this audit.

## Recommended delivery order

1. Agree the milestone map and the PYR help exception; inventory actual player
   ownership cases and settle #6/#11's choice behavior.
2. Implement a narrowly scoped Lantern Vale reward table and idempotent
   reconciliation; keep current equipment and unlock paths for other modes.
3. Connect reward source text, selection and receipt UI to server state; make
   the Home loadout understandable without creating a new class screen.
4. Verify the real flow with disposable saves and a beginner playthrough,
   including all 20 contracts, the boss, help, equipment changes, relaunch,
   shop availability and existing-save reconciliation. Measure actual time;
   assess PYR question quality and evidence independently of combat rewards.

The third armour art and these mechanics are a sufficient vertical slice to
evaluate progression. Defer more bespoke armour animation sheets until that
playthrough establishes which additional pieces improve the experience.
