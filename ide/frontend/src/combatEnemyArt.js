// Match stable, public encounter names; an Elder is the same species as its
// ordinary counterpart. Unknown encounters retain the existing placeholder.
const LANTERN_ACTORS = new Set([
  'first-spark', 'whispering-gate', 'endless-echo', 'little-lantern',
  'inventory-drowner', 'counting-moth', 'mapkeeper', 'delivery-beast',
  'broken-number', 'test-lantern', 'module-mason', 'selfless-golem',
  'clockwork-caravan', 'memory-keeper', 'quiet-flame', 'transformation-sprite',
  'remembering-shade', 'unwritten-road', 'unwritten-king',
])

export function combatEnemyArt(name, projectId = '') {
  const normal = String(name || '').trim().toLowerCase().replace(/^(the|elder)\s+/, '')
  const slug = normal.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  if (projectId === '01-blackjack') {
    const actors = { 'empty-table': 'empty-table', 'dealer-s-hand': 'dealers-hand', 'count-keeper': 'count-keeper', hitman: 'hitman', 'bust-hound': 'bust-hound', 'house-clerk': 'house-clerk', judge: 'judge', 'rematch-shade': 'rematch-shade' }
    if (actors[slug]) return `blackjack-${actors[slug]}`
  }
  if (projectId === '04-casino-slots' && slug === 'ekse-ouens-p-diddy') return 'silver-mogul'
  if (projectId === '05-dungeon-crawler' && slug === 'die-tozza-van-zamalek') return 'tozza'
  if (projectId === '01-blackjack' && slug === 'house') return 'blackjack-house'
  if (projectId === '00-lantern-vale' && slug === 'lord-twang-iii') return 'lantern-unwritten-king'
  if (projectId === '00-lantern-vale' && LANTERN_ACTORS.has(slug)) return `lantern-${slug}`
  return ({
    'nameless wraith': 'wraith',
    'string mimic': 'string-mimic',
    'forked path': 'forked-path',
    'mimic matriarch': 'mimic-matriarch',
    'indexerror drowner': 'drowner',
    'keyerror ghoul': 'ghoul',
    'loaded die': 'loaded-die',
    'drowned hoard': 'drowned-hoard',
  })[normal] || 'wraith'
}
