import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = (relativeUrl) => readFileSync(new URL(relativeUrl, import.meta.url), 'utf8')

test('Monaco is bundled locally with local Vite workers and no CDN loader', () => {
  const main = source('../main.jsx')
  const packageJson = JSON.parse(source('../../package.json'))

  assert.ok(packageJson.dependencies['monaco-editor'])
  assert.match(main, /loader\.config\(\{ monaco \}\)/)
  assert.match(main, /monaco-editor\/esm\/vs\/editor\/editor\.worker\?worker/)
  assert.match(main, /MonacoEnvironment\s*=\s*\{/)
  assert.doesNotMatch(main, /https?:\/\/[^\s'"`]*(jsdelivr|unpkg|cdnjs)/i)
})

test('terminal cosmetics update in place without changing the PTY lifecycle key', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /\}, \[role, banner\]\)/)
  assert.match(app, /term\.options\.fontSize\s*=\s*fontSize/)
  assert.match(app, /term\.options\.theme\s*=\s*terminalPalette\(skin\)/)
})

test('tutor polling distinguishes clean updates from dirty external conflicts', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /window\.setInterval\(pollTutor, 1000\)/)
  assert.match(app, /PYR updated tutor\.py/)
  assert.match(app, /Reload external version/)
  assert.match(app, /Keep my edits/)
})

test('campaign projections use revision polling and state-service events', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const combat = source('../combatShell.js')

  assert.match(app, /\/api\/state\/revision/)
  assert.match(app, /window\.setInterval\(pollCampaignRevision, 1000\)/)
  assert.match(app, /state_events/)
  assert.match(app, /questlab:campaign-updated/)
  assert.match(app, /<RewardQueue items=\{rewardQueue\} \/>/)
  assert.match(views, /data-testid="encounter-resolve"/)
  assert.match(views, /progress\.codex\?\.encounters/)
  assert.match(views, /data-campaign-revision=\{revision\}/)
  assert.match(combat, /refreshCampaignIfChanged/)
  assert.match(combat, /questlab:campaign-updated/)
  assert.doesNotMatch(views, /mob\.encounter \|\| 'This encounter has not revealed/)
})

test('combat projection treats legacy cleared mobs as terminal', () => {
  const combat = source('../combatShell.js')
  const views = source('../RpgViews.jsx')

  assert.match(combat, /isMobDefeated\s*=\s*\(mob\)\s*=>\s*mob\?\.status === 'defeated' \|\| mob\?\.status === 'cleared'/)
  assert.match(combat, /mobs\.findIndex\(\(mob\) => !isMobDefeated\(mob\)\)/)
  assert.match(views, /const isMobDefeated = \(status\) => status === 'defeated' \|\| status === 'cleared'/)
  assert.doesNotMatch(views, /mob\.status === 'defeated' \? '✓'/)
})

test('legacy reconciliation renders validated restoration feedback without inventing rewards', () => {
  const app = source('../AppV2.jsx')

  assert.match(app, /action === 'reconcile_legacy_progress'/)
  assert.match(app, /PROGRESS RESTORED/)
  assert.match(app, /restored_xp/)
  assert.match(app, /restored_coins/)
  assert.match(app, /restored_mobs/)
  assert.match(app, /restored_fields/)
  assert.match(app, /CODEX UPDATED/)
})

test('bounded player-state sync stays behind one engine with revision/conflict controls', () => {
  const app = source('../AppV2.jsx')
  const views = source('../RpgViews.jsx')
  const engine = source('./syncEngine.js')

  assert.match(app, /syncEngine\.observeCampaign\(next\)/)
  assert.match(app, /resolveCloudConflict/)
  assert.match(views, /Use cloud copy/)
  assert.match(views, /Keep this device/)
  assert.match(engine, /\/api\/state\/sync/)
  assert.match(engine, /save_player_state/)
  assert.match(engine, /SYNC_OUTBOX_STORAGE_KEY/)
  assert.match(engine, /resolveConflict\(choice\)/)
  assert.match(engine, /localPlayer: playerSummary\(local\?\.projection\)/)
  assert.match(engine, /cloudPlayer: playerSummary\(cloud\?\.state\)/)
  assert.match(engine, /isStarterProjection/)
  assert.match(engine, /published to the starter cloud copy/)
  assert.match(engine, /window\.setInterval\(\(\) => \{[\s\S]*void this\.sync\(\{ silent: true \}\)/)
})

test('top HUD SVG icons are nested content, not nested stat pills', () => {
  const styles = source('../styles.css')
  const v2 = source('../v2.css')

  assert.match(styles, /\.top-stats\s*>\s*span,\.git-pill/)
  assert.match(styles, /\.app-shell\[data-hud="hud-adventurer"\] \.top-stats\s*>\s*span/)
  assert.match(v2, /\.forge-v2\[data-hud="hud-adventurer"\] \.top-stats\s*>\s*span/)
  assert.doesNotMatch(styles, /\.top-stats\s+span,\.git-pill/)
  assert.match(styles, /\.top-stats\s*>\s*span\s*>\s*\.quest-icon/)
  assert.match(styles, /\.top-stats\s*>\s*span\s*>\s*\[data-stat-value\]/)
  assert.match(styles, /\.top-stats\s+\.cloud-pill\{[^}]*min-width:15ch/)
})

test('avatar controls use the account-scoped storage boundary with a local fallback', () => {
  const enhancements = source('../forgeEnhancements.js')
  const engine = source('./syncEngine.js')
  const avatar = source('./avatarStorage.js')

  assert.match(enhancements, /syncEngine\.setAvatarDataUrl\(dataUrl\)/)
  assert.match(enhancements, /syncEngine\.removeAvatar\(\)/)
  assert.match(enhancements, /questlab:avatar-updated/)
  assert.match(engine, /AVATAR_BUCKET/)
  assert.match(engine, /_saveAvatarProfilePath/)
  assert.match(engine, /_pollAvatarReference/)
  assert.match(engine, /readCachedAvatar\(this\.storage, userId\)/)
  assert.match(avatar, /AVATAR_MAX_BYTES = 1_000_000/)
  assert.match(avatar, /avatarObjectPath\(userId\)/)
})
