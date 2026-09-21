const GRID_WIDTH = 24
const GRID_HEIGHT = 32

// The Merchant is deliberately authored as a tiny, bounded pixel sheet rather
// than a scaled illustration. Every glyph occupies exactly one cell; the
// renderer validates this contract before it reaches the DOM.
const PALETTE = {
  o: '#091212', // outline
  k: '#17221f', // deepest cloth shadow
  t: '#164945', // robe shadow
  T: '#2d8178', // robe
  U: '#4fa696', // robe highlight
  b: '#4a2a20', // leather shadow
  B: '#8b4b2c', // leather
  f: '#281c1d', // deep skin shadow
  F: '#5b392f', // skin midtone
  s: '#8f5a43', // warm skin highlight
  q: '#c9a875', // fur shadow
  Q: '#f2e3c4', // fur light
  l: '#7d482b', // hat shadow
  h: '#a6603a', // hat mid
  H: '#d28e58', // hat light
  a: '#ffd15b', // gold glint
  c: '#e6a83c', // coin
  p: '#a3628f', // scarf accent
}

function row(...runs) {
  const cells = Array(GRID_WIDTH).fill('.')
  runs.forEach(([start, glyphs]) => {
    if (!Number.isInteger(start) || start < 0 || start + glyphs.length > GRID_WIDTH) {
      throw new Error(`Merchant pixel run exceeds ${GRID_WIDTH} columns: ${start}:${glyphs}`)
    }
    ;[...glyphs].forEach((token, offset) => {
      const index = start + offset
      if (cells[index] !== '.') {
        throw new Error(`Merchant pixel runs overlap at column ${index}`)
      }
      cells[index] = token
    })
  })
  return cells.join('')
}

function merchantFrame({ blink = false, coinLift = false } = {}) {
  // The face is intentionally mirror-symmetric so the Merchant reads as
  // front-facing at a glance instead of leaning or staring past the player.
  const faceEyes = blink ? 'sQssffssQs' : 'sQkQffQkQs'
  const coins = coinLift ? 'BcaB' : 'BccB'
  const hand = coinLift ? 'BBcaB' : 'BBccB'
  return [
    row(),
    row(),
    row([11, 'oo']),
    row([9, 'ooHHHoo']),
    row([8, 'oHHHHHHo']),
    row([7, 'oHHHHHHHHo']),
    row([6, 'oHHHHHHHHHHo']),
    row([3, 'oo'], [5, 'hhhhllllhhhhhhhh'], [21, 'oo']),
    row([2, 'o'], [3, 'hHHHHHHHHHHHHHHHHh'], [21, 'o']),
    row([1, 'oo'], [3, 'hhhhhhhhhhllllllll'], [21, 'oo']),
    row([6, 'o'], [7, 'ffffffffff'], [17, 'o']),
    row([6, 'o'], [7, 'fFssssssFf'], [17, 'o']),
    row([6, 'o'], [7, faceEyes], [17, 'o']),
    row([6, 'o'], [7, 'fFssffssFf'], [17, 'o']),
    row([7, 'o'], [8, 'fFsFFsFf'], [16, 'o']),
    row([7, 'o'], [8, 'ffFssFff'], [16, 'o']),
    row([4, 'o'], [5, 'qqQQQQqq'], [13, 'qqQQQQqq'], [21, 'o']),
    row([3, 'o'], [4, 'qqQQQQQQqq'], [14, 'qqQQQQQ'], [21, 'o']),
    row([2, 'o'], [3, 'qqQQQQqqqq'], [14, 'qqQQQQqq'], [22, 'o']),
    row([3, 'o'], [4, 'QQQQQQ'], [10, 'tTTTTTTt'], [18, 'QQQQQ'], [23, 'o']),
    row([5, 'o'], [6, 'tTTTTUUTTTTt'], [18, 'o']),
    row([5, 'o'], [6, 'tTTTTUUTTTTt'], [18, 'o']),
    row([2, 'oBBaB'], [7, 'tTTTkkTTT'], [16, 'o'], [17, hand], [22, 'o']),
    row([3, 'oBB'], [8, 'tTTTTt'], [14, 'tTTTTt'], [20, 'oBBo']),
    row([4, 'o'], [5, 'tTTTTpTTTTTt'], [18, 'o']),
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    // The counter starts around row 23. Keep the commerce cue above it;
    // lower rows preserve the silhouette even though the furniture occludes them.
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([7, 'o'], [8, 'bbTTbb'], [14, 'o'], [15, 'bbTTbb'], [21, 'o']),
    row([6, 'obbbo'], [14, 'obbbo']),
  ]
}

const MERCHANT_FRAMES = [
  merchantFrame(),
  merchantFrame({ blink: true }),
  merchantFrame({ coinLift: true }),
]

function validateFrame(rows) {
  if (rows.length !== GRID_HEIGHT) {
    throw new Error(`Merchant frame must contain ${GRID_HEIGHT} rows`)
  }
  rows.forEach((frameRow, index) => {
    if (frameRow.length !== GRID_WIDTH) {
      throw new Error(`Merchant row ${index} must contain ${GRID_WIDTH} cells`)
    }
    ;[...frameRow].forEach((token) => {
      if (token !== '.' && !PALETTE[token]) {
        throw new Error(`Unknown Merchant pixel token: ${token}`)
      }
    })
  })
}

function renderFrame(rows, frameIndex) {
  validateFrame(rows)
  const cells = []
  rows.forEach((frameRow) => {
    ;[...frameRow].forEach((token) => {
      const color = PALETTE[token]
      cells.push(`<i class="pixel-cell"${color ? ` style="--pixel-color:${color}"` : ''}></i>`)
    })
  })
  return `<span class="pixel-frame-grid" data-frame-index="${frameIndex}" data-frame-width="${GRID_WIDTH}" data-frame-height="${GRID_HEIGHT}" role="presentation" aria-hidden="true">${cells.join('')}</span>`
}

export function merchantPixelSprite() {
  return MERCHANT_FRAMES.map((frame, index) => `<span class="pixel-sprite-frame pixel-sprite-frame-${String.fromCharCode(97 + index)}">${renderFrame(frame, index)}</span>`).join('')
}
