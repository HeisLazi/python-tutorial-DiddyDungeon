import { cloudConfig } from './config.js'
import { getSupabaseClient } from './supabaseClient.js'
import {
  AVATAR_BUCKET,
  AVATAR_CLOUD_MIME_TYPES,
  AVATAR_MAX_BYTES,
  avatarObjectPath,
  blobToDataUrl,
  dataUrlToBlob,
  readCachedAvatar,
  removeCachedAvatar,
  validateAvatarDataUrl,
  writeCachedAvatar,
} from './avatarStorage.js'

export const DEFAULT_DEVICE_LABEL = 'Quest Lab device'
export const DEVICE_IDS_STORAGE_KEY = 'questlab.cloud.device-ids'
export const DEVICE_LABEL_STORAGE_KEY = 'questlab.cloud.device-label'
export const SYNC_OUTBOX_STORAGE_KEY = 'questlab.cloud.sync-outbox'
export const SYNC_CURSOR_STORAGE_KEY = 'questlab.cloud.sync-cursors'
export const CHECKOUT_NAMESPACE_RE = /^checkout-[0-9a-f]{8,64}$/i
export const MAX_SYNC_OUTBOX_ENTRIES = 8

const SYNC_PLAYER_FIELDS = ['name', 'title', 'rank', 'level', 'xp', 'xp_next', 'lifetime_xp', 'hp', 'max_hp', 'coins', 'potions']
const SYNC_EQUIPMENT_FIELDS = ['armor', 'trinket', 'title', 'owned_armor', 'owned_trinkets']
const SYNC_EQUIPMENT_LIST_FIELDS = ['owned_armor', 'owned_trinkets']
const SYNC_COMPANION_FIELDS = ['name', 'form', 'level', 'bond', 'next_form', 'next_form_requirement']
const SYNC_HOMESTEAD_EQUIPPED_FIELDS = ['theme', 'cursor', 'hud', 'terminal']
const SYNC_PROJECT_FIELDS = ['order', 'branch', 'name', 'status', 'progress', 'boss', 'boss_status', 'clean_clear_eligible', 'completed', 'completed_at', 'clean_clear', 'mob_sequence_complete', 'creative_discoveries', 'boss_validation']
const SYNC_MOB_FIELDS = ['name', 'status', 'assist', 'concept', 'encounter', 'max_resolve', 'resolve', 'impact_applied', 'objective_attempts']
const SYNC_CODEX_FIELDS = ['id', 'project_id', 'mob_name', 'concept', 'status', 'question_types', 'weaknesses', 'notes', 'player_notes', 'attempts', 'results', 'interview_history', 'mastery']
const SYNC_DUNGEON_FIELDS = ['status', 'run_id', 'seed', 'concept_id', 'floor', 'room', 'room_type', 'score', 'run_coins', 'started_at', 'updated_at', 'ended_at', 'loadout', 'inventory', 'question', 'question_number', 'room_choices', 'editor_content', 'last_result', 'history', 'attempts']
const SYNC_DUNGEON_INVENTORY_FIELDS = ['id', 'name', 'kind', 'armor', 'trinket', 'description']

const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value)

const copyFields = (source, fields) => {
  if (!isRecord(source)) return {}
  return Object.fromEntries(fields.filter((field) => Object.prototype.hasOwnProperty.call(source, field)).map((field) => [field, source[field]]))
}

const boundedTextList = (value, limit = 100) => (Array.isArray(value) ? [...new Set(value.filter((item) => typeof item === 'string' && item.trim()))].slice(0, limit) : [])
const boundedRecords = (value, fields, limit = 100) => (Array.isArray(value) ? value.filter(isRecord).slice(-limit).map((item) => copyFields(item, fields)) : [])

const projectCampaignState = (progress = {}) => {
  const source = isRecord(progress?.campaign) ? progress.campaign : progress
  const campaign = {}
  if (isRecord(source.learning_state)) campaign.learning_state = copyFields(source.learning_state, ['project', 'concept', 'phase', 'reference_mode', 'clean_clear_eligible'])
  if (isRecord(source.streak)) {
    campaign.streak = copyFields(source.streak, ['current', 'longest', 'last_active', 'freeze_tokens'])
    if (Array.isArray(source.streak.days_logged)) campaign.streak.days_logged = boundedTextList(source.streak.days_logged)
  }
  if (Array.isArray(source.skills)) {
    campaign.skills = source.skills.filter(isRecord).slice(0, 50).map((skill) => ({
      ...copyFields(skill, ['name', 'concept', 'status', 'evidence', 'interview_passes']),
      ...(isRecord(skill.shield) ? { shield: copyFields(skill.shield, ['tier', 'charges', 'max_charges']) } : {}),
    }))
  }
  if (isRecord(source.stats)) campaign.stats = copyFields(source.stats, ['sessions', 'projects_cleared', 'bosses_defeated', 'mobs_defeated', 'interviews_passed', 'interviews_failed', 'mastery_shields_earned', 'bugs_fixed', 'explanations', 'clean_clears', 'commits_logged', 'reference_mode_uses', 'guided_milestones', 'recovery_trials_passed', 'creative_bonuses', 'discoveries_unlocked'])
  if (Array.isArray(source.achievements)) campaign.achievements = boundedRecords(source.achievements, ['name', 'description', 'unlocked'], 100)
  if (isRecord(source.goals)) {
    campaign.goals = {}
    for (const bucket of ['daily', 'weekly', 'long_term']) {
      if (Array.isArray(source.goals[bucket])) campaign.goals[bucket] = boundedRecords(source.goals[bucket], ['id', 'text', 'target', 'progress', 'reward_xp', 'reward_coins', 'done'], 20)
    }
  }
  if (Array.isArray(source.projects)) {
    campaign.projects = source.projects.filter(isRecord).slice(0, 20).map((project) => ({
      ...copyFields(project, SYNC_PROJECT_FIELDS.filter((field) => field !== 'boss_validation')),
      ...(isRecord(project.boss_validation) ? {
        boss_validation: {
          ...(Array.isArray(project.boss_validation.verified) ? { verified: boundedTextList(project.boss_validation.verified, 3) } : {}),
          ...(Array.isArray(project.boss_validation.history) ? { history: boundedRecords(project.boss_validation.history, ['requirement_id', 'evidence_id', 'reason', 'recorded_at'], 20) } : {}),
          ...(typeof project.boss_validation.completed_at === 'string' ? { completed_at: project.boss_validation.completed_at } : {}),
        },
      } : {}),
      ...(Array.isArray(project.mobs)
        ? { mobs: project.mobs.filter(isRecord).slice(0, 20).map((mob) => copyFields(mob, SYNC_MOB_FIELDS)) }
        : {}),
    }))
  }
  if (Object.prototype.hasOwnProperty.call(source, 'current_quest') && typeof source.current_quest === 'string') campaign.current_quest = source.current_quest
  if (isRecord(source.codex)) {
    campaign.codex = {
      encounters: Array.isArray(source.codex.encounters)
        ? source.codex.encounters.filter(isRecord).slice(0, 100).map((entry) => ({
            ...copyFields(entry, SYNC_CODEX_FIELDS.filter((field) => !['results', 'interview_history', 'mastery'].includes(field))),
            ...(Array.isArray(entry.question_types) ? { question_types: boundedTextList(entry.question_types, 20) } : {}),
            ...(Array.isArray(entry.weaknesses) ? { weaknesses: boundedTextList(entry.weaknesses, 20) } : {}),
            ...(Array.isArray(entry.notes) ? { notes: entry.notes.filter((note) => typeof note === 'string').slice(-20) } : {}),
            ...(Array.isArray(entry.player_notes) ? { player_notes: entry.player_notes.filter((note) => typeof note === 'string').slice(-20) } : {}),
            ...(Array.isArray(entry.results) ? { results: boundedRecords(entry.results, ['outcome', 'evidence_id', 'reason', 'recorded_at'], 20) } : {}),
            ...(Array.isArray(entry.interview_history) ? { interview_history: boundedRecords(entry.interview_history, ['outcome', 'evidence_id', 'reason', 'recorded_at'], 20) } : {}),
            ...(isRecord(entry.mastery) ? { mastery: copyFields(entry.mastery, ['evidence', 'interview_passes', 'shield', 'tier', 'charges', 'max_charges']) } : {}),
          }))
        : [],
    }
  }
  if (Object.prototype.hasOwnProperty.call(source, 'dungeon_run')) {
    const run = source.dungeon_run
    if (run === null) campaign.dungeon_run = null
    else if (isRecord(run)) {
      campaign.dungeon_run = {
        ...copyFields(run, SYNC_DUNGEON_FIELDS.filter((field) => !['loadout', 'inventory', 'question', 'room_choices', 'last_result', 'history'].includes(field))),
        ...(isRecord(run.loadout) ? { loadout: copyFields(run.loadout, ['armor', 'trinket', 'hp', 'max_hp', 'heals', 'coins']) } : {}),
        ...(Array.isArray(run.inventory) ? { inventory: boundedRecords(run.inventory, SYNC_DUNGEON_INVENTORY_FIELDS, 24) } : {}),
        ...(run.question === null ? { question: null } : isRecord(run.question) ? { question: copyFields(run.question, ['id', 'question_type', 'concept_id', 'difficulty', 'prompt', 'options']) } : {}),
        ...(Array.isArray(run.room_choices) ? { room_choices: boundedRecords(run.room_choices, ['id', 'kind', 'label', 'description'], 3) } : {}),
        ...(typeof run.editor_content === 'string' ? { editor_content: run.editor_content.slice(0, 8000) } : {}),
        ...(isRecord(run.last_result) ? { last_result: copyFields(run.last_result, ['outcome', 'question_id', 'mob_name', 'score_delta', 'coins_delta', 'damage', 'evidence_id', 'reason']) } : {}),
        ...(Array.isArray(run.history) ? { history: boundedRecords(run.history, ['room', 'floor', 'question_id', 'mob_name', 'outcome', 'evidence_id', 'score_delta', 'coins_delta', 'damage'], 50) } : {}),
      }
    }
  }
  if (Array.isArray(source.dungeon_leaderboard)) campaign.dungeon_leaderboard = boundedRecords(source.dungeon_leaderboard, ['run_id', 'score', 'floor', 'room', 'status', 'concept_id', 'ended_at'], 50)
  if (Array.isArray(source.practice_sessions)) {
    campaign.practice_sessions = source.practice_sessions.filter(isRecord).slice(-50).map((session) => ({
      ...copyFields(session, ['session_id', 'concept', 'question_type', 'difficulty', 'status', 'attempts', 'correct', 'started_at', 'updated_at']),
      ...(Array.isArray(session.history) ? { history: boundedRecords(session.history, ['outcome', 'evidence_id', 'reason', 'recorded_at'], 20) } : {}),
    }))
  }
  return campaign
}

/**
 * Return the bounded, cloud-syncable subset of a campaign snapshot.
 * Campaign evidence (projects, Codex, skills and restart-safe Dungeon state)
 * travels with the same revision/CAS row. Local event logs, activity and
 * catalogs intentionally stay local.
 */
export function projectPlayerState(progress = {}) {
  const homestead = isRecord(progress.homestead) ? progress.homestead : {}
  const owned = Array.isArray(homestead.owned_cosmetics)
    ? [...new Set(homestead.owned_cosmetics.filter((item) => typeof item === 'string'))].slice(0, 100)
    : []
  const equipped = isRecord(homestead.equipped)
    ? copyFields(homestead.equipped, SYNC_HOMESTEAD_EQUIPPED_FIELDS)
    : {}
  const equipment = copyFields(progress.equipment, SYNC_EQUIPMENT_FIELDS)
  for (const field of SYNC_EQUIPMENT_LIST_FIELDS) {
    equipment[field] = boundedTextList(equipment[field], 24)
    if (equipment[field].length === 0 && !Array.isArray(progress.equipment?.[field])) delete equipment[field]
  }
  return {
    player: copyFields(progress.player, SYNC_PLAYER_FIELDS),
    equipment,
    companion: copyFields(progress.companion, SYNC_COMPANION_FIELDS),
    homestead: {
      ...copyFields(homestead, ['name']),
      owned_cosmetics: owned,
      equipped,
    },
    campaign: projectCampaignState(progress),
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
const fnvDigest = (value) => {
  let hash = 2166136261
  for (let index = 0; index < value.length; index += 1) hash = Math.imul(hash ^ value.charCodeAt(index), 16777619) >>> 0
  return hash.toString(16).padStart(8, '0')
}

/**
 * Partition recoverable browser sync metadata by checkout without exposing a
 * filesystem path to Supabase or device rows. The backend normally supplies
 * an opaque SHA-256 namespace; the bounded local digest is a safe fallback
 * for tests or a runtime that predates that field.
 */
export function checkoutStorageNamespace(identity) {
  const normalized = String(identity ?? '').trim()
  if (!normalized) return ''
  if (CHECKOUT_NAMESPACE_RE.test(normalized)) return normalized.toLowerCase()
  return `checkout-${fnvDigest(normalized)}`
}

const scopedStorageKey = (base, namespace = '') => (namespace ? `${base}:${namespace}` : base)
const syncUserKey = (base, userId, namespace = '') => `${scopedStorageKey(base, namespace)}:${encodeURIComponent(userId)}`

const playerSummary = (projection) => {
  const player = isRecord(projection?.player) ? projection.player : {}
  return {
    level: Number.isFinite(Number(player.level)) ? Number(player.level) : null,
    xp: Number.isFinite(Number(player.xp)) ? Number(player.xp) : null,
    xpNext: Number.isFinite(Number(player.xp_next)) ? Number(player.xp_next) : null,
    coins: Number.isFinite(Number(player.coins)) ? Number(player.coins) : null,
  }
}

// A starter cloud row is the untouched account projection created during
// onboarding.  It is safe to replace only this exact baseline with a
// validated local campaign; any other cloud divergence remains an explicit
// conflict so one device can never silently overwrite another device's work.
const isStarterProjection = (projection) => {
  const player = isRecord(projection?.player) ? projection.player : null
  if (!player) return false
  const required = ['level', 'xp', 'lifetime_xp', 'coins']
  if (!required.every((field) => Object.prototype.hasOwnProperty.call(player, field))) return false
  return Number(player.level) === 1
    && Number(player.xp) === 0
    && Number(player.lifetime_xp) === 0
    && Number(player.coins) === 0
    && (player.xp_next === undefined || Number(player.xp_next) === 100)
    && (player.hp === undefined || Number(player.hp) === 100)
    && (player.max_hp === undefined || Number(player.max_hp) === 100)
}

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

const profileColumns = 'id,display_name,avatar_path,created_at,updated_at'
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

export function deviceIdForUser(userId, storage = getStorage(), namespace = '') {
  const stored = readStorage(storage, scopedStorageKey(DEVICE_IDS_STORAGE_KEY, checkoutStorageNamespace(namespace)))
  let ids = {}
  try {
    ids = stored ? JSON.parse(stored) : {}
  } catch {
    ids = {}
  }

  const existing = typeof ids?.[userId] === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(ids[userId]) ? ids[userId] : ''
  if (existing) return existing

  const id = createDeviceId()
  writeStorage(storage, scopedStorageKey(DEVICE_IDS_STORAGE_KEY, checkoutStorageNamespace(namespace)), JSON.stringify({ ...ids, [userId]: id }))
  return id
}

const userSummary = (user) => (user ? { id: user.id, email: user.email ?? '' } : null)
const profileSummary = (profile) =>
  profile
    ? {
        id: profile.id,
        display_name: profile.display_name,
        avatar_path: profile.avatar_path ?? null,
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
  const fingerprint = [error?.code, error?.error_code, error?.name, error?.message]
    .filter(Boolean)
    .join(' ')
  if (/over_email_send_rate_limit|email[\s_-]*send[\s_-]*rate[\s_-]*limit/i.test(fingerprint)) {
    const friendly = new Error('Email delivery is temporarily rate-limited. Try again later; no account was created.')
    if (error && typeof error === 'object') {
      if (error.code) friendly.code = error.code
      if (error.error_code) friendly.error_code = error.error_code
    }
    return friendly
  }
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
  avatar: { path: null, dataUrl: '', source: 'local', status: 'idle', cached: false },
  authStatus: 'anonymous',
  label: config.configured && config.valid ? 'Cloud ready' : 'Offline / Local Mode',
  detail: config.reason,
  error: config.valid ? null : config.reason,
  user: null,
  profile: null,
  device: null,
})

export class SyncEngine {
  constructor({ config = cloudConfig, clientFactory = getSupabaseClient, storage = getStorage(), now = () => new Date(), fetchImpl, checkoutIdentity = '' } = {}) {
    this.config = config
    this.clientFactory = clientFactory
    this.storage = storage
    this.now = now
    this.fetchImpl = fetchImpl || (typeof window !== 'undefined' && typeof globalThis.fetch === 'function' ? globalThis.fetch.bind(globalThis) : null)
    this.storageNamespace = checkoutStorageNamespace(checkoutIdentity)
    this.pendingStorageNamespace = null
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
    this.avatarOperation = 0
    this.avatarProfilePromise = null
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

  setCheckoutIdentity(identity) {
    const nextNamespace = checkoutStorageNamespace(identity)
    if (nextNamespace === this.storageNamespace) return this.storageNamespace
    if (this.syncPromise) {
      this.pendingStorageNamespace = nextNamespace
      return nextNamespace
    }

    this.storageNamespace = nextNamespace
    this.syncCursor = null
    this.outbox = []
    this.cloudSnapshot = null
    this.latestLocalSnapshot = null
    if (this._userId()) this._loadSyncMetadata(this._userId())
    else this.setState({ pendingChanges: 0, localRevision: null, cloudRevision: null })
    if (this.session?.user && this.client) this._scheduleSync()
    return this.storageNamespace
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
    this.avatarOperation += 1
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
      this._setAvatar(null, readCachedAvatar(this.storage), 'local')
      this.setState({ user: null, profile: null, device: null, authStatus: 'signed-out', syncStatus: 'local', pendingChanges: 0, conflict: null, label: 'Sign in to sync', detail: 'Forge remains available locally. Sign in when cloud sync is configured.', error: null })
      return this.state
    }

    // Restore the last account-scoped image before the profile request. This
    // keeps a previously synced portrait visible during a brief offline start.
    this._restoreCachedAvatar(user.id, { allowLocalFallback: false })
    this.setState({ user: userSummary(user), authStatus: 'signed-in', syncStatus: 'local', label: 'Signed in · local cache', detail: 'Account identity restored. Campaign, Journal and Codex fields will sync through the state gateway.', error: null })
    try {
      if (!this.accountPromise || this.accountUserId !== user.id) {
        this.accountUserId = user.id
        this.accountPromise = this.ensureAccount(user)
      }
      const account = await this.accountPromise
      if (this.sessionNonce !== sessionNonce || this._userId() !== user.id) return this.state
      this._loadSyncMetadata(user.id)
      this._startSyncPolling()
      this.setState({ profile: account.profile, device: account.device, authStatus: 'signed-in', syncStatus: 'local', label: 'Signed in · local cache', detail: 'Campaign, Journal and Codex fields will sync through the state gateway.', error: null })
      void this._refreshCloudAvatar(account.profile?.avatar_path, user.id)
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

    const label = normalizeDeviceLabel(readStorage(this.storage, this._deviceLabelKey()) || DEFAULT_DEVICE_LABEL)
    const devicePayload = {
      id: deviceIdForUser(user.id, this.storage, this.storageNamespace),
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
    writeStorage(this.storage, this._deviceLabelKey(), label)
    if (!this.session?.user || !this.client) {
      this.setState({ device: this.state.device ? { ...this.state.device, display_name: label } : this.state.device })
      return this.state
    }

    const payload = {
      id: deviceIdForUser(this.session.user.id, this.storage, this.storageNamespace),
      user_id: this.session.user.id,
      display_name: label,
      last_seen_at: this.now().toISOString(),
    }
    const result = await this.client.from('devices').upsert(payload, { onConflict: 'id' }).select(deviceColumns).single()
    if (result.error) throw asError(result.error, 'Device name could not be saved.')
    this.setState({ device: deviceSummary(result.data), error: null })
    return this.state
  }

  _setAvatar(path, dataUrl, source = 'local', status = 'ready') {
    const normalizedDataUrl = typeof dataUrl === 'string' ? dataUrl : ''
    const avatar = { path: path || null, dataUrl: normalizedDataUrl, source, status, cached: Boolean(normalizedDataUrl) }
    this.setState({ avatar })
    if (typeof globalThis.dispatchEvent === 'function' && typeof globalThis.CustomEvent === 'function') {
      globalThis.dispatchEvent(new CustomEvent('questlab:avatar-updated', { detail: { ...avatar, dataUrl: normalizedDataUrl } }))
    }
    return avatar
  }

  _restoreCachedAvatar(userId, { allowLocalFallback = true } = {}) {
    const accountCached = readCachedAvatar(this.storage, userId)
    const localCached = allowLocalFallback ? readCachedAvatar(this.storage) : ''
    return this._setAvatar(null, accountCached || localCached, accountCached ? 'cached-cloud' : 'local', accountCached || localCached ? 'ready' : 'empty')
  }

  async _refreshCloudAvatar(path, userId = this._userId()) {
    if (!userId) return this.state.avatar
    const operation = ++this.avatarOperation
    const expectedPath = avatarObjectPath(userId)
    if (!path) {
      removeCachedAvatar(this.storage, userId)
      if (this._userId() === userId) return this._setAvatar(null, '', 'local', 'empty')
      return this._restoreCachedAvatar(userId)
    }
    if (path !== expectedPath) {
      const cached = readCachedAvatar(this.storage, userId)
      return this._setAvatar(null, cached, 'cloud', 'invalid')
    }
    if (!this.client?.storage?.from) return this._restoreCachedAvatar(userId)

    try {
      const result = await this.client.storage.from(AVATAR_BUCKET).download(path)
      if (result?.error) throw result.error
      const dataUrl = await blobToDataUrl(result?.data)
      if (operation !== this.avatarOperation || this._userId() !== userId) return this.state.avatar
      validateAvatarDataUrl(dataUrl, { maxBytes: AVATAR_MAX_BYTES, allowedMimeTypes: AVATAR_CLOUD_MIME_TYPES })
      writeCachedAvatar(dataUrl, this.storage, userId)
      return this._setAvatar(path, dataUrl, 'cloud')
    } catch {
      const cached = readCachedAvatar(this.storage, userId)
      if (cached) return this._setAvatar(path, cached, 'cached-cloud', 'stale')
      // Avatar transport is optional to the gameplay session. Keep the
      // account signed in and expose the unavailable state without creating
      // an unhandled rejection during background session restore.
      this._setAvatar(path, '', 'cloud', 'unavailable')
      return this.state.avatar
    }
  }

  async _saveAvatarProfilePath(path) {
    if (!this.client?.from || !this.session?.user) throw new Error('Cloud avatar profile updates are unavailable.')
    const result = await this.client
      .from('profiles')
      .update({ avatar_path: path || null })
      .eq('id', this.session.user.id)
      .select(profileColumns)
      .single()
    if (result?.error) throw result.error
    const profile = profileSummary(result?.data)
    this.setState({ profile })
    return profile
  }

  async setAvatarDataUrl(dataUrl) {
    const validation = validateAvatarDataUrl(dataUrl, { maxBytes: AVATAR_MAX_BYTES, allowedMimeTypes: AVATAR_CLOUD_MIME_TYPES })
    this.avatarOperation += 1
    const userId = this._userId()
    if (!userId || !this.client?.storage?.from) {
      // Signed-in fallbacks stay account-scoped. An unscoped local portrait is
      // only for an explicitly anonymous/offline upload.
      writeCachedAvatar(dataUrl, this.storage, userId)
      return this._setAvatar(null, dataUrl, 'local')
    }

    const path = avatarObjectPath(userId)
    const blob = dataUrlToBlob(dataUrl, { maxBytes: AVATAR_MAX_BYTES, allowedMimeTypes: AVATAR_CLOUD_MIME_TYPES })
    this.setState({ avatar: { ...this.state.avatar, path, status: 'uploading' } })
    try {
      const upload = await this.client.storage.from(AVATAR_BUCKET).upload(path, blob, {
        upsert: true,
        contentType: validation.mimeType,
        cacheControl: '3600',
      })
      if (upload?.error) throw upload.error
      await this._saveAvatarProfilePath(path)
      writeCachedAvatar(dataUrl, this.storage, userId)
      return this._setAvatar(path, dataUrl, 'cloud')
    } catch (error) {
      // The fixed path may have replaced a previous valid image. Leave it in
      // place if profile metadata fails so an existing reference never points
      // at a deleted object; the next upload safely upserts the same path.
      this._setAvatar(null, readCachedAvatar(this.storage, userId), 'cached-cloud', 'upload-failed')
      throw asError(error, 'Avatar upload failed.')
    }
  }

  async removeAvatar() {
    const userId = this._userId()
    this.avatarOperation += 1
    if (!userId || !this.client?.storage?.from) {
      removeCachedAvatar(this.storage, userId)
      if (!userId) removeCachedAvatar(this.storage)
      return this._setAvatar(null, '', 'local', 'empty')
    }
    const path = this.state.profile?.avatar_path || this.state.avatar?.path || avatarObjectPath(userId)
    if (path !== avatarObjectPath(userId)) throw new Error('Cloud avatar reference is invalid.')
    this.setState({ avatar: { ...this.state.avatar, path, status: 'removing' } })
    try {
      const removal = await this.client.storage.from(AVATAR_BUCKET).remove([path])
      if (removal?.error) throw removal.error
      await this._saveAvatarProfilePath(null)
      removeCachedAvatar(this.storage, userId)
      removeCachedAvatar(this.storage)
      return this._setAvatar(null, '', 'local', 'empty')
    } catch (error) {
      this._restoreCachedAvatar(userId)
      throw asError(error, 'Avatar could not be removed.')
    }
  }

  _userId() {
    return typeof this.session?.user?.id === 'string' ? this.session.user.id : ''
  }

  _deviceLabelKey() {
    return scopedStorageKey(DEVICE_LABEL_STORAGE_KEY, this.storageNamespace)
  }

  _outboxKey(userId = this._userId()) {
    return userId ? syncUserKey(SYNC_OUTBOX_STORAGE_KEY, userId, this.storageNamespace) : scopedStorageKey(SYNC_OUTBOX_STORAGE_KEY, this.storageNamespace)
  }

  _cursorKey(userId = this._userId()) {
    return userId ? syncUserKey(SYNC_CURSOR_STORAGE_KEY, userId, this.storageNamespace) : scopedStorageKey(SYNC_CURSOR_STORAGE_KEY, this.storageNamespace)
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

  _pollAvatarReference() {
    if (this.avatarProfilePromise || !this.session?.user || !this.client?.from) return this.avatarProfilePromise
    const sessionNonce = this.sessionNonce
    const userId = this._userId()
    this.avatarProfilePromise = (async () => {
      try {
        const result = await this.client.from('profiles').select('avatar_path,updated_at').eq('id', userId).maybeSingle()
        if (sessionNonce !== this.sessionNonce || this._userId() !== userId || result?.error || !result?.data) return
        const path = result.data.avatar_path ?? null
        const updatedAt = result.data.updated_at ?? null
        if (path === (this.state.profile?.avatar_path ?? null) && updatedAt === (this.state.profile?.updated_at ?? null)) return
        this.setState({ profile: this.state.profile ? { ...this.state.profile, avatar_path: path, updated_at: updatedAt } : this.state.profile })
        await this._refreshCloudAvatar(path, userId)
      } catch {
        // Avatar refresh is optional; the last validated image remains visible.
      } finally {
        this.avatarProfilePromise = null
      }
    })()
    return this.avatarProfilePromise
  }

  _startSyncPolling() {
    if (this.syncInterval || typeof window === 'undefined' || typeof window.setInterval !== 'function') return
    this.syncInterval = window.setInterval(() => {
      // Background checks should not make the top HUD alternate between
      // "Synced" and "Syncing…" every few seconds.  A real mutation,
      // reconnect, conflict, or error still announces itself; an unchanged
      // campaign stays visually stable while the revision check runs.
      if (this.session?.user && this.client) {
        void this.sync({ silent: true })
        void this._pollAvatarReference()
      }
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
      localPlayer: playerSummary(local?.projection),
      cloudPlayer: playerSummary(cloud?.state),
    }
    const localPlayer = conflict.localPlayer
    const cloudPlayer = conflict.cloudPlayer
    const formatPlayer = (value) =>
      value.level === null ? 'unavailable' : `Level ${value.level} · ${value.xp ?? 0}/${value.xpNext ?? 100} XP · ${value.coins ?? 0} coins`
    this.setState({
      syncStatus: 'conflict',
      label: 'Sync conflict',
      detail: `This device: ${formatPlayer(localPlayer)}. Cloud: ${formatPlayer(cloudPlayer)}. Choose which validated campaign copy should win.`,
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
    return code === '40001' || Number(error?.status) === 409
  }

  _isCampaignSchemaError(error) {
    return /(?:next_state|campaign projection) contains unsupported domains/i.test(String(error?.message || error || ''))
  }

  async _syncNow({ silent = false } = {}) {
    if (!this.session?.user || !this.client) return this.state
    const sessionNonce = this.sessionNonce
    const userId = this._userId()
    const sessionIsCurrent = () => this.sessionNonce === sessionNonce && this._userId() === userId
    // Keep a settled background state visible while polling.  We still show
    // the transient status for an explicit sync (sign-in, a local mutation,
    // or reconnect), and conflict/error states are always surfaced below.
    if (!silent || this.state.syncStatus !== 'synced') {
      this.setState({ syncStatus: 'syncing', label: 'Syncing…', detail: 'Comparing the local cache with the cloud revision.', error: null })
    }
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

    const pushLocal = async (expectedCloudRevision, entry = null, detail = 'Campaign fields are synced.') => {
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
          this._setSynced(after, saved, detail)
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
      if (local.revision > 0 && cloud.revision > 0 && isStarterProjection(cloud.state) && !isStarterProjection(local.projection)) {
        await pushLocal(cloud.revision, null, 'This device’s validated campaign was published to the starter cloud copy.')
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

  sync({ silent = false } = {}) {
    if (!this.session?.user || !this.client) return Promise.resolve(this.state)
    if (this.syncPromise) return this.syncPromise
    const sessionNonce = this.sessionNonce
    this.syncPromise = this._syncNow({ silent })
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
        const schemaMigrationRequired = this._isCampaignSchemaError(error)
        this.setState({
          syncStatus: 'error',
          label: schemaMigrationRequired ? 'Cloud schema needs migration' : 'Cloud sync error',
          detail: schemaMigrationRequired
            ? 'Campaign sync is queued locally until Supabase applies 20260917000100_player_state_campaign_projection.sql.'
            : safeError.message,
          error: safeError.message,
          pendingChanges: this.outbox.length,
        })
        return this.state
      })
      .finally(() => {
        this.syncPromise = null
        if (this.pendingStorageNamespace !== null && this.pendingStorageNamespace !== this.storageNamespace) {
          const nextNamespace = this.pendingStorageNamespace
          this.pendingStorageNamespace = null
          this.setCheckoutIdentity(nextNamespace)
        } else {
          this.pendingStorageNamespace = null
        }
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
