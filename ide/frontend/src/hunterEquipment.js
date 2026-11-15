// Appearance is derived from equipped gear, never stored as a second loadout.

// Armours with their own recoloured combat look. `look` is the look id the combat scene knows (see
// prototypes/godot-combat/source-art/looks_data.py); `home` is the outfit whose silhouette it shares, which is what the
// Home scene shows because it only has art for the original outfits.
const ARMOUR_LOOKS = {
  'lanternscale vest': ['lanternscale', 'lanternkeeper'], 'first light plate': ['firstlight', 'wardplate'],
  'dealer\'s waistcoat': ['dealer', 'classic'], 'velvet felt jacket': ['velvet', 'classic'], 'pit boss coat': ['pitboss', 'harvest'],
  'gilded lapel armour': ['gilded', 'classic'], 'the high roller\'s mail': ['highroller', 'ivory'],
  'doorman\'s livery': ['doorman', 'classic'], 'silver sequin vest': ['sequin', 'classic'], 'auditor\'s waistcoat': ['auditor', 'patchwork'],
  'vault guard plate': ['vault', 'debugger'], 'the fortune mail': ['fortune', 'debugger'],
  'canvas mining smock': ['canvas', 'pilgrim'], 'riveted leather': ['riveted', 'wayfarer'], 'deepvein brigandine': ['deepvein', 'spectral'],
  'lamp-lit lamellar': ['lamellar', 'norse'], 'the core-forged plate': ['coreforged', 'wardplate'],
  'merchant patchwork coat': ['merchantpatchwork', 'patchwork'], 'merchant pilgrim leather': ['merchantpilgrim', 'pilgrim'],
  'merchant wayfarer brigandine': ['merchantwayfarer', 'wayfarer'],
  'lanternbound coat': ['lanternbound', 'lanternkeeper'], 'drowned mail': ['drowned', 'spectral'], 'flowkeeper plate': ['flowkeeper', 'oracle'],
}
// The look ids that are recolours (each has its own combat sheets, Market preview sheets and idle pose).
export const RECOLOUR_LOOKS = new Set(Object.values(ARMOUR_LOOKS).map(([look]) => look))

export function hunterAppearance(armor, trinket) {
  const name = String(armor || '').toLowerCase()
  let armorLook = 'classic'
  if (name.includes('ivory revel suit')) armorLook = 'ivory'
  else if (name.includes('gravebound warden')) armorLook = 'spectral'
  else if (name.includes('harvest revenant')) armorLook = 'harvest'
  else if (name === 'debugger plate') armorLook = 'debugger'
  else if (name === 'merchant oracle mantle') armorLook = 'merchant-oracle'
  else if (name === 'oracle mantle') armorLook = 'oracle'
  else if (name === 'patchwork travel coat') armorLook = 'patchwork'
  else if (name === 'pilgrim leather') armorLook = 'pilgrim'
  else if (name === 'wayfarer brigandine') armorLook = 'wayfarer'
  else if (name === 'norse mail') armorLook = 'norse'
  else if (name === 'lantern coat' || name === 'lanternkeeper’s coat' || name === 'lanternkeeper\'s coat') armorLook = 'lanternkeeper'
  else if (name === 'pilgrim ward' || name === 'wayfarer’s wardplate' || name === 'wayfarer\'s wardplate') armorLook = 'wardplate'
  else if (ARMOUR_LOOKS[name]) armorLook = ARMOUR_LOOKS[name][0]
  else if (/oracle|inkwoven|runic|aether|mantle|robe/.test(name)) armorLook = 'arcane'
  else if (/plate|mail|cuirass|shellguard|carapace/.test(name)) armorLook = 'steel'
  else if (/ember|lantern|pilgrim|bullhide/.test(name)) armorLook = 'ember'
  const charm = String(trinket || '').trim()
  const trinketLook = !charm || /^none$/i.test(charm) ? 'none' : /pink cap/i.test(charm) ? 'pink' : /jacklight|pumpkin|harvest|ember|flame|spark/i.test(charm) ? 'ember' : /soul lantern|warden|guard|ward|spectral|ash/i.test(charm) ? 'spectral' : 'arcane'
  // Only display trinkets with their own wearable artwork. A generic gem
  // floats over the hunter and falsely represents unrelated equipment.
  const trinketIcon = /^pink cap charm$/i.test(charm) ? 'pink-cap' : /^soul lantern$/i.test(charm) ? 'soul-lantern' : /^jacklight charm$/i.test(charm) ? 'jacklight' : 'none'
  // The Home scene only has art for the original outfits, so a recolour shows as the outfit it was made from.
  const homeLook = ARMOUR_LOOKS[name] ? ARMOUR_LOOKS[name][1] : armorLook
  return { armorLook, homeLook, trinketLook, trinketIcon, pet: armorLook === 'ivory' ? 'oil' : 'none' }
}
