import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { marketWeaponPreview } from './marketWeaponPreview.js'

const armor = ['', 'Ivory Revel Suit', 'Gravebound Warden Plate', 'Harvest Revenant Coat', 'Oracle Mantle', 'Merchant Patchwork Coat', 'Merchant Pilgrim Leather', 'Merchant Wayfarer Brigandine', 'Lanternkeeper’s Coat', 'Wayfarer’s Wardplate', 'Debugger Plate', 'Merchant Oracle Mantle']
const styles = ['sword', 'staff', 'whip', 'greatsword', 'scythe', 'handmagic', 'oil']

test('all supported equipment previews resolve to complete four-frame sheets', () => {
  for (const equipped of armor) for (const style of styles) {
    const preview = marketWeaponPreview({ name: 'Weapon', combat_style: style }, equipped)
    assert.equal(preview.style, style)
    for (const src of [preview.idle, preview.action]) {
      const file = readFileSync(new URL(`../public${src}`, import.meta.url))
      assert.equal(file.readUInt32BE(20), 72, src)
      assert.equal(file.readUInt32BE(16), style === 'sword' ? 384 : 512, src)
    }
  }
})

test('gravebound greatblade uses its own combat pose sheet', () => {
  const preview = marketWeaponPreview({ id: 'hunter-gravebound-greatblade', name: 'Gravebound Greatblade', combat_style: 'greatsword' }, 'Merchant Wayfarer Brigandine')
  assert.match(preview.action, /tate-wayfarer-graveblade-sheet\.png$/)
  assert.equal(readFileSync(new URL(`../public${preview.action}`, import.meta.url)).readUInt32BE(16), 512)
})

test('culture-led Basics armour echoes have their own sheets and never borrow the graveblade variant', () => {
  for (const [equipped, outfit] of [['Lanternkeeper’s Coat', 'lanternkeeper'], ['Wayfarer’s Wardplate', 'wardplate']]) {
    const preview = marketWeaponPreview({ id: 'hunter-gravebound-greatblade', name: 'Gravebound Greatblade', combat_style: 'greatsword' }, equipped)
    assert.match(preview.action, new RegExp(`tate-${outfit}-greatsword-sheet\\.png$`))
    assert.match(marketWeaponPreview({ name: 'Blade', combat_style: 'sword' }, equipped).idle, new RegExp(`tate-${outfit}-sword-idle-sheet\\.png$`))
  }
})

test('Dawn Lantern previews the same staff poses for supported outfits', () => {
  for (const [equipped, prefix] of [['', 'tate'], ['Lantern Coat', 'tate-lanternkeeper'], ['Pilgrim Ward', 'tate-wardplate']]) {
    const preview = marketWeaponPreview({ name: 'Dawn Lantern' }, equipped)
    assert.equal(preview.style, 'staff')
    assert.match(preview.action, new RegExp(`${prefix}-dawn-sheet\\.png$`))
    assert.equal(readFileSync(new URL(`../public${preview.action}`, import.meta.url)).readUInt32BE(16), 512)
  }
})
