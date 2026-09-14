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
