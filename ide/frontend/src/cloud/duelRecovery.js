// Tab-local recovery, scoped to the signed-in account and group. Never store
// session tokens, opponent code, or credentials in the recovery record.
const MAX_AGE = 2 * 60 * 60 * 1000
export function duelRecoveryKey(userId, groupId) {
  return userId && groupId ? `questlab.duel.recovery.${userId}.${groupId}` : ''
}
export function readDuelRecovery(key, storage = null, now = Date.now()) {
  if (!key) return null
  try {
    const value = JSON.parse((storage || window.sessionStorage).getItem(key) || 'null')
    if (!value || !Number.isFinite(value.savedAt) || now - value.savedAt > MAX_AGE || value.savedAt > now + 60000) return null
    if (typeof value.matchId !== 'string' || value.matchId.length > 128 || typeof value.invitation !== 'string' || value.invitation.length > 128) return null
    if (typeof value.code !== 'string' || value.code.length > 20000 || typeof value.stdin !== 'string' || value.stdin.length > 4000) return null
    if (!Number.isInteger(value.round) || value.round < -1 || value.round > 2) return null
    return value
  } catch { return null }
}
export function writeDuelRecovery(key, data, storage = null, now = Date.now()) {
  if (!key) return
  try {
    storage = storage || window.sessionStorage
    if (!data.matchId && !data.invitation) { storage.removeItem(key); return }
    storage.setItem(key, JSON.stringify({matchId:data.matchId, invitation:data.invitation, code:data.code, stdin:data.stdin, round:data.round, savedAt:now}))
  } catch { /* A disabled or full browser store must not interrupt a match. */ }
}
export function clearDuelRecovery(key, storage = null) {
  try { if (key) (storage || window.sessionStorage).removeItem(key) } catch { /* storage unavailable */ }
}
