// Character portrait: a 48x48 head-and-shoulders pixel bust where hairstyles
// have room for real texture (locs, coils, knots, waves, fades). Each style
// is a small routine that paints a back layer (behind the head) and a front
// layer (hairline, fringe, sides) with dark/base/highlight shades.
//
// Tokens: o outline · s skin · S skin shade · L skin light · w eye white ·
// e iris · m lip · c/C outfit · a trim · h/H/d hair base/highlight/dark ·
// f/q fade (hair blended into skin, then lighter) · y/Y/z beard.

import { AVATAR_PALETTES, DEFAULT_APPEARANCE } from './avatarSprite.js'

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
      const token = right > 0.62 || low > 0.86 ? 'S' : right < -0.6 && low > -0.45 && low < 0.05 ? 'L' : 's'
      set(grid, x, y, token)
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

// Tapered sides: from the temples down past the ears, fading into skin.
function paintFade(grid, top = 13, bottom = 24) {
  for (let y = top; y <= bottom; y += 1) {
    for (let x = 0; x < SIZE; x += 1) {
      const side = x + 0.5 < CX - RX + 3.2 || x + 0.5 > CX + RX - 3.2
      if (!side || !inHead(x, y, 0.8)) continue
      const depth = (y - top) / Math.max(1, bottom - top)
      const roll = hash(x, y, 7) / 1000
      const token = depth < 0.35 ? (roll < 0.75 ? 'h' : 'f') : depth < 0.7 ? (roll < 0.6 ? 'f' : 'q') : roll < 0.35 ? 'q' : null
      if (token) set(grid, x, y, token)
    }
  }
}

function paintCap(grid, { grow = 1.2, lift = 0, texture = () => 'h' } = {}) {
  for (const [x, y] of capPixels(grow, lift)) set(grid, x, y, texture(x, y))
}

// A hanging strand (loc or twist) of `width` pixels from (x, y0) to y1.
function strand(grid, x, y0, y1, width, shade) {
  for (let y = y0; y <= y1; y += 1) {
    for (let i = 0; i < width; i += 1) set(grid, x + i, y, shade(i, y, y1))
  }
}

const locShade = (salt) => (i, y, end) => {
  if (y === end) return i === 0 ? 'd' : 'h' // rounded tip
  if ((y + salt) % 4 === 0) return 'd' // segment notch
  return i === 0 ? 'H' : 'h'
}

const twistShade = (i, y) => {
  const phase = (y + i) % 3
  return phase === 0 ? 'd' : phase === 1 ? 'h' : 'H'
}

function knot(grid, cx, cy, r) {
  for (let y = Math.floor(cy - r); y <= Math.ceil(cy + r); y += 1) {
    for (let x = Math.floor(cx - r); x <= Math.ceil(cx + r); x += 1) {
      if (!inEllipse(x, y, cx, cy, r, r)) continue
      const angle = Math.atan2(y + 0.5 - cy, x + 0.5 - cx)
      const dist = Math.hypot(x + 0.5 - cx, y + 0.5 - cy) / r
      const spiral = Math.floor((angle / (Math.PI * 2) + dist * 1.5) * 3) % 2 === 0
      const lit = x + 0.5 < cx && y + 0.5 < cy
      set(grid, x, y, dist > 0.85 ? 'd' : lit && spiral ? 'H' : spiral ? 'h' : 'd')
    }
  }
}

function cloud(grid, cx, cy, r) {
  for (let y = Math.floor(cy - r); y <= Math.ceil(cy + r); y += 1) {
    for (let x = Math.floor(cx - r); x <= Math.ceil(cx + r); x += 1) {
      if (!inEllipse(x, y, cx, cy, r, r)) continue
      const dx = x + 0.5 - cx
      const dy = y + 0.5 - cy
      const token = dx < -r * 0.2 && dy < -r * 0.2 ? 'H' : dx > r * 0.35 || dy > r * 0.45 ? 'd' : 'h'
      set(grid, x, y, token)
    }
  }
}

// ── Styles: back layer (behind head) and front layer (over head) ────────

const STYLES = {
  taper: {
    front(grid) {
      paintCap(grid, { grow: 1.1, texture: (x, y) => (hash(x, y) % 6 === 0 ? 'H' : 'h') })
      paintFade(grid)
    },
  },
  brush_cut: {
    front(grid) {
      paintCap(grid, { grow: 1.6, lift: 1.2, texture: (x, y) => (x % 2 === 0 && y % 3 !== 0 ? 'H' : 'h') })
      paintFade(grid)
    },
  },
  waves: {
    front(grid) {
      paintCap(grid, {
        grow: 1.0,
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
  twist_out: {
    back(grid) {
      const clumps = []
      for (let a = 180; a <= 360; a += 22) clumps.push([CX + Math.cos((a * Math.PI) / 180) * 12.5, 17 + Math.sin((a * Math.PI) / 180) * 12])
      clumps.push([10.5, 25], [36.5, 25], [11.5, 30], [35.5, 30])
      for (const [x, y] of clumps) cloud(grid, x, y, 4.6)
    },
    front(grid) {
      paintCap(grid, { grow: 1.5, texture: (x, y) => (hash(x, y, 9) % 5 === 0 ? 'H' : 'h') })
      for (const x of [15, 19, 23.5, 28, 32]) cloud(grid, x, 9.5, 3.2)
    },
  },
  bantu_knots: {
    front(grid) {
      paintCap(grid, {
        grow: 0.9,
        texture: (x, y) => ((x === 18 || x === 29) && y < 11 ? 'S' : hash(x, y) % 5 === 0 ? 'H' : 'h'),
      })
      knot(grid, 23.5, 4.5, 4.4)
      knot(grid, 13.5, 8.5, 4)
      knot(grid, 33.5, 8.5, 4)
    },
  },
  locs_taper: {
    front(grid) {
      paintCap(grid, { grow: 1.1, texture: (x) => (x % 3 === 0 ? 'd' : 'h') })
      paintFade(grid, 15, 24)
      // Short locs: roots across the top, falling forward over the hairline
      // and a little further down at the temples. A dark gap between locs.
      for (let x = 13; x <= 33; x += 3) {
        const t = Math.abs(x + 1 - CX) / RX
        const top = Math.round(7 + t * t * 3)
        const end = Math.round(13 + t * 4 + (hash(x, 1) % 2))
        strand(grid, x, top, end, 2, locShade(x))
        for (let y = top; y <= end; y += 1) if (grid[y][x + 2] === 'h' || grid[y][x + 2] === 's' || grid[y][x + 2] === 'L') set(grid, x + 2, y, y > hairlineAt(x + 2) ? grid[y][x + 2] : 'd')
      }
    },
  },
  freeform: {
    back(grid) {
      // Long locs behind the head down past the shoulders.
      for (let x = 9; x <= 37; x += 2) {
        const width = 2 + (hash(x, 4) % 2)
        const end = 36 + (hash(x, 5) % 7)
        strand(grid, x, 8, end, width, locShade(x * 3))
      }
    },
    front(grid) {
      paintCap(grid, { grow: 1.5, lift: 0.6, texture: (x) => (x % 3 === 0 ? 'd' : x % 3 === 1 ? 'h' : 'H') })
      // Side locs framing the face, in front of the ears.
      for (const x of [10, 12, 34, 36]) strand(grid, x, 12, 33 + (hash(x, 6) % 5), 2, locShade(x))
      for (const x of [15, 18, 29, 32]) strand(grid, x, 9, 13 + (hash(x, 7) % 2), 2, locShade(x))
    },
  },
  twists: {
    back(grid) {
      for (let x = 8; x <= 37; x += 4) strand(grid, x, 9, 30 + (hash(x, 8) % 4), 3, twistShade)
    },
    front(grid) {
      paintCap(grid, { grow: 1.4, lift: 0.5, texture: (x, y) => (x % 4 === 3 ? 'd' : twistShade(x % 4, y)) })
      for (const x of [9, 35]) strand(grid, x, 12, 31, 3, twistShade)
      for (const x of [14, 18, 27, 31]) strand(grid, x, 8, 13 + (hash(x, 3) % 2), 3, twistShade)
    },
  },
  barrel_twists: {
    front(grid) {
      paintCap(grid, { grow: 1.0, texture: () => 'h' })
      paintFade(grid)
      for (let x = 12; x <= 32; x += 5) {
        const t = Math.abs(x + 2 - CX) / RX
        const top = Math.round(1 + t * 4 + (hash(x, 2) % 2))
        for (let y = top; y <= 13; y += 1) {
          for (let i = 0; i < 4; i += 1) {
            const band = (y + i) % 4 === 0
            set(grid, x + i, y, band ? 'd' : i === 0 ? 'd' : i === 1 ? 'H' : 'h')
          }
          set(grid, x + 4, y, 'd')
        }
        set(grid, x, top, null)
        set(grid, x + 3, top, null)
        set(grid, x + 4, top, null)
      }
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
  const style = STYLES[look.hair_style] || STYLES.locs_taper
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

export const PORTRAIT_STYLES = Object.keys(STYLES)
