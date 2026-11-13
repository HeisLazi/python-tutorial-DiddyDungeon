import test from 'node:test'
import assert from 'node:assert/strict'
import { makeRaidCombatTurn, raidCombatSummary } from './raidCombatUi.js'

test('raid hit carries settled resolve and boss damage into the combat HUD', () => {
  const turn = makeRaidCombatTurn({
    attack_sequence: 2,
    hp: 10,
    max_hp: 35,
    hunter_hp: { a: 4 },
    last_attack: { type: 'hunter', damage: 15 },
  }, 'raid-1', 'a')

  assert.equal(turn.result.fight.resolve_before, 25)
  assert.equal(turn.result.fight.resolve_after, 10)
  assert.equal(turn.result.fight.chip, 15)
  assert.equal(raidCombatSummary({ result: turn.result, fight: turn.result.fight, turn, raidMode: true }), 'The hunters strike for 15 Resolve.')
})

test('raid team attack reports party damage instead of a guarded hit', () => {
  const turn = makeRaidCombatTurn({
    attack_sequence: 3,
    hp: 10,
    max_hp: 35,
    hunter_hp: { a: 4 },
    last_attack: { type: 'aoe', damage: 1 },
  }, 'raid-1', 'a')

  assert.equal(turn.result.damage, 1)
  assert.equal(raidCombatSummary({ result: turn.result, fight: turn.result.fight, turn, encounter: { name: 'The Choef Chief' }, damage: turn.result.damage, raidMode: true }), 'The Choef Chief hits the whole party for 1 HP each.')
})

test('raid single-target mistake identifies the submitting hunter as the target', () => {
  const turn = makeRaidCombatTurn({
    attack_sequence: 1,
    hp: 35,
    max_hp: 35,
    hunter_hp: { a: 4 },
    last_attack: { type: 'single', damage: 1 },
  }, 'raid-1', 'a')

  assert.equal(raidCombatSummary({ result: turn.result, turn, encounter: { name: 'The Choef Chief' }, damage: turn.result.damage, raidMode: true }), 'The Choef Chief hits the submitting hunter for 1 HP.')
})
