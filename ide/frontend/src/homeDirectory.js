// These are walkable rooms, not fast-travel destinations.
export const HOME_DIRECTORY = [
  { id: 'den', short: 'Pyr’s Den', name: 'Pyr’s Den', places: 'Visit and care for Pyr', x: 25, y: 5, exits: { south: 'great_hall' } },
  { id: 'great_hall', short: 'Home', name: 'Great Hall', places: 'Rest, hunter upgrades, gear & trophies', x: 25, y: 50, exits: { north: 'den' } },
]
