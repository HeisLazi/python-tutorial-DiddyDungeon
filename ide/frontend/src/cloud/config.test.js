import assert from 'node:assert/strict'
import test from 'node:test'

import { loadRemoteCloudConfig, resolveCloudConfig } from './config.js'
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

test('same-origin config relay accepts only HTTPS Supabase publishable config', async () => {
  let requestedPath = ''
  const fake = async (path, options) => {
    requestedPath = path
    assert.equal(options.credentials, 'omit')
    assert.equal(options.redirect, 'error')
    return {ok:true, json:async () => ({url:'https://example.supabase.co',publishable_key:'sb_publishable_test'})}
  }
  assert.equal((await loadRemoteCloudConfig(fake, 500)).configured, true)
  assert.equal(requestedPath, '/api/online/client-config')
  assert.equal(await loadRemoteCloudConfig(async () => ({ok:true,json:async () => ({url:'https://example.supabase.co',publishable_key:'sb_secret_test'})}), 500), null)
  assert.equal(await loadRemoteCloudConfig(async () => { throw new Error('offline') }, 500), null)
})
