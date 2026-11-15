import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hunterAppearance } from './hunterEquipment.js'

test('appearance and companion follow equipped armour rather than a separate setting', () => {
  assert.deepEqual(hunterAppearance('Ivory Revel Suit', 'Pink Cap Charm'), { armorLook: 'ivory', trinketLook: 'pink', trinketIcon: 'pink-cap', pet: 'oil' })
  assert.equal(hunterAppearance('', 'Soul Lantern').trinketIcon, 'soul-lantern')
  assert.equal(hunterAppearance('', 'Jacklight Charm').trinketIcon, 'jacklight')
  assert.equal(hunterAppearance('', 'Loop Lens').trinketIcon, 'none')
  assert.equal(hunterAppearance('Gravebound Warden Plate', 'None').armorLook, 'spectral')
  assert.equal(hunterAppearance('Harvest Revenant Coat', '').armorLook, 'harvest')
  assert.equal(hunterAppearance('Debugger Plate', '').armorLook, 'debugger')
  assert.equal(hunterAppearance('Merchant Patchwork Coat', '').armorLook, 'patchwork')
  assert.equal(hunterAppearance('Merchant Pilgrim Leather', '').armorLook, 'pilgrim')
  assert.equal(hunterAppearance('Merchant Wayfarer Brigandine', '').armorLook, 'wayfarer')
  assert.equal(hunterAppearance('Merchant Oracle Mantle', '').armorLook, 'merchant-oracle')
  assert.equal(hunterAppearance('Lanternkeeper’s Coat', '').armorLook, 'lanternkeeper')
  assert.equal(hunterAppearance('Wayfarer’s Wardplate', '').armorLook, 'wardplate')
  assert.equal(hunterAppearance('Lantern Coat', '').armorLook, 'lanternkeeper')
  assert.equal(hunterAppearance('Pilgrim Ward', '').armorLook, 'wardplate')
  assert.equal(hunterAppearance('Apprentice Coat', '').pet, 'none')
})
