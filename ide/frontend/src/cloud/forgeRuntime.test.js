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

test('top HUD SVG icons are nested content, not nested stat pills', () => {
  const styles = source('../styles.css')
  const v2 = source('../v2.css')

  assert.match(styles, /\.top-stats\s*>\s*span,\.git-pill/)
  assert.match(styles, /\.app-shell\[data-hud="hud-adventurer"\] \.top-stats\s*>\s*span/)
  assert.match(v2, /\.forge-v2\[data-hud="hud-adventurer"\] \.top-stats\s*>\s*span/)
  assert.doesNotMatch(styles, /\.top-stats\s+span,\.git-pill/)
  assert.match(styles, /\.top-stats\s*>\s*span\s*>\s*\.quest-icon/)
  assert.match(styles, /\.top-stats\s*>\s*span\s*>\s*\[data-stat-value\]/)
})
