import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveCloudConfig } from './config.js'
import { AVATAR_MAX_BYTES, avatarObjectPath, readCachedAvatar, validateAvatarDataUrl } from './avatarStorage.js'
import {
  CHECKOUT_NAMESPACE_RE,
  DEFAULT_DEVICE_LABEL,
  DEVICE_IDS_STORAGE_KEY,
  DEVICE_LABEL_STORAGE_KEY,
  SYNC_OUTBOX_STORAGE_KEY,
  SyncEngine,
  checkoutStorageNamespace,
  deviceIdForUser,
  normalizeDeviceLabel,
  projectPlayerState,
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

  removeItem(key) {
    this.values.delete(key)
  }
}

function fakeCloudClient(user, { accessToken = 'test-access-token', cloudStore = null } = {}) {
  const profileRows = cloudStore?.profileRows || new Map()
  const deviceRows = cloudStore?.deviceRows || new Map()
  const playerRows = cloudStore?.playerRows || new Map()
  const avatarObjects = cloudStore?.avatarObjects || new Map()
  const writes = []
  let session = {
    access_token: accessToken,
    user: { ...user, user_metadata: { display_name: 'Lazi' } },
  }
  let authCallback = null

  const table = (name) => {
    let filter = null
    let payload = null
    let updatePayload = null
    const builder = {
      select() {
        return builder
      },
      eq(column, value) {
        filter = { column, value }
        return builder
      },
      maybeSingle: async () => {
        if (name === 'player_state') return { data: playerRows.get(user.id) ?? null, error: null }
        const rows = name === 'profiles' ? profileRows : deviceRows
        const value = filter ? rows.get(filter.value) ?? null : null
        return { data: value, error: null }
      },
      upsert(nextPayload) {
        payload = { ...nextPayload }
        writes.push({ table: name, payload: { ...payload } })
        return builder
      },
      update(nextPayload) {
        updatePayload = { ...nextPayload }
        writes.push({ table: name, payload: { ...updatePayload } })
        return builder
      },
      single: async () => {
        const rows = name === 'profiles' ? profileRows : deviceRows
        const now = '2026-09-14T00:00:00.000Z'
        const id = payload?.id || filter?.value
        const existing = rows.get(id)
        const row = {
          ...existing,
          ...payload,
          ...updatePayload,
          ...(id ? { id } : {}),
          created_at: existing?.created_at ?? now,
          updated_at: now,
          ...(name === 'devices' ? { last_seen_at: payload.last_seen_at ?? now } : {}),
        }
        rows.set(id, row)
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
    storage: {
      from(bucket) {
        assert.equal(bucket, 'avatars')
        return {
          async upload(path, blob) {
            avatarObjects.set(path, blob)
            return { data: { path }, error: null }
          },
          async download(path) {
            return { data: avatarObjects.get(path) ?? null, error: avatarObjects.has(path) ? null : { message: 'Avatar not found' } }
          },
          async remove(paths) {
            paths.forEach((path) => avatarObjects.delete(path))
            return { data: paths.map((path) => ({ name: path })), error: null }
          },
        }
      },
    },
    from: table,
    async rpc(name, args) {
      if (name !== 'save_player_state') return { data: null, error: { message: 'unknown rpc' } }
      const existing = playerRows.get(user.id)
      const expected = Number(args.expected_revision)
      if (existing && existing.revision !== expected) return { data: null, error: { code: '40001', message: 'Cloud player state revision conflict' } }
      if (!existing && expected !== 0) return { data: null, error: { code: '40001', message: 'Cloud player state revision conflict' } }
      const now = '2026-09-14T00:00:00.000Z'
      const row = {
        user_id: user.id,
        state: JSON.parse(JSON.stringify(args.next_state)),
        revision: existing ? existing.revision + 1 : 1,
        device_id: args.source_device_id,
        created_at: existing?.created_at || now,
        updated_at: now,
      }
      playerRows.set(user.id, row)
      return { data: row, error: null }
    },
  }
}

const clone = (value) => JSON.parse(JSON.stringify(value))

function fakeLocalApi(initialProgress, initialRevision = 0) {
  let progress = clone(initialProgress)
  let revision = initialRevision
  let unavailable = false
  return {
    setCampaign(nextProgress, nextRevision) {
      progress = clone(nextProgress)
      revision = nextRevision
    },
    setUnavailable(value) {
      unavailable = value
    },
    getProgress() {
      return clone(progress)
    },
    fetch: async (url, options = {}) => {
      if (unavailable) throw new Error('offline')
      if (url === '/api/state/sync') return { ok: true, status: 200, json: async () => ({ projection: projectPlayerState(progress), revision, metadata: { revision } }) }
      if (url !== '/api/state/sync/apply') return { ok: false, status: 404, json: async () => ({ detail: 'not found' }) }
      const body = JSON.parse(options.body || '{}')
      if (body.expected_revision !== revision) return { ok: false, status: 409, json: async () => ({ detail: 'local revision conflict' }) }
      const incoming = projectPlayerState(body.projection)
      for (const domain of ['player', 'equipment', 'companion']) {
        if (incoming[domain] && Object.keys(incoming[domain]).length) progress[domain] = { ...(progress[domain] || {}), ...incoming[domain] }
      }
      if (incoming.homestead) progress.homestead = { ...(progress.homestead || {}), ...incoming.homestead }
      revision += 1
      progress.meta = { ...(progress.meta || {}), revision }
      return { ok: true, status: 200, json: async () => ({ ok: true, changed: true, revision, projection: projectPlayerState(progress) }) }
    },
  }
}

const campaign = (coins, level = 1) => ({
  player: { level, xp: coins, xp_next: 100, lifetime_xp: coins, coins, hp: 100, max_hp: 100 },
  homestead: { owned_cosmetics: ['cursor-basic'], equipped: { cursor: 'cursor-basic' } },
})

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

test('same-user sync metadata is partitioned by an opaque checkout namespace', () => {
  const storage = new MemoryStorage()
  const userId = '00000000-0000-4000-8000-000000000003'
  const namespaceA = checkoutStorageNamespace('C:\\QuestLab\\platform')
  const namespaceB = checkoutStorageNamespace('/home/lazi/projects/questlab-platform')

  assert.match(namespaceA, CHECKOUT_NAMESPACE_RE)
  assert.match(namespaceB, CHECKOUT_NAMESPACE_RE)
  assert.notEqual(namespaceA, namespaceB)
  assert.equal(namespaceA.includes('QuestLab'), false)
  assert.equal(namespaceB.includes('/home'), false)

  const deviceA = deviceIdForUser(userId, storage, namespaceA)
  const deviceB = deviceIdForUser(userId, storage, namespaceB)
  assert.notEqual(deviceA, deviceB)
  assert.equal(storage.getItem(`${DEVICE_IDS_STORAGE_KEY}:${namespaceA}`) !== null, true)
  assert.equal(storage.getItem(`${DEVICE_IDS_STORAGE_KEY}:${namespaceB}`) !== null, true)
  assert.equal(storage.getItem(DEVICE_IDS_STORAGE_KEY), null)

  const engineA = new SyncEngine({ storage, checkoutIdentity: namespaceA })
  const engineB = new SyncEngine({ storage, checkoutIdentity: namespaceB })
  assert.equal(engineA._outboxKey(userId), `${SYNC_OUTBOX_STORAGE_KEY}:${namespaceA}:${encodeURIComponent(userId)}`)
  assert.equal(engineB._outboxKey(userId), `${SYNC_OUTBOX_STORAGE_KEY}:${namespaceB}:${encodeURIComponent(userId)}`)
  assert.equal(engineA._deviceLabelKey(), `${DEVICE_LABEL_STORAGE_KEY}:${namespaceA}`)
  assert.equal(engineB._deviceLabelKey(), `${DEVICE_LABEL_STORAGE_KEY}:${namespaceB}`)
  assert.notEqual(engineA._outboxKey(userId), engineB._outboxKey(userId))
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

test('avatar storage validates bounded WebP data and restores it through an account-scoped cache', async () => {
  const config = resolveCloudConfig({
    VITE_SUPABASE_URL: 'https://example.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'public-anon-key',
  })
  const user = { id: '00000000-0000-4000-8000-000000000051', email: 'avatar@example.test' }
  const cloudStore = { profileRows: new Map(), deviceRows: new Map(), avatarObjects: new Map() }
  const storageA = new MemoryStorage()
  const clientA = fakeCloudClient(user, { cloudStore })
  const engineA = new SyncEngine({ config, clientFactory: () => clientA, storage: storageA })
  const dataUrl = 'data:image/webp;base64,U29tZSBhdmF0YXI='

  assert.deepEqual(validateAvatarDataUrl(dataUrl, { maxBytes: AVATAR_MAX_BYTES, allowedMimeTypes: ['image/webp'] }), { mimeType: 'image/webp', bytes: 11 })
  assert.throws(() => validateAvatarDataUrl('data:image/gif;base64,R0lGODlh', { allowedMimeTypes: ['image/webp'] }), /PNG, JPEG or WebP/)
  assert.throws(() => validateAvatarDataUrl(dataUrl, { maxBytes: 4, allowedMimeTypes: ['image/webp'] }), /under 4 bytes/)

  engineA.initialize()
  await engineA.restoreSession()
  await engineA.setAvatarDataUrl(dataUrl)
  const path = avatarObjectPath(user.id)
  assert.equal(engineA.getState().profile.avatar_path, path)
  assert.equal(engineA.getState().avatar.source, 'cloud')
  assert.equal(cloudStore.avatarObjects.has(path), true)
  assert.equal(readCachedAvatar(storageA, user.id), dataUrl)

  const storageB = new MemoryStorage()
  const engineB = new SyncEngine({ config, clientFactory: () => fakeCloudClient(user, { cloudStore }), storage: storageB })
  engineB.initialize()
  await engineB.restoreSession()
  await engineB._refreshCloudAvatar(path, user.id)
  assert.equal(engineB.getState().avatar.source, 'cloud')
  assert.equal(readCachedAvatar(storageB, user.id), dataUrl)

  await engineB.removeAvatar()
  assert.equal(cloudStore.avatarObjects.has(path), false)
  assert.equal(engineB.getState().profile.avatar_path, null)
  assert.equal(readCachedAvatar(storageB, user.id), '')
  engineA.dispose()
  engineB.dispose()
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

test('player-state projection excludes local projects, Codex and cosmetic catalog data', () => {
  const projection = projectPlayerState({
    player: { level: 3, coins: 20, secret: 'local' },
    projects: [{ name: 'Blackjack' }],
    codex: { encounters: [{ mob_name: 'hidden' }] },
    skills: [{ concept: 'Variables' }],
    homestead: {
      owned_cosmetics: ['cursor-basic', 'cursor-basic', 7],
      equipped: { cursor: 'cursor-basic', secret: 'local' },
      catalog: [{ id: 'rare-secret' }],
      purchase_history: [{ item_id: 'cursor-basic' }],
    },
  })
  assert.deepEqual(projection.player, { level: 3, coins: 20 })
  assert.deepEqual(projection.homestead, { owned_cosmetics: ['cursor-basic'], equipped: { cursor: 'cursor-basic' } })
  assert.equal(Object.prototype.hasOwnProperty.call(projection, 'projects'), false)
  assert.equal(Object.prototype.hasOwnProperty.call(projection, 'codex'), false)
  assert.equal(Object.prototype.hasOwnProperty.call(projection.homestead, 'catalog'), false)
})

test('two isolated engine instances sync through revision-aware push, pull, offline outbox and explicit conflict resolution', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const cloudStore = { playerRows: new Map() }
  const userA = { id: '00000000-0000-4000-8000-000000000021', email: 'a@example.test' }
  const userB = { id: userA.id, email: userA.email }
  const storageA = new MemoryStorage()
  const storageB = new MemoryStorage()
  const localA = fakeLocalApi(campaign(5), 1)
  const localB = fakeLocalApi(campaign(0), 0)
  const clientA = fakeCloudClient(userA, { cloudStore })
  const clientB = fakeCloudClient(userB, { cloudStore })
  const engineA = new SyncEngine({ config, clientFactory: () => clientA, storage: storageA, fetchImpl: localA.fetch })
  const engineB = new SyncEngine({ config, clientFactory: () => clientB, storage: storageB, fetchImpl: localB.fetch })

  engineA.initialize()
  await engineA.restoreSession()
  engineA.observeCampaign({ revision: 1, progress: localA.getProgress() })
  await engineA.sync()
  assert.equal(engineA.getState().syncStatus, 'synced')
  assert.equal(cloudStore.playerRows.get(userA.id).state.player.coins, 5)

  engineB.initialize()
  await engineB.restoreSession()
  await engineB.sync()
  assert.equal(engineB.getState().syncStatus, 'synced')
  assert.equal(localB.getProgress().player.coins, 5)

  const changedA = campaign(12, 2)
  localA.setCampaign(changedA, 2)
  engineA.observeCampaign({ revision: 2, progress: changedA })
  clientA.from = () => { throw new Error('offline') }
  await engineA.sync()
  assert.equal(engineA.getState().pendingChanges, 1)
  assert.equal(engineA.getState().syncStatus, 'error')
  clientA.from = clientB.from
  // Restore the original cloud table reader for profile A while retaining the shared row store.
  const cloudReaderA = fakeCloudClient(userA, { cloudStore })
  clientA.from = cloudReaderA.from
  clientA.rpc = cloudReaderA.rpc
  await engineA.sync()
  assert.equal(engineA.getState().syncStatus, 'synced')
  assert.equal(cloudStore.playerRows.get(userA.id).state.player.coins, 12)

  const cloudRevisionAfterPush = cloudStore.playerRows.get(userA.id).revision
  localA.setCampaign(changedA, 3)
  engineA.observeCampaign({ revision: 3, progress: changedA })
  await engineA.sync()
  assert.equal(cloudStore.playerRows.get(userA.id).revision, cloudRevisionAfterPush)

  const cloudRow = cloudStore.playerRows.get(userA.id)
  cloudStore.playerRows.set(userA.id, { ...cloudRow, revision: cloudRow.revision + 1, state: { ...cloudRow.state, player: { ...cloudRow.state.player, coins: 99 } } })
  const localConflict = campaign(20, 3)
  localA.setCampaign(localConflict, 4)
  engineA.observeCampaign({ revision: 4, progress: localConflict })
  await engineA.sync()
  assert.equal(engineA.getState().syncStatus, 'conflict')
  await engineA.resolveConflict('cloud')
  assert.equal(engineA.getState().syncStatus, 'synced')
  assert.equal(localA.getProgress().player.coins, 99)

  const keepLocal = campaign(77, 4)
  localA.setCampaign(keepLocal, 6)
  engineA.observeCampaign({ revision: 6, progress: keepLocal })
  const newerCloudRow = cloudStore.playerRows.get(userA.id)
  cloudStore.playerRows.set(userA.id, { ...newerCloudRow, revision: newerCloudRow.revision + 1, state: { ...newerCloudRow.state, player: { ...newerCloudRow.state.player, coins: 66 } } })
  await engineA.sync()
  assert.equal(engineA.getState().syncStatus, 'conflict')
  await engineA.resolveConflict('local')
  assert.equal(engineA.getState().syncStatus, 'synced')
  assert.equal(cloudStore.playerRows.get(userA.id).state.player.coins, 77)

  engineA.dispose()
  engineB.dispose()
})

test('silent background sync does not flap a settled HUD status', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const user = { id: '00000000-0000-4000-8000-000000000031', email: 'background@example.test' }
  const storage = new MemoryStorage()
  const local = fakeLocalApi(campaign(5), 1)
  const client = fakeCloudClient(user)
  const engine = new SyncEngine({ config, clientFactory: () => client, storage, fetchImpl: local.fetch })

  engine.initialize()
  await engine.restoreSession()
  await engine.sync()
  assert.equal(engine.getState().syncStatus, 'synced')

  const statuses = []
  const unsubscribe = engine.subscribe((state) => statuses.push(state.syncStatus))
  statuses.length = 0
  await engine.sync({ silent: true })

  assert.equal(statuses.includes('syncing'), false)
  assert.equal(engine.getState().syncStatus, 'synced')
  unsubscribe()
  engine.dispose()
})

test('a validated local cache bootstraps an untouched starter cloud copy', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const user = { id: '00000000-0000-4000-8000-000000000041', email: 'starter-cloud@example.test' }
  const cloudStore = { playerRows: new Map() }
  const starter = projectPlayerState(campaign(0, 1))
  cloudStore.playerRows.set(user.id, {
    user_id: user.id,
    state: starter,
    revision: 1,
    device_id: 'starter-device',
    updated_at: '2026-09-14T00:00:00.000Z',
  })
  const local = fakeLocalApi(campaign(50, 2), 2)
  const engine = new SyncEngine({
    config,
    clientFactory: () => fakeCloudClient(user, { cloudStore }),
    storage: new MemoryStorage(),
    fetchImpl: local.fetch,
  })

  engine.initialize()
  await engine.restoreSession()
  await engine.sync()

  assert.equal(engine.getState().syncStatus, 'synced')
  assert.equal(engine.getState().conflict, null)
  assert.equal(cloudStore.playerRows.get(user.id).revision, 2)
  assert.equal(cloudStore.playerRows.get(user.id).state.player.level, 2)
  assert.equal(cloudStore.playerRows.get(user.id).state.player.xp, 50)
  assert.equal(cloudStore.playerRows.get(user.id).state.player.coins, 50)
  assert.match(engine.getState().detail, /published to the starter cloud copy/i)
  assert.equal(local.getProgress().player.level, 2)
  assert.equal(local.getProgress().player.coins, 50)
  engine.dispose()
})
