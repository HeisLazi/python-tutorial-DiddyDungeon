import test from 'node:test'
import assert from 'node:assert/strict'
import { armorLookShows, boutState, hasPicks, sparGearBySlot, sparLoadout, sparLoadoutRequest, sparView } from './sparLoadout.js'

const armory = {
  weapon: { id: 'lv-01', name: 'Trailkeeper Blade', combat_style: 'sword' },
  equipped: { weapon: 'lv-01', armor: 'Wayfarer’s Wardplate', trinket: 'None' },
  equipped_appearances: { armor: { id: 'a', tier: 'gold' }, weapon: { id: 'w', tier: 'silver', style: 'sword' } },
}
const hammer = { id: 'cas-jackpot-hammer', name: 'Jackpot Hammer', slot: 'weapon', combat_style: 'greatsword' }
const coat = { id: 'x', name: 'Lanternkeeper’s Coat', slot: 'armor' }

test('without picks the hunter fights in their own gear and mastery looks', () => {
  const loadout = sparLoadout(armory)
  assert.deepEqual(
    [loadout.weapon, loadout.weapon_id, loadout.weapon_style, loadout.armor, loadout.trinket],
    ['Trailkeeper Blade', 'lv-01', 'sword', 'Wayfarer’s Wardplate', 'None'],
  )
  assert.deepEqual([loadout.armor_mastery, loadout.weapon_mastery], ['gold', 'silver'])
  assert.equal(hasPicks({}), false)
})

test('trying a weapon uses its id and style, and drops a mastery look that is not its own', () => {
  const loadout = sparLoadout(armory, { weapon: hammer })
  assert.deepEqual([loadout.weapon, loadout.weapon_id, loadout.weapon_style], ['Jackpot Hammer', 'cas-jackpot-hammer', 'greatsword'])
  assert.equal(loadout.weapon_mastery, '')
  assert.equal(loadout.armor_mastery, 'gold') // armour was not touched
  assert.equal(hasPicks({ weapon: hammer }), true)
})

test('picking the equipped weapon again keeps its mastery look', () => {
  assert.equal(sparLoadout(armory, { weapon: armory.weapon }).weapon_mastery, 'silver')
})

test('a mastery look for another weapon style never rides on a different weapon', () => {
  const other = { ...armory, equipped_appearances: { weapon: { tier: 'silver', style: 'staff' } } }
  assert.equal(sparLoadout(other).weapon_mastery, '')
})

test('trying armour and a trinket changes the look; none means bare hands, no coat, no charm', () => {
  const loadout = sparLoadout(armory, { armor: coat, trinket: { name: 'Pink Cap' } })
  assert.deepEqual([loadout.armor, loadout.trinket, loadout.armor_mastery], ['Lanternkeeper’s Coat', 'Pink Cap', ''])
  const bare = sparLoadout(armory, { weapon: null, armor: null, trinket: null })
  assert.deepEqual([bare.weapon, bare.weapon_id, bare.weapon_style, bare.armor, bare.trinket], ['Bare hands', '', 'unarmed', 'Apprentice Coat', 'None'])
})

test('a weapon with no combat style is flagged so the scene can say so', () => {
  assert.equal(sparLoadout(armory, { weapon: { id: 'q', name: 'Odd Thing', combat_style: null } }).visual_unavailable, true)
})

test('gear is grouped by slot', () => {
  const grouped = sparGearBySlot([hammer, coat, { slot: 'trinket', id: 't' }, { slot: 'food', id: 'f' }])
  assert.deepEqual([grouped.weapon.length, grouped.armor.length, grouped.trinket.length], [1, 1, 1])
})

test('a picked mastery look overrides the hunter’s own, and a weapon look only fits its own style', () => {
  const silver = { id: 'sw', tier: 'legendary', style: 'greatsword' }
  const armorLook = { id: 'ar', tier: 'ethereal', appearance_type: 'armor' }
  const looked = sparLoadout(armory, { weapon: hammer, weaponLook: silver, armorLook })
  assert.deepEqual([looked.weapon_mastery, looked.armor_mastery], ['legendary', 'ethereal'])
  // The same look on a different weapon style does nothing.
  assert.equal(sparLoadout(armory, { weaponLook: silver }).weapon_mastery, '')
  // "No look" clears even the hunter's own earned one.
  const none = sparLoadout(armory, { weaponLook: null, armorLook: null })
  assert.deepEqual([none.weapon_mastery, none.armor_mastery], ['', ''])
  assert.equal(hasPicks({ armorLook }), true)
  assert.equal(hasPicks({ weaponLook: null }), true)
})

test('armour looks only show on the base outfit, as in the combat scene', () => {
  for (const name of ['Apprentice Coat', 'Cobalt Plate', 'Oracle Robe', undefined]) assert.equal(armorLookShows(name), true, String(name))
  for (const name of ['Ivory Revel Suit', 'Norse Mail', 'Lanternkeeper’s Coat', 'Wayfarer’s Wardplate']) assert.equal(armorLookShows(name), false, name)
})

test('the replay request is flat: ids for the weapon, names for armour and trinket, null for nothing', () => {
  assert.deepEqual(sparLoadoutRequest(sparLoadout(armory)), { weapon_id: 'lv-01', armor: 'Wayfarer’s Wardplate', trinket: null })
  assert.deepEqual(sparLoadoutRequest(sparLoadout(armory, { weapon: null })), { weapon_id: null, armor: 'Wayfarer’s Wardplate', trinket: null })
})

const sim = {
  max_hp: 20, max_resolve: 12, start: { hp: 20, resolve: 12, guards: 1 },
  rounds: [
    { correct: true, hp: 20, resolve: 8, damage: 0, impact: 4, guards: 1, fired: ['Heavy blow +2'] },
    { correct: false, hp: 17, resolve: 8, damage: 3, impact: 0, guards: 1, fired: ['Armour −1'] },
  ],
}
const history = [{ correct: true, kind: 'choice' }, { correct: false, kind: 'code' }]

test('bout state reads the replay, and clamps to it while a newer one is on its way', () => {
  assert.deepEqual([boutState(sim, history, 0).hp, boutState(sim, history, 0).guards], [20, 1])
  assert.deepEqual([boutState(sim, history, 2).hp, boutState(sim, history, 2).resolve], [17, 8])
  const grown = [...history, { correct: true, kind: 'text' }]
  assert.equal(boutState(sim, grown, 3).hp, 17) // still the last known state, not a jump to the plain fight
  assert.deepEqual([boutState(sim, grown, 3).maxHp, boutState(sim, grown, 3).maxResolve], [20, 12])
})

test('without a replay the bars fall back to the plain one-point fight', () => {
  const state = boutState(null, history)
  assert.deepEqual([state.hp, state.resolve, state.maxHp, state.damage], [4, 4, 5, 1])
})

test('the view shows the state before the latest answer and the exchange it caused', () => {
  const view = sparView(sim, history, { answered: true, evidenceId: 'b-1' })
  assert.deepEqual([view.hpBefore, view.resolveBefore, view.turn.hpAfter], [20, 8, 17])
  assert.deepEqual([view.turn.result.outcome, view.turn.result.damage, view.turn.result.evidence_id], ['incorrect', 3, 'b-1'])
  assert.deepEqual([view.turn.result.fight.resolve_before, view.turn.result.fight.resolve_after], [8, 8])
  assert.deepEqual(view.fired, ['Armour −1'])
  const hit = sparView(sim, history.slice(0, 1), { answered: true })
  assert.deepEqual([hit.turn.result.outcome, hit.turn.result.fight.resolve_before, hit.turn.result.fight.resolve_after], ['correct', 12, 8])
  assert.equal(sparView(sim, history, { answered: false }).turn, null)
  assert.equal(sparView(sim, history, { answered: true, ready: false }).turn, null) // wait for the matching replay
  assert.equal(sparView(sim, [], { answered: true }).turn, null)
})
