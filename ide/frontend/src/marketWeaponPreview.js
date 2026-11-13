import { hunterAppearance } from './hunterEquipment.js'

const OUTFITS = {
  ivory: 'ivory', spectral: 'warden-heavy', harvest: 'harvest-scout', oracle: 'arcane',
  patchwork: 'patchwork', pilgrim: 'pilgrim', wayfarer: 'wayfarer', norse: 'norse', lanternkeeper: 'lanternkeeper', wardplate: 'wardplate',
  debugger: 'debugger-v2', 'merchant-oracle': 'merchant-oracle',
}
const STYLES = new Set(['sword', 'staff', 'whip', 'greatsword', 'scythe', 'handmagic', 'oil'])

// These are the same pose sheets and special graveblade variant used in combat.
export function marketWeaponPreview(item, equippedArmor) {
  const outfit = OUTFITS[hunterAppearance(equippedArmor, '').armorLook] || ''
  const name = String(item?.name || '')
  const inferred = /scythe/i.test(name) ? 'scythe' : /whip/i.test(name) ? 'whip'
    : /staff/i.test(name) ? 'staff' : /greatsword|greatblade/i.test(name) ? 'greatsword'
      : /casting|focus|magic/i.test(name) ? 'handmagic' : 'sword'
  const style = STYLES.has(item?.combat_style) ? item.combat_style : inferred
  const graveblade = !['norse', 'lanternkeeper', 'wardplate'].includes(outfit) && style === 'greatsword' && (item?.id === 'hunter-gravebound-greatblade' || /^gravebound greatblade$/i.test(name))
  const actionStyle = graveblade ? 'graveblade' : (!outfit && style === 'sword') ? 'sword-v2' : (!outfit && style === 'oil') ? 'oil-pink' : style
  const prefix = outfit ? `tate-${outfit}` : 'tate'
  const root = `${import.meta.env?.BASE_URL || '/'}campaign-art/`
  const action = `${root}weapon-preview/${prefix}-${actionStyle}-sheet.png`
  const idle = style === 'sword' ? `${root}hunter-idle/${outfit ? `${prefix}-sword-idle-sheet.png` : 'tate-idle-sheet.png'}` : action
  return { action, idle, style, aspectRatio: style === 'sword' ? '96 / 72' : '128 / 72' }
}
