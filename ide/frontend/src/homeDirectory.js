// Positions describe the walkable Godot rooms, not fast-travel destinations.
export const HOME_DIRECTORY = [
  { id: 'gallery', short: 'Gallery', name: 'Trophy Gallery', places: 'Trophies & stats', x: 10, y: 5, exits: { south: 'library' } },
  { id: 'library', short: 'Library', name: 'Library', places: 'Tutor & study', x: 10, y: 50, exits: { north: 'gallery', south: 'pantry', east: 'great_hall' } },
  { id: 'pantry', short: 'Pantry', name: 'Pantry', places: 'Meals', x: 10, y: 95, exits: { north: 'library' } },
  { id: 'great_hall', short: 'Hall', name: 'Great Hall', places: 'Hearth & Forge', x: 65, y: 50, exits: { west: 'library', east: 'armory' } },
  { id: 'armory', short: 'Arms', name: 'Hall of Arms', places: 'Gear & training', x: 120, y: 50, exits: { west: 'great_hall', north: 'war_room' } },
  { id: 'war_room', short: 'War Room', name: 'War Room', places: 'Dungeon map', x: 120, y: 5, exits: { south: 'armory', east: 'den' } },
  { id: 'den', short: 'Den', name: "Pyr’s Den", places: 'Pyr’s perch', x: 175, y: 5, exits: { west: 'war_room' } },
]
