"""Run-only Dungeon equipment. Effects never alter or answer learning tasks."""

# Eight regional signature weapons come from floor bosses, not the shop.
WEAPONS = (
    ('basics', 'dawn-lantern', 'Dawn Lantern', 'staff', 'First correct answer deals +2 Resolve; breaking Resolve restores 2 HP.', {'chip_first': 2, 'heal_break': 2}),
    ('collections', 'undertow-scythe', 'Undertow Scythe', 'scythe', 'Stores damage taken from wrong answers (up to 10); your next correct answer adds it to Resolve damage.', {'damage_bank': 10}),
    ('flow', 'warden-chain', 'Warden Chain', 'whip', 'Clean follow-up answers deal +2 Resolve; enemy mechanics take one extra answer to trigger.', {'chip_follow': 2, 'mechanic_delay': 1}),
    ('archive', 'last-page', 'The Last Page', 'handmagic', 'Once per run, survive a lethal hit with 25% of maximum HP.', {'revive_once': 25}),
    ('labyrinth', 'minotaur-edge', 'Minotaur Edge', 'greatsword', 'Correct answers deal +3 Resolve while at or below half HP.', {'chip_low': 3}),
    ('workshop', 'clockwork-greatblade', 'Clockwork Greatblade', 'greatsword', 'Correcting an answer after a mistake deals +3 Resolve.', {'chip_retry': 3}),
    ('spire', 'oracle-staff', 'Oracle Staff', 'staff', 'Clean answers deal +2 Resolve.', {'chip_clean': 2}),
    ('hollow', 'hollow-fang', 'Hollow Fang', 'sword', 'Breaking Resolve restores 5 HP and awards 3 extra run coins.', {'heal_break': 5, 'break_coins': 3}),
)

# Armour is offered only by its region's run market.
ARMOURS = (
    ('basics', 'lantern-coat', 'Lantern Coat', 85, 'Reduce damage from each failed answer by 2.', {'damage_flat': 2}),
    ('basics', 'pilgrim-ward', 'Pilgrim Ward', 120, 'The first failed answer each floor deals half damage.', {'damage_first_floor': 50}),
    ('collections', 'divers-mail', 'Diver’s Mail', 105, 'Reduce damage from each failed answer by 3.', {'damage_flat': 3}),
    ('collections', 'shellguard', 'Shellguard', 145, 'The first mistake in each fight deals 4 less damage.', {'damage_first_fight': 4}),
    ('flow', 'keeper-plate', 'Keeper Plate', 140, 'Reduce damage from each failed answer by 4.', {'damage_flat': 4}),
    ('archive', 'inkwoven-robe', 'Inkwoven Robe', 135, 'The first failed answer each floor deals half damage.', {'damage_first_floor': 50}),
    ('labyrinth', 'bullhide', 'Bullhide', 160, 'Reduce damage from failed answers by 5 at or below half HP.', {'damage_low': 5}),
    ('workshop', 'clockwork-mail', 'Clockwork Mail', 165, 'Reduce damage from each failed answer by 4.', {'damage_flat': 4}),
    ('spire', 'oracle-mantle', 'Oracle Mantle', 170, 'The first mistake in each fight deals 5 less damage.', {'damage_first_fight': 5}),
    ('hollow', 'hollow-carapace', 'Hollow Carapace', 190, 'Reduce damage from each failed answer by 5.', {'damage_flat': 5}),
    ('hollow', 'last-light-vest', 'Last Light Vest', 240, 'Once per run, survive a lethal hit with 25% of maximum HP.', {'revive_once': 25}),
)

# Region-specific trinkets are awarded by elites; each has a clear combat role.
TRINKETS = (
    ('basics', 'village-lantern', 'Village Lantern', 'First correct answer deals +1 Resolve.', {'chip_first': 1}),
    ('basics', 'pilgrim-knot', 'Pilgrim Knot', 'First mistake in each fight deals 2 less damage.', {'damage_first_fight': 2}),
    ('basics', 'warm-ember', 'Warm Ember', 'Restore 2 HP when you break Resolve.', {'heal_break': 2}),
    ('collections', 'tidal-pearl', 'Tidal Pearl', 'Correcting a mistaken answer deals +1 Resolve.', {'chip_retry': 1}),
    ('collections', 'cave-shell', 'Cave Shell', 'Reduce damage from each failed answer by 1.', {'damage_flat': 1}),
    ('collections', 'hoard-token', 'Hoard Token', 'Gain 2 extra run coins when you break Resolve.', {'break_coins': 2}),
    ('flow', 'loop-thread', 'Loop Thread', 'Clean follow-up answers deal +1 Resolve.', {'chip_follow': 1}),
    ('flow', 'still-clock', 'Still Clock', 'Enemy mechanics take one extra answer to trigger.', {'mechanic_delay': 1}),
    ('flow', 'keepers-ring', 'Keeper’s Ring', 'First correct answer deals +1 Resolve.', {'chip_first': 1}),
    ('archive', 'ink-seal', 'Ink Seal', 'Clean answers deal +1 Resolve.', {'chip_clean': 1}),
    ('archive', 'book-clasp', 'Book Clasp', 'The first failed answer each floor deals 25% less damage.', {'damage_first_floor': 25}),
    ('archive', 'quiet-page', 'Quiet Page', 'Restore 1 HP after each clean answer.', {'heal_clean': 1}),
    ('labyrinth', 'thread-spool', 'Thread Spool', 'Correct answers against elites deal +1 Resolve.', {'chip_elite': 1}),
    ('labyrinth', 'stone-eye', 'Stone Eye', 'Reduce failed-answer damage by 2 at or below half HP.', {'damage_low': 2}),
    ('labyrinth', 'bull-ring', 'Bull Ring', 'Correct answers at or below half HP deal +1 Resolve.', {'chip_low': 1}),
    ('workshop', 'copper-spring', 'Copper Spring', 'Correcting a mistaken answer deals +1 Resolve.', {'chip_retry': 1}),
    ('workshop', 'brass-gear', 'Brass Gear', 'First mistake in each fight deals 3 less damage.', {'damage_first_fight': 3}),
    ('workshop', 'tuning-fork', 'Tuning Fork', 'Gain 2 extra run coins when you break Resolve.', {'break_coins': 2}),
    ('spire', 'oracle-lens', 'Oracle Lens', 'Clean answers deal +1 Resolve.', {'chip_clean': 1}),
    ('spire', 'star-thread', 'Star Thread', 'Restore 1 HP after each clean answer.', {'heal_clean': 1}),
    ('spire', 'warding-star', 'Warding Star', 'The first failed answer each floor deals 25% less damage.', {'damage_first_floor': 25}),
    ('hollow', 'ash-talisman', 'Ash Talisman', 'Correct answers against bosses deal +1 Resolve.', {'chip_boss': 1}),
    ('hollow', 'spectral-chain', 'Spectral Chain', 'Enemy mechanics take one extra answer to trigger.', {'mechanic_delay': 1}),
    ('hollow', 'ember-heart', 'Ember Heart', 'Restore 2 HP when you break Resolve.', {'heal_break': 2}),
    ('hollow', 'last-spark', 'Last Spark', 'Once per run, survive a lethal hit with 15% of maximum HP.', {'revive_once': 15}),
)


def _item(region, slug, name, kind, description, effect, **extra):
    return {'id': f'dungeon-{slug}', 'name': name, 'kind': kind, kind: name,
            'description': description, 'region': region, 'effects': effect, **extra}

SIGNATURE_WEAPONS = tuple(_item(region, slug, name, 'weapon', description, effects, style=style)
                          for region, slug, name, style, description, effects in WEAPONS)
REGIONAL_ARMOURS = tuple(_item(region, slug, name, 'armor', description, effects, price=price)
                         for region, slug, name, price, description, effects in ARMOURS)
REGIONAL_TRINKETS = tuple(_item(region, slug, name, 'trinket', description, effects)
                          for region, slug, name, description, effects in TRINKETS)
GEAR_BY_NAME = {item['name']: item for item in (*SIGNATURE_WEAPONS, *REGIONAL_ARMOURS, *REGIONAL_TRINKETS)}
