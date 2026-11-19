import assert from 'node:assert/strict'
import { test } from 'node:test'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

test('online duel renders the friend challenge lobby and both coding formats', async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { default: OnlineDuel } = await vite.ssrLoadModule('/src/OnlineDuel.jsx')
    const html = renderToString(React.createElement(OnlineDuel, {
      groupId: '00000000-0000-4000-8000-000000000001',
      userId: '00000000-0000-4000-8000-000000000011',
      visitors: [{ id: '00000000-0000-4000-8000-000000000022', name: 'Friend Two' }],
      onClose: () => {},
      configured: true,
      duelClient: {},
    }))

    assert.match(html, /Challenge a friend/)
    assert.match(html, /Friend Two/)
    assert.match(html, /Friendly · choose any gear/)
    for (const label of [/Basic · quick questions/, /Normal · lists, dictionaries/, /Advanced · build a mini poker game/, /Bug Hunt/, /Output Oracle/]) assert.match(html, label)
    assert.doesNotMatch(html, /Potion shop|Locked chest/)
    assert.match(html, /Challenges for you/)
    assert.match(html, /Back to PvP menu/)
    assert.doesNotMatch(html, /PRIVATE DUEL · EARLY PREVIEW/)
  } finally {
    await vite.close()
  }
})

test('saved duel recovery is clear and offers an accessible resume action', async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { RecoverableDuels } = await vite.ssrLoadModule('/src/OnlineDuel.jsx')
    const html = renderToString(React.createElement(RecoverableDuels, {
      matches: [{ match_id:'match-1', opponent_id:'friend-1', mode:'geared', round:1 }],
      names: new Map([['friend-1', 'Friend One']]),
    }))
    assert.match(html, /Saved duels/)
    assert.match(html, /Friend One/)
    assert.match(html, /Ranked/)
    assert.match(html, /Challenge <!-- -->2/)
    assert.match(html, />Resume</)
    assert.match(html, /stay saved if the app closes or reconnects/)
  } finally {
    await vite.close()
  }
})
