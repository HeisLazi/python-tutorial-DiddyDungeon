// Sparring is a simulation, so the Sparring Ring lets a hunter try on any gear in the game.
// `picks` holds only what was changed from the hunter's real gear:
//   picks.weapon  undefined = the equipped weapon, null = bare hands, item = that weapon
//   picks.armor / picks.trinket  undefined = the equipped piece, item = that piece, null = none
//   picks.armorLook / picks.weaponLook  a Colosseum mastery look: undefined = the hunter's own earned look,
//     null = no look, look = that look (cosmetic only: it never changes what the gear does)
// Nothing here touches the save: the result only feeds the combat scene and the practice fight.
import { hunterAppearance } from './hunterEquipment.js'

export const SPAR_SLOTS = ['weapon', 'armor', 'trinket']
const PICK_KEYS = [...SPAR_SLOTS, 'armorLook', 'weaponLook']

export const hasPicks = (picks = {}) => PICK_KEYS.some((key) => picks[key] !== undefined)

// The combat scene only paints an armour mastery look on the base Tate outfit; the other outfits show as they are.
const BASE_OUTFIT_LOOKS = new Set(['classic', 'steel', 'ember', 'arcane'])
export const armorLookShows = (armorName) => BASE_OUTFIT_LOOKS.has(hunterAppearance(armorName).armorLook)

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
  // Colosseum mastery looks belong to the hunter's own gear. Trying something else on shows that gear as it is,
  // unless a look is picked on purpose. A weapon look only fits its own weapon style.
  const keepsArmorLook = picks.armor === undefined || sameName(picks.armor?.name, equipped.armor)
  const keepsWeaponLook = picks.weapon === undefined || (picks.weapon && picks.weapon.id === armory?.weapon?.id)
  const weaponStyle = weaponItem?.combat_style
  const armorTier = picks.armorLook !== undefined ? picks.armorLook?.tier || '' : keepsArmorLook ? looks.armor?.tier || '' : ''
  const weaponLook = picks.weaponLook !== undefined ? picks.weaponLook : keepsWeaponLook ? looks.weapon : null
  return {
    weapon: weaponItem?.name || 'Bare hands',
    weapon_id: weaponItem?.id || '',
    weapon_style: weaponItem?.combat_style || 'unarmed',
    armor,
    trinket,
    armor_mastery: armorTier,
    weapon_mastery: weaponLook && weaponLook.style === weaponStyle ? weaponLook.tier || '' : '',
    visual_unavailable: Boolean(weaponItem && !weaponItem.combat_style),
    ...extra,
  }
}

// The fight in numbers. `sim` is the server's replay of the answered rounds with the tried-on gear
// (POST /api/spar/simulate); `history` is [{ correct, kind }] for each answered round. Before the server has
// answered (or if it cannot), the bars fall back to the plain one-point-a-round fight.
export const SPAR_ROUNDS = 5

export function boutState(sim, history = [], count = history.length) {
  if (sim?.rounds) {
    // A reply for fewer rounds than are now answered is still the best known state; show it until the next one lands.
    const n = Math.min(count, sim.rounds.length)
    const at = n === 0 ? { ...sim.start, damage: 0, impact: 0, fired: [] } : sim.rounds[n - 1]
    return { hp: at.hp, resolve: at.resolve, guards: at.guards ?? 0, maxHp: sim.max_hp, maxResolve: sim.max_resolve, damage: at.damage || 0, impact: at.impact || 0, fired: at.fired || [], guardBroken: Boolean(at.guard_broken) }
  }
  const shown = history.slice(0, count)
  const hits = shown.filter((round) => round.correct).length
  const last = shown[shown.length - 1]
  return { hp: Math.max(0, SPAR_ROUNDS - (shown.length - hits)), resolve: Math.max(0, SPAR_ROUNDS - hits), guards: 0, maxHp: SPAR_ROUNDS, maxResolve: SPAR_ROUNDS, damage: last && !last.correct ? 1 : 0, impact: last?.correct ? 1 : 0, fired: [], guardBroken: false }
}

// What the combat scene and bars show: the state before the latest answer, and the exchange that follows it
// once an answer has been given (`answered`). `ready` is false while a newer replay is still on its way.
export function sparView(sim, history, { answered = false, evidenceId = 'spar', ready = true } = {}) {
  const count = history.length
  if (!answered || count === 0) {
    const now = boutState(sim, history, count)
    return { ...now, hpBefore: now.hp, resolveBefore: now.resolve, turn: null }
  }
  const before = boutState(sim, history, count - 1)
  const after = boutState(sim, history, count)
  const landed = Boolean(history[count - 1].correct)
  const turn = ready ? {
    hpAfter: after.hp,
    result: {
      evidence_id: evidenceId, outcome: landed ? 'correct' : 'incorrect', damage: after.damage,
      fight: { chip: landed ? Math.max(1, after.impact) : 0, max_resolve: after.maxResolve, resolve_before: before.resolve, resolve_after: after.resolve },
    },
  } : null
  return { ...after, hpBefore: before.hp, resolveBefore: before.resolve, turn }
}

// The server wants one flat description of the loadout.
export const sparLoadoutRequest = (loadout) => ({ weapon_id: loadout.weapon_id || null, armor: loadout.armor || null, trinket: loadout.trinket && loadout.trinket !== 'None' ? loadout.trinket : null })
