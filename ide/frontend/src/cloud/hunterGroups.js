// Group membership is enforced by the database. Never put an invitation or
// session token in a URL, persistent storage, presence payload, or log.
import { getSupabaseClient } from './supabaseClient.js'
import { onlineDuel } from './onlineDuel.js'

const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const invitePattern = /^[0-9a-f]{48}$/

async function authenticatedClient() {
  const client = getSupabaseClient()
  if (!client) throw new Error('Set up cloud sync to use Shax Champions House.')
  const { data, error } = await client.auth.getSession()
  if (error) throw error
  if (!data?.session?.user?.id) throw new Error('Sign in to use Shax Champions House.')
  return { client, user: data.session.user }
}

async function rpc(name, args) {
  const { client } = await authenticatedClient()
  const { data, error } = await client.rpc(name, args)
  if (error) throw error
  return data
}

export async function listHunterGroups() {
  const { client } = await authenticatedClient()
  const { data, error } = await client.from('hunter_groups').select('id,name,owner_id').order('created_at')
  if (error) throw error
  return data || []
}
export async function createHunterGroup(name) {
  const trimmed = String(name || '').trim()
  if (!trimmed || trimmed.length > 40) throw new Error('Choose a group name of up to 40 characters.')
  return rpc('create_hunter_group', { group_name: trimmed })
}
export async function createHunterGroupInvite(groupId) {
  if (!uuid.test(String(groupId))) throw new Error('Choose a group first.')
  return rpc('create_hunter_group_invite', { target_group: groupId })
}
export async function joinHunterGroup(invite) {
  const code = String(invite || '').trim().toLowerCase()
  if (!invitePattern.test(code)) throw new Error('Enter a valid invitation code.')
  return rpc('join_hunter_group', { invitation: code })
}
export async function leaveHunterGroup(groupId) {
  if (!uuid.test(String(groupId))) throw new Error('Choose a group first.')
  return rpc('leave_hunter_group', { target_group: groupId })
}

export async function hunterGroupLadder(groupId) {
  if (!uuid.test(String(groupId))) throw new Error('Choose a group first.')
  const { client } = await authenticatedClient()
  const [roster, standings] = await Promise.all([
    client.rpc('hunter_group_roster', { target_group: groupId }),
    onlineDuel.ladder(groupId),
  ])
  if (roster.error) throw roster.error
  const names = new Map((roster.data || []).map(member => [member.user_id, member.display_name]))
  const ratings = new Map((standings.ratings || []).map(entry => [entry.user_id, entry]))
  return (roster.data || []).map(member => ({
    ...(ratings.get(member.user_id) || { user_id:member.user_id, rating:1000, wins:0, losses:0, draws:0 }),
    name:names.get(member.user_id) || 'Hunter',
  })).sort((a, b) => b.rating - a.rating || a.name.localeCompare(b.name))
}

const looks = new Set(['classic', 'ivory', 'spectral', 'harvest', 'oracle', 'patchwork', 'pilgrim', 'wayfarer', 'lanternkeeper', 'wardplate', 'debugger', 'merchant-oracle', 'arcane', 'steel', 'ember'])
const facings = new Set(['up', 'down', 'left', 'right'])
const rooms = new Set(['online_hideout', 'online_ferryman'])
const clamp = (n, low, high) => Math.max(low, Math.min(high, n))
function visual(payload) {
  if (!payload || typeof payload !== 'object' || !uuid.test(String(payload.id)) || !Number.isFinite(payload.x) || !Number.isFinite(payload.y)) return null
  const name = String(payload.name || 'Hunter').replace(/[\u0000-\u001f\u007f]/g, '').trim().slice(0, 24) || 'Hunter'
  return { id: String(payload.id), name, x: clamp(payload.x, 0, 320), y: clamp(payload.y, 0, 180),
    room: rooms.has(payload.room) ? payload.room : 'online_hideout', facing: facings.has(payload.facing) ? payload.facing : 'down',
    look: looks.has(payload.look) ? payload.look : 'classic' }
}

// Requires the group's private Realtime RLS policies and public Realtime
// access disabled server-side. Presence and broadcasts are cosmetic only: the
// channel is never used as evidence for identity, possessions or game results.
export async function connectHunterPresence({ groupId, name, look, onVisitors, onStatus }) {
  if (!uuid.test(String(groupId))) throw new Error('Choose a group first.')
  const { client, user } = await authenticatedClient()
  const local = visual({ id: user.id, name, look, room: 'online_hideout', facing: 'down', x: 160, y: 150 })
  const guests = new Map()
  let subscribed = false
  let closed = false
  let lastBroadcast = 0
  let positionSnapshot = null
  const channel = client.channel(`hunter-group:${groupId}`, { config: { private: true, presence: { key: user.id }, broadcast: { self: false } } })
  const publish = () => onVisitors?.([...guests.values()].slice(0, 3))
  const sync = () => {
    const active = new Set()
    for (const entries of Object.values(channel.presenceState())) {
      for (const entry of entries) {
        const guest = visual(entry)
        if (!guest || guest.id === user.id) continue
        active.add(guest.id)
        if (!guests.has(guest.id)) guests.set(guest.id, guest)
      }
    }
    for (const id of guests.keys()) if (!active.has(id)) guests.delete(id)
    publish()
  }
  channel.on('presence', { event: 'sync' }, sync)
  channel.on('broadcast', { event: 'move' }, ({ payload }) => {
    const guest = visual(payload)
    if (!guest || guest.id === user.id || !guests.has(guest.id)) return
    guests.set(guest.id, guest)
    publish()
  })
  channel.subscribe(async status => {
    if (closed) return
    subscribed = status === 'SUBSCRIBED'
    onStatus?.(status)
    if (subscribed) await channel.track(local)
  })
  return {
    async move(position) {
      if (!subscribed || closed) return
      const update = visual({ ...local, ...position, id: user.id })
      if (!update) return
      Object.assign(local, update)
      clearTimeout(positionSnapshot)
      // Presence is a low-frequency snapshot for friends joining later;
      // movement itself uses Broadcast and never drives game authority.
      positionSnapshot = setTimeout(() => {
        if (subscribed && !closed) void channel.track(local)
      }, 600)
      const now = performance.now()
      if (now - lastBroadcast < 125) return
      lastBroadcast = now
      await channel.send({ type: 'broadcast', event: 'move', payload: local })
    },
    async close() {
      if (closed) return
      closed = true
      clearTimeout(positionSnapshot)
      guests.clear()
      onVisitors?.([])
      await client.removeChannel(channel)
    },
  }
}
