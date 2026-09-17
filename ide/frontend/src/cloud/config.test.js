import assert from 'node:assert/strict'
import test from 'node:test'

import { resolveCloudConfig } from './config.js'
import { SyncEngine } from './syncEngine.js'

test('missing cloud values select Offline / Local Mode without creating a client', () => {
  const config = resolveCloudConfig({})
  let clientCreated = false
  const engine = new SyncEngine({
    config,
    clientFactory: () => {
      clientCreated = true
      return {}
    },
  })

  const state = engine.initialize()

  assert.equal(config.configured, false)
  assert.equal(config.valid, true)
  assert.equal(state.mode, 'local')
  assert.equal(state.syncStatus, 'local')
  assert.equal(state.label, 'Offline / Local Mode')
  assert.equal(clientCreated, false)
})

test('partial cloud configuration is rejected safely and remains local', () => {
  const config = resolveCloudConfig({ VITE_SUPABASE_URL: 'https://example.supabase.co' })

  assert.equal(config.configured, false)
  assert.equal(config.valid, false)
  assert.equal(config.mode, 'local')
})

test('public Supabase values enable the cloud service boundary', () => {
  const config = resolveCloudConfig({
    VITE_SUPABASE_URL: 'https://example.supabase.co',
    VITE_SUPABASE_ANON_KEY: 'public-anon-key',
  })
  const expectedClient = { kind: 'test-client' }
  const engine = new SyncEngine({ config, clientFactory: () => expectedClient })

  const state = engine.initialize()

  assert.equal(config.configured, true)
  assert.equal(config.valid, true)
  assert.equal(engine.client, expectedClient)
  assert.equal(state.mode, 'cloud-ready')
})
