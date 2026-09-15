import { cloudConfig } from './config.js'
import { getSupabaseClient } from './supabaseClient.js'

export const DEFAULT_DEVICE_LABEL = 'Quest Lab device'
export const DEVICE_IDS_STORAGE_KEY = 'questlab.cloud.device-ids'
export const DEVICE_LABEL_STORAGE_KEY = 'questlab.cloud.device-label'
export const SYNC_OUTBOX_STORAGE_KEY = 'questlab.cloud.sync-outbox'
export const SYNC_CURSOR_STORAGE_KEY = 'questlab.cloud.sync-cursors'
export const MAX_SYNC_OUTBOX_ENTRIES = 8

const SYNC_PLAYER_FIELDS = ['name', 'title', 'rank', 'level', 'xp', 'xp_next', 'lifetime_xp', 'hp', 'max_hp', 'coins', 'potions']
const SYNC_EQUIPMENT_FIELDS = ['armor', 'trinket', 'title']
const SYNC_COMPANION_FIELDS = ['name', 'form', 'level', 'bond', 'next_form', 'next_form_requirement']
const SYNC_HOMESTEAD_EQUIPPED_FIELDS = ['theme', 'cursor', 'hud', 'terminal']

const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)

const copyFields = (source, fields) => {
  if (!isRecord(source)) return {}
  return Object.fromEntries(fields.filter((field) => Object.prototype.hasOwnProperty.call(source, field)).map((field) => [field, source[field]]))
}

/**
 * Return the bounded, cloud-syncable subset of a campaign snapshot.
 * Projects, Codex, skills, activity and catalogs intentionally stay local in
 * this first transport slice.
 */
export function projectPlayerState(progress = {}) {
  const homestead = isRecord(progress.homestead) ? progress.homestead : {}
  const owned = Array.isArray(homestead.owned_cosmetics)
    ? [...new Set(homestead.owned_cosmetics.filter((item) => typeof item === 'string'))].slice(0, 100)
    : []
  const equipped = isRecord(homestead.equipped)
    ? copyFields(homestead.equipped, SYNC_HOMESTEAD_EQUIPPED_FIELDS)
    : {}
  return {
    player: copyFields(progress.player, SYNC_PLAYER_FIELDS),
    equipment: copyFields(progress.equipment, SYNC_EQUIPMENT_FIELDS),
    companion: copyFields(progress.companion, SYNC_COMPANION_FIELDS),
    homestead: {
      ...copyFields(homestead, ['name']),
      owned_cosmetics: owned,
      equipped,
    },
  }
}

const stableJson = (value) => {
  const normalize = (entry) => {
    if (Array.isArray(entry)) return entry.map(normalize)
    if (!isRecord(entry)) return entry
    return Object.keys(entry)
      .sort()
      .reduce((result, key) => {
        result[key] = normalize(entry[key])
        return result
      }, {})
  }
  return JSON.stringify(normalize(value))
}
const syncUserKey = (base, userId) => `${base}:${encodeURIComponent(userId)}`

const readStoredJson = (storage, key, fallback) => {
  try {
    const raw = storage?.getItem(key)
    if (!raw) return fallback
    const parsed = JSON.parse(raw)
    return parsed ?? fallback
  } catch {
    return fallback
  }
}

const writeStoredJson = (storage, key, value) => {
  try {
    storage?.setItem(key, JSON.stringify(value))
  } catch {
    // Sync metadata is recoverable; a storage quota failure must not stop Forge.
  }
}

const profileColumns = 'id,display_name,created_at,updated_at'
const deviceColumns = 'id,user_id,display_name,created_at,updated_at,last_seen_at'

const getStorage = () => {
  try {
    return globalThis.localStorage ?? null
  } catch {
    return null
  }
}

const readStorage = (storage, key) => {
  try {
    return storage?.getItem(key) ?? null
  } catch {
    return null
  }
}

const writeStorage = (storage, key, value) => {
  try {
    storage?.setItem(key, value)
  } catch {
    // Local preferences must never stop Forge from launching.
  }
}

const safeDisplayName = (value, fallback) => {
  const normalized = String(value ?? '')
    .trim()
    .replace(/\s+/g, ' ')
    .slice(0, 80)
  if (!normalized || /[\u0000-\u001f\u007f]/.test(normalized)) return fallback
  return normalized
}

const normalizeProfileName = (value) => safeDisplayName(value, 'Quest Lab player')

export function normalizeDeviceLabel(value) {
  const normalized = safeDisplayName(value, '')
  if (!normalized) return DEFAULT_DEVICE_LABEL
  // These characters are deliberately refused because they are common in
  // absolute Windows/POSIX paths. A friendly label never needs them.
  if (normalized.includes('/') || normalized.includes('\\') || normalized.includes(':')) {
    throw new Error('Device name must be a friendly label, not a filesystem path.')
  }
  return normalized
}

export function createDeviceId() {
  if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID()

  const template = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'
  return template.replace(/[xy]/g, (character) => {
    const value = Math.floor(Math.random() * 16)
    const nibble = character === 'x' ? value : (value & 0x3) | 0x8
    return nibble.toString(16)
  })
}

export function deviceIdForUser(userId, storage = getStorage()) {
  const stored = readStorage(storage, DEVICE_IDS_STORAGE_KEY)
  let ids = {}
  try {
    ids = stored ? JSON.parse(stored) : {}
  } catch {
    ids = {}
  }

  const existing = typeof ids?.[userId] === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(ids[userId]) ? ids[userId] : ''
  if (existing) return existing

  const id = createDeviceId()
  writeStorage(storage, DEVICE_IDS_STORAGE_KEY, JSON.stringify({ ...ids, [userId]: id }))
  return id
}

const userSummary = (user) => (user ? { id: user.id, email: user.email ?? '' } : null)
const profileSummary = (profile) =>
  profile
    ? {
        id: profile.id,
        display_name: profile.display_name,
        created_at: profile.created_at,
        updated_at: profile.updated_at,
      }
    : null
const deviceSummary = (device) =>
  device
    ? {
        id: device.id,
        user_id: device.user_id,
        display_name: device.display_name,
        created_at: device.created_at,
        updated_at: device.updated_at,
        last_seen_at: device.last_seen_at,
      }
    : null

const redactErrorMessage = (value) =>
  String(value || 'Cloud request failed')
    .replace(/Bearer\s+[A-Za-z0-9._~-]+/gi, 'Bearer [redacted]')
    .replace(/eyJ[A-Za-z0-9_-]{20,}/g, '[redacted-token]')

const asError = (error, fallback = 'Cloud request failed') => {
  if (error instanceof Error) {
    error.message = redactErrorMessage(error.message)
    return error
  }
  return new Error(redactErrorMessage(error?.message || error || fallback))
}

const initialState = (config) => ({
  configured: config.configured,
  configurationValid: config.valid,
  mode: config.configured && config.valid ? 'cloud-ready' : 'local',
  syncStatus: 'local',
  pendingChanges: 0,
  localRevision: null,
  cloudRevision: null,
  conflict: null,
  authStatus: 'anonymous',
  label: config.configured && config.valid ? 'Cloud ready' : 'Offline / Local Mode',
  detail: config.reason,
  error: config.valid ? null : config.reason,
  user: null,
  profile: null,
  device: null,
})

export class SyncEngine {
  constructor({ config = cloudConfig, clientFactory = getSupabaseClient, storage = getStorage(), now = () => new Date(), fetchImpl } = {}) {
    this.config = config
    this.clientFactory = clientFactory
    this.storage = storage
    this.now = now
    this.fetchImpl = fetchImpl || (typeof window !== 'undefined' && typeof globalThis.fetch === 'function' ? globalThis.fetch.bind(globalThis) : null)
    this.client = null
    this.session = null
    this.authSubscription = null
    this.restorePromise = null
    this.accountPromise = null
    this.accountUserId = null
    this.initialized = false
    this.sessionNonce = 0
    this.syncPromise = null
    this.syncTimer = null
    this.syncInterval = null
    this.latestLocalSnapshot = null
    this.syncCursor = null
    this.outbox = []
    this.cloudSnapshot = null
    this.onlineListener = null
    this.listeners = new Set()
    this.state = initialState(config)
  }

  getState() {
    return this.state
  }

  subscribe(listener) {
    this.listeners.add(listener)
    listener(this.state)
    return () => this.listeners.delete(listener)
  }

  setState(patch) {
    this.state = { ...this.state, ...patch }
    for (const listener of this.listeners) listener(this.state)
  }

  initialize() {
    if (this.initialized) return this.state
    this.initialized = true

    if (typeof globalThis.addEventListener === 'function') {
      this.onlineListener = () => void this.sync()
      globalThis.addEventListener('online', this.onlineListener)
    }

    if (!this.config.configured || !this.config.valid) {
      this.state = initialState(this.config)
      this.emit()
      return this.state
    }

    try {
      this.client = this.clientFactory(this.config)
    } catch (error) {
      this.setState({ syncStatus: 'error', label: 'Cloud unavailable · local mode', error: asError(error).message })
      return this.state
    }

    // A test/dry-run service boundary may not provide Auth. The real client
    // does, but configuration detection must never make Forge crash.
    if (!this.client?.auth?.getSession) {
      this.emit()
      return this.state
    }

    this.setState({ authStatus: 'restoring', label: 'Restoring session…', detail: 'Checking for a locally persisted Quest Lab session.', error: null })
    void this.restoreSession()
    return this.state
  }

  async restoreSession() {
    if (this.restorePromise) return this.restorePromise
    this.restorePromise = this._restoreSession()
    return this.restorePromise
  }

  async _restoreSession() {
    try {
      const { data, error } = await this.client.auth.getSession()
      if (error) throw error
      await this.applySession(data?.session ?? null)

      if (typeof this.client.auth.onAuthStateChange === 'function' && !this.authSubscription) {
        const result = this.client.auth.onAuthStateChange((event, session) => {
          if (event === 'INITIAL_SESSION') return
          queueMicrotask(() => void this.applySession(session))
        })
        this.authSubscription = result?.data?.subscription ?? result?.subscription ?? result
      }
    } catch (error) {
      const safeError = asError(error, 'Could not restore the cloud session.')
      this.setState({ authStatus: 'signed-out', syncStatus: 'error', mode: 'cloud-ready', label: 'Cloud unavailable · local mode', detail: safeError.message, error: safeError.message })
    }
    return this.state
  }

  async applySession(session) {
    const sessionNonce = ++this.sessionNonce
    this.session = session ?? null
    const user = session?.user ?? null
    if (!user) {
      this.accountPromise = null
      this.accountUserId = null
      this.syncCursor = null
      this.outbox = []
      this.cloudSnapshot = null
      this.latestLocalSnapshot = null
      this._stopSyncPolling()
      this.setState({ user: null, profile: null, device: null, authStatus: 'signed-out', syncStatus: 'local', pendingChanges: 0, conflict: null, label: 'Sign in to sync', detail: 'Forge remains available locally. Sign in when cloud sync is configured.', error: null })
      return this.state
    }

    this.setState({ user: userSummary(user), authStatus: 'signed-in', syncStatus: 'local', label: 'Signed in · local cache', detail: 'Account identity restored. Campaign fields will sync through the state gateway.', error: null })
    try {
      if (!this.accountPromise || this.accountUserId !== user.id) {
        this.accountUserId = user.id
        this.accountPromise = this.ensureAccount(user)
      }
      const account = await this.accountPromise
      if (this.sessionNonce !== sessionNonce || this._userId() !== user.id) return this.state
      this._loadSyncMetadata(user.id)
      this._startSyncPolling()
      this.setState({ profile: account.profile, device: account.device, authStatus: 'signed-in', syncStatus: 'local', label: 'Signed in · local cache', detail: 'Campaign fields will sync through the state gateway. Projects and Codex remain local in this slice.', error: null })
      void this.sync()
    } catch (error) {
      this.accountPromise = null
      const safeError = asError(error, 'Signed in, but profile/device registration could not be completed.')
      this.setState({ authStatus: 'signed-in', syncStatus: 'error', label: 'Signed in · local mode', detail: safeError.message, error: safeError.message })
    }
    return this.state
  }

  async ensureAccount(user) {
    const fallbackName = safeDisplayName(user.user_metadata?.display_name, safeDisplayName(user.email?.split('@')[0], 'Quest Lab player'))
    const profileResult = await this.client.from('profiles').select(profileColumns).eq('id', user.id).maybeSingle()
    if (profileResult.error) throw profileResult.error

    let profile = profileResult.data
    if (!profile) {
      const insertedProfile = await this.client
        .from('profiles')
        .upsert({ id: user.id, display_name: fallbackName }, { onConflict: 'id' })
        .select(profileColumns)
        .single()
      if (insertedProfile.error) throw insertedProfile.error
      profile = insertedProfile.data
    }

    const label = normalizeDeviceLabel(readStorage(this.storage, DEVICE_LABEL_STORAGE_KEY) || DEFAULT_DEVICE_LABEL)
    const devicePayload = {
      id: deviceIdForUser(user.id, this.storage),
      user_id: user.id,
      display_name: label,
      last_seen_at: this.now().toISOString(),
    }
    const deviceResult = await this.client
      .from('devices')
      .upsert(devicePayload, { onConflict: 'id' })
      .select(deviceColumns)
      .single()
    if (deviceResult.error) throw deviceResult.error

    return { profile: profileSummary(profile), device: deviceSummary(deviceResult.data) }
  }

  async signIn(email, password) {
    if (!this.client?.auth) throw new Error('Cloud sign-in is unavailable in Offline / Local Mode.')
    this.setState({ authStatus: 'signing-in', detail: 'Signing in…', error: null })
    const { data, error } = await this.client.auth.signInWithPassword({ email: String(email).trim(), password })
    if (error) {
      const safeError = asError(error, 'Sign-in failed.')
      this.setState({ authStatus: 'signed-out', syncStatus: 'local', label: 'Sign-in failed', detail: safeError.message, error: safeError.message })
      throw safeError
    }
    await this.applySession(data?.session ?? null)
    return this.state
  }

  async signUp(email, password, displayName) {
    if (!this.client?.auth) throw new Error('Cloud sign-up is unavailable in Offline / Local Mode.')
    const name = normalizeProfileName(displayName)
    this.setState({ authStatus: 'signing-up', detail: 'Creating your Quest Lab account…', error: null })
    const { data, error } = await this.client.auth.signUp({
      email: String(email).trim(),
      password,
      options: { data: { display_name: name } },
    })
    if (error) {
      const safeError = asError(error, 'Account creation failed.')
      this.setState({ authStatus: 'signed-out', syncStatus: 'local', label: 'Sign-up failed', detail: safeError.message, error: safeError.message })
      throw safeError
    }
    if (data?.session) {
      await this.applySession(data.session)
    } else {
      this.setState({ authStatus: 'pending-email', syncStatus: 'local', label: 'Check your email', detail: 'Supabase requires email confirmation before this account can sign in.', error: null })
    }
    return this.state
  }

  async signOut() {
    if (!this.client?.auth) {
      await this.applySession(null)
      return this.state
    }
    this.setState({ authStatus: 'signing-out', detail: 'Signing out…', error: null })
    const { error } = await this.client.auth.signOut()
    if (error) throw asError(error, 'Sign-out failed.')
    await this.applySession(null)
    return this.state
  }

  async setDeviceLabel(value) {
    const label = normalizeDeviceLabel(value)
    writeStorage(this.storage, DEVICE_LABEL_STORAGE_KEY, label)
    if (!this.session?.user || !this.client) {
      this.setState({ device: this.state.device ? { ...this.state.device, display_name: label } : this.state.device })
      return this.state
    }

    const payload = {
      id: deviceIdForUser(this.session.user.id, this.storage),
      user_id: this.session.user.id,
      display_name: label,
      last_seen_at: this.now().toISOString(),
    }
    const result = await this.client.from('devices').upsert(payload, { onConflict: 'id' }).select(deviceColumns).single()
    if (result.error) throw asError(result.error, 'Device name could not be saved.')
    this.setState({ device: deviceSummary(result.data), error: null })
    return this.state
  }

  _userId() {
    return typeof this.session?.user?.id === 'string' ? this.session.user.id : ''
  }

  _outboxKey(userId = this._userId()) {
    return userId ? syncUserKey(SYNC_OUTBOX_STORAGE_KEY, userId) : SYNC_OUTBOX_STORAGE_KEY
  }

  _cursorKey(userId = this._userId()) {
    return userId ? syncUserKey(SYNC_CURSOR_STORAGE_KEY, userId) : SYNC_CURSOR_STORAGE_KEY
  }

  _readOutbox(userId = this._userId()) {
    const stored = readStoredJson(this.storage, this._outboxKey(userId), [])
    if (!Array.isArray(stored)) return []
    return stored
      .filter((entry) => isRecord(entry) && Number.isInteger(entry.localRevision) && entry.localRevision >= 0 && Number.isInteger(entry.baseCloudRevision) && entry.baseCloudRevision >= 0 && isRecord(entry.projection))
      .map((entry) => ({
        localRevision: entry.localRevision,
        baseCloudRevision: entry.baseCloudRevision,
        projection: projectPlayerState(entry.projection),
        queuedAt: typeof entry.queuedAt === 'string' ? entry.queuedAt : this.now().toISOString(),
      }))
      .sort((left, right) => left.localRevision - right.localRevision)
      .slice(-MAX_SYNC_OUTBOX_ENTRIES)
  }

  _writeOutbox(entries = this.outbox, userId = this._userId()) {
    this.outbox = entries.slice(-MAX_SYNC_OUTBOX_ENTRIES)
    if (userId) writeStoredJson(this.storage, this._outboxKey(userId), this.outbox)
    this.setState({ pendingChanges: this.outbox.length })
  }

  _readCursor(userId = this._userId()) {
    const cursor = readStoredJson(this.storage, this._cursorKey(userId), null)
    if (!isRecord(cursor) || !Number.isInteger(cursor.localRevision) || cursor.localRevision < 0 || !Number.isInteger(cursor.cloudRevision) || cursor.cloudRevision < 0) return null
    return { localRevision: cursor.localRevision, cloudRevision: cursor.cloudRevision }
  }

  _writeCursor(cursor, userId = this._userId()) {
    if (!cursor || !userId) return
    this.syncCursor = { localRevision: cursor.localRevision, cloudRevision: cursor.cloudRevision }
    writeStoredJson(this.storage, this._cursorKey(userId), this.syncCursor)
    this.setState({ localRevision: cursor.localRevision, cloudRevision: cursor.cloudRevision })
  }

  _loadSyncMetadata(userId = this._userId()) {
    this.syncCursor = this._readCursor(userId)
    this.outbox = this._readOutbox(userId)
    this.setState({
      pendingChanges: this.outbox.length,
      localRevision: this.syncCursor?.localRevision ?? null,
      cloudRevision: this.syncCursor?.cloudRevision ?? null,
    })
  }

  _enqueueLocal(snapshot, baseCloudRevision) {
    if (!snapshot || !Number.isInteger(snapshot.revision) || snapshot.revision < 0) return
    const entry = {
      localRevision: snapshot.revision,
      baseCloudRevision: Math.max(0, Number(baseCloudRevision) || 0),
      projection: projectPlayerState(snapshot.projection),
      queuedAt: this.now().toISOString(),
    }
    const remaining = this.outbox.filter((item) => item.localRevision !== entry.localRevision)
    this._writeOutbox([...remaining, entry])
  }

  _clearOutboxThrough(revision) {
    this._writeOutbox(this.outbox.filter((entry) => entry.localRevision > revision))
  }

  _scheduleSync() {
    if (this.syncTimer || !this.session?.user || !this.client) return
    const run = () => {
      this.syncTimer = null
      void this.sync()
    }
    if (typeof queueMicrotask === 'function') queueMicrotask(run)
    else this.syncTimer = setTimeout(run, 0)
    if (typeof queueMicrotask === 'function') this.syncTimer = true
  }

  scheduleSync() {
    this._scheduleSync()
  }

  _startSyncPolling() {
    if (this.syncInterval || typeof window === 'undefined' || typeof window.setInterval !== 'function') return
    this.syncInterval = window.setInterval(() => {
      if (this.session?.user && this.client) void this.sync()
    }, 2000)
  }

  _stopSyncPolling() {
    if (this.syncInterval && typeof window !== 'undefined' && typeof window.clearInterval === 'function') window.clearInterval(this.syncInterval)
    this.syncInterval = null
  }

  observeCampaign(campaign) {
    if (!isRecord(campaign)) return this.state
    const revision = Number(campaign.revision ?? campaign.progress?.meta?.revision ?? 0)
    if (!Number.isInteger(revision) || revision < 0) return this.state
    this.latestLocalSnapshot = {
      revision,
      projection: projectPlayerState(campaign.progress || {}),
      metadata: campaign.metadata || {},
    }
    if (this.session?.user && this.client) this._scheduleSync()
    return this.state
  }

  async _responseJson(response) {
    try {
      return await response.json()
    } catch {
      try {
        return JSON.parse(await response.text())
      } catch {
        return null
      }
    }
  }

  async _fetchLocalSnapshot() {
    if (typeof this.fetchImpl !== 'function') throw new Error('The local state gateway is unavailable.')
    const response = await this.fetchImpl('/api/state/sync', { headers: { Accept: 'application/json' } })
    const body = await this._responseJson(response)
    if (!response?.ok) throw new Error(body?.detail || `Local state gateway returned ${response?.status || 'an error'}.`)
    const revision = Number(body?.revision ?? body?.metadata?.revision)
    if (!Number.isInteger(revision) || revision < 0 || !isRecord(body?.projection)) throw new Error('The local state gateway returned an invalid sync snapshot.')
    return { revision, projection: projectPlayerState(body.projection), metadata: body.metadata || {} }
  }

  async _applyCloudProjection(local, cloud) {
    if (typeof this.fetchImpl !== 'function') throw new Error('The local state gateway is unavailable.')
    const response = await this.fetchImpl('/api/state/sync/apply', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        expected_revision: local.revision,
        cloud_revision: cloud.revision,
        projection: cloud.state,
      }),
    })
    const body = await this._responseJson(response)
    if (!response?.ok) {
      const error = new Error(body?.detail || `Local state gateway returned ${response?.status || 'an error'}.`)
      error.status = response?.status
      throw error
    }
    const revision = Number(body?.revision)
    if (!Number.isInteger(revision) || revision < 0) throw new Error('The local state gateway returned an invalid cloud-apply revision.')
    return { ...body, revision, projection: projectPlayerState(body.projection || cloud.state) }
  }

  _normalizeCloudRow(row) {
    if (!row) return null
    const revision = Number(row.revision)
    if (!Number.isInteger(revision) || revision < 0) throw new Error('Cloud player state returned an invalid revision.')
    if (!isRecord(row.state)) throw new Error('Cloud player state returned an invalid projection.')
    return {
      revision,
      state: projectPlayerState(row.state),
      deviceId: row.device_id || null,
      updatedAt: row.updated_at || null,
    }
  }

  async _readCloudState() {
    if (!this.client?.from) throw new Error('Cloud player-state access is unavailable.')
    const result = await this.client.from('player_state').select('state,revision,device_id,updated_at').maybeSingle()
    if (result?.error) throw asError(result.error, 'Cloud player state could not be read.')
    return this._normalizeCloudRow(result?.data)
  }

  async _saveCloudState(expectedRevision, projection) {
    if (!this.client?.rpc) throw new Error('Cloud player-state writes are unavailable.')
    const result = await this.client.rpc('save_player_state', {
      expected_revision: expectedRevision,
      next_state: projectPlayerState(projection),
      source_device_id: this.state.device?.id || null,
    })
    if (result?.error) {
      const error = asError(result.error, 'Cloud player state could not be saved.')
      error.code = result.error.code || error.code
      error.status = result.error.status || error.status
      throw error
    }
    const row = Array.isArray(result?.data) ? result.data[0] : result?.data
    const normalized = this._normalizeCloudRow(row)
    if (!normalized) throw new Error('Cloud player-state save returned no row.')
    return normalized
  }

  _projectionsEqual(left, right) {
    return stableJson(left) === stableJson(right)
  }

  _setSynced(local, cloud, detail = 'Campaign fields are synced.') {
    this.cloudSnapshot = cloud
    this.setState({
      syncStatus: 'synced',
      label: 'Synced',
      detail,
      error: null,
      conflict: null,
      localRevision: local?.revision ?? this.state.localRevision,
      cloudRevision: cloud?.revision ?? this.state.cloudRevision,
      pendingChanges: this.outbox.length,
    })
  }

  _setConflict(reason, local, cloud) {
    this.cloudSnapshot = cloud || null
    const conflict = {
      reason,
      localRevision: local?.revision ?? null,
      cloudRevision: cloud?.revision ?? null,
    }
    this.setState({
      syncStatus: 'conflict',
      label: 'Sync conflict',
      detail: 'Choose which validated campaign copy should win.',
      error: null,
      conflict,
      localRevision: local?.revision ?? null,
      cloudRevision: cloud?.revision ?? null,
      pendingChanges: this.outbox.length,
    })
    return this.state
  }

  _isConflictError(error) {
    const code = String(error?.code || '').toLowerCase()
    const message = String(error?.message || '').toLowerCase()
    return code === '40001' || error?.status === 409 || message.includes('conflict') || message.includes('revision')
  }

  async _syncNow() {
    if (!this.session?.user || !this.client) return this.state
    const sessionNonce = this.sessionNonce
    const userId = this._userId()
    const sessionIsCurrent = () => this.sessionNonce === sessionNonce && this._userId() === userId
    this.setState({ syncStatus: 'syncing', label: 'Syncing…', detail: 'Comparing the local cache with the cloud revision.', error: null })
    const local = await this._fetchLocalSnapshot()
    if (!sessionIsCurrent()) return this.state
    this.latestLocalSnapshot = local
    let cursor = this.syncCursor || this._readCursor()

    if ((!cursor && local.revision > 0) || (cursor && local.revision > cursor.localRevision)) {
      this._enqueueLocal(local, cursor?.cloudRevision ?? 0)
    }
    let cloud = await this._readCloudState()
    if (!sessionIsCurrent()) return this.state

    // A local revision may have advanced because of a local-only domain
    // (Codex, activity, encounter history). Do not publish a no-op cloud
    // snapshot or manufacture a conflict when the bounded projection still
    // matches the current cloud row.
    if (cursor && cloud && local.revision > cursor.localRevision && this._projectionsEqual(local.projection, cloud.state)) {
      this._clearOutboxThrough(local.revision)
      this._writeCursor({ localRevision: local.revision, cloudRevision: cloud.revision })
      this._setSynced(local, cloud, 'Local-only campaign history changed; synced player fields are unchanged.')
      return this.state
    }

    const pushLocal = async (expectedCloudRevision, entry = null) => {
      const captured = entry || { localRevision: local.revision, projection: local.projection }
      try {
        const saved = await this._saveCloudState(expectedCloudRevision, captured.projection)
        if (!sessionIsCurrent()) return this.state
        this._writeCursor({ localRevision: captured.localRevision, cloudRevision: saved.revision })
        this._clearOutboxThrough(captured.localRevision)
        cloud = saved
        const after = await this._fetchLocalSnapshot()
        if (!sessionIsCurrent()) return this.state
        this.latestLocalSnapshot = after
        if (after.revision > captured.localRevision) {
          this._enqueueLocal(after, saved.revision)
          this.setState({ syncStatus: 'syncing', label: 'Syncing…', detail: 'A newer local mutation is queued for the next cloud revision.' })
        } else {
          this._setSynced(after, saved)
        }
        return saved
      } catch (error) {
        if (!sessionIsCurrent()) return this.state
        if (this._isConflictError(error)) return this._setConflict('Cloud changed while this device was saving.', local, await this._readCloudState())
        throw error
      }
    }

    if (!cursor) {
      if (!cloud) {
        await pushLocal(0)
        return this.state
      }
      if (this._projectionsEqual(local.projection, cloud.state)) {
        this._writeCursor({ localRevision: local.revision, cloudRevision: cloud.revision })
        this._setSynced(local, cloud, 'Local and cloud campaign copies already match.')
        return this.state
      }
      if (local.revision === 0 && cloud.revision > 0) {
        const applied = await this._applyCloudProjection(local, cloud)
        const refreshed = await this._fetchLocalSnapshot()
        this.latestLocalSnapshot = refreshed
        this._writeCursor({ localRevision: applied.revision, cloudRevision: cloud.revision })
        this._clearOutboxThrough(refreshed.revision)
        this._setSynced(refreshed, cloud, 'Pulled the existing cloud campaign into the local cache.')
        return this.state
      }
      if (cloud.revision === 0 && local.revision > 0) {
        await pushLocal(0)
        return this.state
      }
      return this._setConflict('Both local and cloud copies contain independent progress.', local, cloud)
    }

    if (!cloud || cloud.revision < cursor.cloudRevision) return this._setConflict('The cloud revision moved backwards or was removed.', local, cloud)

    const pending = this.outbox[this.outbox.length - 1]
    if (pending) {
      if (cloud.revision !== pending.baseCloudRevision) return this._setConflict('Cloud progress changed while this device was offline.', local, cloud)
      await pushLocal(cloud.revision, pending)
      return this.state
    }

    if (cloud.revision > cursor.cloudRevision) {
      if (local.revision !== cursor.localRevision) return this._setConflict('Local progress changed without a queued sync record.', local, cloud)
      const applied = await this._applyCloudProjection(local, cloud)
      const refreshed = await this._fetchLocalSnapshot()
      this.latestLocalSnapshot = refreshed
      this._writeCursor({ localRevision: applied.revision, cloudRevision: cloud.revision })
      this._clearOutboxThrough(refreshed.revision)
      this._setSynced(refreshed, cloud, 'Pulled newer validated campaign progress.')
      return this.state
    }

    if (!this._projectionsEqual(local.projection, cloud.state)) return this._setConflict('Local and cloud campaign copies differ at the same revision.', local, cloud)
    this._writeCursor({ localRevision: local.revision, cloudRevision: cloud.revision })
    this._setSynced(local, cloud)
    return this.state
  }

  sync() {
    if (!this.session?.user || !this.client) return Promise.resolve(this.state)
    if (this.syncPromise) return this.syncPromise
    const sessionNonce = this.sessionNonce
    this.syncPromise = this._syncNow()
      .catch(async (error) => {
        if (this.sessionNonce !== sessionNonce) return this.state
        const safeError = asError(error, 'Cloud sync failed.')
        if (this._isConflictError(error)) {
          let cloud = this.cloudSnapshot
          try {
            cloud = await this._readCloudState()
          } catch {
            // Keep the last safe cloud snapshot when a conflict refresh is unavailable.
          }
          return this._setConflict('Cloud rejected this save because another revision won.', this.latestLocalSnapshot, cloud)
        }
        this.setState({ syncStatus: 'error', label: 'Cloud sync error', detail: safeError.message, error: safeError.message, pendingChanges: this.outbox.length })
        return this.state
      })
      .finally(() => {
        this.syncPromise = null
      })
    return this.syncPromise
  }

  async resolveConflict(choice) {
    if (!this.state.conflict || !this.session?.user || !this.client) throw new Error('There is no active cloud conflict to resolve.')
    if (choice !== 'cloud' && choice !== 'local') throw new Error('Conflict resolution must choose cloud or local.')
    this.setState({ syncStatus: 'syncing', label: 'Resolving sync…', detail: choice === 'cloud' ? 'Applying the cloud copy to this device.' : 'Publishing this device copy explicitly.', error: null })
    try {
      if (choice === 'cloud') {
        const cloud = (await this._readCloudState()) || this.cloudSnapshot
        if (!cloud) throw new Error('The cloud copy is no longer available.')
        const local = await this._fetchLocalSnapshot()
        const applied = await this._applyCloudProjection(local, cloud)
        const refreshed = await this._fetchLocalSnapshot()
        this.latestLocalSnapshot = refreshed
        this._clearOutboxThrough(refreshed.revision)
        this._writeCursor({ localRevision: applied.revision, cloudRevision: cloud.revision })
        this._setSynced(refreshed, cloud, 'Cloud copy selected; local cache updated.')
      } else {
        const local = await this._fetchLocalSnapshot()
        const cloud = await this._readCloudState()
        const saved = await this._saveCloudState(cloud?.revision ?? 0, local.projection)
        this.latestLocalSnapshot = local
        this._clearOutboxThrough(local.revision)
        this._writeCursor({ localRevision: local.revision, cloudRevision: saved.revision })
        this._setSynced(local, saved, 'This device copy selected and published explicitly.')
      }
      return this.state
    } catch (error) {
      if (this._isConflictError(error)) {
        let cloud = this.cloudSnapshot
        try {
          cloud = await this._readCloudState()
        } catch {
          // Keep the last safe cloud snapshot when the conflict refresh is unavailable.
        }
        return this._setConflict('Cloud changed again; choose a copy once more.', this.latestLocalSnapshot, cloud)
      }
      const safeError = asError(error, 'Conflict resolution failed.')
      this.setState({ syncStatus: 'error', label: 'Cloud sync error', detail: safeError.message, error: safeError.message })
      throw safeError
    }
  }

  emit() {
    for (const listener of this.listeners) listener(this.state)
  }

  dispose() {
    this.authSubscription?.unsubscribe?.()
    this.authSubscription = null
    if (this.onlineListener && typeof globalThis.removeEventListener === 'function') globalThis.removeEventListener('online', this.onlineListener)
    this.onlineListener = null
    this._stopSyncPolling()
    if (this.syncTimer && typeof this.syncTimer !== 'boolean') clearTimeout(this.syncTimer)
    this.syncTimer = null
    this.listeners.clear()
  }
}

export const syncEngine = new SyncEngine()
