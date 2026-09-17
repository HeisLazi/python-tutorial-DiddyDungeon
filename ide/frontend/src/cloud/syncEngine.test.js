import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveCloudConfig } from './config.js'
import { AVATAR_MAX_BYTES, avatarObjectPath, readCachedAvatar, validateAvatarDataUrl, writeCachedAvatar } from './avatarStorage.js'
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
      const sourceDevice = deviceRows.get(args.source_device_id)
      if (!sourceDevice || sourceDevice.user_id !== user.id) {
        return { data: null, error: { code: '42501', message: 'source_device_id does not belong to the authenticated account' } }
      }
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
      if (incoming.campaign) {
        for (const [domain, value] of Object.entries(incoming.campaign)) {
          progress[domain] = clone(value)
        }
      }
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

test('signed-in status names the campaign surfaces that share the sync gateway', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const user = { id: '00000000-0000-4000-8000-000000000011', email: 'surfaces@example.test' }
  const engine = new SyncEngine({ config, clientFactory: () => fakeCloudClient(user), storage: new MemoryStorage(), fetchImpl: fakeLocalApi(campaign(0), 0).fetch })
  const details = []
  engine.subscribe((state) => details.push(state.detail))

  engine.initialize()
  await engine.restoreSession()

  assert.equal(details.some((detail) => /Campaign, Journal and Codex fields will sync through the state gateway/.test(detail)), true)
  assert.equal(details.some((detail) => /Account identity restored\. Campaign fields will sync through the state gateway\./.test(detail)), false)
  engine.dispose()
})

test('email delivery rate limits use a bounded sign-up message', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const user = { id: '00000000-0000-4000-8000-000000000012', email: 'rate-limit@example.test' }
  const client = fakeCloudClient(user)
  client.auth.signUp = async () => ({ data: { session: null }, error: { status: 429, error_code: 'over_email_send_rate_limit', message: 'email rate limit exceeded' } })
  const engine = new SyncEngine({ config, clientFactory: () => client, storage: new MemoryStorage(), fetchImpl: fakeLocalApi(campaign(0), 0).fetch })
  engine.initialize()
  await engine.restoreSession()

  await assert.rejects(() => engine.signUp(user.email, 'not-a-real-password', 'Codex QA'), /Email delivery is temporarily rate-limited\. Try again later; no account was created\./)
  assert.equal(engine.getState().label, 'Sign-up failed')
  assert.match(engine.getState().detail, /Try again later/)
  assert.doesNotMatch(engine.getState().detail, /over_email_send_rate_limit/)
  engine.dispose()
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
  assert.equal(readCachedAvatar(storageA), '')

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

test('signed-in avatar removal cannot resurrect an unscoped local portrait', async () => {
  const config = resolveCloudConfig({
    VITE_SUPABASE_URL: 'https://example.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'public-anon-key',
  })
  const user = { id: '00000000-0000-4000-8000-000000000052', email: 'avatar-removal@example.test' }
  const storage = new MemoryStorage()
  const staleLocal = 'data:image/webp;base64,U3RhbGUgYXZhdGFy'
  writeCachedAvatar(staleLocal, storage)
  const engine = new SyncEngine({ config, clientFactory: () => fakeCloudClient(user), storage })

  engine.initialize()
  await engine.restoreSession()
  assert.equal(engine.getState().avatar.cached, false)
  await engine._refreshCloudAvatar(null, user.id)

  assert.equal(engine.getState().avatar.cached, false)
  assert.equal(engine.getState().avatar.status, 'empty')
  assert.equal(readCachedAvatar(storage), staleLocal)
  engine.dispose()
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

test('player-state projection carries bounded campaign evidence but excludes local logs and catalogs', () => {
  const projection = projectPlayerState({
    player: { level: 3, coins: 20, secret: 'local' },
    projects: [{ name: 'Blackjack' }],
    codex: { encounters: [{ mob_name: 'hidden', player_notes: ['Review indexing before the next encounter.'] }] },
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
  assert.deepEqual(projection.campaign.projects, [{ name: 'Blackjack' }])
  assert.deepEqual(projection.campaign.codex, { encounters: [{ mob_name: 'hidden', player_notes: ['Review indexing before the next encounter.'] }] })
  assert.deepEqual(projection.campaign.skills, [{ concept: 'Variables' }])
  assert.equal(Object.prototype.hasOwnProperty.call(projection, 'state_events'), false)
  assert.equal(Object.prototype.hasOwnProperty.call(projection.campaign, 'profile'), false)
  assert.equal(Object.prototype.hasOwnProperty.call(projection.homestead, 'catalog'), false)
})

test('campaign evidence and a Dungeon checkpoint travel through the same cloud revision', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const cloudStore = { playerRows: new Map(), deviceRows: new Map() }
  const user = { id: '00000000-0000-4000-8000-000000000022', email: 'campaign@example.test' }
  const source = campaign(55, 2)
  source.projects = [{ branch: '01-blackjack', name: 'Blackjack', status: 'active', progress: 38, mobs: [{ name: 'The Empty Table', status: 'defeated' }, { name: 'The Hitman', status: 'available', resolve: 8, max_resolve: 8 }] }]
  source.codex = { encounters: [{ id: 'blackjack-empty-table', project_id: '01-blackjack', mob_name: 'The Empty Table', concept: 'Variables', status: 'defeated', player_notes: ['Review indexing before the next encounter.'], results: [{ outcome: 'defeated', evidence_id: 'legacy-1' }] }] }
  source.dungeon_run = {
    status: 'active', run_id: 'dungeon-1', floor: 2, room: 4, room_type: 'encounter', editor_content: 'answer = 1',
    inventory: [{ id: 'run-lantern', name: 'Run Lantern', kind: 'trinket', description: 'A temporary run aid.' }],
    question: { id: 'question-1', question_type: 'code_checkpoint', concept_id: 'variables', difficulty: 2, prompt: 'Use a variable.', options: [], answer_key: 'must-not-travel' },
  }
  const localA = fakeLocalApi(source, 4)
  const localB = fakeLocalApi(campaign(0), 0)
  const clientA = fakeCloudClient(user, { cloudStore })
  const clientB = fakeCloudClient(user, { cloudStore })
  const engineA = new SyncEngine({ config, clientFactory: () => clientA, storage: new MemoryStorage(), fetchImpl: localA.fetch })
  const engineB = new SyncEngine({ config, clientFactory: () => clientB, storage: new MemoryStorage(), fetchImpl: localB.fetch })

  engineA.initialize()
  await engineA.restoreSession()
  engineA.observeCampaign({ revision: 4, progress: source })
  await engineA.sync()
  const cloudCampaign = cloudStore.playerRows.get(user.id).state.campaign
  assert.equal(cloudCampaign.projects[0].mobs[0].status, 'defeated')
  assert.equal(cloudCampaign.codex.encounters[0].mob_name, 'The Empty Table')
  assert.deepEqual(cloudCampaign.codex.encounters[0].player_notes, ['Review indexing before the next encounter.'])
  assert.equal(cloudCampaign.dungeon_run.run_id, 'dungeon-1')
  assert.deepEqual(cloudCampaign.dungeon_run.inventory, [{ id: 'run-lantern', name: 'Run Lantern', kind: 'trinket', description: 'A temporary run aid.' }])
  assert.equal(Object.prototype.hasOwnProperty.call(cloudCampaign.dungeon_run.question, 'answer_key'), false)

  engineB.initialize()
  await engineB.restoreSession()
  await engineB.sync()
  assert.equal(localB.getProgress().projects[0].mobs[1].name, 'The Hitman')
  assert.equal(localB.getProgress().codex.encounters[0].mob_name, 'The Empty Table')
  assert.deepEqual(localB.getProgress().codex.encounters[0].player_notes, ['Review indexing before the next encounter.'])
  assert.equal(localB.getProgress().dungeon_run.run_id, 'dungeon-1')
  assert.deepEqual(localB.getProgress().dungeon_run.inventory, [{ id: 'run-lantern', name: 'Run Lantern', kind: 'trinket', description: 'A temporary run aid.' }])
  engineA.dispose()
  engineB.dispose()
})

test('two isolated engine instances sync through revision-aware push, pull, offline outbox and explicit conflict resolution', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const cloudStore = { playerRows: new Map(), deviceRows: new Map() }
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

test('cloud writes require an account-owned device provenance row', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const user = { id: '00000000-0000-4000-8000-000000000061', email: 'device-owner@example.test' }
  const cloudStore = { playerRows: new Map(), deviceRows: new Map() }
  const local = fakeLocalApi(campaign(0), 0)
  const client = fakeCloudClient(user, { cloudStore })
  const engine = new SyncEngine({ config, clientFactory: () => client, storage: new MemoryStorage(), fetchImpl: local.fetch })

  engine.initialize()
  await engine.restoreSession()
  const ownedDevice = engine.getState().device.id
  assert.equal(cloudStore.deviceRows.get(ownedDevice).user_id, user.id)

  engine.state = { ...engine.getState(), device: { ...engine.getState().device, id: '00000000-0000-4000-8000-000000000062' } }
  await assert.rejects(() => engine._saveCloudState(0, campaign(1)), (error) => error.code === '42501')
  engine.dispose()
})

test('only protocol conflict code or status enters conflict handling', () => {
  const engine = new SyncEngine()
  assert.equal(engine._isConflictError({ code: '40001' }), true)
  assert.equal(engine._isConflictError({ status: 409 }), true)
  assert.equal(engine._isConflictError({ message: 'revision metadata is missing' }), false)
  assert.equal(engine._isConflictError({ message: 'conflict-looking validation failure' }), false)
})

test('an older hosted validator explains the queued campaign migration requirement', async () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co', VITE_SUPABASE_ANON_KEY: 'public-anon-key' })
  const user = { id: '00000000-0000-4000-8000-000000000071', email: 'schema@example.test' }
  const local = fakeLocalApi(campaign(3), 1)
  const client = fakeCloudClient(user)
  client.rpc = async () => ({ data: null, error: { message: 'next_state contains unsupported domains' } })
  const engine = new SyncEngine({ config, clientFactory: () => client, storage: new MemoryStorage(), fetchImpl: local.fetch })

  engine.initialize()
  await engine.restoreSession()
  await engine.sync()

  assert.equal(engine.getState().syncStatus, 'error')
  assert.equal(engine.getState().label, 'Cloud schema needs migration')
  assert.match(engine.getState().detail, /20260917000100_player_state_campaign_projection\.sql/)
  assert.equal(engine.getState().pendingChanges, 1)
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
