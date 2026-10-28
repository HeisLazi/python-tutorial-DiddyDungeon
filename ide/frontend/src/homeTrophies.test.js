import { test } from 'node:test'
import assert from 'node:assert/strict'
import { campaignBossTrophies } from './homeTrophies.js'

test('shows named bosses only when their own campaign has been cleared', () => {
  const trophies = campaignBossTrophies({ stats: { bosses_defeated: 9 }, projects: [
    { branch: 'lantern', name: 'Lantern Vale', boss: 'The Unwritten King', boss_status: 'available' },
    { branch: 'casino', name: 'Blackjack', boss: 'The House', boss_status: 'defeated', completed_at: '2026-10-28' },
    { branch: 'old', boss: 'The Archivist', completed: true },
    { branch: 'unnamed', completed: true },
  ] })
  assert.deepEqual(trophies.map((trophy) => trophy.boss), ['The House', 'The Archivist'])
  assert.equal(trophies[0].campaign, 'Blackjack')
  assert.deepEqual(campaignBossTrophies({ stats: { bosses_defeated: 3 } }), [])
})
