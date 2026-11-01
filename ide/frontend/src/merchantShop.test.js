import { test } from 'node:test'
import assert from 'node:assert/strict'
import { merchantLots } from './merchantShop.js'

test('combines the two inventories while retaining ownership, prices, and purchase sources', () => {
  const lots = merchantLots([{ id: 'blade', slot: 'weapon', affordable: true, price: 40 }], [
    { id: 'ward', name: 'Ward', kind: 'Trinket', detail: 'Blocks a hit', price: 48 },
    { id: 'coat', name: 'Coat', kind: 'Armor', detail: 'Protection', price: 80 },
  ], ['ward'], 50)
  assert.equal(lots[0].source, 'armory')
  assert.deepEqual([lots[1].source, lots[1].owned, lots[1].affordable, lots[1].effect], ['merchant', true, false, 'Blocks a hit'])
  assert.deepEqual([lots[2].slot, lots[2].owned, lots[2].affordable, lots[2].price], ['armor', false, false, 80])
})


test('unlocked items precede locked items from either inventory', () => {
  const lots = merchantLots([{ id: 'locked', locked: 'Complete a campaign' }, { id: 'open', locked: null }], [{ id: 'classic', name: 'Classic', kind: 'Supply', price: 10 }], [], 20)
  assert.deepEqual(lots.map((item) => item.id), ['open', 'classic', 'locked'])
})
