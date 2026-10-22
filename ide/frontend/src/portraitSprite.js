// Character portrait: a 48x48 head-and-shoulders pixel bust where hairstyles
// have room for real detail (locs, twists, knots, waves, fades). Hand-drawn
// styles live in portraitHair.js as pixel rows; the rest are small routines.
// Either way a style paints a back layer (behind the head) and a front layer
// (hairline, fringe, sides) with dark/base/highlight shades.
//
// Tokens: o outline · s skin · S skin shade · L skin light · w eye white ·
// e iris · m lip · c/C outfit · a trim · h/H/d hair base/highlight/dark ·
// f/q fade (hair blended into skin, then lighter) · y/Y/z beard.

import { AVATAR_PALETTES, DEFAULT_APPEARANCE } from './avatarSprite.js'
import { PORTRAIT_HAIR } from './portraitHair.js'

export const PORTRAIT_SIZE = 48
const SIZE = PORTRAIT_SIZE

// Head geometry
const CX = 23.5
const CY = 20
const RX = 10.5
const RY = 12
const HAIRLINE = 12 // forehead top at the centre

function hash(x, y, salt = 0) {
  let n = (x * 374761393 + y * 668265263 + salt * 2147483647) | 0
  n = (n ^ (n >>> 13)) * 1274126177
  return ((n ^ (n >>> 16)) >>> 0) % 1000
}

function makeGrid() {
  return Array.from({ length: SIZE }, () => Array(SIZE).fill(null))
}

function set(grid, x, y, token) {
  if (x >= 0 && x < SIZE && y >= 0 && y < SIZE) grid[y][x] = token
}

function inEllipse(x, y, cx, cy, rx, ry) {
  const dx = (x + 0.5 - cx) / rx
  const dy = (y + 0.5 - cy) / ry
  return dx * dx + dy * dy <= 1
}

function inHead(x, y, grow = 0) {
  return inEllipse(x, y, CX, CY, RX + grow, RY + grow)
}

// Hairline height at column x: lowest at the temples, highest mid-forehead.
function hairlineAt(x) {
  const t = Math.abs(x + 0.5 - CX) / RX
  return Math.round(HAIRLINE + t * t * 4)
}

// ── Body and face ──────────────────────────────────────────────────────

function paintBody(grid) {
  // Shoulders and chest.
  for (let y = 37; y < SIZE; y += 1) {
    const half = Math.min(19, 10 + (y - 37) * 2)
    for (let x = Math.floor(CX - half); x <= Math.ceil(CX + half - 1); x += 1) {
      const shade = x > CX + half - 4 ? 'C' : 'c'
      set(grid, x, y, shade)
    }
  }
  // Neck.
  for (let y = 29; y < 39; y += 1) {
    for (let x = 19; x <= 28; x += 1) set(grid, x, y, x >= 26 || y <= 31 ? 'S' : 's')
  }
  // Collar trim.
  for (let x = 17; x <= 30; x += 1) set(grid, x, 38, 'a')
  for (let x = 18; x <= 29; x += 1) set(grid, x, 39, 'a')
}

function paintHead(grid) {
  // Ears: small rounded shapes with an inner shadow.
  for (let y = 18; y <= 25; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      if (inEllipse(x, y, 12.5, 21.5, 1.8, 3.8)) set(grid, x, y, x === 12 && y > 19 && y < 24 ? 'S' : 's')
      if (inEllipse(x, y, 35, 21.5, 1.8, 3.8)) set(grid, x, y, x === 35 && y > 19 && y < 24 ? 'S' : 'S')
    }
  }
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      if (!inHead(x, y)) continue
      // Light from the upper left: shade the right edge and under the jaw.
      const right = (x + 0.5 - CX) / RX
      const low = (y + 0.5 - CY) / RY
      set(grid, x, y, right > 0.62 || low > 0.86 ? 'S' : 's')
    }
  }
}

function paintFace(grid, look) {
  // Brows (hair dark), eyes, nose, mouth.
  for (let x = 16; x <= 20; x += 1) set(grid, x, 18, 'd')
  for (let x = 27; x <= 31; x += 1) set(grid, x, 18, 'd')
  const eye = (x0) => {
    set(grid, x0, 21, 'w'); set(grid, x0 + 1, 21, 'e'); set(grid, x0 + 2, 21, 'e'); set(grid, x0 + 3, 21, 'w')
    set(grid, x0 + 1, 20, 'o'); set(grid, x0 + 2, 20, 'o')
    set(grid, x0 + 1, 22, 'e'); set(grid, x0 + 2, 22, 'e')
  }
  eye(16)
  eye(28)
  set(grid, 25, 22, 'S'); set(grid, 25, 23, 'S'); set(grid, 25, 24, 'S')
  set(grid, 23, 25, 'L'); set(grid, 24, 25, 'L')
  set(grid, 22, 26, 'S'); set(grid, 23, 26, 'S'); set(grid, 24, 26, 'S'); set(grid, 25, 26, 'S')
  for (let x = 21; x <= 26; x += 1) set(grid, x, 28, 'm')
  for (let x = 22; x <= 25; x += 1) set(grid, x, 29, 'S')
  void look
}

// ── Hair helpers ───────────────────────────────────────────────────────

// Scalp cap: everything above the hairline inside the (grown) head shape.
function capPixels(grow = 1.2, lift = 0) {
  const pixels = []
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      if (!inEllipse(x, y + lift, CX, CY, RX + grow, RY + grow)) continue
      if (y >= hairlineAt(x)) continue
      pixels.push([x, y])
    }
  }
  return pixels
}

// Faded sides: hair over the temples thins to the fade colours and is gone
// before the ear, so the ears and the skin below stay clean. A thin faded
// sideburn runs down in front of each ear.
function paintFade(grid) {
  for (let y = 11; y <= 18; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      const left = x + 0.5 < CX - RX + 3.5
      const right = x + 0.5 > CX + RX - 3.5
      if ((!left && !right) || !inHead(x, y, 1.2)) continue
      const token = y <= 12 ? 'h' : y <= 14 ? 'f' : y === 15 ? ((x + y) % 2 ? 'q' : null) : null
      if (token) set(grid, x, y, token)
      else if (inHead(x, y)) set(grid, x, y, right && (x + 0.5 - CX) / RX > 0.62 ? 'S' : 's')
      else set(grid, x, y, null)
    }
  }
  for (let y = 15; y <= 18; y += 1) {
    set(grid, 14, y, 'q')
    set(grid, 33, y, 'q')
  }
}

// Lineup: a crisp, straight hairline with squared temple corners.
function lineupAt(x) {
  const t = Math.abs(x + 0.5 - CX)
  return t < 7 ? HAIRLINE : t < 8.5 ? HAIRLINE + 1 : HAIRLINE + 3
}

function paintCap(grid, { grow = 1.2, lift = 0, lineup = false, texture = () => 'h' } = {}) {
  for (const [x, y] of capPixels(grow, lift)) {
    if (lineup && y >= lineupAt(x)) continue
    set(grid, x, y, texture(x, y))
  }
}

// Paint a hand-drawn layer from portraitHair.js ('.' is transparent).
function paintArt(grid, art = '') {
  for (const line of art.split('\n')) {
    const match = line.match(/^\s*(\d+) (.*)$/)
    if (!match) continue
    ;[...match[2]].forEach((token, x) => { if (token !== '.') set(grid, x, Number(match[1]), token) })
  }
}


// ── Styles: back layer (behind head) and front layer (over head) ────────

const STYLES = {
  taper: {
    front(grid) {
      paintCap(grid, { grow: 1.1, lineup: true, texture: (x, y) => (hash(x, y) % 6 === 0 ? 'H' : 'h') })
      paintFade(grid)
    },
  },
  brush_cut: {
    front(grid) {
      paintCap(grid, { grow: 1.6, lift: 1.2, lineup: true, texture: (x, y) => (x % 2 === 0 && y % 3 !== 0 ? 'H' : 'h') })
      paintFade(grid)
    },
  },
  waves: {
    front(grid) {
      paintCap(grid, {
        grow: 1.0,
        lineup: true,
        texture: (x, y) => {
          const d = y + 1.4 * Math.sin((x + 0.5) / 1.9) + Math.abs(x + 0.5 - CX) * 0.18
          const band = ((Math.floor(d) % 3) + 3) % 3
          return band === 0 ? 'H' : band === 1 ? 'h' : 'd'
        },
      })
      paintFade(grid)
    },
  },
  afro: {
    back(grid) {
      const cx = CX
      const cy = 17
      const r = 17
      for (let y = 0; y < 36; y += 1) {
        for (let x = 0; x < SIZE; x += 1) {
          if (!inEllipse(x, y, cx, cy, r, r * 0.95)) continue
          const roll = hash(x, y, 3)
          const lit = x + 0.5 < cx - r * 0.25 && y + 0.5 < cy - r * 0.25
          set(grid, x, y, roll % 7 === 0 ? 'd' : lit && roll % 3 === 0 ? 'H' : roll % 11 === 0 ? 'H' : 'h')
        }
      }
    },
    front(grid) {
      paintCap(grid, { grow: 1.6, texture: (x, y) => (hash(x, y, 3) % 7 === 0 ? 'd' : 'h') })
    },
  },
  hooded: {
    back(grid) {
      for (let y = 2; y < 40; y += 1) {
        for (let x = 0; x < SIZE; x += 1) if (inEllipse(x, y, CX, 19, 15, 18)) set(grid, x, y, x > CX + 8 ? 'C' : 'c')
      }
    },
    front(grid) {
      for (let y = 4; y < 14; y += 1) {
        for (let x = 0; x < SIZE; x += 1) if (inHead(x, y, 1.5) && y < hairlineAt(x) + 1) set(grid, x, y, 'c')
      }
    },
  },
}

const BEARDS = {
  none: () => {},
  stubble(grid) {
    for (let y = 22; y < 33; y += 1) for (let x = 0; x < SIZE; x += 1) {
      if (!inHead(x, y) || grid[y][x] === 'm' || grid[y][x] === 'e' || grid[y][x] === 'w') continue
      const jaw = y >= 26 || x + 0.5 < CX - RX + 2.5 || x + 0.5 > CX + RX - 2.5
      if (jaw && hash(x, y, 11) % 3 !== 0) set(grid, x, y, 'z')
    }
  },
  mustache(grid) {
    for (let x = 20; x <= 27; x += 1) { set(grid, x, 27, 'y'); if (x > 20 && x < 27) set(grid, x, 26, 'y') }
  },
  goatee(grid) {
    for (let y = 29; y <= 32; y += 1) for (let x = 21; x <= 26; x += 1) if (grid[y][x] !== 'm') set(grid, x, y, (x + y) % 3 === 0 ? 'Y' : 'y')
  },
  circle_beard(grid) {
    BEARDS.mustache(grid)
    BEARDS.goatee(grid)
    for (let y = 27; y <= 29; y += 1) { set(grid, 20, y, 'y'); set(grid, 27, y, 'y') }
  },
  chin_strap(grid) {
    for (let y = 18; y < 34; y += 1) for (let x = 0; x < SIZE; x += 1) {
      if (inHead(x, y) && !inHead(x, y, -1.4)) set(grid, x, y, 'y')
    }
  },
  full_beard(grid) {
    for (let y = 22; y < 36; y += 1) for (let x = 0; x < SIZE; x += 1) {
      if (!inHead(x, y, 0.8)) continue
      const cheek = y >= 23 && (x + 0.5 < 18 || x + 0.5 > 30)
      const lower = y >= 26
      if (!cheek && !lower) continue
      if (y >= 28 && y <= 29 && x >= 21 && x <= 26) continue // keep the mouth visible
      set(grid, x, y, hash(x, y, 13) % 4 === 0 ? 'Y' : hash(x, y, 14) % 5 === 0 ? 'z' : 'y')
    }
  },
}

// Outline every filled pixel that touches empty space.
function outline(grid) {
  const out = grid.map((line) => [...line])
  for (let y = 0; y < SIZE; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      if (grid[y][x] !== null) continue
      const near = [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => grid[y + dy]?.[x + dx] != null)
      if (near) out[y][x] = 'o'
    }
  }
  return out
}

function mix(first, second, weight = 0.5) {
  const ch = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16))
  const a = ch(first)
  const b = ch(second)
  return `#${a.map((v, i) => Math.round(v * (1 - weight) + b[i] * weight).toString(16).padStart(2, '0')).join('')}`
}

export function portraitPalette(appearance = {}) {
  const look = { ...DEFAULT_APPEARANCE, ...appearance }
  const [skin, skinShade] = AVATAR_PALETTES.skin[look.skin] || AVATAR_PALETTES.skin.umber
  const [hair, hairLight] = AVATAR_PALETTES.hair_color[look.hair_color] || AVATAR_PALETTES.hair_color.black
  const [beard, beardLight] = AVATAR_PALETTES.hair_color[look.beard_color] || [hair, hairLight]
  const [outfit, outfitShade] = AVATAR_PALETTES.outfit[look.outfit] || AVATAR_PALETTES.outfit.indigo
  return {
    o: '#0b0a14', s: skin, S: skinShade, L: mix(skin, '#ffffff', 0.12), w: '#f4ecd8',
    e: AVATAR_PALETTES.eyes[look.eyes] || AVATAR_PALETTES.eyes.brown, m: mix(skinShade, '#3a1c1c', 0.4),
    h: hair, H: mix(hairLight, '#ffffff', 0.12), d: mix(hair, '#000000', 0.45), f: mix(hair, skinShade, 0.45), q: mix(hair, skinShade, 0.75),
    y: beard, Y: beardLight, z: mix(beard, skinShade, 0.5),
    c: outfit, C: outfitShade, a: AVATAR_PALETTES.accent[look.accent] || AVATAR_PALETTES.accent.gold,
  }
}

export function buildPortraitGrid(appearance = {}) {
  const look = { ...DEFAULT_APPEARANCE, ...appearance }
  const entry = PORTRAIT_HAIR[look.hair_style]
  const art = entry?.lengths ? entry.lengths[look.hair_length] || Object.values(entry.lengths)[0] : entry
  const style = art ? {
    back: (grid) => paintArt(grid, art.back),
    front: (grid) => { if (entry.fade) paintFade(grid); paintArt(grid, art.front) },
  } : STYLES[look.hair_style] || STYLES.taper
  const grid = makeGrid()
  style.back?.(grid, look)
  paintBody(grid)
  paintHead(grid)
  paintFace(grid, look)
  ;(BEARDS[look.facial_hair] || BEARDS.none)(grid)
  style.front?.(grid, look)
  return outline(grid)
}

export function portraitRects(appearance = {}) {
  const grid = buildPortraitGrid(appearance)
  const palette = portraitPalette(appearance)
  const rects = []
  grid.forEach((line, y) => {
    let x = 0
    while (x < SIZE) {
      const token = line[x]
      if (!token || !palette[token]) { x += 1; continue }
      let end = x + 1
      while (end < SIZE && line[end] === token) end += 1
      rects.push({ x, y, width: end - x, fill: palette[token] })
      x = end
    }
  })
  return rects
}

export const PORTRAIT_STYLES = [...Object.keys(PORTRAIT_HAIR), ...Object.keys(STYLES)]
