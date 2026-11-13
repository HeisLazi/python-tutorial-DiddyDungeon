import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

const css = readFileSync(new URL('./onlineMenu.css', import.meta.url), 'utf8')

test('leaderboard renders its heading, actions and note', async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { default: OnlineLeaderboard } = await vite.ssrLoadModule('/src/OnlineLeaderboard.jsx')
    const html = renderToString(React.createElement(OnlineLeaderboard, {
      groupId: '00000000-0000-4000-8000-000000000001',
      userId: '00000000-0000-4000-8000-000000000011',
      onClose: () => {},
      loadLadder: () => new Promise(() => {}),
    }))
    for (const text of [/Leaderboards/, /Ranked results for your private group/, /Refresh/, /← Lobby/, /Loading group standings/, /Only ranked duels change ratings/]) assert.match(html, text)
    // The button wrapper must carry the class the dark theme styles, or the buttons collapse together.
    assert.match(html, /class="online-leaderboard-buttons online-menu-leaderboard-buttons"/)
  } finally {
    await vite.close()
  }
})

test('dark leaderboard rules outrank the light-theme ones from onlineHideout.css', () => {
  // onlineHideout.css loads later and has one-class selectors, so every dark rule must
  // use the two-class prefix; otherwise the panel and heading turn light on the dark page.
  const bare = [...css.matchAll(/(^|[,}{])\s*\.online-menu-leaderboard(?![-\w])/g)]
  assert.equal(bare.length, 0, 'found a dark leaderboard selector without the .online-leaderboard prefix')
  assert.match(css, /\.online-leaderboard\.online-menu-leaderboard\s*\{[^}]*background:transparent/)
  assert.match(css, /\.online-leaderboard\.online-menu-leaderboard \.online-heading\{[^}]*flex-wrap:wrap/)
})

test('leaderboard table fits narrow windows without sideways scrolling', () => {
  assert.match(css, /@media\(max-width:560px\)\{[^@]*\.online-leaderboard-table\{min-width:0\}/)
})
