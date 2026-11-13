// Appearance is derived from equipped gear, never stored as a second loadout.
export function hunterAppearance(armor, trinket) {
  const name = String(armor || '').toLowerCase()
  let armorLook = 'classic'
  if (name.includes('ivory revel suit')) armorLook = 'ivory'
  else if (name.includes('gravebound warden')) armorLook = 'spectral'
  else if (name.includes('harvest revenant')) armorLook = 'harvest'
  else if (name === 'debugger plate') armorLook = 'debugger'
  else if (name === 'merchant oracle mantle') armorLook = 'merchant-oracle'
  else if (name === 'oracle mantle') armorLook = 'oracle'
  else if (name === 'patchwork travel coat' || name === 'merchant patchwork coat') armorLook = 'patchwork'
  else if (name === 'pilgrim leather' || name === 'merchant pilgrim leather') armorLook = 'pilgrim'
  else if (name === 'wayfarer brigandine' || name === 'merchant wayfarer brigandine') armorLook = 'wayfarer'
  else if (name === 'norse mail') armorLook = 'norse'
  else if (name === 'lanternkeeper’s coat' || name === 'lanternkeeper\'s coat') armorLook = 'lanternkeeper'
  else if (name === 'wayfarer’s wardplate' || name === 'wayfarer\'s wardplate') armorLook = 'wardplate'
  else if (/oracle|inkwoven|runic|aether|mantle|robe/.test(name)) armorLook = 'arcane'
  else if (/plate|mail|cuirass|shellguard|carapace/.test(name)) armorLook = 'steel'
  else if (/ember|lantern|pilgrim|bullhide/.test(name)) armorLook = 'ember'
  const charm = String(trinket || '').trim()
  const trinketLook = !charm || /^none$/i.test(charm) ? 'none' : /pink cap/i.test(charm) ? 'pink' : /jacklight|pumpkin|harvest|ember|flame|spark/i.test(charm) ? 'ember' : /soul lantern|warden|guard|ward|spectral|ash/i.test(charm) ? 'spectral' : 'arcane'
  // Only display trinkets with their own wearable artwork. A generic gem
  // floats over the hunter and falsely represents unrelated equipment.
  const trinketIcon = /^pink cap charm$/i.test(charm) ? 'pink-cap' : /^soul lantern$/i.test(charm) ? 'soul-lantern' : /^jacklight charm$/i.test(charm) ? 'jacklight' : 'none'
  return { armorLook, trinketLook, trinketIcon, pet: armorLook === 'ivory' ? 'oil' : 'none' }
}
