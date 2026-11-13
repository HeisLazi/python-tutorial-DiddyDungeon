import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'
import { merchantItemArt } from './merchantItemArt.js'
import { lanternItemArt } from './lanternItemArt.js'
const here = dirname(fileURLToPath(import.meta.url))
const publicDir = resolve(here, '../public')

test('every priced campaign armoury item resolves to an existing image', () => {
  for (const campaign of ['00-lantern-vale', '01-blackjack', '04-casino-slots', '05-dungeon-crawler']) {
    const data = JSON.parse(readFileSync(resolve(here, `../../server/campaigns/${campaign}.json`), 'utf8'))
    for (const item of data.armory.filter((item) => item.price != null)) {
      const path = merchantItemArt(item)
      assert.ok(existsSync(resolve(publicDir, `.${path}`)), `${item.id}: ${path}`)
    }
  }
})

test('starter coats and vision scrolls resolve to actual images', () => {
  for (const id of ['armor-apprentice-coat', 'dungeon-starter-armor', 'vision-scroll', 'dungeon-vision-scroll']) {
    const path = lanternItemArt(id)
    assert.ok(path && existsSync(resolve(publicDir, `.${path}`)), id)
  }
})

test('Basics run gear and Journal echoes use their own existing item icons', () => {
  const ids = ['dawn-lantern', 'lantern-coat', 'pilgrim-ward', 'village-lantern', 'pilgrim-knot', 'warm-ember']
  const paths = ids.map(id => {
    const runId = `dungeon-${id}`
    const path = lanternItemArt(runId)
    assert.equal(path, lanternItemArt(`campaign-${runId}`), id)
    assert.equal(path, merchantItemArt({ id: runId }), id)
    const png = readFileSync(resolve(publicDir, `.${path}`))
    assert.equal(png.readUInt32BE(16), 64, id)
    assert.equal(png.readUInt32BE(20), 64, id)
    return path
  })
  assert.equal(new Set(paths).size, ids.length)
})
