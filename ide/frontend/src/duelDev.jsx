// Disposable loopback-only playtest. This entry is not part of the production build.
import React from 'react'
import { createRoot } from 'react-dom/client'
import { loader } from '@monaco-editor/react'
import OnlineDuel from './OnlineDuel.jsx'
import './duelDev.css'

const root = createRoot(document.getElementById('root'))
if (!import.meta.env.DEV || window.location.hostname !== '127.0.0.1') {
  root.render(<p>Local development playtest unavailable.</p>)
} else {
  loader.config({ paths: { vs: '/monaco/vs' } })
  const player = new URLSearchParams(window.location.search).get('player') === '2' ? 2 : 1
  const group = '00000000-0000-4000-8000-000000000001'
  const ids = { 1: '00000000-0000-4000-8000-000000000011', 2: '00000000-0000-4000-8000-000000000022' }
  const request = async (path, method = 'GET', body) => {
    const response = await fetch(`http://127.0.0.1:8911${path}`, {
      method,
      headers: { Authorization: `Bearer player-${player === 1 ? 'one' : 'two'}`, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
    const result = await response.json().catch(() => ({}))
    if (!response.ok) throw new Error(typeof result.detail === 'string' ? result.detail : 'Local playtest service is unavailable.')
    return result
  }
  const gp = id => `/groups/${id}`
  const duelClient = {
    invite: (g, guest, chain, mode) => request(`${gp(g)}/invites`, 'POST', { guest_id: guest, chain_id: chain, mode }),
    pending: g => request(`${gp(g)}/invites`),
    invitation: (g, id) => request(`${gp(g)}/invites/${id}`),
    accept: (g, id) => request(`${gp(g)}/invites/${id}/accept`, 'POST', {}),
    withdraw: (g, id) => request(`${gp(g)}/invites/${id}/withdraw`, 'POST', {}),
    recoverable: g => request(`${gp(g)}/matches/recoverable`),
    match: (g, id) => request(`${gp(g)}/matches/${id}`),
    catalog: (g, mode = 'fair') => request(`${gp(g)}/loadouts?mode=${encodeURIComponent(mode)}`),
    loadout: (g, id, selection) => request(`${gp(g)}/matches/${id}/loadout`, 'POST', selection),
    submit: (g, id, code, stance, choice) => request(`${gp(g)}/matches/${id}/submit`, 'POST', choice === undefined ? { code, stance } : { code, stance, choice }),
    practice: (g, id, code, stdin) => request(`${gp(g)}/matches/${id}/practice`, 'POST', { code, stdin }),
    bonus: (g, id, answer, reward) => request(`${gp(g)}/matches/${id}/bonus`, 'POST', { answer, reward }),
    ready: (g, id) => request(`${gp(g)}/matches/${id}/ready`, 'POST', {}),
    cancel: (g, id) => request(`${gp(g)}/matches/${id}/cancel`, 'POST', {}),
  }
  root.render(<><div className="playtest-banner">LOCAL PLAYTEST · Hunter {player} · Disposable identities · No account or save connected</div><OnlineDuel groupId={group} userId={ids[player]} visitors={[{ id: ids[player === 1 ? 2 : 1], name: `Hunter ${player === 1 ? 2 : 1}` }]} duelClient={duelClient} configured onClose={() => window.location.reload()} /></>)
}
