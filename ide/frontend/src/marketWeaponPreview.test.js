import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { marketWeaponPreview } from './marketWeaponPreview.js'

// Every armour in the Home armory, so every outfit and recolour a hunter can wear has complete preview sheets.
const armor = ['', ...["Patchwork Travel Coat", "Pilgrim Leather", "Wayfarer Brigandine", "Lanternscale Vest", "First Light Plate", "Dealer's Waistcoat", "Velvet Felt Jacket", "Pit Boss Coat", "Gilded Lapel Armour", "The High Roller's Mail", "Doorman's Livery", "Silver Sequin Vest", "Auditor's Waistcoat", "Vault Guard Plate", "The Fortune Mail", "Canvas Mining Smock", "Riveted Leather", "Deepvein Brigandine", "Lamp-Lit Lamellar", "The Core-Forged Plate", "Ivory Revel Suit", "Gravebound Warden Plate", "Harvest Revenant Coat", "Merchant Patchwork Coat", "Merchant Pilgrim Leather", "Merchant Wayfarer Brigandine", "Merchant Oracle Mantle", "Lanternbound Coat", "Drowned Mail", "Flowkeeper Plate", "Norse Mail", "Lanternkeeper’s Coat", "Wayfarer’s Wardplate"]]
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
  const preview = marketWeaponPreview({ id: 'hunter-gravebound-greatblade', name: 'Gravebound Greatblade', combat_style: 'greatsword' }, 'Wayfarer Brigandine')
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
