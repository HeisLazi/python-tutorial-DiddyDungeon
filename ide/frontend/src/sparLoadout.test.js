import test from 'node:test'
import assert from 'node:assert/strict'
import { hasPicks, sparDemoTurn, sparGearBySlot, sparLoadout } from './sparLoadout.js'

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

test('gear is grouped by slot and demo turns alternate a landed hit and a taken hit', () => {
  const grouped = sparGearBySlot([hammer, coat, { slot: 'trinket', id: 't' }, { slot: 'food', id: 'f' }])
  assert.deepEqual([grouped.weapon.length, grouped.armor.length, grouped.trinket.length], [1, 1, 1])
  assert.equal(sparDemoTurn(1, true).result.outcome, 'correct')
  assert.equal(sparDemoTurn(2, false).result.damage, 1)
  const mid = sparDemoTurn(3, true, 3, 2)
  assert.deepEqual([mid.hpAfter, mid.result.fight.resolve_before, mid.result.fight.resolve_after], [3, 2, 1])
  assert.equal(sparDemoTurn(4, false, 0, 5).hpAfter, 0)
  assert.notEqual(sparDemoTurn(1, true).result.evidence_id, sparDemoTurn(2, true).result.evidence_id)
})
