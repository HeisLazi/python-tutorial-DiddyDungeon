import assert from 'node:assert/strict'
import { test } from 'node:test'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { createServer } from 'vite'

test('online route presents a direct Colosseum menu to signed-out visitors', async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { default: OnlineHideout } = await vite.ssrLoadModule('/src/OnlineHideout.jsx')
    const html = renderToString(React.createElement(OnlineHideout, {
      account: { authStatus: 'signed-out' },
      progress: {},
      onNavigate: () => {},
    }))

    assert.match(html, /Colosseum/)
    assert.match(html, /Sign in to play online/)
    assert.match(html, /Open account settings/)
    assert.doesNotMatch(html, /Preview the House|online-house-preview|walkable hub/i)
  } finally {
    await vite.close()
  }
})

test('signed-in online menu exposes lobby, shop and Leaderboards pages', async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { default: OnlineHideout } = await vite.ssrLoadModule('/src/OnlineHideout.jsx')
    const html = renderToString(React.createElement(OnlineHideout, {
      account: { authStatus:'signed-in', user:{ id:'12345678-1234-1234-1234-123456789abc' } },
      progress: { name:'Hunter' },
      onNavigate: () => {},
      onEquipmentSynced: () => {},
    }))

    assert.match(html, /aria-label="Online pages"/)
    assert.match(html, />Lobby<\/button>/)
    assert.match(html, />Shop<\/button>/)
    assert.match(html, />Leaderboards<\/button>/)
    assert.match(html, /Create a lobby, then share a code/)
    assert.match(html, /disabled="" title="Create or join a lobby first"/)
  } finally {
    await vite.close()
  }
})

test('group Leaderboards presents readable ranked standings and loading state', async () => {
  const vite = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
  try {
    const { default: OnlineLeaderboard } = await vite.ssrLoadModule('/src/OnlineLeaderboard.jsx')
    const html = renderToString(React.createElement(OnlineLeaderboard, {
      groupId:'12345678-1234-1234-1234-123456789abc',
      userId:'12345678-1234-1234-1234-123456789abc',
      onClose: () => {},
    }))

    assert.match(html, /aria-label="Group Leaderboards"/)
    assert.match(html, /Ranked results for your private group/)
    assert.match(html, /Loading group standings/)
    assert.match(html, /Only ranked duels change ratings/)
  } finally {
    await vite.close()
  }
})
