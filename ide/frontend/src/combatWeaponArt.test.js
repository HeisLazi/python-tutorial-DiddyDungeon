import test from 'node:test'
import assert from 'node:assert/strict'
import { combatStyle, combatWeaponVariant } from './combatWeaponArt.js'

test('run and campaign Dawn Lantern use the staff and distinct weapon art', () => {
  for (const name of ['Dawn Lantern', 'Matriarch’s Dawnlight', "Matriarch's Dawnlight"]) {
    assert.equal(combatStyle(name), 'staff')
    assert.equal(combatWeaponVariant(name), 'dawn-lantern')
  }
  assert.equal(combatWeaponVariant('Gravebound Greatblade'), 'graveblade')
  assert.equal(combatWeaponVariant('Aether Staff'), '')
  assert.equal(combatStyle('Aether Staff'), 'staff')
})
