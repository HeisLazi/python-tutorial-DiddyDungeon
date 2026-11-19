// Saved runs may predate weapon_style; resolve the two Dawn Lantern names too.
export function combatStyle(name = '') {
  if (/hand\s*magic|runic casting/i.test(name)) return 'handmagic'
  if (/greatsword|two.hand/i.test(name)) return 'greatsword'
  if (/scythe/i.test(name)) return 'scythe'
  if (/whip/i.test(name)) return 'whip'
  if (/staff/i.test(name) || isDawnLantern(name)) return 'staff'
  return 'sword'
}

function isDawnLantern(name) {
  return /^(dawn lantern|matriarch['’]s dawnlight)$/i.test(String(name || '').trim())
}

export function combatWeaponVariant(name) {
  if (isDawnLantern(name)) return 'dawn-lantern'
  return /^gravebound greatblade$/i.test(String(name || '').trim()) ? 'graveblade' : ''
}
