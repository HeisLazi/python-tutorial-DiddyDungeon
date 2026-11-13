# Campaign loot

This describes the implemented campaign drop rules in the feature worktree.
It supersedes the fixed contract reward table in
`LANTERN_VALE_PROGRESSION_AUDIT.md` and the interactive story proposal in
`LANTERN_VALE_STORY_DESIGN.md`. Campaign objectives and Infinite Dungeon's
run loot remain separate.

- Normal campaign contracts roll campaign equipment or consumables. The
  existing tier/depth weights remain in place.
- Each authored elite has its own named, permanent trinket. An elite also
  awards one Ember for Home upgrades and has a 35% chance to award an
  additional unowned campaign weapon or armour piece. Existing optional aid
  drops remain separate. Named elite trinkets use existing object icons as
  placeholders until they have bespoke art.
- Campaign bosses award their fixed weapon, armour and relic, plus two Embers
  and the existing PYR's Blessing. Bosses do not award trinkets. The casino
  boss's weapon remains Oil of Doom and Despair. The other three use their
  existing campaign legendary weapons and armour; their weapon styles are
  mapped to available animations. Existing item names, effects and visuals
  remain in place; not all armour has its own bespoke character sprites yet.
- Lantern Vale help does not reduce fight XP, coins or loot and does not spend
  free-ask charges. Elsewhere PYR's existing XP/coin cost remains; named elite
  loot and Embers are protected from the two-ask ordinary loot penalty.
- Existing saves retain their equipment. Named elite trinkets and fixed boss
  gear can be inferred from individual recorded clears, shown in the Armory
  and made permanent when equipped; earned boss relics also apply passively.
  No Ember or consumable balance is backfilled. If an old synced completed
  campaign no longer contains individual mob records, do not infer which elite
  clears occurred from completion alone. A boss-clear record still grants the
  corresponding boss gear.

The fixed boss gear is listed in `CAMPAIGN_BOSS_GEAR`, while the named
keepsakes are listed in `CAMPAIGN_ELITE_TRINKETS` in `ide/server/state.py`.
Each elite and boss clear is recorded by the existing verified progression
flow, so no reward is awarded for simply opening an encounter.
