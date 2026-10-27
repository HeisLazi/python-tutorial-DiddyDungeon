import test from 'node:test'
import assert from 'node:assert/strict'
import { projectPlayerState } from './syncEngine.js'

const levels = { great_hall: 3, library: 1, armory: 3, pantry: 0, gallery: 0, war_room: 0, den: 1 }

test('Home levels, Embers and legacy upgrades survive the cloud projection', () => {
  const projection = projectPlayerState({ homestead: {
    room_levels: levels, upgrade_tokens: 86, room_upgrades: ['reinforced-hearth'],
    upgrade_effects: { max_hp_delta: 10 }, market_purchases: ['loop-lens'],
  } })
  assert.deepEqual(projection.homestead.room_levels, levels)
  assert.equal(projection.homestead.upgrade_tokens, 86)
  assert.deepEqual(projection.homestead.room_upgrades, ['reinforced-hearth'])
  assert.deepEqual(projection.homestead.upgrade_effects, { max_hp_delta: 10 })
  assert.deepEqual(projection.homestead.market_purchases, ['loop-lens'])
})

test('cloud projection refuses malformed room levels and Embers', () => {
  assert.throws(() => projectPlayerState({ homestead: { room_levels: { ...levels, pantry: 9 } } }), /Invalid Home room levels/)
  assert.throws(() => projectPlayerState({ homestead: { room_levels: { den: 1 } } }), /Invalid Home room levels/)
  assert.throws(() => projectPlayerState({ homestead: { upgrade_tokens: -1 } }), /Invalid Home Embers/)
})
