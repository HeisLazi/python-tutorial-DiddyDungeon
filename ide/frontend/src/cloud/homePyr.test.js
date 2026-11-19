import test from 'node:test'
import assert from 'node:assert/strict'
import { homePyrStage } from '../homePyr.js'

test('Pyr artwork stage follows existing bond and mastery milestones', () => {
  assert.equal(homePyrStage({}), 1)
  assert.equal(homePyrStage({ companion: { bond: 3 } }), 2)
  assert.equal(homePyrStage({ companion: { bond: 6 }, stats: { mastery_shields_earned: 2 } }), 3)
  assert.equal(homePyrStage({ companion: { bond: 6 }, stats: { mastery_shields_earned: 3 } }), 4)
  assert.equal(homePyrStage({ companion: { bond: 2 }, stats: { mastery_shields_earned: 9 } }), 1)
})
