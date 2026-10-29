// Match stable, public encounter names; an Elder is the same species as its
// ordinary counterpart. Unknown encounters retain the existing placeholder.
export function combatEnemyArt(name) {
  const normal = String(name || '').trim().toLowerCase().replace(/^(the|elder)\s+/, '')
  return ({
    'nameless wraith': 'wraith',
    'string mimic': 'string-mimic',
    'forked path': 'forked-path',
    'mimic matriarch': 'mimic-matriarch',
  })[normal] || 'wraith'
}
