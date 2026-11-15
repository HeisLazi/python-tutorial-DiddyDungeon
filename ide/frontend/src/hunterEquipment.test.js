import { test } from 'node:test'
import assert from 'node:assert/strict'
import { hunterAppearance } from './hunterEquipment.js'

test('appearance and companion follow equipped armour rather than a separate setting', () => {
  assert.deepEqual(hunterAppearance('Ivory Revel Suit', 'Pink Cap Charm'), { armorLook: 'ivory', homeLook: 'ivory', trinketLook: 'pink', trinketIcon: 'pink-cap', pet: 'oil' })
  assert.equal(hunterAppearance('', 'Soul Lantern').trinketIcon, 'soul-lantern')
  assert.equal(hunterAppearance('', 'Jacklight Charm').trinketIcon, 'jacklight')
  assert.equal(hunterAppearance('', 'Loop Lens').trinketIcon, 'none')
  assert.equal(hunterAppearance('Gravebound Warden Plate', 'None').armorLook, 'spectral')
  assert.equal(hunterAppearance('Harvest Revenant Coat', '').armorLook, 'harvest')
  assert.equal(hunterAppearance('Debugger Plate', '').armorLook, 'debugger')
  // The Merchant's coats are recolours of the road outfits, each with its own look; Home shows the outfit they share.
  assert.deepEqual([hunterAppearance('Merchant Patchwork Coat', '').armorLook, hunterAppearance('Merchant Patchwork Coat', '').homeLook], ['merchantpatchwork', 'patchwork'])
  assert.deepEqual([hunterAppearance('Merchant Pilgrim Leather', '').armorLook, hunterAppearance('Merchant Pilgrim Leather', '').homeLook], ['merchantpilgrim', 'pilgrim'])
  assert.deepEqual([hunterAppearance('Merchant Wayfarer Brigandine', '').armorLook, hunterAppearance('Merchant Wayfarer Brigandine', '').homeLook], ['merchantwayfarer', 'wayfarer'])
  assert.equal(hunterAppearance('Merchant Oracle Mantle', '').armorLook, 'merchant-oracle')
  assert.equal(hunterAppearance('Lanternkeeper’s Coat', '').armorLook, 'lanternkeeper')
  assert.equal(hunterAppearance('Wayfarer’s Wardplate', '').armorLook, 'wardplate')
  assert.equal(hunterAppearance('Lantern Coat', '').armorLook, 'lanternkeeper')
  assert.equal(hunterAppearance('Pilgrim Ward', '').armorLook, 'wardplate')
  assert.equal(hunterAppearance('Apprentice Coat', '').pet, 'none')
})

// Every armour in the Home armory (see docs/ARMOUR_IDENTITIES.md) must look different in combat.
const ARMOURS = ["Patchwork Travel Coat", "Pilgrim Leather", "Wayfarer Brigandine", "Lanternscale Vest", "First Light Plate", "Dealer's Waistcoat", "Velvet Felt Jacket", "Pit Boss Coat", "Gilded Lapel Armour", "The High Roller's Mail", "Doorman's Livery", "Silver Sequin Vest", "Auditor's Waistcoat", "Vault Guard Plate", "The Fortune Mail", "Canvas Mining Smock", "Riveted Leather", "Deepvein Brigandine", "Lamp-Lit Lamellar", "The Core-Forged Plate", "Ivory Revel Suit", "Gravebound Warden Plate", "Harvest Revenant Coat", "Merchant Patchwork Coat", "Merchant Pilgrim Leather", "Merchant Wayfarer Brigandine", "Merchant Oracle Mantle", "Lanternbound Coat", "Drowned Mail", "Flowkeeper Plate", "Norse Mail", "Lanternkeeper’s Coat", "Wayfarer’s Wardplate"]

test('no two armours share a combat look', () => {
  const looks = ARMOURS.map((name) => hunterAppearance(name, '').armorLook)
  const repeated = looks.filter((look, index) => looks.indexOf(look) !== index)
  assert.deepEqual(repeated, [], 'two armours show the same outfit in combat')
  assert.equal(new Set(looks).size, ARMOURS.length)
})

test('the Home scene always gets an outfit it has art for', () => {
  const known = new Set(['classic', 'ivory', 'spectral', 'harvest', 'oracle', 'patchwork', 'pilgrim', 'wayfarer', 'norse', 'lanternkeeper', 'wardplate', 'debugger', 'merchant-oracle', 'arcane', 'steel', 'ember'])
  for (const name of ARMOURS) assert.ok(known.has(hunterAppearance(name, '').homeLook), `${name} -> ${hunterAppearance(name, '').homeLook}`)
})

// Every trinket in the Home armory (docs/TRINKET_IDENTITIES.md) is worn on the hero as a charm of its own.
const TRINKETS = ["Amber Seed", "Traveler Compass", "Little Beacon Charm", "Mira Road Badge", "Heart of the Vale", "Lucky Chip", "Marked Card", "Counting Abacus", "Mara's Pocket Watch", "The Gilded Ace", "Silver Dollar", "Weighted Die", "Auditor's Ledger", "Four-Leaf Clip", "The Probability Lens", "Canary Feather", "Compass Needle", "Ore Sniffer Charm", "Brigid's Hard Hat Badge", "The Heart of the Mine", "Pink Cap Charm", "Soul Lantern", "Jacklight Charm", "Delver's Village Lantern", "Delver's Pilgrim Knot", "Delver's Warm Ember", "Delver's Tidal Pearl", "Delver's Cave Shell", "Delver's Hoard Token", "Delver's Loop Thread", "Delver's Still Clock", "Delver's Keeper’s Ring", "Delver's Ink Seal", "Delver's Book Clasp", "Delver's Quiet Page", "Delver's Thread Spool", "Delver's Stone Eye", "Delver's Bull Ring", "Delver's Copper Spring", "Delver's Brass Gear", "Delver's Tuning Fork", "Delver's Oracle Lens", "Delver's Star Thread", "Delver's Warding Star", "Delver's Ash Talisman", "Delver's Spectral Chain", "Delver's Ember Heart", "Delver's Last Spark", "Cinder Vow", "Pale Guard Locket", "Last Laugh Charm", "Echo Knot", "Delivery Seal", "Caravan Gear", "Open Road Token", "Debt Ghoul Token", "Greed Spirit’s Coin", "Balancer’s Weight", "Front Door Key", "Seeded Maze Knot", "Star Seeker’s Lens", "Context Keeper’s Seal", "Lantern Keeper’s Wick", "Inquisitor’s Sigil"]

test('every trinket is worn as its own charm in combat', () => {
  const icons = TRINKETS.map((name) => hunterAppearance('', name).trinketIcon)
  assert.equal(icons.filter((icon) => icon === 'none').length, 0, 'a trinket has no worn charm')
  assert.equal(new Set(icons).size, TRINKETS.length, 'two trinkets share a worn charm')
})

test('a trinket without a worn charm shows nothing rather than a stand-in', () => {
  assert.equal(hunterAppearance('', 'Loop Lens').trinketIcon, 'none')
  assert.equal(hunterAppearance('', 'None').trinketIcon, 'none')
})
