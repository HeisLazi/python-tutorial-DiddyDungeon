import { cloudConfig } from './config.js'
import { getSupabaseClient } from './supabaseClient.js'

const initialState = (config) => ({
  configured: config.configured,
  configurationValid: config.valid,
  mode: config.configured ? 'cloud-ready' : 'local',
  syncStatus: 'local',
  authStatus: 'anonymous',
  label: config.configured ? 'Cloud ready' : 'Offline / Local Mode',
  detail: config.reason,
  error: config.valid ? null : config.reason,
})

export class SyncEngine {
  constructor({ config = cloudConfig, clientFactory = getSupabaseClient } = {}) {
    this.config = config
    this.clientFactory = clientFactory
    this.client = null
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

  initialize() {
    if (!this.config.configured || !this.config.valid) {
      this.state = initialState(this.config)
      this.emit()
      return this.state
    }

    this.client = this.clientFactory(this.config)
    this.state = {
      ...this.state,
      mode: 'cloud-ready',
      label: 'Cloud ready',
      detail: 'Cloud is configured. Sign-in support is initialized separately.',
      error: null,
    }
    this.emit()
    return this.state
  }

  emit() {
    for (const listener of this.listeners) listener(this.state)
  }
}

export const syncEngine = new SyncEngine()
