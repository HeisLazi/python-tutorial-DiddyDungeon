// Both purchase gateways remain authoritative for their existing inventories.
export function merchantLots(armoryLots, classicStock, purchases, coins) {
  const owned = new Set(Array.isArray(purchases) ? purchases : [])
  const classic = classicStock.map((item) => ({
    id: item.id, name: item.name, slot: item.kind === 'Armor' ? 'armor' : item.kind === 'Trinket' ? 'trinket' : 'supply',
    tier: item.price >= 120 ? 'rare' : item.price >= 70 ? 'uncommon' : 'common',
    effect: item.detail, price: item.price, campaign: 'merchant', source: 'merchant',
    owned: item.kind !== 'Supply' && owned.has(item.id), locked: null, affordable: (item.kind === 'Supply' || !owned.has(item.id)) && coins >= item.price,
  }))
  return [...(Array.isArray(armoryLots) ? armoryLots : []).map((item) => ({ ...item, source: 'armory' })), ...classic].sort((a, b) => Number(Boolean(a.locked)) - Number(Boolean(b.locked)))
}
