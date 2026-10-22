// Player paper-doll: a 24x32 pixel sprite built from layers (body, outfit,
// hair, armor, trinket, weapon) in the same grid style as the Merchant.
// Appearance values are the option names stored in equipment.avatar
// (state.py AVATAR_OPTIONS); gear is the equipped item names.

const WIDTH = 24
const HEIGHT = 32

export const AVATAR_PALETTES = {
  skin: {
    espresso: ['#4a2c1c', '#33190f'], deep: ['#5a3825', '#3f2618'], umber: ['#6e4228', '#4f2c19'],
    brown: ['#8d5a3b', '#6b3f27'], caramel: ['#b07848', '#8a5a33'], tan: ['#d9a066', '#b07a45'],
    olive: ['#b98a5a', '#8f6640'], fair: ['#f1c9a5', '#cf9f7c'], porcelain: ['#f6dccb', '#d9b39d'],
  },
  hair_color: {
    black: ['#141218', '#2c2830'], dark_brown: ['#2e1d14', '#4a3022'], brown: ['#5b3a29', '#8a5a3d'],
    auburn: ['#8c3b22', '#c2603a'], copper: ['#b5562a', '#e07a45'], honey: ['#a8742a', '#d9a24e'],
    blonde: ['#c9a23a', '#f2d77e'], platinum: ['#d9d4c3', '#f5f2e6'], silver: ['#9aa1ae', '#e6eaf2'],
    white: ['#e2e2e2', '#ffffff'], burgundy: ['#5e1a2a', '#8a2a40'], crimson: ['#a3263b', '#d94a60'],
    pink: ['#d9568a', '#f28ab0'], violet: ['#5b3a99', '#8f6bd6'], blue: ['#2a4fb5', '#4f7ae0'],
    teal: ['#1f7a78', '#3fb3ad'], green: ['#2f7a3a', '#4fae5a'],
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
  skin: 'Skin', hair_style: 'Hair', hair_color: 'Hair colour', facial_hair: 'Facial hair', eyes: 'Eyes', outfit: 'Outfit', accent: 'Trim',
}

export const DEFAULT_APPEARANCE = { skin: 'umber', hair_style: 'locs_taper', hair_color: 'black', facial_hair: 'none', eyes: 'brown', outfit: 'indigo', accent: 'gold' }

// Button labels for the hair styles (option values are state identifiers).
export const AVATAR_STYLE_LABELS = {
  locs_taper: 'Locs + taper', freeform: 'Freeform locs', twists: 'Two-strand twists', barrel_twists: 'Barrel twists',
  twist_out: 'Twist-out', afro: 'Afro', bantu_knots: 'Bantu knots', waves: '360 waves', brush_cut: 'Brush cut',
  taper: 'Taper fade', hooded: 'Hood',
  none: 'Clean shaven', stubble: 'Stubble', mustache: 'Mustache', goatee: 'Goatee', circle_beard: 'Circle beard',
  chin_strap: 'Chin strap', full_beard: 'Full beard',
}

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

// 50/50 blend of two #rrggbb colours (the taper fade).
function mix(first, second) {
  const channels = (hex) => [1, 3, 5].map((index) => parseInt(hex.slice(index, index + 2), 16))
  const a = channels(first)
  const b = channels(second)
  return `#${a.map((value, index) => Math.round((value + b[index]) / 2).toString(16).padStart(2, '0')).join('')}`
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

// Hair styles. Face cells are x8..15 on rows 4-10, the head outline sits on
// x7/x16; 'f' is the fade (hair blended into skin) used by tapers.
const HAIR = {
  locs_taper: {
    1: row([8, 'oooooooo']),
    2: row([7, 'ohHhHhHhHo']),
    3: row([7, 'ohHhHhHhHo']),
    4: row([7, 'o'], [8, 'f'], [9, 'H'], [11, 'h'], [13, 'H'], [15, 'f'], [16, 'o']),
    5: row([7, 'o'], [8, 'f'], [10, 'h'], [12, 'H'], [15, 'f'], [16, 'o']),
  },
  freeform: {
    1: row([8, 'oooooooo']),
    2: row([7, 'ohhHhhHhho']),
    3: row([6, 'ohHhhHhHhhHo']),
    4: row([5, 'ohHh'], [15, 'hHho']),
    5: row([5, 'oHh'], [16, 'hHo']),
    6: row([5, 'ohH'], [16, 'Hho']),
    7: row([5, 'oHh'], [16, 'Hho']),
    8: row([5, 'ohH'], [16, 'hHo']),
    9: row([5, 'oHh'], [16, 'Hho']),
    10: row([5, 'ohH'], [16, 'hHo']),
    11: row([5, 'oHh'], [16, 'Hho']),
    12: row([5, 'ohH'], [16, 'hHo']),
    13: row([5, 'oh'], [17, 'ho']),
    14: row([5, 'o'], [18, 'o']),
  },
  twists: {
    1: row([8, 'oooooooo']),
    2: row([7, 'ohHhHhHhHo']),
    3: row([6, 'ohHhHhHhHhHo']),
    4: row([5, 'oHhH'], [15, 'HhHo']),
    5: row([5, 'oHh'], [16, 'hHo']),
    6: row([5, 'ohH'], [16, 'Hho']),
    7: row([5, 'oHh'], [16, 'hHo']),
    8: row([5, 'ohH'], [16, 'Hho']),
    9: row([5, 'oHh'], [16, 'hHo']),
    10: row([5, 'oho'], [16, 'oho']),
    11: row([6, 'o'], [17, 'o']),
  },
  barrel_twists: {
    0: row([8, 'oo'], [11, 'oo'], [14, 'oo']),
    1: row([7, 'ohHohHohHo']),
    2: row([7, 'ohHohHohHo']),
    3: row([7, 'ohHohHohHo']),
    4: row([7, 'o'], [8, 'f'], [15, 'f'], [16, 'o']),
    5: row([7, 'o'], [8, 'f'], [15, 'f'], [16, 'o']),
  },
  twist_out: {
    1: row([7, 'oooooooooo']),
    2: row([6, 'ohHhhHhhHhho']),
    3: row([5, 'ohhHhhHhhHhhHo']),
    4: row([5, 'oHh'], [16, 'hHo']),
    5: row([5, 'ohH'], [16, 'Hho']),
    6: row([5, 'oHh'], [16, 'hHo']),
    7: row([5, 'ohH'], [16, 'Hho']),
    8: row([6, 'oo'], [16, 'oo']),
  },
  afro: {
    0: row([8, 'oooooooo']),
    1: row([6, 'oohhhhhhhhoo']),
    2: row([5, 'ohhhHhhhHhhhho']),
    3: row([4, 'ohhhhhhhhhhhhhho']),
    4: row([4, 'ohhhh'], [15, 'hhhho']),
    5: row([4, 'ohhh'], [16, 'hhho']),
    6: row([4, 'ohhh'], [16, 'hhho']),
    7: row([4, 'ohhh'], [16, 'hhho']),
    8: row([5, 'ohh'], [16, 'hho']),
    9: row([6, 'oo'], [16, 'oo']),
  },
  bantu_knots: {
    0: row([7, 'ooo'], [10, 'oooo'], [14, 'ooo']),
    1: row([7, 'oHo'], [10, 'oHHo'], [14, 'oHo']),
    2: row([7, 'ooo'], [10, 'oooo'], [14, 'ooo']),
    3: row([7, 'ohhohhohho']),
    4: row([7, 'oh'], [15, 'ho']),
  },
  waves: {
    1: row([8, 'oooooooo']),
    2: row([7, 'ohHhhHhhHo']),
    3: row([7, 'oHhhHhhHho']),
    4: row([7, 'oh'], [15, 'ho']),
    5: row([7, 'o'], [8, 'f'], [15, 'f'], [16, 'o']),
  },
  brush_cut: {
    1: row([8, 'oooooooo']),
    2: row([7, 'ohHhHhHhho']),
    3: row([7, 'ohhhhhhhho']),
    4: row([7, 'o'], [8, 'h'], [15, 'h'], [16, 'o']),
    5: row([7, 'o'], [8, 'f'], [15, 'f'], [16, 'o']),
  },
  taper: {
    2: row([8, 'oooooooo']),
    3: row([7, 'ohhhhhhhho']),
    4: row([7, 'o'], [8, 'f'], [15, 'f'], [16, 'o']),
    5: row([7, 'o'], [8, 'f'], [15, 'f'], [16, 'o']),
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

// Facial hair, drawn in the hair colour (stubble in the fade colour). The
// mouth sits on row 9 (x11-12) and the chin on row 10 (x9-14).
const FACIAL_HAIR = {
  none: {},
  stubble: {
    8: row([8, 'f'], [15, 'f']),
    9: row([8, 'f'], [10, 'f'], [13, 'f'], [15, 'f']),
    10: row([9, 'ffffff']),
  },
  mustache: {
    8: row([10, 'hhhh']),
  },
  goatee: {
    9: row([10, 'h'], [13, 'h']),
    10: row([10, 'hhhh']),
  },
  circle_beard: {
    8: row([10, 'hhhh']),
    9: row([10, 'h'], [13, 'h']),
    10: row([10, 'hhhh']),
  },
  chin_strap: {
    8: row([8, 'h'], [15, 'h']),
    9: row([8, 'h'], [15, 'h']),
    10: row([9, 'hhhhhh']),
  },
  full_beard: {
    7: row([8, 'h'], [15, 'h']),
    8: row([8, 'h'], [10, 'hHhh'], [15, 'h']),
    9: row([8, 'hhh'], [13, 'hhh']),
    10: row([8, 'ohhHhhho']),
    11: row([9, 'ohhhho']),
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
  paint(grid, HAIR[look.hair_style] || HAIR.locs_taper)
  paint(grid, FACIAL_HAIR[look.facial_hair] || FACIAL_HAIR.none)
  if (ARMOR_COLORS[gear.armor]) paint(grid, ARMOR_LAYER)
  if (TRINKET_COLORS[gear.trinket]) paint(grid, TRINKET_LAYER)
  if (gear.weapon) paint(grid, weaponLayer(gear.weapon))
  return grid
}

export function avatarPalette(appearance = {}, gear = {}) {
  const look = { ...DEFAULT_APPEARANCE, ...appearance }
  const [skin, skinShade] = AVATAR_PALETTES.skin[look.skin] || AVATAR_PALETTES.skin.umber
  const [hair, hairLight] = AVATAR_PALETTES.hair_color[look.hair_color] || AVATAR_PALETTES.hair_color.black
  const [outfit, outfitShade] = AVATAR_PALETTES.outfit[look.outfit] || AVATAR_PALETTES.outfit.indigo
  const [armor, armorShade] = ARMOR_COLORS[gear.armor] || ['#888', '#666']
  const weaponKind = /lantern/i.test(gear.weapon || '') ? 'lantern' : /compass/i.test(gear.weapon || '') ? 'compass' : 'blade'
  return {
    o: '#0b0a14', s: skin, S: skinShade, M: skinShade, w: '#f4ecd8',
    e: AVATAR_PALETTES.eyes[look.eyes] || AVATAR_PALETTES.eyes.brown,
    h: hair, H: hairLight, f: mix(hair, skinShade), c: outfit, C: outfitShade,
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
