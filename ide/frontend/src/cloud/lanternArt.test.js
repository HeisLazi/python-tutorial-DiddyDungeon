import { test } from 'node:test'
import assert from 'node:assert/strict'
import { existsSync, readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { lanternEncounterArt, lanternEncounterLocation } from '../lanternEncounterArt.js'
import { lanternItemArt } from '../lanternItemArt.js'

const frontend = fileURLToPath(new URL('../../', import.meta.url))
const campaign = JSON.parse(readFileSync(new URL('../../../server/campaigns/00-lantern-vale.json', import.meta.url)))

test('every Lantern Vale encounter has artwork and other campaigns do not inherit it', () => {
  for (const name of [...campaign.mobs.map(mob => mob.name), campaign.boss]) {
    const url = lanternEncounterArt(campaign.branch, name)
    assert.ok(url, name)
    assert.ok(existsSync(`${frontend}public${url}`), url)
    const location = lanternEncounterLocation(campaign.branch, name)
    assert.ok(location, name)
    assert.ok(existsSync(`${frontend}public${location}`), location)
    assert.equal(lanternEncounterLocation('another-project', name), null)
    assert.equal(lanternEncounterArt('another-project', name), null)
  }
})

test('each campaign act selects its intended setting', () => {
  const places = ['first-light', 'vale-road', 'workshop', 'living-vale']
  for (const mob of campaign.mobs) {
    const location = lanternEncounterLocation(campaign.branch, mob.name)
    assert.ok(location?.endsWith(`/${places[mob.act - 1]}.png`), mob.name)
  }
  assert.ok(lanternEncounterLocation(campaign.branch, campaign.boss)?.endsWith('/living-vale.png'))
})

test('Lantern Vale weapon, trinket and relic icons exist for their item ids', () => {
  for (const id of ['dungeon-lens', 'dungeon-warden-sigil', 'dungeon-hunting-bell', 'dungeon-whetstone-charm', 'dungeon-syntax-sabre', 'dungeon-loopblade', 'dungeon-aether-staff', 'dungeon-pathfinder-whip', 'dungeon-iron-greatsword', 'dungeon-grave-scythe', 'dungeon-runic-casting', 'trinket-ember-scythe', 'trinket-guardian-sigil', 'trinket-phoenix-ember', 'syntax-ward', 'loop-lens', 'guard-bell', 'scimitar-of-momentum', 'vision-scroll', 'hunter-sparring-scythe', 'hunter-sparring-staff', 'hunter-sparring-whip', 'hunter-sparring-greatsword', 'hunter-sparring-focus', 'lv-01', 'lv-02', 'lv-03', 'lv-04', 'lv-05', 'lv-11', 'lv-12', 'lv-13', 'lv-14', 'lv-15', 'lv-22']) {
    const url = lanternItemArt(id)
    assert.ok(url)
    assert.ok(existsSync(`${frontend}public${url}`), url)
  }
  assert.equal(lanternItemArt('unknown-item'), null)
})
