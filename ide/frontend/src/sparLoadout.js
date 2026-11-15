// Sparring is a simulation, so the Sparring Ring lets a hunter try on any gear in the game.
// `picks` holds only what was changed from the hunter's real gear:
//   picks.weapon  undefined = the equipped weapon, null = bare hands, item = that weapon
//   picks.armor / picks.trinket  undefined = the equipped piece, item = that piece, null = none
// Nothing here touches the save: the result only feeds the combat scene.

export const SPAR_SLOTS = ['weapon', 'armor', 'trinket']

export const hasPicks = (picks = {}) => SPAR_SLOTS.some((slot) => picks[slot] !== undefined)

// Weapons first, then armour, then trinkets; each list keeps the server's tier order.
export function sparGearBySlot(gear = []) {
  const grouped = { weapon: [], armor: [], trinket: [] }
  for (const item of gear) if (grouped[item?.slot]) grouped[item.slot].push(item)
  return grouped
}

const sameName = (a, b) => String(a || '').trim().toLowerCase() === String(b || '').trim().toLowerCase()

export function sparLoadout(armory, picks = {}, extra = {}) {
  const equipped = armory?.equipped || {}
  const weaponItem = picks.weapon === undefined ? armory?.weapon || null : picks.weapon
  const armor = picks.armor === undefined ? equipped.armor : picks.armor?.name || 'Apprentice Coat'
  const trinket = picks.trinket === undefined ? equipped.trinket : picks.trinket?.name || 'None'
  const looks = armory?.equipped_appearances || {}
  // Colosseum mastery looks belong to the hunter's own gear. Trying something else on shows that gear as it is.
  const keepsArmorLook = picks.armor === undefined || sameName(picks.armor?.name, equipped.armor)
  const keepsWeaponLook = picks.weapon === undefined || (picks.weapon && picks.weapon.id === armory?.weapon?.id)
  return {
    weapon: weaponItem?.name || 'Bare hands',
    weapon_id: weaponItem?.id || '',
    weapon_style: weaponItem?.combat_style || 'unarmed',
    armor,
    trinket,
    armor_mastery: keepsArmorLook ? looks.armor?.tier || '' : '',
    weapon_mastery: keepsWeaponLook && looks.weapon?.style === weaponItem?.combat_style ? looks.weapon?.tier || '' : '',
    visual_unavailable: Boolean(weaponItem && !weaponItem.combat_style),
    ...extra,
  }
}

// A made-up exchange for the "test swing" and "take a hit" buttons: one hit lands, or one is taken.
// It starts from the bout's current hit points and resolve so the bars do not jump mid-fight.
export function sparDemoTurn(count, landed, hp = 5, resolve = 5) {
  return {
    hpAfter: landed ? hp : Math.max(0, hp - 1),
    result: {
      evidence_id: `gear-demo-${count}`,
      outcome: landed ? 'correct' : 'incorrect',
      damage: landed ? 0 : 1,
      fight: { chip: landed ? 1 : 0, max_resolve: 5, resolve_before: resolve, resolve_after: landed ? Math.max(0, resolve - 1) : resolve },
    },
  }
}
