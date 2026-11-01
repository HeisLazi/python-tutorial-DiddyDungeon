// Only opt in named Lantern Vale encounters: other campaigns can reuse names.
const LANTERN_ENCOUNTERS = new Set([
  'first-spark', 'nameless-wraith', 'whispering-gate', 'forked-path', 'endless-echo',
  'little-lantern', 'inventory-drowner', 'counting-moth', 'mapkeeper', 'delivery-beast',
  'broken-number', 'test-lantern', 'module-mason', 'selfless-golem', 'clockwork-caravan',
  'memory-keeper', 'quiet-flame', 'transformation-sprite', 'remembering-shade', 'unwritten-road', 'unwritten-king',
])

export function lanternEncounterArt(projectId, name) {
  if (projectId !== '00-lantern-vale' || !name) return null
  const slug = name.toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  return LANTERN_ENCOUNTERS.has(slug) ? `${(import.meta.env?.BASE_URL || '/')}campaign-art/lantern-vale/${slug}.png` : null
}

// Each encounter belongs to a specific place in the beginner story.
const LANTERN_LOCATIONS = [
  ['first-light', ['first-spark', 'nameless-wraith', 'whispering-gate', 'forked-path', 'endless-echo']],
  ['vale-road', ['little-lantern', 'inventory-drowner', 'counting-moth', 'mapkeeper', 'delivery-beast']],
  ['workshop', ['broken-number', 'test-lantern', 'module-mason', 'selfless-golem', 'clockwork-caravan']],
  ['living-vale', ['memory-keeper', 'quiet-flame', 'transformation-sprite', 'remembering-shade', 'unwritten-road', 'unwritten-king']],
]

export function lanternEncounterLocation(projectId, name) {
  if (projectId !== '00-lantern-vale' || !name) return null
  const slug = name.toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const location = LANTERN_LOCATIONS.find(([, encounters]) => encounters.includes(slug))?.[0]
  return location ? `${(import.meta.env?.BASE_URL || '/')}campaign-art/lantern-vale/locations/${location}.png` : null
}
