import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveCloudConfig } from './config.js'
import {
  DEFAULT_DEVICE_LABEL,
  DEVICE_IDS_STORAGE_KEY,
  SyncEngine,
  deviceIdForUser,
  normalizeDeviceLabel,
} from './syncEngine.js'

class MemoryStorage {
  constructor() {
    this.values = new Map()
  }

  getItem(key) {
    return this.values.has(key) ? this.values.get(key) : null
  }

  setItem(key, value) {
    this.values.set(key, String(value))
  }
}

function fakeCloudClient(user, { accessToken = 'eyJ-this-must-never-enter-state' } = {}) {
  const profileRows = new Map()
  const deviceRows = new Map()
  const writes = []
  let session = {
    access_token: accessToken,
    user: { ...user, user_metadata: { display_name: 'Lazi' } },
  }
  let authCallback = null

  const table = (name) => {
    let filter = null
    let payload = null
    const builder = {
      select() {
        return builder
      },
      eq(column, value) {
        filter = { column, value }
        return builder
      },
      maybeSingle: async () => {
        const rows = name === 'profiles' ? profileRows : deviceRows
        const value = filter ? rows.get(filter.value) ?? null : null
        return { data: value, error: null }
      },
      upsert(nextPayload) {
        payload = { ...nextPayload }
        writes.push({ table: name, payload: { ...payload } })
        return builder
      },
      single: async () => {
        const rows = name === 'profiles' ? profileRows : deviceRows
        const now = '2026-09-14T00:00:00.000Z'
        const existing = rows.get(payload.id)
        const row = {
          ...existing,
          ...payload,
          created_at: existing?.created_at ?? now,
          updated_at: now,
          ...(name === 'devices' ? { last_seen_at: payload.last_seen_at ?? now } : {}),
        }
        rows.set(payload.id, row)
        return { data: row, error: null }
      },
    }
    return builder
  }

  return {
    writes,
    auth: {
      getSession: async () => ({ data: { session }, error: null }),
      onAuthStateChange(callback) {
        authCallback = callback
        return { data: { subscription: { unsubscribe() {} } } }
      },
      async signInWithPassword() {
        authCallback?.('SIGNED_IN', session)
        return { data: { session }, error: null }
      },
      async signUp() {
        return { data: { session }, error: null }
      },
      async signOut() {
        session = null
        authCallback?.('SIGNED_OUT', null)
        return { error: null }
      },
    },
    from: table,
  }
}

test('device labels are friendly names and per-account IDs never contain filesystem paths', () => {
  const storage = new MemoryStorage()
  assert.equal(normalizeDeviceLabel('  Papasmurff   Desktop  '), 'Papasmurff Desktop')
  assert.equal(normalizeDeviceLabel(''), DEFAULT_DEVICE_LABEL)
  assert.throws(() => normalizeDeviceLabel('C:\\Users\\lazi'), /filesystem path/)
  assert.throws(() => normalizeDeviceLabel('/home/lazi'), /filesystem path/)

  const userA = deviceIdForUser('00000000-0000-4000-8000-000000000001', storage)
  const userB = deviceIdForUser('00000000-0000-4000-8000-000000000002', storage)
  assert.notEqual(userA, userB)
  const stored = JSON.parse(storage.getItem(DEVICE_IDS_STORAGE_KEY))
  assert.deepEqual(Object.keys(stored).sort(), [
    '00000000-0000-4000-8000-000000000001',
    '00000000-0000-4000-8000-000000000002',
  ])
  assert.match(userA, /^[0-9a-f-]{36}$/)
})

test('restored auth creates private profile/device records through the service boundary', async () => {
  const config = resolveCloudConfig({
    VITE_SUPABASE_URL: 'https://example.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'public-anon-key',
  })
  const storage = new MemoryStorage()
  const user = { id: '00000000-0000-4000-8000-000000000001', email: 'lazi@example.test' }
  const client = fakeCloudClient(user)
  const engine = new SyncEngine({ config, clientFactory: () => client, storage, now: () => new Date('2026-09-14T12:00:00.000Z') })

  engine.initialize()
  await engine.restoreSession()

  const state = engine.getState()
  assert.equal(state.authStatus, 'signed-in')
  assert.deepEqual(state.user, { id: user.id, email: user.email })
  assert.equal(state.profile.display_name, 'Lazi')
  assert.equal(state.device.display_name, DEFAULT_DEVICE_LABEL)
  assert.equal(Object.prototype.hasOwnProperty.call(state, 'session'), false)
  assert.equal(client.writes.length, 2)
  assert.deepEqual(Object.keys(client.writes[1].payload).sort(), ['display_name', 'id', 'last_seen_at', 'user_id'])
  assert.equal(Object.prototype.hasOwnProperty.call(client.writes[1].payload, 'workspace'), false)
  assert.equal(Object.prototype.hasOwnProperty.call(client.writes[1].payload, 'path'), false)
})

test('sign-out returns to local Forge without deleting the local device identity', async () => {
  const config = resolveCloudConfig({
    VITE_SUPABASE_URL: 'https://example.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'public-anon-key',
  })
  const storage = new MemoryStorage()
  const user = { id: '00000000-0000-4000-8000-000000000001', email: 'lazi@example.test' }
  const client = fakeCloudClient(user)
  const engine = new SyncEngine({ config, clientFactory: () => client, storage })

  engine.initialize()
  await engine.restoreSession()
  const deviceId = engine.getState().device.id
  await engine.signOut()

  assert.equal(engine.getState().authStatus, 'signed-out')
  assert.equal(engine.getState().syncStatus, 'local')
  assert.equal(deviceIdForUser(user.id, storage), deviceId)
})
