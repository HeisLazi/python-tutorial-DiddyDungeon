// Player paper-doll: a 24x32 pixel sprite built from layers (body, outfit,
// hair, armor, trinket, weapon) in the same grid style as the Merchant.
// Appearance values are the option names stored in equipment.avatar
// (state.py AVATAR_OPTIONS); gear is the equipped item names.

const WIDTH = 24
const HEIGHT = 32

export const AVATAR_PALETTES = {
  skin: {
    porcelain: ['#f6dccb', '#d9b39d'], fair: ['#f1c9a5', '#cf9f7c'], tan: ['#d9a066', '#b07a45'],
    olive: ['#b98a5a', '#8f6640'], brown: ['#8d5a3b', '#6b3f27'], deep: ['#5a3825', '#3f2618'],
  },
  hair_color: {
    black: ['#1d1b26', '#3a3650'], brown: ['#5b3a29', '#8a5a3d'], auburn: ['#8c3b22', '#c2603a'],
    blonde: ['#c9a23a', '#f2d77e'], silver: ['#9aa1ae', '#e6eaf2'], crimson: ['#a3263b', '#d94a60'],
    teal: ['#1f7a78', '#3fb3ad'], violet: ['#5b3a99', '#8f6bd6'],
  },
  eyes: { brown: '#4a2c1a', blue: '#3a7bd5', green: '#3a9a5b', grey: '#7a8290', amber: '#c98a2a' },
  outfit: {
    indigo: ['#3d3a8c', '#2a2766'], crimson: ['#8c2a3a', '#661d29'], forest: ['#2f6b3f', '#1f4a2b'],
    charcoal: ['#3a3d46', '#25272d'], plum: ['#6b3a6b', '#4a284a'], teal: ['#1f6b6b', '#154a4a'],
    gold: ['#b8902a', '#8a6a1d'], sand: ['#b89a6b', '#8a7350'],
  },
  accent: { gold: '#ffcc33', silver: '#d6dbe6', crimson: '#ff4d6d', teal: '#4cc9f0', violet: '#b48cff', white: '#f4ecd8' },
}

export const AVATAR_LABELS = {
  skin: 'Skin', hair_style: 'Hair', hair_color: 'Hair colour', eyes: 'Eyes', outfit: 'Outfit', accent: 'Trim',
}

export const DEFAULT_APPEARANCE = { skin: 'tan', hair_style: 'short', hair_color: 'brown', eyes: 'brown', outfit: 'indigo', accent: 'gold' }

// Armor colours by equipped armor name (campaign catalogue + Dungeon starter).
const ARMOR_COLORS = {
  'Leather Guard': ['#8b5a2b', '#5e3b1b'], 'Ledgerguard Coat': ['#6b4a2f', '#4a3220'],
  'Runic Mail': ['#7f8fa6', '#58637a'], 'Debugger Plate': ['#5fa86b', '#3f7a4a'],
  Emberplate: ['#c2452d', '#8a2e1d'], 'Emberweave Mantle': ['#b5482f', '#7a2e1d'],
  'Guardian Aegis': ['#d9b44a', '#a8862f'], 'Mythril Archive Plate': ['#9fd3e6', '#6aa3b8'],
}
const TRINKET_COLORS = {
  'Ember Scythe': '#ff7a3d', 'Guardian Sigil': '#ffcc33', 'Phoenix Ember': '#ff4d6d', 'Syntax Ward': '#4cc9f0',
  'Loop Lens': '#b48cff', 'Guard Bell': '#ffe27a', 'Scimitar of Momentum': '#d6dbe6', 'Vision Scroll': '#f4ecd8',
}

function row(...runs) {
  const cells = Array(WIDTH).fill('.')
  runs.forEach(([start, glyphs]) => {
    ;[...glyphs].forEach((token, offset) => {
      const index = start + offset
      if (index >= 0 && index < WIDTH) cells[index] = token
    })
  })
  return cells.join('')
}

function blank() {
  return Array.from({ length: HEIGHT }, () => '.'.repeat(WIDTH))
}

// Paint `layer` (row index -> row string) over `grid`; '.' is transparent.
function paint(grid, layer) {
  Object.entries(layer).forEach(([index, line]) => {
    const target = [...grid[Number(index)]]
    ;[...line].forEach((token, x) => { if (token !== '.') target[x] = token })
    grid[Number(index)] = target.join('')
  })
}

const BODY = {
  3: row([8, 'oooooooo']),
  4: row([7, 'o'], [8, 'ssssssss'], [16, 'o']),
  5: row([7, 'o'], [8, 'ssssssss'], [16, 'o']),
  6: row([7, 'o'], [8, 'ssssssss'], [16, 'o']),
  7: row([7, 'o'], [8, 'swessews'], [16, 'o']),
  8: row([7, 'o'], [8, 'ssssssss'], [16, 'o']),
  9: row([7, 'o'], [8, 'sssMMsss'], [16, 'o']),
  10: row([8, 'o'], [9, 'ssssss'], [15, 'o']),
  11: row([9, 'oo'], [11, 'SS'], [13, 'oo']),
  12: row([5, 'o'], [6, 'cccccccccccc'], [18, 'o']),
  13: row([4, 'o'], [5, 'cccccccccccccc'], [19, 'o']),
  14: row([3, 'o'], [4, 'cc'], [6, 'o'], [7, 'cccccccccc'], [17, 'o'], [18, 'cc'], [20, 'o']),
  15: row([3, 'o'], [4, 'cc'], [6, 'o'], [7, 'cccccccccc'], [17, 'o'], [18, 'cc'], [20, 'o']),
  16: row([3, 'o'], [4, 'cc'], [6, 'o'], [7, 'cccccccccc'], [17, 'o'], [18, 'cc'], [20, 'o']),
  17: row([3, 'o'], [4, 'CC'], [6, 'o'], [7, 'cccccccccc'], [17, 'o'], [18, 'CC'], [20, 'o']),
  18: row([3, 'o'], [4, 'CC'], [6, 'o'], [7, 'CccccccccC'], [17, 'o'], [18, 'CC'], [20, 'o']),
  19: row([3, 'o'], [4, 'ss'], [6, 'o'], [7, 'aaaaaaaaaa'], [17, 'o'], [18, 'ss'], [20, 'o']),
  20: row([3, 'o'], [4, 'ss'], [6, 'o'], [7, 'CCCCCCCCCC'], [17, 'o'], [18, 'ss'], [20, 'o']),
  21: row([4, 'oo'], [6, 'o'], [7, 'CCCCCCCCCC'], [17, 'o'], [18, 'oo']),
  22: row([7, 'o'], [8, 'ppp'], [11, 'oo'], [13, 'ppp'], [16, 'o']),
  23: row([7, 'o'], [8, 'ppp'], [11, 'oo'], [13, 'ppp'], [16, 'o']),
  24: row([7, 'o'], [8, 'ppp'], [11, 'oo'], [13, 'ppp'], [16, 'o']),
  25: row([7, 'o'], [8, 'ppp'], [11, 'oo'], [13, 'ppp'], [16, 'o']),
  26: row([7, 'o'], [8, 'ppp'], [11, 'oo'], [13, 'ppp'], [16, 'o']),
  27: row([7, 'o'], [8, 'bbb'], [11, 'oo'], [13, 'bbb'], [16, 'o']),
  28: row([7, 'o'], [8, 'bbb'], [11, 'oo'], [13, 'bbb'], [16, 'o']),
  29: row([6, 'o'], [7, 'bbbb'], [11, 'oo'], [13, 'bbbb'], [17, 'o']),
  30: row([6, 'ooooo'], [13, 'ooooo']),
}

const HAIR = {
  short: {
    2: row([8, 'oooooooo']),
    3: row([7, 'ohHHhhhhho']),
    4: row([7, 'ohh'], [14, 'hho']),
    5: row([7, 'oh'], [15, 'ho']),
  },
  long: {
    2: row([8, 'oooooooo']),
    3: row([7, 'ohHHhhhhho']),
    4: row([6, 'ohhh'], [14, 'hhho']),
    5: row([6, 'ohh'], [15, 'hho']),
    6: row([6, 'oh'], [16, 'ho']),
    7: row([6, 'oh'], [16, 'ho']),
    8: row([6, 'oh'], [16, 'ho']),
    9: row([6, 'oh'], [16, 'ho']),
    10: row([6, 'ohh'], [15, 'hho']),
    11: row([6, 'oo'], [16, 'oo']),
  },
  spiky: {
    0: row([8, 'o'], [11, 'o'], [14, 'o']),
    1: row([7, 'oho'], [10, 'oho'], [13, 'oho']),
    2: row([7, 'ohhhhhhhho']),
    3: row([7, 'ohHhhHhhho']),
    4: row([7, 'ohh'], [14, 'hho']),
    5: row([7, 'oh'], [15, 'ho']),
  },
  bun: {
    0: row([10, 'oooo']),
    1: row([9, 'ohHHho']),
    2: row([8, 'oooooooo']),
    3: row([7, 'ohHHhhhhho']),
    4: row([7, 'ohh'], [14, 'hho']),
    5: row([7, 'oh'], [15, 'ho']),
  },
  mohawk: {
    0: row([10, 'oooo']),
    1: row([10, 'oHho']),
    2: row([10, 'oHho']),
    3: row([7, 'ooo'], [10, 'ohho'], [14, 'ooo']),
  },
  hooded: {
    1: row([8, 'oooooooo']),
    2: row([7, 'occcccccco']),
    3: row([6, 'occCCCCcco']),
    4: row([6, 'occ'], [15, 'cco']),
    5: row([6, 'oc'], [16, 'co']),
    6: row([6, 'oc'], [16, 'co']),
    7: row([6, 'oc'], [16, 'co']),
    8: row([6, 'oc'], [16, 'co']),
    9: row([6, 'oc'], [16, 'co']),
    10: row([6, 'occ'], [15, 'cco']),
    11: row([7, 'oc'], [15, 'co']),
  },
}

const ARMOR_LAYER = {
  12: row([5, 'oAAo'], [15, 'oAAo']),
  13: row([4, 'oAAAo'], [15, 'oAAAo']),
  15: row([9, 'AAAAAA']),
  16: row([9, 'ABBBBA']),
  17: row([9, 'AAAAAA']),
}

const TRINKET_LAYER = {
  13: row([10, 'a'], [13, 'a']),
  14: row([11, 'TT']),
  15: row([11, 'TT']),
}

function weaponLayer(name = '') {
  const lower = name.toLowerCase()
  if (lower.includes('lantern')) {
    return { 18: row([20, 'oo']), 19: row([20, 'oWWo']), 20: row([20, 'oWWo']), 21: row([20, 'oWWo']), 22: row([21, 'oo']) }
  }
  if (lower.includes('compass')) {
    return { 19: row([20, 'oWWo']), 20: row([20, 'oWWo']), 21: row([21, 'oo']) }
  }
  // Blades and anything else: a sword held upright.
  const blade = {}
  for (let y = 10; y <= 17; y += 1) blade[y] = row([20, 'oWo'])
  blade[9] = row([21, 'o'])
  blade[18] = row([19, 'oaaao'])
  return blade
}

const WEAPON_COLORS = { lantern: '#ffcc33', compass: '#c9a875', blade: '#d6dbe6' }

export function buildAvatarGrid(appearance = {}, gear = {}) {
  const look = { ...DEFAULT_APPEARANCE, ...appearance }
  const grid = blank()
  paint(grid, BODY)
  paint(grid, HAIR[look.hair_style] || HAIR.short)
  if (ARMOR_COLORS[gear.armor]) paint(grid, ARMOR_LAYER)
  if (TRINKET_COLORS[gear.trinket]) paint(grid, TRINKET_LAYER)
  if (gear.weapon) paint(grid, weaponLayer(gear.weapon))
  return grid
}

export function avatarPalette(appearance = {}, gear = {}) {
  const look = { ...DEFAULT_APPEARANCE, ...appearance }
  const [skin, skinShade] = AVATAR_PALETTES.skin[look.skin] || AVATAR_PALETTES.skin.tan
  const [hair, hairLight] = AVATAR_PALETTES.hair_color[look.hair_color] || AVATAR_PALETTES.hair_color.brown
  const [outfit, outfitShade] = AVATAR_PALETTES.outfit[look.outfit] || AVATAR_PALETTES.outfit.indigo
  const [armor, armorShade] = ARMOR_COLORS[gear.armor] || ['#888', '#666']
  const weaponKind = /lantern/i.test(gear.weapon || '') ? 'lantern' : /compass/i.test(gear.weapon || '') ? 'compass' : 'blade'
  return {
    o: '#0b0a14', s: skin, S: skinShade, M: skinShade, w: '#f4ecd8',
    e: AVATAR_PALETTES.eyes[look.eyes] || AVATAR_PALETTES.eyes.brown,
    h: hair, H: hairLight, c: outfit, C: outfitShade,
    a: AVATAR_PALETTES.accent[look.accent] || AVATAR_PALETTES.accent.gold,
    p: '#2b2a3d', b: '#4a2c1a', A: armor, B: armorShade,
    T: TRINKET_COLORS[gear.trinket] || '#ffcc33', W: WEAPON_COLORS[weaponKind],
  }
}

// Horizontal runs of one colour become one rect, keeping the SVG small.
export function avatarRects(appearance = {}, gear = {}) {
  const grid = buildAvatarGrid(appearance, gear)
  const palette = avatarPalette(appearance, gear)
  const rects = []
  grid.forEach((line, y) => {
    let x = 0
    while (x < WIDTH) {
      const token = line[x]
      if (token === '.' || !palette[token]) { x += 1; continue }
      let end = x + 1
      while (end < WIDTH && line[end] === token) end += 1
      rects.push({ x, y, width: end - x, fill: palette[token] })
      x = end
    }
  })
  return rects
}

export const AVATAR_VIEWBOX = `0 0 ${WIDTH} ${HEIGHT}`
