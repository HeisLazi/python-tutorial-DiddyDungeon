const GRID_WIDTH = 24
const GRID_HEIGHT = 32

// The prototype merchant is deliberately data-driven: every frame is a
// bounded 24x32 cell sheet, so animation never bleeds into a neighbouring
// frame or turns into a scaled illustration.
const PALETTE = {
  o: '#091212', k: '#17221f', t: '#164945', T: '#2d8178', U: '#4fa696',
  b: '#4a2a20', B: '#8b4b2c', f: '#281c1d', F: '#5b392f', s: '#8f5a43',
  q: '#c9a875', Q: '#f2e3c4', l: '#7d482b', h: '#a6603a', H: '#d28e58',
  a: '#ffd15b', c: '#e6a83c', p: '#a3628f',
}

function row(...runs) {
  const cells = Array(GRID_WIDTH).fill('.')
  runs.forEach(([start, glyphs]) => {
    if (!Number.isInteger(start) || start < 0 || start + glyphs.length > GRID_WIDTH) throw new Error(`Merchant pixel run exceeds ${GRID_WIDTH} columns`)
    ;[...glyphs].forEach((token, offset) => {
      const index = start + offset
      if (cells[index] !== '.') throw new Error(`Merchant pixel runs overlap at column ${index}`)
      cells[index] = token
    })
  })
  return cells.join('')
}

function merchantFrame({ blink = false, coinLift = false } = {}) {
  const faceEyes = blink ? 'sQssffssQs' : 'sQkQffQkQs'
  const hand = coinLift ? 'BBcaB' : 'BBccB'
  return [
    row(), row(), row([11, 'oo']), row([9, 'ooHHHoo']), row([8, 'oHHHHHHo']),
    row([7, 'oHHHHHHHHo']), row([6, 'oHHHHHHHHHHo']),
    row([3, 'oo'], [5, 'hhhhllllhhhhhhhh'], [21, 'oo']),
    row([2, 'o'], [3, 'hHHHHHHHHHHHHHHHHh'], [21, 'o']),
    row([1, 'oo'], [3, 'hhhhhhhhhhllllllll'], [21, 'oo']),
    row([6, 'o'], [7, 'ffffffffff'], [17, 'o']),
    row([6, 'o'], [7, 'fFssssssFf'], [17, 'o']),
    row([6, 'o'], [7, faceEyes], [17, 'o']),
    row([6, 'o'], [7, 'fFssffssFf'], [17, 'o']),
    row([7, 'o'], [8, 'fFsFFsFf'], [16, 'o']), row([7, 'o'], [8, 'ffFssFff'], [16, 'o']),
    row([4, 'o'], [5, 'qqQQQQqq'], [13, 'qqQQQQqq'], [21, 'o']),
    row([3, 'o'], [4, 'qqQQQQQQqq'], [14, 'qqQQQQQ'], [21, 'o']),
    row([2, 'o'], [3, 'qqQQQQqqqq'], [14, 'qqQQQQqq'], [22, 'o']),
    row([3, 'o'], [4, 'QQQQQQ'], [10, 'tTTTTTTt'], [18, 'QQQQQ'], [23, 'o']),
    row([5, 'o'], [6, 'tTTTTUUTTTTt'], [18, 'o']), row([5, 'o'], [6, 'tTTTTUUTTTTt'], [18, 'o']),
    row([2, 'oBBaB'], [7, 'tTTTkkTTT'], [16, 'o'], [17, hand], [22, 'o']),
    row([3, 'oBB'], [8, 'tTTTTt'], [14, 'tTTTTt'], [20, 'oBBo']),
    row([4, 'o'], [5, 'tTTTTpTTTTTt'], [18, 'o']), row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']), row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']), row([4, 'o'], [5, 'tTTTTTTTTTTt'], [18, 'o']),
    row([7, 'o'], [8, 'bbTTbb'], [14, 'o'], [15, 'bbTTbb'], [21, 'o']),
    row([6, 'obbbo'], [14, 'obbbo']),
  ]
}

const MERCHANT_FRAMES = [merchantFrame(), merchantFrame({ blink: true }), merchantFrame({ coinLift: true })]

function renderFrame(rows, frameIndex) {
  if (rows.length !== GRID_HEIGHT || rows.some((line) => line.length !== GRID_WIDTH)) throw new Error('Merchant pixel frame dimensions are invalid')
  const cells = rows.flatMap((line) => [...line].map((token) => `<i class="pixel-cell"${PALETTE[token] ? ` style="--pixel-color:${PALETTE[token]}"` : ''}></i>`))
  return `<span class="pixel-frame-grid" data-frame-index="${frameIndex}" data-frame-width="${GRID_WIDTH}" data-frame-height="${GRID_HEIGHT}">${cells.join('')}</span>`
}

export function merchantPixelSprite() {
  return MERCHANT_FRAMES.map((frame, index) => `<span class="pixel-sprite-frame pixel-sprite-frame-${String.fromCharCode(97 + index)}">${renderFrame(frame, index)}</span>`).join('')
}
