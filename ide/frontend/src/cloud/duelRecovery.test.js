import test from 'node:test'
import assert from 'node:assert/strict'
import { duelRecoveryKey, readDuelRecovery, writeDuelRecovery, clearDuelRecovery } from './duelRecovery.js'

function store() {
  const values = new Map()
  return {getItem:key => values.get(key) ?? null, setItem:(key,value) => values.set(key,value), removeItem:key => values.delete(key)}
}
test('recovery is scoped to user and group and excludes credentials', () => {
  const storage = store(), key = duelRecoveryKey('hunter-a','group-a')
  writeDuelRecovery(key, {matchId:'match-1', invitation:'', code:'print(1)', stdin:'hi', round:0, token:'must-not-store'}, storage, 1000)
  const saved = readDuelRecovery(key, storage, 1001)
  assert.equal(saved.code, 'print(1)')
  assert.equal(saved.stdin, 'hi')
  assert.equal(saved.token, undefined)
  assert.equal(readDuelRecovery(duelRecoveryKey('hunter-b','group-a'), storage, 1001), null)
  assert.equal(readDuelRecovery(duelRecoveryKey('hunter-a','group-b'), storage, 1001), null)
  clearDuelRecovery(key, storage)
  assert.equal(readDuelRecovery(key, storage, 1001), null)
})
test('expired and malformed recovery data are ignored', () => {
  const storage = store(), key = duelRecoveryKey('hunter','group')
  writeDuelRecovery(key, {matchId:'match-1', invitation:'', code:'pass', stdin:'', round:0}, storage, 1000)
  assert.equal(readDuelRecovery(key, storage, 1000 + 2*60*60*1000 + 1), null)
  storage.setItem(key, '{not valid')
  assert.equal(readDuelRecovery(key, storage, 1001), null)
})
