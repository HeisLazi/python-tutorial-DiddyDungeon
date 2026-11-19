// The service URL is public configuration; the user's access token stays in
// the Authorization header and is never put in URLs, logs, or persistent state.
import { getSupabaseClient } from './supabaseClient.js'
import { onlineServiceUrl as raw } from './onlineService.js'
let serviceUrl = ''
try {
  const parsed = new URL(raw)
  if (parsed.protocol === 'https:' && !parsed.username && !parsed.password && !parsed.search && !parsed.hash) serviceUrl = parsed.href.replace(/\/$/, '')
} catch { /* online duel service is optional */ }
export const onlineDuelsConfigured = Boolean(serviceUrl)
const safeId = /^[0-9a-f-]{36}$/i
const opaqueId = /^[A-Za-z0-9_-]{12,128}$/

async function request(path, method = 'GET', body) {
  if (!serviceUrl) throw new Error('Online duels are not configured yet.')
  const client = getSupabaseClient()
  if (!client) throw new Error('Sign in to Quest Lab first.')
  const { data, error } = await client.auth.getSession()
  if (error || !data?.session?.access_token) throw new Error('Your account session has expired. Sign in again.')
  const response = await fetch(serviceUrl + path, { method, headers: { Authorization: `Bearer ${data.session.access_token}`, ...(body ? { 'Content-Type': 'application/json' } : {}) }, ...(body ? { body: JSON.stringify(body) } : {}) })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) {
    const failure = new Error(typeof result.detail === 'string' ? result.detail : 'The duel service is unavailable.')
    failure.status = response.status
    throw failure
  }
  return result
}
function groupPath(groupId) {
  if (!safeId.test(String(groupId))) throw new Error('Select a valid group.')
  return `/groups/${groupId}`
}
function validOpaque(id) {
  if (!opaqueId.test(String(id))) throw new Error('The duel reference is invalid.')
  return id
}
export const onlineDuel = {
  invite: (group, guest, chain, mode) => request(`${groupPath(group)}/invites`, 'POST', {guest_id:guest, chain_id:chain, mode}),
  pending: group => request(`${groupPath(group)}/invites`),
  invitation: (group, id) => request(`${groupPath(group)}/invites/${validOpaque(id)}`),
  accept: (group, id) => request(`${groupPath(group)}/invites/${validOpaque(id)}/accept`, 'POST', {}),
  withdraw: (group, id) => request(`${groupPath(group)}/invites/${validOpaque(id)}/withdraw`, 'POST', {}),
  recoverable: group => request(`${groupPath(group)}/matches/recoverable`),
  match: (group, id) => request(`${groupPath(group)}/matches/${validOpaque(id)}`),
  catalog: (group, mode = 'fair') => request(`${groupPath(group)}/loadouts?mode=${encodeURIComponent(mode)}`),
  ladder: group => request(`${groupPath(group)}/ladder`),
  wallet: group => request(`${groupPath(group)}/wallet`),
  merchant: group => request(`${groupPath(group)}/merchant`),
  purchase: (group, itemId) => request(`${groupPath(group)}/merchant/purchase`, 'POST', {item_id:itemId}),
  loadout: (group, id, selection) => request(`${groupPath(group)}/matches/${validOpaque(id)}/loadout`, 'POST', selection),
  submit: (group, id, code, stance, choice) => request(`${groupPath(group)}/matches/${validOpaque(id)}/submit`, 'POST', choice === undefined ? {code, stance} : {code, stance, choice}),
  practice: (group, id, code, stdin) => request(`${groupPath(group)}/matches/${validOpaque(id)}/practice`, 'POST', {code, stdin}),
  bonus: (group, id, answer, reward) => request(`${groupPath(group)}/matches/${validOpaque(id)}/bonus`, 'POST', {answer, reward}),
  ready: (group, id) => request(`${groupPath(group)}/matches/${validOpaque(id)}/ready`, 'POST', {}),
  cancel: (group, id) => request(`${groupPath(group)}/matches/${validOpaque(id)}/cancel`, 'POST', {}),
}
