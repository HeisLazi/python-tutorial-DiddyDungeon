import { cloudConfig } from './config.js'
import { getSupabaseClient } from './supabaseClient.js'

export const DEFAULT_DEVICE_LABEL = 'Quest Lab device'
export const DEVICE_IDS_STORAGE_KEY = 'questlab.cloud.device-ids'
export const DEVICE_LABEL_STORAGE_KEY = 'questlab.cloud.device-label'

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

  const existing = typeof ids?.[userId] === 'string' ? ids[userId] : ''
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
  authStatus: 'anonymous',
  label: config.configured && config.valid ? 'Cloud ready' : 'Offline / Local Mode',
  detail: config.reason,
  error: config.valid ? null : config.reason,
  user: null,
  profile: null,
  device: null,
})

export class SyncEngine {
  constructor({ config = cloudConfig, clientFactory = getSupabaseClient, storage = getStorage(), now = () => new Date() } = {}) {
    this.config = config
    this.clientFactory = clientFactory
    this.storage = storage
    this.now = now
    this.client = null
    this.session = null
    this.authSubscription = null
    this.restorePromise = null
    this.accountPromise = null
    this.accountUserId = null
    this.initialized = false
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
    this.session = session ?? null
    const user = session?.user ?? null
    if (!user) {
      this.accountPromise = null
      this.accountUserId = null
      this.setState({ user: null, profile: null, device: null, authStatus: 'signed-out', syncStatus: 'local', label: 'Sign in to sync', detail: 'Forge remains available locally. Sign in when cloud sync is configured.', error: null })
      return this.state
    }

    this.setState({ user: userSummary(user), authStatus: 'signed-in', syncStatus: 'local', label: 'Signed in', detail: 'Account identity restored. Cloud save migration is a later milestone.', error: null })
    try {
      if (!this.accountPromise || this.accountUserId !== user.id) {
        this.accountUserId = user.id
        this.accountPromise = this.ensureAccount(user)
      }
      const account = await this.accountPromise
      this.setState({ profile: account.profile, device: account.device, authStatus: 'signed-in', syncStatus: 'local', label: 'Signed in', detail: 'Signed in. Quest Lab is using local progress until Sync Engine v1.', error: null })
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

  emit() {
    for (const listener of this.listeners) listener(this.state)
  }

  dispose() {
    this.authSubscription?.unsubscribe?.()
    this.authSubscription = null
    this.listeners.clear()
  }
}

export const syncEngine = new SyncEngine()
