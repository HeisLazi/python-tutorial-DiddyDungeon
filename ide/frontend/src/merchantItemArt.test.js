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
  // The two armour echoes are armours in the Home armory, so each has an icon of its own (see the every-armour test below).
  const armourEchoes = new Set(['lantern-coat', 'pilgrim-ward'])
  const paths = ids.map(id => {
    const runId = `dungeon-${id}`
    const path = lanternItemArt(runId)
    if (armourEchoes.has(id)) {
      assert.match(lanternItemArt(`campaign-${runId}`), new RegExp(`armor-campaign-${runId}\\.png$`), id)
      assert.notEqual(lanternItemArt(`campaign-${runId}`), path, id)
    } else assert.equal(path, lanternItemArt(`campaign-${runId}`), id)
    assert.equal(path, merchantItemArt({ id: runId }), id)
    const png = readFileSync(resolve(publicDir, `.${path}`))
    assert.equal(png.readUInt32BE(16), 64, id)
    assert.equal(png.readUInt32BE(20), 64, id)
    return path
  })
  assert.equal(new Set(paths).size, ids.length)
})

// Every armour in the Home armory (docs/ARMOUR_IDENTITIES.md) has an icon of its own: a real file, never the shared coat.
const ARMOUR_IDS = ["lv-06", "lv-07", "lv-08", "lv-09", "lv-10", "bj-dealer-s-waistcoat", "bj-velvet-felt-jacket", "bj-pit-boss-coat", "bj-gilded-lapel-armour", "bj-the-high-roller-s-mail", "cas-doorman-s-livery", "cas-silver-sequin-vest", "cas-auditor-s-waistcoat", "cas-vault-guard-plate", "cas-the-fortune-mail", "dc-canvas-mining-smock", "dc-riveted-leather", "dc-deepvein-brigandine", "dc-lamp-lit-lamellar", "dc-the-core-forged-plate", "hunter-ivory-revel-suit", "hunter-gravebound-plate", "hunter-harvest-coat", "merchant-patchwork-coat", "merchant-pilgrim-leather", "merchant-wayfarer-brigandine", "merchant-oracle-mantle", "forged-lantern-coat", "forged-divers-mail", "forged-keeper-plate", "forged-norse-mail", "campaign-dungeon-lantern-coat", "campaign-dungeon-pilgrim-ward"]
test('every armour has its own icon', () => {
  const seen = new Map()
  for (const id of ARMOUR_IDS) {
    const src = merchantItemArt({ id, slot: 'armor' })
    assert.match(src, new RegExp(`/campaign-art/items/armor-${id}\\.png$`), id)
    const file = readFileSync(new URL(`../public${src}`, import.meta.url))
    assert.equal(file.readUInt32BE(16), 128, id)
    assert.equal(seen.has(src), false, `${id} repeats ${seen.get(src)}`)
    seen.set(src, id)
    assert.equal(seen.size, ARMOUR_IDS.indexOf(id) + 1)
  }
  assert.equal(seen.size, 33)
})
