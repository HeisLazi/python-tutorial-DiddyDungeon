// These are walkable rooms, not fast-travel destinations.
export const HOME_DIRECTORY = [
  { id: 'den', short: 'Pyr’s Den', name: 'Pyr’s Den', places: 'Visit and care for Pyr', x: 2, y: 5, exits: { south: 'great_hall' } },
  { id: 'still', short: 'The Still', name: 'Hunter’s Still', places: 'Crafting and Legacy Journal', x: 48, y: 5, exits: { south: 'great_hall' } },
  { id: 'great_hall', short: 'Home', name: 'Great Hall', places: 'Rest, hunter upgrades, gear & trophies', x: 25, y: 55, exits: { northwest: 'den', northeast: 'still' } },
]
