import test from 'node:test'
import assert from 'node:assert/strict'
import { combatEnemyArt } from './combatEnemyArt.js'

test('matches actual Basics Village encounter and boss names', () => {
  assert.equal(combatEnemyArt('The Nameless Wraith'), 'wraith')
  assert.equal(combatEnemyArt('The String Mimic'), 'string-mimic')
  assert.equal(combatEnemyArt('Elder String Mimic'), 'string-mimic')
  assert.equal(combatEnemyArt('The Forked Path'), 'forked-path')
  assert.equal(combatEnemyArt('Elder Forked Path'), 'forked-path')
  assert.equal(combatEnemyArt('The Mimic Matriarch'), 'mimic-matriarch')
})

test('unknown foes use the placeholder without pretending to be a known species', () => {
  assert.equal(combatEnemyArt('The Drowned Hoard'), 'wraith')
  assert.equal(combatEnemyArt(null), 'wraith')
})
