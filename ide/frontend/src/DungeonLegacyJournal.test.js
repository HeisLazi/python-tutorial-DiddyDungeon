import assert from 'node:assert/strict'
import { test } from 'node:test'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

const regions = [
  { id: 'basics', label: 'Basics Village', boss: 'The Mimic Matriarch', cleared: true, echoes_total: 2, echoes_earned: 1 },
  { id: 'flow', label: 'Flow Keep', boss: 'The Endless Warden', cleared: false, echoes_total: 1, echoes_earned: 0 },
]
const checklist = [
  { id: 'a', name: 'Matriarch’s Dawnlight', slot: 'weapon', tier: 'epic', region: 'basics', earned: true, how: 'Boss drop · The Mimic Matriarch', modes: ['campaign', 'sparring', 'pvp'] },
  { id: 'b', name: 'Delver’s Pilgrim Knot', slot: 'trinket', tier: 'rare', region: 'basics', earned: false, how: 'Elite drop · Basics Village', modes: ['campaign'] },
  { id: 'c', name: 'Flow Lantern', slot: 'trinket', tier: 'rare', region: 'flow', earned: false, how: 'Elite drop · Flow Keep', modes: ['campaign', 'sparring', 'pvp'] },
  { id: 'd', name: 'Oathkeeper Sabre', slot: 'weapon', tier: 'epic', region: null, earned: false, how: 'Legacy reward', modes: ['campaign', 'sparring', 'pvp'] },
]
const journal = {
  unlocks: [{ id: 'a', name: 'Matriarch’s Dawnlight', slot: 'weapon' }], cleared_bosses: [{ id: 'basics', name: 'The Mimic Matriarch', region: 'Basics Village' }],
  bonuses: { starting_hp: 5, starting_bandages: 0, starting_coins: 10, starting_tonics: 1 },
  perks: [{ boss: 1, label: '+5 starting HP', earned: true }, { boss: 4, label: '+10 starting run coins', earned: false }], title: 'Master Delver', next_milestone: 'Clear a regional boss for +5 starting HP.',
  checklist, regions, totals: { bosses: 1, bosses_total: 8, echoes: 1, echoes_total: 4 },
}

async function render(props) {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { DungeonLegacyJournal } = await vite.ssrLoadModule('/src/RpgViews.jsx')
    // React's server renderer puts comment markers between interpolated pieces of text.
    return renderToString(React.createElement(DungeonLegacyJournal, props)).replace(/<!-- -->/g, '')
  } finally {
    await vite.close()
  }
}

test('the Journal lists every echo and boss, earned or not, with how to earn each', async () => {
  const html = await render({ journal })
  for (const text of [/1 \/ 8 BOSSES · 1 \/ 4 ECHOES/, /Basics Village/, /Flow Keep/, /BOSS CLEARED/, /BOSS NOT CLEARED/, /Boss drop · The Mimic Matriarch/, /Elite drop · Basics Village/, /Any region/, /Oathkeeper Sabre/, /Delver’s Pilgrim Knot/]) assert.match(html, text)
  assert.match(html, /usable in Campaign · Sparring · PvP/)  // only earned echoes advertise their modes
  assert.equal((html.match(/usable in/g) || []).length, 1)
  assert.match(html, /\(earned\)/)
  assert.match(html, /\(not earned yet\)/)
})

test('the rule text is accurate and no longer mentions armour the Journal does not grant', async () => {
  const html = await render({ journal })
  assert.match(html, /permanent echo/)
  assert.doesNotMatch(html, /forged armour|camp stash/)
})

test('the setup page keeps the checklist collapsed and in-run views open it', async () => {
  assert.doesNotMatch(await render({ journal, compact: true }), /<details[^>]*open/)
  assert.match(await render({ journal }), /<details[^>]*open/)
})

test('an older payload without a checklist still renders its earned entries', async () => {
  const html = await render({ journal: { unlocks: journal.unlocks, cleared_bosses: journal.cleared_bosses, bonuses: journal.bonuses } })
  assert.match(html, /Matriarch’s Dawnlight/)
  assert.match(html, /The Mimic Matriarch/)
})

test('the Journal shows perks from bosses four to eight and the earned title', async () => {
  const html = await render({ journal })
  for (const text of [/<strong>\+10<\/strong><small>starting run coins/, /<strong>\+1<\/strong><small>starting tonics/, /Boss 4/, /Locked/, /Earned/, /Title earned:<\/strong> Master Delver/]) assert.match(html, text)
  const plain = await render({ journal: { ...journal, bonuses: { starting_hp: 5, starting_bandages: 0 }, perks: [], title: null } })
  assert.doesNotMatch(plain, /Title earned/)
  assert.doesNotMatch(plain, /<small>starting run coins/)
})
