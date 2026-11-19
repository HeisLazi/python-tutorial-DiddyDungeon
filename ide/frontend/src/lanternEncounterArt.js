// Only opt in named Lantern Vale encounters: other campaigns can reuse names.
const LANTERN_ENCOUNTERS = new Set([
  'first-spark', 'nameless-wraith', 'whispering-gate', 'forked-path', 'endless-echo',
  'little-lantern', 'inventory-drowner', 'counting-moth', 'mapkeeper', 'delivery-beast',
  'broken-number', 'test-lantern', 'module-mason', 'selfless-golem', 'clockwork-caravan',
  'memory-keeper', 'quiet-flame', 'transformation-sprite', 'remembering-shade', 'unwritten-road', 'unwritten-king',
])

export function lanternEncounterArt(projectId, name) {
  if (projectId !== '00-lantern-vale' || !name) return null
  const slug = name.toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').replace(/^lord-twang-iii$/, 'unwritten-king')
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
  const slug = name.toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').replace(/^lord-twang-iii$/, 'unwritten-king')
  const location = LANTERN_LOCATIONS.find(([, encounters]) => encounters.includes(slug))?.[0]
  return location ? `${(import.meta.env?.BASE_URL || '/')}campaign-art/lantern-vale/locations/${location}.png` : null
}

// Where each encounter happens inside its region (x, y as % of the 16:9 scene).
// The region is the location art for that act; the spot is a named place on it.
const LANTERN_SPOTS = {
  'first-spark': ['The Alley', 13, 58], 'nameless-wraith': ['The Noticeboard', 31, 50], 'whispering-gate': ['The Well Gate', 50, 56],
  'forked-path': ['The Crossroads', 68, 60], 'endless-echo': ['The Echoing Arcade', 87, 48],
  'little-lantern': ['The Lamplighter\u2019s Post', 11, 52], 'inventory-drowner': ['The Riverbank', 29, 59], 'counting-moth': ['The Moth Lamps', 46, 50],
  'mapkeeper': ['The Waystone', 61, 60], 'delivery-beast': ['The Old Bridge', 79, 50],
  'broken-number': ['The Smouldering Forge', 14, 56], 'test-lantern': ['The Lantern Rack', 32, 42], 'module-mason': ['The Workbench', 50, 59],
  'selfless-golem': ['The Golem Alcove', 68, 50], 'clockwork-caravan': ['The Parts Shelves', 87, 52],
  'memory-keeper': ['The Archive Arch', 13, 48], 'quiet-flame': ['The Stone Lantern', 31, 58], 'transformation-sprite': ['The Garden Path', 49, 60],
  'remembering-shade': ['The Ruined Terrace', 68, 56], 'unwritten-road': ['The Moonlit Stair', 87, 46],
}
const LANTERN_REGION_NAMES = { 'first-light': 'First Light Town', 'vale-road': 'The Vale Road', workshop: 'The Workshop', 'living-vale': 'The Living Vale' }

export function lanternEncounterSpot(projectId, name) {
  if (projectId !== '00-lantern-vale' || !name) return null
  const slug = name.toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const spot = LANTERN_SPOTS[slug]
  if (!spot) return null
  const region = LANTERN_LOCATIONS.find(([, encounters]) => encounters.includes(slug))?.[0]
  return { place: spot[0], x: spot[1], y: spot[2], region: LANTERN_REGION_NAMES[region] || '' }
}

// The campaign map is the painted world map (campaign-art/maps/dungeon-world.png).
// Each act is a region of it; each encounter is a named place there (x, y as % of
// the map). `focus` is where the camera sits when that region is open.
const WORLD_REGIONS = {
  'first-light': { name: 'First Light Town', fx: 17, fy: 69, zoom: 2.7, w: 24, h: 26 },
  'vale-road': { name: 'The Vale Road', fx: 43, fy: 69, zoom: 2.0, w: 38, h: 26 },
  workshop: { name: 'The Workshop', fx: 83, fy: 78, zoom: 2.7, w: 34, h: 26 },
  'living-vale': { name: 'The Living Vale', fx: 63, fy: 36, zoom: 1.35, w: 48, h: 56 },
}
const WORLD_SPOTS = {
  'first-spark': ['The Alley', 10, 69], 'nameless-wraith': ['The Noticeboard', 14.5, 64], 'whispering-gate': ['The Well Gate', 19, 69],
  'forked-path': ['The Crossroads', 23.5, 74], 'endless-echo': ['The Echoing Arcade', 16, 75],
  'little-lantern': ['The Lamplighter\u2019s Post', 27, 66], 'inventory-drowner': ['The Riverbank', 32, 72], 'counting-moth': ['The Moth Lamps', 37, 62],
  'mapkeeper': ['The Waystone', 47, 70], 'delivery-beast': ['The Old Bridge', 60, 77],
  'broken-number': ['The Smouldering Forge', 72, 80], 'test-lantern': ['The Lantern Rack', 77, 74], 'module-mason': ['The Workbench', 82, 81],
  'selfless-golem': ['The Golem Alcove', 88, 74], 'clockwork-caravan': ['The Parts Shelves', 93, 82],
  'memory-keeper': ['The Archive Arch', 69, 55], 'quiet-flame': ['The Stone Lantern', 62, 45], 'transformation-sprite': ['The Garden Path', 54, 38],
  'remembering-shade': ['The Ruined Terrace', 50, 17], 'unwritten-road': ['The Moonlit Stair', 82, 24],
}
export const WORLD_MAP_ART = 'campaign-art/maps/dungeon-world.png'
export const WORLD_FOCUS = { fx: 50, fy: 50, zoom: 1 }

export function lanternWorldSpot(projectId, name) {
  if (projectId !== '00-lantern-vale' || !name) return null
  const slug = name.toLowerCase().replace(/^the\s+/, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
  const spot = WORLD_SPOTS[slug]
  if (!spot) return null
  const key = LANTERN_LOCATIONS.find(([, encounters]) => encounters.includes(slug))?.[0]
  const region = WORLD_REGIONS[key]
  return region ? { place: spot[0], x: spot[1], y: spot[2], region: region.name, regionKey: key, focus: region } : null
}
export const worldRegions = () => Object.entries(WORLD_REGIONS).map(([key, region]) => ({ key, ...region }))
